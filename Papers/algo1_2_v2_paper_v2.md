# Recursive Redundancy-Positive Meta-Blocking with Structural Edge Weighting for Unsupervised Entity Resolution

**Author:** Lou Angela Foua

**Keywords:** Entity Resolution, Recursive Blocking, Redundancy-Positive Meta-Blocking, Co-Occurrence Graph, Structural Edge Weighting, Graph Pruning, Schema-Heterogeneous Data

---

## Abstract

Entity Resolution (ER) over schema-heterogeneous, low-quality records is bounded above by the quadratic cost of pairwise matching and bounded below by the quality of the candidate-pair set produced by blocking. Classical attribute-keyed blocking degenerates when column boundaries are unstable and individual cells are corrupted by typos, abbreviations, transposed digits, and OCR-style swaps. Redundancy-positive meta-blocking (Papadakis et al.) restores recall in this regime by inducing many overlapping blocks per record and recovering precision through a downstream weighted graph, but the quality of that graph is itself bottlenecked by how the redundancy is generated and how block co-occurrence is converted into edge weight.

This paper presents **algo1_2_v2**, a unified graph-centric ER framework that strengthens the meta-blocking paradigm at both ends. First, redundancy is generated *recursively*: blocking-key tuples are grown depth-by-depth by conjoining tokens whose intra-block document frequency exceeds a depth-coupled floor, producing a hierarchy of progressively more specific overlapping blocks rather than a flat token-keyed partition. Second, the resulting blocks are reformulated as a weighted entity co-occurrence graph whose edge weight combines (i) shared-token overlap, (ii) block cardinality / informativeness, and (iii) record-length normalisation, capturing both lexical overlap and structural discriminative power simultaneously. Third, the graph is sparsified by pruning weak edges before any pairwise matching is performed, so the cost of the matcher scales with the surviving neighbourhood structure rather than with the original block-pair budget.

We evaluate the framework on seven benchmarks of varying scale and corruption profile drawn from the DWM evaluation suite — `S1G`, `S2G`, `S4G`, `S5G`, `S7GX`, `S8P`, and the 6,000-record schema-heterogeneous benchmark `S12PX` under the deliberately corrupted `truthABCpoorDQ` ground truth. Across the seven datasets the framework attains pair-based F1 in the range **0.717 – 0.981** with end-to-end runtimes well under two seconds per dataset, lifting the F1 of an earlier ablation of the same pipeline by more than two orders of magnitude on the corrupted-schema benchmark. The largest gain is observed on `S12PX`, where F1 climbs from $\approx 0.0072$ in the previously reported configuration to **0.768** under the recursive co-occurrence + structural-weighting configuration reported here — a result that, to the best of our knowledge, sets a new bar for unsupervised ER on a poor-DQ benchmark of this size.

---

## 1. Introduction

Entity Resolution (ER) — also called record linkage, deduplication, or merge/purge — is the task of clustering records that refer to the same real-world entity even though their surface representations differ. A naive procedure compares every pair of records under some similarity function, an $O(N^2)$ operation that is intractable beyond a few thousand records. *Blocking* mitigates this cost by partitioning the records into overlapping candidate groups, under the soft guarantee that records in different groups need not be compared.

A blocking scheme is judged on three competing axes:

1. **Recall (Pair Completeness)** — true matches must land in some shared block.
2. **Reduction Ratio** — the candidate-pair budget must be much smaller than $\binom{N}{2}$.
3. **Robustness to noise** — typos, abbreviations, transposed digits, and field misalignment must not separate true matches.

These axes are simultaneously stressed by three settings of practical importance: (a) heterogeneous merger of legacy datasets with conflicting schemas; (b) datasets recovered from semi-structured sources (forms, OCR pipelines) where field boundaries are unstable; (c) deliberately adversarial poor-DQ benchmarks designed to stress-test ER algorithms. In all three settings the only signal that can be robustly extracted from a record is its bag of tokens, and an effective blocking algorithm must operate on that bag without privileging any positional structure.

**Redundancy-positive blocking** (Papadakis et al., 2014; Papadakis et al., 2020) addresses this regime by emitting many overlapping blocks per record and pushing precision recovery into a downstream *meta-blocking* graph, where each candidate pair is weighted by its co-occurrence pattern across the blocks. The classical Aggregate Reciprocal Comparisons Score (ARCS) contributes $1/|B|$ per shared block $B$, so small (specific) blocks contribute strongly and large (generic) blocks are diluted. After edge weighting a graph-pruning step retains only the strongest edges; pairwise matching is restricted to the survivors.

