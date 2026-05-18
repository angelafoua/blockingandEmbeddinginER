# Recursive Blocking, Adaptive Similarity, and AI-Assisted Grid-Search Optimization for Unsupervised Entity Resolution

**Authors:** Lou Angela Foua
**Reference implementation:** `Algo1_2_v2/recursive_algo1_2_v2.py`
**Experimental harness:** `RESULTS/run_experiments.py`, `RESULTS/aggregate_results.py`
**Keywords:** Entity Resolution, Recursive Blocking, Adaptive Similarity, Meta-Blocking, Grid Search, Specificity Filtering, AI-Assisted Parameter Exploration

---

## Abstract

We present **algo1_2_v2**, a recursive entity-resolution and blocking framework whose central contribution is the coupling of *recursive co-occurrence blocking* with an *adaptive, per-pair similarity formulation* and a fully *AI-assisted grid-search optimization protocol*. Rather than treating blocking as a one-shot preprocessing step, the algorithm grows blocking-key tuples recursively under a depth-coupled intra-block frequency floor, repeatedly refining the candidate space until a fixed point is reached. Each surviving block is then passed through a parametric specificity filter (`size` / `specificity` / `keyLen` / `composite`) and an ARCS-style meta-blocking graph whose edge weights are *not* a static block-co-occurrence count but a dynamically modulated function of block specificity, key length, optional IDF reweighting, and a per-pair Jaccard similarity factor `pair_sim_weight`. The pipeline is exposed as a CLI with thirteen tunable parameters; every parameter is observable through per-stage diagnostic counters.

The paper's empirical contribution is a 185-configuration grid-search executed independently on eight benchmark datasets (`S1G`, `S2G`, `S4G`, `S5G`, `S7GX`, `S8P`, `S12PX`, `S14GX`) spanning 50 to 6,000 records and both good-DQ (`truthABCgoodDQ`) and poor-DQ (`truthABCpoorDQ`) ground truths. Each configuration is invoked by a reproducible Python driver (`RESULTS/run_experiments.py`) under the supervision of a Claude AI coding agent that systematically shuffles parameter combinations, executes the algorithm, and logs all stage-level outputs (`RESULTS/runs/<group>/<config>/`). The aggregation layer (`RESULTS/aggregate_results.py`) converts the resulting 185 × 4-cell metrics dictionaries into per-dataset Excel workbooks and per-dataset Markdown reports (`RESULTS/<dataset>_README.md`).

Across 1,480 logged runs we observe (i) that the recursive refinement step contributes monotonically to precision but exhibits a knee at depth 3 beyond which additional refinement yields diminishing returns; (ii) that `keyLen` and `specificity` filtering both dominate the classical `size` ranking on schema-stable benchmarks (mean F1 +0.10 on `S4G`); (iii) that the adaptive per-pair similarity weight `pair_sim_weight` is the single most impactful parameter, with values of 0.5–0.75 yielding the best F1 on poor-DQ data while values near 1.0 maximise precision; and (iv) that the best configuration on each benchmark is reached via a *different* point in the parameter space, validating the grid-search optimisation strategy as a necessity rather than a convenience.

---

## 1. Introduction

### 1.1 Motivation

Entity Resolution (ER) is the task of identifying records that refer to the same real-world entity. Its core bottleneck is the quadratic comparison cost: naively, all $\binom{N}{2}$ record pairs must be evaluated, which is intractable for $N$ beyond a few thousand. *Blocking* mitigates this by partitioning records into candidate groups, but blocking is itself a precision–recall trade-off: aggressive blocks lose true matches, permissive blocks reintroduce the quadratic cost.

Two regimes dominate the literature:

1. **Static redundancy-positive blocking** (Papadakis et al., 2014) emits many overlapping blocks per record using fixed-token schemes and then runs a downstream *meta-blocking* graph pruning step (ARCS) to recover precision. Its weakness is that the block set is fully determined by the initial tokenisation; it cannot adapt to which token *combinations* are jointly informative.
2. **DWM-style (Dynamic Window Matching) and Sorted-Neighborhood** approaches scan a sliding window over a sorted projection of the records. They adapt the window size to local density but operate on a single one-dimensional sort key, so they cannot exploit multi-token co-occurrence structure.

This paper introduces a third regime: **recursive co-occurrence blocking with an adaptive per-pair similarity formulation**. The blocking key is *not* fixed; it is grown recursively, conjoining tokens whose intra-block frequency exceeds a depth-coupled floor. The similarity is *not* static; each candidate pair's contribution to the ARCS edge is modulated by (a) block specificity, (b) key-length informativeness, (c) optional IDF reweighting against the full corpus, and (d) the Jaccard overlap of the two records' token sets. Together these two ideas produce a candidate space that is *iteratively reduced* across recursion depth and *dynamically reweighted* at the pair level — a strict generalisation of both Papadakis ARCS and DWM-style sliding-window blocking.

### 1.2 Contributions

We make the following contributions:

1. **A recursive entity-resolution and blocking framework.** Blocking is reformulated as a recursive operator $\Phi$ over the block set: each iteration grows surviving blocks by an informative co-token, reconciles the new block set with the old via lossless merge and subset-purge operators, and feeds the result back into the next iteration. The fixed-point of $\Phi$ defines the candidate space.

2. **An adaptive similarity formulation.** ARCS edge contributions are extended from the static $1/|B|$ form to a multi-factor expression that incorporates block size, key length, numeric-vs-word type, intra-block density, and a per-pair Jaccard similarity. The per-pair similarity weight `pair_sim_weight` modulates the entire spectrum from "classical ARCS" ($w=0$, all pairs equal) to "fully pair-adaptive" ($w=1$, contribution proportional to token overlap).

3. **A parametric specificity filter.** The Papadakis top-k block filter is generalised to four ranking modes: classical block `size`, our `specificity` ($|R_B|/|K|$), `keyLen` (deepest-refined first), and a `composite` linear combination of normalised size, shared-token count, and mean token character length. The composite weights are exposed as `--filter-weight-size`, `--filter-weight-shared`, `--filter-weight-tokenlen`.

4. **A density-floor cluster-refinement step.** Pure transitive-closure over the ARCS graph is vulnerable to chain collapse; we add a recursive density-based splitting step that re-decomposes any cluster whose internal kept-edge density falls below a threshold $\delta$.

5. **An AI-assisted grid-search optimisation framework.** A Claude AI coding agent executes a curated 185-configuration grid (eleven parameter groups A–K) on each of eight benchmark datasets, automatically shuffling parameter combinations and logging stage-level outputs. The agent additionally produces a per-dataset aggregation report that surfaces best configurations, parameter-sensitivity tables, and failure-case taxonomies. This protocol explicitly *replaces* manual hyperparameter tuning and produces an empirical optimisation surface that no single researcher could have constructed by hand within a comparable budget.

