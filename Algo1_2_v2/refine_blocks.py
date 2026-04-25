"""from collections import defaultdict

def refine_blocks(blocks, beta):

    blocks = {
        blockingKey: {
            refID: set(tokens)
        }
    }

    Returns refined blocks with one additional blocking token.


    newBlocks = defaultdict(dict)

    for blockingKey, recordDict in blocks.items():

        # Compute token frequency inside this block
        blockTokenFreq = defaultdict(int)

        for refID, tokenSet in recordDict.items():
            for token in tokenSet:
                if token != blockingKey:
                    blockTokenFreq[token] += 1

        # Build refined blocks
        for refID, tokenSet in recordDict.items():
            for token in tokenSet:
                if token != blockingKey and blockTokenFreq[token] >= beta:
                    
                    # Create composite blocking key
                    if isinstance(blockingKey, tuple):
                        newKey = blockingKey + (token,)
                    else:
                        newKey = (blockingKey, token)

                    newBlocks[newKey][refID] = tokenSet

    return newBlocks"""
from collections import defaultdict

def refine_blocks(blocks, beta):

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

                if blockTokenFreq[token] >= beta:

                    
                    newKey = tuple(sorted(usedTokens | {token}))
                    newBlocks[newKey][refID] = tokenSet

    return newBlocks