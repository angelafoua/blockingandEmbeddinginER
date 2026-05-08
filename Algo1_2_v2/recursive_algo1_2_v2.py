"""Recursive blocking pipeline (algo1_2_v2).

Refactor notes:
- The legacy `stop_k` parameter conflated three independent knobs.
  They are now split into `init_df_max` (upper-bound DF cap for
  initial blocking tokens), `max_recursion_depth` (recursion ceiling),
  and `min_intra_freq` (lower-bound floor used by `refine_blocks`).
- The mode-of-record-length heuristic was replaced by a DF-percentile
  cutoff (`compute_init_df_cap`), in the same space as the cap it
  produces.
- Block-construction filters (`min_blk_token_len`, `exclude_numeric`)
  and the post-filter `min_block_size` are now CLI-tunable.
- Diagnostic counters and histograms are emitted at each gate so the
  effect of every parameter is observable.
- `--stop-k` and `--stop-k-factor` remain accepted as deprecated
  aliases.
"""

import build_tokenFreqDict
from refine_blocks import refine_blocks
import ast
import os
from pathlib import Path
import build_refDict


def load_dict(path_str):
    path = Path(path_str)
    with open(path, "r", encoding="utf-8") as f:
        return ast.literal_eval(f.read())


from statistics import mean, mode
from math import floor
import time


def compute_stop_k(refDict, factor=0.6):
    """Legacy heuristic: floor(factor * mode(record vocab size)).

    Retained for diagnostic comparison only; not used as the primary
    parameter source. The mode is unstable on integer-valued data and
    lives in record-length space, not in DF space.
    """
    token_lengths = [len(set(tokens)) for tokens in refDict.values()]
    mode_length = mode(token_lengths)
    stop_k = floor(factor * mode_length)
    print(f"[legacy] Mode token length: {mode_length}")
    print(f"[legacy] stop_k = floor({factor} * {mode_length}) = {stop_k}")
    return stop_k


def compute_init_df_cap(tokenFreqDict, percentile=0.95):
    """DF cap for initial blocking tokens.

    Operates directly on the document-frequency distribution, so it
    scales with corpus size and is robust to integer-mode instability.
    Returns the DF value at the given percentile of the sorted DF list,
    i.e. tokens with `freq <= cap` survive the upper-bound check.
    """
    if not tokenFreqDict:
        return 0
    freqs = sorted(tokenFreqDict.values())
    idx = min(int(len(freqs) * percentile), len(freqs) - 1)
    return freqs[idx]


def _percentiles(values, qs=(0.5, 0.9, 0.95, 0.99)):
    if not values:
        return {q: 0 for q in qs}
    s = sorted(values)
    n = len(s)
    return {q: s[min(int(q * n), n - 1)] for q in qs}


def recursive_blocking(depth, blocks, max_depth, min_intra_freq,
                       do_merge=True, do_purge=True, peak=None):
    """Recursive refinement loop.

    `depth` starts at 1 and increments. Each iteration calls
    `refine_blocks` with `max(depth, min_intra_freq)` so the
    intra-block frequency floor grows with depth but never drops
    below the configured floor.
    """
    effective_floor = max(depth, min_intra_freq)
    print(f"\n--- depth={depth}, effective min_intra_freq={effective_floor}, "
          f"max_depth={max_depth} (do_merge={do_merge}, do_purge={do_purge}) ---")
    print(f"Current number of blocks: {len(blocks)}")

    # Record the entry-state snapshot (covers the initial-blocks case at depth=1).
    if peak is not None and len(blocks) > peak["size"]:
        peak["size"] = len(blocks)
        peak["blocks"] = blocks
        peak["depth"] = depth - 1

    if depth > max_depth:
        print("Stopping: depth > max_recursion_depth")
        return blocks

    print(f"Calling refine_blocks with min_intra_freq={effective_floor}...")
    start_time = time.time()
    newBlocks = refine_blocks(blocks, effective_floor)
    refine_time = time.time() - start_time
    print(f"refine_blocks took {refine_time:.2f} seconds, produced "
          f"{len(newBlocks) if newBlocks else 0} blocks")

    if not newBlocks:
        print("Stopping: newBlocks is empty (refine produced nothing)")
        return blocks

    if do_merge:
        print(f"Merging blocks...")
        start_time = time.time()
        merged_blocks = merge_blocks(blocks, newBlocks)
        merge_time = time.time() - start_time
        print(f"merge_blocks took {merge_time:.2f} seconds, "
              f"result: {len(merged_blocks)} blocks")
    else:
        # Naive union: keep both, last-write-wins on key collision (no ref-set dedup)
        print(f"Skipping merge_blocks (do_merge=False); naive concat...")
        merged_blocks = {**blocks, **newBlocks}
        print(f"  result: {len(merged_blocks)} blocks")

    if do_purge:
        print(f"Purging subset blocks...")
        start_time = time.time()
        before = len(merged_blocks)
        merged_blocks = purge_subset_blocks(merged_blocks)
        purge_time = time.time() - start_time
        print(f"purge_subset_blocks took {purge_time:.2f} seconds, "
              f"dropped {before - len(merged_blocks)}, "
              f"result: {len(merged_blocks)} blocks")
    else:
        print(f"Skipping purge_subset_blocks (do_purge=False)")

    if peak is not None and len(merged_blocks) > peak["size"]:
        peak["size"] = len(merged_blocks)
        peak["blocks"] = merged_blocks
        peak["depth"] = depth

    return recursive_blocking(depth + 1, merged_blocks, max_depth,
                              min_intra_freq,
                              do_merge=do_merge, do_purge=do_purge,
                              peak=peak)


def merge_blocks(old_blocks, new_blocks):
    """Optimized merge using a single pass with hash-based deduplication."""
    ref_set_to_data = {}

    combined = {**old_blocks, **new_blocks}

    for key, refs in combined.items():
        ref_set = frozenset(refs.keys())

        if isinstance(key, tuple):
            key_tuple = key
        else:
            key_tuple = (key,)

        if ref_set not in ref_set_to_data:
            ref_set_to_data[ref_set] = (list(key_tuple), refs)
        else:
            existing_keys, _ = ref_set_to_data[ref_set]
            existing_keys.extend(key_tuple)

    merged = {}
    for ref_set, (key_list, refs) in ref_set_to_data.items():
        unique_keys = list(dict.fromkeys(key_list))

        if len(unique_keys) == 1:
            final_key = unique_keys[0]
        else:
            final_key = tuple(unique_keys)

        merged[final_key] = refs

    return merged


