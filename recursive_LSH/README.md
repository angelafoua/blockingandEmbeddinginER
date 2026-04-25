# Recursive LSH with Word Signatures - Documentation

## Overview

A token-based entity resolution system that handles data quality variations by creating word signatures and recursively refining blocks.

**Problem:** Records with spelling variations (john/jon, smith/smyth) are treated as different tokens  
**Solution:** Create signatures for similar words, then use recursive blocking to find duplicates

---

## The 4 Phases

### Phase 0: Token Frequency Analysis & Data Quality Generation
Remove high-frequency tokens (noise) and generate data quality variations for each unique token.
- Count token frequencies
- Remove high-frequency tokens
- Generate variations (fuzzy match, phonetic, or manual)

**Output:** Cleaned tokens + Variation dictionary

---

### Phase 1: Hashing Keys for Token Variations
Assign each unique token and its variations a consistent hashing key.
- Group similar tokens together
- Create token → hash key mapping
- All variations of same concept get same hash key

**Output:** token_hash_mapping, hash_key_records

---

### Phase 2: Blocking Based on Merging Tokens
Create initial blocks by grouping records that share hash keys.
- Create blocks for each hash key
- Merge records across keys (records in multiple blocks together)
- Generate candidate pairs

**Output:** Initial blocks, candidate pairs

---

### Phase 3: Recursive Blocking Within Blocks
Iteratively refine blocks to increase precision.
- Identify distinguishing hash keys within blocks
- Create sub-blocks based on more specific key matches
- Recursively refine until can't block further

**Output:** Final refined blocks

---

## Algorithm Flow

```
Raw Records
     ↓
[Phase 0] Token Frequency & Data Quality
     ↓ (Remove noise, generate variations)
     ↓
Clean tokens + Variation dictionary
     ↓
[Phase 1] Create Hash Keys
     ↓ (Map tokens to hash keys)
     ↓
Hash key mapping + Record hash key sets
     ↓
[Phase 2] Initial Blocking
     ↓ (Group by shared keys)
     ↓
Initial blocks + Candidate pairs
     ↓
[Phase 3] Recursive Refinement
     ↓ (Recursively split blocks)
     ↓
Final blocks (similar records grouped)
     ↓
Deduplicated Records
```

---

## Documentation Files

- **README.md** - This overview
- **PHASE_0.md** - Token frequency analysis & data quality generation
- **PHASE_1.md** - Hashing keys for token variations
- **PHASE_2.md** - Blocking based on merging tokens
- **PHASE_3.md** - Recursive blocking within blocks

Read each phase documentation for detailed implementation guidance.

---

## Key Concepts

**Token:** A single word/string element in a record
**Hash Key:** Unique identifier for a group of token variations
**Block:** Group of records sharing hash keys
**Refinement:** Creating sub-blocks by adding more specific hash key requirements
**Data Quality Variations:** Misspellings, abbreviations, alternative spellings of the same concept

---

## Configuration

Each phase has configuration parameters:

**Phase 0:**
- `max_frequency`: Threshold for removing tokens

**Phase 1:**
- `similarity_threshold`: For fuzzy matching (0-100)

**Phase 2:**
- `num_perm`: MinHash permutations (for LSH optimization)
- `lsh_threshold`: LSH bucketing threshold

**Phase 3:**
- `max_depth`: Maximum recursion depth
- `min_bucket_size`: Minimum records to continue refining

See individual phase documentation for details.
