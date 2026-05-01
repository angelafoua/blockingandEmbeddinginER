"""Here I do block, merge and block until I reach a certain threshold. 
I block elements based on 1 token, then merge blocks that share at least one refID.
Then, I block based on the two tokens of the merged blocks. 
Then I repeat the process until I reach a certain threshold."""

import build_tokenFreqDict
import build_refDict
from collections import defaultdict
from pathlib import Path
import ast


def load_dict(path_str):
    path = Path(path_str)
    with open(path, "r", encoding="utf-8") as f:
        return ast.literal_eval(f.read())


def blocking(beta, refDict, tokenFreqDict):
    print("beta =", beta)

    blocks = defaultdict(dict)

    for refID in refDict:
        tokenList = refDict[refID]

        for token in tokenList:
            freq = tokenFreqDict[token]

            if freq >= beta:
                blocks[token][refID] = set(tokenList)

    return blocks

# --------------------------------------------
# Merge blocks that share reference IDs
# --------------------------------------------

def merge_blocks(blocks):

    merged = []
    used = set()

    block_items = list(blocks.items())

    for i, (key1, refs1) in enumerate(block_items):

        if key1 in used:
            continue

        combined_key = [key1]
        combined_refs = dict(refs1)

        for j, (key2, refs2) in enumerate(block_items):

            if i == j or key2 in used:
                continue

            # check if they share refID
            if set(refs1.keys()) & set(refs2.keys()):
                combined_key.append(key2)
                combined_refs.update(refs2)
                used.add(key2)

        used.add(key1)

        merged.append(("_".join(sorted(combined_key)), combined_refs))

    return dict(merged)


# --------------------------------------------
# Re-block using merged keys
# --------------------------------------------
def reblock(merged_blocks):

    new_blocks = defaultdict(dict)

    for block_key, refs in merged_blocks.items():

        tokens = block_key.split("_")

        for refID, token_set in refs.items():

            new_key = "_".join(sorted(tokens))

            new_blocks[new_key][refID] = token_set

    return new_blocks


# --------------------------------------------
# Iterative blocking until convergence
# --------------------------------------------
def iterative_blocking(initial_blocks):

    previous_len = -1
    current_blocks = initial_blocks

    while previous_len != len(current_blocks):

        previous_len = len(current_blocks)

        merged = merge_blocks(current_blocks)

        current_blocks = reblock(merged)

        print("Number of blocks:", len(current_blocks))

    return current_blocks


# --------------------------------------------
# MAIN
# --------------------------------------------
if __name__ == "__main__":
    import sys
    import os
    # Allow importing global_correction.py and er_metrics.py from the repository root
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    import global_correction
    import er_metrics

    input_file = r"C:\Users\ldfoua1\OneDrive - UA Little Rock\Documents\PhD\Blocking-only DWM\S12PX.txt"
    truth_dir  = r"C:\Users\ldfoua1\OneDrive - UA Little Rock\Documents\PhD\Blocking-only DWM"

    refDict = build_refDict.tokenizeInput(input_file)
    tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)

    # --- Global correction (DWM25) before blocking ---
    # Pass word_list_path="DWM_WordList.txt" if you have the word list file.
    refDict = global_correction.global_replace(refDict, tokenFreqDict)
    tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)  # rebuild after correction
    # -------------------------------------------------

    initial_blocks = blocking(4, refDict, tokenFreqDict)
    final_blocks = iterative_blocking(initial_blocks)

    print("Final number of blocks:", len(final_blocks))

    # --- ER metrics (precision / recall / F1) ---
    truth_file = er_metrics.detect_truth_file(input_file, truth_dir=truth_dir)
    if truth_file is None:
        print("No truth file matched for input; skipping ER metrics.")
    else:
        er_metrics.compute_metrics(final_blocks, truth_file)
