# Experiment Report - S5G.txt (algo1_2_v2)

Auto-generated aggregation of the recursive blocking + ARCS clustering pipeline for the `S5G.txt` dataset.

## 1. Dataset summary

- **Source file:** `S5G.txt`
- **Records loaded:** 3004
- **Unique records:** 3004
- **Truth clusters (good-DQ ground truth):** 1877
- **Truth equivalent pairs (E):** 1526
- **Truth source:** `truthABCgoodDQ.txt` (auto-detected by `er_metrics.detect_truth_file` because the filename contains a `G`).
- **Truth cluster size distribution:** `{"1": 1076, "2": 538, "3": 209, "4": 46, "5": 7, "6": 1}`
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

- **F1:** 0.8861
- **Precision:** 0.8729
- **Recall:** 0.8997
- **TP / FP / FN:** 1373 / 200 / 153
- **Linked pairs (L):** 1573
- **Expected pairs (E):** 1526
- **Group / config:** `G_blocking` / `full` / ablation `m1_p0`
- **Predicted clusters:** 1847 (822 multi, 1025 singletons)
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
- **Runtime breakdown (s):** recursive=1.701, filter=0.180, cluster=0.467, total=2.348

## 4. Observed patterns

### Precision / recall tradeoff
- Max precision: 1.0000 (recall at that row: 0.2942)
- Max recall: 0.8997 (precision at that row: 0.8729)
- Precision spread across runs: 0.9836; recall spread: 0.8768. The wider axis is precision.

### Sensitivity to clustering threshold `tau`
Means across all runs at each tau (uniform weighting unless specified):

|   tau |     F1 |   precision |   recall |   n |
|------:|-------:|------------:|---------:|----:|
|  0.05 | 0.7113 |      0.6402 |   0.8184 |   4 |
|  0.1  | 0.8018 |      0.8166 |   0.7942 |   4 |
|  0.2  | 0.6997 |      0.8818 |   0.6285 | 157 |
|  0.3  | 0.6172 |      0.9679 |   0.4813 |   4 |
|  0.4  | 0.624  |      0.85   |   0.5922 |   8 |
|  0.5  | 0.4248 |      0.9867 |   0.3145 |   4 |
|  1    | 0.7952 |      0.8978 |   0.7197 |   4 |

- Best mean F1 at `tau=0.1`; worst at `tau=0.5`.

### Cluster post-processing (`density_floor`)
Mean metrics at each `density_floor` cutoff:

|   density_floor |     F1 |   precision |   recall |   n |
|----------------:|-------:|------------:|---------:|----:|
|             0   | 0.6892 |      0.874  |   0.6261 | 173 |
|             0.3 | 0.7532 |      0.9372 |   0.6394 |   4 |
|             0.5 | 0.753  |      0.9371 |   0.6391 |   4 |
|             0.7 | 0.7469 |      0.9464 |   0.6257 |   4 |

### ARCS weighting mode
Uniform vs IDF weighting in the meta-blocking graph:

| arcs_weighting   |     F1 |   precision |   recall |   n |
|:-----------------|-------:|------------:|---------:|----:|
| idf              | 0.69   |      0.6681 |   0.7864 |  12 |
| uniform          | 0.6935 |      0.8928 |   0.6156 | 173 |

### Blocking strategy impact

| blocking_mode   |     F1 |   precision |   recall |   n |
|:----------------|-------:|------------:|---------:|----:|
| default         | 0.6902 |      0.8768 |   0.6241 | 180 |
| full            | 0.8031 |      0.9288 |   0.7208 |   4 |
| hierarchical    | 0.8061 |      0.9328 |   0.7097 |   1 |

### Filter-mode impact

| filter_mode   |     F1 |   precision |   recall |   n |
|:--------------|-------:|------------:|---------:|----:|
| composite     | 0.764  |      0.9382 |   0.6566 |  32 |
| keylen        | 0.775  |      0.9393 |   0.6744 |   4 |
| size          | 0.6737 |      0.8617 |   0.6184 | 145 |
| specificity   | 0.7528 |      0.9375 |   0.6387 |   4 |

### Runtime vs accuracy
- Pearson correlation between total runtime and F1: 0.102
- Fastest run: 0.547 s (F1=0.7042, group=`H_recursion_depth/d=1`)
- Slowest run: 6.063 s (F1=0.8053, group=`G_blocking/full`)

## 5. Key insights for research paper

- Largest precision-recall gap is 0.9771 in run `K_min_block_size/mbs=5/m0_p0` (P=1.0000, R=0.0229), highlighting which knob trades pair quality for pair completeness.
- 161 runs are FN-dominant (recall-limited) and 24 are FP-dominant (precision-limited).
- Uniform ARCS weighting mean F1 = 0.6935; IDF weighting mean F1 = 0.6900.
- `full` blocking F1 range: [0.7605, 0.8861] across 4 run(s).
- `hierarchical` blocking F1 range: [0.8061, 0.8061] across 1 run(s).

**Failure cases / anomalies:** Configurations that yielded F1 = 0 typically correspond to (a) overly aggressive thresholding (`tau` higher than the IDF/uniform edge weight scale), (b) `top_k=1` which strips co-occurrence signal, or (c) filter modes that disagree with `composite` zero-weight inputs. Such rows are useful as negative ablations in the paper.

## 6. Reproducibility instructions

All experiments use the existing pipeline at `Algo1_2_v2/recursive_algo1_2_v2.py`. The full grid is re-runnable end-to-end via:

```bash
cd /home/user/blockingandEmbeddinginER
DATASET=S5G.txt python RESULTS/run_experiments.py
DATASET=S5G.txt python RESULTS/aggregate_results.py
```

To rerun only the best configuration:

```bash
cd Algo1_2_v2 && \
    python recursive_algo1_2_v2.py \
    --input ../S5G.txt \
    --truth-dir .. \
    --clusters-json /tmp/S5G_best.json \
    --full-blocking \
    --max-block-pair-cost \
    100000
```

Auto-detected truth file for `S5G.txt` is `truthABCgoodDQ.txt`. The pipeline is deterministic given the same input and CLI args (no RNG seeds are exposed because the algorithm itself contains no stochastic steps).

## Artifacts

- `RESULTS/S5G_results.xlsx` &mdash; `runs` sheet (one row per pipeline configuration) and `summary` sheet (group-level aggregates).
- `RESULTS/runs/<group>/<config>/` &mdash; per-run clusters JSON, metrics JSON, metrics log, raw stdout, and invocation manifest.
- `RESULTS/run_experiments.py` &mdash; reproducible grid driver.
- `RESULTS/aggregate_results.py` &mdash; this report generator.
