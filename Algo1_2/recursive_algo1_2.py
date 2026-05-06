
""""This the same as algo1 but using deduplication after each recursive step. Also taken from alo2,
we will change the way we find and use beta and stop the whole process"""



import build_tokenFreqDict
from refine_blocks import refine_blocks
import ast
from pathlib import Path
import build_refDict

def load_dict(path_str):
    path = Path(path_str)
    with open(path, "r", encoding="utf-8") as f:
        return ast.literal_eval(f.read())

from statistics import mean
from scipy.stats import mode
from math import floor


def compute_stop_k(refDict, factor=0.6):
    token_lengths = [len(set(tokens)) for tokens in refDict.values()]
    mode_length = mode(token_lengths, keepdims=True)[0][0]
    stop_k = floor(factor * mode_length)

    print("Mode token length:", mode_length)
    print(f"Stopping threshold k: {stop_k} (factor={factor})")

    return stop_k

def recursive_blocking(beta, blocks, stop_k):

    if beta > stop_k:
        return blocks

    newBlocks = refine_blocks(blocks, beta)

    if not newBlocks:
        return blocks

    merged_blocks = merge_blocks(blocks, newBlocks)

    return recursive_blocking(beta + 1, merged_blocks, stop_k)

def merge_blocks(old_blocks, new_blocks):
    merged = {}
    seen = {}

    # combine both dictionaries
    combined = {**old_blocks, **new_blocks}

    for key, refs in combined.items():
        ref_set = frozenset(refs.keys())

        if ref_set not in seen:
            seen[ref_set] = key
            merged[key] = refs

    return merged

def blocking(refDict, tokenFreqDict):

    from collections import defaultdict
    blocks = defaultdict(dict)

    avg_freq = mean(tokenFreqDict.values())
    threshold = 1.1 * avg_freq

    print("Average token frequency:", avg_freq)
    print("Token threshold:", threshold)

    for key in refDict:
        tokenList = refDict[key]

        for token in tokenList:
            freq = tokenFreqDict[token]

            if freq >= threshold:
                blocks[token][key] = set(tokenList)

    return blocks


if __name__ == "__main__":

    refDict = build_refDict.tokenizeInput(r"C:\Users\ldfoua1\OneDrive - UA Little Rock\Documents\PhD\Blocking-only DWM\S12PX.txt")

    tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)

    # Tune stop_k by setting STOP_K (explicit int) or STOP_K_FACTOR (multiplier
     # of the modal record length). STOP_K wins when both are set.
    STOP_K = None
    STOP_K_FACTOR = 0.6
    stop_k = STOP_K if STOP_K is not None else compute_stop_k(refDict, factor=STOP_K_FACTOR)

    initial_blocks = blocking(refDict, tokenFreqDict)

    final_blocks = recursive_blocking(1, initial_blocks, stop_k)

    print(final_blocks)
    print("number of blocks:", len(final_blocks))