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

import os
import sys

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
    """Run all four phases and return their outputs."""
    cleaned_refDict, tokenFreqDict, variations_dict = run_phase_0(
        refDict,
        max_frequency=max_frequency,
        method=variation_method,
        similarity_threshold=similarity_threshold,
        manual_map=manual_map,
    )

    token_hash_mapping, hash_to_tokens, hash_key_records = run_phase_1(
        cleaned_refDict, variations_dict
    )

    blocks_by_key, blocks_by_key_set, candidate_pairs = run_phase_2(
        hash_key_records,
        use_lsh=use_lsh,
        num_perm=num_perm,
        lsh_threshold=lsh_threshold,
    )

    final_blocks = run_phase_3(
        blocks_by_key_set, hash_key_records,
        max_depth=max_depth,
        min_bucket_size=min_bucket_size,
    )

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


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(here, "S12PX.txt")
    input_path = sys.argv[1] if len(sys.argv) > 1 else default_input

    refDict = build_refDict.tokenizeInput(input_path)
    print(f"Loaded {len(refDict)} records from {input_path}")

    results = run_pipeline(
        refDict,
        max_frequency=6,
        variation_method="fuzzy",
        similarity_threshold=85,
        use_lsh=False,
        max_depth=3,
        min_bucket_size=2,
    )

    print(f"\nFinal blocks: {len(results['final_blocks'])}")
    print(f"Candidate pairs: {len(results['candidate_pairs'])}")

    try:
        export_blocks_to_excel(
            results["final_blocks"],
            results["cleaned_refDict"],
            os.path.join(here, "recursive_lsh_results.xlsx"),
        )
    except ImportError:
        print("openpyxl not available; skipping Excel export.")
