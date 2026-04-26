"""
Phase 1 - Step 2: Assign Hash Keys to Variation Groups

For each disjoint group from Step 1, mint one deterministic hash key
(``HASH_00001``, ``HASH_00002``, ...). Every token in the group is
mapped to that key, so all variants of one concept share a key.

Returns:
  - token_hash_mapping : {token: hash_key}
  - hash_to_tokens     : {hash_key: set(tokens)}

Run as a script to inspect the mappings:

    python phase_1_step_2.py [input.csv] --method fuzzy
"""

import argparse
import os
import sys
from collections import Counter

import build_refDict
from phase_0 import run_phase_0
from phase_1_step_1 import build_groups


def assign_hash_keys(groups, key_prefix="HASH"):
    """Mint a unique hash key per group; return forward + reverse maps."""
    groups_sorted = sorted(groups, key=lambda g: sorted(g)[0])

    token_hash_mapping = {}
    hash_to_tokens = {}

    for idx, group in enumerate(groups_sorted, start=1):
        hash_key = f"{key_prefix}_{idx:05d}"
        hash_to_tokens[hash_key] = set(group)
        for token in group:
            token_hash_mapping[token] = hash_key

    return token_hash_mapping, hash_to_tokens


def _print_summary(token_hash_mapping, hash_to_tokens, sample_n=10):
    print("\n=== Phase 1 - Step 2: Token -> Hash Key Mapping ===")
    print(f"Hash keys minted:  {len(hash_to_tokens)}")
    print(f"Tokens mapped:     {len(token_hash_mapping)}")
    if not hash_to_tokens:
        return

    sizes = [len(v) for v in hash_to_tokens.values()]
    singletons = sum(1 for s in sizes if s == 1)
    multi = sum(1 for s in sizes if s > 1)
    print(f"Singleton keys (1 token):  {singletons}")
    print(f"Multi-token keys (>=2):   {multi}")
    print(f"Max tokens per key:        {max(sizes)}")

    bins = Counter(sizes)
    max_size = max(bins)
    print("\nTokens-per-key distribution:")
    for size in sorted(bins):
        if size <= 10 or size % 5 == 0 or size == max_size:
            print(f"  size={size:<5} -> {bins[size]} keys")

    ranked = sorted(hash_to_tokens.items(),
                    key=lambda kv: -len(kv[1]))
    print(f"\nLargest {sample_n} hash keys (key -> sample tokens):")
    for hkey, toks in ranked[:sample_n]:
        if len(toks) <= 1:
            break
        sample = ", ".join(sorted(toks)[:8])
        more = f" (+{len(toks) - 8} more)" if len(toks) > 8 else ""
        print(f"  [{len(toks):>4}]  {hkey}: {sample}{more}")

    print(f"\nFirst {sample_n} token -> hash_key entries:")
    for token, hkey in list(token_hash_mapping.items())[:sample_n]:
        print(f"  {token!r} -> {hkey}")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Phase 1 - Step 2: assign hash keys to variation groups."
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
    print(f"Step 1 produced {len(groups)} disjoint variation groups")

    token_hash_mapping, hash_to_tokens = assign_hash_keys(
        groups, key_prefix=args.key_prefix
    )
    _print_summary(token_hash_mapping, hash_to_tokens, sample_n=args.sample_n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
