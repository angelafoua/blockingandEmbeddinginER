"""
Phase 1 - Step 3: Convert Records to Hash-Key Sets

Translate every record's tokens into the sorted tuple of hash keys
they map to (using ``token_hash_mapping`` from Step 2). This produces
the per-record "fingerprint" that Phase 2 uses for blocking.

Run as a script to inspect record fingerprints:

    python phase_1_step_3.py [input.csv] --method fuzzy
"""

import argparse
import os
import sys
from collections import Counter

import build_refDict
from phase_0 import run_phase_0
from phase_1_step_1 import build_groups
from phase_1_step_2 import assign_hash_keys


def records_to_hash_keys(refDict, token_hash_mapping):
    """Convert each record's tokens into a sorted tuple of hash keys."""
    hash_key_records = {}
    for refID, tokens in refDict.items():
        keys = {token_hash_mapping[t] for t in tokens if t in token_hash_mapping}
        hash_key_records[refID] = tuple(sorted(keys))
    return hash_key_records


def _print_summary(hash_key_records, sample_n=10):
    print("\n=== Phase 1 - Step 3: Record -> Hash-Key Sets ===")
    print(f"Records: {len(hash_key_records)}")
    if not hash_key_records:
        return

    sizes = [len(v) for v in hash_key_records.values()]
    empty = sum(1 for s in sizes if s == 0)
    print(f"Records with zero hash keys:   {empty}")
    print(f"Records with >=1 hash key:    {len(hash_key_records) - empty}")
    if any(sizes):
        non_empty = [s for s in sizes if s > 0]
        print(f"Avg keys / record (non-empty): {sum(non_empty) / len(non_empty):.2f}")
        print(f"Max keys in a record:          {max(sizes)}")

    bins = Counter(sizes)
    max_size = max(bins)
    print("\nKeys-per-record distribution:")
    for size in sorted(bins):
        if size <= 15 or size % 5 == 0 or size == max_size:
            print(f"  keys={size:<4} -> {bins[size]} records")

    print(f"\nFirst {sample_n} records (refID -> hash keys):")
    for refID, keys in list(hash_key_records.items())[:sample_n]:
        if len(keys) > 8:
            shown = ", ".join(keys[:8]) + f" (+{len(keys) - 8} more)"
        else:
            shown = ", ".join(keys) if keys else "(no keys)"
        print(f"  {refID}: {shown}")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Phase 1 - Step 3: convert records to hash-key sets."
    )
    parser.add_argument("input", nargs="?", default=default_input)
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--max-frequency", type=int, default=6)
    parser.add_argument("--method",
                        choices=["data_quality", "fuzzy", "phonetic", "manual"],
                        default="fuzzy")
    parser.add_argument("--similarity-threshold", type=int, default=85)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--key-prefix", default="HASH")
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

    groups = build_groups(variations)
    token_hash_mapping, _ = assign_hash_keys(groups, key_prefix=args.key_prefix)
    print(f"Step 2 minted {len(set(token_hash_mapping.values()))} hash keys "
          f"covering {len(token_hash_mapping)} tokens")

    hash_key_records = records_to_hash_keys(cleaned, token_hash_mapping)
    _print_summary(hash_key_records, sample_n=args.sample_n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
