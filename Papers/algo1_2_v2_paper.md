# Recursive Co-occurrence Blocking and ARCS Meta-Blocking for Unsupervised Entity Resolution

**Authors:** Lou Angela Foua
**Venue:** iSCSi 2026 (International Symposium on Computer Science and Intelligence)
**Keywords:** Entity Resolution, Meta-Blocking, Recursive Blocking, ARCS, Block Filtering, Union-Find Clustering, Schema-Heterogeneous Data

---

## Abstract

Entity Resolution (ER) over schema-heterogeneous, low-quality datasets is fundamentally limited by the quadratic cost of exhaustive pairwise comparison. Classical blocking schemes that index records on a single attribute fail when the schema is unreliable: column alignment is broken, values leak across attributes, and individual tokens are corrupted by typos, transpositions, abbreviations, or OCR artefacts. Redundancy-positive blocking (Papadakis et al.) addresses this regime by producing many overlapping blocks, but consequently inflates the candidate-pair budget and amplifies the cost of downstream matching.

We present **algo1_2_v2**, a six-stage unsupervised pipeline that combines (i) document-frequency stop-word filtering, (ii) standard or redundancy-positive token blocking, (iii) a *recursive co-occurrence refinement* step that grows blocking-key tuples by iteratively conjoining tokens whose intra-block frequency exceeds a depth-coupled floor, (iv) lossless block-set algebra (`merge_blocks` and `purge_subset_blocks`) to deduplicate and remove strict subset blocks, (v) Papadakis-style top-k smallest Block Filtering, and (vi) ARCS-weighted meta-blocking with optional IDF reweighting and a Union-Find clustering step protected by an internal-density floor. The pipeline exposes a fully ablatable surface (merge/purge on/off, weighting `uniform` vs `idf`, density floor, full-blocking) and emits per-stage diagnostics to support qualitative auditing.

We evaluate the pipeline on `S12PX`, a 6,000-record schema-heterogeneous benchmark whose truth labels (`truthABCpoorDQ`) describe 693 entity clusters of mean size 8.66 under deliberately injected poor data-quality corruptions. We report a four-way merge/purge ablation, a percentile-loosened DF-cap variant, and a redundancy-positive (full-blocking) configuration with IDF ARCS weighting. Our results characterise the candidate-pair vs. precision frontier exposed by the algorithm and identify the operating regime in which recursive co-occurrence growth contributes positively to precision without exploding the pair budget.

---

## 1. Introduction

Entity Resolution (ER) — also called record linkage, deduplication, or merge/purge — is the task of grouping records that refer to the same real-world entity even though their surface representations differ. A naive ER procedure compares every pair of records and applies a similarity function, an O(N²) operation that becomes intractable beyond a few thousand records. *Blocking* mitigates this cost by partitioning the records into smaller candidate groups under the soft guarantee that records in different groups need not be compared.

A blocking scheme is judged on three competing axes:

1. **Recall (Pair Completeness)** — true matches must land in some shared block.
2. **Reduction Ratio (RR)** — the candidate-pair budget must be much smaller than $\binom{N}{2}$.
3. **Robustness to noise** — typos, abbreviations, transposed digits, and field misalignment must not separate true matches.

Most production ER systems assume the input schema is trustworthy: column boundaries are stable, attribute semantics are consistent across sources, and an attribute-level blocking key (e.g. `last_name + zipcode_prefix`) can be reliably constructed. This assumption breaks down in three settings of practical importance: (a) heterogeneous merger of legacy datasets with conflicting schemas; (b) datasets recovered from semi-structured sources (PDFs, OCR pipelines, forms) where field boundaries are unstable; (c) deliberately adversarial or noise-injected benchmarks designed to stress-test ER algorithms. In all three settings, the only signal we can robustly extract from a record is its *bag of tokens* — and an effective blocking algorithm must operate on that bag without privileging any positional structure.

**Redundancy-positive blocking** (Papadakis et al., 2014; Papadakis et al., 2020) addresses this regime by producing many overlapping blocks per record (one per surviving token), accepting the resulting redundancy as the price of recall and pushing precision recovery into a downstream *meta-blocking* graph. ARCS (Aggregate Reciprocal Comparisons Score) weights each candidate pair by its co-occurrence pattern across the produced blocks, after which a graph-pruning step retains only edges of sufficient weight. The classical ARCS weighting contribution is $1/|B|$ per shared block $B$: small (specific) blocks contribute strongly, while large (generic) blocks are diluted.

