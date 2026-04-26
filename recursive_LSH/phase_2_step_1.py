"""
Phase 2 - Step 1: Build Per-Key Buckets (Inverted Index)

For each hash key, list every record that contains it. This inverted
index is consumed by Phase 3 (recursive refinement needs to look up
records by individual key).

Run as a script to inspect bucket statistics:

    python phase_2_step_1.py [input.csv]
"""

import argparse
import os
import sys
from collections import defaultdict, Counter

import build_refDict
from phase_0 import run_phase_0
from phase_1 import run_phase_1


def blocks_by_individual_key(hash_key_records):
    """For each hash key, list the records that contain it."""
    blocks = defaultdict(list)
    for refID, keys in hash_key_records.items():
        for key in keys:
            blocks[key].append(refID)
    return dict(blocks)


def _print_summary(by_key, sample_n=10):
    print("\n=== Phase 2 - Step 1: Per-Key Buckets ===")
    print(f"Hash keys: {len(by_key)}")
    if not by_key:
        return

    sizes = [len(v) for v in by_key.values()]
    singleton = sum(1 for s in sizes if s == 1)
    multi = sum(1 for s in sizes if s > 1)
    print(f"Singleton keys (1 record):  {singleton}")
    print(f"Multi-record keys (>=2):   {multi}")
    print(f"Max bucket size:            {max(sizes)}")
    if multi:
        avg_multi = sum(s for s in sizes if s > 1) / multi
        print(f"Avg size (multi-record):    {avg_multi:.2f}")

    bins = Counter(sizes)
    max_size = max(bins)
    print("\nBucket-size distribution (size -> # buckets):")
    for size in sorted(bins):
        if size <= 10 or size % 5 == 0 or size == max_size:
            print(f"  size={size:<5} -> {bins[size]} buckets")

    ranked = sorted(by_key.items(), key=lambda kv: -len(kv[1]))
    print(f"\nLargest {sample_n} buckets (key -> # records, sample IDs):")
    for key, ids in ranked[:sample_n]:
        sample = ", ".join(map(str, ids[:6]))
        more = f" (+{len(ids) - 6} more)" if len(ids) > 6 else ""
        print(f"  [{len(ids):>4}]  {key}: {sample}{more}")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Phase 2 - Step 1: build per-key buckets."
    )
    parser.add_argument("input", nargs="?", default=default_input)
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--max-frequency", type=int, default=6)
    parser.add_argument("--method",
                        choices=["data_quality", "fuzzy", "phonetic", "manual"],
                        default="fuzzy")
    parser.add_argument("--similarity-threshold", type=int, default=85)
    parser.add_argument("--seed", type=int, default=42)
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

    by_key = blocks_by_individual_key(hash_key_records)
    _print_summary(by_key, sample_n=args.sample_n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
