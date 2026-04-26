"""
Phase 0: Token Frequency Analysis & Data Quality Generation

Three sub-steps, each in its own file and runnable individually:

  1. phase_0_step_1.py - count token frequencies
  2. phase_0_step_2.py - remove high-frequency tokens
  3. phase_0_step_3.py - generate token variations

This module orchestrates all three. ``run_phase_0`` is consumed by
``recursive_lsh.run_pipeline``. Run this module directly to execute
the whole phase end-to-end:

    python phase_0.py [input.csv]
"""

import argparse
import os
import sys
from time import perf_counter

import build_refDict
from phase_0_step_1 import count_token_frequencies
from phase_0_step_2 import remove_high_frequency_tokens
from phase_0_step_3 import generate_variations


def run_phase_0(refDict, max_frequency=60, method="data_quality",
                similarity_threshold=85, manual_map=None, seed=42):
    """Execute Phase 0 end-to-end."""
    t0 = perf_counter()
    tokenFreqDict = count_token_frequencies(refDict)
    t_freq = perf_counter() - t0

    t0 = perf_counter()
    cleaned_refDict, removed = remove_high_frequency_tokens(
        refDict, tokenFreqDict, max_frequency=max_frequency
    )
    t_clean = perf_counter() - t0

    t0 = perf_counter()
    variations_dict = generate_variations(
        cleaned_refDict,
        method=method,
        similarity_threshold=similarity_threshold,
        manual_map=manual_map,
        seed=seed,
    )
    t_var = perf_counter() - t0

    print(f"[Phase 0] removed {len(removed)} high-frequency tokens "
          f"(threshold={max_frequency})")
    print(f"[Phase 0] generated variations for "
          f"{len(variations_dict)} unique tokens (method={method})")
    print(f"[Phase 0]   step timings: "
          f"count_freq={t_freq:.3f}s, "
          f"remove_high_freq={t_clean:.3f}s, "
          f"generate_variations={t_var:.3f}s")

    return cleaned_refDict, tokenFreqDict, variations_dict


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Run all three Phase 0 sub-steps end-to-end."
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

    cleaned, freq, variations = run_phase_0(
        refDict,
        max_frequency=args.max_frequency,
        method=args.method,
        similarity_threshold=args.similarity_threshold,
        seed=args.seed,
    )
    print(f"\nPhase 0 complete:")
    print(f"  cleaned records:        {len(cleaned)}")
    print(f"  unique tokens (freq):   {len(freq)}")
    print(f"  variation groups:       {len(variations)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
