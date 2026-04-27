"""
Phase 1 - Step 3: Build Record Signatures

For each record, look up the signatures of each token (from Step 2),
and flatten them into a single sorted tuple. This is the record's
signature fingerprint for blocking.

Run as a script to inspect record signatures:

    python phase_1_step_3.py [input.csv] --method fuzzy
"""

import argparse
import os
import sys
from collections import Counter

import build_refDict
from phase_0 import run_phase_0
from phase_1_step_1 import assign_signatures_to_sets
from phase_1_step_2 import build_token_to_signatures


def build_record_signatures(refDict, refined_sigs):
    """
    For each record, look up its tokens' signatures and flatten into a
    single sorted tuple. Tokens not in refined_sigs are skipped.

    Returns: {refID: tuple(sorted signatures)}
    """
    hash_key_records = {}
    for refID, tokens in refDict.items():
        # Collect all signatures from all tokens
        all_sigs = set()
        for token in tokens:
            if token in refined_sigs:
                all_sigs.update(refined_sigs[token])
        # Store as sorted tuple for determinism
        hash_key_records[refID] = tuple(sorted(all_sigs))
    return hash_key_records


def _print_summary(hash_key_records, sample_n=10):
    print("\n=== Phase 1 - Step 3: Record Signatures ===")
    print(f"Records: {len(hash_key_records)}")
    if not hash_key_records:
        return

    sig_counts = [len(v) for v in hash_key_records.values()]
    empty = sum(1 for s in sig_counts if s == 0)
    print(f"Records with zero signatures:   {empty}")
    print(f"Records with >=1 signature:    {len(hash_key_records) - empty}")
    if any(sig_counts):
        non_empty = [s for s in sig_counts if s > 0]
        print(f"Avg signatures / record (non-empty): {sum(non_empty) / len(non_empty):.2f}")
        print(f"Max signatures in a record:          {max(sig_counts)}")

    bins = Counter(sig_counts)
    max_count = max(bins)
    print("\nSignatures-per-record distribution:")
    for count in sorted(bins):
        if count <= 15 or count % 5 == 0 or count == max_count:
            print(f"  sigs={count:<4} -> {bins[count]} records")

    print(f"\nFirst {sample_n} records (refID -> signatures):")
    for refID, sigs in list(hash_key_records.items())[:sample_n]:
        if len(sigs) > 8:
            shown = ", ".join(sigs[:8]) + f" (+{len(sigs) - 8} more)"
        else:
            shown = ", ".join(sigs) if sigs else "(no signatures)"
        print(f"  {refID}: {shown}")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Phase 1 - Step 3: build record signatures."
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

    cleaned, _, variations = run_phase_0(
        refDict, max_frequency=args.max_frequency,
        method=args.method,
        similarity_threshold=args.similarity_threshold,
        seed=args.seed,
    )

    sig_to_tokens = assign_signatures_to_sets(variations)
    print(f"Step 1 assigned {len(sig_to_tokens)} signatures")

    refined_sigs = build_token_to_signatures(variations, sig_to_tokens)
    print(f"Step 2 mapped {len(refined_sigs)} tokens to their signatures")

    hash_key_records = build_record_signatures(cleaned, refined_sigs)
    _print_summary(hash_key_records, sample_n=args.sample_n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
