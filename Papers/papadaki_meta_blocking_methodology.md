# Meta-Blocking: Taking Entity Resolution to the Next Level
**Papadakis, Koutrika, Palpanas, Nejdl**

---

## 1. Overview and Motivation

**Entity Resolution (ER)** is inherently quadratic — every entity must be compared to all others. **Blocking** reduces this cost by grouping similar entities into blocks and only comparing within blocks.

### Problem with Redundancy-Positive Blocking
- Methods like q-grams, Suffix Array, HARRA, and schema-agnostic blocking place each entity in *multiple* blocks
- More blocks shared between two entities → more likely they are duplicates (redundancy-positive property)
- This redundancy ensures high recall but at the cost of many unnecessary comparisons:
  - **Redundant comparisons**: same pair compared in multiple blocks
  - **Superfluous comparisons**: pairs that are not duplicates

### What Meta-Blocking Does
Meta-blocking is a **post-blocking, pre-comparison** procedure that:
- Takes a block collection **B** as input
- Outputs a restructured block collection **B'** with substantially fewer comparisons
- Maintains (nearly) the same effectiveness (recall)
- Operates at the level of *individual comparisons*, not entire blocks

It does **not replace** blocking — it **complements** it by sitting between block building and block processing.

---

## 2. Formal Problem Definition

### Key Definitions

**Entity Profile**: A tuple `⟨id, Ap⟩` where `id` is a unique identifier and `Ap` is a set of name-value pairs `⟨n, v⟩`. Schema-flexible — attribute names and values may be absent (tag-style).

**Types of ER**:
- **Clean-Clean ER**: Both input collections E₁ and E₂ are duplicate-free
- **Dirty-Clean ER**: E₁ is clean, E₂ is dirty
- **Dirty ER**: A single dirty collection E containing duplicates

**Block Types**:
- **Unilateral blocks**: All entities from the same dirty collection — all pairs are candidate matches
- **Bilateral blocks**: Internally partitioned into two sub-blocks from E₁ and E₂ — only cross-collection comparisons allowed

### Quality Metrics

| Metric | Formula | Meaning |
|--------|---------|---------|
| **Pair Completeness (PC)** | `|D_B| / |D_E|` | Fraction of true duplicates that share at least one block (effectiveness) |
| **Pairs Quality (PQ)** | `|D_B| / ‖B‖` | Fraction of comparisons that are true matches (efficiency) |
| **Reduction Ratio (RR)** | `1 - ‖B‖ / ‖B_bs‖` | How much the comparison count is reduced vs. baseline |

Where:
- `‖B‖` = aggregate cardinality (total comparisons)
- `‖b_i‖ = |b_i|(|b_i|-1)/2` for unilateral blocks
- `‖b_j‖ = |b_j¹| · |b_j²|` for bilateral blocks

### BC-CC Metric Space

Used to estimate PC and RR *without executing comparisons*:

- **Blocking Cardinality (BC)**: Average block assignments per entity — measures redundancy
  - BC = 1 → redundancy-free
  - BC > 1 → redundancy-bearing (higher = more redundant)
- **Comparisons Cardinality (CC)**: Ratio of block assignments to comparisons — measures efficiency
  - CC = 2 → optimal (all blocks contain exactly 2 entities)

**Ideal Point**: `(BC=1, CC=2)` — each duplicate pair gets its own minimum-size block, no redundant or superfluous comparisons.

**Goal of meta-blocking**: Move block collection mapping closer to the Ideal Point.

### Formal Problem Statement

> **Problem 1 (Meta-blocking)**: Given a block collection **B**, restructure it into **B'** such that:
> - `PQ(B') >> PQ(B)` and `RR(B', B) >> 0` (significantly higher efficiency)
> - `PC(B') ≥ PC(B)` (maintained effectiveness)

---

## 3. The Meta-Blocking Pipeline

The methodology consists of **four successive steps**:

