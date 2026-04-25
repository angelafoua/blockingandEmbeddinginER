"""This algorithm is the uses recursion and iteration together. It combines algo1 and algo2.
The problem with this algorithm is that it will after the first iteration, 
it will create one block"""

from collections import defaultdict, Counter
from itertools import combinations
from statistics import mean
from math import floor
from scipy.stats import mode
import build_refDict


# ------------------------------------------------------------
# Utility: Disjoint Set (Union-Find) for Efficient Merging
# ------------------------------------------------------------

class UnionFind:
    def __init__(self, elements):
        self.parent = {e: e for e in elements}
        self.rank = {e: 0 for e in elements}

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        rootX = self.find(x)
        rootY = self.find(y)

        if rootX == rootY:
            return

        if self.rank[rootX] < self.rank[rootY]:
            self.parent[rootX] = rootY
        elif self.rank[rootX] > self.rank[rootY]:
            self.parent[rootY] = rootX
        else:
            self.parent[rootY] = rootX
            self.rank[rootX] += 1


# ------------------------------------------------------------
# Step 1: Compute Token Frequencies
# ------------------------------------------------------------

def compute_token_freq(ref_dict):
    token_freq = Counter()
    for tokens in ref_dict.values():
        token_freq.update(tokens)
    return token_freq


# ------------------------------------------------------------
# Step 2: Build Blocks by k-token combinations
# ------------------------------------------------------------

def build_blocks(ref_dict, valid_tokens, k):
    blocks = defaultdict(set)

    for ref_id, tokens in ref_dict.items():
        filtered = sorted(set(tokens) & valid_tokens)
        if len(filtered) < k:
            continue

        for combo in combinations(filtered, k):
            blocks[combo].add(ref_id)

    return blocks


# ------------------------------------------------------------
# Step 3: Deduplicate identical blocks
# ------------------------------------------------------------

def deduplicate_blocks(blocks):
    unique = {}
    seen = {}

    for key, ref_ids in blocks.items():
        frozen = frozenset(ref_ids)
        if frozen not in seen:
            seen[frozen] = key
            unique[key] = ref_ids

    return unique


# ------------------------------------------------------------
# Step 4: Merge blocks that share ≥1 refID
# ------------------------------------------------------------
def merge_by_key_overlap(blocks):
    keys = list(blocks.keys())
    parent = {k: k for k in keys}

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    # Compare keys by token overlap
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if set(keys[i]) & set(keys[j]):
                union(keys[i], keys[j])

    # Build merged blocks
    merged = defaultdict(set)
    for key in keys:
        root = find(key)
        merged[root].update(blocks[key])

    return dict(merged)





# ------------------------------------------------------------
# Full Iterative Blocking Process
# ------------------------------------------------------------

def iterative_blocking(ref_dict):
    # Compute stopping threshold
    token_lengths = [len(set(tokens)) for tokens in ref_dict.values()]
    mode_length = mode(token_lengths, keepdims=True)[0][0]
    max_k = floor(0.75 * mode_length)

    print(f"Stopping threshold k = {max_k}")

    current_blocks = None

    for k in range(1, max_k + 1):

        print(f"\n=== Iteration k={k} ===")

        # Step A: Compute frequency
        token_freq = compute_token_freq(ref_dict)
        token_freq = compute_token_freq(ref_dict)

        if not token_freq:
            print("No tokens left. Stopping.")
            break

        avg_freq = mean(token_freq.values())
        threshold = 1.5 * avg_freq

        valid_tokens = {t for t, f in token_freq.items() if f > threshold}

        print(f"Valid tokens count: {len(valid_tokens)}")

        # Step B: Build blocks
        blocks = build_blocks(ref_dict, valid_tokens, k)

        print(f"Blocks before dedup: {len(blocks)}")

        # Step C: Deduplicate
        blocks = deduplicate_blocks(blocks)

        print(f"Blocks after dedup: {len(blocks)}")

        # Step D: Merge overlapping blocks
        blocks = merge_by_key_overlap(blocks)

        print(f"Blocks after merge: {len(blocks)}")

        current_blocks = blocks

        # Recompute ref_dict from merged blocks
        # Each block becomes a new pseudo-record
        ref_dict = {f"block_{i}": list(block)
                    for i, block in enumerate(blocks.values())}

    return current_blocks

if __name__ == "__main__":

    #refDict = load_dict(r"C:\Users\ldfoua1\OneDrive - UA Little Rock\Documents\PhD\Blocking-only DWM\refDict")
    refDict = build_refDict.tokenizeInput(r"C:\Users\ldfoua1\OneDrive - UA Little Rock\Documents\PhD\Blocking-only DWM\S12PX.txt")
    #tokenFreqDict = load_dict(r"C:\Users\ldfoua1\OneDrive - UA Little Rock\Documents\PhD\Blocking-only DWM\tokenFreqDict")
  
    result = iterative_blocking(refDict)

    print("\nFinal Blocks:", result)
    print('\nnumber of blocks:', len(result))
    #for k, v in result.items():
        #print(k, v)