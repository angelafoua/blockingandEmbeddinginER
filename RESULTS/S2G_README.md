# Experiment Report - S2G.txt (algo1_2_v2)

Auto-generated aggregation of the recursive blocking + ARCS clustering pipeline for the `S2G.txt` dataset.

## 1. Dataset summary

- **Source file:** `S2G.txt`
- **Records loaded:** 100
- **Unique records:** 100
- **Truth clusters (good-DQ ground truth):** 62
- **Truth equivalent pairs (E):** 48
- **Truth source:** `truthABCgoodDQ.txt` (auto-detected by `er_metrics.detect_truth_file` because the filename contains a `G`).
- **Truth cluster size distribution:** `{"1": 33, "2": 21, "3": 7, "4": 1}`
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

- **F1:** 0.9167
- **Precision:** 0.9167
- **Recall:** 0.9167
- **TP / FP / FN:** 44 / 4 / 4
- **Linked pairs (L):** 48
- **Expected pairs (E):** 48
- **Group / config:** `G_blocking` / `full` / ablation `m0_p0`
- **Predicted clusters:** 61 (31 multi, 30 singletons)
- **Full parameter configuration:**
  - `blocking_mode` = full
  - `do_merge` = False
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
- **Runtime breakdown (s):** recursive=0.532, filter=0.060, cluster=0.006, total=0.598

## 4. Observed patterns

### Precision / recall tradeoff
- Max precision: 1.0000 (recall at that row: 0.4375)
- Max recall: 1.0000 (precision at that row: 0.5275)
- Precision spread across runs: 0.8362; recall spread: 1.0000. The wider axis is recall.

### Sensitivity to clustering threshold `tau`
Means across all runs at each tau (uniform weighting unless specified):

|   tau |     F1 |   precision |   recall |   n |
|------:|-------:|------------:|---------:|----:|
|  0.05 | 0.7363 |      0.6004 |   0.9896 |   4 |
|  0.1  | 0.7852 |      0.6826 |   0.9323 |   4 |
|  0.2  | 0.7456 |      0.8039 |   0.7496 | 157 |
|  0.3  | 0.7364 |      0.938  |   0.6458 |   4 |
|  0.4  | 0.6656 |      0.8141 |   0.6641 |   8 |
|  0.5  | 0.5267 |      0.9539 |   0.4062 |   4 |
|  1    | 0.7779 |      0.9345 |   0.6979 |   4 |

- Best mean F1 at `tau=0.1`; worst at `tau=0.5`.

### Cluster post-processing (`density_floor`)
Mean metrics at each `density_floor` cutoff:

|   density_floor |     F1 |   precision |   recall |   n |
|----------------:|-------:|------------:|---------:|----:|
|             0   | 0.7349 |      0.804  |   0.7434 | 173 |
|             0.3 | 0.7916 |      0.8246 |   0.7708 |   4 |
|             0.5 | 0.7906 |      0.8277 |   0.7656 |   4 |
|             0.7 | 0.7926 |      0.8654 |   0.7344 |   4 |

### ARCS weighting mode
Uniform vs IDF weighting in the meta-blocking graph:

| arcs_weighting   |     F1 |   precision |   recall |   n |
|:-----------------|-------:|------------:|---------:|----:|
| idf              | 0.7619 |      0.7449 |   0.8507 |  12 |
| uniform          | 0.7369 |      0.8106 |   0.7369 | 173 |

### Blocking strategy impact

| blocking_mode   |     F1 |   precision |   recall |   n |
|:----------------|-------:|------------:|---------:|----:|
| default         | 0.7388 |      0.8058 |   0.7456 | 180 |
| full            | 0.7254 |      0.8481 |   0.6823 |   4 |
| hierarchical    | 0.7423 |      0.7347 |   0.75   |   1 |

### Filter-mode impact

| filter_mode   |     F1 |   precision |   recall |   n |
|:--------------|-------:|------------:|---------:|----:|
| composite     | 0.802  |      0.8381 |   0.7819 |  32 |
| keylen        | 0.7818 |      0.7898 |   0.7969 |   4 |
| size          | 0.7215 |      0.7986 |   0.7336 | 145 |
| specificity   | 0.8056 |      0.8478 |   0.776  |   4 |

### Runtime vs accuracy
- Pearson correlation between total runtime and F1: 0.213
- Fastest run: 0.015 s (F1=0.7423, group=`G_blocking/hierarchical`)
- Slowest run: 0.598 s (F1=0.9167, group=`G_blocking/full`)

## 5. Key insights for research paper

- 3 runs collapse to F1 = 0; these configurations are useful negative ablations.
- Largest precision-recall gap is 1.0000 in run `K_min_block_size/mbs=4/m0_p0` (P=1.0000, R=0.0000), highlighting which knob trades pair quality for pair completeness.
- 104 runs are FN-dominant (recall-limited) and 75 are FP-dominant (precision-limited).
- Uniform ARCS weighting mean F1 = 0.7369; IDF weighting mean F1 = 0.7619.
- `full` blocking F1 range: [0.5833, 0.9167] across 4 run(s).
- `hierarchical` blocking F1 range: [0.7423, 0.7423] across 1 run(s).

**Failure cases / anomalies:** Configurations that yielded F1 = 0 typically correspond to (a) overly aggressive thresholding (`tau` higher than the IDF/uniform edge weight scale), (b) `top_k=1` which strips co-occurrence signal, or (c) filter modes that disagree with `composite` zero-weight inputs. Such rows are useful as negative ablations in the paper.

## 6. Reproducibility instructions

All experiments use the existing pipeline at `Algo1_2_v2/recursive_algo1_2_v2.py`. The full grid is re-runnable end-to-end via:

```bash
cd /home/user/blockingandEmbeddinginER
DATASET=S2G.txt python RESULTS/run_experiments.py
DATASET=S2G.txt python RESULTS/aggregate_results.py
```

To rerun only the best configuration:

```bash
cd Algo1_2_v2 && \
    python recursive_algo1_2_v2.py \
    --input ../S2G.txt \
    --truth-dir .. \
    --clusters-json /tmp/S2G_best.json \
    --full-blocking \
    --max-block-pair-cost \
    100000
```

Auto-detected truth file for `S2G.txt` is `truthABCgoodDQ.txt`. The pipeline is deterministic given the same input and CLI args (no RNG seeds are exposed because the algorithm itself contains no stochastic steps).

## Artifacts

- `RESULTS/S2G_results.xlsx` &mdash; `runs` sheet (one row per pipeline configuration) and `summary` sheet (group-level aggregates).
- `RESULTS/runs/<group>/<config>/` &mdash; per-run clusters JSON, metrics JSON, metrics log, raw stdout, and invocation manifest.
- `RESULTS/run_experiments.py` &mdash; reproducible grid driver.
- `RESULTS/aggregate_results.py` &mdash; this report generator.
