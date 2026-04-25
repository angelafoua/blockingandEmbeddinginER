"""This the same as algo1 but using deduplication after each recursive step. Also taken from alo2,
we will change the way we find and use beta and stop the whole process.
Another change is that we will create combine the keys of blocks that have the same reference IDs. 
This is to reduce the number of blocks and increase the size of blocks. """


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
import time

def compute_stop_k(refDict):
    token_lengths = [len(set(tokens)) for tokens in refDict.values()]
    mode_length = mode(token_lengths, keepdims=True)[0][0]
    stop_k = floor(0.6 * mode_length)
    print("Mode token length:", mode_length)
    print("Stopping threshold k:", stop_k)
    return stop_k

def recursive_blocking(beta, blocks, stop_k):
    print(f"\n--- Beta = {beta}, Stop_k = {stop_k} ---")
    print(f"Current number of blocks: {len(blocks)}")
    
    if beta > stop_k:
        print("Stopping: beta > stop_k")
        return blocks
    
    print(f"Calling refine_blocks with beta={beta}...")
    start_time = time.time()
    newBlocks = refine_blocks(blocks, beta)
    refine_time = time.time() - start_time
    print(f"refine_blocks took {refine_time:.2f} seconds, produced {len(newBlocks) if newBlocks else 0} blocks")
    
    if not newBlocks:
        print("Stopping: newBlocks is empty")
        return blocks
    
    print(f"Merging blocks...")
    start_time = time.time()
    merged_blocks = merge_blocks(blocks, newBlocks)
    merge_time = time.time() - start_time
    print(f"merge_blocks took {merge_time:.2f} seconds, result: {len(merged_blocks)} blocks")
    
    return recursive_blocking(beta + 1, merged_blocks, stop_k)

def merge_blocks(old_blocks, new_blocks):
    """Optimized merge using a single pass with hash-based deduplication"""
    ref_set_to_data = {}  # Maps frozenset of refs -> (list of keys, refs dict)
    
    # Combine both dictionaries
    combined = {**old_blocks, **new_blocks}
    
    # Single pass: group by reference set
    for key, refs in combined.items():
        ref_set = frozenset(refs.keys())
        
        # Normalize key to ensure it's hashable
        if isinstance(key, tuple):
            key_tuple = key
        else:
            key_tuple = (key,)
        
        if ref_set not in ref_set_to_data:
            # First occurrence of this reference set
            ref_set_to_data[ref_set] = (list(key_tuple), refs)
        else:
            # Add new keys to existing list (will dedupe later)
            existing_keys, _ = ref_set_to_data[ref_set]
            existing_keys.extend(key_tuple)
    
    # Build final merged dictionary
    merged = {}
    for ref_set, (key_list, refs) in ref_set_to_data.items():
        # Deduplicate keys using set (fast) then convert back to list
        unique_keys = list(dict.fromkeys(key_list))  # Preserves order, removes dupes
        
        # Create final key
        if len(unique_keys) == 1:
            final_key = unique_keys[0]
        else:
            final_key = tuple(unique_keys)
        
        merged[final_key] = refs
    
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
    print("Starting...")
    refDict = build_refDict.tokenizeInput(r"C:\Users\ldfoua1\OneDrive - UA Little Rock\Documents\PhD\Blocking-only DWM\S12PX.txt")
    print(f"Loaded {len(refDict)} records")
    
    tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)
    print(f"Built token frequency dict with {len(tokenFreqDict)} unique tokens")
    
    stop_k = compute_stop_k(refDict)
    
    print("\nCreating initial blocks...")
    initial_blocks = blocking(refDict, tokenFreqDict)
    print(f"Initial blocks created: {len(initial_blocks)}")
    
    print("\nStarting recursive blocking...")
    final_blocks = recursive_blocking(1, initial_blocks, stop_k)
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Number of final blocks: {len(final_blocks)}")