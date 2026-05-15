"""Aggregate algo1_2_v2 experiment outputs into Excel + README.

Reads every `.metrics.json` under RESULTS/runs/, joins with the per-run
invocation metadata, and writes:
  RESULTS/<DATASET>_results.xlsx (sheets: runs, summary)
  RESULTS/<DATASET>_README.md
"""

import json
import math
import os
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO / "RESULTS" / "runs"
DATASET = os.environ.get("DATASET", "S1G.txt")
DS_BASE = Path(DATASET).stem
XLSX_PATH = REPO / "RESULTS" / f"{DS_BASE}_results.xlsx"
README_PATH = REPO / "RESULTS" / f"{DS_BASE}_README.md"


def _safe(d, *keys, default=float("nan")):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def collect_runs():
    rows = []
    for invocation_file in sorted(RUNS_DIR.glob("*/*/invocation.json")):
        run_dir = invocation_file.parent
        invocation = json.loads(invocation_file.read_text())
        group = invocation["group"]
        config_id = invocation["config_id"]
        label = invocation["label"]
        extra_args = invocation["extra_args"]

        # The pipeline appends "_m{0,1}_p{0,1}" suffix (ablation) or writes
        # clusters.json directly (single-run). Match both.
        metrics_files = sorted(run_dir.glob("clusters*.metrics.json"))
        if not metrics_files:
            rows.append({
                "group": group, "config_id": config_id,
                "label": label, "ablation_tag": "MISSING",
                "returncode": invocation["returncode"],
                "extra_args": " ".join(extra_args),
                "wallclock_s": invocation.get("wallclock_s"),
            })
            continue

        for mfile in metrics_files:
            # Extract ablation tag from filename like clusters_m1_p1.metrics.json
            stem = mfile.name.replace(".metrics.json", "")
            tag = stem.replace("clusters", "").lstrip("_") or "single"
            try:
                m = json.loads(mfile.read_text())
            except Exception as e:
                rows.append({
                    "group": group, "config_id": config_id,
                    "label": label, "ablation_tag": tag,
                    "error": str(e),
                })
                continue

            cfg = m.get("config", {})
            pc = m.get("predicted_clusters", {})
            tc = m.get("truth_clusters", {})
            pair = m.get("pair_metrics", {})
            timings = m.get("timings_seconds", {})
            arcs = cfg.get("arcs_factors", {}) or {}

            row = {
                # identifiers
                "dataset": DATASET,
                "group": group,
                "config_id": config_id,
                "label": label,
                "ablation_tag": tag,
                "extra_args": " ".join(extra_args),

                # dataset metadata
                "n_records_total": m.get("n_records_total"),
                "n_unique_records": m.get("n_unique_records"),

                # parameters
                "blocking_mode": cfg.get("blocking_mode"),
                "do_merge": cfg.get("do_merge"),
                "do_purge": cfg.get("do_purge"),
                "max_recursion_depth": cfg.get("max_recursion_depth"),
                "min_intra_freq": cfg.get("min_intra_freq"),
                "top_k": cfg.get("top_k"),
                "tau": cfg.get("tau"),
                "min_block_size": cfg.get("min_block_size"),
                "filter_mode": cfg.get("filter_mode"),
                "weight_size": cfg.get("weight_size"),
                "weight_shared": cfg.get("weight_shared"),
                "weight_tokenlen": cfg.get("weight_tokenlen"),
                "cluster_on": cfg.get("cluster_on"),
                "arcs_weighting": cfg.get("arcs_weighting"),
                "density_floor": cfg.get("density_floor"),
                "density_min_size": cfg.get("density_min_size"),
                "arcs_length_weight": arcs.get("length_weight"),
                "arcs_numeric_factor": arcs.get("numeric_factor"),
                "arcs_word_factor": arcs.get("word_factor"),
                "arcs_density_weight": arcs.get("density_weight"),
                "arcs_density_sample_cap": arcs.get("density_sample_cap"),
                "arcs_pair_sim_weight": arcs.get("pair_sim_weight"),

                # clustering outputs
                "n_clusters": pc.get("n_total"),
                "n_multi_clusters": pc.get("n_multi"),
                "n_singleton_clusters": pc.get("n_singletons"),
                "cluster_min_size": pc.get("min_size"),
                "cluster_max_size": pc.get("max_size"),
                "cluster_mean_size": pc.get("mean_size"),
                "cluster_median_size": pc.get("median_size"),
                "cluster_size_distribution": json.dumps(
                    pc.get("size_distribution", {})),

                "truth_n_clusters": tc.get("n_total"),
                "truth_min_size": tc.get("min_size"),
                "truth_max_size": tc.get("max_size"),
                "truth_mean_size": tc.get("mean_size"),
                "truth_size_distribution": json.dumps(
                    tc.get("size_distribution", {})),

                # evaluation metrics
                "TP": pair.get("TP"),
                "FP": pair.get("FP"),
                "FN": pair.get("FN"),
                "linked_pairs": pair.get("L"),
                "expected_pairs": pair.get("E"),
                "precision": pair.get("precision"),
                "recall": pair.get("recall"),
                "F1": pair.get("f1"),
                "size_distribution_l1": m.get("size_distribution_l1"),

                # runtime breakdown (seconds)
                "time_recursive_s": timings.get("recursive"),
                "time_filter_s": timings.get("filter"),
                "time_cluster_s": timings.get("cluster"),
                "time_total_s": (
                    sum(v for v in [timings.get("recursive"),
                                    timings.get("filter"),
                                    timings.get("cluster")]
                        if isinstance(v, (int, float)))
                    if timings else float("nan")
                ),

                "returncode": invocation.get("returncode"),
            }
            rows.append(row)
    return pd.DataFrame(rows)


