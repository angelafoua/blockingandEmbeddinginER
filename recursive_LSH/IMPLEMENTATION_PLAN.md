# Recursive LSH Implementation Plan

## Overview
Implement a recursive Locality-Sensitive Hashing (LSH) algorithm for entity resolution that handles data quality variations (misspellings, abbreviations) by creating word signatures and progressively refining record buckets.

## Project Goals
1. Handle data quality variations (john/jon, smith/smyth, new york/ny)
2. Create efficient candidate pair discovery using LSH
3. Iteratively refine buckets to improve matching precision
4. Validate results on labeled data before scaling

---

## Phase 1: Foundation & Setup (Week 1)

### 1.1 Create Test Data & Validation Framework
**Files:** `data/test_dataset.py`, `validation/metrics.py`

**Tasks:**
- [ ] Create labeled test dataset (100-200 records with known duplicates)
- [ ] Implement precision/recall metrics
- [ ] Create confusion matrix reporting
- [ ] Document ground truth pairs

**Expected Output:**
- Test dataset with known duplicate pairs
- Evaluation functions to measure accuracy

**Acceptance Criteria:**
- Can load test data
- Can compute precision/recall correctly
- Clear reporting of results

---

### 1.2 Word Signature Creation Module
**Files:** `signatures/signature_generator.py`

**Tasks:**
- [ ] Implement fuzzy matching signature creation (similarity threshold)
- [ ] Implement phonetic signature creation (Soundex)
- [ ] Implement manual mapping signature creation
- [ ] Create signature validation/inspection tools

**Code Structure:**
```python
# signatures/signature_generator.py

class SignatureGenerator:
    def __init__(self, method='fuzzy', threshold=85):
        self.method = method
        self.threshold = threshold
    
    def create_signatures(self, refDict):
        """Create word signatures from token set"""
        pass
    
    def get_signature(self, word):
        """Get signature for a single word"""
        pass
    
    def inspect_signatures(self):
        """Debug: show signature groupings"""
        pass
```

**Expected Output:**
- Word → Signature mapping
- Signature grouping report

**Acceptance Criteria:**
- Fuzzy matching creates correct groupings
- Phonetic method handles names well
- Manual mapping is flexible
- Can inspect/debug signatures

---

## Phase 2: Single-Level LSH (Week 2)

### 2.1 Basic LSH Bucketing
**Files:** `lsh/simple_lsh.py`

**Tasks:**
- [ ] Implement MinHash signature creation
- [ ] Implement LSH index (bucketing)
- [ ] Implement candidate pair extraction
- [ ] Test on labeled data

**Code Structure:**
```python
# lsh/simple_lsh.py

class SimpleLSH:
    def __init__(self, num_perm=128, threshold=0.5):
        self.num_perm = num_perm
        self.threshold = threshold
    
    def create_minhash_signatures(self, record_signatures):
        """Convert records to MinHash signatures"""
        pass
    
    def build_index(self, minhash_signatures):
        """Build LSH index"""
        pass
    
    def get_candidates(self):
        """Extract candidate pairs from buckets"""
        pass
    
    def evaluate(self, ground_truth_pairs):
        """Evaluate against labeled data"""
        pass
```

**Expected Output:**
- Candidate pairs from LSH
- Precision/recall metrics
- Comparison to baseline

**Acceptance Criteria:**
- Candidate pairs make sense
- Precision/recall > 70% on test data
- Faster than brute force
- Can identify false positives/negatives

---

### 2.2 Simple Matching Rules
**Files:** `matching/simple_matcher.py`

**Tasks:**
- [ ] Implement token overlap matching
- [ ] Implement Jaccard similarity matching
- [ ] Implement field-level matching
- [ ] Threshold tuning

**Code Structure:**
```python
# matching/simple_matcher.py

class SimpleMatcher:
    def __init__(self, threshold=0.8):
        self.threshold = threshold
    
    def match_records(self, record_i, record_j):
        """Determine if two records match"""
        pass
    
    def compute_similarity(self, record_i, record_j):
        """Compute similarity score"""
        pass
```

**Acceptance Criteria:**
- Matching rules are interpretable
- Can explain why records matched
- Threshold tuning improves results

---

## Phase 3: Recursive LSH (Week 3)

### 3.1 Recursive Bucketing Algorithm
**Files:** `lsh/recursive_lsh.py`

**Tasks:**
- [ ] Implement recursive bucket refinement
- [ ] Handle stopping conditions (max_depth, min_bucket_size)
- [ ] Track bucket hierarchy
- [ ] Implement bucket inspection tools

**Code Structure:**
```python
# lsh/recursive_lsh.py

class RecursiveLSH:
    def __init__(self, num_perm=128, threshold=0.5, max_depth=3, min_bucket_size=2):
        self.num_perm = num_perm
        self.threshold = threshold
        self.max_depth = max_depth
        self.min_bucket_size = min_bucket_size
    
    def recursive_bucketing(self, records, signatures, depth=0):
        """Recursively refine buckets"""
        pass
    
    def get_final_buckets(self):
        """Extract final refined buckets"""
        pass
    
    def get_bucket_hierarchy(self):
        """Show bucket refinement at each level"""
        pass
    
    def evaluate(self, ground_truth_pairs):
        """Evaluate recursive approach"""
        pass
```

