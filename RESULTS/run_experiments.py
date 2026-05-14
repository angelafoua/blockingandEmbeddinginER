"""Run the full algo1_2_v2 experiment suite for a single dataset.

Each configuration is executed by invoking the existing pipeline as a
subprocess. The pipeline writes one `.metrics.json` per (merge,purge)
config beside the clusters JSON, which we collect afterwards.
"""

import itertools
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ALGO = REPO / "Algo1_2_v2"
PIPELINE = "recursive_algo1_2_v2.py"

DATASET = os.environ.get("DATASET", "S1G.txt")
INPUT_REL = f"../{DATASET}"
TRUTH_DIR = ".."

RUNS_DIR = REPO / "RESULTS" / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _slug(d):
    parts = []
    for k, v in sorted(d.items()):
        sv = str(v).replace(".", "p").replace("-", "n").replace("/", "_")
        parts.append(f"{k}={sv}")
    return ",".join(parts)


def run_one(group, config_id, extra_args, label):
    """Execute one pipeline invocation. Returns the run directory."""
    run_dir = RUNS_DIR / group / config_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    clusters_json = run_dir / "clusters.json"
    log_path = run_dir / "run.log"

    cmd = [sys.executable, PIPELINE,
           "--input", INPUT_REL,
           "--truth-dir", TRUTH_DIR,
           "--clusters-json", str(clusters_json)] + extra_args
    t0 = time.time()
    with open(log_path, "w") as logf:
        logf.write(f"# group={group} config_id={config_id}\n")
        logf.write(f"# label={label}\n")
        logf.write(f"# cmd={' '.join(cmd)}\n\n")
        logf.flush()
        proc = subprocess.run(cmd, cwd=str(ALGO),
                              stdout=logf, stderr=subprocess.STDOUT)
    elapsed = time.time() - t0

    meta = {
        "group": group,
        "config_id": config_id,
        "label": label,
        "cmd": cmd,
        "extra_args": extra_args,
        "returncode": proc.returncode,
        "wallclock_s": elapsed,
    }
    with open(run_dir / "invocation.json", "w") as f:
        json.dump(meta, f, indent=2)
    return run_dir, proc.returncode


def build_grid():
    """Curated parameter grid for the algo1_2_v2 suite.

    Groups cover all major knobs documented in the pipeline CLI:
      A: merge/purge 4-way ablation (built-in baseline)
      B: filter_mode x merge/purge
      C: composite filter weight combinations
      D: similarity threshold tau sweep
      E: top_k sweep
      F: ARCS weighting (uniform vs idf) x tau
      G: blocking mode (default/full/hierarchical)
      H: max_recursion_depth sweep
      I: density-floor sweep
      J: arcs-pair-sim-weight sweep
      K: min-block-size sweep
    """
    grid = []

    # A: baseline 4-way merge/purge ablation (no extra args).
    grid.append(("A_merge_purge", "default", [], "baseline 4-way"))

    # B: filter_mode x merge/purge (each invocation = 4 m/p configs).
    for fm in ["size", "specificity", "keylen", "composite"]:
        extra = ["--filter-mode", fm]
        if fm == "composite":
            extra += ["--filter-weight-size", "1.0",
                      "--filter-weight-shared", "1.0",
                      "--filter-weight-tokenlen", "1.0"]
        grid.append(("B_filter_mode", f"fm={fm}", extra, f"filter_mode={fm}"))

    # C: composite weight combos (single-run via --no-merge to keep light;
    # we instead use default merge/purge so all 4 configs emitted).
    comp_combos = [
        ("all_equal",      1.0, 1.0, 1.0),
        ("size_only",      1.0, 0.0, 0.0),
        ("shared_only",    0.0, 1.0, 0.0),
        ("tokenlen_only",  0.0, 0.0, 1.0),
        ("size_shared",    1.0, 1.0, 0.0),
        ("size_tokenlen",  1.0, 0.0, 1.0),
        ("shared_tokenlen",0.0, 1.0, 1.0),
    ]
    for name, ws, wsh, wt in comp_combos:
        extra = ["--filter-mode", "composite",
                 "--filter-weight-size", str(ws),
                 "--filter-weight-shared", str(wsh),
                 "--filter-weight-tokenlen", str(wt)]
        grid.append(("C_composite", f"w={name}", extra, f"composite/{name}"))

    # D: tau sweep
    for tau in [0.05, 0.1, 0.2, 0.3, 0.4, 0.5]:
        extra = ["--tau", str(tau)]
        grid.append(("D_tau", f"tau={tau}", extra, f"tau={tau}"))

    # E: top_k sweep
    for k in [1, 2, 3, 5, 10]:
        extra = ["--top-k", str(k)]
        grid.append(("E_top_k", f"k={k}", extra, f"top_k={k}"))

    # F: ARCS weighting (idf) at two thresholds; uniform already covered.
    for tau in [0.2, 0.4, 1.0]:
        extra = ["--arcs-weighting", "idf", "--tau", str(tau)]
        grid.append(("F_arcs_idf", f"tau={tau}", extra, f"arcs=idf,tau={tau}"))

    # G: alternate blocking modes (single-config runs).
    grid.append(("G_blocking", "full",
                 ["--full-blocking", "--max-block-pair-cost", "100000"],
                 "full blocking"))
    grid.append(("G_blocking", "hierarchical",
                 ["--hierarchical-blocking"],
                 "hierarchical blocking"))

    # H: max_recursion_depth sweep
    for d in [1, 2, 3, 5, 7, 10]:
        extra = ["--max-recursion-depth", str(d)]
        grid.append(("H_recursion_depth", f"d={d}", extra, f"max_depth={d}"))

    # I: density-floor sweep (cluster splitting)
    for df in [0.0, 0.3, 0.5, 0.7]:
        extra = ["--density-floor", str(df)]
        grid.append(("I_density_floor", f"df={df}", extra,
                     f"density_floor={df}"))

    # J: arcs-pair-sim-weight sweep (per-pair similarity modulation)
    for psw in [0.0, 0.25, 0.5, 0.75, 1.0]:
        extra = ["--arcs-pair-sim-weight", str(psw)]
        grid.append(("J_pair_sim_w", f"psw={psw}", extra,
                     f"pair_sim_weight={psw}"))

    # K: min-block-size sweep
    for mbs in [2, 3, 4, 5]:
        extra = ["--min-block-size", str(mbs)]
        grid.append(("K_min_block_size", f"mbs={mbs}", extra,
                     f"min_block_size={mbs}"))

    return grid


def main():
    grid = build_grid()
    print(f"Total invocations: {len(grid)}", flush=True)
    failed = []
    for i, (group, cid, extra, label) in enumerate(grid, 1):
        print(f"[{i}/{len(grid)}] {group}/{cid}  ({label})", flush=True)
        run_dir, rc = run_one(group, cid, extra, label)
        if rc != 0:
            failed.append((group, cid, rc))
            print(f"   FAILED rc={rc}", flush=True)
    print(f"\nDone. Failed: {len(failed)}")
    for g, c, rc in failed:
        print(f"  {g}/{c} rc={rc}")


if __name__ == "__main__":
    main()
