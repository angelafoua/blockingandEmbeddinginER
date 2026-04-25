"""
Phase 1: Hashing Keys for Token Variations

For each group of token variations produced by Phase 0, assign a single
deterministic hash key. All variations of the same concept share the key.

Outputs:
  - token_hash_mapping : {token: hash_key}
  - hash_to_tokens     : {hash_key: set(tokens)}   (reverse mapping)
  - hash_key_records   : {refID: tuple(sorted hash keys)}
"""


def _build_groups(variations_dict):
    """
    Merge variation sets that share at least one token (union-find).
    Returns a list of disjoint groups (sets of tokens).
    """
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for token, variants in variations_dict.items():
        for v in variants | {token}:
            parent.setdefault(v, v)
        canonical = token
        for v in variants:
            union(canonical, v)

    groups = {}
    for token in parent:
        root = find(token)
        groups.setdefault(root, set()).add(token)

    return list(groups.values())


def build_token_hash_mapping(variations_dict, key_prefix="HASH"):
    """
    Assign each variation group a unique hash key.

    Returns (token_hash_mapping, hash_to_tokens).
    """
    groups = _build_groups(variations_dict)
    groups.sort(key=lambda g: sorted(g)[0])

    token_hash_mapping = {}
    hash_to_tokens = {}

    for idx, group in enumerate(groups, start=1):
        hash_key = f"{key_prefix}_{idx:05d}"
        hash_to_tokens[hash_key] = set(group)
        for token in group:
            token_hash_mapping[token] = hash_key

    return token_hash_mapping, hash_to_tokens


def records_to_hash_keys(refDict, token_hash_mapping):
    """Convert each record's tokens into a sorted tuple of hash keys."""
    hash_key_records = {}
    for refID, tokens in refDict.items():
        keys = {token_hash_mapping[t] for t in tokens if t in token_hash_mapping}
        hash_key_records[refID] = tuple(sorted(keys))
    return hash_key_records


def run_phase_1(refDict, variations_dict, key_prefix="HASH"):
    """Execute Phase 1 end-to-end."""
    token_hash_mapping, hash_to_tokens = build_token_hash_mapping(
        variations_dict, key_prefix=key_prefix
    )
    hash_key_records = records_to_hash_keys(refDict, token_hash_mapping)

    print(f"[Phase 1] {len(hash_to_tokens)} hash keys created from "
          f"{len(token_hash_mapping)} tokens")

    return token_hash_mapping, hash_to_tokens, hash_key_records
