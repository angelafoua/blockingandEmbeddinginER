"""
Phase 3: Recursive Blocking Within Blocks

Iteratively refine each initial block by splitting on the most balanced
"distinguishing" hash key (a key that appears in some, but not all, members
of the block). Recursion stops on any of:

  * depth >= max_depth
  * len(block) <= min_bucket_size
  * no distinguishing keys remain
  * single-record block
"""


def _find_best_split_key(block, hash_key_records):
    """
    Choose the distinguishing key that produces the most balanced split.
    Returns (best_key, with_set, without_set) or (None, None, None).
    """
    if len(block) < 2:
        return None, None, None

    key_to_refs = {}
    for refID in block:
        for key in hash_key_records.get(refID, ()):
            key_to_refs.setdefault(key, set()).add(refID)

    block_set = set(block)
    best_key = None
    best_score = -1
    best_with = None

    for key, refs in key_to_refs.items():
        with_count = len(refs)
        if with_count == 0 or with_count == len(block_set):
            continue
        without_count = len(block_set) - with_count
        score = min(with_count, without_count)
        if score > best_score:
            best_score = score
            best_key = key
            best_with = refs

    if best_key is None:
        return None, None, None

    return best_key, best_with, block_set - best_with


def refine_block(block, hash_key_records, max_depth=3, min_bucket_size=2,
                 depth=0, accumulated_keys=()):
    """
    Recursively refine a single block, returning a list of
    (tuple_of_split_keys, [refIDs]) tuples for the leaf blocks.
    """
    block = list(block)

    if len(block) <= 1 or len(block) <= min_bucket_size or depth >= max_depth:
        return [(accumulated_keys, sorted(block))]

    best_key, group_with, group_without = _find_best_split_key(
        block, hash_key_records
    )

    if best_key is None:
        return [(accumulated_keys, sorted(block))]

    refined = []
    refined.extend(refine_block(
        group_with, hash_key_records,
        max_depth=max_depth,
        min_bucket_size=min_bucket_size,
        depth=depth + 1,
        accumulated_keys=accumulated_keys + (("+" + best_key),),
    ))
    refined.extend(refine_block(
        group_without, hash_key_records,
        max_depth=max_depth,
        min_bucket_size=min_bucket_size,
        depth=depth + 1,
        accumulated_keys=accumulated_keys + (("-" + best_key),),
    ))
    return refined


def run_phase_3(blocks_by_key_set, hash_key_records,
                max_depth=3, min_bucket_size=2):
    """
    Execute Phase 3 across all initial blocks.

    Returns:
      final_blocks : {block_label: [refID]}
    """
    final_blocks = {}
    block_idx = 0

    for parent_keys, members in blocks_by_key_set.items():
        leaves = refine_block(
            members, hash_key_records,
            max_depth=max_depth,
            min_bucket_size=min_bucket_size,
            accumulated_keys=tuple(parent_keys),
        )
        for split_keys, refIDs in leaves:
            label = split_keys if split_keys else (f"BLOCK_{block_idx}",)
            base = label
            suffix = 0
            while label in final_blocks:
                suffix += 1
                label = base + (f"#{suffix}",)
            final_blocks[label] = refIDs
            block_idx += 1

    print(f"[Phase 3] refined into {len(final_blocks)} final blocks "
          f"(max_depth={max_depth}, min_bucket_size={min_bucket_size})")

    return final_blocks
