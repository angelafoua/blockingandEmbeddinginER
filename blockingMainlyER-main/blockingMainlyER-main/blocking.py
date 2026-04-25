from collections import defaultdict
from itertools import combinations

def build_blocks(blocking_tokens):

    blocks = defaultdict(list)

    for record_id, tokens in blocking_tokens.items():
        for token in tokens:
            blocks[token].append(record_id)

    return blocks


def recursive_blocking(blocks, max_block_size=100):

    new_blocks = {}

    for block_id, records in blocks.items():
        if len(records) <= max_block_size:
            new_blocks[block_id] = records
        else:
            for i, r in enumerate(records):
                new_blocks[f"{block_id}_{i%5}"] = [r]

    return new_blocks


def generate_candidate_pairs(blocks):

    pairs = set()

    for records in blocks.values():
        for r1, r2 in combinations(records, 2):
            pairs.add((r1, r2))

    return pairs
