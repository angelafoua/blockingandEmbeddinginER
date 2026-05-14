# Experiment Report - S1G.txt (algo1_2_v2)

Auto-generated aggregation of the recursive blocking + ARCS clustering pipeline for the `S1G.txt` dataset.

## 1. Dataset summary

- **Source file:** `S1G.txt`
- **Records loaded:** 50
- **Unique records:** 50
- **Truth clusters (good-DQ ground truth):** 30
- **Truth equivalent pairs (E):** 27
- **Truth source:** `truthABCgoodDQ.txt` (auto-detected by `er_metrics.detect_truth_file` because the filename contains a `G`).
- **Truth cluster size distribution:** `{"1": 16, "2": 9, "3": 4, "4": 1}`
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

- **F1:** 0.9818
- **Precision:** 0.9643
- **Recall:** 1.0000
- **TP / FP / FN:** 27 / 1 / 0
- **Linked pairs (L):** 28
- **Expected pairs (E):** 27
- **Group / config:** `D_tau` / `tau=0.3` / ablation `m0_p0`
- **Predicted clusters:** 29 (15 multi, 14 singletons)
- **Full parameter configuration:**
  - `blocking_mode` = default
  - `do_merge` = False
  - `do_purge` = False
  - `max_recursion_depth` = 5
  - `min_intra_freq` = 2
  - `top_k` = 3
  - `tau` = 0.3
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
- **Extra CLI args:** `--tau 0.3`
- **Runtime breakdown (s):** recursive=0.363, filter=0.037, cluster=0.002, total=0.402

## 4. Observed patterns

### Precision / recall tradeoff
- Max precision: 1.0000 (recall at that row: 0.1852)
- Max recall: 1.0000 (precision at that row: 0.7941)
- Precision spread across runs: 0.6301; recall spread: 1.0000. The wider axis is recall.

### Sensitivity to clustering threshold `tau`
Means across all runs at each tau (uniform weighting unless specified):

|   tau |     F1 |   precision |   recall |   n |
|------:|-------:|------------:|---------:|----:|
|  0.05 | 0.6376 |      0.4969 |   0.9722 |   4 |
|  0.1  | 0.8144 |      0.6961 |   1      |   4 |
|  0.2  | 0.7356 |      0.7574 |   0.7754 | 157 |
|  0.3  | 0.7906 |      0.922  |   0.7315 |   4 |
|  0.4  | 0.6758 |      0.8233 |   0.6806 |   8 |
|  0.5  | 0.385  |      0.9673 |   0.3055 |   4 |
|  1    | 0.5831 |      0.9483 |   0.5    |   4 |

- Best mean F1 at `tau=0.1`; worst at `tau=0.5`.

### Cluster post-processing (`density_floor`)
Mean metrics at each `density_floor` cutoff:

|   density_floor |     F1 |   precision |   recall |   n |
|----------------:|-------:|------------:|---------:|----:|
|             0   | 0.7185 |      0.7636 |   0.7615 | 173 |
|             0.3 | 0.7872 |      0.7652 |   0.8148 |   4 |
|             0.5 | 0.7719 |      0.7366 |   0.8148 |   4 |
|             0.7 | 0.7999 |      0.8784 |   0.7407 |   4 |

### ARCS weighting mode
Uniform vs IDF weighting in the meta-blocking graph:

| arcs_weighting   |     F1 |   precision |   recall |   n |
|:-----------------|-------:|------------:|---------:|----:|
| idf              | 0.6796 |       0.73  |   0.7901 |  12 |
| uniform          | 0.7259 |       0.768 |   0.7615 | 173 |

### Blocking strategy impact

| blocking_mode   |     F1 |   precision |   recall |   n |
|:----------------|-------:|------------:|---------:|----:|
| default         | 0.7277 |      0.7638 |   0.7687 | 180 |
| full            | 0.5192 |      0.8889 |   0.5185 |   4 |
| hierarchical    | 0.6667 |      0.5833 |   0.7778 |   1 |

### Filter-mode impact

| filter_mode   |     F1 |   precision |   recall |   n |
|:--------------|-------:|------------:|---------:|----:|
| composite     | 0.775  |      0.748  |   0.8125 |  32 |
| keylen        | 0.7468 |      0.6969 |   0.8148 |   4 |
| size          | 0.7087 |      0.771  |   0.7494 | 145 |
| specificity   | 0.7964 |      0.7745 |   0.8241 |   4 |

### Runtime vs accuracy
- Pearson correlation between total runtime and F1: 0.346
- Fastest run: 0.005 s (F1=0.6667, group=`G_blocking/hierarchical`)
- Slowest run: 0.662 s (F1=0.8889, group=`G_blocking/full`)

## 5. Key insights for research paper

- 2 runs reach F1 >= 0.95, indicating the pipeline can saturate recall and precision simultaneously on this dataset.
- 2 runs collapse to F1 = 0; these configurations are useful negative ablations.
- Largest precision-recall gap is 1.0000 in run `K_min_block_size/mbs=4/m0_p0` (P=1.0000, R=0.0000), highlighting which knob trades pair quality for pair completeness.
- 39 runs are FN-dominant (recall-limited) and 74 are FP-dominant (precision-limited).
- Uniform ARCS weighting mean F1 = 0.7259; IDF weighting mean F1 = 0.6796.
- `full` blocking F1 range: [0.2000, 0.8889] across 4 run(s).
- `hierarchical` blocking F1 range: [0.6667, 0.6667] across 1 run(s).

**Failure cases / anomalies:** Configurations that yielded F1 = 0 typically correspond to (a) overly aggressive thresholding (`tau` higher than the IDF/uniform edge weight scale), (b) `top_k=1` which strips co-occurrence signal, or (c) filter modes that disagree with `composite` zero-weight inputs. Such rows are useful as negative ablations in the paper.

## 6. Reproducibility instructions

All experiments use the existing pipeline at `Algo1_2_v2/recursive_algo1_2_v2.py`. The full grid is re-runnable end-to-end via:

```bash
cd /home/user/blockingandEmbeddinginER
DATASET=S1G.txt python RESULTS/run_experiments.py
DATASET=S1G.txt python RESULTS/aggregate_results.py
```

To rerun only the best configuration:

```bash
cd Algo1_2_v2 && \
    python recursive_algo1_2_v2.py \
    --input ../S1G.txt \
    --truth-dir .. \
    --clusters-json /tmp/S1G_best.json \
    --tau \
    0.3
```

Auto-detected truth file for `S1G.txt` is `truthABCgoodDQ.txt`. The pipeline is deterministic given the same input and CLI args (no RNG seeds are exposed because the algorithm itself contains no stochastic steps).

## Artifacts

- `RESULTS/S1G_results.xlsx` &mdash; `runs` sheet (one row per pipeline configuration) and `summary` sheet (group-level aggregates).
- `RESULTS/runs/<group>/<config>/` &mdash; per-run clusters JSON, metrics JSON, metrics log, raw stdout, and invocation manifest.
- `RESULTS/run_experiments.py` &mdash; reproducible grid driver.
- `RESULTS/aggregate_results.py` &mdash; this report generator.
