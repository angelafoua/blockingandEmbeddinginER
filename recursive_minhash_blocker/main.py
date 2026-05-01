"""CLI entry point + sample-dataset generator for the Recursive MinHash Blocker.

Examples
--------

Generate a synthetic dataset and run blocking:

    python -m recursive_minhash_blocker.main --generate-sample sample.csv --rows 500
    python -m recursive_minhash_blocker.main --input sample.csv \\
        --columns Name Address --alpha 2 --beta 200 --q 2 --num_perm 64 \\
        --max_depth 4 --min_block_size 2 --output blocks.csv

Run on your own CSV:

    python -m recursive_minhash_blocker.main --input mydata.csv \\
        --columns Name Address --score-jaccard

Enable global token correction before blocking (DWM25-style):

    python -m recursive_minhash_blocker.main --input mydata.csv \\
        --columns Name Address --global-correction \\
        --gc-min-freq-std 10 --gc-min-len-std 3 --gc-max-freq-err 3
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from pathlib import Path
from typing import List, Optional, Sequence

import pandas as pd

from .blocking import RecursiveMinHashBlocker
from .config import BlockerConfig
from .metrics import compute_metrics, print_metrics


# --------------------------------------------------------------------------- #
# Sample data generator
# --------------------------------------------------------------------------- #
_FIRST = ["John", "Jon", "Jane", "Mary", "Maria", "Robert", "Bob", "Mike",
          "Michael", "Alice", "Liz", "Elizabeth", "Tom", "Thomas", "Sara",
          "Sarah", "Peter", "Pete", "Anna", "Anne"]
_LAST = ["Smith", "Smyth", "Johnson", "Williams", "Brown", "Jones", "Garcia",
         "Miller", "Davis", "Lopez", "Martinez", "Wilson", "Anderson", "Taylor"]
_STREETS = ["Main", "Oak", "Pine", "Maple", "Cedar", "Elm", "Lake", "Hill",
            "River", "Park", "Sunset", "Washington", "Lincoln", "Madison"]
_SUFFIX_PAIRS = [("Street", "St"), ("Road", "Rd"), ("Avenue", "Ave"),
                 ("Boulevard", "Blvd"), ("Lane", "Ln"), ("Drive", "Dr")]
_CITIES = ["Springfield", "Riverside", "Franklin", "Greenville", "Bristol"]


def _maybe_typo(s: str, rng: random.Random, p: float = 0.15) -> str:
    """Inject a single-character typo with probability p - simulates dirty data."""
    if len(s) < 3 or rng.random() > p:
        return s
    i = rng.randrange(len(s))
    op = rng.choice(("drop", "swap", "dup"))
    if op == "drop":
        return s[:i] + s[i + 1 :]
    if op == "dup":
        return s[: i + 1] + s[i] + s[i + 1 :]
    # swap with neighbor
    if i + 1 < len(s):
        return s[:i] + s[i + 1] + s[i] + s[i + 2 :]
    return s


def generate_sample_dataset(
    n_rows: int = 500,
    duplicate_ratio: float = 0.3,
    seed: int = 0,
    out_path: Optional[str] = None,
) -> pd.DataFrame:
    """Build a small entity-resolution-style dataset with planted duplicates.

    duplicate_ratio is the share of records that are noisy variants of an
    earlier record (different RecID, same logical entity).
    """
    rng = random.Random(seed)
    rows: List[dict] = []
    n_unique = max(1, int(n_rows * (1 - duplicate_ratio)))
    base_records: List[dict] = []

    for i in range(n_unique):
        first = rng.choice(_FIRST)
        last = rng.choice(_LAST)
        num = rng.randint(1, 9999)
        street = rng.choice(_STREETS)
        long_suf, _short_suf = rng.choice(_SUFFIX_PAIRS)
        city = rng.choice(_CITIES)
        rec = {
            "RecID": 1000 + i,
            "Name": f"{first} {last}",
            "Address": f"{num} {street} {long_suf}, {city}",
        }
        rows.append(rec)
        base_records.append(rec)

    next_id = 1000 + n_unique
    while len(rows) < n_rows:
        base = rng.choice(base_records)
        first, last = base["Name"].split(" ", 1)
        # Variations: initial-only first name, abbreviated suffix, typos.
        if rng.random() < 0.4:
            first_v = first[0]
        else:
            first_v = _maybe_typo(first, rng)
        last_v = _maybe_typo(last, rng)
        addr_v = base["Address"]
        for long_suf, short_suf in _SUFFIX_PAIRS:
            if long_suf in addr_v and rng.random() < 0.6:
                addr_v = addr_v.replace(long_suf, short_suf)
                break
        addr_v = _maybe_typo(addr_v, rng, p=0.1)
        rows.append({
            "RecID": next_id,
            "Name": f"{first_v} {last_v}",
            "Address": addr_v,
        })
        next_id += 1

    df = pd.DataFrame(rows)
    if out_path:
        df.to_csv(out_path, index=False)
    return df


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="recursive_minhash_blocker",
        description="Recursive MinHash blocking for entity resolution.",
    )
    p.add_argument("--input", type=str, help="Path to input CSV.")
    p.add_argument(
        "--columns",
        nargs="+",
        default=["Name", "Address"],
        help="Columns to concatenate for tokenization (default: Name Address).",
    )
    p.add_argument("--id-column", type=str, default="RecID",
                   help="Name of the unique-record-id column (default: RecID).")
    p.add_argument("--alpha", type=int, default=2,
                   help="Min frequency for a useful blocking signature.")
    p.add_argument("--beta", type=int, default=1000,
                   help="Max frequency for a useful blocking signature.")
    p.add_argument("--q", type=int, default=2, help="Q-gram size (default: 2).")
    p.add_argument("--num_perm", type=int, default=64,
                   help="MinHash permutations (default: 64).")
    p.add_argument("--max_depth", type=int, default=5)
    p.add_argument("--min_block_size", type=int, default=2)
    p.add_argument("--max_keys_per_level", type=int, default=3)
    p.add_argument("--auto-stop-percentile", type=float, default=0.005,
                   help="Top-X fraction of signatures to drop as stop words.")
    p.add_argument("--manual-stopwords", nargs="*", default=[],
                   help="Tokens (raw words) to forcibly treat as stop words.")
    p.add_argument("--score-jaccard", action="store_true",
                   help="Compute pairwise Jaccard inside each final block.")
    p.add_argument("--output", type=str, default=None,
                   help="Path for the long-form output CSV.")
    p.add_argument("--no-report", action="store_true",
                   help="Skip the human-readable per-block report.")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    # Sample-data utilities
    p.add_argument("--generate-sample", type=str, default=None,
                   help="Write a synthetic CSV to this path and exit.")
    p.add_argument("--rows", type=int, default=500,
                   help="Number of rows for --generate-sample.")
    p.add_argument("--seed", type=int, default=0, help="Sample-generator seed.")
    # Global correction (DWM25-style)
    p.add_argument("--global-correction", action="store_true",
                   help="Apply DWM25 global token correction before blocking.")
    p.add_argument("--gc-word-list", type=str, default=None,
                   help="Path to DWM_WordList.txt for the global correction step.")
    p.add_argument("--gc-min-freq-std", type=int, default=10,
                   help="Min token frequency to be treated as a standard form (default: 10).")
    p.add_argument("--gc-min-len-std", type=int, default=3,
                   help="Min token length to be treated as a standard form (default: 3).")
    p.add_argument("--gc-max-freq-err", type=int, default=3,
                   help="Max token frequency to be a correction candidate (default: 3).")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.generate_sample:
        df = generate_sample_dataset(
            n_rows=args.rows, seed=args.seed, out_path=args.generate_sample
        )
        print(f"Wrote {len(df)} rows to {args.generate_sample}")
        return 0

    if not args.input:
        print("ERROR: --input is required (or use --generate-sample).", file=sys.stderr)
        return 2
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"ERROR: input file not found: {in_path}", file=sys.stderr)
        return 2

    df = pd.read_csv(in_path)
    cfg = BlockerConfig(
        id_column=args.id_column,
        blocking_columns=list(args.columns),
        q=args.q,
        num_perm=args.num_perm,
        alpha=args.alpha,
        beta=args.beta,
        max_depth=args.max_depth,
        min_block_size=args.min_block_size,
        max_keys_per_level=args.max_keys_per_level,
        auto_stopword_top_percentile=args.auto_stop_percentile,
        manual_stopwords=list(args.manual_stopwords),
        score_jaccard=args.score_jaccard,
        output_csv=args.output,
        print_report=not args.no_report,
        log_level=args.log_level,
        run_global_correction=args.global_correction,
        gc_word_list_path=args.gc_word_list,
        gc_min_freq_std=args.gc_min_freq_std,
        gc_min_len_std=args.gc_min_len_std,
        gc_max_freq_err=args.gc_max_freq_err,
    )

    blocker = RecursiveMinHashBlocker(cfg)
    t0 = time.perf_counter()
    blocker.fit(df)
    runtime = time.perf_counter() - t0

    metrics = compute_metrics(
        blocker.blocks,
        total_records=len(df),
        runtime_seconds=runtime,
        max_depth_reached=blocker.max_depth_reached,
    )
    print_metrics(metrics)
    if cfg.print_report:
        blocker.print_report()
    if cfg.output_csv:
        blocker.export_csv(cfg.output_csv)
        print(f"\nBlock-record rows written to {cfg.output_csv}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