**Expected Output:**
- Refined buckets at multiple levels
- Hierarchy visualization
- Precision/recall improvement

**Acceptance Criteria:**
- Recursion doesn't over-partition (false negatives)
- Recursion doesn't under-partition (false positives)
- Improvement over single-level LSH
- Can explain bucket hierarchy

---

### 3.2 Transitive Closure & Merging
**Files:** `merging/transitive_closure.py`, `merging/record_merger.py`

**Tasks:**
- [ ] Implement transitive closure (A=B, B=C → A=C)
- [ ] Handle merging across bucket levels
- [ ] Implement canonical record selection
- [ ] Handle conflicts when multiple levels disagree

**Code Structure:**
```python
# merging/transitive_closure.py

class TransitiveClosure:
    def __init__(self):
        self.graph = defaultdict(set)
    
    def add_match(self, record_i, record_j):
        """Add a match pair"""
        pass
    
    def compute_groups(self):
        """Find connected components (duplicate groups)"""
        pass
    
    def get_canonical_groups(self):
        """Return final deduplicated groups"""
        pass

# merging/record_merger.py

class RecordMerger:
    def __init__(self, conflict_resolution='union'):
        """
        conflict_resolution: 'union' (combine all), 'first' (keep first), 'vote' (majority)
        """
        self.conflict_resolution = conflict_resolution
    
    def merge_records(self, duplicate_group):
        """Merge multiple records into one canonical record"""
        pass
    
    def merge_all_groups(self, duplicate_groups):
        """Merge all groups"""
        pass
```

**Acceptance Criteria:**
- Transitive closure correctly merges groups
- Handles conflicts gracefully
- Final dataset has no duplicates
- Can audit merge decisions

---

## Phase 4: Integration & Validation (Week 4)

### 4.1 Complete Pipeline
**Files:** `pipeline/recursive_lsh_pipeline.py`

**Tasks:**
- [ ] Integrate all components
- [ ] Create end-to-end pipeline
- [ ] Add logging and debugging
- [ ] Document usage

**Code Structure:**
```python
# pipeline/recursive_lsh_pipeline.py

class RecursiveLSHPipeline:
    def __init__(self, config):
        self.sig_generator = SignatureGenerator(config['signature_method'])
        self.lsh = RecursiveLSH(config['lsh_params'])
        self.matcher = SimpleMatcher(config['matching_threshold'])
        self.merger = RecordMerger(config['merge_strategy'])
    
    def run(self, input_records):
        """
        1. Create signatures
        2. Convert to signature sets
        3. Recursive LSH bucketing
        4. Match records in buckets
        5. Transitive closure
        6. Merge duplicates
        """
        pass
    
    def evaluate(self, ground_truth):
        """Full evaluation"""
        pass
    
    def report(self):
        """Generate results report"""
        pass
```

**Expected Output:**
- Deduplicated dataset
- Detailed evaluation metrics
- Audit trail of decisions

**Acceptance Criteria:**
- Pipeline runs end-to-end
- Results match manual validation
- Performance acceptable for dataset size
- Clear audit trail

---

### 4.2 Parameter Tuning & Optimization
**Files:** `optimization/parameter_tuning.py`

**Tasks:**
- [ ] Grid search for optimal parameters
- [ ] Sensitivity analysis
- [ ] Performance profiling
- [ ] Scalability testing

**Parameters to tune:**
- `num_perm`: MinHash signature size (128, 256, 512)
- `lsh_threshold`: Jaccard similarity threshold (0.5-0.9)
- `max_depth`: Maximum recursion depth (2-5)
- `min_bucket_size`: Minimum records per bucket (2-10)
- `matching_threshold`: Record similarity threshold (0.7-0.95)

**Expected Output:**
- Optimal parameter set
- Sensitivity analysis report
- Performance benchmarks

**Acceptance Criteria:**
- Parameters improve over baseline
- Can explain tradeoffs
- Scalable to larger datasets

---

## Phase 5: Documentation & Testing (Week 5)

### 5.1 Unit Tests
**Files:** `tests/test_*.py`

**Test Coverage:**
- [ ] `test_signature_generator.py` - Signature creation
- [ ] `test_simple_lsh.py` - Single-level LSH
- [ ] `test_recursive_lsh.py` - Recursive bucketing
- [ ] `test_matcher.py` - Matching rules
- [ ] `test_transitive_closure.py` - Merging
- [ ] `test_pipeline.py` - End-to-end

**Acceptance Criteria:**
- >80% code coverage
- All tests pass
- Edge cases handled

---

### 5.2 Documentation
**Files:** `README.md`, `USAGE.md`, code comments

