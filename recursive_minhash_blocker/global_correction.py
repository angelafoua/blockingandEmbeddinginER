"""Global token correction for the Recursive MinHash Blocker.

This is a thin re-export of the top-level global_correction module so the
package stays self-contained.  See the repo-root global_correction.py for
full documentation.
"""

from __future__ import annotations

import operator
from collections import Counter
from typing import Dict, List, Optional

import Levenshtein as lev
from textdistance import DamerauLevenshtein


def global_replace(
    refDict: Dict,
    tokenFreqDict: Dict[str, int],
    word_list_path: Optional[str] = None,
    min_freq_std_token: int = 10,
    min_len_std_token: int = 3,
    max_freq_err_token: int = 3,
    verbose: bool = True,
) -> Dict:
    """Replace misspelled low-frequency tokens with their high-frequency neighbours.

    Parameters mirror the top-level global_correction.global_replace; see
    that module's docstring for full details.
    """
    _dl = DamerauLevenshtein()

    word_list: set = set()
    if word_list_path is not None:
        with open(word_list_path, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w:
                    word_list.add(w)
        if verbose:
            print(f"[global_correction] Word list loaded: {len(word_list)} words")

    sorted_index = sorted(
        tokenFreqDict.items(), reverse=True, key=operator.itemgetter(1)
    )
    clean_index = []
    for word, freq in sorted_index:
        if len(word) < min_len_std_token:
            continue
        if not word.isalpha():
            continue
        if freq <= max_freq_err_token and word in word_list:
            continue
        clean_index.append([word, freq])

    if verbose:
        print(f"[global_correction] Tokens in clean index: {len(clean_index)}")

    std_token_dict: Dict[str, str] = {}
    clean_cnt = len(clean_index)

    for j in range(clean_cnt - 1):
        word_j, freq_j = clean_index[j]
        if freq_j < min_freq_std_token:
            break
        for k in range(clean_cnt - 1, 1, -1):
            word_k, freq_k = clean_index[k]
            if not word_k:
                continue
            if freq_k > max_freq_err_token:
                break
            dist = lev.distance(word_j.lower(), word_k.lower())
            if dist == 1:
                std_token_dict[word_k] = word_j
                clean_index[k][0] = ""
            elif dist == 2 and _dl.distance(word_j, word_k) == 1:
                std_token_dict[word_k] = word_j
                clean_index[k][0] = ""

    if verbose:
        print(f"[global_correction] Correction pairs found: {len(std_token_dict)}")

    token_change_cnt = 0
    ref_change_cnt = 0
    new_dict: Dict = {}

    for ref_id, token_list in refDict.items():
        new_list: List[str] = []
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