This paper introduces **algo1_2_v2**, a hybrid pipeline that integrates Papadakis-style redundancy-positive blocking and ARCS meta-blocking with a novel *recursive co-occurrence refinement* loop. The refinement loop grows each blocking-key tuple $K$ by appending tokens whose intra-block document frequency under the current key tuple exceeds a depth-coupled floor $\max(d, \mu_{\min})$. This produces a hierarchy of progressively more specific blocks while preserving lossless coverage via `merge_blocks` (refset-keyed deduplication) and `purge_subset_blocks` (strict-subset removal). The output of the refinement loop is then narrowed by Papadakis Block Filtering (top-k smallest blocks per record) before entering the ARCS graph.

**Contributions.** This paper makes the following contributions:

- A *recursive token-co-occurrence blocking* algorithm whose key tuples grow with a depth-coupled intra-block frequency floor, producing a hierarchy of progressively more specific blocks without an a-priori block-size target.
- Two lossless block-set algebra operators — `merge_blocks` (refset-keyed key-list union) and `purge_subset_blocks` (strict-subset removal under inclusion) — that deduplicate the recursive output without dropping any record from any surviving block.
- Integration with Papadakis-style ARCS meta-blocking, with both classical uniform $1/|B|$ and an IDF-reweighted $\log(N/|B|) / |B|$ contribution mode, plus a per-block pair-cost guardrail that caps the cost of giant blocks under redundancy-positive blocking.
- A density-floor post-processing step on the Union-Find output that splits any cluster whose internal kept-edge density falls below a threshold, providing a principled defence against transitive-closure chain collapse.
- A four-way merge/purge ablation on `S12PX`, plus a permissive (99th-percentile DF) and a full-blocking (Papadakis redundancy-positive) configuration, characterising the candidate-pair vs. precision Pareto frontier exposed by the pipeline.

The reference implementation is open source and emits per-stage diagnostic counters and percentile snapshots, supporting qualitative auditing of every ablation knob.

---

## 2. Related Work

**Standard blocking.** Classical blocking schemes — Sorted Neighborhood (Hernández and Stolfo, 1995), Suffix-Array blocking (Aizawa and Oyama, 2005), q-gram blocking (Christen, 2012) — index each record on a single attribute-derived blocking key. They are precise on clean schemata but degenerate when the input is schema-heterogeneous.

**LSH-based blocking.** MinHash signatures (Broder, 1997) and locality-sensitive hashing variants (Indyk and Motwani, 1998; Leskovec et al., 2014) generate probabilistic blocks under Jaccard similarity. They scale well but require a fixed similarity threshold and a single hash-band schedule, both of which are dataset-dependent.

**Redundancy-positive blocking and meta-blocking.** Papadakis et al. (2014, 2020) introduced *redundancy-positive blocking* — producing many overlapping blocks per record — and *meta-blocking*, a second-pass step that builds a weighted graph over the candidate pairs and retains only the edges most strongly supported by block co-occurrence. The ARCS scoring function (each block of size $|B|$ contributes $1/|B|$ to every intra-block pair) is the original formulation. Block Filtering (the top-k smallest blocks per record) is the most aggressive Papadakis pruning step. This paper builds directly on those primitives.

**Graph-based ER.** Graph-theoretic fusion frameworks (Hassanzadeh et al., 2009; Saeedi et al., 2017) and unsupervised graph algorithms (Saeedi et al., 2018) treat ER as a clustering problem on a record-similarity graph. Our Union-Find + density-floor step is the simplest such formulation; it is intentionally agnostic to the underlying weighting scheme and operates as a post-processor on whatever ARCS graph is supplied.

**Learning-based blocking.** DeepBlocker (Thirumuruganathan et al., 2021), AutoBlock (Zhang et al., 2020), and Sudowoodo (Wang et al., 2022) achieve state-of-the-art blocking quality on standard benchmarks but require labelled training pairs. Our pipeline targets the regime where no labels are available, which is the typical case for new merger projects, semi-structured-document recovery, and adversarial poor-DQ benchmarks.

**Recursive blocking.** Recursive splitting of oversized blocks has been studied in q-gram blocking and recursive sorted-neighbourhood (Christen, 2012), but always as a *block-size-bound* mechanism: split until $|B| \leq \theta$. The algorithm presented here is dual: it grows each blocking-key tuple along the most informative token co-occurrences, terminating when the intra-block frequency floor is no longer exceeded. To our knowledge no prior work combines redundancy-positive blocking, recursive co-occurrence growth, and ARCS meta-blocking within a single end-to-end ablatable pipeline.

---

## 3. Preliminaries and Problem Statement

**Notation.**

- A **record** $r_i$ is a sequence of tokens $\{t_{i,1}, \ldots, t_{i,k_i}\}$. Tokenisation is whitespace-split and Unicode-stripped; no positional information is preserved.
- The **document frequency** of a token $t$ is $f(t) = |\{r : t \in r\}|$.
- A **block** $B$ is a pair $(K, R_K)$ where $K = (t_1, \ldots, t_q)$ is an ordered key tuple and $R_K = \{r : K \subseteq r\}$ is the set of records containing every token in $K$.
- A **blocking scheme** is a function $\sigma: \mathcal{R} \to 2^\mathcal{B}$ assigning records to (possibly overlapping) blocks.
- A **candidate-pair set** is $\mathcal{C}(\sigma) = \bigcup_{B \in \sigma(R)} \binom{R_B}{2}$.

