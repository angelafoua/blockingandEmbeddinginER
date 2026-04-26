"""
Interactive matplotlib visualization of the recursive-LSH final blocks.

Each cluster is drawn as a translucent circle whose area scales with the
number of member records. Inside the circle, individual records are placed
in a sunflower pattern. Hovering over a record dot pops up its full token
list, refID, and cluster label.

Usage:
    python visualize_matplotlib.py [input.csv]
        [--min-cluster-size N] [--save out.png]
"""

import argparse
import math
import os
import sys

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

import build_refDict
from recursive_lsh import run_pipeline


def sunflower(n, radius):
    """Return ``n`` points evenly distributed inside a disc of given radius."""
    if n <= 0:
        return []
    if n == 1:
        return [(0.0, 0.0)]
    phi2 = ((1 + math.sqrt(5)) / 2) ** 2
    pts = []
    for i in range(n):
        r = radius * math.sqrt((i + 0.5) / n)
        theta = 2 * math.pi * i / phi2
        pts.append((r * math.cos(theta), r * math.sin(theta)))
    return pts


def pack_circles(radii):
    """Greedy packing: for each circle (largest first), grow a search radius
    out from the origin and place the circle at the first non-overlapping
    spot found. Returns centers in input order.
    """
    n = len(radii)
    if n == 0:
        return []

    order = sorted(range(n), key=lambda i: -radii[i])
    centers = [None] * n

    placed_x = [0.0]
    placed_y = [0.0]
    placed_r = [radii[order[0]]]
    centers[order[0]] = (0.0, 0.0)

    for idx in order[1:]:
        r = radii[idx]
        px = np.asarray(placed_x)
        py = np.asarray(placed_y)
        pr = np.asarray(placed_r)
        min_d2 = (pr + r) ** 2

        step = max(min(pr.min(), r) * 0.4, 0.2)
        chosen = None
        d = 0.0
        for _ in range(2000):
            if d == 0.0:
                angles = np.array([0.0])
            else:
                n_angles = max(16, int(2 * math.pi * d / step))
                angles = np.linspace(0.0, 2 * math.pi, n_angles, endpoint=False)
            xs = d * np.cos(angles)
            ys = d * np.sin(angles)
            dx = xs[:, None] - px[None, :]
            dy = ys[:, None] - py[None, :]
            ok = np.all(dx * dx + dy * dy >= min_d2[None, :] - 1e-9, axis=1)
            valid = np.flatnonzero(ok)
            if valid.size:
                k = int(valid[0])
                chosen = (float(xs[k]), float(ys[k]))
                break
            d += step

        if chosen is None:
            chosen = (d, 0.0)
        centers[idx] = chosen
        placed_x.append(chosen[0])
        placed_y.append(chosen[1])
        placed_r.append(r)

    return centers


def build_layout(refDict, final_blocks, min_cluster_size):
    """Compute per-record (x, y) positions and cluster geometry.

    Returns:
        clusters:  list of dicts {label, center, radius, refIDs}
        points:    list of dicts {x, y, refID, tokens, cluster_label}
    """
    clusters_raw = []
    for label, refIDs in final_blocks.items():
        ids = list(refIDs)
        if len(ids) < min_cluster_size:
            continue
        label_str = " ".join(label) if isinstance(label, tuple) else str(label)
        clusters_raw.append((label_str, ids))

    # Cluster radius scales with sqrt(count) so area ~ count.
    # 0.6 unit per record gives roomy interiors without huge circles.
    radii = [0.6 * math.sqrt(len(ids) + 1) + 0.4 for _, ids in clusters_raw]
    centers = pack_circles(radii)

    clusters = []
    points = []
    for (label, ids), center, radius in zip(clusters_raw, centers, radii):
        clusters.append({
            "label": label,
            "center": center,
            "radius": radius,
            "size": len(ids),
        })
        # Leave a margin so dots don't sit on the cluster boundary.
        inner_r = max(radius - 0.25, radius * 0.7)
        for (dx, dy), rid in zip(sunflower(len(ids), inner_r), ids):
            tokens = refDict.get(rid, [])
            points.append({
                "x": center[0] + dx,
                "y": center[1] + dy,
                "refID": rid,
                "tokens": tokens,
                "cluster_label": label,
            })

    return clusters, points


