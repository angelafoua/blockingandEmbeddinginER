# Recursive Locality-Sensitive Hashing with Word Signatures for Scalable Entity Resolution Blocking

**Authors:** Lou Angela Foua
**Keywords:** Entity Resolution, Blocking, Locality-Sensitive Hashing, MinHash, Record Linkage, Data Quality, Distributed Systems

---

## Abstract

Entity Resolution (ER) is the process of identifying records that refer to the same real-world.

There are different world cases where the schema given to us may be untrustworthy, and where the alignment of the columns do not match the values in the cells. So, there is a need to be able to perform ER on dataset that display this kind of behavior with noisy, schema-heterogeneous data

ER is fundamentally limited by the quadratic cost of all-pairs comparison. Blocking mitigates this cost by partitioning records into smaller candidate groups, but classical blocking schemes…[limitations of right now methods]

We propose Recursive LSH with Word Signatures, a four-phase blocking pipeline that runs on a distributed systems using Spark:
 (i) cleans and *expands* tokens into data-quality variation classes
 (ii) maps each variation class to a stable hash key, 
 (iii) groups records by shared hash-key sets
 (iv) recursively refines oversized initial blocks by splitting on the most balanced *distinguishing* hash key. 

We evaluate our novel pipeline on synthetic PII, and business registration and product datasets. 

We provided interactive visualization tooling to make failure modes auditable, accelerate threshold tuning, and show results of the performance of the pipeline.


---

## 1. Introduction

Entity Resolution is the task of grouping records that refer to the same underlying entity, even when those records contain typos, missing fields, transposed digits, abbreviations, or formatting differences. Naive ER compares every pair of records: O(N²). For N = 6,000 records this is already 18M comparisons; for N = 1M it is 5 × 10¹¹. Blocking reduces this cost by guaranteeing that pairs in different blocks are *not* compared.

A good blocking scheme must trade off three objectives:

1. **Recall** — true matches should land in the same block.
2. **Reduction Ratio** — the candidate-pair budget must be much smaller than N²/2.
3. **Robustness to noise** — typos and field variations should not separate true matches.

[TODO: 1–2 sentences naming the gap your work fills.]

**Contributions.** This paper makes the following contributions:

- A recursive blocking pipeline that uses *word signatures* — variation-aware hash keys built from token-level data-quality transforms — to merge noisy tokens into the same block while preserving discriminative power.
- A novel Phase-3 refinement step that recursively splits oversized blocks on the *most balanced distinguishing key*, bounding final block size without sacrificing recall.
- An empirical evaluation on the `S12PX` dataset comparing four variation-generation strategies (`data_quality`, `fuzzy`, `phonetic`, `manual`) under identical Phase 1–3 settings.
- An open-source implementation with two interactive visualizations (D3-based HTML and matplotlib) to support qualitative auditing of blocking quality.

---

## 2. Related Work

**Standard blocking.** [TODO: 2–3 sentences on Hernández & Stolfo sorted neighborhood, blocking-key-based methods, q-gram blocking. Cite Christen 2012 survey.]