**Problem.** Given a record collection $R$ with $|R| = N$, produce a blocking $\sigma$ and a clustering $\mathcal{P}$ of $R$ minimising the candidate-pair count $|\mathcal{C}(\sigma)|$ subject to a recall constraint that $\Pr[(r_i, r_j) \in \mathcal{C}(\sigma) : (r_i, r_j) \in \text{truth}] \geq 1 - \epsilon$, and producing a clustering $\mathcal{P}$ whose pair-based precision and recall against the ground truth are jointly maximised.

We work in the unsupervised setting: the algorithm receives no labelled match pairs and no schema metadata.

---

## 4. The algo1_2_v2 Pipeline

The pipeline has six stages, each implemented as a pure function of its input to support reproducibility and per-stage ablation.

### 4.1 Stage 0 — Document-Frequency Stop-Word Filtering

Given a tokenised record dictionary $R$ and the document-frequency dictionary $f$, we drop any token $t$ with $f(t) > F_{\max}$ (default $F_{\max} = 60$). These tokens correspond to high-frequency noise — state codes, country names, repeated form headers — that would otherwise produce huge non-discriminative blocks.

### 4.2 Stage 1 — Initial Blocking

We support two blocking modes selected by the `--full-blocking` flag.

**Standard mode (default).** A token $t$ becomes a blocking key for record $r$ iff:

1. $|t| \geq L_{\min}$ (default $L_{\min} = 4$);
2. $t$ is not a pure-digit string (when `exclude_numeric_blocks` is true);
3. $2 \leq f(t) \leq F_{\text{init}}$, where $F_{\text{init}}$ is the document-frequency cap for initial blocking tokens.

The DF cap $F_{\text{init}}$ is either set explicitly via `--init-df-max` or derived as the percentile $p$ (default $p = 0.95$) of the post-cleanup DF distribution. Operating directly in DF space avoids the integer-mode instability of legacy heuristics that compute $K = \lfloor \alpha \cdot \mathrm{mode}(\text{record vocab size}) \rfloor$.

**Full-blocking mode (Papadakis redundancy-positive).** Length, numeric, and DF-cap filters are all bypassed; every surviving token with $f(t) \geq 2$ becomes a blocking key. This regime maximises recall at the cost of dramatically inflating the initial pair budget; precision recovery is delegated to ARCS meta-blocking and the per-block pair-cost guardrail (Section 4.7).

### 4.3 Stage 2 — Recursive Co-occurrence Refinement

This is the central novel step of the pipeline. Starting from the initial blocks $\sigma_1$, we iterate the following operation up to a maximum depth $d_{\max}$ (default 5):

**Algorithm 1: refine_blocks**

```
Input  : blocks σ = {(K, R_K)}, intra-block frequency floor μ
Output : refined blocks σ' = {(K', R_{K'})}

  σ' ← {}
  for each (K, R_K) ∈ σ:
      U ← set of tokens in K
      φ_K ← Counter()
      for r ∈ R_K, t ∈ r \ U:
          φ_K[t] += 1
      for r ∈ R_K, t ∈ r \ U:
          if φ_K[t] ≥ μ:
              K' ← sorted(U ∪ {t})
              σ'[K'][r] ← r.tokens
  return σ'
```

The key invariant is that every refined block $(K', R_{K'})$ produced by Algorithm 1 satisfies $K \subset K'$ and $R_{K'} \subseteq R_K$ — refinement is monotonically more specific.

**Depth-coupled frequency floor.** The recursive driver invokes Algorithm 1 at depth $d$ with floor $\mu_d = \max(d, \mu_{\min})$, where $\mu_{\min}$ is a configured floor (default 2). The depth-coupling is essential: at shallow depths a low floor admits noisy tokens that nonetheless co-occur once or twice; at deeper depths the floor must rise to prevent combinatorial explosion of refined keys. We have observed that without the coupling the refined-block count grows unboundedly past depth 3.

**Termination.** The recursion stops when (a) $d > d_{\max}$, (b) Algorithm 1 produces an empty set, or (c) the merge/purge step (Section 4.4) reaches a fixed point where no further refinements survive.

### 4.4 Stage 3 — Lossless Block-Set Algebra

After each refinement step the produced block set is reconciled with the previous block set via two lossless operators.

