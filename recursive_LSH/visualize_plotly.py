"""
Interactive Plotly visualization of the recursive-LSH final clusters.

Each cluster is drawn as a translucent circle whose area scales with the
number of member records. Inside the circle, individual records are placed
in a sunflower pattern. Hovering over a record dot shows its full token
list, refID, and cluster label.

Usage:
    python visualize_plotly.py [input.csv]
        [--min-cluster-size N] [--out clusters.html] [--no-show]
"""

import argparse
import math
import os
import sys

import plotly.graph_objects as go

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
    """Row-pack circles into a roughly square area. Sort by radius desc, then
    fill rows whose width is bounded by ``sqrt(total_area) * 1.4``. Each row's
    height equals its largest circle's diameter. O(N), no overlap search.
    Returns centers in input order.
    """
    n = len(radii)
    if n == 0:
        return []

    indexed = sorted(enumerate(radii), key=lambda x: -x[1])
    total_area = sum(math.pi * r * r for _, r in indexed)
    target_w = math.sqrt(total_area) * 1.4

    rows = [[]]
    row_widths = [0.0]
    row_heights = [0.0]
    pad = 0.15

    for idx, r in indexed:
        diam = 2.0 * r + pad
        if row_widths[-1] > 0 and row_widths[-1] + diam > target_w:
            rows.append([])
            row_widths.append(0.0)
            row_heights.append(0.0)
        rows[-1].append((idx, r))
        row_widths[-1] += diam
        row_heights[-1] = max(row_heights[-1], 2.0 * r + pad)

    centers = [None] * n
    y_cursor = 0.0
    for row, row_h in zip(rows, row_heights):
        x_cursor = 0.0
        for idx, r in row:
            centers[idx] = (x_cursor + r, y_cursor - row_h / 2.0)
            x_cursor += 2.0 * r + pad
        y_cursor -= row_h

    return centers


def build_layout(refDict, final_blocks, min_cluster_size):
    """Compute per-record (x, y) positions and cluster geometry."""
    clusters_raw = []
    for label, refIDs in final_blocks.items():
        ids = list(refIDs)
        if len(ids) < min_cluster_size:
            continue
        label_str = " ".join(label) if isinstance(label, tuple) else str(label)
        clusters_raw.append((label_str, ids))

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


def _color_for_size(size, max_size):
    """Map a cluster size to a Plotly 'rgba(...)' color from the Viridis ramp."""
    # Hand-picked stops along the Viridis colormap so we don't pull in numpy/PIL.
    stops = [
        (0.00, (68,   1,  84)),
        (0.25, (59,  82, 139)),
        (0.50, (33, 145, 140)),
        (0.75, (94, 201,  98)),
        (1.00, (253, 231,  37)),
    ]
    t = min(size / max(max_size, 1), 1.0)
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t <= t1:
            f = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            r = int(c0[0] + (c1[0] - c0[0]) * f)
            g = int(c0[1] + (c1[1] - c0[1]) * f)
            b = int(c0[2] + (c1[2] - c0[2]) * f)
            return f"rgba({r},{g},{b},0.35)", f"rgb({r},{g},{b})"
    r, g, b = stops[-1][1]
    return f"rgba({r},{g},{b},0.35)", f"rgb({r},{g},{b})"


