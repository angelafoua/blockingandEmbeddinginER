"""
Phase 1 - Step 1: Assign Signature to Each Variation Set

For each token that is a KEY in variations_dict, compute a deterministic
signature for its variation set. Each variation set gets exactly one signature.

Run as a script to inspect the signature assignments:

    python phase_1_step_1.py [input.csv] --method fuzzy
"""

import argparse
import os
import sys
from collections import Counter

import build_refDict
from phase_0 import run_phase_0


def assign_signatures_to_sets(variations_dict, sig_prefix="VSIG"):
    """
    For each key (token) in variations_dict, assign a signature to its
    variation set. Returns signature -> frozenset of tokens in that set.

    Note: Multiple keys may map to the same variation set (if their sets
    are identical), so we use frozenset to deduplicate.
    """
    set_to_sig = {}
    sig_to_tokens = {}
    sig_counter = 1

    for token, variant_set in variations_dict.items():
        # The variation set includes the token itself
        variation_set = frozenset(variant_set | {token})

        # If we've seen this exact set before, reuse its signature
        if variation_set not in set_to_sig:
            sig = f"{sig_prefix}_{sig_counter:05d}"
            set_to_sig[variation_set] = sig
            sig_to_tokens[sig] = tuple(sorted(variation_set))
            sig_counter += 1

    return sig_to_tokens


def _print_summary(sig_to_tokens, sample_n=10):
    print("\n=== Phase 1 - Step 1: Variation Set Signatures ===")
    print(f"Unique variation sets: {len(sig_to_tokens)}")
    if not sig_to_tokens:
        return

    sizes = [len(v) for v in sig_to_tokens.values()]
    print(f"Avg tokens per set:    {sum(sizes) / len(sizes):.2f}")
    print(f"Max tokens in a set:   {max(sizes)}")
    print(f"Min tokens in a set:   {min(sizes)}")

    bins = Counter(sizes)
    max_size = max(bins)
    print("\nTokens-per-set distribution:")
    for size in sorted(bins):
        if size <= 10 or size % 5 == 0 or size == max_size:
            print(f"  size={size:<4} -> {bins[size]} sets")

    ranked = sorted(sig_to_tokens.items(),
                    key=lambda kv: -len(kv[1]))
    print(f"\nLargest {sample_n} variation sets (sig -> sample tokens):")
    for sig, toks in ranked[:sample_n]:
        sample = ", ".join(toks[:8])
        more = f" (+{len(toks) - 8} more)" if len(toks) > 8 else ""
        print(f"  [{len(toks):>4}]  {sig}: {sample}{more}")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Phase 1 - Step 1: assign signatures to variation sets."
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

    sig_to_tokens = assign_signatures_to_sets(variations)
    _print_summary(sig_to_tokens, sample_n=args.sample_n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