**Tasks:**
- [ ] Write README (overview, quick start)
- [ ] Write USAGE.md (detailed guide)
- [ ] Document configuration options
- [ ] Add code comments/docstrings
- [ ] Create example notebooks

**Acceptance Criteria:**
- Someone unfamiliar with code can understand approach
- Can replicate results
- Can modify for different datasets

---

## Phase 6: Comparison with Existing Algorithms

### 6.1 Benchmark Against Baselines
**Files:** `comparison/benchmark.py`

**Compare against:**
- [ ] Your current token-based algorithm (Algo1_2_v2_refined)
- [ ] Simple brute-force matching
- [ ] Non-recursive LSH

**Metrics:**
- Precision/Recall
- F1 score
- Runtime (seconds)
- Memory usage
- Number of comparisons

**Expected Output:**
- Comparison table
- Performance graphs
- Recommendations

---

## Folder Structure

```
recursive_LSH/
├── IMPLEMENTATION_PLAN.md          (this file)
├── README.md                       (overview, quick start)
├── USAGE.md                        (detailed usage guide)
├── requirements.txt                (dependencies)
├── config/
│   ├── default_config.yaml         (default parameters)
│   └── tuned_config.yaml           (optimized parameters)
├── data/
│   ├── test_dataset.py             (labeled test data)
│   ├── sample_data.txt             (example records)
│   └── ground_truth.csv            (known duplicate pairs)
├── signatures/
│   ├── __init__.py
│   ├── signature_generator.py      (fuzzy, phonetic, manual)
│   └── test_signature_generator.py
├── lsh/
│   ├── __init__.py
│   ├── simple_lsh.py               (single-level LSH)
│   ├── recursive_lsh.py            (recursive bucketing)
│   ├── test_simple_lsh.py
│   └── test_recursive_lsh.py
├── matching/
│   ├── __init__.py
│   ├── simple_matcher.py           (matching rules)
│   └── test_matcher.py
├── merging/
│   ├── __init__.py
│   ├── transitive_closure.py       (connected components)
│   ├── record_merger.py            (record merging)
│   └── test_transitive_closure.py
├── pipeline/
│   ├── __init__.py
│   └── recursive_lsh_pipeline.py   (end-to-end pipeline)
├── validation/
│   ├── __init__.py
│   ├── metrics.py                  (precision, recall, F1)
│   └── evaluator.py                (evaluation harness)
├── optimization/
│   ├── __init__.py
│   └── parameter_tuning.py         (grid search)
├── comparison/
│   ├── __init__.py
│   └── benchmark.py                (compare with baselines)
├── notebooks/
│   ├── 01_explore_data.ipynb       (data exploration)
│   ├── 02_test_signatures.ipynb    (test signatures)
│   ├── 03_lsh_evaluation.ipynb     (LSH results)
│   ├── 04_recursive_evaluation.ipynb
│   └── 05_parameter_tuning.ipynb
├── results/
│   ├── metrics.json                (evaluation results)
│   ├── comparison.csv              (baseline comparison)
│   └── reports/                    (detailed reports)
└── tests/
    └── test_*.py                   (all unit tests)
```

---

## Timeline

| Phase | Duration | Focus |
|-------|----------|-------|
| Phase 1 | 1 week | Setup, test data, signatures |
| Phase 2 | 1 week | Basic LSH, matching rules |
| Phase 3 | 1 week | Recursive algorithm, merging |
| Phase 4 | 1 week | Integration, validation |
| Phase 5 | 1 week | Testing, documentation |
| Phase 6 | Ongoing | Optimization, comparison |

**Total: 4-5 weeks for MVP**

---

## Success Criteria

✅ **Core Functionality:**
- [ ] Creates word signatures handling variations
- [ ] Single-level LSH produces correct buckets
- [ ] Recursive LSH improves precision
- [ ] Transitive closure merges correctly

✅ **Quality:**
- [ ] Precision > 85% on test data
- [ ] Recall > 80% on test data
- [ ] No obvious false positives
- [ ] All tests pass

✅ **Performance:**
- [ ] Faster than brute force for large datasets
- [ ] Scalable to 100k+ records
- [ ] Memory efficient

✅ **Usability:**
- [ ] Clear documentation
- [ ] Reproducible results
- [ ] Configurable parameters
- [ ] Audit trail of decisions

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Over-partitioning (false negatives) | Medium | High | Validate recursion depth, min_bucket_size |
| Poor signature quality | Medium | High | Start with manual mappings, test first |
| Parameter sensitivity | High | Medium | Grid search, sensitivity analysis |
| Scalability issues | Low | Medium | Profile early, optimize bottlenecks |
| Transitive closure bugs | Medium | High | Thorough testing, audit trail |

---

## Next Steps

1. **Start Phase 1:** Create test data and validation framework
2. **Validate incrementally:** Test each phase before moving to next
3. **Adjust parameters:** Use ground truth to tune signatures
4. **Compare with baselines:** Ensure improvement over existing algorithms
5. **Document learnings:** Record what works and what doesn't
