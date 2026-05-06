"""Refinement step for recursive blocking.

For each block, count how often each (non-key) token co-occurs across the
records in the block, and emit a refined block keyed by the original key
plus that token, restricted to records containing it. The intra-block
frequency floor `min_intra_freq` controls how supported a co-token must
be to seed a refined block.

Note: this `min_intra_freq` is a LOWER bound on intra-block token
frequency. It is a different parameter from the upper-bound DF cap used
in `blocking()` (init_df_max). The recursion in
`recursive_algo1_2_v2.recursive_blocking` typically passes
`max(depth, configured_min_intra_freq)` so that the floor grows with
recursion depth without ever falling below the configured minimum.
"""
from collections import defaultdict


def refine_blocks(blocks, min_intra_freq):
    newBlocks = defaultdict(dict)

    for blockingKey, recordDict in blocks.items():

        # Normalize to tuple
        if not isinstance(blockingKey, tuple):
            usedTokens = {blockingKey}
        else:
            usedTokens = set(blockingKey)

        blockTokenFreq = defaultdict(int)

        # Compute token frequency inside block
        for refID, tokenSet in recordDict.items():
            for token in tokenSet:
                if token not in usedTokens:
                    blockTokenFreq[token] += 1

        # Build refined blocks
        for refID, tokenSet in recordDict.items():
            for token in tokenSet:
                if token in usedTokens:
                    continue

                if blockTokenFreq[token] >= min_intra_freq:
                    newKey = tuple(sorted(usedTokens | {token}))
                    newBlocks[newKey][refID] = tokenSet

    return newBlocks