```
B → [Graph Building] → G_B → [Edge Weighting] → G_B^w → [Graph Pruning] → G_B^p → [Block Collecting] → B'
```

---

## 3.1 Step 1: Graph Building

### The Blocking Graph
Given block collection **B**, construct the **blocking graph** G_B:
- **Nodes** (V_B): One node per entity profile appearing in at least one block
- **Edges** (E_B): One undirected edge per pair of co-occurring entities (entities sharing at least one block)
- **Key property**: Redundant comparisons are automatically eliminated — each pair gets at most one edge regardless of how many blocks they share

**For bilateral blocks**: The result is a **bipartite graph** — edges only between entities from different collections (E₁ vs E₂).

**For directed graphs**: Node-centric pruning algorithms produce **directed blocking graphs** Ḡ_B (edges point from one entity to another).

### Algorithm 1: Building the Blocking Graph
```
Input: Block collection B, weighting scheme WS
Output: Blocking graph G_B

1. Initialize V_B = {}, E_B = {}
2. For each block b_i in B:
   3. For each entity p_i in b_i¹:
      4. Add node v_i to V_B
      5. For each entity p_j in b_i²:
         6. Add node v_j to V_B
         7. Add edge e_{i,j} to E_B
8. Set edge weights using WS
9. Normalize edge weights to [0,1]
10. Return G_B = {V_B, E_B, WS}
```

**Time complexity**: O(‖B‖) — linear in the aggregate cardinality of B

**Implementation options** (for large-scale use):
- **Inverted indices**: Associate each entity with the list of blocks containing it
- **Bit arrays**: Represent each entity as a binary vector over blocks

---

## 3.2 Step 2: Edge Weighting

### Core Principle
The weight `e_{i,j}.weight` of edge `e_{i,j}` approximates the *utility* of comparing entities `p_i` and `p_j`:
- Weight ≈ 0 → likely non-matching
- Weight ≈ 1 → likely duplicates

Since the actual gain cannot be known without comparing, weight is **approximated** from block structure.

**Notation**:
- `B_i ⊆ B` — blocks containing entity `p_i`
- `B_{i,j} = B_i ∩ B_j` — blocks shared by `p_i` and `p_j`
- `|v_i|` — degree of node `v_i` (number of adjacent edges)

### The Five Schema-Agnostic Weighting Schemes

#### (i) Aggregate Reciprocal Comparisons Scheme (ARCS)
Larger blocks are less discriminating. Weight is the sum of reciprocal cardinalities of shared blocks:

```
e_{i,j}.weight = Σ_{b_k ∈ B_{i,j}}  1 / ‖b_k‖
```

Best for: **Dirty ER**

#### (ii) Common Blocks Scheme (CBS)
More shared blocks = more similar. Simple count:

```
e_{i,j}.weight = |B_{i,j}|
```

#### (iii) Enhanced Common Blocks Scheme (ECBS)
Improves CBS with IDF-style contextual information — entities appearing in fewer blocks get higher weight:

```
e_{i,j}.weight = |B_{i,j}| · log(|B| / |B_i|) · log(|B| / |B_j|)
```

Best for: **Clean-Clean ER** with weight pruning

#### (iv) Jaccard Scheme (JS)
Normalizes shared blocks by total blocks associated with each entity:

```
e_{i,j}.weight = |B_{i,j}| / (|B_i| + |B_j| - |B_{i,j}|)
```

Values in [0,1]: 0 = no common blocks, 1 = identical block lists

#### (v) Enhanced Jaccard Scheme (EJS)
Improves JS by adding IDF-style degree weighting per node:

```
e_{i,j}.weight = (|B_{i,j}| / (|B_i| + |B_j| - |B_{i,j}|)) · log(|E_B| / |v_i|) · log(|E_B| / |v_j|)
```

Best for: **Clean-Clean ER** with cardinality pruning

### Weighting Scheme Summary

