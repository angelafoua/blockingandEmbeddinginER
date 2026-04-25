""""This the same as algo1 but using deduplication after each recursive step"""



import build_tokenFreqDict
from refine_blocks import refine_blocks
import ast
from pathlib import Path
import build_refDict

def load_dict(path_str):
    path = Path(path_str)
    with open(path, "r", encoding="utf-8") as f:
        return ast.literal_eval(f.read())

def recursive_blocking(beta, blocks):
    if beta <= 1:
        return blocks

    newBlocks = refine_blocks(blocks, beta)

    if not newBlocks:
        return blocks

    # merge blocks
    merged_blocks = merge_blocks(blocks, newBlocks)

    return recursive_blocking(beta - 1, merged_blocks)

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

def blocking(beta, refDict, tokenFreqDict):
    print('beta =',beta)
    #create the default dict for blocksfrom collections import defaultdict
    from collections import defaultdict
    blocks = defaultdict(dict)
    #go thru the refDict dictionary
    for key in refDict:
        tokenList = refDict[key]
        #for every record, look at its tokens
        for token in tokenList:
            freq = tokenFreqDict[token]
            if freq>=beta:
                blocks[token][key] = set(tokenList)
    return blocks


if __name__ == "__main__":
     #read files
    #refDict = load_dict(r"C:\Users\ldfoua1\OneDrive - UA Little Rock\Documents\PhD\Blocking-only DWM\refDict")
    refDict = build_refDict.tokenizeInput(r"C:\Users\ldfoua1\OneDrive - UA Little Rock\Documents\PhD\Blocking-only DWM\S12PX.txt")
    #tokenFreqDict = load_dict(r"C:\Users\ldfoua1\OneDrive - UA Little Rock\Documents\PhD\Blocking-only DWM\tokenFreqDict")
    tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)
    initial_blocks = blocking(4, refDict, tokenFreqDict)
    final_blocks = recursive_blocking(4, initial_blocks)
    print(final_blocks)
    print('number of blocks:', len(final_blocks))