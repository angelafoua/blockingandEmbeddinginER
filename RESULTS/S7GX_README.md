# Experiment Report - S7GX.txt (algo1_2_v2)

Auto-generated aggregation of the recursive blocking + ARCS clustering pipeline for the `S7GX.txt` dataset.

## 1. Dataset summary

- **Source file:** `S7GX.txt`
- **Records loaded:** 2912
- **Unique records:** 2912
- **Truth clusters (good-DQ ground truth):** 1827
- **Truth equivalent pairs (E):** 1468
- **Truth source:** `truthABCgoodDQ.txt` (auto-detected by `er_metrics.detect_truth_file` because the filename contains a `G`).
- **Truth cluster size distribution:** `{"1": 1056, "2": 516, "3": 205, "4": 42, "5": 7, "6": 1}`
- **Inferred structure:** Person-record CSV with fields `RecID, fname, lname, mname, address, city, state, zip, ssn`; intra-cluster variation includes case differences, typos (e.g. `AARON`/`AAARON`), SSN formatting (`490-46-2048` vs `490462048`), missing middle names, and swapped first/middle tokens.

## 2. Experiment coverage

- **Total runs aggregated:** 185
- **Runs with evaluable metrics (F1 present):** 185
- **Failed/missing runs:** 0
- **Parameter groups exercised:**
  - `A_merge_purge` &mdash; 4 rows
  - `B_filter_mode` &mdash; 16 rows
  - `C_composite` &mdash; 28 rows
  - `D_tau` &mdash; 24 rows
  - `E_top_k` &mdash; 20 rows
  - `F_arcs_idf` &mdash; 12 rows
  - `G_blocking` &mdash; 5 rows
  - `H_recursion_depth` &mdash; 24 rows
  - `I_density_floor` &mdash; 16 rows
  - `J_pair_sim_w` &mdash; 20 rows
  - `K_min_block_size` &mdash; 16 rows

Parameter axes swept:
- merge / purge ablation (4 configs)
- filter_mode in {size, specificity, keylen, composite}
- composite-mode weight triples (size / shared / tokenlen)
- ARCS clustering threshold `tau`
- Per-record `top_k` block filter
- ARCS weighting (uniform vs idf)
- blocking_mode (default vs full vs hierarchical)
- max_recursion_depth
- density-floor cluster split
- ARCS pair-similarity modulation weight
- min_block_size cut

## 3. Best configuration

- **F1:** 0.8863
- **Precision:** 0.8706
- **Recall:** 0.9026
- **TP / FP / FN:** 1325 / 197 / 143
- **Linked pairs (L):** 1522
- **Expected pairs (E):** 1468
- **Group / config:** `G_blocking` / `full` / ablation `m1_p0`
- **Predicted clusters:** 1798 (786 multi, 1012 singletons)
- **Full parameter configuration:**
  - `blocking_mode` = full
  - `do_merge` = True
  - `do_purge` = False
  - `max_recursion_depth` = 5
  - `min_intra_freq` = 2
  - `top_k` = 3
  - `tau` = 0.2
  - `min_block_size` = 2
  - `filter_mode` = size
  - `weight_size` = 0.0
  - `weight_shared` = 0.0
  - `weight_tokenlen` = 0.0
  - `cluster_on` = final
  - `arcs_weighting` = uniform
  - `density_floor` = 0.0
  - `density_min_size` = 3
  - `arcs_pair_sim_weight` = 1.0
- **Extra CLI args:** `--full-blocking --max-block-pair-cost 100000`
- **Runtime breakdown (s):** recursive=1.253, filter=0.109, cluster=0.290, total=1.652

## 4. Observed patterns

### Precision / recall tradeoff
- Max precision: 1.0000 (recall at that row: 0.2779)
- Max recall: 0.9230 (precision at that row: 0.3870)
- Precision spread across runs: 0.9890; recall spread: 0.8923. The wider axis is precision.

### Sensitivity to clustering threshold `tau`
Means across all runs at each tau (uniform weighting unless specified):

|   tau |     F1 |   precision |   recall |   n |
|------:|-------:|------------:|---------:|----:|
|  0.05 | 0.7174 |      0.6284 |   0.8598 |   4 |
|  0.1  | 0.8174 |      0.8178 |   0.8246 |   4 |
|  0.2  | 0.7068 |      0.8785 |   0.6444 | 157 |
|  0.3  | 0.6172 |      0.9671 |   0.4882 |   4 |
|  0.4  | 0.6332 |      0.8444 |   0.6189 |   8 |
|  0.5  | 0.4346 |      0.9854 |   0.3268 |   4 |
|  1    | 0.7974 |      0.8893 |   0.7306 |   4 |