| Scheme | Formula Basis | Best Use Case |
|--------|--------------|---------------|
| ARCS | Reciprocal block cardinality | Dirty ER |
| CBS | Count of shared blocks | General |
| ECBS | CBS + IDF correction | Clean-Clean ER, weight pruning |
| JS | Jaccard similarity of block sets | General |
| EJS | JS + IDF correction | Clean-Clean ER, cardinality pruning |

---

## 3.3 Step 3: Graph Pruning

Edges with low weights (likely non-matching pairs) are removed. This step has two components:

### Pruning Algorithms

#### Edge-Centric Algorithms
- Iterate over **all edges** of the blocking graph
- Select the *globally* best comparisons
- Produce an **undirected** pruned blocking graph
- Can only be combined with **global thresholds**

#### Node-Centric Algorithms
- Iterate over **all nodes** of the blocking graph
- Select the *locally* best comparisons for each entity
- Produce a **directed** pruned blocking graph
- Compatible with both local and global thresholds

### Pruning Criteria (Two-Dimensional Taxonomy)

**Dimension 1 — Functionality**:
- **Weight thresholds**: Specify minimum weight for retained edges (controls effectiveness)
- **Cardinality thresholds**: Specify maximum number of retained edges (controls comparison count)

**Dimension 2 — Scope**:
- **Global thresholds**: Apply to the entire blocking graph
- **Local thresholds**: Apply to the neighborhood of each specific node

### The Four Pruning Schemes

#### 3.3.1 Weight Edge Pruning (WEP)
**Type**: Edge-centric + global weight threshold

```
Algorithm 2: Weight Edge Pruning
Input: G_B, w_min (global weight threshold)
Output: Undirected pruned G_B

1. For each edge e_{i,j} in E_B:
2.   If e_{i,j}.weight < w_min:
3.     Remove e_{i,j} from E_B
4. Return pruned G_B
```

**Time complexity**: O(‖B‖)

**Threshold selection**: Use the **average edge weight** as `w_min` — efficient (one pass) and empirically reliable across datasets and weighting schemes.

**Characteristics**:
- Deeper pruning → fewer comparisons
- Higher PQ than node-centric schemes
- More aggressive reduction in PC

---

#### 3.3.2 Cardinality Edge Pruning (CEP) — "Top-K Edges"
**Type**: Edge-centric + global cardinality threshold K

```
Algorithm 3: Cardinality Edge Pruning
Input: G_B, K (number of edges to retain)
Output: Undirected pruned G_B

1. SortedStack = {} (sorted descending by weight)
2. For each edge e_{i,j} in E_B:
3.   Push e_{i,j} to SortedStack
4.   If K < SortedStack.size():
5.     Pop lowest-weight edge
6. For each edge e_{i,j} in E_B:
7.   If e_{i,j} not in SortedStack:
8.     Remove e_{i,j} from E_B
9. Return pruned G_B
```

**Time complexity**: O(‖B‖)

**Optimal K selection** (using BC-CC mapping):
- Pruned graph → bilateral blocks of size 2, so CC_out = 2 (maximum)
- For improved BC-CC mapping: `K ≤ ⌊BC_in · |E| / 2⌋`
- This minimizes comparisons for a given level of redundancy

**Characteristics**:
- Highest efficiency (RR ≈ 97–99.9% in experiments)
- More aggressive PC reduction (>14% in experiments)
- Results in redundancy-free output blocks

---

#### 3.3.3 Weight Node Pruning (WNP)
**Type**: Node-centric + local weight threshold

```
Algorithm 4: Weight Node Pruning
Input: G_B, wt (function for local weight threshold)
Output: Directed pruned G_B

1. E_B_out = {}
2. For each node v_i in V_B:
3.   G_{v_i} = getNeighborhood(v_i, G_B)
4.   t_{v_i} = wt(G_{v_i})  // local threshold
5.   For each edge e_{i,j} in E_{v_i}:
6.     If t_{v_i} ≤ e_{i,j}.weight:
7.       Add directed edge ē_{i,j} to E_B_out
8. Return directed G_B = {V_B, E_B_out, WS}
```

