"""
Phase 2 - Step 2: Form Initial Blocks

Group records that share the same hash-key set into blocks. Two modes:

  - exact : identical hash-key sets => same block (default).
  - lsh   : MinHash + LSH bucketing (requires datasketch). Catches
            records whose key-sets overlap but aren't identical.

Run as a script to see block statistics:

    python phase_2_step_2.py [input.csv]
    python phase_2_step_2.py [input.csv] --use-lsh
"""

import argparse
import os
import sys
from collections import defaultdict, Counter

import build_refDict
from phase_0 import run_phase_0
from phase_1 import run_phase_1


def blocks_by_full_key_set(hash_key_records):
    """Group records that share an *identical* hash-key set."""
    blocks = defaultdict(list)
    for refID, keys in hash_key_records.items():
        blocks[tuple(keys)].append(refID)
    return dict(blocks)


def _lsh_blocks(hash_key_records, num_perm, lsh_threshold):
    """LSH-bucketed blocks. Requires the ``datasketch`` package."""
    from datasketch import MinHash, MinHashLSH

    lsh = MinHashLSH(threshold=lsh_threshold, num_perm=num_perm)
    minhashes = {}

    for refID, keys in hash_key_records.items():
        if not keys:
            continue
        m = MinHash(num_perm=num_perm)
        for key in keys:
            m.update(key.encode("utf-8"))
        minhashes[refID] = m
        lsh.insert(str(refID), m)

    bucket_to_refs = defaultdict(set)
    for refID, m in minhashes.items():
        members = tuple(sorted(lsh.query(m)))
        bucket_to_refs[members].add(refID)

    return {k: sorted(v) for k, v in bucket_to_refs.items()}


def form_initial_blocks(hash_key_records, use_lsh=False,
                        num_perm=128, lsh_threshold=0.5):
    """Dispatch to exact or LSH bucketing. Returns (blocks, mode_str)."""
    if use_lsh:
        try:
            blocks = _lsh_blocks(hash_key_records, num_perm, lsh_threshold)
            return blocks, f"LSH (num_perm={num_perm}, threshold={lsh_threshold})"
        except ImportError:
            print("[Phase 2 - Step 2] datasketch not installed; "
                  "falling back to exact bucketing")
    return blocks_by_full_key_set(hash_key_records), "exact"


def _print_summary(blocks, mode, sample_n=10):
    print(f"\n=== Phase 2 - Step 2: Initial Blocks (mode={mode}) ===")
    print(f"Initial blocks: {len(blocks)}")
    if not blocks:
        return

    sizes = [len(v) for v in blocks.values()]
    singleton = sum(1 for s in sizes if s == 1)
    multi = sum(1 for s in sizes if s > 1)
    print(f"Singleton blocks (1 record):  {singleton}")
    print(f"Multi-record blocks (>=2):   {multi}")
    print(f"Max block size:               {max(sizes)}")
    if multi:
        avg_multi = sum(s for s in sizes if s > 1) / multi
        print(f"Avg size (multi-record):     {avg_multi:.2f}")

    bins = Counter(sizes)
    max_size = max(bins)
    print("\nBlock-size distribution (size -> # blocks):")
    for size in sorted(bins):
        if size <= 10 or size % 5 == 0 or size == max_size:
            print(f"  size={size:<5} -> {bins[size]} blocks")

    ranked = sorted(blocks.items(), key=lambda kv: -len(kv[1]))
    print(f"\nLargest {sample_n} blocks (key-set -> # records):")
    for key_set, ids in ranked[:sample_n]:
        if isinstance(key_set, tuple):
            label = " ".join(map(str, key_set[:5]))
            if len(key_set) > 5:
                label += f" (+{len(key_set) - 5})"
        else:
            label = str(key_set)
        sample = ", ".join(map(str, ids[:6]))
        more = f" (+{len(ids) - 6} more)" if len(ids) > 6 else ""
        print(f"  [{len(ids):>4}]  {label}: {sample}{more}")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Phase 2 - Step 2: form initial blocks."
    )
    parser.add_argument("input", nargs="?", default=default_input)
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--max-frequency", type=int, default=6)
    parser.add_argument("--method",
                        choices=["data_quality", "fuzzy", "phonetic", "manual"],
                        default="fuzzy")
    parser.add_argument("--similarity-threshold", type=int, default=85)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--use-lsh", action="store_true")
    parser.add_argument("--num-perm", type=int, default=128)
    parser.add_argument("--lsh-threshold", type=float, default=0.5)
    parser.add_argument("--sample-n", type=int, default=10)
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    if not os.path.isfile(args.input):
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    refDict = build_refDict.tokenizeInput(args.input, delimiter=args.delimiter)
    print(f"Loaded {len(refDict)} records from {args.input}")

    cleaned, _, variations = run_phase_0(
        refDict, max_frequency=args.max_frequency,
        method=args.method,
        similarity_threshold=args.similarity_threshold,
        seed=args.seed,
    )
    _, _, hash_key_records = run_phase_1(cleaned, variations)

    blocks, mode = form_initial_blocks(
        hash_key_records,
        use_lsh=args.use_lsh,
        num_perm=args.num_perm,
        lsh_threshold=args.lsh_threshold,
    )
    _print_summary(blocks, mode, sample_n=args.sample_n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