def purge_subset_blocks(blocks):
    """Lossless subset purging."""
    from collections import defaultdict

    block_keys = list(blocks.keys())
    block_id = {k: i for i, k in enumerate(block_keys)}
    block_size = [len(blocks[k]) for k in block_keys]

    ref_to_blocks = defaultdict(set)
    for i, k in enumerate(block_keys):
        for refID in blocks[k]:
            ref_to_blocks[refID].add(i)

    keep = {}
    for i, k in enumerate(block_keys):
        refs = blocks[k]
        if not refs:
            continue
        ref_iter = iter(refs)
        first = next(ref_iter)
        candidates = set(ref_to_blocks[first])
        for refID in ref_iter:
            candidates &= ref_to_blocks[refID]
            if len(candidates) == 1:
                break

        is_strict_subset = False
        for j in candidates:
            if j == i:
                continue
            if block_size[j] > block_size[i]:
                is_strict_subset = True
                break
            if block_size[j] == block_size[i] and j < i:
                is_strict_subset = True
                break

        if not is_strict_subset:
            keep[k] = refs

    return keep


def remove_high_frequency_tokens(refDict, tokenFreqDict, max_frequency=60):
    """Drop tokens whose document frequency exceeds max_frequency."""
    noisy = {t for t, f in tokenFreqDict.items() if f > max_frequency}
    cleaned = {refID: [t for t in tokens if t not in noisy]
               for refID, tokens in refDict.items()}
    return cleaned, noisy


def filter_top_k_smallest(blocks, k=3, min_block_size=2):
    """Per-record top-k smallest filter (Block Filtering, Papadakis et al.)."""
    from collections import defaultdict

    record_to_blocks = defaultdict(list)
    for key, refs in blocks.items():
        size = len(refs)
        for refID in refs:
            record_to_blocks[refID].append((size, key))

    keep = defaultdict(set)
    for refID, sized_keys in record_to_blocks.items():
        sized_keys.sort(key=lambda x: x[0])
        for _, key in sized_keys[:k]:
            keep[key].add(refID)

    result = {}
    for key, refs in blocks.items():
        kept_ids = keep.get(key, set())
        if len(kept_ids) < min_block_size:
            continue
        result[key] = {r: refs[r] for r in refs if r in kept_ids}
    return result


class UnionFind:
    def __init__(self, elements):
        self.parent = {e: e for e in elements}
        self.rank = {e: 0 for e in elements}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1

    def get_clusters(self):
        from collections import defaultdict
        clusters = defaultdict(list)
        for e in self.parent:
            clusters[self.find(e)].append(e)
        return list(clusters.values())


def build_arcs_graph(blocks, weighting="uniform", corpus_size=None,
                     max_block_pair_cost=None):
    """Build a weighted graph using ARCS scoring.

    For each block of size s containing N_corpus total records, every
    pair (A, B) in the block accumulates a contribution to its edge:

      weighting="uniform":  contribution = 1 / s
      weighting="idf":      contribution = log(N_corpus / s) / s

    Uniform is the original ARCS scoring; IDF additionally penalises
    generic (large) blocks by weighting each block's contribution by
    its inverse-document-frequency. Specific blocks (small s) dominate;
    generic blocks (large s) become near-zero.

    `max_block_pair_cost` is a compute guardrail used in
    redundancy-positive (full) blocking: any block whose pair count
    s*(s-1)/2 exceeds the cap is skipped. Its per-pair contribution
    would be ≤ 1/s anyway, near zero for large s.

    Returns {(refID_a, refID_b): weight} with refID_a < refID_b.
    """
    import math
    from collections import defaultdict
    edge_weights = defaultdict(float)

    n_skipped_too_big = 0
    pairs_skipped = 0

    for refs in blocks.values():
        ref_list = list(refs.keys())
        block_size = len(ref_list)
        if block_size < 2:
            continue
        n_pairs = block_size * (block_size - 1) // 2
        if max_block_pair_cost is not None and n_pairs > max_block_pair_cost:
            n_skipped_too_big += 1
            pairs_skipped += n_pairs
            continue
        if weighting == "idf":
            if corpus_size is None or corpus_size <= block_size:
                contribution = 0.0
            else:
                contribution = math.log(corpus_size / block_size) / block_size
        else:
            contribution = 1.0 / block_size
        if contribution == 0.0:
            continue
        for i in range(len(ref_list)):
            for j in range(i + 1, len(ref_list)):
                a, b = ref_list[i], ref_list[j]
                if a > b:
                    a, b = b, a
                edge_weights[(a, b)] += contribution

    if max_block_pair_cost is not None and n_skipped_too_big > 0:
        print(f"  [pair-cost guardrail] skipped {n_skipped_too_big} blocks "
              f"with >{max_block_pair_cost} pairs each "
              f"(total {pairs_skipped:,} pairs avoided)")

    return edge_weights


def _print_edge_histogram(edge_weights, n_buckets=10):
    if not edge_weights:
        print("  (no edges to histogram)")
        return
    weights = list(edge_weights.values())
    lo, hi = min(weights), max(weights)
    if lo == hi:
        print(f"  All {len(weights)} edges have weight {lo:.4f}")
        return
    width = (hi - lo) / n_buckets
    counts = [0] * n_buckets
    for w in weights:
        idx = min(int((w - lo) / width), n_buckets - 1)
        counts[idx] += 1
    print(f"  ARCS edge-weight histogram ({len(weights)} edges, "
          f"range [{lo:.4f}, {hi:.4f}]):")
    for i, c in enumerate(counts):
        bucket_lo = lo + i * width
        bucket_hi = bucket_lo + width
        print(f"    [{bucket_lo:.4f}, {bucket_hi:.4f}): {c}")


def _connected_components_from_edges(nodes, edges):
    """edges: iterable of (a, b). Returns list of components covering nodes."""
    from collections import defaultdict
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    visited = set()
    comps = []
    for n in nodes:
        if n in visited:
            continue
        stack = [n]
        comp = []
        while stack:
            x = stack.pop()
            if x in visited:
                continue
            visited.add(x)
            comp.append(x)
            for y in adj[x]:
                if y not in visited:
                    stack.append(y)
        comps.append(comp)
    return comps


