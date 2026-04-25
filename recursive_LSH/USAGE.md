# Recursive LSH Usage Guide

## Table of Contents
1. [Installation](#installation)
2. [Basic Usage](#basic-usage)
3. [Creating Word Signatures](#creating-word-signatures)
4. [Running the Pipeline](#running-the-pipeline)
5. [Evaluating Results](#evaluating-results)
6. [Troubleshooting](#troubleshooting)

---

## Installation

### Requirements
- Python 3.8+
- Libraries: datasketch, fuzzywuzzy, scipy, pandas

### Setup

```bash
cd recursive_LSH

# Install dependencies
pip install -r requirements.txt

# (Optional) Run tests to verify installation
pytest tests/
```

---

## Basic Usage

### Minimal Example

```python
from pipeline.recursive_lsh_pipeline import RecursiveLSHPipeline
import yaml

# Load config
config = yaml.safe_load(open('config/default_config.yaml'))

# Create pipeline
pipeline = RecursiveLSHPipeline(config)

# Your records (dict: record_id -> list of tokens)
records = {
    1: ["john", "smith", "new", "york"],
    2: ["jon", "smith", "new", "york"],       # Duplicate of 1
    3: ["jane", "doe", "boston"],
    4: ["jane", "doe", "boston"]              # Duplicate of 3
}

# Run deduplication
results = pipeline.run(records)

# Print results
print(results)
# Output: Deduplicated records with duplicate groups identified
```

---

## Creating Word Signatures

### Option 1: Fuzzy Matching (Automatic)

Automatically groups similar words based on edit distance:

```python
from signatures.signature_generator import SignatureGenerator

# Create generator with fuzzy matching
sig_gen = SignatureGenerator(method='fuzzy', threshold=85)

# Tokenize your records
refDict = {
    1: ["john", "smith", "new", "york"],
    2: ["jon", "smith", "new", "york"],
    3: ["jane", "doe", "boston"]
}

# Generate signatures
word_signatures = sig_gen.create_signatures(refDict)

print(word_signatures)
# Output:
# {
#   "john": "SIG_0000",
#   "jon": "SIG_0000",           ← Same!
#   "smith": "SIG_0001",
#   "new": "SIG_0002",
#   ...
# }

# Inspect groupings
sig_gen.inspect_signatures()
# Shows which words were grouped together
```

**Tuning:**
- `threshold=95`: Very strict, only identical words grouped
- `threshold=85`: Moderate (default)
- `threshold=70`: Loose, many variations grouped

### Option 2: Phonetic Matching (For Names)

Good for handling name variations:

```python
sig_gen = SignatureGenerator(method='phonetic')

word_signatures = sig_gen.create_signatures(refDict)

# Output:
# {
#   "john": "PHON_J500",
#   "jon": "PHON_J500",      ← Phonetically similar
#   "jane": "PHON_J500",     ← Also phonetically similar!
#   "smith": "PHON_S530",
#   "smyth": "PHON_S530"     ← Same
# }
```

**Note:** Can be too loose (groups unrelated names like john/jane)

### Option 3: Manual Mapping (Most Precise)

Define known variations manually:

```python
sig_gen = SignatureGenerator(method='manual')

# Define signature groups
signature_groups = {
    "SIG_JOHN": ["john", "jon", "jhon", "jahn"],
    "SIG_SMITH": ["smith", "smyth", "smythe"],
    "SIG_NEWYORK": ["new york", "ny", "n.y."],
    "SIG_LOSANGELES": ["los angeles", "la", "l.a."]
}

sig_gen.set_manual_mappings(signature_groups)
word_signatures = sig_gen.create_signatures(refDict)
```

**Pros:** Most precise control  
**Cons:** Labor-intensive, needs domain expertise

---

## Running the Pipeline

### Step-by-Step Execution

```python
from pipeline.recursive_lsh_pipeline import RecursiveLSHPipeline
from data.test_dataset import load_test_data, get_ground_truth
import yaml

# Load configuration
config = yaml.safe_load(open('config/default_config.yaml'))

# Create pipeline
pipeline = RecursiveLSHPipeline(config)

# Load test data
test_records = load_test_data()

# Run pipeline
print("Step 1: Creating signatures...")
# (handled internally)

print("Step 2: Running recursive LSH...")
buckets = pipeline.lsh.recursive_bucketing(...)
# (handled internally)

print("Step 3: Matching and merging...")
results = pipeline.run(test_records)
# (handled internally)

print("Done!")
```

### Full Pipeline Object Usage

```python
# Configuration
config = {
    'signature_method': 'fuzzy',
    'signature_threshold': 85,
    'lsh_num_perm': 128,
    'lsh_threshold': 0.5,
    'max_depth': 3,
    'min_bucket_size': 2,
    'matching_threshold': 0.8,
    'merge_strategy': 'union'
}

pipeline = RecursiveLSHPipeline(config)

# Run on records
results = pipeline.run(test_records)

# Access results
print(f"Total input records: {len(test_records)}")
print(f"Deduplicated records: {len(results['deduplicated'])}")
print(f"Duplicate groups: {results['duplicate_groups']}")
print(f"Merge decisions: {results['merge_trace']}")

# Generate report
report = pipeline.report()
print(report)
```

---

## Evaluating Results

### On Labeled Test Data

```python
from validation.metrics import compute_metrics, precision_recall_fscore
from data.test_dataset import load_test_data, get_ground_truth

# Load ground truth (known duplicate pairs)
ground_truth = get_ground_truth()

# Run pipeline
results = pipeline.run(test_records)
predicted_pairs = results['predicted_duplicate_pairs']

# Compute metrics
metrics = compute_metrics(predicted_pairs, ground_truth)

print(f"Precision: {metrics['precision']:.2%}")
print(f"Recall: {metrics['recall']:.2%}")
print(f"F1 Score: {metrics['f1']:.2%}")
print(f"Accuracy: {metrics['accuracy']:.2%}")
```

### Detailed Analysis

```python
# Get false positives (pairs we said match but don't)
false_positives = metrics['false_positives']
print(f"\nFalse Positives ({len(false_positives)}):")
for record_i, record_j in false_positives[:5]:
    print(f"  Record {record_i} vs {record_j}")

# Get false negatives (pairs we missed)
false_negatives = metrics['false_negatives']
print(f"\nFalse Negatives ({len(false_negatives)}):")
for record_i, record_j in false_negatives[:5]:
    print(f"  Record {record_i} vs {record_j}")

# Confusion matrix
print(f"\nConfusion Matrix:")
print(f"  True Positives: {metrics['tp']}")
print(f"  True Negatives: {metrics['tn']}")
print(f"  False Positives: {metrics['fp']}")
print(f"  False Negatives: {metrics['fn']}")
```

### Adjust Parameters Based on Results

```python
# If low recall (missing duplicates):
# → Decrease matching_threshold (be more lenient)
# → Increase max_depth (more refined buckets)

config['matching_threshold'] = 0.75  # Was 0.8
config['max_depth'] = 4             # Was 3

pipeline = RecursiveLSHPipeline(config)
results = pipeline.run(test_records)
# Test again...

# If low precision (false positives):
# → Increase matching_threshold (be more strict)
# → Improve word signatures
# → Use manual mapping instead of fuzzy
```

---

## Configuration Guide

### Default Configuration (`config/default_config.yaml`)

```yaml
signature:
  method: 'fuzzy'              # 'fuzzy', 'phonetic', 'manual'
  similarity_threshold: 85     # 0-100, higher = more strict

lsh:
  num_perm: 128                # MinHash signature size
                               # Higher = more accurate but slower
                               # Try: 64, 128, 256, 512

  threshold: 0.5               # Jaccard similarity threshold
                               # Lower = more candidates (higher recall)
                               # Higher = fewer candidates (higher precision)
                               # Try: 0.3, 0.5, 0.7, 0.9

  max_depth: 3                 # Maximum recursion depth
                               # Higher = more refinement (more buckets)
                               # Try: 2, 3, 4, 5
                               # Warning: Too high = over-partition

  min_bucket_size: 2           # Minimum records per bucket
                               # Lower = more splitting
                               # Try: 1, 2, 5, 10
                               # Warning: Too low = over-partition

matching:
  threshold: 0.8               # Record similarity threshold
                               # Lower = more matches (higher recall)
                               # Higher = fewer matches (higher precision)
                               # Try: 0.7, 0.8, 0.85, 0.9

  method: 'jaccard'            # 'jaccard' (token overlap)
                               # 'cosine' (if using embeddings)

merging:
  strategy: 'union'            # How to merge duplicate records
                               # 'union': combine all tokens
                               # 'first': keep first record
                               # 'vote': majority vote
```

### Common Scenarios

**Scenario 1: High Precision (Few False Positives)**
```yaml
signature:
  similarity_threshold: 90     # Very strict signatures
lsh:
  threshold: 0.7               # Higher threshold = fewer candidates
matching:
  threshold: 0.85              # Stricter matching
```

**Scenario 2: High Recall (Find All Duplicates)**
```yaml
signature:
  similarity_threshold: 75     # Loose signatures
lsh:
  threshold: 0.3               # Lower threshold = more candidates
lsh:
  max_depth: 4                 # More refinement
matching:
  threshold: 0.75              # Looser matching
```

**Scenario 3: Balanced (F1 Score)**
```yaml
signature:
  similarity_threshold: 85     # Default
lsh:
  threshold: 0.5               # Default
lsh:
  max_depth: 3                 # Default
matching:
  threshold: 0.8               # Default
```

---

## Advanced Usage

### Custom Matching Rules

```python
class CustomMatcher:
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def match_records(self, record_i, record_j):
        """Your custom matching logic"""
        # Example: Must share first name AND last name
        first_match = record_i['tokens'][0] == record_j['tokens'][0]
        last_match = record_i['tokens'][1] == record_j['tokens'][1]
        return first_match and last_match

# Use in pipeline
pipeline.matcher = CustomMatcher(pipeline)
results = pipeline.run(test_records)
```

### Incremental Processing

```python
# Process records in batches
batch_size = 1000
all_results = []

for batch_start in range(0, len(records), batch_size):
    batch_end = batch_start + batch_size
    batch = {k: v for k, v in records.items() 
             if batch_start <= k < batch_end}
    
    results = pipeline.run(batch)
    all_results.append(results)

# Merge batch results
final_results = merge_batch_results(all_results)
```

### Parameter Tuning Grid Search

```python
from optimization.parameter_tuning import grid_search

param_grid = {
    'signature_threshold': [75, 85, 95],
    'lsh_threshold': [0.3, 0.5, 0.7],
    'matching_threshold': [0.75, 0.8, 0.85],
    'max_depth': [2, 3, 4]
}

best_config, results = grid_search(
    param_grid, 
    test_records, 
    ground_truth,
    metric='f1'  # Optimize for F1 score
)

print(f"Best config: {best_config}")
print(f"Best F1: {results['f1']:.2%}")
```

---

## Troubleshooting

### Issue: Too Many False Positives

**Symptoms:** Algorithm matches records that aren't duplicates

**Solutions:**
1. Increase `matching_threshold` (0.8 → 0.85)
2. Use stricter signatures (`similarity_threshold`: 85 → 90)
3. Reduce `max_depth` (3 → 2) to avoid over-refinement
4. Switch to manual signature mapping for known problems

### Issue: Too Many False Negatives

**Symptoms:** Algorithm misses actual duplicates

**Solutions:**
1. Decrease `matching_threshold` (0.8 → 0.75)
2. Use looser signatures (`similarity_threshold`: 85 → 75)
3. Increase `max_depth` (3 → 4) for more refinement
4. Lower `lsh_threshold` (0.5 → 0.3) for more candidates

### Issue: Slow Performance

**Symptoms:** Pipeline takes too long to run

**Solutions:**
1. Reduce `num_perm` (128 → 64) for MinHash
2. Reduce `max_depth` (3 → 2)
3. Increase `min_bucket_size` (2 → 5) to stop refining early
4. Use smaller test dataset to debug
5. Profile code: `python -m cProfile pipeline.py`

### Issue: Out of Memory

**Symptoms:** Process crashes with memory error

**Solutions:**
1. Process in batches (see Advanced Usage)
2. Reduce `num_perm` (128 → 64)
3. Reduce dataset size
4. Increase `min_bucket_size` to create fewer buckets

---

## Example: Complete Workflow

```python
from pipeline.recursive_lsh_pipeline import RecursiveLSHPipeline
from data.test_dataset import load_test_data, get_ground_truth
from validation.metrics import compute_metrics
import yaml

# 1. Load configuration
print("Loading configuration...")
config = yaml.safe_load(open('config/default_config.yaml'))

# 2. Create pipeline
print("Creating pipeline...")
pipeline = RecursiveLSHPipeline(config)

# 3. Load test data
print("Loading test data...")
test_records = load_test_data()
ground_truth = get_ground_truth()

# 4. Run deduplication
print("Running deduplication...")
results = pipeline.run(test_records)

# 5. Evaluate results
print("Evaluating results...")
metrics = compute_metrics(
    results['predicted_duplicate_pairs'],
    ground_truth
)

# 6. Print report
print("\n" + "="*50)
print("RESULTS")
print("="*50)
print(f"Input records: {len(test_records)}")
print(f"Output records: {len(results['deduplicated'])}")
print(f"Duplicates merged: {len(test_records) - len(results['deduplicated'])}")
print(f"\nPrecision: {metrics['precision']:.2%}")
print(f"Recall: {metrics['recall']:.2%}")
print(f"F1 Score: {metrics['f1']:.2%}")

# 7. Inspect failures
if metrics['false_positives']:
    print(f"\nFalse Positives ({len(metrics['false_positives'])}):")
    for record_i, record_j in metrics['false_positives'][:3]:
        print(f"  Record {record_i} vs {record_j}")

if metrics['false_negatives']:
    print(f"\nFalse Negatives ({len(metrics['false_negatives'])}):")
    for record_i, record_j in metrics['false_negatives'][:3]:
        print(f"  Record {record_i} vs {record_j}")

print("\nDone!")
```

---

## Questions?

See README.md for project overview or IMPLEMENTATION_PLAN.md for development phases.
