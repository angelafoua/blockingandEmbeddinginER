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
# Step 4: Merge blocks that share >=1 refID
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

def iterative_blocking(ref_dict, original_ref_dict=None):
    """Run the iterative k-token blocking process.

    Returns a tuple (current_blocks, refid_blocks) where refid_blocks maps
    block_key -> set of original refIDs (resolved through all pseudo-record
    rewrites).  Pass the un-rewritten ref_dict as original_ref_dict to
    enable that resolution; when omitted the second value mirrors the first.
    """
    # Compute stopping threshold
    token_lengths = [len(set(tokens)) for tokens in ref_dict.values()]
    mode_length = mode(token_lengths, keepdims=True)[0][0]
    max_k = floor(0.75 * mode_length)

    print(f"Stopping threshold k = {max_k}")

    current_blocks = None
    # Track which original refIDs end up in each "pseudo-record" id introduced
    # by the rewrite step at the bottom of the loop.
    pseudo_to_refs = {rid: {rid} for rid in ref_dict.keys()} if original_ref_dict is not None else None

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

        # Recompute ref_dict from merged blocks. Each block becomes a new
        # pseudo-record whose "tokens" are the refIDs of its members.
        new_ref_dict = {}
        new_pseudo_to_refs = {}
        for i, members in enumerate(blocks.values()):
            pseudo_id = f"block_{i}"
            new_ref_dict[pseudo_id] = list(members)
            if pseudo_to_refs is not None:
                resolved = set()
                for m in members:
                    resolved.update(pseudo_to_refs.get(m, {m}))
                new_pseudo_to_refs[pseudo_id] = resolved
        ref_dict = new_ref_dict
        if pseudo_to_refs is not None:
            pseudo_to_refs = new_pseudo_to_refs

    # Resolve final blocks back to original refIDs.
    if current_blocks is None:
        return {}, {}
    if pseudo_to_refs is None:
        # No resolution requested -- return blocks as-is for both.
        return current_blocks, current_blocks

    refid_blocks = {}
    for key, members in current_blocks.items():
        resolved = set()
        for m in members:
            resolved.update(pseudo_to_refs.get(m, {m}))
        refid_blocks[key] = resolved
    return current_blocks, refid_blocks


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

    # --- Global correction (DWM25) before blocking ---
    # Pass word_list_path="DWM_WordList.txt" if you have the word list file.
    tokenFreqDict = dict(compute_token_freq(refDict))
    refDict = global_correction.global_replace(refDict, tokenFreqDict)
    # -------------------------------------------------

    # Keep a copy of the original refDict so we can resolve pseudo-records
    # back to real refIDs for evaluation.
    original_refDict = {rid: list(toks) for rid, toks in refDict.items()}

    raw_blocks, refid_blocks = iterative_blocking(refDict, original_ref_dict=original_refDict)

    print('\nnumber of blocks:', len(raw_blocks))

    # --- ER metrics (precision / recall / F1) ---
    truth_file = er_metrics.detect_truth_file(input_file, truth_dir=truth_dir)
    if truth_file is None:
        print("No truth file matched for input; skipping ER metrics.")
    else:
        er_metrics.compute_metrics(refid_blocks, truth_file)
