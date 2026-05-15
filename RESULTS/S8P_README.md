# Experiment Report - S8P.txt (algo1_2_v2)

Auto-generated aggregation of the recursive blocking + ARCS clustering pipeline for the `S8P.txt` dataset.

## 1. Dataset summary

- **Source file:** `S8P.txt`
- **Records loaded:** 1000
- **Unique records:** 1000
- **Truth clusters (poor-DQ ground truth):** 195
- **Truth equivalent pairs (E):** 2811
- **Truth source:** `truthABCpoorDQ.txt` (auto-detected by `er_metrics.detect_truth_file` because the filename contains a `P`).
- **Truth cluster size distribution:** `{"1": 16, "2": 15, "3": 30, "4": 25, "5": 33, "6": 26, "7": 10, "8": 19, "9": 9, "10": 4, "11": 3, "12": 3, "14": 1, "17": 1}`
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

- **F1:** 0.5281
- **Precision:** 0.5527
- **Recall:** 0.5055
- **TP / FP / FN:** 1421 / 1150 / 1390
- **Linked pairs (L):** 2571
- **Expected pairs (E):** 2811
- **Group / config:** `D_tau` / `tau=0.05` / ablation `m1_p0`
- **Predicted clusters:** 291 (192 multi, 99 singletons)
- **Full parameter configuration:**
  - `blocking_mode` = default
  - `do_merge` = True
  - `do_purge` = False
  - `max_recursion_depth` = 5
  - `min_intra_freq` = 2
  - `top_k` = 3
  - `tau` = 0.05
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
- **Extra CLI args:** `--tau 0.05`
- **Runtime breakdown (s):** recursive=0.403, filter=0.041, cluster=0.059, total=0.503

## 4. Observed patterns

### Precision / recall tradeoff
- Max precision: 1.0000 (recall at that row: 0.0149)
- Max recall: 0.6450 (precision at that row: 0.0349)
- Precision spread across runs: 0.9651; recall spread: 0.6450. The wider axis is precision.

### Sensitivity to clustering threshold `tau`
Means across all runs at each tau (uniform weighting unless specified):

|   tau |     F1 |   precision |   recall |   n |
|------:|-------:|------------:|---------:|----:|
|  0.05 | 0.417  |      0.6775 |   0.3219 |   4 |
|  0.1  | 0.2918 |      0.7539 |   0.1854 |   4 |
|  0.2  | 0.1748 |      0.8413 |   0.1187 | 157 |
|  0.3  | 0.0976 |      0.9586 |   0.053  |   4 |
|  0.4  | 0.2095 |      0.8436 |   0.1406 |   8 |
|  0.5  | 0.0441 |      0.9753 |   0.0233 |   4 |
|  1    | 0.1935 |      0.8671 |   0.1114 |   4 |

- Best mean F1 at `tau=0.05`; worst at `tau=0.5`.

### Cluster post-processing (`density_floor`)
Mean metrics at each `density_floor` cutoff:

|   density_floor |     F1 |   precision |   recall |   n |
|----------------:|-------:|------------:|---------:|----:|
|             0   | 0.1815 |      0.8382 |   0.1241 | 173 |
|             0.3 | 0.173  |      0.8837 |   0.0981 |   4 |
|             0.5 | 0.1728 |      0.8915 |   0.0977 |   4 |
|             0.7 | 0.1312 |      0.9119 |   0.0716 |   4 |

### ARCS weighting mode
Uniform vs IDF weighting in the meta-blocking graph:

| arcs_weighting   |     F1 |   precision |   recall |   n |
|:-----------------|-------:|------------:|---------:|----:|
| idf              | 0.3304 |      0.7332 |   0.2459 |  12 |
| uniform          | 0.1696 |      0.8495 |   0.1133 | 173 |

### Blocking strategy impact

| blocking_mode   |     F1 |   precision |   recall |   n |
|:----------------|-------:|------------:|---------:|----:|
| default         | 0.1807 |      0.8405 |   0.1228 | 180 |
| full            | 0.1726 |      0.895  |   0.0971 |   4 |
| hierarchical    | 0.0917 |      0.8831 |   0.0484 |   1 |

### Filter-mode impact

| filter_mode   |     F1 |   precision |   recall |   n |
|:--------------|-------:|------------:|---------:|----:|
| composite     | 0.1714 |      0.8739 |   0.0974 |  32 |
| keylen        | 0.1796 |      0.8592 |   0.1032 |   4 |
| size          | 0.1822 |      0.8335 |   0.1284 | 145 |
| specificity   | 0.1715 |      0.8726 |   0.0975 |   4 |

### Runtime vs accuracy
- Pearson correlation between total runtime and F1: 0.224
- Fastest run: 0.179 s (F1=0.0917, group=`G_blocking/hierarchical`)
- Slowest run: 2.994 s (F1=0.1985, group=`G_blocking/full`)

## 5. Key insights for research paper

- 3 runs collapse to F1 = 0; these configurations are useful negative ablations.
- Largest precision-recall gap is 1.0000 in run `K_min_block_size/mbs=4/m0_p0` (P=1.0000, R=0.0000), highlighting which knob trades pair quality for pair completeness.
- 179 runs are FN-dominant (recall-limited) and 6 are FP-dominant (precision-limited).
- Uniform ARCS weighting mean F1 = 0.1696; IDF weighting mean F1 = 0.3304.
- `full` blocking F1 range: [0.1212, 0.2495] across 4 run(s).
- `hierarchical` blocking F1 range: [0.0917, 0.0917] across 1 run(s).

**Failure cases / anomalies:** Configurations that yielded F1 = 0 typically correspond to (a) overly aggressive thresholding (`tau` higher than the IDF/uniform edge weight scale), (b) `top_k=1` which strips co-occurrence signal, or (c) filter modes that disagree with `composite` zero-weight inputs. Such rows are useful as negative ablations in the paper.

## 6. Reproducibility instructions

All experiments use the existing pipeline at `Algo1_2_v2/recursive_algo1_2_v2.py`. The full grid is re-runnable end-to-end via:

```bash
cd /home/user/blockingandEmbeddinginER
DATASET=S8P.txt python RESULTS/run_experiments.py
DATASET=S8P.txt python RESULTS/aggregate_results.py
```

To rerun only the best configuration:

```bash
cd Algo1_2_v2 && \
    python recursive_algo1_2_v2.py \
    --input ../S8P.txt \
    --truth-dir .. \
    --clusters-json /tmp/S8P_best.json \
    --tau \
    0.05
```

Auto-detected truth file for `S8P.txt` is `truthABCpoorDQ.txt`. The pipeline is deterministic given the same input and CLI args (no RNG seeds are exposed because the algorithm itself contains no stochastic steps).

## Artifacts

- `RESULTS/S8P_results.xlsx` &mdash; `runs` sheet (one row per pipeline configuration) and `summary` sheet (group-level aggregates).
- `RESULTS/runs/<group>/<config>/` &mdash; per-run clusters JSON, metrics JSON, metrics log, raw stdout, and invocation manifest.
- `RESULTS/run_experiments.py` &mdash; reproducible grid driver.
- `RESULTS/aggregate_results.py` &mdash; this report generator.
