"""
Recursive LSH with Word Signatures — main orchestrator.

Pipeline:
  Phase 0  -> token frequencies + data-quality variations
  Phase 1  -> token-to-hash-key mapping + per-record hash-key sets
  Phase 2  -> initial blocks (optionally MinHash-LSH bucketed)
  Phase 3  -> recursive refinement of each initial block

Run as a script to process the bundled S12PX.txt sample:

    python recursive_lsh.py [path/to/input.csv]
"""

import argparse
import csv
import os
import sys
import time

import build_refDict
from phase_0 import run_phase_0
from phase_1 import run_phase_1
from phase_2 import run_phase_2
from phase_3 import run_phase_3


def run_pipeline(refDict,
                 max_frequency=60,
                 variation_method="fuzzy",
                 similarity_threshold=85,
                 manual_map=None,
                 use_lsh=False,
                 num_perm=128,
                 lsh_threshold=0.5,
                 max_depth=3,
                 min_bucket_size=2):
    """Run all four phases and return their outputs with timing."""
    timing = {}

    t0 = time.time()
    cleaned_refDict, tokenFreqDict, variations_dict = run_phase_0(
        refDict,
        max_frequency=max_frequency,
        method=variation_method,
        similarity_threshold=similarity_threshold,
        manual_map=manual_map,
    )
    timing["Phase 0"] = time.time() - t0

    t0 = time.time()
    token_hash_mapping, hash_to_tokens, hash_key_records = run_phase_1(
        cleaned_refDict, variations_dict
    )
    timing["Phase 1"] = time.time() - t0

    t0 = time.time()
    blocks_by_key, blocks_by_key_set, candidate_pairs = run_phase_2(
        hash_key_records,
        use_lsh=use_lsh,
        num_perm=num_perm,
        lsh_threshold=lsh_threshold,
    )
    timing["Phase 2"] = time.time() - t0

    t0 = time.time()
    final_blocks = run_phase_3(
        blocks_by_key_set, hash_key_records,
        max_depth=max_depth,
        min_bucket_size=min_bucket_size,
    )
    timing["Phase 3"] = time.time() - t0

    return {
        "cleaned_refDict":     cleaned_refDict,
        "tokenFreqDict":       tokenFreqDict,
        "variations_dict":     variations_dict,
        "token_hash_mapping":  token_hash_mapping,
        "hash_to_tokens":      hash_to_tokens,
        "hash_key_records":    hash_key_records,
        "blocks_by_key":       blocks_by_key,
        "blocks_by_key_set":   blocks_by_key_set,
        "candidate_pairs":     candidate_pairs,
        "final_blocks":        final_blocks,
        "timing":              timing,
    }