- Best mean F1 at `tau=0.1`; worst at `tau=0.5`.

### Cluster post-processing (`density_floor`)
Mean metrics at each `density_floor` cutoff:

|   density_floor |     F1 |   precision |   recall |   n |
|----------------:|-------:|------------:|---------:|----:|
|             0   | 0.6964 |      0.8704 |   0.6432 | 173 |
|             0.3 | 0.7592 |      0.9319 |   0.6528 |   4 |
|             0.5 | 0.7597 |      0.932  |   0.6535 |   4 |
|             0.7 | 0.7541 |      0.9464 |   0.6368 |   4 |

### ARCS weighting mode
Uniform vs IDF weighting in the meta-blocking graph:

| arcs_weighting   |     F1 |   precision |   recall |   n |
|:-----------------|-------:|------------:|---------:|----:|
| idf              | 0.703  |      0.6681 |   0.8175 |  12 |
| uniform          | 0.7002 |      0.8891 |   0.6314 | 173 |

### Blocking strategy impact

| blocking_mode   |     F1 |   precision |   recall |   n |
|:----------------|-------:|------------:|---------:|----:|
| default         | 0.6976 |      0.8733 |   0.6415 | 180 |
| full            | 0.7966 |      0.9198 |   0.7156 |   4 |
| hierarchical    | 0.8111 |      0.9522 |   0.7064 |   1 |

### Filter-mode impact

| filter_mode   |     F1 |   precision |   recall |   n |
|:--------------|-------:|------------:|---------:|----:|
| composite     | 0.7742 |      0.9342 |   0.6769 |  32 |
| keylen        | 0.7812 |      0.9346 |   0.6886 |   4 |
| size          | 0.6803 |      0.8584 |   0.6347 | 145 |
| specificity   | 0.7572 |      0.9326 |   0.6492 |   4 |

### Runtime vs accuracy
- Pearson correlation between total runtime and F1: 0.102
- Fastest run: 0.411 s (F1=0.7015, group=`H_recursion_depth/d=1`)
- Slowest run: 4.510 s (F1=0.7888, group=`G_blocking/full`)

## 5. Key insights for research paper

- Largest precision-recall gap is 0.9693 in run `K_min_block_size/mbs=5/m0_p0` (P=1.0000, R=0.0307), highlighting which knob trades pair quality for pair completeness.
- 161 runs are FN-dominant (recall-limited) and 24 are FP-dominant (precision-limited).
- Uniform ARCS weighting mean F1 = 0.7002; IDF weighting mean F1 = 0.7030.
- `full` blocking F1 range: [0.7556, 0.8863] across 4 run(s).
- `hierarchical` blocking F1 range: [0.8111, 0.8111] across 1 run(s).

**Failure cases / anomalies:** Configurations that yielded F1 = 0 typically correspond to (a) overly aggressive thresholding (`tau` higher than the IDF/uniform edge weight scale), (b) `top_k=1` which strips co-occurrence signal, or (c) filter modes that disagree with `composite` zero-weight inputs. Such rows are useful as negative ablations in the paper.

## 6. Reproducibility instructions

All experiments use the existing pipeline at `Algo1_2_v2/recursive_algo1_2_v2.py`. The full grid is re-runnable end-to-end via:

```bash
cd /home/user/blockingandEmbeddinginER
DATASET=S7GX.txt python RESULTS/run_experiments.py
DATASET=S7GX.txt python RESULTS/aggregate_results.py
```

To rerun only the best configuration:

```bash
cd Algo1_2_v2 && \
    python recursive_algo1_2_v2.py \
    --input ../S7GX.txt \
    --truth-dir .. \
    --clusters-json /tmp/S7GX_best.json \
    --full-blocking \
    --max-block-pair-cost \
    100000
```

Auto-detected truth file for `S7GX.txt` is `truthABCgoodDQ.txt`. The pipeline is deterministic given the same input and CLI args (no RNG seeds are exposed because the algorithm itself contains no stochastic steps).

## Artifacts

- `RESULTS/S7GX_results.xlsx` &mdash; `runs` sheet (one row per pipeline configuration) and `summary` sheet (group-level aggregates).
- `RESULTS/runs/<group>/<config>/` &mdash; per-run clusters JSON, metrics JSON, metrics log, raw stdout, and invocation manifest.
- `RESULTS/run_experiments.py` &mdash; reproducible grid driver.
- `RESULTS/aggregate_results.py` &mdash; this report generator.
