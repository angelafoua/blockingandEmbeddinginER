# Experiment Report - S14GX.txt (algo1_2_v2)

Auto-generated aggregation of the recursive blocking + ARCS clustering pipeline for the `S14GX.txt` dataset.

## 1. Dataset summary

- **Source file:** `S14GX.txt`
- **Records loaded:** 5000
- **Unique records:** 5000
- **Truth clusters (good-DQ ground truth):** 2183
- **Truth equivalent pairs (E):** 4865
- **Truth source:** `truthABCgoodDQ.txt` (auto-detected by `er_metrics.detect_truth_file` because the filename contains a `G`).
- **Truth cluster size distribution:** `{"1": 741, "2": 597, "3": 440, "4": 298, "5": 89, "6": 18}`
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

- **F1:** 0.8788
- **Precision:** 0.9225
- **Recall:** 0.8391
- **TP / FP / FN:** 4082 / 343 / 783
- **Linked pairs (L):** 4425
- **Expected pairs (E):** 4865
- **Group / config:** `G_blocking` / `full` / ablation `m1_p0`
- **Predicted clusters:** 2336 (1438 multi, 898 singletons)
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
- **Runtime breakdown (s):** recursive=2.304, filter=0.205, cluster=0.450, total=2.959

## 4. Observed patterns

### Precision / recall tradeoff
- Max precision: 1.0000 (recall at that row: 0.0290)
- Max recall: 0.8532 (precision at that row: 0.0650)
- Precision spread across runs: 0.9350; recall spread: 0.8440. The wider axis is precision.

### Sensitivity to clustering threshold `tau`
Means across all runs at each tau (uniform weighting unless specified):

|   tau |     F1 |   precision |   recall |   n |
|------:|-------:|------------:|---------:|----:|
|  0.05 | 0.716  |      0.7368 |   0.7373 |   4 |
|  0.1  | 0.7418 |      0.8987 |   0.6488 |   4 |
|  0.2  | 0.5663 |      0.9306 |   0.4489 | 157 |
|  0.3  | 0.415  |      0.9846 |   0.2939 |   4 |
|  0.4  | 0.5279 |      0.8942 |   0.4718 |   8 |
|  0.5  | 0.2688 |      0.9945 |   0.1787 |   4 |
|  1    | 0.6674 |      0.9465 |   0.5334 |   4 |

- Best mean F1 at `tau=0.1`; worst at `tau=0.5`.

### Cluster post-processing (`density_floor`)
Mean metrics at each `density_floor` cutoff:

|   density_floor |     F1 |   precision |   recall |   n |
|----------------:|-------:|------------:|---------:|----:|
|             0   | 0.5636 |      0.9238 |   0.4551 | 173 |
|             0.3 | 0.5874 |      0.9721 |   0.442  |   4 |
|             0.5 | 0.5871 |      0.9728 |   0.4412 |   4 |
|             0.7 | 0.5418 |      0.9772 |   0.3906 |   4 |

### ARCS weighting mode
Uniform vs IDF weighting in the meta-blocking graph:

| arcs_weighting   |     F1 |   precision |   recall |   n |
|:-----------------|-------:|------------:|---------:|----:|
| idf              | 0.6673 |      0.76   |   0.6709 |  12 |
| uniform          | 0.557  |      0.9387 |   0.438  | 173 |

### Blocking strategy impact

| blocking_mode   |     F1 |   precision |   recall |   n |
|:----------------|-------:|------------:|---------:|----:|
| default         | 0.5612 |      0.9261 |   0.4507 | 180 |
| full            | 0.6446 |      0.9625 |   0.5117 |   4 |
| hierarchical    | 0.7744 |      0.9619 |   0.6481 |   1 |

### Filter-mode impact

| filter_mode   |     F1 |   precision |   recall |   n |
|:--------------|-------:|------------:|---------:|----:|
| composite     | 0.6102 |      0.9718 |   0.4691 |  32 |
| keylen        | 0.626  |      0.9744 |   0.488  |   4 |
| size          | 0.5516 |      0.9146 |   0.449  | 145 |
| specificity   | 0.5867 |      0.9718 |   0.4412 |   4 |

### Runtime vs accuracy
- Pearson correlation between total runtime and F1: 0.135
- Fastest run: 0.723 s (F1=0.4608, group=`H_recursion_depth/d=1`)
- Slowest run: 7.295 s (F1=0.6480, group=`G_blocking/full`)

## 5. Key insights for research paper

- Largest precision-recall gap is 0.9908 in run `K_min_block_size/mbs=5/m0_p0` (P=1.0000, R=0.0092), highlighting which knob trades pair quality for pair completeness.
- 172 runs are FN-dominant (recall-limited) and 13 are FP-dominant (precision-limited).
- Uniform ARCS weighting mean F1 = 0.5570; IDF weighting mean F1 = 0.6673.
- `full` blocking F1 range: [0.5258, 0.8788] across 4 run(s).
- `hierarchical` blocking F1 range: [0.7744, 0.7744] across 1 run(s).

**Failure cases / anomalies:** Configurations that yielded F1 = 0 typically correspond to (a) overly aggressive thresholding (`tau` higher than the IDF/uniform edge weight scale), (b) `top_k=1` which strips co-occurrence signal, or (c) filter modes that disagree with `composite` zero-weight inputs. Such rows are useful as negative ablations in the paper.

## 6. Reproducibility instructions

All experiments use the existing pipeline at `Algo1_2_v2/recursive_algo1_2_v2.py`. The full grid is re-runnable end-to-end via:

```bash
cd /home/user/blockingandEmbeddinginER
DATASET=S14GX.txt python RESULTS/run_experiments.py
DATASET=S14GX.txt python RESULTS/aggregate_results.py
```

To rerun only the best configuration:

```bash
cd Algo1_2_v2 && \
    python recursive_algo1_2_v2.py \
    --input ../S14GX.txt \
    --truth-dir .. \
    --clusters-json /tmp/S14GX_best.json \
    --full-blocking \
    --max-block-pair-cost \
    100000
```

Auto-detected truth file for `S14GX.txt` is `truthABCgoodDQ.txt`. The pipeline is deterministic given the same input and CLI args (no RNG seeds are exposed because the algorithm itself contains no stochastic steps).

## Artifacts

- `RESULTS/S14GX_results.xlsx` &mdash; `runs` sheet (one row per pipeline configuration) and `summary` sheet (group-level aggregates).
- `RESULTS/runs/<group>/<config>/` &mdash; per-run clusters JSON, metrics JSON, metrics log, raw stdout, and invocation manifest.
- `RESULTS/run_experiments.py` &mdash; reproducible grid driver.
- `RESULTS/aggregate_results.py` &mdash; this report generator.