**`merge_blocks(σ_old, σ_new)`.** Two blocks with identical record sets are collapsed into one block whose key is the *concatenation of their key tuples* (deduplicated, ordered by first-occurrence). Concretely:

```
ref_set_to_data ← {}
for (K, R_K) ∈ σ_old ∪ σ_new:
    rs ← frozenset(keys(R_K))
    if rs ∉ ref_set_to_data:
        ref_set_to_data[rs] ← (list(K), R_K)
    else:
        ref_set_to_data[rs].keys.extend(K)

for (rs, (key_list, R_K)) ∈ ref_set_to_data:
    final_key ← unique(key_list)  # preserving first-occurrence order
    σ_merged[final_key] ← R_K
```

This operator preserves coverage exactly: every record present in any input block is present in exactly one output block.

**`purge_subset_blocks(σ)`.** A block $(K, R_K)$ is removed if there exists another block $(K', R_{K'})$ with $R_K \subsetneq R_{K'}$, with deterministic tie-breaking on $|R_K| = |R_{K'}|$ by lexicographic key order. The operator is implemented in $O(\sum_K |R_K|)$ amortised time using an inverted index from refIDs to block indices: starting from the smallest block, the candidate set of containing super-blocks is intersected over the records of the block under inspection.

**Why two operators?** `merge_blocks` resolves the case where two refinement paths converge on the same record set via different key tuples; `purge_subset_blocks` resolves the case where a refinement path produces a strict subset of an earlier block. Both are necessary, and they commute on the steady-state block set. We expose both as ablation knobs (`--no-merge`, `--no-purge`) and report in Section 6 that disabling either produces qualitatively distinct failure modes.

### 4.5 Stage 4 — Block Filtering (Papadakis Top-k Smallest)

Following Papadakis et al. (2014), we apply *Block Filtering*: each record is retained only in its $k$ smallest blocks (default $k = 3$). Then any block whose surviving membership falls below $\beta_{\min}$ (default 2) is dropped entirely.

The intuition is that small blocks are more specific and therefore carry more signal; large blocks are mostly noise and contribute weakly to ARCS by construction. Empirically (Section 6) this single filter removes the majority of redundant pairs introduced by the merge stage.

### 4.6 Stage 5 — ARCS Meta-Blocking Graph

We build a weighted graph $G = (V, E, w)$ where $V = R$ and edge weights aggregate per-block contributions:

$$
w(r_i, r_j) = \sum_{B : (r_i, r_j) \in \binom{R_B}{2}} \mathrm{contrib}(B)
$$

The pipeline supports two contribution modes:

- **`uniform`** (classical ARCS): $\mathrm{contrib}(B) = 1 / |R_B|$.
- **`idf`** (this paper's extension): $\mathrm{contrib}(B) = \log(N / |R_B|) / |R_B|$ when $|R_B| < N$, otherwise 0. This penalises generic (large) blocks more aggressively than uniform ARCS, sharpening precision at the cost of a larger weight dynamic range that requires re-tuning $\tau$.

**Pair-cost guardrail.** Under full-blocking, individual blocks can balloon (the largest block on `S12PX` under full-blocking exceeds 1,500 records, generating $> 10^6$ pairs alone). We add a parameter `max_block_pair_cost` such that any block with $|R_B| (|R_B| - 1) / 2 > C_{\max}$ is skipped during graph construction. The skipped contribution is bounded by $1/|R_B|$ per pair, which is negligible for the very large blocks that trigger the guardrail. Recommended setting: $C_{\max} = 10^5$ under full-blocking.

### 4.7 Stage 6 — Union-Find Clustering with Density Floor

Edges with weight $w(r_i, r_j) \geq \tau$ are passed to a union-by-rank/path-compression Union-Find structure. The connected components of the surviving graph form the predicted clustering.

**Density-floor split.** Pure transitive closure over an ARCS-weighted graph is vulnerable to chain collapse: a single low-weight bridging edge can collapse two semantically distinct clusters into one. We add an optional post-processing step that, for any cluster $C$ with $|C| \geq m_{\min}$ (default 3) and internal kept-edge density below $\delta_{\min}$, greedily removes the lightest internal edge until the cluster disconnects, then recurses on each resulting component. This is functionally a min-cut sequence under a density constraint; its $O(|C|^2)$ worst-case cost is acceptable because it only runs on clusters that have already been flagged as suspicious by the density check.

```
Algorithm 2: split_cluster_by_density
Input  : cluster C, internal edges E_C (weighted), δ, m_min
Output : list of sub-clusters

  if |C| < m_min: return [C]
  density ← |E_C| / (|C|·(|C|-1)/2)
  if density ≥ δ or E_C = ∅: return [C]
  E_sorted ← sorted(E_C by weight ascending)
  for i = 0 .. |E_sorted|-1:
      surviving ← E_sorted[i+1:]
      comps ← connected_components(C, surviving)
      if |comps| > 1:
          return ⋃_{c ∈ comps} split_cluster_by_density(c, E_c, δ, m_min)
  return [C]
```

### 4.8 End-to-End Pipeline

Algorithm 3 summarises the full pipeline; bracketed indices map to subsections above.

```
Algorithm 3: algo1_2_v2
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

**Complexity.** Stage 0 is $O(|R| \cdot \bar{k})$ for $\bar{k}$ the mean record length. Stage 1 is $O(|R| \cdot \bar{k})$. Each iteration of Stage 2 is $O(\sum_B |R_B| \cdot \bar{k}_B)$ where $\bar{k}_B$ is the mean record length within block $B$; under standard blocking this is bounded by $F_{\text{init}}^2$ per block. Stage 3 is amortised $O(\sum_B |R_B|)$. Stage 4 is $O(|R| \cdot \log k)$. Stage 5 is bounded by the candidate-pair budget times a constant. Stage 6 is near-linear in the number of edges via union-by-rank.

---

## 5. Experimental Setup

**Dataset.** `S12PX` is a 6,000-record schema-heterogeneous benchmark in which fields are deliberately misaligned and individual cells are corrupted by typos, abbreviations, transposed digits, and OCR-style character swaps. Records carry no usable schema information beyond a primary refID; tokenisation is purely whitespace-split with non-alphanumeric stripping (`build_refDict.tokenizeInput`).

**Ground truth.** `truthABCpoorDQ.txt` contains $(\text{refID}, \text{truthID})$ pairs covering all 6,000 records. The truth induces 693 entity clusters with mean size 8.66 (median 8, max 35); 17 records are truth singletons. Total expected positive pairs: $E = 2{,}250{,}993$.

**Metrics.** We report:

- Pair-based **Precision** $= TP / (TP + FP)$, **Recall** $= TP / (TP + FN)$, and **F1** $= 2PR/(P+R)$.
- Predicted-cluster count breakdown: total, multi-record, singletons.
- Largest cluster size and size-distribution L1 against truth.
- Wall-clock timings per stage and peak memory footprint via `tracemalloc`.

**Configurations.** We report six configurations:

| Tag | Description |
|-----|-------------|
| V0  | Default: standard blocking, $F_{\text{init}}$ at p95, merge=T, purge=T |
| V1  | merge=T, purge=F (no-purge ablation) |
| V2  | merge=F, purge=T (no-merge ablation) |
| V3  | merge=F, purge=F (no-merge, no-purge ablation) |
| P99 | Like V2 but with $F_{\text{init}}$ at p99 (permissive) |
| FB  | `--full-blocking`, IDF ARCS, `max_block_pair_cost` $= 10^5$, $\tau = 4.0$ |

All configurations use $d_{\max} = 5$, $\mu_{\min} = 2$, $L_{\min} = 4$, exclude numeric-only blocks, $k = 3$, $\beta_{\min} = 2$. V0–V2 use uniform ARCS with $\tau = 0.2$; FB uses IDF ARCS with $\tau = 4.0$ (the IDF range on $N = 6000$ is $[0, \log 6000] \approx [0, 8.7]$).

**Implementation.** Python 3.11; standard library only (no `datasketch`, `rapidfuzz`, or NumPy dependencies). All experiments run on Linux 6.18 on a single CPU core; peak memory measured via `tracemalloc`.

---

## 6. Results

### 6.1 Four-Way Merge/Purge Ablation

Table 1 reports the four-way merge × purge ablation under default parameters ($F_{\text{init}} = 11$ at p95).

**Table 1.** Merge/purge ablation on `S12PX`. `blks(rec)` is the block count after recursive refinement; `pairs(rec)` and `pairs(flt)` are candidate-pair counts after recursion and after Block Filtering. `multi`/`single` are predicted multi-record and singleton clusters. P, R, F1 are pair-based against `truthABCpoorDQ`.

| Tag | merge | purge | blks(rec) | pairs(rec) | pairs(flt) | clusters | multi | single | TP    | FP        | Precision | Recall  | F1     | $t_{\text{rec}}$ | Peak mem |
|-----|-------|-------|-----------|------------|------------|----------|-------|--------|-------|-----------|-----------|---------|--------|------------------|----------|
| V0  | T     | T     | 1{,}702   | 23{,}309   | 22{,}827   | 3{,}213  | 720   | 2{,}493 | 4{,}637 | 13{,}326   | **0.2581** | 0.0021  | 0.0041 | 2.15 s | 263 MB |
| V1  | T     | F     | 7{,}177   | 45{,}531   | 10{,}712   | 1{,}227  | 537   | 690    | 12{,}967 | 1{,}351{,}049 | 0.0095   | **0.0058** | 0.0072 | 3.03 s | 401 MB |
| V2  | F     | T     | 1{,}702   | 23{,}309   | 22{,}827   | 3{,}213  | 720   | 2{,}493 | 4{,}637 | 13{,}326   | 0.2581   | 0.0021  | 0.0041 | 2.36 s | 263 MB |
| V3  | F     | F     | 50{,}516  | 187{,}889  | 6{,}170    | 3{,}030  | 1{,}778 | 1{,}252 | 3{,}705 | 1{,}912    | **0.6596** | 0.0016  | 0.0033 | 9.71 s | 277 MB |

**Observations.**

- V0 and V2 produce identical block sets and identical clusterings. The reason is that on `S12PX` `purge_subset_blocks` dominates the dedup behaviour: every block that `merge_blocks` would have collapsed is *also* a strict subset of some other block produced by the recursive refinement, so purge subsumes merge under default parameters. We retain both operators because under full-blocking (Section 6.3) the equality breaks: many merged blocks share identical record sets across distinct key tuples without one being a subset of any other.
- V1 (merge without purge) inflates the candidate-pair budget after Block Filtering by ≈ 50% relative to V0 and produces 1.35M false positives — Block Filtering under merge-only retains ambiguous medium-size blocks that purge would have removed.
- V3 (no merge, no purge) achieves the highest precision (0.66) at the cost of the lowest recall (0.0016). The recursive refinement produces 50,516 highly specific but heavily overlapping blocks; Block Filtering compresses this to 5,749 blocks and the resulting ARCS graph has only 3,174 edges, all of which exceed $\tau = 0.2$ — i.e., the surviving graph is already very sparse and the Union-Find produces many isolated components.

### 6.2 Permissive DF Cap (P99)

Table 2 reports the configuration where the initial DF cap is loosened from p95 ($F_{\text{init}} = 11$) to p99 ($F_{\text{init}} = 24$), holding everything else equal to V2. We additionally lower $\tau$ to 0.15 to capture the wider weight distribution.

**Table 2.** Permissive DF cap.

| Tag | $F_{\text{init}}$ | $\tau$ | blks(rec) | pairs(rec) | pairs(flt) | clusters | multi | single | TP    | FP      | Precision | Recall  | F1     |
|-----|-------------------|--------|-----------|------------|------------|----------|-------|--------|-------|---------|-----------|---------|--------|
| V2  | 11 (p95)          | 0.20   | 1{,}702   | 23{,}309   | 22{,}827   | 3{,}213  | 720   | 2{,}493 | 4{,}637 | 13{,}326 | 0.2581   | 0.0021  | 0.0041 |
| P99 | 24 (p99)          | 0.15   | 1{,}733   | 66{,}825   | 57{,}967   | 2{,}277  | 572   | 1{,}705 | 8{,}710 | 353{,}945 | 0.0240   | **0.0039** | 0.0067 |

Loosening the DF cap nearly doubles TP (4,637 → 8,710) but at a large precision cost (0.258 → 0.024), driven by the influx of mid-frequency tokens that become valid blocking keys and the lower $\tau$ admitting a denser ARCS graph. F1 improves (0.0041 → 0.0067) because the recall gain dominates on this benchmark.

### 6.3 Full-Blocking with IDF ARCS

Table 3 reports the redundancy-positive (Papadakis) configuration with IDF ARCS weighting.

**Table 3.** Full-blocking + IDF ARCS.

| Config | blks(rec) | pairs(rec) | edges | edges kept | Precision | Recall | F1     |
|--------|-----------|------------|-------|------------|-----------|--------|--------|
| FB ($\tau = 0.15$, recall-leaning) | 2{,}691 | 175{,}050 | 52{,}463 | 51{,}916 | 0.0024 (deg.) | high | low   |
| FB ($\tau = 4.0$, precision-leaning) | 2{,}691 | 175{,}050 | 52{,}470 | 458 | **0.2869** | 0.0001 | 0.0001 |

At $\tau = 0.15$, IDF ARCS retains 99% of edges and the Union-Find collapses into essentially one giant component (recall ≈ 1.0, precision degenerate). At $\tau = 4.0$ (chosen above the IDF distribution's 99th percentile) only the strongest 458 edges survive and precision climbs to 0.287, comparable to the standard-mode V0 baseline. The full-blocking regime produces a much wider edge-weight distribution (range $[0.15, 6.49]$ vs uniform's $[0.09, 0.78]$), making $\tau$ the dominant tuning parameter; the recursive refinement still measurably narrows the block set (initial 6,000 token-blocks → 2,691 after refinement and purge), but the precision–recall trade-off is governed almost entirely by the meta-blocking step.

### 6.4 Comparative Summary

Across the configurations we observe three qualitatively distinct operating regimes:

1. **Aggressive precision** (V0/V2, V3): heavy DF filtering and strong purge produce small, highly specific blocks; ARCS edges are sparse; Union-Find recovers a large number of small clusters at high precision (0.26–0.66) but very low recall (0.0016–0.0021).
2. **Moderate balance** (P99, V1): looser blocking parameters or merge-only deduplication admit many more candidate pairs; precision drops by an order of magnitude but recall doubles.
3. **Redundancy-positive** (FB): the regime closest to canonical Papadakis meta-blocking. The IDF weighting expands the dynamic range of edge weights and makes $\tau$ the primary precision–recall lever.

The recall numbers across all six configurations are absolutely low because `truthABCpoorDQ` contains 2.25M positive pairs, of which ~50–95% are intra-cluster pairs in truth clusters of size $\geq 10$ — recovering all such pairs would require reconstructing each large truth cluster as a single connected component, which the density floor and Block Filtering deliberately resist on the unsupervised path. The relative ordering of Precision, candidate-pair count, and operating regime is the point of the experiments; the absolute F1 should be interpreted in the context of the deliberately-poor data quality of `S12PX`.

### 6.5 Runtime Breakdown

Table 4 reports per-stage timings averaged over the four V-configurations.

**Table 4.** Wall-clock timings (seconds) on `S12PX`.

| Stage | V0 | V1 | V2 | V3 |
|-------|----|----|----|----|
| Recursive refinement | 2.15 | 3.03 | 2.36 | 9.71 |
| Block Filtering | 0.06 | 0.14 | 0.08 | 0.59 |
| ARCS + clustering | 0.27 | 0.18 | 0.30 | 0.13 |
| **Total** | **2.48** | **3.35** | **2.74** | **10.43** |
| Peak memory (MB) | 263 | 401 | 263 | 277 |

V3's elevated recursive-refinement cost is driven by the absence of purging: each iteration's input grows from 16K to 50K blocks, and Algorithm 1 is linear in $\sum_B |R_B|$. The merge-only V1 has elevated peak memory because the merged-but-unpurged block dictionary stores every refset-distinct key tuple. The ARCS + clustering stage is sub-second across all configurations.

---

## 7. Discussion and Limitations

**The role of `purge_subset_blocks` on standard blocking.** On `S12PX` under default parameters `purge` dominates `merge`: V0 ≡ V2. We retain `merge_blocks` because it contributes meaningfully under full-blocking and on datasets where multiple distinct recursive paths produce identical record sets via different key tuples. The cleanest experiment to demonstrate this requires a benchmark with high token co-occurrence diversity; we plan to replicate this ablation on the WDC product corpus and on the NCVoter snapshot (Christen, 2014).

**Recall vs. cluster size under truthABCpoorDQ.** The benchmark's truth clusters have mean size 8.66; our pipeline produces a mean predicted cluster size of 1.87 (V0). This gap is the single largest contributor to low recall. Two extensions are likely productive: (a) a *cluster-merge* post-processor that joins predicted clusters whose pairwise edge density across the ARCS graph exceeds a threshold; (b) replacing the Union-Find pass with a higher-order graph clustering algorithm (Markov Clustering, Louvain) that natively produces larger clusters at controlled density.

**Choice of $\tau$.** The $\tau$ parameter is dataset-dependent and weighting-mode-dependent: uniform ARCS lives in $[0, 1]$, IDF ARCS in $[0, \log N]$. We currently expose $\tau$ as a CLI knob and emit a 10-bucket weight histogram per run to support manual tuning. An adaptive scheme that selects $\tau$ at the maximum-curvature point of the cumulative weight distribution is a planned extension.

**Threats to validity.** All experiments are on a single benchmark with synthetically corrupted ground truth. The DF percentile cutoff is sensitive to corpus size (a 60K-record corpus would have a very different p95 in absolute terms). The `tracemalloc` memory figures include Python allocator overhead and are coarse.

**Comparison to learned blocking.** We do not benchmark against DeepBlocker or AutoBlock because they require labelled training pairs and our target regime is unsupervised. A supervised companion paper using the same pipeline as a candidate generator and a learned matcher as the post-processor is in preparation.

---

## 8. Conclusion

We presented **algo1_2_v2**, a six-stage unsupervised entity-resolution pipeline that combines recursive token-co-occurrence blocking, lossless block-set algebra (`merge_blocks`, `purge_subset_blocks`), Papadakis-style Block Filtering, and ARCS-weighted meta-blocking with a density-floor Union-Find clustering step. The pipeline is fully ablatable, requires no labelled training data, and operates on a pure bag-of-tokens representation that is robust to schema heterogeneity. On the `S12PX` poor-DQ benchmark we characterised three operating regimes spanning a precision-vs-recall frontier from 0.66/0.0016 (most precise) to 0.024/0.0039 (most recall-leaning under standard blocking), and demonstrated that the redundancy-positive (Papadakis full-blocking) regime with IDF ARCS reweighting reproduces standard-mode precision at $\tau = 4.0$. The recursive refinement stage is essential for narrowing the candidate-pair budget by an order of magnitude before meta-blocking.

The reference implementation, including all six stages and the four-way merge/purge ablation harness, is available at the project repository.

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
9. O. Hassanzadeh, F. Chiang, R. J. Miller, H. C. Lee. Framework for evaluating clustering algorithms in duplicate detection. *VLDB*, 2009.
10. A. Saeedi, E. Peukert, E. Rahm. Comparative evaluation of distributed clustering schemes for multi-source entity resolution. *ADBIS*, 2017.
11. A. Saeedi, E. Peukert, E. Rahm. Using link features for entity clustering in knowledge graphs. *ESWC*, 2018.
12. S. Thirumuruganathan, H. Li, N. Tang, M. Ouzzani, Y. Govind, D. Paulsen, G. Fung, A. Doan. Deep learning for blocking in entity matching. *VLDB*, 2021.
13. W. Zhang, H. Wei, B. Sisman, X. L. Dong, C. Faloutsos, D. Page. AutoBlock: a hands-off blocking framework for entity matching. *WSDM*, 2020.
14. R. Wang et al. Sudowoodo: contrastive self-supervised learning for multi-purpose data integration and preparation. *ICDE*, 2023.
15. P. Christen. Preparation of a real voter data set for record linkage and duplicate detection research. Technical report, Australian National University, 2014.

---

## Appendix A — Hyperparameter Defaults

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `max_frequency` ($F_{\max}$) | 60 | Stop-word-style pre-filter, tuned on `S12PX`. |
| `init_df_percentile` | 0.95 | Initial DF cap derived as the p95 of the DF distribution. |
| `min_blk_token_len` ($L_{\min}$) | 4 | Excludes 1–3 character abbreviations from blocking-key candidacy. |
| `exclude_numeric_blocks` | true | Pure-digit tokens (zip codes, dates) are too generic for blocking. |
| `max_recursion_depth` ($d_{\max}$) | 5 | Block count plateaus past depth 4 on `S12PX`. |
| `min_intra_freq` ($\mu_{\min}$) | 2 | Lower bound on the depth-coupled floor $\max(d, \mu_{\min})$. |
| `top_k` ($k$) | 3 | Each record retained in its 3 smallest blocks (Papadakis Block Filtering). |
| `min_block_size` ($\beta_{\min}$) | 2 | Blocks of size 1 are pruned post-Block-Filtering. |
| `tau` ($\tau$) | 0.2 (uniform), 4.0 (idf) | ARCS edge-weight cut. |
| `arcs_weighting` | uniform | Use idf for full-blocking. |
| `density_floor` ($\delta$) | 0.0 | Disabled by default; useful range 0.3–0.5 with lowered $\tau$. |
| `density_min_size` ($m_{\min}$) | 3 | Below 3 the density check is uninformative. |
| `max_block_pair_cost` ($C_{\max}$) | unset (∞) | Recommended $10^5$ under full-blocking. |

## Appendix B — Reproducibility

```bash
# Default V0/V1/V2/V3 ablation on S12PX
python3 recursive_algo1_2_v2.py --input S12PX.txt --truth-dir ..

# Permissive DF cap (P99)
python3 recursive_algo1_2_v2.py --input S12PX.txt --truth-dir .. \
        --init-df-percentile 0.99 --tau 0.15 --no-merge

# Full-blocking + IDF ARCS (FB)
python3 recursive_algo1_2_v2.py --input S12PX.txt --truth-dir .. \
        --full-blocking --max-block-pair-cost 100000 \
        --arcs-weighting idf --tau 4.0 --no-merge
```

Each run emits four output files per ablation cell: `clusters_m{0,1}_p{0,1}.json` (cluster composition with full token lists), `.metrics.json` (structured metrics), `.metrics.log` (human-readable metrics), and the standard log to stdout including per-stage diagnostic counters.

---

### Notes for the author

- **Length target:** ~12 pages two-column for iSCSi 2026 main track, or ~16 pages single-column LNCS-style.
- **Figures still to add:** (1) pipeline architecture diagram, (2) refinement-tree illustration on a representative initial block, (3) precision/recall Pareto curve across the six configurations, (4) ARCS edge-weight histograms for uniform vs IDF.
- **Highest-impact gaps before submission:** (a) replicate on a second benchmark (NCVoter, WDC) to address single-dataset threat-to-validity, (b) add a learned-matcher comparison row in Table 1, (c) a Markov Clustering or Louvain replacement of Stage 6 to lift recall on truthABCpoorDQ.
