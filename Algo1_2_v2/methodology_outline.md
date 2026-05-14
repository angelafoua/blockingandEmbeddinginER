# algo1_2_v2 — Six-Stage Unsupervised ER Pipeline: Methodology Outline

## Problem Setting

- Unsupervised entity resolution over schema-heterogeneous, low-quality datasets
- No labelled training pairs, no schema metadata; operates on pure **bag-of-tokens** representation
- Goal: minimise candidate-pair count while preserving recall of true matches, then cluster records by entity

---

## Stage 0 — Document-Frequency Stop-Word Filtering

- Build a per-token document-frequency (DF) dict across all records
- Drop any token with `DF > F_max` (default 60) — high-frequency tokens produce large non-discriminative blocks
- Rebuild the DF dict on the cleaned vocabulary
- Emits diagnostic: how many tokens were removed and examples

---

## Stage 1 — Initial Blocking

Two modes, selected by `--full-blocking`:

### Standard Mode (default)

Token `t` becomes a blocking key for record `r` iff:

1. `len(t) >= L_min` (default 4)
2. `t` is not a pure-digit string (when `exclude_numeric_blocks = True`)
3. `2 <= DF(t) <= F_init`, where `F_init` is derived as the p95 (default) of the post-cleanup DF distribution (avoids mode-of-record-length integer instability)

### Full-Blocking Mode (Papadakis redundancy-positive)

- All length, numeric, and DF-cap filters bypassed
- Every surviving token with `DF >= 2` becomes a blocking key
- Maximises recall; precision recovery delegated downstream to ARCS + pair-cost guardrail

---

## Stage 2 — Recursive Co-occurrence Refinement *(central novel step)*

Iterates up to `d_max` (default 5) depths. At each depth `d`:

### `refine_blocks(blocks, μ)` — Algorithm 1

1. For each existing block `(K, R_K)`:
   - Count the intra-block frequency `φ_K[t]` of every token `t` *not already in K* across all records in `R_K`
   - For every such token where `φ_K[t] >= μ`: create a new refined block with key `K' = sorted(K ∪ {t})` and record set `R_{K'} = {r ∈ R_K : t ∈ r}`
2. Every refined block satisfies `K ⊂ K'` and `R_{K'} ⊆ R_K` — strictly more specific

### Depth-Coupled Frequency Floor

- Floor at depth `d` = `max(d, μ_min)` where `μ_min = 2` by default
- The coupling prevents combinatorial explosion at deeper depths (floor rises as depth increases)

### Termination

Stops when any of the following hold:
- `d > d_max`
- Refinement produces an empty set
- merge/purge reaches a fixed point

---

## Stage 3 — Lossless Block-Set Algebra *(applied after each refinement step)*

Two operators, each independently ablatable:

### `merge_blocks(σ_old, σ_new)`

- Groups all blocks by their frozenset of record IDs
- Blocks with identical record sets → collapsed into one block; key = concatenation of key tuples (deduplicated, first-occurrence order)
- Purpose: deduplicates when two distinct recursive paths converge on the same record set

### `purge_subset_blocks(σ)`

- Removes any block `(K, R_K)` where there exists another block `(K', R_{K'})` with `R_K ⊊ R_{K'}`
- Implemented in amortised O(Σ|R_K|) using an inverted index from refIDs to block indices
- Deterministic tie-breaking on equal-size blocks by lexicographic key order
- Purpose: removes blocks that are strict subsets of other blocks (redundant coverage)

### Why Both?

They handle different cases and commute on the steady state. Under standard blocking on S12PX, purge subsumes merge (V0 ≡ V2); under full-blocking, merge contributes meaningfully.

---

## Stage 4 — Block Filtering (Papadakis Top-k Smallest)

- For each record, sort its blocks by size ascending; keep only the `k` (default 3) smallest blocks
- Drop any block whose surviving membership falls below `β_min` (default 2)
- Intuition: small blocks are more specific and carry stronger ARCS signal; large blocks contribute negligibly

---

## Stage 5 — ARCS Meta-Blocking Graph Construction

Builds weighted graph `G = (V, E, w)` where `V = records` and edge weights accumulate per-block contributions:

$$w(r_i, r_j) = \sum_{B \,:\, (r_i, r_j) \in \binom{R_B}{2}} \mathrm{contrib}(B)$$

### Contribution Modes