def export_blocks_to_excel(final_blocks, refDict, filename="recursive_lsh_results.xlsx"):
    """Write the final blocks to an .xlsx workbook (requires openpyxl)."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Final Blocks"
    ws.append(["Block Label", "Record ID", "Tokens"])

    for label, refIDs in final_blocks.items():
        label_str = " ".join(label) if isinstance(label, tuple) else str(label)
        for refID in refIDs:
            tokens = refDict.get(refID, [])
            ws.append([label_str, refID, ", ".join(tokens)])

    wb.save(filename)
    print(f"Saved final blocks to: {filename}")


def export_blocks_to_csv(final_blocks, refDict, filename="recursive_lsh_results.csv"):
    """Write the final blocks to a CSV file (no extra dependencies)."""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Block Label", "Record ID", "Tokens"])
        for label, refIDs in final_blocks.items():
            label_str = " ".join(label) if isinstance(label, tuple) else str(label)
            for refID in refIDs:
                tokens = refDict.get(refID, [])
                writer.writerow([label_str, refID, ", ".join(tokens)])
    print(f"Saved final blocks to: {filename}")


def _parse_args(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")

    parser = argparse.ArgumentParser(
        description="Run the recursive LSH blocking pipeline on a CSV-style file."
    )
    parser.add_argument(
        "input", nargs="?", default=default_input,
        help=f"Path to the input file (default: {default_input}).",
    )
    parser.add_argument(
        "--delimiter", default=",",
        help="Field delimiter for the input file (default: ',').",
    )
    parser.add_argument(
        "--max-frequency", type=int, default=6,
        help="Phase 0: drop tokens whose document frequency exceeds this (default: 6).",
    )
    parser.add_argument(
        "--variation-method", choices=["fuzzy", "phonetic", "manual"],
        default="fuzzy",
        help="Phase 0 variation method (default: fuzzy).",
    )
    parser.add_argument(
        "--similarity-threshold", type=int, default=85,
        help="Phase 0 fuzzy-match similarity threshold 0-100 (default: 85).",
    )
    parser.add_argument(
        "--use-lsh", action="store_true",
        help="Phase 2: use MinHash-LSH bucketing (requires datasketch).",
    )
    parser.add_argument(
        "--num-perm", type=int, default=128,
        help="Phase 2 LSH MinHash permutations (default: 128).",
    )
    parser.add_argument(
        "--lsh-threshold", type=float, default=0.5,
        help="Phase 2 LSH bucketing threshold (default: 0.5).",
    )
    parser.add_argument(
        "--max-depth", type=int, default=3,
        help="Phase 3 recursion depth limit (default: 3).",
    )
    parser.add_argument(
        "--min-bucket-size", type=int, default=2,
        help="Phase 3: stop refining blocks at or below this size (default: 2).",
    )
    parser.add_argument(
        "--export-xlsx", default=None,
        help="Optional path to write final blocks as .xlsx (requires openpyxl).",
    )
    parser.add_argument(
        "--no-export", action="store_true",
        help="Skip writing the default <input>_results.xlsx file.",
    )
    parser.add_argument(
        "--visualize-html", default=None,
        help="Path to write the interactive HTML visualization "
             "(default: <input>_clusters.html).",
    )
    parser.add_argument(
        "--no-visualize", action="store_true",
        help="Skip generating the HTML visualization.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    overall_start = time.time()
    args = _parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    load_start = time.time()
    refDict = build_refDict.tokenizeInput(args.input, delimiter=args.delimiter)
    load_time = time.time() - load_start
    print(f"Loaded {len(refDict)} records from {args.input} ({load_time:.3f}s)")

    results = run_pipeline(
        refDict,
        max_frequency=args.max_frequency,
        variation_method=args.variation_method,
        similarity_threshold=args.similarity_threshold,
        use_lsh=args.use_lsh,
        num_perm=args.num_perm,
        lsh_threshold=args.lsh_threshold,
        max_depth=args.max_depth,
        min_bucket_size=args.min_bucket_size,
    )

    print(f"\nFinal blocks: {len(results['final_blocks'])}")
    print(f"Candidate pairs: {len(results['candidate_pairs'])}")

    print("\n=== Timing Breakdown ===")
    timing = results["timing"]
    for phase, elapsed in timing.items():
        print(f"{phase}: {elapsed:.3f}s")

    pipeline_time = sum(timing.values())
    export_time = 0
    if not args.no_export:
        out_path = args.export_xlsx
        if out_path is None:
            base, _ = os.path.splitext(os.path.basename(args.input))
            out_path = os.path.join(
                os.path.dirname(os.path.abspath(args.input)),
                f"{base}_results.xlsx",
            )
        export_start = time.time()
        try:
            export_blocks_to_excel(
                results["final_blocks"],
                results["cleaned_refDict"],
                out_path,
            )
        except ImportError:
            csv_path = os.path.splitext(out_path)[0] + ".csv"
            print(f"openpyxl not available; falling back to CSV: {csv_path}")
            export_blocks_to_csv(
                results["final_blocks"],
                results["cleaned_refDict"],
                csv_path,
            )
        export_time = time.time() - export_start
        print(f"Export: {export_time:.3f}s")

    viz_time = 0
    if not args.no_visualize:
        viz_path = args.visualize_html
        if viz_path is None:
            base, _ = os.path.splitext(os.path.basename(args.input))
            viz_path = os.path.join(
                os.path.dirname(os.path.abspath(args.input)),
                f"{base}_clusters.html",
            )
        viz_start = time.time()
        try:
            from visualize import build_visualization
            build_visualization(
                results["cleaned_refDict"],
                results["final_blocks"],
                viz_path,
            )
        except Exception as e:
            print(f"Visualization failed: {e}", file=sys.stderr)
        viz_time = time.time() - viz_start
        print(f"Visualization: {viz_time:.3f}s")

    overall_time = time.time() - overall_start
    print(f"\nTotal time: {overall_time:.3f}s (load: {load_time:.3f}s + "
          f"pipeline: {pipeline_time:.3f}s + export: {export_time:.3f}s + "
          f"viz: {viz_time:.3f}s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
