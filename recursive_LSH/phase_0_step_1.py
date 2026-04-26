"""
Phase 0 - Step 1: Token Frequency Counting

Count document frequencies for every token across all records. A token's
frequency is the number of distinct records that contain it (each record
counted at most once even if the token appears multiple times in it).

Run as a script to inspect frequency stats:

    python phase_0_step_1.py [input.csv]
"""

import argparse
import os
import sys
from collections import Counter

import build_refDict


def count_token_frequencies(refDict):
    """Return a {token: frequency} mapping over all records."""
    counter = Counter()
    for tokens in refDict.values():
        counter.update(set(tokens))
    return dict(counter)


def _print_summary(tokenFreqDict, top_n=20):
    print("\n=== Phase 0 - Step 1: Token Frequencies ===")
    if not tokenFreqDict:
        print("No tokens.")
        return

    items = sorted(tokenFreqDict.items(), key=lambda kv: -kv[1])
    print(f"Unique tokens:       {len(tokenFreqDict)}")
    print(f"Total occurrences:   {sum(tokenFreqDict.values())}")
    print(f"Max document freq:   {items[0][1]}")
    print(f"Min document freq:   {items[-1][1]}")

    print(f"\nTop {top_n} most frequent tokens:")
    for token, freq in items[:top_n]:
        print(f"  {freq:>6}  {token}")

    bins = Counter(tokenFreqDict.values())
    max_freq = max(bins)
    print("\nFrequency distribution (# tokens at each document frequency):")
    for freq in sorted(bins):
        if freq <= 10 or freq % 10 == 0 or freq == max_freq:
            print(f"  freq={freq:<5} -> {bins[freq]} tokens")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Phase 0 - Step 1: count token document frequencies."
    )
    parser.add_argument("input", nargs="?", default=default_input)
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--top-n", type=int, default=20)
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    if not os.path.isfile(args.input):
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    refDict = build_refDict.tokenizeInput(args.input, delimiter=args.delimiter)
    print(f"Loaded {len(refDict)} records from {args.input}")

    tokenFreqDict = count_token_frequencies(refDict)
    _print_summary(tokenFreqDict, top_n=args.top_n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
