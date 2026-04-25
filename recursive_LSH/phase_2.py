"""
Phase 2: Blocking Based on Merging Tokens

Group records by their hash-key sets to form initial blocks, then expose the
candidate pairs implied by each block.

Optionally use MinHash + LSH (datasketch) when ``use_lsh=True`` and the
package is available; otherwise fall back to exact bucketing on the full
hash-key set.

Outputs:
  - blocks_by_key      : {hash_key: [refID]}                 (per-key buckets)
  - blocks_by_key_set  : {tuple(hash_keys): [refID]}         (initial blocks)
  - candidate_pairs    : [(refID_a, refID_b)]
"""

from collections import defaultdict
from itertools import combinations


def blocks_by_individual_key(hash_key_records):
    """For each hash key, list the records that contain it."""
    blocks = defaultdict(list)
    for refID, keys in hash_key_records.items():
        for key in keys:
            blocks[key].append(refID)
    return dict(blocks)


def blocks_by_full_key_set(hash_key_records):
    """Group records that share an *identical* hash-key set."""
    blocks = defaultdict(list)
    for refID, keys in hash_key_records.items():
        blocks[tuple(keys)].append(refID)
    return dict(blocks)


def candidate_pairs_from_blocks(blocks):
    """All within-block pairs across the supplied blocks."""
    pairs = set()
    for refIDs in blocks.values():
        if len(refIDs) < 2:
            continue
        for a, b in combinations(sorted(refIDs), 2):
            pairs.add((a, b))
    return sorted(pairs)


def _lsh_blocks(hash_key_records, num_perm, lsh_threshold):
    """LSH-bucketed blocks. Requires the ``datasketch`` package."""
    from datasketch import MinHash, MinHashLSH

    lsh = MinHashLSH(threshold=lsh_threshold, num_perm=num_perm)
    minhashes = {}

    for refID, keys in hash_key_records.items():
        if not keys:
            continue
        m = MinHash(num_perm=num_perm)
        for key in keys:
            m.update(key.encode("utf-8"))
        minhashes[refID] = m
        lsh.insert(str(refID), m)

    bucket_to_refs = defaultdict(set)
    for refID, m in minhashes.items():
        members = tuple(sorted(lsh.query(m)))
        bucket_to_refs[members].add(refID)

    return {k: sorted(v) for k, v in bucket_to_refs.items()}


def run_phase_2(hash_key_records, use_lsh=False, num_perm=128,
                lsh_threshold=0.5):
    """Execute Phase 2 end-to-end."""
    by_key = blocks_by_individual_key(hash_key_records)

    if use_lsh:
        try:
            blocks_by_key_set = _lsh_blocks(
                hash_key_records, num_perm, lsh_threshold
            )
            mode = f"LSH (num_perm={num_perm}, threshold={lsh_threshold})"
        except ImportError:
            print("[Phase 2] datasketch not installed; falling back to exact bucketing")
            blocks_by_key_set = blocks_by_full_key_set(hash_key_records)
            mode = "exact (fallback)"
    else:
        blocks_by_key_set = blocks_by_full_key_set(hash_key_records)
        mode = "exact"

    candidate_pairs = candidate_pairs_from_blocks(blocks_by_key_set)

    print(f"[Phase 2] {len(by_key)} per-key buckets, "
          f"{len(blocks_by_key_set)} initial blocks ({mode}), "
          f"{len(candidate_pairs)} candidate pairs")

    return by_key, blocks_by_key_set, candidate_pairs
