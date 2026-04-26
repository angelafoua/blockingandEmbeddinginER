"""
Advanced visualizations for recursive LSH results.

Generates:
  1. Summary statistics (text)
  2. Block size histogram (text-based)
  3. JSON export (for downstream tools)
"""

import json
import os
from collections import Counter


def export_stats_txt(final_blocks, refDict, filename="recursive_lsh_stats.txt"):
    """Write summary statistics to a text file."""
    block_sizes = [len(refs) for refs in final_blocks.values()]

    with open(filename, "w", encoding="utf-8") as f:
        f.write("=== Recursive LSH Blocking Statistics ===\n\n")

        f.write(f"Total blocks: {len(final_blocks)}\n")
        f.write(f"Total records: {len(refDict)}\n")
        f.write(f"Total tokens: {sum(len(tokens) for tokens in refDict.values())}\n\n")

        f.write("Block Size Distribution:\n")
        f.write(f"  Min: {min(block_sizes)}\n")
        f.write(f"  Max: {max(block_sizes)}\n")
        f.write(f"  Median: {sorted(block_sizes)[len(block_sizes)//2]}\n")
        f.write(f"  Mean: {sum(block_sizes) / len(block_sizes):.2f}\n\n")

        size_counts = Counter(block_sizes)
        f.write("Block Size Frequency:\n")
        for size in sorted(size_counts.keys())[:20]:  # Top 20 sizes
            count = size_counts[size]
            pct = 100 * count / len(final_blocks)
            bar = "█" * min(40, count // 2)
            f.write(f"  Size {size:3d}: {count:5d} blocks ({pct:5.1f}%) {bar}\n")

        if len(size_counts) > 20:
            f.write(f"  ... and {len(size_counts) - 20} more sizes\n")

        f.write("\n")
        singleton_blocks = sum(1 for s in block_sizes if s == 1)
        f.write(f"Singleton blocks (size=1): {singleton_blocks} ({100*singleton_blocks/len(final_blocks):.1f}%)\n")
        f.write(f"Multi-record blocks (size≥2): {len(final_blocks) - singleton_blocks}\n")
        f.write(f"  (potential duplicates: {sum(1 for s in block_sizes if s >= 2)} blocks)\n")

    print(f"Saved statistics to: {filename}")


def export_json(final_blocks, refDict, tokenFreqDict, filename="recursive_lsh_data.json"):
    """Export all data as JSON for custom analysis."""
    data = {
        "metadata": {
            "total_blocks": len(final_blocks),
            "total_records": len(refDict),
            "total_tokens": len(tokenFreqDict),
        },
        "records": {
            refID: {
                "tokens": tokens,
                "token_count": len(tokens),
            }
            for refID, tokens in refDict.items()
        },
        "blocks": {
            (label if isinstance(label, str) else " ".join(label)): {
                "refIDs": sorted(refs),
                "size": len(refs),
            }
            for label, refs in final_blocks.items()
        },
        "token_frequencies": tokenFreqDict,
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved JSON export to: {filename}")


def export_blocks_txt(final_blocks, refDict, filename="recursive_lsh_blocks.txt"):
    """Write human-readable block listing to a text file."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write("=== Recursive LSH Blocks ===\n\n")

        sorted_blocks = sorted(
            final_blocks.items(),
            key=lambda x: (-len(x[1]), str(x[0]))
        )

        for block_idx, (label, refIDs) in enumerate(sorted_blocks, 1):
            label_str = label if isinstance(label, str) else " ".join(label)
            f.write(f"Block {block_idx} ({len(refIDs)} records):\n")
            f.write(f"  Label: {label_str}\n")
            f.write(f"  Records:\n")

            for refID in sorted(refIDs):
                tokens = refDict.get(refID, [])
                f.write(f"    {refID}: {' | '.join(tokens)}\n")

            f.write("\n")

    print(f"Saved block listing to: {filename}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python visualize_advanced.py <results.csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not os.path.isfile(csv_path):
        print(f"Error: {csv_path} not found")
        sys.exit(1)

    import csv
    final_blocks = {}
    refDict = {}

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for block_label, refID, tokens_str in reader:
            tokens = [t.strip() for t in tokens_str.split(",") if t.strip()]
            refDict.setdefault(refID, []).extend(tokens)
            final_blocks.setdefault(block_label, []).append(refID)

    tokenFreqDict = {}
    for tokens in refDict.values():
        for t in set(tokens):
            tokenFreqDict[t] = tokenFreqDict.get(t, 0) + 1

    base = os.path.splitext(csv_path)[0]
    export_stats_txt(final_blocks, refDict, f"{base}_stats.txt")
    export_blocks_txt(final_blocks, refDict, f"{base}_blocks.txt")
    export_json(final_blocks, refDict, tokenFreqDict, f"{base}_data.json")