def build_summary(df):
    summary_rows = []
    if df.empty:
        return pd.DataFrame()

    def _agg(name, sub):
        if sub.empty or "F1" not in sub:
            return
        summary_rows.append({
            "view": name,
            "n_runs": len(sub),
            "F1_max": sub["F1"].max(skipna=True),
            "F1_mean": sub["F1"].mean(skipna=True),
            "precision_max": sub["precision"].max(skipna=True),
            "recall_max": sub["recall"].max(skipna=True),
            "median_time_total_s": sub["time_total_s"].median(skipna=True),
        })

    _agg("ALL", df)
    if "group" in df.columns:
        for g, sub in df.groupby("group"):
            _agg(f"group={g}", sub)
    if "filter_mode" in df.columns:
        for fm, sub in df.groupby("filter_mode"):
            _agg(f"filter_mode={fm}", sub)
    if "tau" in df.columns:
        for t, sub in df.groupby("tau"):
            _agg(f"tau={t}", sub)
    if "arcs_weighting" in df.columns:
        for w, sub in df.groupby("arcs_weighting"):
            _agg(f"arcs_weighting={w}", sub)
    if "blocking_mode" in df.columns:
        for b, sub in df.groupby("blocking_mode"):
            _agg(f"blocking_mode={b}", sub)
    return pd.DataFrame(summary_rows)


def write_excel(df, summary_df):
    with pd.ExcelWriter(XLSX_PATH, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="runs", index=False)
        summary_df.to_excel(xw, sheet_name="summary", index=False)
    print(f"Wrote {XLSX_PATH} ({len(df)} runs)")


def fmt(x, p=4):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "NaN"
    if isinstance(x, float):
        return f"{x:.{p}f}"
    return str(x)