| Mode | Formula | Notes |
|------|---------|-------|
| `uniform` (classical ARCS) | `contrib(B) = 1 / \|B\|` | Original formulation |
| `idf` (this paper's extension) | `contrib(B) = log(N / \|B\|) / \|B\|` | Penalises generic blocks more aggressively; sharpens precision but widens weight dynamic range, requiring re-tuning of τ |

### Optional Enrichments (all multiplicative)

- **Length weight**: `1 + weight × log(1 + max-token-length-in-key)`
- **Numeric/word type factor**: different multipliers for purely numeric vs. word-token keys
- **Block density factor**: `1 + weight × mean_intra_block_Jaccard` (sampled)
- **Pair similarity weight**: scales each pair's contribution by `Jaccard(tokens_A, tokens_B)` — records sharing no tokens contribute nothing

### Pair-Cost Guardrail (for full-blocking)

- Any block where `|B|(|B|-1)/2 > C_max` (recommended: 10⁵) is skipped during graph construction
- Skipped contribution is bounded by `1/|B|` per pair — negligible for very large blocks

---

## Stage 6 — Union-Find Clustering with Density-Floor Split

### Step 1 — Union-Find Clustering

- Retain all edges with weight `w(r_i, r_j) >= τ` (default `τ = 0.2` for uniform, `4.0` for IDF)
- Union-by-rank with path compression; connected components = predicted clusters

### Step 2 — Density-Floor Split — Algorithm 2

For each cluster `C` with `|C| >= m_min` (default 3):

1. Compute `density = |E_C| / (|C|(|C|-1)/2)` using only kept edges
2. If `density < δ_min` (default 0.0, i.e., disabled by default):
   - Sort internal edges by weight ascending
   - Greedily remove lightest edges one by one until the cluster disconnects
   - Recurse on each resulting component

**Purpose:** resists transitive-closure chain collapse (a single low-weight bridging edge collapsing two semantically distinct clusters).

---

## Hyperparameter Summary

| Parameter | Default | Role |
|-----------|---------|------|
| `F_max` | 60 | Stop-word DF cap |
| `init_df_percentile` | 0.95 (p95) | Initial blocking DF cap |
| `L_min` | 4 | Min token length for blocking |
| `exclude_numeric` | `true` | Exclude pure-digit tokens |
| `d_max` | 5 | Max recursion depth |
| `μ_min` | 2 | Min intra-block frequency floor |
| `k` (top-k) | 3 | Block Filtering per record |
| `β_min` | 2 | Min block size post-filter |
| `τ` | 0.2 / 4.0 | ARCS edge-weight threshold (uniform / IDF) |
| `arcs_weighting` | `uniform` | Contribution mode |
| `δ` (density floor) | 0.0 | Cluster-split threshold (disabled) |
| `C_max` | ∞ (10⁵ for full-blocking) | Pair-cost guardrail |

---

## Ablation Surface

Four-way merge × purge ablation runs all combinations **(merge=T/F) × (purge=T/F)**:

| Tag | merge | purge | Description |
|-----|-------|-------|-------------|
| V0  | T | T | Default baseline |
| V1  | T | F | No-purge ablation |
| V2  | F | T | No-merge ablation |
| V3  | F | F | Neither operator |

Additional configurations:

| Tag | Description |
|-----|-------------|
| P99 | Permissive DF cap (p99 instead of p95) |
| FB  | Full-blocking with IDF ARCS weighting |

All runs output:
- Per-stage diagnostic counters and percentile snapshots
- Cluster composition JSON (`clusters_m{0,1}_p{0,1}.json`)
- Structured metrics JSON (`.metrics.json`)
- Human-readable metrics log (`.metrics.log`)

---

## End-to-End Algorithm Summary (Algorithm 3)

```
Input  : refDict R, hyperparameters Θ
Output : final_clusters P

// Stage 0
R, removed ← remove_high_frequency_tokens(R, f, F_max)
// Stage 1
σ_init ← blocking(R, f, F_init, L_min, exclude_numeric, full_blocking)
// Stages 2–3
σ ← σ_init
for d = 1 .. d_max:
    μ_d ← max(d, μ_min)
    σ_new ← refine_blocks(σ, μ_d)
    if σ_new = ∅: break
    σ ← purge_subset_blocks(merge_blocks(σ, σ_new))
// Stage 4
σ ← filter_top_k_smallest(σ, k, β_min)
// Stage 5
G ← build_arcs_graph(σ, weighting, N, C_max)
// Stage 6
P ← union_find_clusters(G, τ)
if δ > 0:
    P ← split_low_density(P, G, δ, m_min)
return P
```

---

## Complexity

| Stage | Complexity |
|-------|-----------|
| Stage 0 (stop-word filter) | O(\|R\| · k̄) |
| Stage 1 (initial blocking) | O(\|R\| · k̄) |
| Stage 2 (recursive refinement, per iteration) | O(Σ_B \|R_B\| · k̄_B), bounded by F²_init per block under standard blocking |
| Stage 3 (merge/purge) | Amortised O(Σ_B \|R_B\|) |
| Stage 4 (block filtering) | O(\|R\| · log k) |
| Stage 5 (ARCS graph) | O(candidate-pair budget) |
| Stage 6 (Union-Find) | Near-linear in number of edges |