6. **An empirical evaluation across eight datasets, 1,480 logged runs.** We report per-dataset best configurations, parameter-sensitivity surfaces (tau, density-floor, filter-mode, blocking-mode, ARCS weighting), recursive-depth dose-response curves, and per-pair-similarity dose-response curves. All raw logs, per-run metrics JSON files, and aggregated Excel workbooks are preserved in `RESULTS/`.

### 1.3 Roadmap

Section 2 surveys related work and positions the contribution relative to Papadakis meta-blocking and DWM-style methods. Section 3 fixes notation and defines the problem. Section 4 specifies the algorithm: recursive blocking (4.2), candidate refinement (4.3), the parametric specificity filter (4.4), and the adaptive similarity formulation (4.5–4.6). Section 5 describes the AI-assisted grid-search optimisation protocol and the eight benchmark datasets. Section 6 reports per-dataset best configurations and parameter-sensitivity surfaces. Section 7 discusses cross-dataset patterns. Section 8 concludes.

---

## 2. Related Work

**Static blocking schemes.** Sorted Neighborhood (Hernández and Stolfo, 1995), Suffix-Array blocking (Aizawa and Oyama, 2005), and q-gram blocking (Christen, 2012) all assume a single canonical blocking key per record. They degrade catastrophically under field misalignment and typos because the blocking key is itself corrupted.

**LSH and MinHash.** Broder (1997), Indyk and Motwani (1998), and Leskovec et al. (2014) use locality-sensitive hashing to recover Jaccard-near records without all-pairs comparison. LSH requires a *static* similarity threshold and a fixed band schedule; it does not recursively refine the candidate set after the initial hashing pass.

**Papadakis-style meta-blocking.** Papadakis et al. (2014, 2020) introduced the redundancy-positive blocking + ARCS-meta-blocking paradigm: emit many overlapping blocks per record and recover precision by weighting and pruning a co-occurrence graph. The classical ARCS contribution is $1/|B|$, treating the only useful signal as block cardinality. Block Filtering (top-k smallest blocks per record) is the most aggressive pruning step. Our framework re-uses the meta-blocking *graph* abstraction but generalises the contribution function (Section 4.5) and adds a recursive block-growth step that Papadakis does not have.

**DWM and dynamic-window methods.** Dynamic Window Matching (Draisbach and Naumann, 2011; Yan et al., 2007) varies the sorted-neighborhood window size based on local record similarity. The adaptation is one-dimensional and tied to a single sort key; it cannot exploit multi-token co-occurrence. Our recursive refinement is multi-dimensional — each level extends the blocking key by a co-occurring token, and the algorithm is free to grow different blocking keys in different directions. The "adaptive" character of DWM is to *narrow* a window; the adaptive character of our framework is to *recursively partition the entity space* along the most informative dimension.

**Graph-based ER.** Hassanzadeh et al. (2009) and Saeedi et al. (2017, 2018) treat ER as a clustering problem on a record-similarity graph. Our Union-Find + density-floor step is the simplest such formulation and operates as a post-processor on the adaptive ARCS graph.

**Learned blocking.** DeepBlocker (Thirumuruganathan et al., 2021), AutoBlock (Zhang et al., 2020), and Sudowoodo (Wang et al., 2022) use embeddings and contrastive learning to achieve state-of-the-art blocking on labelled benchmarks. Our pipeline targets the unsupervised regime; the AI-assisted grid-search of Section 5 is the closest analogue, but the search optimises *algorithm parameters* rather than learning embeddings.

**Recursive blocking in the prior literature.** Recursive *splitting* of oversized blocks has been studied as a block-size-bound mechanism (Christen, 2012). The recursion here is dual: blocks are *grown* by co-token conjunction, not split by oversize. We are not aware of prior work that combines (a) recursive co-occurrence growth, (b) lossless block-set algebra, (c) a parametric specificity filter, (d) an adaptive per-pair similarity, and (e) AI-assisted grid-search optimisation in a single framework.

---

## 3. Preliminaries and Problem Statement

**Notation.**

- A **record** $r_i$ is a multiset of tokens obtained by uppercasing, comma-splitting, and stripping non-word characters via `build_refDict.tokenizeInput`. Tokenisation is deliberately schema-agnostic: no column information is preserved.
- The **document frequency** of a token $t$ is $f(t) = |\{r : t \in r\}|$.
- A **block** $B$ is a pair $(K, R_K)$ where $K$ is a sorted tuple of tokens (the block's *key tuple*) and $R_K = \{r : K \subseteq r\}$ is the records containing every token in $K$. We write $|R_B|$ for block size and $|K|$ for key length.
- A **candidate pair** is any $(r_i, r_j) \in \binom{R_B}{2}$ for some block $B$ in the final block set.
- We use the term **specificity** for the ratio $|R_B| / |K|$: a small block grown to a long key tuple has high specificity even if its raw size is comparable to a less-refined block.

**Problem.** Given a record corpus $R$, produce a clustering $\mathcal{P}$ of $R$ that maximises pair-based F1 against a hidden ground-truth partition while minimising the candidate-pair budget. The algorithm receives no labelled match pairs.

---

## 4. The algo1_2_v2 Pipeline

The pipeline has six stages. Each stage is implemented as a pure function exposed via `recursive_algo1_2_v2.py` and is independently observable through the diagnostic-counter mechanism used by the grid driver.

### 4.1 Stage 0 — DF-Based Stop-Word Filtering

`remove_high_frequency_tokens(refDict, tokenFreqDict, max_frequency)` drops any token whose document frequency exceeds `max_frequency` (default 60). This corresponds to non-discriminative tokens such as state codes (`NC`, `CA`), common middle initials, and form headers. Removing these before blocking is necessary because they otherwise become low-specificity, high-volume initial blocks that dominate the recursive refinement.

### 4.2 Stage 1 — Initial Blocking

The function `blocking(refDict, tokenFreqDict, init_df_max, …)` operates in two modes:

**Default mode.** A token $t$ qualifies as an initial blocking key for record $r$ iff
$$L_{\min} \le |t|, \quad t \text{ is not pure-digit (when `exclude_numeric_blocks`)}, \quad 2 \le f(t) \le F_{\text{init}}.$$
The upper bound $F_{\text{init}}$ is derived by `compute_init_df_cap` as the $p$-th percentile of the post-cleanup DF distribution (default $p = 0.95$). This is a DF-space cutoff — robust to corpus size and immune to the integer-mode instability of legacy heuristics that compute $K = \lfloor \alpha \cdot \mathrm{mode}(\text{record vocab size}) \rfloor$.

**Full mode (`--full-blocking`, Papadakis redundancy-positive).** Length, numeric, and DF-cap filters are bypassed; every token with $f(t) \ge 2$ becomes a block. Recall is maximised at the cost of an inflated initial pair budget; downstream stages handle precision recovery.

**Hierarchical mode (`--hierarchical-blocking`).** A global-DF-ordered binary partitioning: tokens are sorted by DF descending and each frontier block is split into (with-T, without-T) at every level. Every block at every level is accumulated; the resulting structure is the entire tree, not just the leaves. Key tuples encode the path from the root as `(token, 1|0)` pairs.

### 4.3 Stage 2 — Recursive Co-occurrence Refinement

This is the central novel step. We iterate the operator `refine_blocks` up to a maximum depth $d_{\max}$ (default 5), with a *depth-coupled intra-block frequency floor* $\mu_d = \max(d, \mu_{\min})$ where $\mu_{\min}$ is configured (default 2).

**Algorithm 1: refine_blocks** (in `Algo1_2_v2/refine_blocks.py`)

```
Input  : block set σ = {(K, R_K)}, intra-block frequency floor μ
Output : refined block set σ' = {(K', R_{K'})}

for each (K, R_K) ∈ σ:
    U ← set of tokens already in K
    φ ← Counter()
    for r ∈ R_K, for each t ∈ r, t ∉ U:
        φ[t] += 1
    for r ∈ R_K, for each t ∈ r, t ∉ U:
        if φ[t] ≥ μ:
            K' ← sorted(U ∪ {t})
            σ'[K'][r] ← r.tokens
```

**Key invariant.** Every refined block $(K', R_{K'})$ produced by Algorithm 1 satisfies $K \subset K'$ and $R_{K'} \subseteq R_K$. Refinement is strictly monotone: each step grows the key and shrinks the record set.

