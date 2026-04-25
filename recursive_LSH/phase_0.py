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


def generate_variations(refDict, method="fuzzy", similarity_threshold=85,
                        manual_map=None):
    """
    Build {token: set(variations)} for every unique token in ``refDict``.

    method ∈ {'fuzzy', 'phonetic', 'manual'}
    """
    unique_tokens = {t for tokens in refDict.values() for t in tokens}

    if method == "fuzzy":
        return _fuzzy_variations(unique_tokens, similarity_threshold)
    if method == "phonetic":
        return _phonetic_variations(unique_tokens)
    if method == "manual":
        return _manual_variations(unique_tokens, manual_map or {})

    raise ValueError(f"Unknown variation method: {method}")


def run_phase_0(refDict, max_frequency=60, method="fuzzy",
                similarity_threshold=85, manual_map=None):
    """Execute Phase 0 end-to-end."""
    tokenFreqDict = count_token_frequencies(refDict)
    cleaned_refDict, removed = remove_high_frequency_tokens(
        refDict, tokenFreqDict, max_frequency=max_frequency
    )
    variations_dict = generate_variations(
        cleaned_refDict,
        method=method,
        similarity_threshold=similarity_threshold,
        manual_map=manual_map,
    )

    print(f"[Phase 0] removed {len(removed)} high-frequency tokens "
          f"(threshold={max_frequency})")
    print(f"[Phase 0] generated variations for "
          f"{len(variations_dict)} unique tokens (method={method})")

    return cleaned_refDict, tokenFreqDict, variations_dict