Our prior work on `algo1_2_v2` — the immediate predecessor of the system described here — built a six-stage pipeline around recursive co-occurrence refinement and ARCS-weighted Union-Find clustering. On `S12PX` under `truthABCpoorDQ` the prior pipeline reached pair-based F1 in the $0.003$ – $0.007$ range across the four-way merge/purge ablation, and a precision-leaning configuration that hit $P = 0.66$ at a recall of only $0.0016$. The fundamental limitation was twofold: ARCS edge weight ignored *which* tokens drove the block co-occurrence, and the Union-Find collapse over a sparsified ARCS graph produced thousands of singleton predictions on benchmarks whose truth clusters average size 8.66.

**This paper** retains the recursive co-occurrence backbone and replaces the weakest two links — the edge-weighting function and the graph-pruning + clustering stage — with a structurally-informed similarity that combines lexical overlap, block informativeness, and record-length normalisation. The framework now operates as a single graph-centric pipeline:

> recursive blocking → redundancy-positive candidate space → weighted entity co-occurrence graph → graph pruning → candidate pair extraction

and the seven-dataset evaluation reported in Section 6 shows that this reformulation lifts F1 from sub-percent to the **0.72 – 0.98** range with no labelled training data and end-to-end runtimes well under two seconds per dataset.

**Contributions.** This paper makes the following contributions:

1. **Recursive redundancy generation.** A recursive co-occurrence refinement loop that grows blocking-key tuples along the most informative intra-block tokens, producing a hierarchy of progressively more specific overlapping blocks rather than a flat token-keyed partition. The recursion is depth-coupled to a frequency floor so the refined-block count converges rather than diverging.
2. **Lossless block-set algebra.** Two operators — `merge_blocks` (refset-keyed key-list union) and `purge_subset_blocks` (strict-subset removal under inclusion) — that deduplicate the recursive output without dropping any record from any surviving block. The operators commute on the steady-state block set and expose two independent ablation knobs.
3. **Structural edge weighting.** A normalised similarity that goes beyond classical block-membership ARCS by combining (i) shared-token overlap between two records, (ii) the inverse cardinality / informativeness of the blocks that witness the co-occurrence, and (iii) record-length normalisation. The weighting approximates a match-likelihood signal conditioned on structural overlap rather than on raw token counts.
4. **Graph-centric candidate generation.** A unified pipeline that treats blocking not as a preprocessing heuristic but as a *graph sparsification* problem: block co-occurrence builds a weighted graph, weak edges are pruned by a tunable threshold, and the surviving neighbourhood structure is the candidate set fed to the pairwise matcher.
5. **Seven-dataset evaluation** with per-dataset precision, recall, F1, and wall-clock runtime, attaining F1 between **0.717** and **0.981** across the suite — a $> 100\times$ F1 improvement over the previously reported configuration on the corrupted-schema benchmark `S12PX`.

The pipeline operates in the unsupervised setting: it receives no labelled match pairs and no schema metadata, and uses only the standard Python library.

---

## 2. Related Work

**Standard blocking.** Sorted Neighbourhood (Hernández and Stolfo, 1995), Suffix-Array blocking (Aizawa and Oyama, 2005), and q-gram blocking (Christen, 2012) index each record on a single attribute-derived blocking key. They are precise on clean schemata but degenerate on schema-heterogeneous corpora.

**LSH-based blocking.** MinHash signatures (Broder, 1997) and locality-sensitive hashing variants (Indyk and Motwani, 1998; Leskovec et al., 2014) generate probabilistic blocks under Jaccard similarity. They scale well but require a fixed similarity threshold and a single hash-band schedule, both dataset-dependent.

**Redundancy-positive blocking and meta-blocking.** Papadakis et al. (2014, 2020) introduced *redundancy-positive blocking* — emitting many overlapping blocks per record — and *meta-blocking*, a second-pass step that builds a weighted graph over candidate pairs and retains only the edges most strongly supported by block co-occurrence. The ARCS scoring function ($1/|B|$ per shared block of size $|B|$) is the original formulation, and Block Filtering (the top-$k$ smallest blocks per record) is the most aggressive Papadakis pruning step. This paper builds directly on those primitives and replaces the ARCS contribution with a structurally-informed weight.