def _split_cluster_by_density(cluster, internal_edges,
                              density_floor, min_size):
    """Recursively split a cluster if its internal edge density is below
    `density_floor`. `internal_edges` is a list of (w, a, b) tuples,
    only edges within `cluster`. Splitting works by greedily removing
    the lightest edge until the cluster disconnects, then recursing on
    each new component using only its surviving edges.
    """
    n = len(cluster)
    if n < min_size:
        return [cluster]

    max_edges = n * (n - 1) // 2
    density = len(internal_edges) / max_edges if max_edges > 0 else 1.0
    if density >= density_floor or not internal_edges:
        return [cluster]

    sorted_edges = sorted(internal_edges, key=lambda x: x[0])
    for i in range(len(sorted_edges)):
        surviving = sorted_edges[i + 1:]
        comps = _connected_components_from_edges(
            cluster, [(a, b) for _, a, b in surviving]
        )
        if len(comps) > 1:
            result = []
            for comp in comps:
                comp_set = set(comp)
                comp_edges = [(w, a, b) for (w, a, b) in surviving
                              if a in comp_set and b in comp_set]
                result.extend(_split_cluster_by_density(
                    comp, comp_edges, density_floor, min_size
                ))
            return result

    return [cluster]


def cluster_records(blocks, all_refIDs, tau=1.0, weighting="uniform",
                    density_floor=0.0, density_min_size=3,
                    max_block_pair_cost=None):
    """Build ARCS graph, prune edges below tau, return clusters via Union-Find.
    If `density_floor > 0`, post-process clusters by splitting any whose
    internal edge density falls below the floor (helps resist
    transitive-closure chain collapse).
    """
    print(f"\nBuilding ARCS weighted graph (weighting={weighting})...")
    start = time.time()
    edge_weights = build_arcs_graph(blocks, weighting=weighting,
                                    corpus_size=len(all_refIDs),
                                    max_block_pair_cost=max_block_pair_cost)
    print(f"  Graph built in {time.time() - start:.2f}s — {len(edge_weights)} edges")

    _print_edge_histogram(edge_weights)

    uf = UnionFind(all_refIDs)
    kept = 0
    for (a, b), w in edge_weights.items():
        if w >= tau:
            uf.union(a, b)
            kept += 1
    print(f"  Edges kept (weight >= {tau}): {kept} / {len(edge_weights)}")

    clusters = uf.get_clusters()
    multi = [c for c in clusters if len(c) > 1]
    singletons = [c for c in clusters if len(c) == 1]
    print(f"  Clusters (pre-density): {len(multi)} multi-record, "
          f"{len(singletons)} singletons")

    if density_floor > 0.0:
        print(f"  Density floor {density_floor} applied to clusters of "
              f"size >= {density_min_size}...")
        kept_edges = {(a, b): w for (a, b), w in edge_weights.items()
                      if w >= tau}
        new_clusters = []
        n_split = 0
        n_pieces_added = 0
        for c in clusters:
            if len(c) < density_min_size:
                new_clusters.append(c)
                continue
            cset = set(c)
            internal = [(w, a, b) for (a, b), w in kept_edges.items()
                        if a in cset and b in cset]
            pieces = _split_cluster_by_density(
                c, internal, density_floor, density_min_size
            )
            if len(pieces) > 1:
                n_split += 1
                n_pieces_added += len(pieces) - 1
            new_clusters.extend(pieces)
        clusters = new_clusters
        multi = [c for c in clusters if len(c) > 1]
        singletons = [c for c in clusters if len(c) == 1]
        print(f"  Split {n_split} low-density clusters into "
              f"{n_split + n_pieces_added} pieces")
        print(f"  Clusters (post-density): {len(multi)} multi-record, "
              f"{len(singletons)} singletons")

    return clusters


def blocking(refDict, tokenFreqDict, init_df_max,
             min_blk_token_len=4, exclude_numeric_blocks=True,
             full_blocking=False):
    """Select blocking tokens.

    Default mode keeps token `t` as a blocking key for record `r` iff:
      - len(t) >= min_blk_token_len
      - t is not pure-digit (when exclude_numeric_blocks is True)
      - 2 <= tokenFreqDict[t] <= init_df_max

    With `full_blocking=True`, the redundancy-positive (Papadakis) regime
    applies: every token surviving stop-word removal becomes a block as
    long as `tokenFreqDict[t] >= 2`. Length, numeric, and DF-cap filters
    are bypassed; ARCS reciprocal weighting + the build_arcs_graph
    pair-cost guardrail handle giant blocks downstream.
    """
    from collections import defaultdict
    blocks = defaultdict(dict)

    if full_blocking:
        print("Blocking mode: FULL (Papadakis redundancy-positive). "
              "Length / numeric / DF-cap filters are disabled; "
              "only freq >= 2 enforced.")
    else:
        print(f"Blocking filters: min_blk_token_len={min_blk_token_len}, "
              f"exclude_numeric_blocks={exclude_numeric_blocks}, "
              f"freq window=[2, {init_df_max}]")

    n_too_short = 0
    n_numeric = 0
    n_freq_too_low = 0
    n_freq_too_high = 0
    n_kept = 0

    for key, tokenList in refDict.items():
        tokenSet = set(tokenList)
        for token in tokenSet:
            if not full_blocking:
                if len(token) < min_blk_token_len:
                    n_too_short += 1
                    continue
                if exclude_numeric_blocks and token.isdigit():
                    n_numeric += 1
                    continue
            freq = tokenFreqDict[token]
            if freq < 2:
                n_freq_too_low += 1
                continue
            if not full_blocking and freq > init_df_max:
                n_freq_too_high += 1
                continue
            blocks[token][key] = tokenSet
            n_kept += 1

    print(f"Blocking gate counters (per-record token instances):")
    if not full_blocking:
        print(f"  too_short (< {min_blk_token_len}): {n_too_short}")
        print(f"  numeric (excluded):                {n_numeric}")
    print(f"  freq < 2:                          {n_freq_too_low}")
    if not full_blocking:
        print(f"  freq > {init_df_max}:                       {n_freq_too_high}")
    print(f"  kept (became block memberships):   {n_kept}")
    print(f"  unique blocking keys produced:     {len(blocks)}")

    return blocks


