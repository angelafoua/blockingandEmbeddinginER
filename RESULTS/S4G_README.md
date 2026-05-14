# Experiment Report - S4G.txt (algo1_2_v2)

Auto-generated aggregation of the recursive blocking + ARCS clustering pipeline for the `S4G.txt` dataset.

## 1. Dataset summary

- **Source file:** `S4G.txt`
- **Records loaded:** 1912
- **Unique records:** 1912
- **Truth clusters (good-DQ ground truth):** 1188
- **Truth equivalent pairs (E):** 990
- **Truth source:** `truthABCgoodDQ.txt` (auto-detected by `er_metrics.detect_truth_file` because the filename contains a `G`).
- **Truth cluster size distribution:** `{"1": 678, "2": 339, "3": 136, "4": 28, "5": 6, "6": 1}`
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

- **F1:** 0.8826
- **Precision:** 0.9406
- **Recall:** 0.8313
- **TP / FP / FN:** 823 / 52 / 167
- **Linked pairs (L):** 875
- **Expected pairs (E):** 990
- **Group / config:** `I_density_floor` / `df=0.7` / ablation `m1_p0`
- **Predicted clusters:** 1241 (499 multi, 742 singletons)
- **Full parameter configuration:**
  - `blocking_mode` = default
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
  - `density_floor` = 0.7
  - `density_min_size` = 3
  - `arcs_pair_sim_weight` = 1.0
- **Extra CLI args:** `--density-floor 0.7`
- **Runtime breakdown (s):** recursive=0.352, filter=0.045, cluster=0.113, total=0.510

## 4. Observed patterns

### Precision / recall tradeoff
- Max precision: 1.0000 (recall at that row: 0.1646)
- Max recall: 0.9374 (precision at that row: 0.3531)
- Precision spread across runs: 0.9940; recall spread: 0.9020. The wider axis is precision.

### Sensitivity to clustering threshold `tau`
Means across all runs at each tau (uniform weighting unless specified):

|   tau |     F1 |   precision |   recall |   n |
|------:|-------:|------------:|---------:|----:|
|  0.05 | 0.7212 |      0.626  |   0.8798 |   4 |
|  0.1  | 0.8275 |      0.8143 |   0.8485 |   4 |
|  0.2  | 0.7222 |      0.8803 |   0.6643 | 157 |
|  0.3  | 0.6417 |      0.9668 |   0.5116 |   4 |
|  0.4  | 0.6457 |      0.8401 |   0.6333 |   8 |
|  0.5  | 0.4376 |      0.9851 |   0.331  |   4 |
|  1    | 0.7867 |      0.8893 |   0.7149 |   4 |

- Best mean F1 at `tau=0.1`; worst at `tau=0.5`.

### Cluster post-processing (`density_floor`)
Mean metrics at each `density_floor` cutoff:

|   density_floor |     F1 |   precision |   recall |   n |
|----------------:|-------:|------------:|---------:|----:|
|             0   | 0.7106 |      0.8719 |   0.6617 | 173 |
|             0.3 | 0.7756 |      0.9312 |   0.675  |   4 |
|             0.5 | 0.7757 |      0.932  |   0.6748 |   4 |
|             0.7 | 0.7703 |      0.9402 |   0.6614 |   4 |

### ARCS weighting mode
Uniform vs IDF weighting in the meta-blocking graph:

| arcs_weighting   |     F1 |   precision |   recall |   n |
|:-----------------|-------:|------------:|---------:|----:|
| idf              | 0.712  |      0.6795 |   0.8208 |  12 |
| uniform          | 0.7148 |      0.8896 |   0.6512 | 173 |

### Blocking strategy impact

| blocking_mode   |     F1 |   precision |   recall |   n |
|:----------------|-------:|------------:|---------:|----:|
| default         | 0.7121 |      0.8744 |   0.6606 | 180 |
| full            | 0.8054 |      0.9292 |   0.7237 |   4 |
| hierarchical    | 0.8108 |      0.9413 |   0.7121 |   1 |

### Filter-mode impact

| filter_mode   |     F1 |   precision |   recall |   n |
|:--------------|-------:|------------:|---------:|----:|
| composite     | 0.7864 |      0.9334 |   0.6922 |  32 |
| keylen        | 0.7965 |      0.932  |   0.7114 |   4 |
| size          | 0.6949 |      0.8602 |   0.6539 | 145 |
| specificity   | 0.7754 |      0.9325 |   0.6738 |   4 |

### Runtime vs accuracy
- Pearson correlation between total runtime and F1: 0.109
- Fastest run: 0.260 s (F1=0.7241, group=`H_recursion_depth/d=1`)
- Slowest run: 3.263 s (F1=0.8039, group=`G_blocking/full`)

## 5. Key insights for research paper

- Largest precision-recall gap is 0.9646 in run `K_min_block_size/mbs=5/m0_p0` (P=1.0000, R=0.0354), highlighting which knob trades pair quality for pair completeness.
- 159 runs are FN-dominant (recall-limited) and 26 are FP-dominant (precision-limited).
- Uniform ARCS weighting mean F1 = 0.7148; IDF weighting mean F1 = 0.7120.
- `full` blocking F1 range: [0.7677, 0.8825] across 4 run(s).
- `hierarchical` blocking F1 range: [0.8108, 0.8108] across 1 run(s).

**Failure cases / anomalies:** Configurations that yielded F1 = 0 typically correspond to (a) overly aggressive thresholding (`tau` higher than the IDF/uniform edge weight scale), (b) `top_k=1` which strips co-occurrence signal, or (c) filter modes that disagree with `composite` zero-weight inputs. Such rows are useful as negative ablations in the paper.

## 6. Reproducibility instructions

All experiments use the existing pipeline at `Algo1_2_v2/recursive_algo1_2_v2.py`. The full grid is re-runnable end-to-end via:

```bash
cd /home/user/blockingandEmbeddinginER
DATASET=S4G.txt python RESULTS/run_experiments.py
DATASET=S4G.txt python RESULTS/aggregate_results.py
```

To rerun only the best configuration:

```bash
cd Algo1_2_v2 && \
    python recursive_algo1_2_v2.py \
    --input ../S4G.txt \
    --truth-dir .. \
    --clusters-json /tmp/S4G_best.json \
    --density-floor \
    0.7
```

Auto-detected truth file for `S4G.txt` is `truthABCgoodDQ.txt`. The pipeline is deterministic given the same input and CLI args (no RNG seeds are exposed because the algorithm itself contains no stochastic steps).

## Artifacts

- `RESULTS/S4G_results.xlsx` &mdash; `runs` sheet (one row per pipeline configuration) and `summary` sheet (group-level aggregates).
- `RESULTS/runs/<group>/<config>/` &mdash; per-run clusters JSON, metrics JSON, metrics log, raw stdout, and invocation manifest.
- `RESULTS/run_experiments.py` &mdash; reproducible grid driver.
- `RESULTS/aggregate_results.py` &mdash; this report generator.