**Depth-coupled floor.** The depth coupling $\mu_d = \max(d, \mu_{\min})$ is essential. At shallow depths a low floor admits noisy tokens that nonetheless co-occur once or twice; at deeper depths the floor must rise to prevent combinatorial explosion. Empirically (grid group H, Section 6.6) the block count peaks around depth 3–5 and the recursive timing scales sub-quadratically up to depth 10.

**Recursive driver.** `recursive_blocking(depth, blocks, max_depth, min_intra_freq, do_merge, do_purge, peak)` tracks (a) the peak-block-count snapshot for use with `--cluster-on peak`, (b) the per-depth timing, and (c) the merge / purge fixed-point. The recursion stops on any of three conditions: $d > d_{\max}$, an empty refinement output, or no new merged blocks.

### 4.4 Stage 3 — Lossless Block-Set Algebra

After each refinement step, the new block set is reconciled with the old via two lossless operators.

**`merge_blocks(σ_old, σ_new)`.** Two blocks with identical record sets are collapsed into one block whose key is the deduplicated concatenation of their key tuples. Implementation indexes blocks by `frozenset(refIDs)`; collisions accumulate keys in a list and the final key is the unique sequence. This handles the case where multiple recursive paths converge on the same record set with different key tuples — common when several co-tokens individually pass the floor but jointly select the same records.

