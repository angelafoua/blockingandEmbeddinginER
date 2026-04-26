"""
Phase 1: Hashing Keys for Token Variations

Three sub-steps, each in its own file and runnable individually:

  1. phase_1_step_1.py - merge variation sets into disjoint groups
  2. phase_1_step_2.py - assign one hash key per group
  3. phase_1_step_3.py - convert each record's tokens to its hash-key set

This module orchestrates all three. ``run_phase_1`` is consumed by
``recursive_lsh.run_pipeline``. Run this module directly to execute
the whole phase end-to-end:

    python phase_1.py [input.csv]
"""

import argparse
import os
import sys

import build_refDict
from phase_0 import run_phase_0
from phase_1_step_1 import build_groups
from phase_1_step_2 import assign_hash_keys
from phase_1_step_3 import records_to_hash_keys


def build_token_hash_mapping(variations_dict, key_prefix="HASH"):
    """Compose Steps 1 + 2: groups -> (token_hash_mapping, hash_to_tokens)."""
    groups = build_groups(variations_dict)
    return assign_hash_keys(groups, key_prefix=key_prefix)


def run_phase_1(refDict, variations_dict, key_prefix="HASH"):
    """Execute Phase 1 end-to-end."""
    token_hash_mapping, hash_to_tokens = build_token_hash_mapping(
        variations_dict, key_prefix=key_prefix
    )
    hash_key_records = records_to_hash_keys(refDict, token_hash_mapping)

    print(f"[Phase 1] {len(hash_to_tokens)} hash keys created from "
          f"{len(token_hash_mapping)} tokens")

    return token_hash_mapping, hash_to_tokens, hash_key_records


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Run all three Phase 1 sub-steps end-to-end."
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

    token_hash_mapping, hash_to_tokens, hash_key_records = run_phase_1(
        cleaned, variations, key_prefix=args.key_prefix
    )
    print(f"\nPhase 1 complete:")
    print(f"  hash keys:           {len(hash_to_tokens)}")
    print(f"  tokens mapped:       {len(token_hash_mapping)}")
    print(f"  records fingerprinted: {len(hash_key_records)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