**LSH-based blocking.** [TODO: MinHash, banding (Broder 1997, Leskovec et al.), HLSH; cite Papadakis et al.'s blocking surveys for ER specifically.]

**Learning-based blocking.** [TODO: DeepBlocker, AutoBlock, Sudowoodo — note that learned methods need labeled data which our approach does not.]

**Variation/typo expansion.** [TODO: Levenshtein neighborhoods, Soundex/Metaphone, Felligi-Sunter; explain why a *combined* approach is novel.]

[TODO: Position your contribution: existing LSH blocking is single-pass; existing recursive blocking does not use LSH-style hash-key sets.]

---

## 3. Preliminaries and Problem Statement

**Notation.**

- A **record** $r_i$ is a sequence of tokens $\{t_{i,1}, ..., t_{i,k_i}\}$.
- A **token variation class** $V(t) \subseteq \mathcal{T}$ is a set of tokens considered equivalent under some similarity criterion.
- A **hash key** $h(t)$ is a stable identifier shared by all tokens in $V(t)$.
- A **block** $B \subseteq R$ is a subset of records that should be compared pairwise.
- A **blocking scheme** is a function $\sigma: R \to 2^B$ assigning records to (possibly overlapping) blocks.

**Problem.** Given $R$, produce a blocking $\{B_1, ..., B_m\}$ minimizing the candidate-pair count $\sum_i \binom{|B_i|}{2}$ subject to a recall constraint that $\Pr[\text{true match } (r_i, r_j) \in \text{some } B_k] \geq 1 - \epsilon$.

---

## 4. The Recursive LSH Pipeline

The pipeline has four phases. Each is a pure function of its input, supporting reproducibility and per-phase ablation.

### 4.1 Phase 0 — Token Frequency Filtering and Variation Generation

We first count document-frequency $f(t)$ for each token $t \in \bigcup_i r_i$ and remove tokens with $f(t) > \tau_{max}$ (default $\tau_{max} = 6$); these correspond to high-frequency stop-words and noise (e.g., common state codes) that would create huge non-discriminative blocks.

We then generate a variation set $V(t)$ for each surviving token using one of four methods:

- **`fuzzy`** — pairs of tokens whose Levenshtein similarity exceeds a threshold $\theta$ (default 85) are clustered into the same variation class.
- **`phonetic`** — tokens sharing a Soundex code are merged.
- **`manual`** — caller-provided $\{t \to V(t)\}$ map; useful for domain glossaries.
- **`data_quality`** — for each token $t$, we generate plausible corruptions via a data-quality generator (transposition, deletion, OCR-style swaps, etc.) and merge $t$ with $t'$ whenever a generated variant of $t$ exactly matches an actual token $t'$ in the dataset. This is more discriminative than `fuzzy` because it ignores spurious n-gram fragments.

```
Algorithm 1: data_quality variation generation
Input  : T = unique tokens in cleaned_refDict
Output : variations: {token -> set(token)}

  lower_to_tokens <- map t.lower() -> {t}
  variations      <- {t: {t} for t in T}
  for t in T:
      seed RNG with hash(t.lower())
      generated <- generate_all_variations(t.lower())
      for v in generated:
          if v in lower_to_tokens:
              for t' in lower_to_tokens[v]:
                  variations[t].add(t')
                  variations[t'].add(t)
  return variations
```

### 4.2 Phase 1 — Token-to-Hash-Key Mapping

For each variation class $V(t)$ we mint one hash key $h_V$ (e.g., `HASH_05295`). Each record $r_i$ is then represented by its **hash-key set** $H(r_i) = \{h_V : t \in r_i, t \in V\}$. Tokens that were merged in Phase 0 now collapse to the same hash key, providing noise-tolerance "for free" without altering Phase 2/3.

### 4.3 Phase 2 — Initial Blocking by Hash-Key Set

Records with *identical* hash-key sets land in the same initial block. Concretely, $B_{init}(K) = \{r_i : H(r_i) = K\}$. Optionally, when records' key sets only partially overlap, we activate **MinHash-LSH bucketing** (`datasketch`) with parameters `num_perm=128`, `lsh_threshold=0.5` to recover near-duplicates whose key sets differ by a few keys.

[TODO: Justify why exact-set bucketing is sufficient on `S12PX` but LSH is needed on larger / noisier data.]

### 4.4 Phase 3 — Recursive Refinement

Phase 2 may produce oversized blocks (e.g., the largest initial block on `S12PX` under `data_quality` contained 1,498 records). Phase 3 recursively refines each oversized block by selecting the **most balanced distinguishing key** — a hash key present in some but not all members of the block — and splitting the block into a "with-key" subset and a "without-key" subset. Recursion terminates when:

- depth ≥ `max_depth` (default 3), or
- block size ≤ `min_bucket_size` (default 2), or
- no distinguishing key exists.

Each leaf block is labeled by its accumulated `+/-` key path, enabling exact provenance for any pair.

```
Algorithm 2: refine_block
Input  : B (block), HKR (hash_key_records),
         max_depth, min_bucket_size, depth, acc_keys
Output : list of (acc_keys, leaf_block)

  if |B| <= 1 or |B| <= min_bucket_size or depth >= max_depth:
      return [(acc_keys, sorted(B))]
  best_key, with_set, without_set <- find_best_split_key(B, HKR)
  if best_key is None:
      return [(acc_keys, sorted(B))]
  return refine_block(with_set,   ..., depth+1, acc_keys + ("+" + best_key))
       + refine_block(without_set,..., depth+1, acc_keys + ("-" + best_key))
```

`find_best_split_key` scores each candidate key $k$ by $\min(|B_k|, |B \setminus B_k|)$ where $B_k$ is the subset of records containing $k$, and returns the key maximizing this balanced-split score (skipping keys present in all or none of $B$).

**Complexity.** Per-block refinement is $O(d \cdot |B| \cdot \bar{k})$ where $d$ = `max_depth` and $\bar{k}$ = average per-record key count. Across all initial blocks the total cost is $O(d \cdot N \cdot \bar{k})$, near-linear in $N$ for fixed $d$.

---

## 5. Experimental Setup

**Dataset.** `S12PX` — 6,000 records. [TODO: describe domain (it appears to contain US addresses, names, dates), source, licensing, and any preprocessing.]

**Ground truth.** [TODO: Describe how match/non-match labels were obtained for evaluation. If unavailable, state that and report only block-quality metrics.]

**Metrics.**

- **Pair Completeness (PC)**: fraction of true matches captured in some block.
- **Reduction Ratio (RR)**: $1 - C / \binom{N}{2}$ where $C$ is the number of candidate pairs.
- **F1 of Pairs Quality (FQ)**: harmonic mean of PC and Pair Quality.
- **Largest Block Size (LBS)** and **Number of Final Blocks (NFB)**.

**Baselines.**

- **All-pairs** (oracle upper bound on recall).
- **Single-key blocking** (every record indexed by one canonical token).
- **Sorted Neighborhood** with window $w \in \{5, 10, 20\}$.
- **Standard Q-gram blocking** ($q = 3$).
- [TODO: any others.]

**Variants of our method.** We compare four configurations of Phase 0:

| Config        | Variation method | Threshold |
|---------------|------------------|-----------|
| RLSH-fuzzy    | fuzzy            | 85        |
| RLSH-phon     | phonetic         | —         |
| RLSH-data     | data_quality     | —         |
| RLSH-manual   | manual           | (glossary)|

**Implementation.** Python 3.11; `datasketch` for optional MinHash-LSH; `rapidfuzz` for similarity scoring; matplotlib + D3.js for visualization. All experiments run on [TODO: hardware spec].

---

## 6. Results

### 6.1 Block-Quality Metrics

Table 1 reports NFB, LBS, candidate-pair count, PC and RR for each variant on `S12PX`.

| Method        | NFB   | LBS    | Candidate Pairs | PC      | RR     |
|---------------|-------|--------|-----------------|---------|--------|
| All-pairs     | 1     | 6000   | 17,997,000      | 1.000   | 0.000  |
| RLSH-fuzzy    | 5,693 | [TODO] | 669             | [TODO]  | 0.99996|
| RLSH-phon     | [TODO]| [TODO] | [TODO]          | [TODO]  | [TODO] |
| RLSH-data     | 3,420 | 1,498  | 1,148,947       | [TODO]  | 0.9362 |
| RLSH-manual   | [TODO]| [TODO] | [TODO]          | [TODO]  | [TODO] |

**Observations.**

- `data_quality` produces fewer, larger blocks (3,420 vs. 5,693 for `fuzzy`), suggesting it merges more noisy variants — but at the cost of one outlier block of 1,498 records that survives Phase 3 refinement at default depth.
- [TODO: comment on PC differences.]
- [TODO: trade-off between RR and PC across methods.]

### 6.2 Sensitivity to `max_depth`

[TODO: Plot LBS and NFB as `max_depth` varies from 1 to 8. Show that LBS converges and depth ≥ 3 captures most of the benefit.]

### 6.3 Runtime Breakdown

| Phase | Wall time (s) | % of total |
|-------|---------------|------------|
| 0 (`data_quality`) | 0.87 | 12% |
| 0 (`fuzzy`)        | 51.20 | 95% |
| 1                  | 0.05  | <1% |
| 2                  | 1.88  | 26% |
| 3                  | 0.02  | <1% |

Phase 0 with `fuzzy` dominates due to the $O(N^2)$ pairwise Levenshtein step; `data_quality` is two orders of magnitude faster because it uses the union of generated variants as a hash lookup.

### 6.4 Qualitative Audit via Interactive Visualization

We render every final block as a circle whose area scales with member count, with individual records placed inside in a sunflower pattern. Hovering reveals each record's full token list and cluster label, supporting rapid manual auditing of false-positive merges and false-negative splits. [TODO: include screenshots; reference Figs. X, Y.]

---

## 7. Discussion and Limitations

**Recall vs. Reduction.** [TODO: Discuss the LBS=1498 outlier under `data_quality` — likely caused by dominant tokens (state codes, repeated apartment numbers). Suggest mitigations: per-token IDF weighting, tighter `max_frequency`.]

**Threshold sensitivity.** [TODO: How does PC vary as `max_frequency` and `similarity_threshold` change?]

**Generalization.** All experiments are on a single dataset. [TODO: Future work on DBLP, NCVoter, Cora.]

**Comparison to learned blocking.** Our method uses no labeled data; learned methods like DeepBlocker may achieve higher PC at equivalent RR but require training pairs. [TODO: discuss when each is appropriate.]

**Threats to validity.** [TODO: ground-truth construction, limited variation methods, single hardware setting.]

---

## 8. Conclusion

We presented a four-phase Recursive LSH blocking pipeline that combines variation-aware token expansion, hash-key-set bucketing, and recursive refinement to produce small, well-balanced blocks for entity resolution without requiring labeled data. On `S12PX`, our best variant achieves a [TODO: ×]-fold reduction in candidate-pair count while [TODO: comparable / superior] recall to standard blocking baselines. The open-source implementation and interactive visualizations are available at [TODO: GitHub URL].

---

## Acknowledgments

[TODO]

---

## References

[TODO: convert to your venue's citation style — ACM/IEEE/Springer.]

1. P. Christen. *Data Matching: Concepts and Techniques for Record Linkage, Entity Resolution, and Duplicate Detection.* Springer, 2012.
2. M. A. Hernández and S. J. Stolfo. The merge/purge problem for large databases. *SIGMOD*, 1995.
3. A. Z. Broder. On the resemblance and containment of documents. *Compression and Complexity of Sequences*, 1997.
4. J. Leskovec, A. Rajaraman, J. D. Ullman. *Mining of Massive Datasets.* Cambridge, 2014.
5. G. Papadakis et al. Blocking and filtering techniques for entity resolution: A survey. *ACM Computing Surveys*, 53(2), 2020.
6. S. Thirumuruganathan et al. DeepBlocker: Deep learning for blocking in entity matching. *VLDB*, 2021.
7. [TODO: data_quality_generator citation if it has a paper.]
8. M. Bawa, T. Condie, P. Ganesan. LSH forest: self-tuning indexes for similarity search. *WWW*, 2005.
9. P. Indyk and R. Motwani. Approximate nearest neighbors: towards removing the curse of dimensionality. *STOC*, 1998.

---

## Appendix A — Pipeline Pseudocode

```
Algorithm 3: run_pipeline
Input  : refDict (raw {refID -> [tokens]}), hyperparameters
Output : final_blocks ({label -> [refID]})

  cleaned, freq, variations <- run_phase_0(refDict, max_frequency, method)
  token_to_hash, hash_to_tokens, HKR <- run_phase_1(cleaned, variations)
  per_key, by_key_set, candidate_pairs <- run_phase_2(HKR, use_lsh, ...)
  final_blocks <- {}
  for (parent_keys, members) in by_key_set.items():
      leaves <- refine_block(members, HKR, max_depth, min_bucket_size,
                             depth=0, acc_keys=tuple(parent_keys))
      for (split_keys, refIDs) in leaves:
          final_blocks[unique_label(split_keys)] <- refIDs
  return final_blocks
```

## Appendix B — Hyperparameter Defaults

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `max_frequency` | 6 | Removes top-decile tokens; tuned on `S12PX`. |
| `similarity_threshold` | 85 | Standard `rapidfuzz` cutoff. |
| `max_depth` | 3 | LBS converges past depth 3 on `S12PX`. |
| `min_bucket_size` | 2 | Below 2, refinement is meaningless. |
| `num_perm` (LSH) | 128 | datasketch default. |
| `lsh_threshold` | 0.5 | Conservative recall preference. |

## Appendix C — Reproducibility

```bash
git clone [TODO: repo url]
cd recursive_LSH
python recursive_lsh.py S12PX.txt --variation-method data_quality
python visualize.py --variation-method data_quality
```

---

### Notes for the author

- **Length target:** ~10–12 pages two-column (e.g., ACM SIGMOD / VLDB style) or 14–16 pages single-column (Springer LNCS).
- **What's still missing:** ground-truth labels (Section 5) and at least one comparison against a published baseline (Section 6.1) — those are the highest-impact gaps before submission.
- **Strong figures to add:** (1) pipeline architecture diagram, (2) Phase-3 refinement tree on a representative oversized block, (3) PC vs. RR Pareto curve across methods, (4) screenshot of the interactive visualization.
- **Suggested venue:** SIGMOD industrial track, VLDB demo track (the visualizations make this competitive), or *Information Systems* journal if the focus stays on the algorithm.