def hierarchical_blocking(refDict, tokenFreqDict, all_refIDs,
                          progress_every=1000):
    """Hierarchical, global-DF-ordered binary partitioning.

    Sort tokens by DF descending (ties broken alphabetically). Start from
    one universe block keyed by (). At each level, split every current
    frontier block into (with-T, without-T); keep both halves. The token
    is the same for every frontier block at a given level. Every block
    produced at every level — root, internal nodes, and leaves — is
    accumulated and returned as the entire tree.

    Singleton frontier blocks and frontier blocks whose records all share
    (or all lack) the current token are carried forward unchanged at the
    frontier and are not re-emitted into the accumulator (already there
    from the prior level).

    Returns Dict[Hashable, Dict[refID, set]] matching the contract
    expected by filter_top_k_smallest and cluster_records. Keys are
    tuples of (token, 1|0) pairs recording the path from the root; the
    universe block uses key ().
    """
    sorted_tokens = sorted(
        tokenFreqDict.keys(),
        key=lambda t: (-tokenFreqDict[t], t),
    )
    n_tokens = len(sorted_tokens)
    print(f"Hierarchical blocking: {n_tokens} tokens, "
          f"starting from 1 universe block of {len(all_refIDs)} records")

    universe_refs = {refID: set(refDict[refID]) for refID in all_refIDs}
    root_key = ()
    all_blocks = {root_key: universe_refs}
    frontier = {root_key: universe_refs}

    for level, token in enumerate(sorted_tokens, 1):
        new_frontier = {}
        n_split = 0
        n_carry_singleton = 0
        n_carry_no_partition = 0
        for key, refs in frontier.items():
            if len(refs) <= 1:
                new_frontier[key] = refs
                n_carry_singleton += 1
                continue
            with_t = {r: ts for r, ts in refs.items() if token in ts}
            without_t = {r: ts for r, ts in refs.items() if token not in ts}
            if not with_t or not without_t:
                new_frontier[key] = refs
                n_carry_no_partition += 1
                continue
            yes_key = key + ((token, 1),)
            no_key = key + ((token, 0),)
            new_frontier[yes_key] = with_t
            new_frontier[no_key] = without_t
            all_blocks[yes_key] = with_t
            all_blocks[no_key] = without_t
            n_split += 1
        frontier = new_frontier

        if level <= 5 or level % progress_every == 0 or level == n_tokens:
            sizes = [len(r) for r in frontier.values()]
            max_size = max(sizes) if sizes else 0
            n_singleton = sum(1 for s in sizes if s == 1)
            print(f"  level {level}/{n_tokens} (token='{token}', "
                  f"DF={tokenFreqDict[token]}): "
                  f"frontier={len(frontier)} "
                  f"(split={n_split}, carry_singleton={n_carry_singleton}, "
                  f"carry_no_partition={n_carry_no_partition}), "
                  f"tree={len(all_blocks)}, max_size={max_size}, "
                  f"singletons={n_singleton}")

    print(f"Hierarchical blocking finished: {len(all_blocks)} total blocks "
          f"across the tree (frontier at last level: {len(frontier)})")
    return all_blocks


