# Phase 1: Hashing Keys for Token Variations

## Overview

Assign each unique token and its variations a consistent hashing key (signature). All variations of the same token get the same key.

---

## Purpose

Convert the concept of "similar tokens" into concrete identifiers (hash keys) for use in blocking.

**Before:** john, jon, jhon are different tokens  
**After:** john, jon, jhon all map to HASH_001

---

## Step 1: Create Token-to-Hash-Key Mapping

For each group of token variations, create a unique hash key.

```
Input variations_dict:
  john → [john, jon, jhon, jahn]
  smith → [smith, smyth, smythe]
  boston → [boston]

Output token_hash_mapping:
  john → HASH_001
  jon → HASH_001
  jhon → HASH_001
  jahn → HASH_001
  smith → HASH_002
  smyth → HASH_002
  smythe → HASH_002
  boston → HASH_003
```

---

## Step 2: Create Reverse Mapping (For Inspection)

Optionally create reverse mapping (hash key → variations) for debugging.

```
hash_to_tokens:
  HASH_001 → [john, jon, jhon, jahn]
  HASH_002 → [smith, smyth, smythe]
  HASH_003 → [boston]
```

---

## Step 3: Convert Records to Hash Keys

Convert each record's tokens into their corresponding hash keys.

```
Record 1 tokens: [john, smith, boston]
Record 1 hash keys: (HASH_001, HASH_002, HASH_003)

Record 2 tokens: [jon, smith, boston]
Record 2 hash keys: (HASH_001, HASH_002, HASH_003)
↑ Same hash key set!

Record 3 tokens: [jane, doe]
Record 3 hash keys: (HASH_004, HASH_005)
```

---

## Output

### token_hash_mapping
```
{
  "john": "HASH_00001",
  "jon": "HASH_00001",
  "smith": "HASH_00002",
  ...
}
```

### hash_key_records
```
{
  1: ("HASH_00001", "HASH_00002", "HASH_00003"),
  2: ("HASH_00001", "HASH_00002", "HASH_00003"),
  3: ("HASH_00004", "HASH_00005"),
}
```

---

## Key Insights

**Deterministic:** Same token always maps to same hash key

**One-to-Many:** One hash key represents many token variations

**Reusable:** Hash key mapping can be saved and reused

**Comparable:** Hash key sets enable easy comparison
- Identical hash key sets = likely duplicates