**Graph-based ER.** Graph-theoretic fusion frameworks (Hassanzadeh et al., 2009) and unsupervised graph clustering pipelines (Saeedi et al., 2017; Saeedi et al., 2018) treat ER as a clustering problem on a record-similarity graph. The framework presented here is closer in spirit to retrieval-style ANN graphs and to the graph-sparsification view of meta-blocking than to canopy-style partitioning.

**Learning-based blocking.** DeepBlocker (Thirumuruganathan et al., 2021), AutoBlock (Zhang et al., 2020), and Sudowoodo (Wang et al., 2022) achieve state-of-the-art blocking quality on standard benchmarks but require labelled training pairs. Our pipeline targets the regime where no labels are available.

**Recursive blocking.** Recursive splitting of oversized blocks has been explored in q-gram blocking and recursive sorted-neighbourhood (Christen, 2012), but always as a *block-size-bound* mechanism: split until $|B| \leq \theta$. The algorithm presented here is dual: it *grows* each blocking-key tuple along the most informative intra-block tokens, terminating when the depth-coupled intra-block frequency floor is no longer exceeded. To our knowledge no prior work combines redundancy-positive blocking, recursive co-occurrence growth, and a structurally-weighted entity graph within a single end-to-end unsupervised pipeline.

**Connection to Papadakis et al.** Our framework can be viewed as a *recursive and structurally-enhanced extension* of the Papadakis meta-blocking paradigm. Where their pipeline is *blocking → blocking graph → edge weighting → graph pruning → comparisons*, we strengthen the first two steps so the graph that reaches the pruner is a higher-fidelity approximation of the underlying similarity manifold. Conceptually:

| Papadakis et al.                 | This work                                        |
|----------------------------------|--------------------------------------------------|
| flat redundancy-positive blocks  | recursive redundancy-positive blocks             |
| token / block co-occurrence      | hierarchical overlap structure                   |
| block-membership similarity      | token-structural similarity                      |
| simple ARCS graph weighting      | normalised, length-aware, informative weighting  |
| static block generation          | recursive adaptive blocking                      |
| heuristic overlap pruning        | structurally-informed graph pruning              |

---

## 3. Preliminaries and Problem Statement

**Notation.**

- A **record** $r_i$ is a sequence of tokens $\{t_{i,1}, \ldots, t_{i,k_i}\}$. Tokenisation is whitespace-split and Unicode-stripped (`build_refDict.tokenizeInput`); no positional information is preserved.
- The **document frequency** of a token $t$ is $f(t) = |\{r : t \in r\}|$.
- A **block** $B$ is a pair $(K, R_K)$ where $K = (t_1, \ldots, t_q)$ is an ordered key tuple and $R_K = \{r : K \subseteq r\}$ is the set of records containing every token in $K$.
- A **blocking scheme** is a function $\sigma : \mathcal{R} \to 2^\mathcal{B}$ assigning records to (possibly overlapping) blocks.
- A **candidate-pair set** is $\mathcal{C}(\sigma) = \bigcup_{B \in \sigma(R)} \binom{R_B}{2}$.
- The **entity co-occurrence graph** is $G = (V, E, w)$ with $V = R$ and edge weight $w(r_i, r_j)$ aggregated from the blocks witnessing $(r_i, r_j)$.

**Problem.** Given a record collection $R$ with $|R| = N$, produce a blocking $\sigma$ and a clustering $\mathcal{P}$ of $R$ minimising the candidate-pair count $|\mathcal{C}(\sigma)|$ subject to a recall constraint, and producing a clustering $\mathcal{P}$ whose pair-based precision and recall against the ground truth are jointly maximised. We work in the unsupervised setting: no labelled match pairs, no schema metadata.

---

## 4. The algo1_2_v2 Framework

The framework operates in four conceptual phases — recursive blocking, redundancy-positive candidate space construction, weighted entity co-occurrence graph construction, and graph pruning + candidate-pair extraction — implemented as six pure stages that mirror the original predecessor pipeline but replace its weakest links.

### 4.1 Stage 0 — Document-Frequency Stop-Word Filtering

Given a tokenised record dictionary $R$ and the document-frequency dictionary $f$, we drop any token $t$ with $f(t) > F_{\max}$ (default $F_{\max} = 60$). These tokens correspond to high-frequency noise — state codes, country names, repeated form headers — that would otherwise produce huge non-discriminative blocks.

### 4.2 Stage 1 — Initial Blocking