def candidate_pairs(blocks):
    """Total number of intra-block pairs across all blocks (with multiplicity)."""
    return sum((len(refs) * (len(refs) - 1)) // 2 for refs in blocks.values())


def dump_clusters_json(clusters, original_refDict, out_path,
                       include_singletons=True, metadata=None):
    """Write cluster composition to a JSON file.

    Each cluster is assigned an integer `cluster_id` after sorting by
    size descending (so cluster 0 is the largest). Each record carries
    its full token list from the ORIGINAL refDict (pre stop-word
    removal), so all elements of the record are present.
    """
    import json
    from pathlib import Path

    sized = sorted(clusters, key=lambda c: (-len(c), c[0] if c else ""))
    payload_clusters = []
    for cid, members in enumerate(sized):
        if not include_singletons and len(members) <= 1:
            continue
        records = []
        for refID in members:
            tokens = original_refDict.get(refID, [])
            records.append({"refID": refID, "tokens": list(tokens)})
        payload_clusters.append({
            "cluster_id": cid,
            "size": len(members),
            "records": records,
        })

    payload = {
        "metadata": metadata or {},
        "n_clusters": len(payload_clusters),
        "clusters": payload_clusters,
    }

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {len(payload_clusters)} clusters to {out_path}")


def _path_with_config_suffix(base_path, do_merge, do_purge):
    """Insert merge/purge suffix before the file extension."""
    from pathlib import Path
    p = Path(base_path)
    suffix = f"_m{int(do_merge)}_p{int(do_purge)}"
    return p.with_name(p.stem + suffix + p.suffix)


def _import_er_metrics():
    """Import er_metrics from the repo root (one level above Algo1_2_v2/)."""
    import sys
    from pathlib import Path
    try:
        import er_metrics
        return er_metrics
    except ImportError:
        parent = str(Path(__file__).resolve().parent.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        import er_metrics
        return er_metrics


def compute_run_metrics(clusters, all_refIDs, truth_file_path=None,
                        config=None, timings=None):
    """Compute summary + (optional) ground-truth metrics for a clustering.

    Returns a dict with: record counts, predicted-cluster size distribution,
    and — if `truth_file_path` is provided — pair-based P/R/F1 plus the
    truth-cluster size distribution and L1 distance between distributions.
    """
    from collections import Counter
    import statistics

    sizes = sorted([len(c) for c in clusters], reverse=True)
    size_dist = dict(Counter(sizes))
    metrics = {
        "config": config or {},
        "n_records_total": len(all_refIDs),
        "n_unique_records": len(set(all_refIDs)),
        "predicted_clusters": {
            "n_total": len(clusters),
            "n_multi": sum(1 for s in sizes if s > 1),
            "n_singletons": sum(1 for s in sizes if s == 1),
            "min_size": min(sizes) if sizes else 0,
            "max_size": max(sizes) if sizes else 0,
            "mean_size": round(statistics.mean(sizes), 3) if sizes else 0,
            "median_size": statistics.median(sizes) if sizes else 0,
            "size_distribution": {str(k): v for k, v in
                                  sorted(size_dist.items())},
        },
    }

    if truth_file_path:
        er_metrics = _import_er_metrics()
        truth = er_metrics.load_truth(truth_file_path)
        all_set = set(all_refIDs)
        truth_clusters = {}
        for ref, tid in truth.items():
            if ref in all_set:
                truth_clusters.setdefault(tid, []).append(ref)
        truth_sizes = sorted([len(v) for v in truth_clusters.values()],
                             reverse=True)
        truth_dist = dict(Counter(truth_sizes))

        # Pair-based metrics: convert cluster list to {cid: [refIDs]}
        cluster_blocks = {i: c for i, c in enumerate(clusters)}
        pair = er_metrics.compute_metrics(cluster_blocks, truth_file_path,
                                          verbose=False)

        all_sizes = set(size_dist) | set(truth_dist)
        l1 = sum(abs(size_dist.get(s, 0) - truth_dist.get(s, 0))
                 for s in all_sizes)

        metrics["truth_clusters"] = {
            "truth_file": truth_file_path,
            "n_total": len(truth_clusters),
            "min_size": min(truth_sizes) if truth_sizes else 0,
            "max_size": max(truth_sizes) if truth_sizes else 0,
            "mean_size": round(statistics.mean(truth_sizes), 3)
                         if truth_sizes else 0,
            "median_size": statistics.median(truth_sizes)
                           if truth_sizes else 0,
            "size_distribution": {str(k): v for k, v in
                                  sorted(truth_dist.items())},
        }
        metrics["pair_metrics"] = pair
        metrics["size_distribution_l1"] = l1
        metrics["cluster_count_diff"] = len(clusters) - len(truth_clusters)

    if timings:
        metrics["timings_seconds"] = {k: round(v, 3) for k, v in timings.items()}

    return metrics


def write_metrics_files(metrics, clusters_out_path):
    """Write structured `.metrics.json` and human-readable `.metrics.log`
    next to the clusters JSON."""
    import json
    from pathlib import Path

    base = Path(clusters_out_path)
    json_path = base.with_name(base.stem + ".metrics.json")
    log_path = base.with_name(base.stem + ".metrics.log")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    lines = []
    lines.append("=" * 72)
    lines.append("  RUN METRICS")
    lines.append("=" * 72)

    cfg = metrics.get("config", {})
    if cfg:
        lines.append("\n[Configuration]")
        for k, v in cfg.items():
            lines.append(f"  {k:<24} = {v}")

    lines.append("\n[Records]")
    lines.append(f"  total                    = {metrics['n_records_total']}")
    lines.append(f"  unique                   = {metrics['n_unique_records']}")

    pc = metrics["predicted_clusters"]
    lines.append("\n[Predicted Clusters]")
    lines.append(f"  total                    = {pc['n_total']}")
    lines.append(f"  multi-record             = {pc['n_multi']}")
    lines.append(f"  singletons               = {pc['n_singletons']}")
    lines.append(f"  size  min / max          = {pc['min_size']} / {pc['max_size']}")
    lines.append(f"  size  mean / median      = {pc['mean_size']} / {pc['median_size']}")
    lines.append("  size distribution (size: count):")
    for s, n in sorted(pc["size_distribution"].items(), key=lambda x: int(x[0])):
        lines.append(f"    size {int(s):>3} : {n}")

    if "truth_clusters" in metrics:
        tc = metrics["truth_clusters"]
        lines.append(f"\n[Truth Clusters]  ({tc['truth_file']})")
        lines.append(f"  total                    = {tc['n_total']}")
        lines.append(f"  size  min / max          = {tc['min_size']} / {tc['max_size']}")
        lines.append(f"  size  mean / median      = {tc['mean_size']} / {tc['median_size']}")
        lines.append("  size distribution (size: count):")
        for s, n in sorted(tc["size_distribution"].items(),
                           key=lambda x: int(x[0])):
            lines.append(f"    size {int(s):>3} : {n}")

        lines.append("\n[Distribution Match]")
        lines.append(f"  cluster count diff       = {metrics['cluster_count_diff']}  "
                     f"(predicted - truth)")
        lines.append(f"  size-distribution L1     = {metrics['size_distribution_l1']}")

        p = metrics["pair_metrics"]
        lines.append("\n[Pair-based Metrics]")
        lines.append(f"  TP                       = {p['TP']}")
        lines.append(f"  FP                       = {p['FP']}")
        lines.append(f"  FN                       = {p['FN']}")
        lines.append(f"  Linked Pairs (L)         = {p['L']}")
        lines.append(f"  Expected Pairs (E)       = {p['E']}")
        lines.append(f"  Precision                = {p['precision']}")
        lines.append(f"  Recall                   = {p['recall']}")
        lines.append(f"  F1                       = {p['f1']}")

    if "timings_seconds" in metrics:
        lines.append("\n[Timings (seconds)]")
        for k, v in metrics["timings_seconds"].items():
            lines.append(f"  {k:<24} = {v}")

    lines.append("\n" + "=" * 72)

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"  Wrote metrics JSON to {json_path}")
    print(f"  Wrote metrics log  to {log_path}")


def run_pipeline(initial_blocks, max_recursion_depth, min_intra_freq,
                 all_refIDs, do_merge, do_purge,
                 top_k=3, tau=1.0, min_block_size=2, cluster_on="final",
                 arcs_weighting="uniform",
                 density_floor=0.0, density_min_size=3,
                 original_refDict=None, clusters_json_path=None,
                 single_run=False, include_singletons=True,
                 truth_file_path=None, write_metrics=True,
                 max_block_pair_cost=None,
                 hierarchical=False, blocking_mode="default"):
    """Run recursive blocking + filter + clustering with given ablation flags.

    When hierarchical=True, `initial_blocks` is treated as already-final
    (the full hierarchical tree). recursive_blocking, merge_blocks, and
    purge_subset_blocks are skipped; do_merge / do_purge / max_recursion_depth
    / min_intra_freq are ignored.
    """
    import copy, tracemalloc

    if hierarchical:
        label = f"mode=hierarchical"
    else:
        label = f"merge={do_merge}, purge={do_purge}"
    print(f"\n{'#' * 70}\n# RUN: {label}\n{'#' * 70}")

    blocks_in = copy.deepcopy(initial_blocks)

    tracemalloc.start()
    t0 = time.time()
    if hierarchical:
        final_blocks = blocks_in
        peak = {"blocks": final_blocks, "size": len(final_blocks), "depth": 0}
        t_recursive = time.time() - t0
        print(f"\nHierarchical mode: {len(final_blocks)} blocks already "
              f"produced upstream; recursion / merge / purge skipped.")
    else:
        peak = {"blocks": blocks_in, "size": len(blocks_in), "depth": 0}
        final_blocks = recursive_blocking(1, blocks_in, max_recursion_depth,
                                          min_intra_freq,
                                          do_merge=do_merge, do_purge=do_purge,
                                          peak=peak)
        t_recursive = time.time() - t0
        print(f"\nPeak block count during recursion: {peak['size']} "
              f"(at depth={peak['depth']})")

    if cluster_on == "peak" and not hierarchical:
        print(f"Clustering on PEAK snapshot ({peak['size']} blocks)")
        blocks_for_cluster = peak["blocks"]
    else:
        print(f"Clustering on FINAL snapshot ({len(final_blocks)} blocks)")
        blocks_for_cluster = final_blocks

    n_blocks_post_recursive = len(blocks_for_cluster)
    pairs_post_recursive = candidate_pairs(blocks_for_cluster)

    t0 = time.time()
    blocks_for_cluster = filter_top_k_smallest(blocks_for_cluster, k=top_k,
                                               min_block_size=min_block_size)
    t_filter = time.time() - t0

    t0 = time.time()
    clusters = cluster_records(blocks_for_cluster, all_refIDs, tau=tau,
                               weighting=arcs_weighting,
                               density_floor=density_floor,
                               density_min_size=density_min_size,
                               max_block_pair_cost=max_block_pair_cost)
    t_cluster = time.time() - t0

    final_blocks = blocks_for_cluster

    meta = {
        "blocking_mode": blocking_mode,
        "do_merge": do_merge,
        "do_purge": do_purge,
        "max_recursion_depth": max_recursion_depth,
        "min_intra_freq": min_intra_freq,
        "top_k": top_k,
        "tau": tau,
        "min_block_size": min_block_size,
        "cluster_on": cluster_on,
        "arcs_weighting": arcs_weighting,
        "density_floor": density_floor,
        "density_min_size": density_min_size,
    }

    out_path = None
    if clusters_json_path is not None and original_refDict is not None:
        out_path = (clusters_json_path if single_run
                    else _path_with_config_suffix(clusters_json_path,
                                                  do_merge, do_purge))
        dump_clusters_json(clusters, original_refDict, out_path,
                           include_singletons=include_singletons,
                           metadata=meta)

    if write_metrics and out_path is not None:
        timings = {
            "recursive": t_recursive,
            "filter": t_filter,
            "cluster": t_cluster,
        }
        run_metrics = compute_run_metrics(
            clusters, all_refIDs,
            truth_file_path=truth_file_path,
            config=meta, timings=timings,
        )
        write_metrics_files(run_metrics, out_path)

    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "label": label,
        "do_merge": do_merge,
        "do_purge": do_purge,
        "blocks_post_recursive": n_blocks_post_recursive,
        "pairs_post_recursive": pairs_post_recursive,
        "blocks_post_filter": len(final_blocks),
        "pairs_post_filter": candidate_pairs(final_blocks),
        "clusters_total": len(clusters),
        "clusters_multi": sum(1 for c in clusters if len(c) > 1),
        "clusters_singletons": sum(1 for c in clusters if len(c) == 1),
        "time_recursive_s": t_recursive,
        "time_filter_s": t_filter,
        "time_cluster_s": t_cluster,
        "peak_mem_mb": peak_mem / (1024 * 1024),
    }


