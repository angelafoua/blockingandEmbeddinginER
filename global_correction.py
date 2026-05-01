"""Standalone global token correction, ported from DWM25_Global_Token_Replace.

Replaces low-frequency tokens that are within edit-distance 1 (Levenshtein)
or edit-distance 1 transposition (Damerau-Levenshtein) of a high-frequency
token.  Run this after building refDict and tokenFreqDict, before blocking,
then rebuild tokenFreqDict from the returned corrected refDict.

Requirements::

    pip install python-Levenshtein textdistance

Example (Algo1 / Algo2 / Algo3)::

    import build_refDict, build_tokenFreqDict, global_correction

    refDict       = build_refDict.tokenizeInput(input_file)
    tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)

    refDict       = global_correction.global_replace(refDict, tokenFreqDict)
    tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)  # rebuild

    # ... run your blocking algorithm
"""

import operator

import Levenshtein as lev
from textdistance import DamerauLevenshtein


def global_replace(
    refDict,
    tokenFreqDict,
    word_list_path=None,
    min_freq_std_token=10,
    min_len_std_token=3,
    max_freq_err_token=3,
    verbose=True,
):
    """Return a corrected copy of refDict with misspelled tokens replaced.

    Parameters
    ----------
    refDict : dict[any, list[str]]
        {refID: [token, ...]} as produced by build_refDict.tokenizeInput.
    tokenFreqDict : dict[str, int]
        {token: frequency} as produced by build_tokenFreqDict.buildTokenFreqDict.
    word_list_path : str or None
        Optional path to a newline-separated word list (e.g. DWM_WordList.txt).
        Rare tokens that appear in this list are excluded from the error-token
        candidate set so legitimately uncommon words are never corrected.
    min_freq_std_token : int
        A token must appear at least this many times to be a standard (correct)
        form that other tokens can be corrected towards.
    min_len_std_token : int
        Tokens shorter than this are never used as standard tokens.
    max_freq_err_token : int
        A token appearing at most this many times is a candidate error token.
    verbose : bool
        Print progress statistics to stdout.

    Returns
    -------
    dict[any, list[str]]
        New refDict with corrected tokens.  tokenFreqDict is NOT updated;
        call buildTokenFreqDict on the returned dict before blocking.
    """
    _dl = DamerauLevenshtein()

    # Phase 1 — load optional word list
    word_list = set()
    if word_list_path is not None:
        with open(word_list_path, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w:
                    word_list.add(w)
        if verbose:
            print(f"[global_correction] Word list loaded: {len(word_list)} words")

    # Phase 2 — build a clean, frequency-sorted token index
    sorted_index = sorted(
        tokenFreqDict.items(), reverse=True, key=operator.itemgetter(1)
    )
    clean_index = []
    for word, freq in sorted_index:
        if len(word) < min_len_std_token:
            continue
        if not word.isalpha():
            continue
        # Skip rare tokens that exist in the word list (correctly spelled but uncommon)
        if freq <= max_freq_err_token and word in word_list:
            continue
        clean_index.append([word, freq])

    if verbose:
        print(f"[global_correction] Tokens in clean index: {len(clean_index)}")

    # Phase 3 — build correction map: error_token -> standard_token
    # Iterates from the highest-frequency (standard) end downward and compares
    # against lowest-frequency (error) candidates from the bottom upward.
    std_token_dict = {}
    clean_cnt = len(clean_index)

    for j in range(clean_cnt - 1):
        word_j, freq_j = clean_index[j]
        if freq_j < min_freq_std_token:
            break  # remaining tokens are all below the standard threshold
        for k in range(clean_cnt - 1, 1, -1):
            word_k, freq_k = clean_index[k]
            if not word_k:
                continue  # already consumed
            if freq_k > max_freq_err_token:
                break  # remaining tokens are no longer error candidates
            dist = lev.distance(word_j.lower(), word_k.lower())
            if dist == 1:
                std_token_dict[word_k] = word_j
                clean_index[k][0] = ""  # mark as consumed
            elif dist == 2 and _dl.distance(word_j, word_k) == 1:
                # Levenshtein distance 2 but Damerau distance 1 means a single
                # adjacent transposition (e.g. "teh" -> "the").
                std_token_dict[word_k] = word_j
                clean_index[k][0] = ""

    if verbose:
        print(f"[global_correction] Correction pairs found: {len(std_token_dict)}")

    # Phase 4 — apply corrections to all references
    token_change_cnt = 0
    ref_change_cnt = 0
    new_dict = {}

    for ref_id, token_list in refDict.items():
        new_list = []
        changed = False
        for token in token_list:
            if token in std_token_dict:
                new_list.append(std_token_dict[token])
                token_change_cnt += 1
                changed = True
            else:
                new_list.append(token)
        new_dict[ref_id] = new_list
        if changed:
            ref_change_cnt += 1

    if verbose:
        print(f"[global_correction] Tokens corrected    : {token_change_cnt}")
        print(f"[global_correction] References corrected: {ref_change_cnt}")

    return new_dict
