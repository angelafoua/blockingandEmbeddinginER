""""The minimum number of clusters should be the number of records, if all the records are unique"""

from collections import defaultdict
from statistics import mean
from scipy.stats import mode
from math import floor

def remove_high_freq_tokens(refDict, max_freq=60):
    """
    Remove tokens whose frequency is greater than max_freq.
    """

    from collections import Counter

    # Step 1: Compute token frequencies
    token_counter = Counter()

    for tokens in refDict.values():
        token_counter.update(tokens)

    # Step 2: Identify tokens to remove
    tokens_to_remove = {
        token for token, freq in token_counter.items()
        if freq > max_freq
    }

    print(f"Removing {len(tokens_to_remove)} high-frequency tokens")

    # Step 3: Remove them from records
    new_refDict = {}

    for refID, tokens in refDict.items():
        filtered = [t for t in tokens if t not in tokens_to_remove]
        new_refDict[refID] = filtered

    return new_refDict

def compute_stop_k(refDict, factor=0.6):
    token_lengths = [len(set(tokens)) for tokens in refDict.values()]
    mode_length = mode(token_lengths, keepdims=True)[0][0]
    return floor(factor * mode_length)


def initial_partition(refDict, tokenFreqDict):
    """
    Create initial partition based on frequent tokens.
    Each record belongs to exactly one block.
    """

    avg_freq = mean(tokenFreqDict.values())
    threshold = 1.1 * avg_freq

    blocks = defaultdict(dict)

    for refID, tokenList in refDict.items():
        # pick the most frequent qualifying token
        qualifying_tokens = [
            t for t in tokenList if tokenFreqDict[t] >= threshold
        ]

        if qualifying_tokens:
            key = (max(qualifying_tokens, key=lambda t: tokenFreqDict[t]),)
        else:
            # fallback: unique block
            key = ("UNIQUE_" + str(refID),)

        blocks[key][refID] = set(tokenList)

    return blocks


def refine_partition(blocks, beta):
    """
    Refine by splitting blocks (not duplicating).
    Each block is partitioned based on additional shared tokens.
    """

    newBlocks = {}

    for blockKey, recordDict in blocks.items():

        if len(recordDict) < beta:
            newBlocks[blockKey] = recordDict
            continue

        usedTokens = set(blockKey)

        # Count token frequencies inside block
        tokenCounts = defaultdict(list)

        for refID, tokenSet in recordDict.items():
            for token in tokenSet:
                if token not in usedTokens:
                    tokenCounts[token].append(refID)

        # Find best token to split on
        best_token = None
        best_size = 0

        for token, refIDs in tokenCounts.items():
            if len(refIDs) >= beta and len(refIDs) > best_size:
                best_token = token
                best_size = len(refIDs)

        if best_token is None:
            # no refinement possible
            newBlocks[blockKey] = recordDict
        else:
            # split block
            group_with = {}
            group_without = {}

            for refID, tokenSet in recordDict.items():
                if best_token in tokenSet:
                    group_with[refID] = tokenSet
                else:
                    group_without[refID] = tokenSet

            newKey = tuple(sorted(usedTokens | {best_token}))

            newBlocks[newKey] = group_with

            if group_without:
                newBlocks[blockKey] = group_without

    return newBlocks


def iterative_blocking(refDict, tokenFreqDict, stop_k=None, stop_k_factor=0.6):

    if stop_k is None:
        stop_k = compute_stop_k(refDict, factor=stop_k_factor)

    blocks = initial_partition(refDict, tokenFreqDict)

    beta = 2

    while beta <= stop_k:
        newBlocks = refine_partition(blocks, beta)

        if newBlocks == blocks:
            break

        blocks = newBlocks
        beta += 1

    return blocks


from openpyxl import Workbook

def export_blocks_to_excel(blocks, filename="blocking_results.xlsx"):
    """
    Export blocks dictionary to an Excel file.

    Format expected:
    {
        block_key: {
            refID: tokenSet
        }
    }
    """

    wb = Workbook()
    ws = wb.active
    ws.title = "Blocks"

    # Header row
    ws.append(["Block Key", "Record ID", "Tokens"])

    for block_key, record_dict in blocks.items():

        # Convert key to readable string
        if isinstance(block_key, tuple):
            block_name = ", ".join(block_key)
        else:
            block_name = str(block_key)

        for refID, tokenSet in record_dict.items():
            ws.append([
                block_name,
                refID,
                ", ".join(sorted(tokenSet))
            ])

    wb.save(filename)
    print(f"Excel file saved as: {filename}")

if __name__ == "__main__":

    import sys
    import os
    import build_refDict
    import build_tokenFreqDict

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    import global_correction
    import er_metrics

    input_file = r"C:\Users\ldfoua1\OneDrive - UA Little Rock\Documents\PhD\Blocking-only DWM\S12PX.txt"
    truth_dir  = r"C:\Users\ldfoua1\OneDrive - UA Little Rock\Documents\PhD\Blocking-only DWM"

    refDict = build_refDict.tokenizeInput(input_file)
    refDict = remove_high_freq_tokens(refDict, max_freq=6)
    tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)

    # --- Global correction (DWM25) before blocking ---
    refDict = global_correction.global_replace(refDict, tokenFreqDict)
    tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)
    # -------------------------------------------------

    # Tune stop_k by setting STOP_K (explicit int) or STOP_K_FACTOR (multiplier
     # of the modal record length). STOP_K wins when both are set.
    STOP_K = None
    STOP_K_FACTOR = 0.6
    final_blocks = iterative_blocking(refDict, tokenFreqDict,
                                      stop_k=STOP_K,
                                      stop_k_factor=STOP_K_FACTOR)

    print("\nFinal number of blocks:", len(final_blocks))
    print("Total records:", len(refDict))
    export_blocks_to_excel(final_blocks, "blocking_results.xlsx")

    # --- ER metrics (precision / recall / F1) ---
    truth_file = er_metrics.detect_truth_file(input_file, truth_dir=truth_dir)
    if truth_file is None:
        print("No truth file matched for input; skipping ER metrics.")
    else:
        er_metrics.compute_metrics(final_blocks, truth_file,
                                   universe=refDict.keys())
    # --------------------------------------------