def build_figure(clusters, points, total_clusters, total_records,
                 min_cluster_size):
    """Build a Plotly figure with cluster circles + record dots."""
    fig = go.Figure()

    if not clusters:
        fig.add_annotation(
            text=f"No clusters with >= {min_cluster_size} members",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color="#e2e8f0", size=18),
        )
        fig.update_layout(
            paper_bgcolor="#0f172a", plot_bgcolor="#0f172a",
            xaxis=dict(visible=False), yaxis=dict(visible=False),
        )
        return fig

    max_size = max(c["size"] for c in clusters)

    shapes = []
    for c in clusters:
        cx, cy = c["center"]
        r = c["radius"]
        fill, edge = _color_for_size(c["size"], max_size)
        shapes.append(dict(
            type="circle",
            xref="x", yref="y",
            x0=cx - r, y0=cy - r, x1=cx + r, y1=cy + r,
            fillcolor=fill, line=dict(color=edge, width=1.2),
            layer="below",
        ))

    label_xs, label_ys, label_texts = [], [], []
    for c in clusters:
        if c["radius"] > 0.9:
            label_xs.append(c["center"][0])
            label_ys.append(c["center"][1] + c["radius"] - 0.15)
            label_texts.append(str(c["size"]))

    if label_xs:
        fig.add_trace(go.Scatter(
            x=label_xs, y=label_ys,
            mode="text",
            text=label_texts,
            textfont=dict(family="monospace", size=11, color="#cbd5e1"),
            hoverinfo="skip",
            showlegend=False,
        ))

    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    hover = []
    for p in points:
        toks = ", ".join(p["tokens"]) if p["tokens"] else "(no tokens)"
        # Insert <br> every ~60 chars for readability in the hover box.
        if len(toks) > 60:
            wrapped = []
            line = ""
            for tok in p["tokens"]:
                piece = (", " if line else "") + tok
                if len(line) + len(piece) > 60:
                    wrapped.append(line)
                    line = tok
                else:
                    line += piece
            if line:
                wrapped.append(line)
            toks = "<br>  ".join(wrapped)
        hover.append(
            f"<b>{p['refID']}</b><br>"
            f"  {toks}<br>"
            f"<span style='color:#94a3b8'>cluster: {p['cluster_label']}</span>"
        )

    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="markers",
        marker=dict(
            size=8, color="#f1f5f9",
            line=dict(color="#1e293b", width=0.6),
        ),
        hovertext=hover,
        hoverinfo="text",
        showlegend=False,
        name="records",
    ))

    pad = 1.0
    x_min, x_max = min(xs) - pad, max(xs) + pad
    y_min, y_max = min(ys) - pad, max(ys) + pad

    fig.update_layout(
        title=dict(
            text=(f"Recursive LSH Clusters &middot; "
                  f"showing {len(clusters)}/{total_clusters} clusters &middot; "
                  f"{len(points)}/{total_records} records &middot; "
                  f"min size {min_cluster_size}"),
            font=dict(color="#f1f5f9", size=14),
            x=0.5, xanchor="center",
        ),
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        shapes=shapes,
        xaxis=dict(
            range=[x_min, x_max], visible=False,
            scaleanchor="y", scaleratio=1,
        ),
        yaxis=dict(range=[y_min, y_max], visible=False),
        margin=dict(l=20, r=20, t=60, b=20),
        hoverlabel=dict(
            bgcolor="#fde68a", bordercolor="#f59e0b",
            font=dict(family="monospace", size=11, color="#0f172a"),
        ),
    )

    return fig


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Interactive Plotly visualization of recursive-LSH clusters."
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
    parser.add_argument("--out", default=None,
                        help="Path to save the figure as a self-contained HTML "
                             "(default: <input>_clusters_plotly.html).")
    parser.add_argument("--no-show", action="store_true",
                        help="Skip opening the figure in a browser; only write "
                             "the HTML file.")
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

    print(f"Building layout for {len(final_blocks)} clusters "
          f"(min_cluster_size={args.min_cluster_size})...", flush=True)
    clusters, points = build_layout(
        cleaned, final_blocks, args.min_cluster_size
    )
    print(f"Visualizing {len(clusters)} clusters, {len(points)} records",
          flush=True)

    fig = build_figure(
        clusters, points,
        total_clusters=total_clusters,
        total_records=total_records,
        min_cluster_size=args.min_cluster_size,
    )

    out_path = args.out
    if out_path is None:
        base, _ = os.path.splitext(os.path.basename(args.input))
        out_path = os.path.join(
            os.path.dirname(os.path.abspath(args.input)),
            f"{base}_clusters_plotly.html",
        )
    fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
    print(f"Saved Plotly visualization to: {out_path}")
    print(f"  open in browser: file://{os.path.abspath(out_path)}")

    if not args.no_show:
        try:
            fig.show()
        except Exception as e:
            print(f"Could not open figure in browser ({e}); "
                  f"open the HTML file manually.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
