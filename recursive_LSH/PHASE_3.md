# Phase 3: Recursive Blocking Within Blocks

## Overview

Iteratively refine blocks to increase matching precision by requiring more specific hash key matches at each level.

---

## Purpose

Reduce false positives by recursively splitting blocks until records are very similar.

**Input:** Initial blocks from Phase 2  
**Output:** Final refined blocks (most specific groupings)

---

## Step 1: Identify Distinguishing Hash Keys

Within each block, find hash keys that differentiate records.

Distinguishing keys are those that:
- Appear in some records in the block
- But NOT in all records in the block

```
Block: [Record 1, Record 2, Record 3]

Hash keys:
  Record 1: [HASH_001, HASH_002, HASH_003]
  Record 2: [HASH_001, HASH_002, HASH_003]
  Record 3: [HASH_001, HASH_004]

Key presence:
  HASH_001: 3 (all) - NOT distinguishing
  HASH_002: 2 (some) - DISTINGUISHING
  HASH_003: 2 (some) - DISTINGUISHING
  HASH_004: 1 (some) - DISTINGUISHING
```

---

## Step 2: Create Sub-blocks

Split block based on distinguishing keys.

Select the best key (most balanced split) and split:
- Records WITH the key → one sub-block
- Records WITHOUT the key → another sub-block

```
Block: [1, 2, 3]
Split by HASH_002:
  With HASH_002: [1, 2]
  Without HASH_002: [3]
```

---

## Step 3: Recursive Refinement

Apply splitting recursively to sub-blocks.

```
Iteration 1:
  Block: [1, 2, 3]
  Split by HASH_002 → [1, 2] | [3]

Iteration 2 (on [1, 2]):
  No distinguishing keys (same)
  Can't refine further → Final block: [1, 2]

Iteration 2 (on [3]):
  Single record → Final block: [3]
```

---

## Stopping Conditions

Stop refining when ANY of these occur:

1. **Depth Reached**: depth >= max_depth
2. **Bucket Too Small**: len(block) <= min_bucket_size
3. **No Distinguishing Keys**: All records have same hash keys
4. **Single Record**: Only one record in block

---

## Configuration

- **max_depth**: Maximum recursion levels (default: 3)
- **min_bucket_size**: Stop refining when block < this many records (default: 2)

---

## Example: Complete Phase 3

**Input:**
```
blocks_by_key_set:
  (HASH_001, HASH_002, HASH_003): [1, 2, 3]
  (HASH_001, HASH_004): [4, 5]

hash_key_records:
  1: (HASH_001, HASH_002, HASH_003)
  2: (HASH_001, HASH_002, HASH_003)
  3: (HASH_001, HASH_004)
  4: (HASH_001, HASH_004)
  5: (HASH_001, HASH_004)
```

**Processing Block [1, 2, 3]:**

Iteration 1:
- Distinguishing keys: {HASH_004} (only 3 has it)
- Split by HASH_004
- With: [3], Without: [1, 2]

Iteration 2 (on [1, 2]):
- No distinguishing keys → Final: [1, 2]

Iteration 2 (on [3]):
- Single record → Final: [3]

**Processing Block [4, 5]:**

Iteration 1:
- No distinguishing keys → Final: [4, 5]

**Final Output:**
```
[[1, 2], [3], [4, 5]]
```

---

## Output

### Final Blocks
Most specific groupings of similar records.

```
Block 1: [Record 1, Record 2]
Block 2: [Record 3]
Block 3: [Record 4, Record 5]
```

---

## Key Insights

**Recursive Refinement:** Each iteration adds more specificity

**Distinguishing Keys:** Keys that separate records are important

**Depth Tradeoff:**
- Higher max_depth = more refined, smaller blocks
- Lower max_depth = larger blocks, less precision

**Final Blocks Quality:** Ready for final matching rules
