"""Local runner: same as recursive_algo1_2_v2 __main__ but uses local path
and prints all final blocks (key snippet + size).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

import build_refDict
import build_tokenFreqDict
from recursive_algo1_2_v2 import (
    remove_high_freq_tokens,
    remove_high_frequency_tokens,
    compute_stop_k,
    blocking,
    recursive_blocking,
    filter_top_k_smallest,
)

INPUT = os.path.join(os.path.dirname(__file__), "S12PX.txt")

print("Starting...")
refDict = build_refDict.tokenizeInput(INPUT)
print(f"Loaded {len(refDict)} records")
refDict = remove_high_freq_tokens(refDict, max_freq=6)

tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)
print(f"Built token frequency dict with {len(tokenFreqDict)} unique tokens")

MAX_TOKEN_FREQUENCY = 60
refDict, removed = remove_high_frequency_tokens(refDict, tokenFreqDict,
                                               max_frequency=MAX_TOKEN_FREQUENCY)
print(f"Stop-word removal: dropped {len(removed)} tokens with freq > {MAX_TOKEN_FREQUENCY}")
print(f"  Examples: {sorted(removed, key=lambda t: -tokenFreqDict[t])[:15]}")
tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)
print(f"Rebuilt token frequency dict: {len(tokenFreqDict)} unique tokens remain")

stop_k = compute_stop_k(refDict)

print("\nCreating initial blocks...")
initial_blocks = blocking(refDict, tokenFreqDict)
print(f"Initial blocks created: {len(initial_blocks)}")

print("\nStarting recursive blocking...")
final_blocks = recursive_blocking(1, initial_blocks, stop_k)

TOP_K = 3
print(f"\nApplying top-{TOP_K} smallest-block filter per record...")
before = len(final_blocks)
final_blocks = filter_top_k_smallest(final_blocks, k=TOP_K)
print(f"  blocks: {before} -> {len(final_blocks)}")

print(f"\n=== FINAL RESULTS ===")
print(f"Number of final blocks: {len(final_blocks)}")

# Print every final block: key snippet + full size
def key_snippet(k, max_chars=80):
    s = repr(k)
    return s if len(s) <= max_chars else s[:max_chars - 3] + "..."

print("\n=== ALL FINAL BLOCKS (key snippet, size) ===")
sizes = []
for i, (k, refs) in enumerate(final_blocks.items()):
    size = len(refs)
    sizes.append(size)
    print(f"[{i:5d}] size={size:5d}  key={key_snippet(k)}")

print("\n=== SIZE SUMMARY ===")
if sizes:
    from collections import Counter
    print(f"Total blocks : {len(sizes)}")
    print(f"Total entries: {sum(sizes)}")
    print(f"Min size     : {min(sizes)}")
    print(f"Max size     : {max(sizes)}")
    print(f"Mean size    : {sum(sizes)/len(sizes):.2f}")
    dist = Counter(sizes)
    print("Size distribution (size: count):")
    for sz in sorted(dist):
        print(f"  {sz}: {dist[sz]}")