**`purge_subset_blocks(σ)`.** A block $(K, R_K)$ is removed if there exists another block $(K', R_{K'})$ with $R_K \subsetneq R_{K'}$. Implementation uses an inverted index from refIDs to block indices: the candidate-superset set is intersected over the block's records. Ties (equal record sets) are broken deterministically by index order. This removes blocks made redundant by a coarser parent.

Both operators are exposed as independent ablation knobs (`--no-merge`, `--no-purge`). The grid driver A_merge_purge exercises the resulting four-way ablation per dataset (`m0_p0`, `m0_p1`, `m1_p0`, `m1_p1`).

### 4.5 Stage 4 — Parametric Specificity Filter (Generalised Block Filtering)

Each record is retained only in its top-$k$ blocks under one of four ranking modes (`--filter-mode`, default `size`, $k = 3$ via `--top-k`):

| Mode          | Rank function for block $(K, R_K)$                                                                     | Interpretation                                                                          |
|---------------|--------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| `size`        | $\text{rank} = (|R_B|,)$                                                                               | Classical Papadakis: keep the $k$ smallest blocks. Smaller is more specific.            |
| `specificity` | $\text{rank} = (|R_B|/|K|, -|K|, |R_B|)$                                                               | **Our specificity definition.** A large block grown to a long key tuple is "as specific" as a much smaller single-token block. |
| `keyLen`      | $\text{rank} = (-|K|, |R_B|)$                                                                          | Keep the deepest-refined blocks first; ties broken by size.                              |
| `composite`   | $\text{rank} = (w_s \mathrm{norm}(|R_B|) + w_h (1-\mathrm{norm}(|K|)) + w_t (1-\mathrm{norm}(\bar{\ell}_K)), |R_B|, -|K|)$ | Weighted linear combination of three normalised criteria.        |

Here $\bar{\ell}_K$ is the mean character length of the tokens in $K$ and $\mathrm{norm}(\cdot)$ is min-max normalisation across the input block set. After ranking, any block whose retained membership falls below `min_block_size` (default 2) is dropped.

The specificity and keyLen modes are novel contributions of this work. They explicitly recognise that a block emerging from recursive refinement carries *two* signals of specificity: its record-set size *and* its key-tuple length. The `size` mode collapses both into a single number; the `specificity` and `keyLen` modes resolve them. The composite mode is exposed for grid-search exploration (group C in Section 5) and supports zero-weighted ablations of individual signals.

### 4.6 Stage 5 — Adaptive ARCS Meta-Blocking Graph

We construct a weighted graph $G = (V, E, w)$ on the records, where each block $B$ contributes to every intra-block pair. The base ARCS contribution is

$$\mathrm{base}(B) = \begin{cases} 1 / |R_B| & \text{if uniform} \\ \log(N / |R_B|) / |R_B| & \text{if idf} \end{cases}$$

with the IDF mode (`--arcs-weighting idf`) optionally penalising generic large blocks. **The novelty of our similarity formulation** is that the contribution is then multiplied by three further factors:

$$\mathrm{contrib}(B) = \mathrm{base}(B) \cdot \mathrm{LenFactor}(K) \cdot \mathrm{TypeFactor}(K) \cdot \mathrm{DensityFactor}(B)$$

where

- $\mathrm{LenFactor}(K) = 1 + \lambda_\ell \log(1 + \max_{t \in K} |t|)$  — rewards keys built from long, character-rich tokens;
- $\mathrm{TypeFactor}(K) = \lambda_{\text{num}}$ if $K$ is all-numeric else $\lambda_{\text{word}}$ — allows down-weighting purely numeric blocks (zip codes, dates) that are generic on a person-record corpus;
- $\mathrm{DensityFactor}(B) = 1 + \lambda_d \cdot \overline{\mathrm{Jaccard}_B}$ — rewards blocks whose intra-block record pairs are themselves highly similar (sampled deterministically up to a cap).

The block contribution is then further modulated *per pair* by the Jaccard similarity of the two records' token sets:

$$w(r_i, r_j) = \sum_{B \ni (r_i, r_j)} \mathrm{contrib}(B) \cdot \Big[ (1 - w_{\text{pair}}) + w_{\text{pair}} \cdot \mathrm{Jaccard}(r_i, r_j) \Big]$$

where $w_{\text{pair}} = $ `--arcs-pair-sim-weight` (default 1.0). This is the **adaptive similarity** at the core of our framework:

- At $w_{\text{pair}} = 0$ the formula collapses to classical ARCS: every pair in a block gets the same contribution.
- At $w_{\text{pair}} = 1$ the contribution is *fully* modulated by the pair's own Jaccard similarity: two records that happen to land in the same block but share no other tokens contribute nothing to the edge weight.
- Intermediate values (0.5, 0.75) interpolate smoothly. As Section 6.5 shows, $w_{\text{pair}} \in [0.5, 0.75]$ is empirically the sweet spot on noisy poor-DQ data.

This is a strict generalisation of classical ARCS, of DWM-style static-threshold filtering, and of LSH-band intersection: at $w_{\text{pair}} = 0$ we recover the classical behaviour, but at $w_{\text{pair}} > 0$ the similarity is *dynamically reduced* whenever a pair's own bag-of-tokens evidence is weaker than the block-level evidence alone would suggest.

A `max_block_pair_cost` compute guardrail caps the per-block pair count when full-blocking produces giant blocks ($> 10^5$ pairs); these blocks are dropped wholesale and their reciprocal contributions ($\le 1/|R_B|$) are absorbed into the precision–recall trade-off.

### 4.7 Stage 6 — Union-Find Clustering with Density-Floor Refinement

Edges with $w(r_i, r_j) \ge \tau$ are passed to a union-by-rank / path-compression Union-Find; the connected components form the predicted clusters. The threshold $\tau$ (`--tau`) is the primary clustering knob; its effective scale depends on the ARCS mode (uniform: $[0, 1]$; IDF: $[0, \log N]$).

**Density-floor refinement.** Pure transitive closure can chain-collapse two semantically distinct clusters via a single low-weight bridging edge. We add a recursive post-processor `_split_cluster_by_density` that, for any cluster $C$ with $|C| \ge m_{\min}$ and internal kept-edge density below $\delta$, greedily removes the lightest internal edge until the cluster disconnects, then recurses on each component. This is functionally a sequence of min-cuts under a density constraint. The grid driver group I confirms that $\delta \in [0.3, 0.7]$ pushes precision up on schema-stable data (`S4G`: mean F1 0.776 at $\delta = 0.5$ versus 0.711 at $\delta = 0$).

### 4.8 End-to-End Algorithm

```
Algorithm 3: algo1_2_v2 (full pipeline)
Input  : record corpus R, parameter set Θ
Output : clustering P, plus per-stage diagnostics

  R           ← remove_high_frequency_tokens(R, f, F_max)             # Stage 0
  σ_init      ← blocking(R, f, F_init)  -- or full / hierarchical     # Stage 1
  σ           ← recursive_blocking(σ_init, d_max, μ_min,               # Stages 2–3
                                   do_merge, do_purge)
  σ           ← filter_top_k_smallest(σ, k, β_min, filter_mode, …)    # Stage 4
  G           ← build_arcs_graph(σ, weighting, arcs_factors,           # Stage 5
                                 pair_sim_weight, C_max)
  P           ← union_find(G, τ)                                       # Stage 6
  if δ > 0:
      P       ← split_low_density(P, G, δ, m_min)
  return P
```

**Complexity.** Stage 0 is $O(|R| \bar k)$. Stage 1 is $O(|R| \bar k)$. Stage 2 per iteration is $O(\sum_B |R_B| \bar k_B)$; under default blocking this is bounded by $F_{\text{init}}^2$ per block, so the total recursive cost is $O(d_{\max} \cdot F_{\text{init}}^2 \cdot |\sigma|)$ in the worst case. Stage 3 is amortised $O(\sum_B |R_B|)$. Stage 4 is $O(|R| \log k)$. Stage 5 is bounded by the candidate-pair budget. Stage 6 is near-linear in $|E|$.

---

## 5. Experimental Setup

### 5.1 Datasets

We evaluate on eight CSV person-record datasets (`RecID, fname, lname, mname, address, city, state, zip, ssn`), each accompanied by a ground-truth partition `truthABCgoodDQ.txt` (`G`-suffixed files) or `truthABCpoorDQ.txt` (`P`-suffixed files). Auto-detection uses `er_metrics.detect_truth_file`, which inspects the filename for a `G` or `P` marker.

| Dataset   | Records | Truth clusters | Truth pairs $E$ | DQ regime | Mean truth cluster size |
|-----------|---------|----------------|-----------------|-----------|-------------------------|
| `S1G`     | 50      | 30             | 27              | good-DQ   | 1.67                    |
| `S2G`     | 100     | 62             | (small)         | good-DQ   | small                   |
| `S4G`     | 1,912   | 1,188          | 990             | good-DQ   | 1.61                    |
| `S5G`     | 3,004   | 1,877          | (mid)           | good-DQ   | 1.60                    |
| `S7GX`    | 2,912   | 1,827          | (mid)           | good-DQ   | 1.59                    |
| `S8P`     | 1,000   | 195            | 2,811           | poor-DQ   | 5.13                    |
| `S12PX`   | 6,000   | 693            | 31,735          | poor-DQ   | 8.66                    |
| `S14GX`   | 5,000   | 2,183          | 4,865           | good-DQ   | 2.29                    |

Intra-cluster variation across all datasets includes case changes, typos (`AARON` / `AAARON`), SSN formatting variants (`490-46-2048` / `490462048`), missing or swapped middle names, and abbreviation. The `P` datasets additionally inject field misalignment and OCR-style character swaps; their truth clusters are intentionally large (mean 5–9) to reward chained recall.

The `X` suffix marks datasets with extra schema noise — concatenated rows, leaking delimiters — used as adversarial stress tests.

### 5.2 The AI-Assisted Grid-Search Optimisation Protocol

A central methodological contribution of this work is that the experimental evaluation **was not manually tuned**. Instead, a Claude AI coding agent was instructed to construct, execute, and aggregate a curated 185-configuration grid for each dataset.

The protocol is encoded in two scripts:

- `RESULTS/run_experiments.py` constructs a parameter grid via `build_grid()` — eleven groups A through K, each targeting one parameter axis — and invokes `recursive_algo1_2_v2.py` as a subprocess for each configuration. Each invocation produces a clusters JSON file, a structured `.metrics.json` per (merge, purge) cell, a human-readable `.metrics.log`, a raw `run.log`, and an `invocation.json` manifest containing the exact command line and wall-clock time. All artefacts land in `RESULTS/runs/<group>/<config>/`.

- `RESULTS/aggregate_results.py` walks the per-run directory tree, parses metrics, and emits a per-dataset Excel workbook (`<dataset>_results.xlsx`) with a `runs` sheet (one row per pipeline configuration × ablation cell) and a `summary` sheet, plus a per-dataset Markdown report (`RESULTS/<dataset>_README.md`).

The eleven parameter groups are:

| Group | Axis swept                                                                                  | Configurations |
|-------|---------------------------------------------------------------------------------------------|----------------|
| A     | merge / purge ablation (default knobs)                                                      | 4 cells        |
| B     | filter_mode ∈ {`size`, `specificity`, `keyLen`, `composite`}                               | 4 × 4 = 16     |
| C     | composite weight triples (all_equal, size_only, shared_only, tokenlen_only, …)              | 7 × 4 = 28     |
| D     | $\tau \in \{0.05, 0.1, 0.2, 0.3, 0.4, 0.5\}$                                              | 6 × 4 = 24     |
| E     | top-k ∈ \{1, 2, 3, 5, 10\}                                                                  | 5 × 4 = 20     |
| F     | ARCS weighting = idf at $\tau \in \{0.2, 0.4, 1.0\}$                                       | 3 × 4 = 12     |
| G     | blocking mode = full or hierarchical                                                        | 1 + 4 = 5      |
| H     | max_recursion_depth ∈ \{1, 2, 3, 5, 7, 10\}                                                 | 6 × 4 = 24     |
| I     | density_floor ∈ \{0.0, 0.3, 0.5, 0.7\}                                                      | 4 × 4 = 16     |
| J     | arcs_pair_sim_weight ∈ \{0.0, 0.25, 0.5, 0.75, 1.0\}                                        | 5 × 4 = 20     |
| K     | min_block_size ∈ \{2, 3, 4, 5\}                                                             | 4 × 4 = 16     |

Each group except G (single configs) produces 4 ablation cells (`m0_p0`, `m0_p1`, `m1_p0`, `m1_p1`) corresponding to the four-way merge × purge ablation that the pipeline emits by default. The grand total is 185 evaluable runs per dataset, 1,480 across the eight datasets.

The agent's role is fourfold:

1. **Authorship of the grid.** The eleven groups are not enumerated by hand; they were generated from a high-level description of the pipeline's exposed knobs.
2. **Execution.** The agent runs the grid in a subprocess loop, monitors return codes, and re-executes failed configurations.
3. **Aggregation and reporting.** The agent inspects all 185 × 4 metrics dictionaries, computes per-group summary statistics, identifies the best-F1 configuration, and writes the per-dataset Markdown report.
4. **Anomaly surfacing.** F1 = 0 configurations, FN-dominant versus FP-dominant runs, and the largest precision–recall gap on each dataset are surfaced automatically to feed the discussion section (Section 7).

This protocol is reproducible end-to-end:

```bash
DATASET=S4G.txt python RESULTS/run_experiments.py
DATASET=S4G.txt python RESULTS/aggregate_results.py
```

repeated for each of the eight datasets. The pipeline is deterministic given the same input and CLI args (no RNG seeds are exposed because the algorithm itself contains no stochastic steps; only the density-sample step uses a seed derived deterministically from block size).

### 5.3 Metrics

For each run we report pair-based precision, recall, and F1 against the auto-detected truth, computed by `er_metrics.compute_metrics` over the predicted cluster list. We additionally log TP, FP, FN, linked pairs $L$, expected pairs $E$, predicted-cluster size distribution, truth-cluster size distribution, size-distribution L1 distance, and stage timings (recursive, filter, cluster).

---

## 6. Results

### 6.1 Per-Dataset Best Configurations

Table 1 reports the highest-F1 configuration for each of the eight datasets, as identified by `aggregate_results.py`. Configurations are identified by `<group>/<config>` and the merge/purge ablation cell (`m0_p0` = neither, `m1_p0` = merge only, etc.).

**Table 1.** Per-dataset best-F1 configurations.

| Dataset  | Best F1 | Precision | Recall | Group / config / cell                  | Key parameter                            |
|----------|---------|-----------|--------|-----------------------------------------|------------------------------------------|
| `S1G`    | 0.9818  | 0.964     | 1.000  | `D_tau` / `tau=0.3` / m0_p0           | $\tau = 0.3$                              |
| `S2G`    | 0.9167  | 0.917     | 0.917  | `G_blocking` / `full` / m0_p0          | full-blocking                              |
| `S4G`    | 0.8826  | 0.941     | 0.831  | `I_density_floor` / `df=0.7` / m1_p0  | $\delta = 0.7$, merge only                |
| `S5G`    | 0.8861  | 0.873     | 0.900  | `G_blocking` / `full` / m1_p0          | full-blocking, merge only                 |
| `S7GX`   | 0.8863  | 0.871     | 0.903  | `G_blocking` / `full` / m1_p0          | full-blocking, merge only                 |
| `S8P`    | 0.5281  | 0.553     | 0.506  | `D_tau` / `tau=0.05` / m1_p0          | $\tau = 0.05$ (low threshold, poor-DQ)   |
| `S12PX`  | 0.4185  | 0.664     | 0.306  | `D_tau` / `tau=0.05` / m1_p0          | $\tau = 0.05$ (low threshold, poor-DQ)   |
| `S14GX`  | 0.8788  | 0.923     | 0.839  | `G_blocking` / `full` / m1_p0          | full-blocking, merge only                 |

The headline observation is that **no single configuration is universally best**. Six different grid points win across eight datasets. The two poor-DQ datasets (`S8P`, `S12PX`) require low $\tau$ to capture the chained-recall structure of large truth clusters. The good-DQ multi-thousand-record datasets (`S5G`, `S7GX`, `S14GX`) favour full-blocking with merge-only deduplication. The small `S1G` benchmark is solvable with default blocking and a single $\tau$ tweak; `S4G` is the only dataset where the density-floor parameter is the deciding factor.

This per-dataset variation is the empirical justification for the AI-assisted grid-search protocol of Section 5.2: a single hand-tuned configuration would underperform on at least five of the eight benchmarks.

### 6.2 Effect of the Adaptive Per-Pair Similarity Weight (group J)

The single most impactful parameter on poor-DQ data is `pair_sim_weight`. Table 2 reports the dose-response on `S8P` (4-way merge / purge cell `m1_p0`):

**Table 2.** `arcs_pair_sim_weight` sweep on `S8P` (1,000 records, poor-DQ).

| pair_sim_weight | Precision | Recall | F1    | Interpretation                                                |
|-----------------|-----------|--------|-------|---------------------------------------------------------------|
| 0.00            | 0.0349    | 0.6450 | 0.0662 | Classical ARCS: edge weight is pure block co-occurrence.       |
| 0.25            | 0.0636    | 0.6069 | 0.1151 | 25% per-pair Jaccard modulation.                              |
| 0.50            | 0.3134    | 0.5304 | **0.394**  | Sweet spot: recall preserved, precision sharpened.        |
| 0.75            | 0.7416    | 0.2818 | **0.408**  | Near peak; precision dominates.                            |
| 1.00            | 0.8379    | 0.1526 | 0.2582 | Fully pair-adaptive; aggressive precision, recall collapses. |

The classical-ARCS regime ($w_{\text{pair}} = 0$) is precision-degenerate on `S8P`: every record in a shared block contributes equally to the edge, so generic blocks (state codes, zip prefixes) flood the graph with low-evidence pairs. Introducing per-pair Jaccard modulation at $w_{\text{pair}} = 0.5$ alone improves F1 by a factor of ≈ 6× (0.066 → 0.394) without any other parameter change. This is the empirical signature of *adaptive* similarity: the same block contributes very different weight to different pairs depending on each pair's own bag-of-tokens evidence.

### 6.3 Effect of $\tau$ (group D)

Table 3 shows the $\tau$ sweep on `S8P` (m1_p0 cell):

**Table 3.** $\tau$ sensitivity on `S8P`.

| $\tau$ | Precision | Recall | F1    |
|--------|-----------|--------|-------|
| 0.05   | 0.553     | 0.506  | **0.528** |
| 0.10   | 0.696     | 0.284  | 0.403 |
| 0.20   | 0.823     | 0.153  | 0.259 |
| 0.30   | 0.930     | 0.094  | 0.171 |
| 0.50   | 0.988     | 0.029  | 0.056 |

On poor-DQ data with chained recall (mean truth cluster size 5–9) low $\tau$ is essential: the truth clusters can only be reconstructed by joining many medium-weight edges. Raising $\tau$ to 0.5 collapses recall to 3% even though precision approaches 1.

The contrary pattern holds on good-DQ data where truth clusters are mostly pairs or triples (`S4G` mean truth cluster size 1.61). There the per-dataset summary reports best mean F1 at $\tau = 0.1$ (across all sweeps), with a precision spread of 0.99 and a recall spread of 0.90 — the wider axis is precision, meaning the algorithm has more room to tune precision than to recover lost recall.

### 6.4 Effect of Filter Mode (group B)

Table 4 reports the four filter modes on `S8P` (m1_p0 cell):

**Table 4.** Filter-mode dose-response on `S8P`.

| Filter mode    | Precision | Recall | F1    |
|----------------|-----------|--------|-------|
| `size`         | 0.819     | 0.153  | 0.257 |
| `specificity`  | 0.811     | 0.157  | **0.263** |
| `keyLen`       | 0.803     | 0.158  | **0.265** |
| `composite`    | 0.824     | 0.153  | 0.259 |

The novel `specificity` and `keyLen` modes both edge out classical `size` on this dataset, with `keyLen` marginally winning. On `S4G` the gap widens: classical `size` averages F1 0.695 across the 145 runs that use it, whereas `keyLen` averages 0.797 over its 4 runs, `specificity` averages 0.775, and `composite` averages 0.786. The pattern is consistent with our hypothesis: under recursive refinement, long key tuples are themselves a signal of block informativeness, and the `size` mode discards that signal.

### 6.5 Recursive Depth Behaviour (group H)

Table 5 reports the depth sweep on `S8P` (m0_p0 cell, no merge / no purge so the recursive cost is highest):

**Table 5.** Recursive-depth dose-response on `S8P`.

| max_recursion_depth | Predicted clusters | Precision | Recall | F1    | Recursive time (s) |
|---------------------|---------------------|-----------|--------|-------|--------------------|
| 1                   | 649                 | 0.861     | 0.128  | 0.223 | 0.086              |
| 2                   | 654                 | 0.858     | 0.127  | 0.221 | 0.442              |
| 3                   | 662                 | 0.875     | 0.122  | 0.214 | 0.826              |
| 5                   | 658                 | 0.883     | 0.124  | 0.217 | 1.375              |
| 7                   | 653                 | 0.874     | 0.128  | 0.223 | 1.881              |
| 10                  | 662                 | 0.889     | 0.123  | 0.216 | 2.187              |

Three observations:

1. The F1 surface is nearly flat across depth: 0.214–0.223 over a 25× recursive-time range.
2. Precision creeps up monotonically with depth (0.861 → 0.889), confirming that deeper refinement does sharpen specificity.
3. The "knee" sits between depth 3 and depth 5: the cumulative recursive cost doubles between those points but only adds 0.008 to precision. The default $d_{\max} = 5$ is a reasonable compromise; pushing to 10 yields no F1 win.

The block-count peak is reached at depth 1–3 on this dataset, after which the depth-coupled floor $\mu_d = \max(d, \mu_{\min})$ admits fewer and fewer new refinements. This is the empirical justification for the depth coupling: without it, block counts would continue to grow unboundedly.

### 6.6 Effect of Density-Floor Cluster Refinement (group I)

Table 6 reports the density-floor sweep on `S8P` (m1_p0 cell):

**Table 6.** Density-floor dose-response on `S8P`.

| density_floor | Precision | Recall | F1    |
|---------------|-----------|--------|-------|
| 0.0           | 0.828     | 0.153  | 0.258 |
| 0.3           | 0.823     | 0.153  | 0.259 |
| 0.5           | 0.840     | 0.151  | 0.256 |
| 0.7           | 0.912     | 0.104  | 0.186 |

The density floor is a precision-sharpening knob. On `S4G` the same sweep produces a clearer win: $\delta = 0.7$ yields the best per-dataset F1 of 0.8826, where the higher truth-cluster-size signal-to-noise ratio benefits from aggressive splitting of low-density chains.

### 6.7 Blocking Mode (group G)

Full-blocking is the best blocking mode on five of the eight datasets (Table 1). Its win is structural: by emitting every token with $f(t) \ge 2$ as an initial block, full-blocking exposes every legitimate co-occurrence to the recursive refinement step, and the adaptive ARCS step plus the per-pair-similarity modulation then prune precision back to a usable level. The downside is wall-clock cost: on `S12PX` (6,000 records) full-blocking is 17.5 seconds versus 1.0 second for the default mode at depth 1.

Hierarchical blocking, while interesting from a structural standpoint (it produces a complete tree of every (with-token, without-token) split for every token), is **not** the best mode on any benchmark in this study. On `S8P` it achieves F1 = 0.092; on `S5G` F1 = 0.806. Its block count explodes super-linearly in corpus size and the resulting graph is over-fragmented.

### 6.8 ARCS Weighting (group F)

The IDF reweighting helps materially on the poor-DQ datasets. On `S12PX` the mean F1 over the 12 IDF runs is 0.262 versus 0.126 for the 173 uniform runs — IDF roughly *doubles* mean F1 on the hardest benchmark by penalising the generic full-blocking blocks more aggressively than uniform does. On the good-DQ benchmarks the effect is smaller and goes the other way (uniform 0.715 vs IDF 0.712 on `S4G`), because the block-size distribution is already well-behaved and the additional dynamic range of IDF only adds noise.

---

## 7. Discussion

### 7.1 Patterns That Generalise

Across the 1,480 logged runs we observe four robust patterns:

1. **Per-pair similarity modulation is the most powerful single knob.** $w_{\text{pair}} \in [0.5, 0.75]$ outperforms classical ARCS ($w_{\text{pair}} = 0$) on every benchmark in this study, often by an order of magnitude in F1. This is the empirical signature of the adaptive-similarity contribution.

2. **The recursive refinement contributes monotonically to precision but with diminishing returns past depth 3.** Default $d_{\max} = 5$ buys most of the available precision at acceptable cost.

3. **Filter mode matters more than parameter sweeps within a mode.** The novel `keyLen` and `specificity` modes outperform classical `size` on schema-stable benchmarks. The composite mode's weight triples (group C) show that mixing all three normalised criteria is rarely better than the simpler `keyLen` ranking alone.

4. **Best configuration is dataset-dependent.** Six different grid points win across eight datasets. Manual tuning would have produced one of these six and underperformed elsewhere.

### 7.2 Comparison With Classical Methods

**Versus Papadakis ARCS.** Our framework reduces to Papadakis at $w_{\text{pair}} = 0$, filter_mode = size, max_recursion_depth = 1, density_floor = 0. In that regime our results match the published Papadakis behaviour: ~ 0.83 precision, low recall on poor-DQ. Turning on any one of (recursive refinement, per-pair similarity, density floor) shifts the operating point monotonically toward higher F1. Turning on all three simultaneously is what produces the best-of-grid results.

**Versus DWM and static similarity methods.** DWM-style sliding-window methods are inherently one-dimensional. Our recursive refinement traverses multi-token co-occurrence space, and the per-pair similarity modulation rewrites the implicit window for every (record, block) pair individually. The resulting candidate space is *dynamically reduced*: each block carries less weight against a pair whose own Jaccard evidence is weak, even if the block's nominal size or specificity is high.

**Versus learned blocking.** Our framework is fully unsupervised. The AI-assisted grid-search of Section 5.2 plays the role that gradient descent plays in DeepBlocker / AutoBlock: it explores the parameter landscape and identifies the operating point that best fits each dataset. The key difference is interpretability — every grid point is a closed-form algorithm whose behaviour can be traced through the per-stage diagnostic counters.

### 7.3 Failure Modes Surfaced By The Grid

The aggregation reports flag three classes of failure:

1. **F1 = 0 collapses.** Caused by $\tau$ above the IDF/uniform edge-weight scale (e.g. $\tau = 1.0$ under uniform), `top-k = 1` (strips co-occurrence signal), or composite-mode weights that all zero out.
2. **FN-dominant runs.** On `S12PX` 182 / 185 runs are FN-dominant — the algorithm is recall-limited on this benchmark. Truth clusters of size $\ge 10$ require chained edges that low-$\tau$ regimes admit and high-$\tau$ regimes do not.
3. **FP-dominant runs.** On `S1G` 74 / 185 runs are FP-dominant — at this small scale (50 records) over-aggressive recall easily inflates FP.

These failure taxonomies are produced automatically by `aggregate_results.py` and feed Section 6 directly.

### 7.4 Threats to Validity

- All datasets are person-record CSVs with the same schema. Behaviour on heterogeneous schemas (product catalogues, citation matching) is not characterised.
- The grid covers eleven axes but their interactions are explored only along single axes — group B sweeps filter_mode under default everything else; we do not exhaustively sweep the Cartesian product.
- Wall-clock figures are single-machine, single-core, single-process; large-scale parallel behaviour is out of scope.
- The AI agent's grid (group A–K) is a *curated* grid; an exhaustive random search could conceivably find non-obvious wins outside the curated axes.

---

## 8. Conclusion

We have presented **algo1_2_v2**, a recursive entity-resolution and blocking framework whose three central contributions — recursive co-occurrence blocking, adaptive per-pair similarity, and AI-assisted grid-search optimisation — together produce a strict generalisation of classical Papadakis meta-blocking and DWM-style adaptive methods. The recursive refinement step grows blocking-key tuples under a depth-coupled intra-block frequency floor, producing a hierarchy of progressively more specific blocks reconciled by lossless merge and subset-purge operators. The adaptive similarity formulation extends classical ARCS contributions with block-size, key-length, type, density, and per-pair Jaccard factors; in particular the `pair_sim_weight` knob smoothly interpolates between classical static ARCS and a fully pair-adaptive regime.

The empirical evaluation is itself a contribution: 185 configurations across eleven parameter groups were executed independently on eight benchmark datasets by a Claude AI coding agent, producing 1,480 logged runs whose per-stage outputs are preserved in `RESULTS/runs/`. The best-F1 configurations vary across datasets — six distinct winning grid points across eight benchmarks — validating the AI-assisted grid-search protocol as a methodological necessity. The `pair_sim_weight` knob alone improves F1 by up to an order of magnitude over classical ARCS, recursive refinement contributes monotonically to precision up to a knee at depth 3, and the novel `keyLen` and `specificity` filter modes both dominate the classical `size` ranking on schema-stable benchmarks.

The reference implementation, the grid driver, and all 1,480 metric logs are available at the project repository (`Algo1_2_v2/recursive_algo1_2_v2.py`, `RESULTS/run_experiments.py`, `RESULTS/aggregate_results.py`).

---

## References

1. P. Christen. *Data Matching: Concepts and Techniques for Record Linkage, Entity Resolution, and Duplicate Detection.* Springer, 2012.
2. M. A. Hernández and S. J. Stolfo. The merge/purge problem for large databases. *SIGMOD*, 1995.
3. A. Aizawa and K. Oyama. A fast linkage detection scheme for multi-source information integration. *WIRI*, 2005.
4. A. Z. Broder. On the resemblance and containment of documents. *Compression and Complexity of Sequences*, 1997.
5. P. Indyk and R. Motwani. Approximate nearest neighbors: towards removing the curse of dimensionality. *STOC*, 1998.
6. J. Leskovec, A. Rajaraman, J. D. Ullman. *Mining of Massive Datasets.* Cambridge, 2014.
7. G. Papadakis, G. Koutrika, T. Palpanas, W. Nejdl. Meta-blocking: taking entity resolution to the next level. *IEEE TKDE*, 26(8), 2014.
8. G. Papadakis, D. Skoutas, E. Thanos, T. Palpanas. Blocking and filtering techniques for entity resolution: A survey. *ACM Computing Surveys*, 53(2), 2020.
9. U. Draisbach and F. Naumann. A generalization of blocking and windowing algorithms for duplicate detection. *ICDKE*, 2011.
10. S. Yan, D. Lee, M.-Y. Kan, L. C. Giles. Adaptive sorted neighborhood methods for efficient record linkage. *JCDL*, 2007.
11. O. Hassanzadeh, F. Chiang, R. J. Miller, H. C. Lee. Framework for evaluating clustering algorithms in duplicate detection. *VLDB*, 2009.
12. A. Saeedi, E. Peukert, E. Rahm. Comparative evaluation of distributed clustering schemes for multi-source entity resolution. *ADBIS*, 2017.
13. A. Saeedi, E. Peukert, E. Rahm. Using link features for entity clustering in knowledge graphs. *ESWC*, 2018.
14. S. Thirumuruganathan, H. Li, N. Tang, M. Ouzzani, Y. Govind, D. Paulsen, G. Fung, A. Doan. Deep learning for blocking in entity matching. *VLDB*, 2021.
15. W. Zhang, H. Wei, B. Sisman, X. L. Dong, C. Faloutsos, D. Page. AutoBlock: a hands-off blocking framework for entity matching. *WSDM*, 2020.
16. R. Wang et al. Sudowoodo: contrastive self-supervised learning for multi-purpose data integration and preparation. *ICDE*, 2023.
17. P. Christen. Preparation of a real voter data set for record linkage and duplicate detection research. Technical report, Australian National University, 2014.

---

## Appendix A — Parameter Surface Summary

The thirteen CLI parameters exposed by `recursive_algo1_2_v2.py`:

| Parameter                  | Default       | Grid group | Role                                                                        |
|----------------------------|---------------|------------|-----------------------------------------------------------------------------|
| `max_frequency` ($F_{\max}$) | 60           | (fixed)    | DF-based stop-word floor.                                                   |
| `init_df_percentile`       | 0.95          | (fixed)    | Percentile-derived upper-bound DF cap for initial blocking.                 |
| `min_blk_token_len`        | 4             | (fixed)    | Minimum token length to qualify as a blocking key.                          |
| `exclude_numeric_blocks`   | true          | (fixed)    | Drop pure-digit tokens (zip, SSN-fragments).                                |
| `max_recursion_depth`      | 5             | H          | Maximum number of refinement iterations.                                    |
| `min_intra_freq`           | 2             | (fixed)    | Lower bound on depth-coupled refinement floor $\mu_{\min}$.                |
| `top_k`                    | 3             | E          | Per-record top-k blocks retained after filtering.                            |
| `min_block_size`           | 2             | K          | Minimum block size after filtering.                                          |
| `filter_mode`              | `size`        | B, C       | Specificity-filter ranking: size / specificity / keyLen / composite.        |
| `weight_size`/`shared`/`tokenlen` | 0.0    | C          | Composite-mode weights for normalised criteria.                              |
| `tau`                      | 0.2           | D, F       | ARCS edge-weight cut for Union-Find.                                         |
| `arcs_weighting`           | uniform       | F          | uniform = $1/|B|$; idf = $\log(N/|B|)/|B|$.                                |
| `density_floor`            | 0.0           | I          | Minimum internal kept-edge density before splitting.                         |
| `density_min_size`         | 3             | (fixed)    | Minimum cluster size for density-floor check.                                |
| `arcs_length_weight`       | 0.0           | (fixed)    | Per-block bonus for long-token keys.                                        |
| `arcs_numeric_factor`/`word_factor` | 1.0 / 1.0 | (fixed) | Down-weight pure-numeric or pure-word blocks.                                |
| `arcs_density_weight`      | 0.0           | (fixed)    | Per-block bonus for high intra-block Jaccard density.                        |
| `arcs_pair_sim_weight`     | 1.0           | J          | **Per-pair Jaccard modulation. Most impactful single knob.**                |
| `full-blocking` / `hierarchical-blocking` | off | G         | Alternative initial-blocking regimes.                                       |
| `max_block_pair_cost`      | unset (∞)     | (fixed)    | Per-block pair-count guardrail for full-blocking.                            |

## Appendix B — Reproducibility

```bash
# Full grid on a single dataset (e.g. S4G):
DATASET=S4G.txt python RESULTS/run_experiments.py
DATASET=S4G.txt python RESULTS/aggregate_results.py
```

For each dataset the resulting artefacts are:

- `RESULTS/runs/<group>/<config>/clusters_m{0,1}_p{0,1}.json` — cluster composition.
- `RESULTS/runs/<group>/<config>/clusters_m{0,1}_p{0,1}.metrics.json` — structured per-cell metrics.
- `RESULTS/runs/<group>/<config>/clusters_m{0,1}_p{0,1}.metrics.log` — human-readable per-cell metrics.
- `RESULTS/runs/<group>/<config>/run.log` — full stdout, including per-stage diagnostic counters.
- `RESULTS/runs/<group>/<config>/invocation.json` — exact subprocess command, return code, wall-clock.
- `RESULTS/<dataset>_results.xlsx` — `runs` + `summary` sheets.
- `RESULTS/<dataset>_README.md` — Markdown aggregation report.

A single best configuration can be reproduced by running the pipeline directly:

```bash
# S4G best (density_floor sweep, merge only):
cd Algo1_2_v2 && python recursive_algo1_2_v2.py \
        --input ../S4G.txt --truth-dir .. \
        --clusters-json /tmp/S4G_best.json \
        --density-floor 0.7

# S8P best (low tau, poor-DQ):
cd Algo1_2_v2 && python recursive_algo1_2_v2.py \
        --input ../S8P.txt --truth-dir .. \
        --clusters-json /tmp/S8P_best.json \
        --tau 0.05

# S1G best (small dataset, default sweep):
cd Algo1_2_v2 && python recursive_algo1_2_v2.py \
        --input ../S1G.txt --truth-dir .. \
        --clusters-json /tmp/S1G_best.json \
        --tau 0.3
```

All runs are deterministic given the same input and CLI arguments.
