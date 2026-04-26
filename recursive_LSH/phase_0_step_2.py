"""
Phase 0 - Step 2: Remove High-Frequency Tokens

Drop tokens whose document frequency exceeds ``max_frequency``. These
common tokens are stop-word-like noise that would inflate every block
and hurt discrimination during blocking.

Run as a script to see what got removed:

    python phase_0_step_2.py [input.csv] --max-frequency 6
"""

import argparse
import os
import sys

import build_refDict
from phase_0_step_1 import count_token_frequencies


def remove_high_frequency_tokens(refDict, tokenFreqDict, max_frequency=60):
    """Remove tokens whose document frequency exceeds ``max_frequency``."""
    noisy = {t for t, f in tokenFreqDict.items() if f > max_frequency}

    cleaned = {}
    for refID, tokens in refDict.items():
        cleaned[refID] = [t for t in tokens if t not in noisy]

    return cleaned, noisy


def _print_summary(refDict, cleaned, noisy, tokenFreqDict,
                   max_frequency, sample_n=20):
    print("\n=== Phase 0 - Step 2: Remove High-Frequency Tokens ===")
    print(f"Threshold (max_frequency): {max_frequency}")
    print(f"Tokens removed:            {len(noisy)}")
    print(f"Tokens kept:               {len(tokenFreqDict) - len(noisy)}")

    before_total = sum(len(t) for t in refDict.values())
    after_total = sum(len(t) for t in cleaned.values())
    print(f"Total token occurrences before: {before_total}")
    print(f"Total token occurrences after:  {after_total}")
    print(f"  removed: {before_total - after_total}")

    if refDict:
        print(f"Avg tokens/record before: "
              f"{before_total / len(refDict):.2f}")
        print(f"Avg tokens/record after:  "
              f"{after_total / len(cleaned):.2f}")

    empty = sum(1 for t in cleaned.values() if not t)
    if empty:
        print(f"Records with zero tokens after filtering: {empty}")

    if noisy:
        ranked = sorted(noisy, key=lambda t: -tokenFreqDict[t])
        print(f"\nTop {sample_n} removed tokens (by freq):")
        for token in ranked[:sample_n]:
            print(f"  {tokenFreqDict[token]:>6}  {token}")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Phase 0 - Step 2: remove high-frequency tokens."
    )
    parser.add_argument("input", nargs="?", default=default_input)
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--max-frequency", type=int, default=6)
    parser.add_argument("--sample-n", type=int, default=20)
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    if not os.path.isfile(args.input):
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    refDict = build_refDict.tokenizeInput(args.input, delimiter=args.delimiter)
    print(f"Loaded {len(refDict)} records from {args.input}")

    tokenFreqDict = count_token_frequencies(refDict)
    print(f"Counted frequencies for {len(tokenFreqDict)} unique tokens")

    cleaned, noisy = remove_high_frequency_tokens(
        refDict, tokenFreqDict, max_frequency=args.max_frequency
    )
    _print_summary(refDict, cleaned, noisy, tokenFreqDict,
                   args.max_frequency, sample_n=args.sample_n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
