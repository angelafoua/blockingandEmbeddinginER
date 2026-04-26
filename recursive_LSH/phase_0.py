"""
Phase 0: Token Frequency Analysis & Data Quality Generation

Steps:
  1. Count token frequencies across records.
  2. Remove tokens whose frequency exceeds ``max_frequency`` (noise / stop words).
  3. Generate data-quality variations for each remaining unique token using
     one of three methods: 'fuzzy', 'phonetic', or 'manual'.

Outputs:
  - cleaned_refDict : {refID: [tokens]} with high-frequency tokens removed
  - tokenFreqDict   : {token: frequency}
  - variations_dict : {token: set(variations)}
"""

from collections import Counter
from time import perf_counter
import os
import random
import sys


def count_token_frequencies(refDict):
    """Return a {token: frequency} mapping over all records."""
    counter = Counter()
    for tokens in refDict.values():
        counter.update(set(tokens))
    return dict(counter)


def remove_high_frequency_tokens(refDict, tokenFreqDict, max_frequency=60):
    """Remove tokens whose document frequency exceeds ``max_frequency``."""
    noisy = {t for t, f in tokenFreqDict.items() if f > max_frequency}

    cleaned = {}
    for refID, tokens in refDict.items():
        cleaned[refID] = [t for t in tokens if t not in noisy]

    return cleaned, noisy


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
    """
    Group tokens using ``data_quality_generator``.

    For every token T we generate its plausible corruptions via
    ``generate_all_variations``. Two tokens are linked only when one of
    them generates a variation that equals another *actual* token in the
    dataset (case-insensitive). This keeps grouping discriminative —
    n-gram fragments / acronyms produced by the generator are ignored
    unless they happen to coincide with a real token.

    The function seeds ``random`` per token so output is reproducible
    regardless of token ordering.

    Complexity: O(N · T · L) where T is the number of transforms in the
    generator (~30) and L is the average token length.
    """
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
    """
    Build {token: set(variations)} for every unique token in ``refDict``.

    method ∈ {'data_quality', 'fuzzy', 'phonetic', 'manual'}
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
