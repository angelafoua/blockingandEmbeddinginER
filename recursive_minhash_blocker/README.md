# Recursive MinHash Blocker

A Python implementation of a recursive blocking algorithm for scalable
**entity resolution**. Records are bucketed by MinHash signatures of cleaned,
normalized tokens; blocks are then **subdivided recursively**, each level
choosing a *different* blocking key (banning ancestors), until no useful
signature remains, the block is small enough, or the maximum depth is hit.

## Layout

```
recursive_minhash_blocker/
├── __init__.py
├── config.py           # BlockerConfig dataclass + abbreviation map
├── preprocess.py       # tokenization, cleaning, q-grams
├── minhash_utils.py    # deterministic MinHash, signature → block-key
├── blocking.py         # RecursiveMinHashBlocker (the main class)
├── metrics.py          # post-run statistics
├── main.py             # CLI + sample dataset generator
├── requirements.txt
└── tests/
    └── test_blocker.py # unittest suite
```

## Algorithm in plain English

1. **Tokenize** each record by concatenating the configured columns,
   lowercasing, and splitting on non-word boundaries.
2. **Standardize** each token via an editable abbreviation map (`st → street`,
   `co → company`, …).
3. **q-gram** every token (default `q=2`) and **MinHash** the q-gram set into a
   deterministic signature; collapse the signature to a short block-key string
   (`MH_<blake2b64>`).
4. **Frequencies** are tallied globally, counting one occurrence per record per
   signature (so word repetition inside a row never inflates a key’s frequency).
5. **Stop signatures** are dropped *globally* — top *X%* by frequency plus an
   optional manual list. No local stop-word lists are ever computed.
6. A signature is a **valid blocking key** when `alpha ≤ freq ≤ beta`.
7. Records are grouped by the rarest valid keys (multi-membership allowed).
8. **Recursion**: each block recomputes frequencies *over its own members*,
   picks a new valid key not used by any ancestor on that branch, and splits.
9. Stops when no key is valid, `size ≤ min_block_size`, or `depth = max_depth`.

## Quick start

```bash
pip install -r recursive_minhash_blocker/requirements.txt

# Generate a synthetic dataset:
python -m recursive_minhash_blocker.main --generate-sample sample.csv --rows 500

# Run blocking:
python -m recursive_minhash_blocker.main \
    --input sample.csv \
    --columns Name Address \
    --alpha 2 --beta 200 --q 2 --num_perm 64 \
    --max_depth 4 --min_block_size 2 \
    --score-jaccard \
    --output blocks.csv
```

## Programmatic use

```python
import pandas as pd
from recursive_minhash_blocker import RecursiveMinHashBlocker, BlockerConfig

df = pd.read_csv("mydata.csv")
cfg = BlockerConfig(
    id_column="RecID",
    blocking_columns=["Name", "Address"],
    alpha=2, beta=500, q=2, num_perm=64,
    max_depth=4, min_block_size=2,
    score_jaccard=True,
)
blocker = RecursiveMinHashBlocker(cfg).fit(df)

for b in blocker.blocks:
    print(b.block_id, b.depth, b.blocking_key, b.size, b.member_record_ids)

blocker.export_csv("blocks.csv")
```

## CLI flags

| Flag | Default | Meaning |
|------|---------|---------|
| `--input` | required | CSV path. |
| `--columns` | `Name Address` | Columns to concatenate for tokenization. |
| `--id-column` | `RecID` | Unique-id column name. |
| `--alpha` | `2` | Min frequency for a useful blocking signature. |
| `--beta` | `1000` | Max frequency for a useful blocking signature. |
| `--q` | `2` | Q-gram length. |
| `--num_perm` | `64` | MinHash permutations. |
| `--max_depth` | `5` | Recursion ceiling. |
| `--min_block_size` | `2` | Stop subdividing at this size. |
| `--max_keys_per_level` | `3` | How many candidate keys to spawn per level (recall ↔ pairs). |
| `--auto-stop-percentile` | `0.005` | Top-X fraction of signatures to drop globally. |
| `--manual-stopwords` | `[]` | Tokens to forcibly treat as stop words. |
| `--score-jaccard` | off | Pairwise Jaccard on token sets within each final block. |
| `--output` | – | Long-form CSV destination (`block_id,depth,parent_block,blocking_key,RecID,…`). |
| `--generate-sample PATH` | – | Write a synthetic CSV and exit. |

## Tests

```bash
python -m unittest discover -s recursive_minhash_blocker/tests -v
```

Covers q-gram generation, normalization, MinHash determinism, block
construction with planted duplicates, used-key history enforcement, Jaccard
scoring, and CSV export.

## Architecture notes

* **Separation of concerns** — preprocessing, hashing, blocking, and metrics
  live in distinct modules; each is independently importable and testable.
* **Caching** — q-gram lists and MinHash signatures are computed *once per
  unique token*, so repeated tokens (the common case) are nearly free.
* **Deterministic hashing** — `MinHasher` uses `datasketch` with a fixed seed
  *and* a SHA1-derived hash function, so signatures don’t depend on
  `PYTHONHASHSEED`.
* **Multi-membership blocking** — a record can land in several candidate
  blocks per recursion level (recall ↑) controlled by `max_keys_per_level`.
* **Used-key history** — every block carries an immutable
  `frozenset[str]` of ancestor blocking keys, so reuse is structurally
  impossible and infinite recursion can’t happen.

## Scaling to millions of rows

The current implementation is single-process and pandas-backed, sufficient for
hundreds of thousands of rows. To go bigger:

1. **Vectorize token cleanup** with `pd.Series.str` accessors / Polars instead
   of per-row `iterrows`.
2. **Precompute & persist** the `token → (signature, block_key)` cache
   (Parquet or LMDB) so re-runs and incremental ingests skip rehashing.
3. **Switch to LSH** (`datasketch.MinHashLSH` or banding by `r×b`) for
   producing candidate pairs *inside* large blocks — currently we group on a
   single signature per level, which is fine for blocking but less for fine
   matching.
4. **Distribute the recursion** with Spark / Dask: each top-level block is
   embarrassingly parallel because its used-key history is self-contained.
5. **Approximate frequencies** with Count-Min Sketch when the dataset is too
   big to hold full counters in memory.
6. **Stream the output CSV** (one block at a time) instead of materializing
   `self.blocks` in memory; the recursion is already DFS so this is a
   one-line change.
7. **Plug in embeddings** at the leaf level — the placeholder
   `minhash_utils.embed_tokens` is the intended hook for sentence-transformers
   or fastText to refine within-block matches.

## Future / extra features

* `BlockerConfig.score_jaccard` — pairwise Jaccard on token sets per block.
* `minhash_utils.embed_tokens` — placeholder for vector-embedding similarity.