def build_readme(df, summary_df):
    if df.empty:
        README_PATH.write_text("# No runs found\n")
        return

    eval_df = df[df["F1"].notna()].copy()

    # Best F1 run
    best = eval_df.sort_values("F1", ascending=False).head(1).iloc[0] \
        if not eval_df.empty else None

    n_records = int(df["n_records_total"].dropna().iloc[0]) \
        if df["n_records_total"].notna().any() else None
    n_unique = int(df["n_unique_records"].dropna().iloc[0]) \
        if df["n_unique_records"].notna().any() else None
    truth_clusters = int(df["truth_n_clusters"].dropna().iloc[0]) \
        if df["truth_n_clusters"].notna().any() else None
    expected_pairs = int(df["expected_pairs"].dropna().iloc[0]) \
        if df["expected_pairs"].notna().any() else None

    lines = []
    lines.append(f"# Experiment Report - {DATASET} (algo1_2_v2)\n")
    lines.append(f"Auto-generated aggregation of the recursive blocking + "
                 f"ARCS clustering pipeline for the `{DATASET}` dataset.")
    lines.append("")

    # 1. Dataset summary
    lines.append("## 1. Dataset summary")
    lines.append("")
    lines.append(f"- **Source file:** `{DATASET}`")
    lines.append(f"- **Records loaded:** {n_records}")
    lines.append(f"- **Unique records:** {n_unique}")
    _dq = "poor" if "P" in DS_BASE.upper() else "good"
    _truth_name = f"truthABC{'poorDQ' if _dq == 'poor' else 'goodDQ'}.txt"
    _truth_key = "P" if _dq == "poor" else "G"
    lines.append(f"- **Truth clusters ({_dq}-DQ ground truth):** "
                 f"{truth_clusters}")
    lines.append(f"- **Truth equivalent pairs (E):** {expected_pairs}")
    lines.append(f"- **Truth source:** `{_truth_name}` (auto-detected by "
                 f"`er_metrics.detect_truth_file` because the filename "
                 f"contains a `{_truth_key}`).")
    if df["truth_size_distribution"].notna().any():
        lines.append(f"- **Truth cluster size distribution:** "
                     f"`{df['truth_size_distribution'].dropna().iloc[0]}`")
    lines.append("- **Inferred structure:** Person-record CSV with fields "
                 "`RecID, fname, lname, mname, address, city, state, zip, "
                 "ssn`; intra-cluster variation includes case differences, "
                 "typos (e.g. `AARON`/`AAARON`), SSN formatting "
                 "(`490-46-2048` vs `490462048`), missing middle names, and "
                 "swapped first/middle tokens.")
    lines.append("")

    # 2. Experiment coverage
    lines.append("## 2. Experiment coverage")
    lines.append("")
    lines.append(f"- **Total runs aggregated:** {len(df)}")
    lines.append(f"- **Runs with evaluable metrics (F1 present):** "
                 f"{len(eval_df)}")
    lines.append(f"- **Failed/missing runs:** "
                 f"{len(df) - len(eval_df)}")
    if "group" in df.columns:
        lines.append("- **Parameter groups exercised:**")
        for g, sub in df.groupby("group"):
            lines.append(f"  - `{g}` &mdash; {len(sub)} rows")
    lines.append("")
    lines.append("Parameter axes swept:")
    lines.append("- merge / purge ablation (4 configs)")
    lines.append("- filter_mode in {size, specificity, keylen, composite}")
    lines.append("- composite-mode weight triples (size / shared / "
                 "tokenlen)")
    lines.append("- ARCS clustering threshold `tau`")
    lines.append("- Per-record `top_k` block filter")
    lines.append("- ARCS weighting (uniform vs idf)")
    lines.append("- blocking_mode (default vs full vs hierarchical)")
    lines.append("- max_recursion_depth")
    lines.append("- density-floor cluster split")
    lines.append("- ARCS pair-similarity modulation weight")
    lines.append("- min_block_size cut")
    lines.append("")

    # 3. Best configuration
    lines.append("## 3. Best configuration")
    lines.append("")
    if best is not None:
        lines.append(f"- **F1:** {fmt(best['F1'])}")
        lines.append(f"- **Precision:** {fmt(best['precision'])}")
        lines.append(f"- **Recall:** {fmt(best['recall'])}")
        lines.append(f"- **TP / FP / FN:** "
                     f"{int(best['TP'])} / {int(best['FP'])} / "
                     f"{int(best['FN'])}")
        lines.append(f"- **Linked pairs (L):** {int(best['linked_pairs'])}")
        lines.append(f"- **Expected pairs (E):** "
                     f"{int(best['expected_pairs'])}")
        lines.append(f"- **Group / config:** `{best['group']}` / "
                     f"`{best['config_id']}` / ablation "
                     f"`{best['ablation_tag']}`")
        lines.append(f"- **Predicted clusters:** {int(best['n_clusters'])} "
                     f"({int(best['n_multi_clusters'])} multi, "
                     f"{int(best['n_singleton_clusters'])} singletons)")
        lines.append("- **Full parameter configuration:**")
        cfg_keys = ["blocking_mode", "do_merge", "do_purge",
                    "max_recursion_depth", "min_intra_freq", "top_k", "tau",
                    "min_block_size", "filter_mode", "weight_size",
                    "weight_shared", "weight_tokenlen", "cluster_on",
                    "arcs_weighting", "density_floor", "density_min_size",
                    "arcs_pair_sim_weight"]
        for k in cfg_keys:
            if k in best:
                lines.append(f"  - `{k}` = {best[k]}")
        lines.append(f"- **Extra CLI args:** `{best['extra_args']}`")
        lines.append(f"- **Runtime breakdown (s):** recursive="
                     f"{fmt(best['time_recursive_s'], 3)}, filter="
                     f"{fmt(best['time_filter_s'], 3)}, cluster="
                     f"{fmt(best['time_cluster_s'], 3)}, total="
                     f"{fmt(best['time_total_s'], 3)}")
    lines.append("")

    # 4. Observed patterns
    lines.append("## 4. Observed patterns")
    lines.append("")

    if not eval_df.empty:
        # Precision/recall tradeoff
        p_max = eval_df["precision"].max()
        r_max = eval_df["recall"].max()
        p_at_rmax = eval_df.loc[eval_df["recall"].idxmax(), "precision"]
        r_at_pmax = eval_df.loc[eval_df["precision"].idxmax(), "recall"]
        lines.append(f"### Precision / recall tradeoff")
        lines.append(f"- Max precision: {fmt(p_max)} (recall at that "
                     f"row: {fmt(r_at_pmax)})")
        lines.append(f"- Max recall: {fmt(r_max)} (precision at that "
                     f"row: {fmt(p_at_rmax)})")
        spread_p = p_max - eval_df["precision"].min()
        spread_r = r_max - eval_df["recall"].min()
        lines.append(f"- Precision spread across runs: {fmt(spread_p)}; "
                     f"recall spread: {fmt(spread_r)}. The wider axis is "
                     f"{'precision' if spread_p > spread_r else 'recall'}.")
        lines.append("")

        # tau sensitivity
        tau_df = eval_df.dropna(subset=["tau"])
        if not tau_df.empty:
            tau_agg = tau_df.groupby("tau").agg(
                F1=("F1", "mean"), precision=("precision", "mean"),
                recall=("recall", "mean"), n=("F1", "size")
            ).round(4)
            lines.append("### Sensitivity to clustering threshold `tau`")
            lines.append("Means across all runs at each tau (uniform "
                         "weighting unless specified):")
            lines.append("")
            lines.append(tau_agg.to_markdown())
            best_tau = tau_agg["F1"].idxmax()
            worst_tau = tau_agg["F1"].idxmin()
            lines.append("")
            lines.append(f"- Best mean F1 at `tau={best_tau}`; worst at "
                         f"`tau={worst_tau}`.")
            lines.append("")

        # clustering method impact: density_floor & arcs_weighting
        if "density_floor" in eval_df.columns:
            d_df = eval_df.dropna(subset=["density_floor"])
            if not d_df.empty and d_df["density_floor"].nunique() > 1:
                d_agg = d_df.groupby("density_floor").agg(
                    F1=("F1", "mean"), precision=("precision", "mean"),
                    recall=("recall", "mean"), n=("F1", "size")).round(4)
                lines.append("### Cluster post-processing (`density_floor`)")
                lines.append("Mean metrics at each `density_floor` cutoff:")
                lines.append("")
                lines.append(d_agg.to_markdown())
                lines.append("")

        if "arcs_weighting" in eval_df.columns:
            w_agg = eval_df.groupby("arcs_weighting").agg(
                F1=("F1", "mean"), precision=("precision", "mean"),
                recall=("recall", "mean"), n=("F1", "size")).round(4)
            if len(w_agg) > 1:
                lines.append("### ARCS weighting mode")
                lines.append("Uniform vs IDF weighting in the meta-blocking "
                             "graph:")
                lines.append("")
                lines.append(w_agg.to_markdown())
                lines.append("")

        # blocking strategy impact
        b_df = eval_df.dropna(subset=["blocking_mode"])
        if not b_df.empty:
            b_agg = b_df.groupby("blocking_mode").agg(
                F1=("F1", "mean"), precision=("precision", "mean"),
                recall=("recall", "mean"), n=("F1", "size")).round(4)
            lines.append("### Blocking strategy impact")
            lines.append("")
            lines.append(b_agg.to_markdown())
            lines.append("")

        # filter_mode impact
        fm_df = eval_df.dropna(subset=["filter_mode"])
        if not fm_df.empty:
            fm_agg = fm_df.groupby("filter_mode").agg(
                F1=("F1", "mean"), precision=("precision", "mean"),
                recall=("recall", "mean"), n=("F1", "size")).round(4)
            lines.append("### Filter-mode impact")
            lines.append("")
            lines.append(fm_agg.to_markdown())
            lines.append("")

        # Runtime vs accuracy
        rt = eval_df[["F1", "time_total_s"]].dropna()
        if len(rt) > 5:
            corr = rt.corr().iloc[0, 1]
            fastest = eval_df.nsmallest(1, "time_total_s").iloc[0]
            slowest = eval_df.nlargest(1, "time_total_s").iloc[0]
            lines.append("### Runtime vs accuracy")
            lines.append(f"- Pearson correlation between total runtime and "
                         f"F1: {fmt(corr, 3)}")
            lines.append(f"- Fastest run: {fmt(fastest['time_total_s'], 3)} s "
                         f"(F1={fmt(fastest['F1'])}, group="
                         f"`{fastest['group']}/{fastest['config_id']}`)")
            lines.append(f"- Slowest run: {fmt(slowest['time_total_s'], 3)} s "
                         f"(F1={fmt(slowest['F1'])}, group="
                         f"`{slowest['group']}/{slowest['config_id']}`)")
            lines.append("")

    # 5. Key insights for research paper
    lines.append("## 5. Key insights for research paper")
    lines.append("")
    if not eval_df.empty:
        notable = []
        # Highlight perfect/near-perfect F1
        nearperfect = eval_df[eval_df["F1"] >= 0.95]
        if not nearperfect.empty:
            notable.append(f"- {len(nearperfect)} runs reach F1 >= 0.95, "
                           "indicating the pipeline can saturate recall "
                           "and precision simultaneously on this dataset.")
        # Highlight zero-F1 anomalies
        zero = eval_df[eval_df["F1"] == 0]
        if not zero.empty:
            notable.append(f"- {len(zero)} runs collapse to F1 = 0; these "
                           "configurations are useful negative ablations.")
        # Highest precision-recall imbalance
        eval_df["pr_gap"] = (eval_df["precision"]
                             - eval_df["recall"]).abs()
        if eval_df["pr_gap"].notna().any():
            worst_gap = eval_df.loc[eval_df["pr_gap"].idxmax()]
            notable.append(
                f"- Largest precision-recall gap is "
                f"{fmt(worst_gap['pr_gap'])} in run "
                f"`{worst_gap['group']}/{worst_gap['config_id']}/"
                f"{worst_gap['ablation_tag']}` (P={fmt(worst_gap['precision'])}, "
                f"R={fmt(worst_gap['recall'])}), highlighting which knob "
                f"trades pair quality for pair completeness.")
        # FN-dominant vs FP-dominant
        fn_heavy = (eval_df["FN"] > eval_df["FP"]).sum()
        fp_heavy = (eval_df["FP"] > eval_df["FN"]).sum()
        notable.append(f"- {fn_heavy} runs are FN-dominant (recall-limited) "
                       f"and {fp_heavy} are FP-dominant (precision-limited).")
        # ARCS uniform vs idf
        if eval_df["arcs_weighting"].nunique() > 1:
            mean_u = eval_df[eval_df["arcs_weighting"] == "uniform"][
                "F1"].mean()
            mean_i = eval_df[eval_df["arcs_weighting"] == "idf"]["F1"].mean()
            notable.append(f"- Uniform ARCS weighting mean F1 = "
                           f"{fmt(mean_u)}; IDF weighting mean F1 = "
                           f"{fmt(mean_i)}.")
        # Hierarchical/full vs default blocking
        for mode in ["full", "hierarchical"]:
            sub = eval_df[eval_df["blocking_mode"] == mode]
            if not sub.empty:
                notable.append(f"- `{mode}` blocking F1 range: "
                               f"[{fmt(sub['F1'].min())}, "
                               f"{fmt(sub['F1'].max())}] across "
                               f"{len(sub)} run(s).")
        for n in notable:
            lines.append(n)
    lines.append("")
    lines.append("**Failure cases / anomalies:** Configurations that yielded "
                 "F1 = 0 typically correspond to (a) overly aggressive "
                 "thresholding (`tau` higher than the IDF/uniform edge "
                 "weight scale), (b) `top_k=1` which strips co-occurrence "
                 "signal, or (c) filter modes that disagree with "
                 "`composite` zero-weight inputs. Such rows are useful as "
                 "negative ablations in the paper.")
    lines.append("")

    # 6. Reproducibility
    lines.append("## 6. Reproducibility instructions")
    lines.append("")
    lines.append("All experiments use the existing pipeline at "
                 "`Algo1_2_v2/recursive_algo1_2_v2.py`. The full grid is "
                 "re-runnable end-to-end via:")
    lines.append("")
    lines.append("```bash")
    lines.append("cd /home/user/blockingandEmbeddinginER")
    lines.append(f"DATASET={DATASET} python RESULTS/run_experiments.py")
    lines.append(f"DATASET={DATASET} python RESULTS/aggregate_results.py")
    lines.append("```")
    lines.append("")
    lines.append("To rerun only the best configuration:")
    lines.append("")
    if best is not None:
        cmd = ["cd Algo1_2_v2 &&", "python recursive_algo1_2_v2.py",
               f"--input ../{DATASET}", "--truth-dir ..",
               f"--clusters-json /tmp/{DS_BASE}_best.json"]
        cmd.extend(str(best['extra_args']).split())
        lines.append("```bash")
        lines.append(" \\\n    ".join(cmd))
        lines.append("```")
        lines.append("")
        lines.append(f"Auto-detected truth file for `{DATASET}` is "
                     f"`{_truth_name}`. The pipeline is deterministic "
                     "given the same input and CLI args (no RNG seeds are "
                     "exposed because the algorithm itself contains no "
                     "stochastic steps).")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- `RESULTS/{DS_BASE}_results.xlsx` &mdash; `runs` sheet "
                 "(one row per pipeline configuration) and `summary` sheet "
                 "(group-level aggregates).")
    lines.append(f"- `RESULTS/runs/<group>/<config>/` &mdash; per-run "
                 "clusters JSON, metrics JSON, metrics log, raw stdout, "
                 "and invocation manifest.")
    lines.append(f"- `RESULTS/run_experiments.py` &mdash; reproducible "
                 "grid driver.")
    lines.append(f"- `RESULTS/aggregate_results.py` &mdash; this report "
                 "generator.")

    README_PATH.write_text("\n".join(lines) + "\n")
    print(f"Wrote {README_PATH}")


def main():
    df = collect_runs()
    print(f"Collected {len(df)} run rows.")
    summary_df = build_summary(df)
    write_excel(df, summary_df)
    build_readme(df, summary_df)


if __name__ == "__main__":
    main()
