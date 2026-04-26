"""
Phase 2 - Step 3: Generate Candidate Pairs

Enumerate all within-block record pairs across the initial blocks. This
is the list of pairs the downstream entity-resolution comparison stage
would need to evaluate in detail.

Run as a script to see candidate-pair statistics:

    python phase_2_step_3.py [input.csv]
"""

import argparse
import os
import sys
from itertools import combinations
from math import comb

import build_refDict
from phase_0 import run_phase_0
from phase_1 import run_phase_1
from phase_2_step_2 import form_initial_blocks


def candidate_pairs_from_blocks(blocks):
    """All within-block pairs across the supplied blocks."""
    pairs = set()
    for refIDs in blocks.values():
        if len(refIDs) < 2:
            continue
        for a, b in combinations(sorted(refIDs), 2):
            pairs.add((a, b))
    return sorted(pairs)


def _print_summary(pairs, blocks, n_records, sample_n=10):
    print("\n=== Phase 2 - Step 3: Candidate Pairs ===")
    print(f"Candidate pairs: {len(pairs)}")
    brute = comb(n_records, 2)
    if brute:
        ratio = 100 * (1 - len(pairs) / brute)
        print(f"Brute-force pairs: {brute} (C(N,2) for N={n_records})")
        print(f"Reduction:         {ratio:.4f}%")

    multi_blocks = [b for b in blocks.values() if len(b) >= 2]
    if multi_blocks:
        avg_per_block = len(pairs) / len(multi_blocks)
        print(f"Multi-record blocks:    {len(multi_blocks)}")
        print(f"Avg pairs per block:    {avg_per_block:.2f}")

    if pairs:
        print(f"\nFirst {sample_n} candidate pairs:")
        for a, b in pairs[:sample_n]:
            print(f"  ({a}, {b})")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Phase 2 - Step 3: enumerate candidate pairs."
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
    print(f"Initial blocks: {len(blocks)} (mode={mode})")

    pairs = candidate_pairs_from_blocks(blocks)
    _print_summary(pairs, blocks, n_records=len(refDict),
                   sample_n=args.sample_n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
