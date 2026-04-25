# Phase 0: Token Frequency Analysis & Data Quality Generation

## Overview

Analyze token frequencies and generate data quality variations for each unique token in the dataset.

---

## Step 1: Count Token Frequencies

### Purpose
Identify how many records contain each token.

### Process

Count occurrences of each token across all records.

```
Input records:
  1: ["john", "smith", "new", "york"]
  2: ["jon", "smith", "new", "york"]
  3: ["jane", "doe", "boston"]

Token frequencies:
  john: 150 records
  smith: 120 records
  new: 4800 records
  york: 4750 records
  jane: 80 records
  doe: 90 records
  boston: 60 records
```

### Output
- **tokenFreqDict**: Token → frequency count mapping

---

## Step 2: Remove High-Frequency Tokens

### Purpose
Remove tokens that appear in too many records (noise/stop words).

High-frequency tokens don't help distinguish between records and create noise.

```
Apply threshold (max_frequency = 60):
  john: 150 → Remove
  smith: 120 → Remove
  new: 4800 → Remove
  york: 4750 → Remove
  jane: 80 → Remove
  doe: 90 → Remove
  boston: 60 → Keep
```

### Output
- **cleaned_refDict**: Records with high-frequency tokens removed

---

## Step 3: Generate Data Quality Variations

### Purpose
For each unique token, identify variations (misspellings, abbreviations, alternative spellings).

### Methods

#### A. Fuzzy Matching (Automatic)
Find similar tokens based on edit distance.

```
john → {john, jon, jhon, jahn}  (85%+ similar)
smith → {smith, smyth, smythe}  (85%+ similar)
boston → {boston}
```

#### B. Phonetic Matching (For Names)
Group by phonetic similarity (Soundex, Metaphone).

```
john (soundex: J500) → {john, jon, jhon}
smith (soundex: S530) → {smith, smyth, smythe}
```

#### C. Manual Mapping (Most Precise)
Explicitly define variations based on domain knowledge.

```
john → {john, jon, jhon, jahn}
smith → {smith, smyth, smythe}
new york → {new york, ny, n.y.}
```

### Output
- **variations_dict**: Token → [list of variations]

---

## Configuration

- **max_frequency**: Threshold for removing tokens (default: 60)
- **variation_method**: 'fuzzy', 'phonetic', or 'manual'
- **similarity_threshold**: For fuzzy matching (0-100, default: 85)

---

## Quality Checks

After Phase 0, verify:

1. No empty records
2. Variations are comprehensive
3. High-frequency tokens properly removed
4. No duplicates in variations

---

## Data Flow Example

```
Input: Raw records with all tokens
         ↓
Count frequencies
         ↓
Remove high-frequency tokens
         ↓
Generate variations for remaining tokens
         ↓
Output: cleaned_refDict + variations_dict
```