def _parse_args():
    import argparse
    p = argparse.ArgumentParser(
        description="Recursive blocking pipeline (algo1_2_v2). "
                    "With no merge/purge flags, runs the 4-way ablation; "
                    "with --no-merge or --no-purge, runs a single config."
    )
    p.add_argument("--input", default="S12PX.txt",
                   help="Input file for build_refDict.tokenizeInput.")
    p.add_argument("--max-freq", type=int, default=60,
                   help="Drop tokens with document frequency > this value "
                        "(stop-word pre-filter, applied to refDict).")

    # New, role-separated parameters.
    p.add_argument("--init-df-max", type=int, default=None,
                   help="Upper-bound DF cap for initial blocking tokens. "
                        "If unset, derived from --init-df-percentile.")
    p.add_argument("--init-df-percentile", type=float, default=0.95,
                   help="Percentile of tokenFreqDict used to derive "
                        "init_df_max when --init-df-max is unset.")
    p.add_argument("--max-recursion-depth", type=int, default=5,
                   help="Maximum number of recursion levels.")
    p.add_argument("--min-intra-freq", type=int, default=2,
                   help="Lower-bound floor on intra-block token frequency "
                        "passed to refine_blocks. Effective floor at depth d "
                        "is max(d, this).")
    p.add_argument("--min-blk-token-len", type=int, default=4,
                   help="Minimum length of a token to qualify as a blocking key.")
    p.add_argument("--include-numeric", action="store_true",
                   help="Include pure-digit tokens as blocking keys "
                        "(default: excluded). Ignored when --full-blocking "
                        "is set (numerics are always included in that mode).")
    p.add_argument("--full-blocking", action="store_true",
                   help="Redundancy-positive (Papadakis) blocking mode: "
                        "every token surviving stop-word removal becomes a "
                        "block as long as its DF >= 2. Disables length, "
                        "numeric, and DF-cap filters in blocking(). Pair with "
                        "--max-block-pair-cost to cap compute on huge blocks.")
    p.add_argument("--hierarchical-blocking", action="store_true",
                   help="Hierarchical blocking mode: sort all tokens by global "
                        "DF (descending), and at each level split every "
                        "frontier block into (with-token, without-token). The "
                        "entire tree (root + internal nodes + leaves) is "
                        "returned and feeds clustering. Bypasses blocking()'s "
                        "DF / length / numeric filters; bypasses refine_blocks; "
                        "forces single-config run with merge/purge skipped. "
                        "Mutually exclusive with --full-blocking.")
    p.add_argument("--max-block-pair-cost", type=int, default=None,
                   help="Compute guardrail for build_arcs_graph: skip any "
                        "block whose pair count |B|*(|B|-1)/2 exceeds this "
                        "value. Recommended ~100000 with --full-blocking. "
                        "Skipped blocks contribute <= 1/|B| per pair anyway.")
    p.add_argument("--min-block-size", type=int, default=2,
                   help="Drop blocks smaller than this after top-k filtering.")

    # Legacy / deprecated.
    p.add_argument("--stop-k", type=int, default=None,
                   help="[DEPRECATED] Legacy combined parameter. Sets "
                        "init_df_max, max_recursion_depth, and (implicitly) "
                        "min_intra_freq=2 all at once.")
    p.add_argument("--stop-k-factor", type=float, default=None,
                   help="[DEPRECATED] Computes K = floor(F * mode(record "
                        "vocab size)) and applies as --stop-k=K.")

    p.add_argument("--no-merge", action="store_true",
                   help="Disable merge_blocks; triggers single-config run.")
    p.add_argument("--no-purge", action="store_true",
                   help="Disable purge_subset_blocks; triggers single-config run.")
    p.add_argument("--tau", type=float, default=0.2,
                   help="ARCS edge-weight threshold for clustering. "
                        "Note: scale depends on --arcs-weighting (uniform "
                        "weights live in [0, ~1]; idf weights live in "
                        "[0, log(N)] where N is corpus size).")
    p.add_argument("--arcs-weighting", choices=["uniform", "idf"],
                   default="uniform",
                   help="ARCS contribution per shared block. "
                        "'uniform' = 1/|B| (original); "
                        "'idf' = log(N/|B|) / |B| (down-weights generic "
                        "blocks, sharpens precision). Re-tune --tau when "
                        "switching modes.")
    p.add_argument("--density-floor", type=float, default=0.0,
                   help="Post-process: split any cluster whose internal "
                        "edge density (kept-edges / max-possible-edges) "
                        "is below this floor. 0.0 disables splitting. "
                        "Useful values: 0.3-0.5. Pair with a lowered "
                        "--tau to reduce singletons without chain "
                        "collapse.")
    p.add_argument("--density-min-size", type=int, default=3,
                   help="Only consider density splitting for clusters of "
                        "at least this size.")
    p.add_argument("--top-k", type=int, default=3,
                   help="Per-record top-k smallest-block filter.")
    p.add_argument("--cluster-on", choices=["peak", "final"], default="final",
                   help="Which recursion snapshot feeds clustering: the "
                        "final state (default) or the peak-block-count state.")
    p.add_argument("--clusters-json", default="clusters.json",
                   help="Path to write cluster composition (cluster_id -> "
                        "records with their full token list). In ablation "
                        "mode, '_m{0,1}_p{0,1}' is appended per config. "
                        "Set to empty string to disable.")
    p.add_argument("--no-singletons-json", action="store_true",
                   help="Exclude singleton clusters from the JSON dump.")
    p.add_argument("--truth-file", default=None,
                   help="Path to truth CSV (refID,truthID). If unset, "
                        "auto-detected from --input via "
                        "er_metrics.detect_truth_file (looks in --truth-dir).")
    p.add_argument("--truth-dir", default="..",
                   help="Directory containing truthABC*.txt files when "
                        "--truth-file is auto-detected. Default: parent dir.")
    p.add_argument("--no-metrics", action="store_true",
                   help="Skip metrics computation and .metrics.{json,log} output.")
    return p.parse_args()


