"""Here I am doing recursive blocking, which means I will do blocking based on 1 token, 
then I will do blocking based on 2 tokens, then 3 tokens, and so on and so forth until I reach the beta threshold.
When I create blocks based on 1 token, I will create blocks based on 2 tokens whithin the blocks created based on 1 token, then I will create blocks based on 3 tokens within the blocks created based on 2 tokens,
and so on and so forth until I reach the beta threshold.
Limitations: The result of this algorithm with beta = 4, and S12PX is 214732 blocks. This is a big number
and I have not looked into how I will do the merging or the transitive closure"""



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
    return recursive_blocking(beta - 1, newBlocks)


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
    import sys
    import os
    # Allow importing global_correction.py from the repository root
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    import global_correction

    refDict = build_refDict.tokenizeInput(r"C:\Users\ldfoua1\OneDrive - UA Little Rock\Documents\PhD\Blocking-only DWM\S12PX.txt")
    tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)

    # --- Global correction (DWM25) before blocking ---
    # Pass word_list_path="DWM_WordList.txt" if you have the word list file.
    refDict = global_correction.global_replace(refDict, tokenFreqDict)
    tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)  # rebuild after correction
    # -------------------------------------------------

    initial_blocks = blocking(4, refDict, tokenFreqDict)
    final_blocks = recursive_blocking(4, initial_blocks)
    print(final_blocks)
    print('number of blocks:', len(final_blocks))