def render(clusters, points, total_clusters, total_records,
           min_cluster_size, save_path=None):
    fig, ax = plt.subplots(figsize=(13, 9))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    if not points:
        ax.text(0.5, 0.5,
                f"No clusters with >= {min_cluster_size} members",
                ha="center", va="center", color="#e2e8f0",
                transform=ax.transAxes, fontsize=14)
        plt.show()
        return

    cmap = plt.colormaps["cool"]
    max_size = max(c["size"] for c in clusters)

    for c in clusters:
        color = cmap(min(c["size"] / max(max_size, 1), 1.0))
        circle = mpatches.Circle(
            c["center"], c["radius"],
            facecolor=color, alpha=0.25,
            edgecolor="#60a5fa", linewidth=1.0,
        )
        ax.add_patch(circle)
        if c["radius"] > 0.9:
            ax.text(c["center"][0],
                    c["center"][1] + c["radius"] - 0.2,
                    str(c["size"]),
                    ha="center", va="top",
                    color="#cbd5e1", fontsize=8,
                    family="monospace")

    xs = np.array([p["x"] for p in points])
    ys = np.array([p["y"] for p in points])

    scatter = ax.scatter(
        xs, ys,
        s=22, c="#f1f5f9",
        edgecolors="#1e293b", linewidths=0.5,
        zorder=3, picker=False,
    )

    pad = 1.0
    ax.set_xlim(xs.min() - pad, xs.max() + pad)
    ax.set_ylim(ys.min() - pad, ys.max() + pad)

    ax.set_title(
        f"Recursive LSH Clusters  ·  "
        f"showing {len(clusters)}/{total_clusters} clusters  ·  "
        f"{len(points)}/{total_records} records  ·  min size {min_cluster_size}",
        color="#f1f5f9", fontsize=12, pad=14,
    )

    if save_path:
        plt.savefig(save_path, dpi=150, facecolor=fig.get_facecolor())
        print(f"Saved static visualization to: {save_path}")
        plt.close(fig)
        return

    annot = ax.annotate(
        "", xy=(0, 0), xytext=(16, 16),
        textcoords="offset points",
        ha="left", va="bottom",
        fontsize=9, family="monospace",
        color="#0f172a",
        bbox=dict(boxstyle="round,pad=0.5",
                  fc="#fde68a", ec="#f59e0b", lw=1.0),
        arrowprops=dict(arrowstyle="->", color="#f59e0b", lw=1.0),
        zorder=10,
    )
    annot.set_visible(False)

    highlight = ax.scatter(
        [], [], s=80, facecolors="none",
        edgecolors="#fbbf24", linewidths=2.0, zorder=4,
    )

    def format_text(p):
        toks = ", ".join(p["tokens"]) if p["tokens"] else "(no tokens)"
        # Wrap long token lists for readability.
        max_chars = 60
        if len(toks) > max_chars:
            wrapped = []
            line = ""
            for tok in p["tokens"]:
                piece = (", " if line else "") + tok
                if len(line) + len(piece) > max_chars:
                    wrapped.append(line)
                    line = tok
                else:
                    line += piece
            if line:
                wrapped.append(line)
            toks = "\n  ".join(wrapped)
        return (f"{p['refID']}\n"
                f"  {toks}\n"
                f"cluster: {p['cluster_label']}")

    def on_move(event):
        if event.inaxes != ax:
            if annot.get_visible():
                annot.set_visible(False)
                highlight.set_offsets(np.empty((0, 2)))
                fig.canvas.draw_idle()
            return
        cont, info = scatter.contains(event)
        if cont:
            i = info["ind"][0]
            p = points[i]
            annot.xy = (p["x"], p["y"])
            annot.set_text(format_text(p))
            annot.set_visible(True)
            highlight.set_offsets([[p["x"], p["y"]]])
            fig.canvas.draw_idle()
        elif annot.get_visible():
            annot.set_visible(False)
            highlight.set_offsets(np.empty((0, 2)))
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", on_move)

    print("Hover over any dot to see its full record. Close the window to exit.")
    plt.show()


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Interactive matplotlib visualization of recursive-LSH clusters."
    )
    parser.add_argument("input", nargs="?", default=default_input)
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--max-frequency", type=int, default=6)
    parser.add_argument("--variation-method",
                        choices=["fuzzy", "phonetic", "manual", "data_quality"],
                        default="fuzzy")
    parser.add_argument("--similarity-threshold", type=int, default=85)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--min-bucket-size", type=int, default=2)
    parser.add_argument("--min-cluster-size", type=int, default=2,
                        help="Only show clusters with at least this many records.")
    parser.add_argument("--save", default=None,
                        help="Optional path to save a static PNG instead of "
                             "opening the interactive window.")
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    refDict = build_refDict.tokenizeInput(args.input, delimiter=args.delimiter)
    print(f"Loaded {len(refDict)} records from {args.input}")

    results = run_pipeline(
        refDict,
        max_frequency=args.max_frequency,
        variation_method=args.variation_method,
        similarity_threshold=args.similarity_threshold,
        max_depth=args.max_depth,
        min_bucket_size=args.min_bucket_size,
    )

    final_blocks = results["final_blocks"]
    cleaned = results["cleaned_refDict"]
    total_clusters = len(final_blocks)
    total_records = sum(len(ids) for ids in final_blocks.values())

    clusters, points = build_layout(
        cleaned, final_blocks, args.min_cluster_size
    )
    print(f"Visualizing {len(clusters)} clusters, {len(points)} records "
          f"(min cluster size = {args.min_cluster_size})")

    render(clusters, points,
           total_clusters=total_clusters,
           total_records=total_records,
           min_cluster_size=args.min_cluster_size,
           save_path=args.save)
    return 0


if __name__ == "__main__":
    sys.exit(main())