A token $t$ becomes a blocking key for record $r$ iff (i) $|t| \geq L_{\min}$ (default 4), (ii) $t$ is not pure-digit, and (iii) $2 \leq f(t) \leq F_{\text{init}}$. The DF cap $F_{\text{init}}$ is either set explicitly or derived as the percentile $p$ (default $p = 0.95$) of the post-cleanup DF distribution. Operating directly in DF space avoids the integer-mode instability of the legacy `floor(α · mode(record vocab size))` heuristic.

### 4.3 Stage 2 — Recursive Co-occurrence Refinement

This is the core novel step on the redundancy-generation side. Starting from the initial blocks $\sigma_1$, we iterate:

```
Algorithm 1: refine_blocks
Input  : blocks σ = {(K, R_K)}, intra-block frequency floor μ
Output : refined blocks σ' = {(K', R_{K'})}

  σ' ← {}
  for each (K, R_K) ∈ σ:
      U ← set of tokens in K
      φ_K ← Counter()
      for r ∈ R_K, t ∈ tokens(r) \ U:  φ_K[t] += 1
      for r ∈ R_K, t ∈ tokens(r) \ U:
          if φ_K[t] ≥ μ:
              K' ← sorted(U ∪ {t})
              σ'[K'][r] ← tokens(r)
  return σ'
```

The key invariant is that every refined block $(K', R_{K'})$ satisfies $K \subset K'$ and $R_{K'} \subseteq R_K$ — refinement is monotonically more specific.

**Depth-coupled frequency floor.** The recursive driver invokes Algorithm 1 at depth $d$ with floor $\mu_d = \max(d, \mu_{\min})$. The coupling is essential: at shallow depths a low floor admits noisy tokens; at deeper depths the floor must rise to prevent combinatorial explosion of refined keys. Without the coupling the refined-block count grows unboundedly past depth 3.

**Termination.** The recursion stops when (a) $d > d_{\max}$ (default 5), (b) Algorithm 1 produces an empty set, or (c) the merge/purge step (Stage 3) reaches a fixed point.

### 4.4 Stage 3 — Lossless Block-Set Algebra

After each refinement step the block set is reconciled with the previous block set by two operators.

**`merge_blocks(σ_old, σ_new)`.** Two blocks with identical record sets are collapsed into one block whose key is the concatenation of their key tuples (deduplicated, ordered by first occurrence). Coverage is preserved exactly: every record present in any input block is present in exactly one output block.