def _resolve_legacy_args(args, refDict, tokenFreqDict):
    """Map deprecated --stop-k / --stop-k-factor onto the new params.

    Returns (init_df_max, max_recursion_depth, min_intra_freq) with
    legacy overrides applied if present.
    """
    legacy_k = None
    if args.stop_k_factor is not None:
        print(f"\n[DEPRECATED] --stop-k-factor={args.stop_k_factor} given. "
              f"Computing legacy K = floor(factor * mode(record vocab size)).")
        legacy_k = compute_stop_k(refDict, factor=args.stop_k_factor)
    if args.stop_k is not None:
        print(f"\n[DEPRECATED] --stop-k={args.stop_k} given; overrides factor.")
        legacy_k = args.stop_k

    if legacy_k is not None:
        print(f"[DEPRECATED] Mapping legacy K={legacy_k} -> "
              f"init_df_max={legacy_k}, max_recursion_depth={legacy_k}, "
              f"min_intra_freq=2.")
        return legacy_k, legacy_k, 2

    # New path.
    if args.init_df_max is not None:
        init_df_max = args.init_df_max
        print(f"init_df_max set explicitly: {init_df_max}")
    else:
        init_df_max = compute_init_df_cap(tokenFreqDict,
                                          percentile=args.init_df_percentile)
        print(f"init_df_max derived from percentile "
              f"{args.init_df_percentile}: {init_df_max}")

    return init_df_max, args.max_recursion_depth, args.min_intra_freq


