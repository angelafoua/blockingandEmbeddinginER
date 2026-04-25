# Phase 2: Blocking Based on Merging Tokens

## Overview

Create initial blocks by grouping records that share hash keys.

---

## Purpose

Convert hash key sets into candidate blocks for matching.

**Input:** Hash key sets for each record  
**Output:** Blocks of candidate records to compare

---

## Step 1: Create Blocks by Hash Key

For each unique hash key, create a block containing all records with that key.

```
hash_key_records:
  1: (HASH_001, HASH_002, HASH_003)
  2: (HASH_001, HASH_002, HASH_003)
  3: (HASH_001, HASH_004)

blocks_by_key:
  HASH_001: [1, 2, 3]
  HASH_002: [1, 2]
  HASH_003: [1, 2]
  HASH_004: [3]
```

---

## Step 2: Merge Records Across Keys

Records appearing in multiple blocks together = strong candidates for matching.

Group records that share ALL their hash keys together.

```
blocks_by_key_set:
  (HASH_001, HASH_002, HASH_003): [1, 2]
  (HASH_001, HASH_004): [3]
```

---

## Step 3: Generate Block Candidates

Identify pairs of records to compare within each block.

```
Block [1, 2]: pair (1, 2)
Block [3]: single record, no pairs

candidate_pairs: [(1, 2)]
```

---

## LSH Optimization (Optional)

For large datasets, use MinHash + LSH to speed up block creation.

Instead of comparing all hash key sets, use LSH bucketing to find similar sets efficiently.

---

## Output

### blocks_by_key_set
Blocks grouped by their hash key sets

### candidate_pairs
All pairs within each block to compare

### Initial Blocks (for Phase 3)
```
Block_A: [1, 2]
Block_B: [3]
```

---

## Configuration

- **num_perm** (LSH only): MinHash permutations (default: 128)
- **threshold** (LSH only): LSH bucketing threshold (default: 0.5)

---

## Key Insights

**Grouping by Hash Keys:** Records with identical hash key sets are strongest candidates

**Candidate Reduction:** Only compare O(candidates) pairs instead of O(n²)

**Block Quality:** Blocks are "initial" - will be refined in Phase 3
