"""
Phase 1 - Step 2: Build Reverse Map (Token -> Signatures)

For each token that appears as a KEY in variations_dict, find all the
signatures (from Step 1) that contain it. A token can appear in multiple
signatures if it's part of multiple variation sets.

Run as a script to inspect token-to-signature mappings:

    python phase_1_step_2.py [input.csv] --method fuzzy
"""

import argparse
import os
import sys
from collections import Counter

import build_refDict
from phase_0 import run_phase_0
from phase_1_step_1 import assign_signatures_to_sets


def build_token_to_signatures(variations_dict, sig_to_tokens):
    """
    For each token that is a KEY in variations_dict, find all signatures
    it appears in (across all variation sets). Returns a dict mapping
    token -> tuple of signatures (sorted for determinism).
    """
    # Build reverse map: token -> set of signatures
    token_to_sigs = {}

    for sig, tokens in sig_to_tokens.items():
        for token in tokens:
            if token not in token_to_sigs:
                token_to_sigs[token] = set()
            token_to_sigs[token].add(sig)

    # Only keep tokens that were KEYS in variations_dict
    # (these are the actual tokens in the dataset)
    refined_sigs = {}
    for token in variations_dict.keys():
        if token in token_to_sigs:
            refined_sigs[token] = tuple(sorted(token_to_sigs[token]))

    return refined_sigs


def _print_summary(refined_sigs, sample_n=10):
    print("\n=== Phase 1 - Step 2: Token -> Signature Mapping ===")
    print(f"Unique tokens (with signatures): {len(refined_sigs)}")
    if not refined_sigs:
        return

    sig_counts = [len(v) for v in refined_sigs.values()]
    print(f"Avg signatures per token:   {sum(sig_counts) / len(sig_counts):.2f}")
    print(f"Max signatures per token:   {max(sig_counts)}")
    print(f"Min signatures per token:   {min(sig_counts)}")

    bins = Counter(sig_counts)
    max_count = max(bins)
    print("\nSignatures-per-token distribution:")
    for count in sorted(bins):
        if count <= 10 or count % 5 == 0 or count == max_count:
            print(f"  sigs={count:<4} -> {bins[count]} tokens")

    ranked = sorted(refined_sigs.items(),
                    key=lambda kv: -len(kv[1]))
    print(f"\nTokens appearing in most signatures (top {sample_n}):")
    for token, sigs in ranked[:sample_n]:
        if len(sigs) <= 1:
            break
        sample = ", ".join(sigs[:6])
        more = f" (+{len(sigs) - 6} more)" if len(sigs) > 6 else ""
        print(f"  [{len(sigs):>3} sigs]  {token}: {sample}{more}")

    print(f"\nFirst {sample_n} token -> signatures entries:")
    for token, sigs in list(refined_sigs.items())[:sample_n]:
        print(f"  {token!r}: {sigs}")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Phase 1 - Step 2: build token -> signatures map."
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
    print(f"Step 1 assigned {len(sig_to_tokens)} signatures to variation sets")

    refined_sigs = build_token_to_signatures(variations, sig_to_tokens)
    _print_summary(refined_sigs, sample_n=args.sample_n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