if __name__ == "__main__":
    args = _parse_args()

    if args.hierarchical_blocking and args.full_blocking:
        raise SystemExit(
            "Error: --hierarchical-blocking and --full-blocking are mutually "
            "exclusive."
        )

    print("Starting...")
    refDict = build_refDict.tokenizeInput(args.input)
    print(f"Loaded {len(refDict)} records")

    # Preserve the original tokenization (pre stop-word removal) so the
    # clusters JSON dump can include all elements of each record.
    original_refDict = {k: list(v) for k, v in refDict.items()}

    tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)
    print(f"Built token frequency dict with {len(tokenFreqDict)} unique tokens")

    refDict, removed = remove_high_frequency_tokens(refDict, tokenFreqDict,
                                                   max_frequency=args.max_freq)
    print(f"Stop-word removal: dropped {len(removed)} tokens with freq > {args.max_freq}")
    print(f"  Examples: {sorted(removed, key=lambda t: -tokenFreqDict[t])[:15]}")
    tokenFreqDict = build_tokenFreqDict.buildTokenFreqDict(refDict)
    print(f"Rebuilt token frequency dict: {len(tokenFreqDict)} unique tokens remain")

    # Diagnostics: where does the chosen DF cap sit relative to the corpus?
    df_pct = _percentiles(list(tokenFreqDict.values()))
    rec_lens = [len(set(t)) for t in refDict.values()]
    rl_pct = _percentiles(rec_lens)
    print("\nDF distribution percentiles (post-cleanup):")
    print(f"  p50={df_pct[0.5]}, p90={df_pct[0.9]}, "
          f"p95={df_pct[0.95]}, p99={df_pct[0.99]}")
    print("Record-length percentiles (distinct tokens, post-cleanup):")
    print(f"  p50={rl_pct[0.5]}, p90={rl_pct[0.9]}, "
          f"p95={rl_pct[0.95]}, p99={rl_pct[0.99]}")

    all_refIDs = list(refDict.keys())

    if args.hierarchical_blocking:
        blocking_mode = "hierarchical"
        # Hierarchical mode owns the whole pipeline up to clustering;
        # init_df_max / max_recursion_depth / min_intra_freq are unused.
        init_df_max = None
        max_recursion_depth = 0
        min_intra_freq = 0

        print(f"\nResolved parameters (hierarchical mode):")
        print(f"  n_levels            = {len(tokenFreqDict)} "
              f"(== unique tokens after stop-word removal)")
        print(f"  min_block_size      = {args.min_block_size}")
        print(f"  top_k               = {args.top_k}")
        print(f"  tau                 = {args.tau}")
        print(f"  arcs_weighting      = {args.arcs_weighting}")
        print(f"  density_floor       = {args.density_floor} "
              f"(min_size={args.density_min_size})")
        print(f"  cluster_on          = final (forced)")

        print("\nBuilding hierarchical block tree...")
        initial_blocks = hierarchical_blocking(refDict, tokenFreqDict,
                                               all_refIDs)
        print(f"Hierarchical tree blocks: {len(initial_blocks)}")

        single_run = True
        configs = [(False, False)]
    else:
        blocking_mode = "full" if args.full_blocking else "default"
        init_df_max, max_recursion_depth, min_intra_freq = _resolve_legacy_args(
            args, refDict, tokenFreqDict)

        # For comparison logging only, also show the legacy heuristic's value.
        legacy_diag = compute_stop_k(refDict, factor=0.6)
        print(f"[diagnostic] Legacy heuristic stop_k(factor=0.6) = {legacy_diag} "
              f"(not used unless --stop-k* given)")

        print(f"\nResolved parameters:")
        print(f"  init_df_max         = {init_df_max}")
        print(f"  max_recursion_depth = {max_recursion_depth}")
        print(f"  min_intra_freq      = {min_intra_freq}")
        print(f"  min_blk_token_len   = {args.min_blk_token_len}")
        print(f"  exclude_numeric     = {not args.include_numeric}")
        print(f"  min_block_size      = {args.min_block_size}")
        print(f"  top_k               = {args.top_k}")
        print(f"  tau                 = {args.tau}")
        print(f"  arcs_weighting      = {args.arcs_weighting}")
        print(f"  density_floor       = {args.density_floor} "
              f"(min_size={args.density_min_size})")
        print(f"  cluster_on          = {args.cluster_on}")

        print("\nCreating initial blocks...")
        initial_blocks = blocking(
            refDict, tokenFreqDict, init_df_max=init_df_max,
            min_blk_token_len=args.min_blk_token_len,
            exclude_numeric_blocks=not args.include_numeric,
            full_blocking=args.full_blocking,
        )
        print(f"Initial blocks created: {len(initial_blocks)}")

        single_run = args.no_merge or args.no_purge
        if single_run:
            configs = [(not args.no_merge, not args.no_purge)]
        else:
            configs = [
                (True,  True),   # V0 baseline
                (True,  False),  # V1 no purge
                (False, True),   # V2 no merge
                (False, False),  # V3 neither
            ]

    clusters_json_path = args.clusters_json or None

    # Resolve truth file (explicit > auto-detect by --input filename).
    truth_file_path = None
    if not args.no_metrics:
        if args.truth_file:
            truth_file_path = args.truth_file
            if not os.path.exists(truth_file_path):
                print(f"[metrics] WARNING: --truth-file '{truth_file_path}' "
                      f"not found; metrics will be computed without truth.")
                truth_file_path = None
        else:
            try:
                er_metrics_mod = _import_er_metrics()
                detected = er_metrics_mod.detect_truth_file(
                    args.input, truth_dir=args.truth_dir)
                if detected and os.path.exists(detected):
                    truth_file_path = detected
                    print(f"[metrics] Auto-detected truth file: {truth_file_path}")
                else:
                    print(f"[metrics] No truth file found in {args.truth_dir} "
                          f"for input '{args.input}'; metrics will be "
                          f"computed without truth.")
            except Exception as e:
                print(f"[metrics] Truth-file detection failed: {e}")

    results = [run_pipeline(initial_blocks, max_recursion_depth,
                            min_intra_freq, all_refIDs, m, p,
                            top_k=args.top_k, tau=args.tau,
                            min_block_size=args.min_block_size,
                            cluster_on=args.cluster_on,
                            arcs_weighting=args.arcs_weighting,
                            density_floor=args.density_floor,
                            density_min_size=args.density_min_size,
                            original_refDict=original_refDict,
                            clusters_json_path=clusters_json_path,
                            single_run=single_run,
                            include_singletons=not args.no_singletons_json,
                            truth_file_path=truth_file_path,
                            write_metrics=not args.no_metrics,
                            max_block_pair_cost=args.max_block_pair_cost,
                            hierarchical=args.hierarchical_blocking,
                            blocking_mode=blocking_mode)
               for (m, p) in configs]

    print("\n\n" + "=" * 110)
    print("ABLATION SUMMARY" if not single_run else "RUN SUMMARY")
    if args.hierarchical_blocking:
        print(f"mode=hierarchical, n_levels={len(tokenFreqDict)}, "
              f"tau={args.tau}, top_k={args.top_k}, "
              f"min_block_size={args.min_block_size}, "
              f"arcs_weighting={args.arcs_weighting}, "
              f"density_floor={args.density_floor}")
    else:
        print(f"mode={blocking_mode}, init_df_max={init_df_max}, "
              f"max_recursion_depth={max_recursion_depth}, "
              f"min_intra_freq={min_intra_freq}, tau={args.tau}, "
              f"top_k={args.top_k}, min_block_size={args.min_block_size}, "
              f"arcs_weighting={args.arcs_weighting}, "
              f"density_floor={args.density_floor}, "
              f"cluster_on={args.cluster_on}")
    print("=" * 110)
    headers = ["merge", "purge", "blks(rec)", "pairs(rec)", "blks(flt)",
               "pairs(flt)", "clusters", "multi", "single",
               "t_rec(s)", "t_flt(s)", "t_clu(s)", "peak(MB)"]
    fmt = "{:>5} {:>5} {:>10} {:>12} {:>10} {:>12} {:>9} {:>6} {:>7} {:>9} {:>9} {:>9} {:>9}"
    print(fmt.format(*headers))
    print("-" * 110)
    for r in results:
        print(fmt.format(
            str(r["do_merge"])[0], str(r["do_purge"])[0],
            r["blocks_post_recursive"], r["pairs_post_recursive"],
            r["blocks_post_filter"], r["pairs_post_filter"],
            r["clusters_total"], r["clusters_multi"], r["clusters_singletons"],
            f"{r['time_recursive_s']:.2f}", f"{r['time_filter_s']:.2f}",
            f"{r['time_cluster_s']:.2f}", f"{r['peak_mem_mb']:.1f}",
        ))
    print("=" * 110)
