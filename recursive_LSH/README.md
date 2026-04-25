# Recursive LSH for Entity Resolution

## Quick Overview

This project implements a **Recursive Locality-Sensitive Hashing (LSH)** algorithm for entity resolution (deduplication) that handles real-world data quality issues.

### The Problem

Entity records often have **data quality variations**:
- Names: "John" vs "Jon" (typo)
- Names: "Smith" vs "Smyth" (alternative spelling)
- Locations: "New York" vs "NY" (abbreviation)

Traditional token-based blocking treats these as different tokens, missing true duplicates.

### The Solution

1. **Create word signatures** that group variations together
   - "john", "jon", "jhon" → all get signature `SIG_JOHN_001`
   - "smith", "smyth" → all get signature `SIG_SMITH_001`

2. **Use Recursive LSH** to efficiently find similar records
   - Level 1: Group by all shared signatures
   - Level 2: Refine groups by additional signatures
   - Level 3: Further refinement for precision

3. **Match and merge** duplicate records
   - Compare records within buckets
   - Apply matching rules
   - Merge duplicates into canonical records

---

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Basic Usage

```python
from pipeline.recursive_lsh_pipeline import RecursiveLSHPipeline
import yaml

# Load configuration
with open('config/default_config.yaml') as f:
    config = yaml.safe_load(f)

# Create pipeline
pipeline = RecursiveLSHPipeline(config)

# Run on your records
input_records = {
    1: ["john", "smith", "new", "york"],
    2: ["jon", "smith", "new", "york"],  # Duplicate of record 1
    3: ["jane", "doe", "boston"],
}

# Get deduplicated results
results = pipeline.run(input_records)

# Print report
pipeline.report()
```

### Evaluate on Test Data

```python
# Load test data with known duplicates
from data.test_dataset import load_test_data, get_ground_truth

test_records = load_test_data()
ground_truth = get_ground_truth()

# Run and evaluate
results = pipeline.run(test_records)
metrics = pipeline.evaluate(ground_truth)

print(f"Precision: {metrics['precision']:.2%}")
print(f"Recall: {metrics['recall']:.2%}")
print(f"F1 Score: {metrics['f1']:.2%}")
```

---

## How It Works

### Step 1: Create Word Signatures

Convert data quality variations into consistent signatures:

```
Input:  ["john", "jon", "jhon", "smith", "smyth"]
Output: {
    "john": "SIG_JOHN_001",
    "jon": "SIG_JOHN_001",      ← Same signature
    "jhon": "SIG_JOHN_001",     ← Same signature
    "smith": "SIG_SMITH_001",
    "smyth": "SIG_SMITH_001"    ← Same signature
}
```

### Step 2: Convert Records to Signatures

Replace words with their signatures:

```
Record 1: ["john", "smith", "new", "york"]
         ↓
Record 1: ["SIG_JOHN_001", "SIG_SMITH_001", "SIG_NEW_001", "SIG_YORK_001"]

Record 2: ["jon", "smith", "new", "york"]
         ↓
Record 2: ["SIG_JOHN_001", "SIG_SMITH_001", "SIG_NEW_001", "SIG_YORK_001"]
         ↑ Now identical!
```

### Step 3: Recursive LSH Bucketing

```
Level 1 (Initial):
  Bucket A: [Record 1, Record 2, Record 5]  ← All share same signatures

Level 2 (Refined):
  Sub-bucket A1: [Record 1, Record 2]       ← More specific match
  Sub-bucket A2: [Record 5]                 ← Different subset

Level 3 (Further refined):
  Final: [Record 1, Record 2]               ← Most specific group
```

### Step 4: Match Within Buckets

```
For Bucket A:
  Compare Record 1 vs Record 2
  Similarity: 95% match
  → DUPLICATE
```

### Step 5: Merge Duplicates

```
Record 1: ["john", "smith", "new", "york"]
Record 2: ["jon", "smith", "new", "york"]
         ↓ Merge
Canonical: ["john", "jon", "smith", "new", "york"]
```

---

## Advantages Over Baselines

### vs. Token-Based Blocking (Your Algo1_2_v2_refined)
- ✅ Handles data quality variations explicitly
- ✅ Recursive refinement improves precision
- ✅ More interpretable (signatures are explicit)
- ❌ Requires defining signatures upfront

### vs. Brute Force (Compare All Pairs)
- ✅ LSH: O(n·log n) vs Brute Force: O(n²)
- ✅ Scalable to millions of records
- ✅ Can handle approximate matching

### vs. Single-Level LSH
- ✅ Recursive refinement reduces false positives
- ✅ Progressive specificity improves precision
- ❌ More complex to implement and tune

---

## Configuration

See `config/default_config.yaml`:

```yaml
signature:
  method: 'fuzzy'              # 'fuzzy', 'phonetic', or 'manual'
  similarity_threshold: 85     # 0-100, higher = more strict

lsh:
  num_perm: 128                # MinHash signature size
  threshold: 0.5               # Jaccard similarity threshold
  max_depth: 3                 # Maximum recursion depth
  min_bucket_size: 2           # Stop refining when bucket < this

matching:
  threshold: 0.8               # Record similarity threshold
  method: 'jaccard'            # How to compute similarity

merging:
  strategy: 'union'            # 'union', 'first', or 'vote'
```

---

## Project Structure

```
recursive_LSH/
├── IMPLEMENTATION_PLAN.md    ← Detailed 5-week plan
├── README.md                 ← This file
├── USAGE.md                  ← Detailed usage guide
├── config/                   ← Configuration files
├── data/                     ← Test data and ground truth
├── signatures/               ← Word signature generation
├── lsh/                      ← LSH algorithms
├── matching/                 ← Record matching rules
├── merging/                  ← Duplicate merging
├── pipeline/                 ← End-to-end pipeline
├── validation/               ← Metrics and evaluation
├── optimization/             ← Parameter tuning
├── comparison/               ← Baseline comparisons
├── notebooks/                ← Jupyter notebooks for exploration
├── results/                  ← Results and reports
└── tests/                    ← Unit tests
```

---

## Key Files to Start With

1. **IMPLEMENTATION_PLAN.md** - Detailed 5-week development plan
2. **USAGE.md** - How to use the pipeline
3. **config/default_config.yaml** - Configuration parameters
4. **data/test_dataset.py** - Test data with known duplicates
5. **pipeline/recursive_lsh_pipeline.py** - Main pipeline code

---

## Development Phases

| Phase | Timeline | Focus |
|-------|----------|-------|
| 1 | Week 1 | Test data, word signatures |
| 2 | Week 2 | Basic LSH, matching |
| 3 | Week 3 | Recursive algorithm |
| 4 | Week 4 | Integration & validation |
| 5 | Week 5 | Testing & documentation |

See `IMPLEMENTATION_PLAN.md` for detailed breakdown.

---

## Validation & Metrics

The project uses standard deduplication metrics:

- **Precision**: Of the pairs we said match, how many actually match?
- **Recall**: Of all true duplicates, how many did we find?
- **F1 Score**: Harmonic mean of precision and recall

Example:
```
Ground truth: 100 duplicate pairs exist
Our algorithm found: 85 pairs
Of those 85: 80 are correct, 5 are false positives

Precision = 80/85 = 94%
Recall = 80/100 = 80%
F1 = 86.5%
```

---

## Next Steps

1. **Read IMPLEMENTATION_PLAN.md** for detailed phases
2. **Review config/default_config.yaml** to understand parameters
3. **Start Phase 1**: Create test data and validation framework
4. **Implement incrementally**: One phase at a time with validation

---

## Questions?

See USAGE.md for detailed examples and troubleshooting.
