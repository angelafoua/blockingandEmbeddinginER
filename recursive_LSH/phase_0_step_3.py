"""
Phase 0 - Step 3: Generate Token Variations

For every remaining unique token, build a set of "equivalent" spellings.
Four methods are supported:

  - data_quality : realistic corruptions from data_quality_generator,
                   intersected with actual tokens in the dataset.
  - fuzzy        : Levenshtein-based similarity threshold.
  - phonetic     : tokens sharing a Soundex code.
  - manual       : caller-provided {token: [variations]} mapping.

Run as a script to inspect the resulting variation groups:

    python phase_0_step_3.py [input.csv] --method fuzzy
"""

import argparse
import os
import random
import sys
from time import perf_counter

import build_refDict
from phase_0_step_1 import count_token_frequencies
from phase_0_step_2 import remove_high_frequency_tokens


def _edit_distance(a, b):
    """Iterative Levenshtein distance (no external deps)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[-1]


def _similarity_ratio(a, b):
    """Normalised similarity in [0, 100], 100 = identical."""
    if not a and not b:
        return 100
    return int(round(100 * (1 - _edit_distance(a, b) / max(len(a), len(b)))))


def _soundex(token):
    """Classic 4-char Soundex code."""
    if not token:
        return ""
    token = token.upper()
    mapping = {
        **dict.fromkeys("BFPV", "1"),
        **dict.fromkeys("CGJKQSXZ", "2"),
        **dict.fromkeys("DT", "3"),
        **dict.fromkeys("L", "4"),
        **dict.fromkeys("MN", "5"),
        **dict.fromkeys("R", "6"),
    }
    first = token[0]
    encoded = [first]
    prev_code = mapping.get(first, "")
    for ch in token[1:]:
        code = mapping.get(ch, "")
        if code and code != prev_code:
            encoded.append(code)
        if ch not in "HW":
            prev_code = code
    return (encoded[0] + "".join(encoded[1:]) + "000")[:4]


def _fuzzy_variations(unique_tokens, similarity_threshold):
    """Group tokens whose pairwise similarity meets the threshold."""
    tokens = sorted(unique_tokens)
    variations = {t: {t} for t in tokens}

    by_first = {}
    for t in tokens:
        by_first.setdefault(t[0] if t else "", []).append(t)

    for t in tokens:
        bucket = by_first.get(t[0] if t else "", [])
        for other in bucket:
            if other == t:
                continue
            if abs(len(other) - len(t)) > 2:
                continue
            if _similarity_ratio(t, other) >= similarity_threshold:
                variations[t].add(other)
    return variations


def _phonetic_variations(unique_tokens):
    """Group tokens that share a Soundex code."""
    by_code = {}
    for t in unique_tokens:
        by_code.setdefault(_soundex(t), set()).add(t)
    return {t: set(by_code[_soundex(t)]) for t in unique_tokens}


def _manual_variations(unique_tokens, manual_map):
    """Use a caller-provided {token: [variations]} mapping; default to identity."""
    variations = {}
    for t in unique_tokens:
        if t in manual_map:
            variations[t] = set(manual_map[t]) | {t}
        else:
            variations[t] = {t}
    return variations


def _data_quality_variations(unique_tokens, seed=42):
    """Group tokens via data_quality_generator, keeping only intersections
    with actual tokens in the dataset."""
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    try:
        from data_quality_generator import generate_all_variations
    except ImportError as e:
        raise ImportError(
            "data_quality_generator.py not found. Expected at "
            f"{os.path.join(parent_dir, 'data_quality_generator.py')}"
        ) from e

    lower_to_tokens = {}
    for t in unique_tokens:
        lower_to_tokens.setdefault(t.lower(), set()).add(t)

    variations = {t: {t} for t in unique_tokens}

    for t in unique_tokens:
        random.seed((seed * 1103515245 + hash(t.lower())) & 0xFFFFFFFF)
        result = generate_all_variations(t.lower())
        generated = result.get(t.lower(), set())

        for variant in generated:
            if not variant or variant == t.lower():
                continue
            matched = lower_to_tokens.get(variant)
            if not matched:
                continue
            for other in matched:
                if other != t:
                    variations[t].add(other)
                    variations[other].add(t)

    return variations


def generate_variations(refDict, method="data_quality", similarity_threshold=85,
                        manual_map=None, seed=42):
    """Build {token: set(variations)} for every unique token in ``refDict``.

    method in {'data_quality', 'fuzzy', 'phonetic', 'manual'}
    """
    unique_tokens = {t for tokens in refDict.values() for t in tokens}

    if method == "data_quality":
        return _data_quality_variations(unique_tokens, seed=seed)
    if method == "fuzzy":
        return _fuzzy_variations(unique_tokens, similarity_threshold)
    if method == "phonetic":
        return _phonetic_variations(unique_tokens)
    if method == "manual":
        return _manual_variations(unique_tokens, manual_map or {})

    raise ValueError(f"Unknown variation method: {method}")


def _print_summary(variations_dict, method, sample_n=10):
    print(f"\n=== Phase 0 - Step 3: Token Variation Groups (method={method}) ===")
    print(f"Unique tokens:             {len(variations_dict)}")

    sizes = [len(v) for v in variations_dict.values()]
    nontrivial = [s for s in sizes if s > 1]
    print(f"Tokens with >=1 variation: {len(nontrivial)}")

    if nontrivial:
        print(f"Avg group size (non-trivial): "
              f"{sum(nontrivial) / len(nontrivial):.2f}")
        print(f"Max group size:               {max(sizes)}")

    ranked = sorted(variations_dict.items(),
                    key=lambda kv: (-len(kv[1]), kv[0]))
    print(f"\nLargest {sample_n} variation groups:")
    shown = 0
    for token, variants in ranked:
        if len(variants) <= 1:
            break
        sample = ", ".join(sorted(variants)[:8])
        more = f" (+{len(variants) - 8} more)" if len(variants) > 8 else ""
        print(f"  [{len(variants):>3}]  {token}: {sample}{more}")
        shown += 1
        if shown >= sample_n:
            break
    if shown == 0:
        print("  (no token has any variations)")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Phase 0 - Step 3: generate token variations."
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

    tokenFreqDict = count_token_frequencies(refDict)
    cleaned, noisy = remove_high_frequency_tokens(
        refDict, tokenFreqDict, max_frequency=args.max_frequency
    )
    print(f"After filtering: {len(tokenFreqDict) - len(noisy)} tokens kept "
          f"(removed {len(noisy)} above freq {args.max_frequency})")

    t0 = perf_counter()
    variations_dict = generate_variations(
        cleaned,
        method=args.method,
        similarity_threshold=args.similarity_threshold,
        seed=args.seed,
    )
    elapsed = perf_counter() - t0
    print(f"Generated variations in {elapsed:.3f}s")

    _print_summary(variations_dict, args.method, sample_n=args.sample_n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
