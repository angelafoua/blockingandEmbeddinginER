"""
Generate an interactive HTML visualization of the final blocks.

Each cluster is rendered as a circle whose area scales with member count.
Hovering over any record shows its full token list. A side panel lists
clusters and supports filtering by minimum size and free-text search.

Usage:
    python visualize.py [input.csv] [--min-cluster-size N] [--out file.html]

The visualization is a self-contained HTML file that loads D3.js from a CDN.
Open it in any modern browser.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

import build_refDict
from recursive_lsh import run_pipeline


D3_URL = "https://d3js.org/d3.v7.min.js"
_HERE = os.path.dirname(os.path.abspath(__file__))
D3_CACHE = os.path.join(_HERE, "_d3.v7.min.js")


def _load_d3_script_tag():
    """Return a <script> tag with D3 inlined, fetching it on first use.

    Falls back to the CDN <script src=...> tag if both the cache and the
    network fetch are unavailable. Inlining matters for environments where
    the browser can't reach the CDN (Codespaces port-forward CSP, offline
    file:// usage, restricted networks).
    """
    if not os.path.isfile(D3_CACHE) or os.path.getsize(D3_CACHE) < 100_000:
        try:
            print(f"Fetching D3.js from {D3_URL} (one-time, cached locally)...")
            urllib.request.urlretrieve(D3_URL, D3_CACHE)
        except (urllib.error.URLError, OSError) as e:
            print(f"Could not fetch D3 ({e}); HTML will load it from the CDN.")
            return f'<script src="{D3_URL}"></script>'
    try:
        with open(D3_CACHE, "r", encoding="utf-8") as f:
            return f"<script>\n{f.read()}\n</script>"
    except OSError:
        return f'<script src="{D3_URL}"></script>'


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Recursive LSH Clusters</title>
__D3_SCRIPT__
<style>
  :root, [data-theme="dark"] {
    --bg: #0f172a;
    --panel: #1e293b;
    --border: #334155;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --heading: #f1f5f9;
    --input-bg: #0f172a;
    --input-border: #475569;
    --hover-bg: #334155;
    --selected-bg: #1e40af;
    --selected-border: #3b82f6;
    --accent: #60a5fa;
    --highlight: #fbbf24;
    --highlight-stroke: #f59e0b;
    --dot: #f1f5f9;
    --dot-stroke: #1e293b;
    --tooltip-bg: #0f172a;
    --label: #cbd5e1;
    --shadow: rgba(0,0,0,0.5);
    --error: #fca5a5;
  }
  [data-theme="light"] {
    --bg: #f8fafc;
    --panel: #ffffff;
    --border: #e2e8f0;
    --text: #1e293b;
    --muted: #64748b;
    --heading: #0f172a;
    --input-bg: #ffffff;
    --input-border: #cbd5e1;
    --hover-bg: #e2e8f0;
    --selected-bg: #dbeafe;
    --selected-border: #2563eb;
    --accent: #2563eb;
    --highlight: #d97706;
    --highlight-stroke: #b45309;
    --dot: #1e293b;
    --dot-stroke: #ffffff;
    --tooltip-bg: #ffffff;
    --label: #334155;
    --shadow: rgba(15,23,42,0.18);
    --error: #b91c1c;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: var(--bg); color: var(--text); height: 100vh; overflow: hidden;
  }
  #app { display: flex; height: 100vh; }
  #sidebar {
    width: 340px; background: var(--panel); border-right: 1px solid var(--border);
    display: flex; flex-direction: column; overflow: hidden;
  }
  #sidebar header {
    padding: 16px; border-bottom: 1px solid var(--border);
  }
  #sidebar header .title-row {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 8px;
  }
  #sidebar h1 { margin: 0; font-size: 18px; color: var(--heading); }
  #sidebar .stats { font-size: 12px; color: var(--muted); }
  #theme-toggle {
    background: transparent; border: 1px solid var(--border); color: var(--text);
    cursor: pointer; padding: 4px 10px; border-radius: 4px; font-size: 11px;
    font-family: inherit; letter-spacing: 0.5px;
  }
  #theme-toggle:hover { background: var(--hover-bg); }
  #controls { padding: 12px 16px; border-bottom: 1px solid var(--border); }
  #controls label {
    display: block; font-size: 12px; color: var(--muted);
    margin-bottom: 4px; margin-top: 8px;
  }
  #controls input {
    width: 100%; padding: 6px 8px; border-radius: 4px;
    border: 1px solid var(--input-border); background: var(--input-bg); color: var(--text);
    font-size: 13px;
  }
  #cluster-list { flex: 1; overflow-y: auto; padding: 8px; }
  .cluster-item {
    padding: 8px 10px; margin-bottom: 4px; border-radius: 4px;
    cursor: pointer; font-size: 13px; border: 1px solid transparent;
  }
  .cluster-item:hover { background: var(--hover-bg); }
  .cluster-item.selected { background: var(--selected-bg); border-color: var(--selected-border); }
  .cluster-item .label { font-family: monospace; font-size: 11px; color: var(--muted); }
  .cluster-item .count { float: right; color: var(--accent); font-weight: bold; }
  #viz { flex: 1; position: relative; overflow: hidden; background: var(--bg); }
  #viz svg { width: 100%; height: 100%; display: block; }
  .cluster-circle {
    fill-opacity: 0.25; stroke: var(--accent); stroke-width: 1;
    cursor: pointer;
  }
  .cluster-circle.selected { fill-opacity: 0.5; stroke: var(--highlight); stroke-width: 2; }
  .cluster-label {
    fill: var(--label); text-anchor: middle; pointer-events: none;
    font-family: monospace; font-size: 10px;
  }
  .record-dot { fill: var(--dot); stroke: var(--dot-stroke); stroke-width: 1; cursor: pointer; }
  .record-dot:hover { fill: var(--highlight); stroke: var(--highlight-stroke); stroke-width: 2; }
  #tooltip {
    position: absolute; pointer-events: none; background: var(--tooltip-bg);
    border: 1px solid var(--accent); border-radius: 6px; padding: 10px 12px;
    max-width: 360px; font-size: 12px; box-shadow: 0 4px 12px var(--shadow);
    opacity: 0; transition: opacity 0.15s;
  }
  #tooltip .rid { color: var(--accent); font-weight: bold; margin-bottom: 4px; }
  #tooltip .tokens { color: var(--text); word-break: break-word; }
  #tooltip .label { color: var(--muted); font-size: 10px; margin-top: 6px; font-family: monospace; }
  #d3-error { color: var(--error); padding: 24px; font-family: monospace; }
</style>
</head>
<body>
<div id="app">
  <aside id="sidebar">
    <header>
      <div class="title-row">
        <h1>Recursive LSH Clusters</h1>
        <button id="theme-toggle" type="button" aria-label="Toggle color theme">Light</button>
      </div>
      <div class="stats" id="stats"></div>
    </header>
    <div id="controls">
      <label>Minimum cluster size</label>
      <input type="number" id="minSize" value="2" min="1">
      <label>Search records / tokens</label>
      <input type="text" id="search" placeholder="e.g. tommy, boston">
    </div>
    <div id="cluster-list"></div>
  </aside>
  <main id="viz">
    <svg></svg>
    <div id="tooltip"></div>
  </main>
</div>

<script>
(function setupTheme() {
  const KEY = "rlsh-theme";
  const btn = document.getElementById("theme-toggle");
  const stored = localStorage.getItem(KEY);
  const prefersLight = window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: light)").matches;
  const initial = stored || (prefersLight ? "light" : "dark");
  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    btn.textContent = theme === "dark" ? "Light" : "Dark";
  }
  apply(initial);
  btn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    localStorage.setItem(KEY, next);
    apply(next);
  });
})();

if (typeof d3 === "undefined") {
  document.querySelector("#viz").innerHTML =
    '<p id="d3-error">' +
    'D3.js failed to load.<br>' +
    'If you are viewing this file via a Codespaces port-forward or another ' +
    'environment that blocks external scripts, regenerate the HTML with ' +
    'an inlined D3 (visualize.py fetches it automatically when it has internet).' +
    '</p>';
  throw new Error("D3.js not loaded");
}
const DATA = __DATA_JSON__;
const records = DATA.records;
const clusters = DATA.clusters;

const svg = d3.select("#viz svg");
const tooltip = d3.select("#tooltip");
let selectedId = null;
let currentNodes = [];

function showTooltip(event, node) {
  const rec = records[node.refID];
  tooltip
    .style("left", (event.offsetX + 14) + "px")
    .style("top", (event.offsetY + 14) + "px")
    .style("opacity", 1)
    .html(
      `<div class="rid">${rec.refID}</div>` +
      `<div class="tokens">${rec.tokens.map(escapeHtml).join(" · ")}</div>` +
      `<div class="label">cluster: ${escapeHtml(node.clusterLabel)}</div>`
    );
}
function hideTooltip() { tooltip.style("opacity", 0); }
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
}

function render() {
  const minSize = +d3.select("#minSize").property("value") || 1;
  const query = d3.select("#search").property("value").trim().toLowerCase();

  let filtered = clusters.filter(c => c.refIDs.length >= minSize);

  if (query) {
    filtered = filtered.filter(c =>
      c.refIDs.some(rid => {
        const rec = records[rid];
        if (!rec) return false;
        if (rec.refID.toLowerCase().includes(query)) return true;
        return rec.tokens.some(t => t.toLowerCase().includes(query));
      })
    );
  }

  d3.select("#stats").text(
    `${clusters.length} total clusters · showing ${filtered.length} · ` +
    `${Object.keys(records).length} records`
  );

  const list = d3.select("#cluster-list").selectAll(".cluster-item").data(filtered, d => d.id);
  list.exit().remove();
  const enter = list.enter().append("div").attr("class", "cluster-item");
  enter.append("span").attr("class", "count");
  enter.append("div").attr("class", "label");
  const merged = enter.merge(list);
  merged.classed("selected", d => d.id === selectedId);
  merged.select(".count").text(d => d.refIDs.length);
  merged.select(".label").text(d => d.label);
  merged.on("click", (e, d) => { selectedId = d.id; render(); });

  drawViz(filtered);
}

function drawViz(filtered) {
  const width = svg.node().clientWidth;
  const height = svg.node().clientHeight;
  svg.selectAll("*").remove();

  const root = d3.hierarchy({ children: filtered.map(c => ({
    cluster: c,
    value: c.refIDs.length,
  })) }).sum(d => d.value || 1);

  const pack = d3.pack().size([width - 20, height - 20]).padding(6);
  pack(root);

  const g = svg.append("g").attr("transform", "translate(10,10)");

  const groups = g.selectAll("g.cluster")
    .data(root.leaves())
    .enter().append("g")
    .attr("class", "cluster")
    .attr("transform", d => `translate(${d.x},${d.y})`);

  groups.append("circle")
    .attr("class", "cluster-circle")
    .classed("selected", d => d.data.cluster.id === selectedId)
    .attr("r", d => d.r)
    .attr("fill", d => d3.interpolateCool(Math.min(d.data.cluster.refIDs.length / 10, 1)))
    .on("click", (e, d) => { selectedId = d.data.cluster.id; render(); });

  groups.filter(d => d.r > 24).append("text")
    .attr("class", "cluster-label")
    .attr("dy", -d => 0)
    .text(d => `${d.data.cluster.refIDs.length}`);

  groups.each(function (d) {
    const cluster = d.data.cluster;
    const r = d.r;
    const dotRadius = Math.max(2, Math.min(5, r / Math.sqrt(cluster.refIDs.length + 1)));
    const positions = sunflower(cluster.refIDs.length, r - dotRadius - 2);
    const sel = d3.select(this);
    sel.selectAll("circle.record-dot")
      .data(cluster.refIDs.map((rid, i) => ({
        refID: rid,
        clusterLabel: cluster.label,
        x: positions[i][0],
        y: positions[i][1],
      })))
      .enter().append("circle")
      .attr("class", "record-dot")
      .attr("cx", n => n.x)
      .attr("cy", n => n.y)
      .attr("r", dotRadius)
      .on("mousemove", (e, n) => showTooltip(e, n))
      .on("mouseleave", hideTooltip);
  });
}

function sunflower(n, radius) {
  const phi = (1 + Math.sqrt(5)) / 2;
  const out = [];
  for (let i = 0; i < n; i++) {
    const r = radius * Math.sqrt((i + 0.5) / n);
    const theta = 2 * Math.PI * i / (phi * phi);
    out.push([r * Math.cos(theta), r * Math.sin(theta)]);
  }
  return out;
}

d3.select("#minSize").on("input", render);
d3.select("#search").on("input", render);
window.addEventListener("resize", render);
render();
</script>
</body>
</html>
"""


