"""Recursive MinHash blocker.

This module implements Steps 5-9 of the algorithm:

    5. Compute global + per-block frequencies of tokens and signatures.
    6. Strip *global* stop words / signatures (auto + manual).
    7. Identify "blocking signatures": alpha <= freq <= beta.
    8. Group records by chosen blocking signatures (multi-membership allowed).
    9. Recurse inside each block, banning ancestor blocking keys, until a
       stop condition is reached.

The public entry point is :class:`RecursiveMinHashBlocker`.
"""

from __future__ import annotations

import logging
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

import pandas as pd

from .config import BlockerConfig
from .minhash_utils import MinHasher, jaccard
from .preprocess import qgrams_for_tokens, tokenize_dataframe

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------------- #
@dataclass
class Block:
    """One node in the recursive blocking tree (final or intermediate)."""

    block_id: int
    depth: int
    parent_block: Optional[int]
    blocking_key: Optional[str]          # None only for the synthetic root
    member_record_ids: List[object]      # original RecID values
    size: int
    used_keys_path: FrozenSet[str]       # ancestor + own keys, bans reuse
    # Optional: intra-block similarity scores (RecID_a, RecID_b, score)
    similarity_scores: List[Tuple[object, object, float]] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Main class
# --------------------------------------------------------------------------- #
class RecursiveMinHashBlocker:
    """Build candidate blocks from a tabular dataset using recursive MinHash."""

    def __init__(self, config: Optional[BlockerConfig] = None) -> None:
        self.config = config or BlockerConfig()
        self.hasher = MinHasher(
            num_perm=self.config.num_perm, seed=self.config.minhash_seed
        )

        # Populated by .fit():
        self._df: Optional[pd.DataFrame] = None
        self._records: Dict[object, Dict[str, object]] = {}
        # rec_idx -> list of MinHash block keys for that record
        self._record_signatures: Dict[object, List[str]] = {}
        # global frequencies
        self._global_token_freq: Counter = Counter()
        self._global_sig_freq: Counter = Counter()
        # global stopword sets (signatures, since blocking happens on sigs)
        self._stop_signatures: Set[str] = set()

        # Output:
        self.blocks: List[Block] = []
        self._next_block_id: int = 0
        self.max_depth_reached: int = 0

    # --------------------------------------------------------------- helpers
    def _new_block_id(self) -> int:
        bid = self._next_block_id
        self._next_block_id += 1
        return bid

    # ------------------------------------------------------------- pipeline
    def fit(self, df: pd.DataFrame) -> "RecursiveMinHashBlocker":
        """Run the full blocking pipeline on *df*.

        Returns self so callers can chain `.fit(df).export(...)`.
        """
        cfg = self.config
        if cfg.id_column not in df.columns:
            raise KeyError(
                f"id_column '{cfg.id_column}' not found in dataframe columns "
                f"{list(df.columns)}"
            )

        # Reset state so .fit() is idempotent.
        self._df = df.reset_index(drop=True).copy()
        self._records = {
            row[cfg.id_column]: row.to_dict() for _, row in self._df.iterrows()
        }
        self.blocks = []
        self._next_block_id = 0
        self.max_depth_reached = 0

        # ---- Step 1-3: tokenize ----
        rec_to_tokens = tokenize_dataframe(
            self._df, cfg.blocking_columns, cfg.normalization_map
        )
        # Re-key by RecID so blocks reference user-facing IDs.
        rec_to_tokens = {
            self._df.loc[idx, cfg.id_column]: toks for idx, toks in rec_to_tokens.items()
        }

        # ---- Step 4: q-grams + MinHash, but only once per *unique* token ----
        all_tokens: Set[str] = set()
        for toks in rec_to_tokens.values():
            all_tokens.update(toks)
        token_to_qgrams = qgrams_for_tokens(all_tokens, cfg.q)
        token_to_key = self.hasher.hash_many(token_to_qgrams)

        # ---- Step 5: global frequencies ----
        # We count *signatures per record*, not per token occurrence, so a
        # record that says "smith smith smith" still only contributes 1 to
        # the global frequency of MH(smith). This matches blocking semantics.
        for rec_id, toks in rec_to_tokens.items():
            unique_keys: List[str] = []
            seen: Set[str] = set()
            for t in toks:
                self._global_token_freq[t] += 1  # raw token freq, all occurrences
                k = token_to_key.get(t, "MH_EMPTY")
                if k == "MH_EMPTY" or k in seen:
                    continue
                seen.add(k)
                unique_keys.append(k)
            self._record_signatures[rec_id] = unique_keys
            for k in unique_keys:
                self._global_sig_freq[k] += 1

        logger.info(
            "Built signatures for %d records (%d unique tokens, %d unique sigs)",
            len(rec_to_tokens),
            len(all_tokens),
            len(self._global_sig_freq),
        )

        # ---- Step 6: global stop words / signatures ----
        self._compute_stop_signatures(token_to_key)

        # ---- Steps 7-9: recursive blocking ----
        all_rec_ids = list(self._record_signatures.keys())
        root = Block(
            block_id=self._new_block_id(),
            depth=0,
            parent_block=None,
            blocking_key=None,
            member_record_ids=all_rec_ids,
            size=len(all_rec_ids),
            used_keys_path=frozenset(),
        )
        # Don't emit the synthetic root as a "real" candidate block; only its
        # children (and their descendants) appear in self.blocks.
        self._recurse(root)

        if cfg.score_jaccard:
            self._score_final_blocks(rec_to_tokens)

        return self

    # ------------------------------------------------------------ stopwords
    def _compute_stop_signatures(self, token_to_key: Dict[str, str]) -> None:
        cfg = self.config

        # Manual list: user passes raw tokens → translate to signatures.
        manual_sigs = {
            token_to_key[t.lower()]
            for t in cfg.manual_stopwords
            if t.lower() in token_to_key
        }

        # Auto: top percentile of signatures by global frequency.
        auto_sigs: Set[str] = set()
        if cfg.auto_stopword_top_percentile > 0 and self._global_sig_freq:
            n = len(self._global_sig_freq)
            cutoff = max(1, math.ceil(n * cfg.auto_stopword_top_percentile))
            most_common = self._global_sig_freq.most_common(cutoff)
            auto_sigs = {sig for sig, _ in most_common}

        self._stop_signatures = manual_sigs | auto_sigs
        logger.info(
            "Stop signatures: %d (manual=%d, auto=%d)",
            len(self._stop_signatures),
            len(manual_sigs),
            len(auto_sigs),
        )

    # -------------------------------------------------------------- recurse
    def _recurse(self, parent: Block) -> None:
        cfg = self.config

        # Termination by depth or block size
        if parent.depth >= cfg.max_depth:
            self._emit_if_real(parent)
            return
        if parent.size <= cfg.min_block_size:
            self._emit_if_real(parent)
            return

        # Local frequencies, restricted to records inside this block.
        local_freq: Counter = Counter()
        for rec_id in parent.member_record_ids:
            for sig in self._record_signatures[rec_id]:
                if sig in self._stop_signatures:
                    continue
                if sig in parent.used_keys_path:
                    continue
                local_freq[sig] += 1

        # Step 7: candidate blocking signatures.
        candidates: List[Tuple[str, int]] = [
            (sig, freq)
            for sig, freq in local_freq.items()
            if cfg.alpha <= freq <= cfg.beta
        ]
        if not candidates:
            self._emit_if_real(parent)
            return

        # Pick the rarest-but-valid signatures first — they discriminate best.
        candidates.sort(key=lambda x: (x[1], x[0]))
        chosen = candidates[: max(1, cfg.max_keys_per_level)]
        logger.debug(
            "Block %s depth=%d size=%d → %d candidates, picked %d",
            parent.block_id, parent.depth, parent.size, len(candidates), len(chosen),
        )

        produced_child = False
        for sig, _freq in chosen:
            members = [
                rec_id
                for rec_id in parent.member_record_ids
                if sig in self._record_signatures[rec_id]
            ]
            # alpha already guarantees freq >= alpha, but defensively:
            if len(members) < max(2, cfg.min_block_size):
                continue
            child = Block(
                block_id=self._new_block_id(),
                depth=parent.depth + 1,
                parent_block=parent.block_id if parent.depth > 0 else None,
                blocking_key=sig,
                member_record_ids=members,
                size=len(members),
                used_keys_path=parent.used_keys_path | {sig},
            )
            produced_child = True
            self.max_depth_reached = max(self.max_depth_reached, child.depth)
            # Always emit the child as a candidate block (it's a real grouping)
            # *and* attempt to recurse further inside it.
            self.blocks.append(child)
            self._recurse(child)

        if not produced_child:
            # No usable child means this is a terminal block.
            self._emit_if_real(parent)

    def _emit_if_real(self, block: Block) -> None:
        # Skip the synthetic depth-0 root node.
        if block.depth == 0 and block.blocking_key is None:
            return
        if block not in self.blocks:
            self.blocks.append(block)

    # ------------------------------------------------------- jaccard scoring
    def _score_final_blocks(self, rec_to_tokens: Dict[object, List[str]]) -> None:
        """Optional Step (extra): pairwise Jaccard inside each final block."""
        for block in self.blocks:
            members = block.member_record_ids
            if len(members) < 2:
                continue
            scores: List[Tuple[object, object, float]] = []
            for i, a in enumerate(members):
                for b in members[i + 1 :]:
                    s = jaccard(rec_to_tokens.get(a, []), rec_to_tokens.get(b, []))
                    scores.append((a, b, s))
            block.similarity_scores = scores

    # ----------------------------------------------------------------- views
    def to_dict(self) -> List[Dict[str, object]]:
        """Serialize all candidate blocks as a list of dicts."""
        out: List[Dict[str, object]] = []
        for b in self.blocks:
            out.append(
                {
                    "block_id": b.block_id,
                    "depth": b.depth,
                    "parent_block": b.parent_block,
                    "blocking_key": b.blocking_key,
                    "size": b.size,
                    "member_record_ids": list(b.member_record_ids),
                    "members": [self._records[r] for r in b.member_record_ids],
                    "similarity_scores": b.similarity_scores,
                }
            )
        return out

    def export_csv(self, path: str) -> None:
        """Write a long-form CSV: one row per (block, record) pair."""
        if self._df is None:
            raise RuntimeError("Call .fit(df) before exporting.")
        cfg = self.config
        rows: List[Dict[str, object]] = []
        for b in self.blocks:
            for rec_id in b.member_record_ids:
                full = dict(self._records[rec_id])
                rows.append(
                    {
                        "block_id": b.block_id,
                        "depth": b.depth,
                        "parent_block": b.parent_block,
                        "blocking_key": b.blocking_key,
                        cfg.id_column: rec_id,
                        **full,
                    }
                )
        out_df = pd.DataFrame(rows)
        out_df.to_csv(path, index=False)
        logger.info("Wrote %d block-record rows to %s", len(rows), path)

    def print_report(self) -> None:
        """Human-readable per-block dump (Step Output #2)."""
        cfg = self.config
        print("\n" + "=" * 60)
        print(f"FINAL BLOCK REPORT  ({len(self.blocks)} blocks)")
        print("=" * 60)
        for b in self.blocks:
            print(f"\nBlock {b.block_id}")
            print(f"Depth: {b.depth}")
            print(f"Parent: {b.parent_block}")
            print(f"Blocking Key: {b.blocking_key}")
            print(f"Size: {b.size}")
            for rec_id in b.member_record_ids:
                rec = self._records[rec_id]
                fields = " | ".join(
                    f"{k}: {rec.get(k)}"
                    for k in [cfg.id_column, *cfg.blocking_columns]
                    if k in rec
                )
                print(f"  {fields}")
            if b.similarity_scores:
                print("  -- Jaccard scores --")
                for a, c, s in b.similarity_scores:
                    print(f"  {a} <-> {c} : {s:.3f}")