**Time complexity**: O(|V_B| · |E_B|) worst case; much lower in practice

**Threshold selection**: Mean edge weight of each node's neighborhood G_{v_i}

**Key differences from WEP**:
- Different threshold per node (local vs. global)
- Retains directed edges (undirected → directed)
- More conservative pruning → higher PC, lower RR

**Characteristics**:
- Ensures every node remains connected to its most similar neighbors
- Significantly higher PC than WEP at cost of lower RR and PQ
- Suitable for effectiveness-focused applications

---

#### 3.3.4 Cardinality Node Pruning (CNP) — "k-Nearest Entities"
**Type**: Node-centric + local cardinality threshold

```
Algorithm 5: Cardinality Node Pruning
Input: G_B, ct (function for local cardinality threshold)
Output: Directed pruned G_B

1. E_B_out = {}
2. For each node v_i in V_B:
3.   SortedStack_{v_i} = {}
4.   G_{v_i} = getNeighborhood(v_i, G_B)
5.   k = ct(G_{v_i})  // local cardinality threshold
6.   For each edge e_{i,j} in E_{v_i}:
7.     Push e_{i,j} to SortedStack_{v_i}
8.     If k < SortedStack_{v_i}.size():
9.       Pop lowest-weight edge
10.  For each edge e_{i,j} in E_{v_i}:
11.    If e_{i,j} in SortedStack_{v_i}:
12.      Add directed edge ē_{i,j} to E_B_out
13. Return directed G_B = {V_B, E_B_out, WS}
```

**Time complexity**: O(|V_B| · |E_B|)

**Optimal k selection** (using BC-CC mapping):
- CC_out = (k+1)/k, BC_out = k+1
- Constraint: `1/(1-CC_or) ≤ k ≤ BC_in - 1`
- Safe default: `k = ⌊BC_in - 1⌋`

**Characteristics**:
- Very high efficiency (RR > 95%)
- Limited impact on PC (< 5% for Clean-Clean ER)
- Results in redundancy-bearing output blocks (possible duplicate comparisons)

---

### Pruning Scheme Comparison Matrix

| Scheme | Algorithm | Threshold Type | Output Graph | PC Impact | RR/Efficiency |
|--------|-----------|---------------|-------------|-----------|---------------|
| WEP | Edge-centric | Global weight | Undirected | Moderate loss | High RR |
| CEP | Edge-centric | Global cardinality | Undirected | Higher loss | Highest RR |
| WNP | Node-centric | Local weight | Directed | Minimal loss | Moderate RR |
| CNP | Node-centric | Local cardinality | Directed | Small loss | High RR |

### Selection Guidelines

| Application Priority | Recommended Scheme |
|---------------------|--------------------|
| Maximize effectiveness (recall) | WNP (node-centric + weight threshold) |
| Maximize efficiency (speed) | CEP (edge-centric + cardinality threshold) |
| Balance both | CNP (node-centric + cardinality threshold) |
| Incremental / Pay-As-You-Go ER | Any (decrease cardinality or increase weight threshold per iteration) |
| Low duplicate ratio | WEP or CEP (edge-centric) |
| High duplicate ratio or social networks | WNP or CNP (node-centric) |

---

## 3.4 Step 4: Block Collecting

Transforms the pruned blocking graph into the final block collection B'.

### From Undirected Pruned Graph (edge-centric output)
- Each retained edge → one **bilateral block of minimum size** (2 entities)
- Output is **redundancy-free** (non-overlapping blocks)
- Example: edge (p₁, p₃) → block b₁ = {{p₁}, {p₃}}

### From Directed Pruned Graph (node-centric output)
- Each node v_i → one bilateral block:
  - One inner block contains the entity mapped to v_i
  - Other inner block contains all entities reachable via outgoing directed edges