def build_visualization(refDict, final_blocks, output_html):
    """Render an interactive HTML visualization to ``output_html``."""
    records = {
        refID: {"refID": refID, "tokens": tokens}
        for refID, tokens in refDict.items()
    }

    clusters = []
    for idx, (label, refIDs) in enumerate(final_blocks.items()):
        label_str = " ".join(label) if isinstance(label, tuple) else str(label)
        clusters.append({
            "id": idx,
            "label": label_str,
            "refIDs": list(refIDs),
        })

    payload = json.dumps({"records": records, "clusters": clusters},
                         ensure_ascii=False)

    html = HTML_TEMPLATE.replace("__D3_SCRIPT__", _load_d3_script_tag())
    html = html.replace("__DATA_JSON__", payload)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Visualization saved to: {output_html}")
    print(f"  open in browser: file://{os.path.abspath(output_html)}")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Generate an interactive HTML cluster visualization."
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
    parser.add_argument("--out", default=None,
                        help="Output HTML path (default: <input>_clusters.html).")
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

    out_path = args.out
    if out_path is None:
        base, _ = os.path.splitext(os.path.basename(args.input))
        out_path = os.path.join(
            os.path.dirname(os.path.abspath(args.input)),
            f"{base}_clusters.html",
        )

    build_visualization(results["cleaned_refDict"], results["final_blocks"], out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
