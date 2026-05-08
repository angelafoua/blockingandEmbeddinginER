# Work Summary — Blocking & Embedding in Entity Resolution

This repo evolved from an initial recursive-LSH prototype into a full meta-blocking + clustering pipeline (`Algo1_2_v2`) with benchmarking, ablations, metrics, visualizations, and a draft research paper. The work spans **42 merged PRs** across roughly two dozen feature branches.

## Major workstreams

### 1. Recursive LSH pipeline (`recursive_LSH/`)
- Implemented the original 4-phase pipeline (Phase 0 data prep → Phase 3 clustering) from a planning doc.
- Split each phase into three runnable sub-step scripts (`phase_0_step_{1,2,3}.py`, etc.) for transparency and debugging.
- Added per-phase / per-step timing instrumentation and a per-run log file.
- Added CLI flags so the pipeline can run on arbitrary inputs.
- Made `data_quality_generator` the default Phase 0 variation method.
- Redesigned Phase 1 around signature-based token mapping.

### 2. Visualization
- Interactive matplotlib viewer for clusters.
- Interactive HTML viewer auto-generated on every pipeline run.
- Inlined D3.js so the HTML works offline (no CDN).
- Replaced an O(N²) circle-pack layout with a row-packing layout.
- Plotly-based viewer for final clusters (`S12PX_clusters_plotly.html`).
- `--variation-method=data_quality` support in `visualize.py`.
- Graceful fallback to CSV when `openpyxl` is unavailable.

### 3. DWM-style global correction (`global_correction.py`)
- Added DWM25 global correction as a pre-step before recursive blocking.
- Pair-based ER metrics (precision / recall / F1) for Algo1, Algo2, Algo3 in `er_metrics.py`.
- Wired global correction + ER metrics into `Algo1_2_v2_refined`.

### 4. `Algo1_2_v2` — meta-blocking pipeline (the main line of work)
Built on top of the refined recursive blocker, this became the focus of most iterations:

- **Recursive blocking core**: `recursive_algo1_2_v2.py` with `build_refDict.py`, `build_tokenFreqDict.py`, `refine_blocks.py`.
- **Stop-word removal**: dropped high-frequency tokens early in the pipeline.
- **Lossless subset purging**: removed blocks that are subsets of others.
- **Top-k smallest-block per record** filter.
- **ARCS meta-blocking graph** + Union-Find clustering for the final step.
- **Removed redundant** early high-frequency token filter (subsumed by stop-word stage).
- **Merge / purge ablation flags** + benchmarking harness.
- **Blocking-key alignment with DWM** (consistent token selection).
- **Tunable `stop_k`**: factor- or override-based, then split into three independent parameters.
- **CLI flags** for `stop_k`, `tau`, ablations.
- **Cluster-from-peak-block-count snapshot** during recursion (chooses the most informative recursion depth).
- **Lower default `tau`** to 0.2.
- **Cluster composition JSON dump** for inspection.
- **IDF-weighted ARCS scoring** (`--arcs-weighting idf`).
- **Density-based cluster splitting** (`--density-floor`).
- **Per-run metrics output**.
- **`--full-blocking`** (Papadakis redundancy-positive variant) + pair-cost guardrail.
- **`--hierarchical-blocking`** mode.
- **Enriched ARCS edge weights** with token length, type, and block density.
- Ground-truth: `S12PX_truth_clusters.json`.

### 5. Recursive MinHash Blocker
- Added a separate `recursive_minhash_blocker/` package as an alternate blocking strategy.

### 6. Research paper drafts (`Papers/`)
- `research_paper_draft.md`: initial template + iterative updates.
- `algo1_2_v2_paper.md`: ISCSi 2026 paper draft describing the `Algo1_2_v2` meta-blocking pipeline.
- Reference PDFs collected (Fellegi, Chen ICDM-2015, ModER, graph-theoretic fusion ER, etc.).

## Auxiliary
- `data_quality_generator.py` for synthetic variation.
- `truthABCgoodDQ.txt` / `truthABCpoorDQ.txt` ground-truth fixtures.
- `.gitignore` for Python bytecode caches.
- Path fix to use local `S12PX.txt`.

## Headline arc
Started with: a planning doc for recursive LSH.
Ended with: a parameterized, ablatable, IDF-weighted ARCS meta-blocking + Union-Find clustering pipeline (`Algo1_2_v2`) with hierarchical/full-blocking modes, density-floor cluster splitting, per-run metrics, ground-truth evaluation, multiple visualizations, and a draft conference paper.
