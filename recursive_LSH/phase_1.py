"""
Phase 1: Signature-Based Token Mapping

Three sub-steps, each in its own file and runnable individually:

  1. phase_1_step_1.py - assign signature to each variation set
  2. phase_1_step_2.py - build token -> signatures reverse map
  3. phase_1_step_3.py - build record -> flattened signatures

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
from phase_1_step_1 import assign_signatures_to_sets
from phase_1_step_2 import build_token_to_signatures
from phase_1_step_3 import build_record_signatures


def run_phase_1(refDict, variations_dict):
    """
    Execute Phase 1 end-to-end using the signature-based approach.

    Returns:
      - token_to_signatures: {token: tuple(signatures it appears in)}
      - sig_to_tokens: {signature: tuple(tokens in that variation set)}
      - hash_key_records: {refID: tuple(flattened signatures)}
    """
    sig_to_tokens = assign_signatures_to_sets(variations_dict)
    token_to_signatures = build_token_to_signatures(variations_dict, sig_to_tokens)
    hash_key_records = build_record_signatures(refDict, token_to_signatures)

    total_sigs = len(sig_to_tokens)
    print(f"[Phase 1] {total_sigs} signatures created from variation sets; "
          f"{len(token_to_signatures)} tokens mapped")

    return token_to_signatures, sig_to_tokens, hash_key_records


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

    token_to_sigs, sig_to_tokens, hash_key_records = run_phase_1(
        cleaned, variations
    )
    print(f"\nPhase 1 complete:")
    print(f"  signatures:           {len(sig_to_tokens)}")
    print(f"  tokens mapped:        {len(token_to_sigs)}")
    print(f"  records fingerprinted: {len(hash_key_records)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