- Output is **redundancy-bearing** (overlapping blocks possible)
- Example: outgoing edges from p₁ to {p₃, p₄} → block b₁ = {{p₁}, {p₃, p₄}}
- Can be further processed with block processing techniques

---

## 4. Experimental Evaluation Summary

### Datasets Used

| Dataset | Type | Entities | Matching Pairs | Baseline PC | Baseline RR |
|---------|------|---------|----------------|-------------|-------------|
| D_movies (IMDB + DBPedia) | Clean-Clean | ~50K | 22,405 | 99.39% | 95.83% |
| D_infoboxes (DBPedia snapshots) | Clean-Clean | ~3.3M | 892,586 | 99.89% | 98.46% |
| D_BTC09 (Billion Triple Challenge) | Dirty | ~253K | 10,653 | 96.94% | 99.59% |

### Key Findings

**Meta-blocking vs. Baseline**:
- All schemes achieve significant efficiency gains (RR > 70% for weight criteria, RR > 95% for cardinality criteria)
- PC reduction is typically < 10% for weight criteria
- Meta-blocking is 10–50× faster than the baseline in absolute time

**Edge-centric vs. Node-centric**:
- Edge-centric: Deeper pruning, higher PQ, more PC reduction
- Node-centric: Shallower pruning, lower PQ, much smaller PC reduction

**Weight vs. Cardinality criteria**:
- Cardinality thresholds: ~10× fewer comparisons, but more PC reduction
- Weight thresholds: Higher PC, but less efficient

**Best weighting schemes**:
- **ECBS** → best for Clean-Clean ER with weight pruning (balanced)
- **EJS** → best for Clean-Clean ER with cardinality pruning (best PC)
- **ARCS** → best for Dirty ER across all pruning schemes

**vs. Iterative Blocking**:
- Meta-blocking consistently outperforms Iterative Blocking on efficiency
- Iterative Blocking only preferred when effectiveness (PC) is the sole priority and efficiency gains > 1% are acceptable

### Time Complexity Summary

| Phase | Time Complexity |
|-------|----------------|
| Materialization (graph building + weighting) | O(‖B‖) |
| Restructure (pruning + block collecting) | O(‖B‖) for edge-centric; O(|V_B|·|E_B|) for node-centric |
| Comparison (executing retained pairs) | Dominates overall time for weight criteria |

---

## 5. Key Theoretical Properties

1. **Redundancy elimination is lossless**: Building the blocking graph automatically removes all redundant comparisons with zero PC cost.

2. **Schema-agnosticism**: All five weighting schemes and all four pruning schemes require no schema information — applicable to any blocking method.

3. **Independence from block type**: Works on both unilateral and bilateral blocks; can transform between types.

4. **Controllable effectiveness trade-off**: Unlike coarse-grained block processing (Block Purging, Block Pruning), meta-blocking's impact on PC is bounded and predictable via threshold tuning.

5. **Robustness**: Sensitivity analysis confirms that small threshold variations lead to small performance variations — thresholds derived from the BC-CC framework are near-optimal.

---

## 6. Position in the ER Pipeline

```
Entity Collections (E₁, E₂)
        ↓
  [Block Building]        ← e.g., attribute-agnostic blocking, q-grams, HARRA
        ↓
  Block Collection B      ← possibly with Block Purging applied first
        ↓
  [META-BLOCKING]         ← graph building → edge weighting → graph pruning → block collecting
        ↓
  Block Collection B'     ← fewer comparisons, same recall
        ↓
  [Block Processing]      ← pairwise entity comparison and matching
        ↓
  Detected Duplicates D_detected
```

Meta-blocking is specifically designed for **redundancy-positive** blocking methods. It does not apply to redundancy-negative (Canopy Clustering) or redundancy-neutral (Sorted Neighborhood) methods, which require known schemas anyway.