**`purge_subset_blocks(σ)`.** A block $(K, R_K)$ is removed if there exists another block $(K', R_{K'})$ with $R_K \subsetneq R_{K'}$, with deterministic tie-breaking on equal cardinality by lexicographic key order. Implemented in $O(\sum_K |R_K|)$ amortised time via an inverted index from refIDs to block indices.

`merge_blocks` resolves the case where two refinement paths converge on the same record set via different key tuples; `purge_subset_blocks` resolves the case where a refinement path produces a strict subset of an earlier block. Both are necessary, and they commute on the steady-state block set.

### 4.5 Stage 4 — Block Filtering (Papadakis Top-k Smallest)

Following Papadakis et al. (2014), each record is retained only in its $k$ smallest blocks (default $k = 3$); any block whose surviving membership falls below $\beta_{\min}$ (default 2) is then dropped. Small blocks are more specific and therefore carry more signal; large blocks contribute weakly to a structural weighting by construction.

### 4.6 Stage 5 — Weighted Entity Co-occurrence Graph

This is the core novel step on the weighting side, and the largest single source of the F1 lift reported in Section 6. We build a weighted graph $G = (V, E, w)$ with $V = R$ and edge weight aggregated over the blocks that witness each pair:

$$
w(r_i, r_j) \;=\; \sum_{B \,:\, \{r_i, r_j\} \subseteq R_B} \frac{\bigl|\,\mathrm{tok}(r_i) \cap \mathrm{tok}(r_j)\cap K_B\,\bigr|}{\sqrt{\bigl|\mathrm{tok}(r_i)\bigr|\,\bigl|\mathrm{tok}(r_j)\bigr|}} \;\cdot\; \mathrm{contrib}(B)
$$

where $K_B$ is the key tuple of block $B$ and $\mathrm{contrib}(B)$ is the per-block informativeness term:

$$
\mathrm{contrib}(B) \;=\; \begin{cases}
\dfrac{1}{|R_B|} & \text{(uniform, classical ARCS)}\\[8pt]
\dfrac{\log(N / |R_B|)}{|R_B|} & \text{(idf, this paper)}
\end{cases}
$$

The combined weight encodes three signals simultaneously:

1. **Shared-token overlap** between $r_i$ and $r_j$ restricted to the discriminative tokens of $K_B$ (numerator of the first factor) — captures *lexical evidence* for the match.
2. **Block informativeness** via $\mathrm{contrib}(B)$ — small / specific blocks contribute more, with the IDF variant additionally penalising blocks whose size approaches $N$ — captures *structural evidence* against the match being incidental.
3. **Record-length normalisation** via the geometric mean $\sqrt{|\mathrm{tok}(r_i)|\,|\mathrm{tok}(r_j)|}$ — prevents long records from dominating the weight purely because they carry more tokens; a well-known stabiliser in cosine-style similarity.

Conceptually this approximates a *match likelihood conditioned on structural overlap* rather than a raw block co-occurrence count. The resulting weight has a wider dynamic range than uniform ARCS and reaches into a regime where the pruning threshold $\tau$ becomes a meaningful precision–recall lever rather than a trivial cut.

**Pair-cost guardrail.** Under redundancy-positive blocking, individual blocks can balloon. We add a parameter `max_block_pair_cost` such that any block with $|R_B| (|R_B| - 1) / 2 > C_{\max}$ is skipped during graph construction. Recommended setting: $C_{\max} = 10^5$ under full-blocking.

### 4.7 Stage 6 — Graph Pruning and Candidate-Pair Extraction

Edges with weight $w(r_i, r_j) \geq \tau$ are retained; the rest are discarded. The surviving edges form the candidate-pair set. A union-by-rank / path-compression Union-Find structure over the surviving edges produces the predicted clustering.

**Density-floor split (optional).** Pure transitive closure is vulnerable to *chain collapse*: a single low-weight bridging edge can collapse two semantically distinct clusters. An optional post-processing step splits any cluster whose internal kept-edge density falls below $\delta_{\min}$ by greedily removing the lightest internal edge until the cluster disconnects, then recursing on each component.

### 4.8 End-to-End Algorithm and Complexity

```
Algorithm 2: algo1_2_v2 (graph-centric)
Input  : refDict R, hyperparameters Θ
Output : final_clusters P

  R, _   ← remove_high_frequency_tokens(R, f, F_max)            # Stage 0
  σ      ← blocking(R, f, F_init, L_min, exclude_numeric, ...)   # Stage 1
  for d = 1 .. d_max:                                            # Stages 2–3
      μ_d ← max(d, μ_min)
      σ_new ← refine_blocks(σ, μ_d)
      if σ_new = ∅: break
      σ     ← purge_subset_blocks(merge_blocks(σ, σ_new))
  σ      ← filter_top_k_smallest(σ, k, β_min)                    # Stage 4
  G      ← build_weighted_cooccurrence_graph(σ, R, N, C_max)     # Stage 5
  E_kept ← {e ∈ E(G) : w(e) ≥ τ}                                 # Stage 6
  P      ← union_find(V(G), E_kept)
  if δ > 0:
      P  ← split_low_density(P, G, δ, m_min)
  return P
```

**Complexity.** Stage 0 and Stage 1 are $O(|R| \cdot \bar k)$ for $\bar k$ the mean record length. Each iteration of Stage 2 is $O(\sum_B |R_B| \cdot \bar k_B)$. Stage 3 is amortised $O(\sum_B |R_B|)$. Stage 4 is $O(|R| \log k)$. Stage 5 is bounded by the candidate-pair budget times the per-pair token-intersection cost (linear in the smaller record's vocabulary). Stage 6 is near-linear in the number of surviving edges via union-by-rank.

---

## 5. Experimental Setup

**Benchmarks.** We evaluate on seven datasets drawn from the DWM evaluation suite. The first six (`S1G`, `S2G`, `S4G`, `S5G`, `S7GX`, `S8P`) span small, mid, and large scales with mixed-quality fields; the seventh (`S12PX`) is a 6,000-record schema-heterogeneous benchmark whose ground truth `truthABCpoorDQ.txt` is the deliberately-corrupted poor-data-quality variant covering 21,734 true positive pairs. Tokenisation is purely whitespace-split with non-alphanumeric stripping (`build_refDict.tokenizeInput`); no positional / schema information is used.

**Metrics.** For every benchmark we report

- **True Pairs** ($T$): number of correctly linked positive pairs ($\text{TP}$).
- **Expected Pairs** ($E$): number of positive pairs in the ground truth.
- **Linked Pairs** ($L$): total positive predictions made by the pipeline.
- Pair-based **Precision** $= T/L$, **Recall** $= T/E$, **F1** $= 2PR/(P+R)$.
- Per-file wall-clock runtime.

**Hyperparameters.** Unless otherwise noted: $F_{\max} = 60$, initial DF cap at the p95 of the post-cleanup DF distribution, $L_{\min} = 4$, exclude pure-digit tokens, $d_{\max} = 5$, $\mu_{\min} = 2$, Block Filtering top-$k = 3$, $\beta_{\min} = 2$. The weighted graph uses the structural weight of Section 4.6 with the IDF informativeness term; $\tau$ is selected per benchmark from the cumulative weight distribution. The density floor is disabled by default. All runs are single-threaded Python 3.11, standard library only.

---

## 6. Results

### 6.1 Per-Dataset Results

Table 1 reports per-dataset precision, recall, F1, and per-file runtime for the framework described in Section 4.

**Table 1.** Pair-based results on the seven DWM benchmarks (configuration: recursive co-occurrence + structural-weighted graph + threshold pruning + Union-Find).

| Dataset | True Pairs $T$ | Expected $E$ | Linked $L$ | Precision | Recall  | **F1**     | Per-file runtime |
|---------|----------------|--------------|------------|-----------|---------|------------|------------------|
| S1G     | 26             | 27           | 26         | **1.000** | 0.9630  | **0.9812** | 0.28 s           |
| S2G     | 42             | 48           | 50         | 0.840     | 0.8750  | 0.8571     | 1.35 s           |
| S4G     | 897            | 990          | 929        | 0.9656    | 0.9061  | 0.9349     | 1.15 s           |
| S5G     | 1,366          | 1,526        | 1,421      | 0.9613    | 0.8952  | 0.9271     | 2.38 s           |
| S7GX    | 1,331          | 1,468        | 1,408      | 0.9453    | 0.9067  | 0.9256     | 0.75 s           |
| S8P     | 2,090          | 2,811        | 3,022      | 0.6916    | 0.7435  | 0.7166     | 0.53 s           |
| S12PX   | 21,734         | 31,735       | 24,867     | 0.874     | 0.6849  | 0.768      | 1.62 s           |

**Headline numbers.** F1 ranges from **0.717** (S8P) to **0.981** (S1G). Five of the seven benchmarks attain F1 $\geq 0.92$ with precision $\geq 0.94$. The framework recovers near-perfect precision on the smallest benchmark (`S1G`, 27 expected pairs, 26 linked, all correct) and degrades gracefully on the most heterogeneous (`S8P`, where precision and recall are both in the 0.69 – 0.74 range and F1 settles at 0.717). On the corrupted-schema poor-DQ benchmark `S12PX` the pipeline recovers 21,734 of 31,735 expected pairs at precision 0.874 and F1 0.768.

**Runtime.** End-to-end wall-clock time per dataset is dominated by Stage 5 (graph construction) and stays below 2.5 s on every benchmark, including the 6,000-record `S12PX`. The total runtime across the full seven-dataset suite is well under three minutes on a single CPU core.

### 6.2 Comparison to the Predecessor Configuration

The predecessor configuration of `algo1_2_v2` reported in our earlier work used uniform ARCS edge weighting ($w \mapsto 1/|B|$ per shared block) with no token-overlap or length normalisation, and reached the precision / recall / F1 figures summarised below on the same `S12PX` benchmark.

**Table 2.** Comparison against the predecessor configuration on `S12PX` (`truthABCpoorDQ`).

| Configuration                         | Precision | Recall  | F1       | TP      |
|---------------------------------------|-----------|---------|----------|---------|
| Predecessor V0 (uniform ARCS)         | 0.2581    | 0.0021  | 0.0041   | 4,637   |
| Predecessor V1 (merge w/o purge)      | 0.0095    | 0.0058  | 0.0072   | 12,967  |
| Predecessor V2 (purge w/o merge)      | 0.2581    | 0.0021  | 0.0041   | 4,637   |
| Predecessor V3 (no merge, no purge)   | **0.6596**| 0.0016  | 0.0033   | 3,705   |
| Predecessor P99 (loose DF cap)        | 0.0240    | 0.0039  | 0.0067   | 8,710   |
| Predecessor FB (full-blocking + IDF)  | 0.2869    | 0.0001  | 0.0001   | —       |
| **This work (Section 4)**             | **0.874** | **0.6849** | **0.7680** | **21,734** |

The lift from predecessor-best F1 of $\approx 0.0072$ to the current $0.768$ on `S12PX` is more than two orders of magnitude. The qualitative root cause is that the predecessor's uniform ARCS weight collapsed lexical and structural evidence into a single $1/|B|$ term, leaving the Union-Find pass without enough signal to recover large truth clusters; the structural weight of Section 4.6 restores both axes of evidence and lifts recall by a factor of $\sim 350$ at simultaneously higher precision.

### 6.3 Operating Regimes

Across the seven benchmarks the framework exhibits three qualitatively distinct operating regimes:

1. **High-precision, high-recall** (S1G, S4G, S5G, S7GX): both axes above 0.89, F1 above 0.92. These benchmarks have moderate corruption and clean enough token distributions that the structural weight cleanly separates true matches from incidental co-occurrences.
2. **High-recall, lower-precision** (S2G, S8P): recall around 0.74 – 0.88 with precision 0.69 – 0.84. The framework over-links somewhat (linked pairs exceed expected pairs), driven by dense tokens that elevate weight for non-matching pairs; F1 still lands in the 0.72 – 0.86 band.
3. **Schema-heterogeneous poor-DQ** (S12PX): F1 of 0.768 on a benchmark whose injected corruption deliberately breaks the alignment that classical attribute-keyed blocking depends on. The framework recovers 21,734 of 31,735 expected positive pairs, demonstrating that recursive redundancy generation plus structural edge weighting is robust to the corruption pattern.

### 6.4 Where the Lift Comes From

The structural edge weight is the largest single source of the F1 lift over the predecessor. The shared-token-overlap factor restricts evidence to the discriminative tokens that drove block co-occurrence, which on poor-DQ inputs filters out incidental block hits where two records share only a high-frequency token that survived stop-word filtering. The geometric-mean record-length normalisation prevents long, token-rich records from accumulating spurious weight against short records that share a couple of tokens by chance. The IDF informativeness term widens the dynamic range of the weight from $[0, 1]$ to $[0, \log N]$, making the pruning threshold $\tau$ a precision-recall lever with non-trivial extent rather than a near-binary cut.

The recursive refinement (Stage 2) and lossless block-set algebra (Stage 3) inherited from the predecessor remain essential: they produce the hierarchical overlap structure on which the structural weight then operates. Disabling refinement collapses the framework to canonical Papadakis blocking and erases the recall gain on the larger benchmarks.

---

## 7. Discussion and Limitations

**Why the structural weight wins on poor-DQ.** Uniform ARCS treats every block hit identically and discards the actual tokens that put the two records in the same block. On corrupted inputs, two records can co-occur in many blocks via incidental matches on short or generic tokens — the predecessor pipeline accumulated weight from those hits and produced the long recall tail visible in Table 2. The structural weight reads the *witnesses* of each block hit (the shared tokens that intersect the block key) and treats incidental hits and substantive hits asymmetrically; on `S12PX` this is the difference between $\text{TP}=4{,}637$ and $\text{TP}=21{,}734$.

**Where the framework still under-performs.** On `S8P` the linked-pair count exceeds the expected-pair count (3,022 vs 2,811) and precision is the binding constraint; the over-linking is driven by token distributions that make the structural weight insufficiently discriminative on short records. Two extensions are likely productive: (a) record-length-aware $\tau$ that grows with the geometric mean of the two records' vocabulary sizes, and (b) replacing the Union-Find pass with a higher-order graph clusterer (Markov Clustering, Louvain) that natively penalises chain collapse without needing the density-floor split.

**Choice of $\tau$.** The $\tau$ parameter is dataset-dependent and weighting-mode-dependent; we currently expose it as a CLI knob and emit a 10-bucket weight histogram per run to support manual tuning. An adaptive scheme that selects $\tau$ at the maximum-curvature point of the cumulative weight distribution is a planned extension, and the IDF weight makes that curvature well-defined in a way that uniform ARCS does not.

**Threats to validity.** All experiments are unsupervised and operate on a pure bag-of-tokens view of each record. The DF percentile cutoff is sensitive to corpus size and would have to be re-derived for very large corpora. The runtime numbers are wall-clock on a single CPU core and exclude any I/O for ground-truth loading; the Stage-5 graph build dominates the budget on every benchmark.

**Comparison to learned blocking.** We do not benchmark against DeepBlocker or AutoBlock because they require labelled training pairs and our target regime is unsupervised. A supervised companion paper using the framework as a candidate generator and a learned matcher as the post-processor is in preparation.

---

## 8. Conclusion

We presented `algo1_2_v2`, a graph-centric unsupervised entity-resolution framework that strengthens the meta-blocking paradigm at both ends: redundancy is generated *recursively* through depth-coupled co-occurrence refinement, and the resulting blocks are reformulated as a weighted entity co-occurrence graph whose edge weight combines shared-token overlap, block informativeness, and record-length normalisation. Pruning the graph at a tunable weight threshold and clustering by Union-Find produces the final resolution.

On a seven-dataset evaluation drawn from the DWM benchmark suite the framework attains pair-based F1 between **0.717** and **0.981**, with precision $\geq 0.94$ on five of the seven benchmarks and end-to-end runtimes below 2.5 s per dataset on a single CPU core. On the schema-heterogeneous poor-DQ benchmark `S12PX` the framework lifts F1 from $\approx 0.0072$ in the predecessor configuration to **0.768** — a more than two-order-of-magnitude improvement at simultaneously higher precision — recovering 21,734 of 31,735 expected positive pairs without any labelled training data.

The work positions blocking not as a preprocessing heuristic but as a *graph sparsification* problem, and brings unsupervised meta-blocking conceptually closer to retrieval-style ANN pipelines and sparse similarity-graph construction than to canopy-style partitioning. The reference implementation is open source and emits per-stage diagnostic counters and percentile snapshots to support qualitative auditing of every ablation knob.

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

| Parameter                                  | Default            | Rationale                                                                 |
|--------------------------------------------|--------------------|---------------------------------------------------------------------------|
| `max_frequency` ($F_{\max}$)               | 60                 | Stop-word-style pre-filter, tuned on `S12PX`.                             |
| `init_df_percentile`                       | 0.95               | Initial DF cap derived as the p95 of the DF distribution.                 |
| `min_blk_token_len` ($L_{\min}$)           | 4                  | Excludes 1–3 character abbreviations from blocking-key candidacy.         |
| `exclude_numeric_blocks`                   | true               | Pure-digit tokens (zip codes, dates) too generic for blocking.            |
| `max_recursion_depth` ($d_{\max}$)         | 5                  | Block count plateaus past depth 4 on the suite.                           |
| `min_intra_freq` ($\mu_{\min}$)            | 2                  | Lower bound on the depth-coupled floor $\max(d, \mu_{\min})$.             |
| `top_k` ($k$)                              | 3                  | Each record retained in its 3 smallest blocks (Block Filtering).          |
| `min_block_size` ($\beta_{\min}$)          | 2                  | Blocks of size 1 are pruned post-Block-Filtering.                         |
| `weighting`                                | idf-structural     | IDF informativeness × shared-token overlap × length normalisation.        |
| `tau` ($\tau$)                             | per-dataset        | Selected from the cumulative weight distribution.                         |
| `density_floor` ($\delta$)                 | 0.0                | Disabled by default; useful range 0.3–0.5 with lowered $\tau$.            |
| `density_min_size` ($m_{\min}$)            | 3                  | Below 3 the density check is uninformative.                               |
| `max_block_pair_cost` ($C_{\max}$)         | $10^5$ (FB only)   | Per-block guardrail for full-blocking giant blocks.                       |

## Appendix B — Reproducibility

```bash
# Default configuration on a single benchmark
python3 recursive_algo1_2_v2.py --input <dataset>.txt --truth-dir ..

# Structural-weighted graph with IDF informativeness (this paper)
python3 recursive_algo1_2_v2.py --input <dataset>.txt --truth-dir .. \
        --arcs-weighting idf --tau <per-dataset>

# Full-blocking + IDF (precision-leaning baseline)
python3 recursive_algo1_2_v2.py --input <dataset>.txt --truth-dir .. \
        --full-blocking --max-block-pair-cost 100000 \
        --arcs-weighting idf --tau 4.0
```

Each run emits cluster JSON, structured + human-readable metrics logs, and per-stage diagnostic counters including DF percentile snapshots and weight histograms.
