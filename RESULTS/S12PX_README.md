# Experiment Report - S12PX.txt (algo1_2_v2)

Auto-generated aggregation of the recursive blocking + ARCS clustering pipeline for the `S12PX.txt` dataset.

## 1. Dataset summary

- **Source file:** `S12PX.txt`
- **Records loaded:** 6000
- **Unique records:** 6000
- **Truth clusters (poor-DQ ground truth):** 693
- **Truth equivalent pairs (E):** 31735
- **Truth source:** `truthABCpoorDQ.txt` (auto-detected by `er_metrics.detect_truth_file` because the filename contains a `P`).
- **Truth cluster size distribution:** `{"1": 17, "2": 40, "3": 39, "4": 65, "5": 52, "6": 51, "7": 58, "8": 55, "9": 51, "10": 60, "11": 33, "12": 32, "13": 26, "14": 21, "15": 19, "16": 13, "17": 18, "18": 14, "19": 11, "20": 3, "21": 5, "22": 3, "23": 2, "25": 2, "26": 1, "28": 1, "35": 1}`
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

- **F1:** 0.4185
- **Precision:** 0.6638
- **Recall:** 0.3055
- **TP / FP / FN:** 9696 / 4910 / 22039
- **Linked pairs (L):** 14606
- **Expected pairs (E):** 31735
- **Group / config:** `D_tau` / `tau=0.05` / ablation `m1_p0`
- **Predicted clusters:** 2045 (1052 multi, 993 singletons)
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
- **Runtime breakdown (s):** recursive=2.503, filter=0.268, cluster=0.364, total=3.135

## 4. Observed patterns

### Precision / recall tradeoff
- Max precision: 1.0000 (recall at that row: 0.0007)
- Max recall: 0.4091 (precision at that row: 0.0097)
- Precision spread across runs: 0.9903; recall spread: 0.4091. The wider axis is precision.

### Sensitivity to clustering threshold `tau`
Means across all runs at each tau (uniform weighting unless specified):

|   tau |     F1 |   precision |   recall |   n |
|------:|-------:|------------:|---------:|----:|
|  0.05 | 0.3146 |      0.7666 |   0.2055 |   4 |
|  0.1  | 0.2252 |      0.8614 |   0.1328 |   4 |
|  0.2  | 0.1286 |      0.8712 |   0.0796 | 157 |
|  0.3  | 0.0718 |      0.958  |   0.0386 |   4 |
|  0.4  | 0.1702 |      0.8777 |   0.1065 |   8 |
|  0.5  | 0.0334 |      0.9778 |   0.0173 |   4 |
|  1    | 0.177  |      0.8729 |   0.1022 |   4 |

- Best mean F1 at `tau=0.05`; worst at `tau=0.5`.

### Cluster post-processing (`density_floor`)
Mean metrics at each `density_floor` cutoff:

|   density_floor |     F1 |   precision |   recall |   n |
|----------------:|-------:|------------:|---------:|----:|
|             0   | 0.1363 |      0.8697 |   0.0846 | 173 |
|             0.3 | 0.1287 |      0.9145 |   0.0724 |   4 |
|             0.5 | 0.1161 |      0.9223 |   0.064  |   4 |
|             0.7 | 0.0732 |      0.9351 |   0.0385 |   4 |

### ARCS weighting mode
Uniform vs IDF weighting in the meta-blocking graph:

| arcs_weighting   |     F1 |   precision |   recall |   n |
|:-----------------|-------:|------------:|---------:|----:|
| idf              | 0.2616 |      0.7302 |   0.1805 |  12 |
| uniform          | 0.1255 |      0.8831 |   0.0761 | 173 |

### Blocking strategy impact

| blocking_mode   |     F1 |   precision |   recall |   n |
|:----------------|-------:|------------:|---------:|----:|
| default         | 0.1336 |      0.8721 |   0.0827 | 180 |
| full            | 0.166  |      0.9045 |   0.0949 |   4 |
| hierarchical    | 0.1305 |      0.9484 |   0.0701 |   1 |

### Filter-mode impact

| filter_mode   |     F1 |   precision |   recall |   n |
|:--------------|-------:|------------:|---------:|----:|
| composite     | 0.1289 |      0.9048 |   0.0727 |  32 |
| keylen        | 0.1359 |      0.9048 |   0.0771 |   4 |
| size          | 0.1356 |      0.8645 |   0.0856 | 145 |
| specificity   | 0.128  |      0.9062 |   0.0724 |   4 |

### Runtime vs accuracy
- Pearson correlation between total runtime and F1: 0.188
- Fastest run: 1.044 s (F1=0.2084, group=`H_recursion_depth/d=1`)
- Slowest run: 17.496 s (F1=0.1721, group=`G_blocking/full`)

## 5. Key insights for research paper

- 2 runs collapse to F1 = 0; these configurations are useful negative ablations.
- Largest precision-recall gap is 1.0000 in run `K_min_block_size/mbs=4/m0_p0` (P=1.0000, R=0.0000), highlighting which knob trades pair quality for pair completeness.
- 182 runs are FN-dominant (recall-limited) and 3 are FP-dominant (precision-limited).
- Uniform ARCS weighting mean F1 = 0.1255; IDF weighting mean F1 = 0.2616.
- `full` blocking F1 range: [0.0934, 0.3050] across 4 run(s).
- `hierarchical` blocking F1 range: [0.1305, 0.1305] across 1 run(s).

**Failure cases / anomalies:** Configurations that yielded F1 = 0 typically correspond to (a) overly aggressive thresholding (`tau` higher than the IDF/uniform edge weight scale), (b) `top_k=1` which strips co-occurrence signal, or (c) filter modes that disagree with `composite` zero-weight inputs. Such rows are useful as negative ablations in the paper.

## 6. Reproducibility instructions

All experiments use the existing pipeline at `Algo1_2_v2/recursive_algo1_2_v2.py`. The full grid is re-runnable end-to-end via:

```bash
cd /home/user/blockingandEmbeddinginER
DATASET=S12PX.txt python RESULTS/run_experiments.py
DATASET=S12PX.txt python RESULTS/aggregate_results.py
```

To rerun only the best configuration:

```bash
cd Algo1_2_v2 && \
    python recursive_algo1_2_v2.py \
    --input ../S12PX.txt \
    --truth-dir .. \
    --clusters-json /tmp/S12PX_best.json \
    --tau \
    0.05
```

Auto-detected truth file for `S12PX.txt` is `truthABCgoodDQ.txt`. The pipeline is deterministic given the same input and CLI args (no RNG seeds are exposed because the algorithm itself contains no stochastic steps).

## Artifacts

- `RESULTS/S12PX_results.xlsx` &mdash; `runs` sheet (one row per pipeline configuration) and `summary` sheet (group-level aggregates).
- `RESULTS/runs/<group>/<config>/` &mdash; per-run clusters JSON, metrics JSON, metrics log, raw stdout, and invocation manifest.
- `RESULTS/run_experiments.py` &mdash; reproducible grid driver.
- `RESULTS/aggregate_results.py` &mdash; this report generator.
