"""
Phase 1 - Step 1: Merge Variation Sets into Disjoint Groups

Phase 0's ``variations_dict`` maps each token to a set of variants, but
those sets can overlap (e.g. A's variants include B, B's variants include
C). Step 1 uses union-find to merge any sets that share at least one
token, producing a list of disjoint groups. Every token in a group will
later receive the same hash key.

Run as a script to inspect the resulting groups:

    python phase_1_step_1.py [input.csv] --method fuzzy
"""

import argparse
import os
import sys
from collections import Counter

import build_refDict
from phase_0 import run_phase_0


def build_groups(variations_dict):
    """
    Merge variation sets that share at least one token (union-find).
    Returns a list of disjoint groups (sets of tokens).
    """
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for token, variants in variations_dict.items():
        for v in variants | {token}:
            parent.setdefault(v, v)
        canonical = token
        for v in variants:
            union(canonical, v)

    groups = {}
    for token in parent:
        root = find(token)
        groups.setdefault(root, set()).add(token)

    return list(groups.values())


def _print_summary(groups, sample_n=10):
    print("\n=== Phase 1 - Step 1: Disjoint Variation Groups ===")
    print(f"Groups: {len(groups)}")
    if not groups:
        return

    sizes = [len(g) for g in groups]
    singletons = sum(1 for s in sizes if s == 1)
    multi = sum(1 for s in sizes if s > 1)
    print(f"Singleton groups (1 token):  {singletons}")
    print(f"Multi-token groups (>=2):   {multi}")
    print(f"Max group size:              {max(sizes)}")
    if multi:
        avg_multi = sum(s for s in sizes if s > 1) / multi
        print(f"Avg size (multi-token):     {avg_multi:.2f}")

    bins = Counter(sizes)
    max_size = max(bins)
    print("\nGroup-size distribution (size -> # groups):")
    for size in sorted(bins):
        if size <= 10 or size % 5 == 0 or size == max_size:
            print(f"  size={size:<5} -> {bins[size]} groups")

    ranked = sorted(groups, key=lambda g: -len(g))
    print(f"\nLargest {sample_n} groups (size -> sample tokens):")
    for group in ranked[:sample_n]:
        if len(group) <= 1:
            break
        sample = ", ".join(sorted(group)[:8])
        more = f" (+{len(group) - 8} more)" if len(group) > 8 else ""
        print(f"  [{len(group):>4}]  {sample}{more}")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Phase 1 - Step 1: build disjoint variation groups."
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

    _, _, variations = run_phase_0(
        refDict, max_frequency=args.max_frequency,
        method=args.method,
        similarity_threshold=args.similarity_threshold,
        seed=args.seed,
    )

    groups = build_groups(variations)
    _print_summary(groups, sample_n=args.sample_n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
