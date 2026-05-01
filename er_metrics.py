"""Pair-based ER metrics (precision / recall / F1) for blocking algorithms.

This is the blocking-aware analogue of DWM99_ERmetrics.  DWM99 evaluates a
clustering (each refID -> exactly one clusterID), but blocking algorithms
produce overlapping blocks where a refID can appear in multiple blocks.
We therefore evaluate at the *pair* level:

    L  = number of distinct candidate pairs produced by the blocks
    E  = number of true equivalent pairs in the truth set
    TP = candidate pairs that are also truth pairs

    Precision (Pair Quality)      = TP / L
    Recall    (Pair Completeness) = TP / E
    F1                            = 2*P*R / (P+R)

Truth file format (matches DWM truthABCpoorDQ.txt / truthABCgoodDQ.txt):

    header_line
    refID,truthID
    refID,truthID
    ...

Usage::

    import er_metrics
    truth_file = er_metrics.detect_truth_file("S12PX.txt", truth_dir=".")
    er_metrics.compute_metrics(final_blocks, truth_file)
"""

import os
from itertools import combinations


def load_truth(truth_file_path):
    """Load truth CSV (skip header). Return dict {refID: truthID}."""
    truth = {}
    with open(truth_file_path, "r", encoding="utf-8") as f:
        next(f, None)  # header
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 2:
                continue
            ref_id = parts[0].strip()
            truth_id = parts[1].strip()
            truth[ref_id] = truth_id
    return truth


def detect_truth_file(input_file_path, truth_dir="."):
    """Pick truthABCpoorDQ.txt or truthABCgoodDQ.txt based on input filename.

    DWM convention: filenames containing 'P' (e.g. S12PX) use the poor-DQ
    truth set; filenames containing 'G' (e.g. S1G) use the good-DQ truth
    set.  Returns the path or None if no match.
    """
    base = os.path.splitext(os.path.basename(input_file_path))[0].upper()
    poor = os.path.join(truth_dir, "truthABCpoorDQ.txt")
    good = os.path.join(truth_dir, "truthABCgoodDQ.txt")
    if "P" in base:
        return poor
    if "G" in base:
        return good
    return None


def _extract_ref_ids(block_value):
    """A block may be a dict {refID: ...}, a set, or a list of refIDs."""
    if isinstance(block_value, dict):
        return list(block_value.keys())
    return list(block_value)


def compute_metrics(blocks, truth_file_path, verbose=True):
    """Compute pair-based precision, recall, F1.

    Parameters
    ----------
    blocks : dict
        {block_key: iterable of refIDs}.  Inner value can be a dict (refIDs
        as keys), a set, or a list.
    truth_file_path : str
        Path to the truth CSV file.
    verbose : bool
        Print metrics to stdout.

    Returns
    -------
    dict with keys: TP, E, L, FP, FN, precision, recall, f1.
    """
    truth = load_truth(truth_file_path)

    # ---- Build the deduplicated set of candidate pairs from blocks ----
    candidate_pairs = set()
    for _key, value in blocks.items():
        ref_ids = _extract_ref_ids(value)
        # Stable ordering so (a, b) and (b, a) collapse to one entry.
        ref_ids = sorted(set(ref_ids))
        for a, b in combinations(ref_ids, 2):
            candidate_pairs.add((a, b))

    L = len(candidate_pairs)

    # ---- Build the set of true pairs from the truth clustering ----
    truth_clusters = {}
    for ref_id, t_id in truth.items():
        truth_clusters.setdefault(t_id, []).append(ref_id)

    true_pairs = set()
    for members in truth_clusters.values():
        if len(members) < 2:
            continue
        for a, b in combinations(sorted(members), 2):
            true_pairs.add((a, b))

    E = len(true_pairs)

    # ---- TP = intersection ----
    TP = len(candidate_pairs & true_pairs)
    FP = L - TP
    FN = E - TP

    precision = TP / L if L > 0 else 1.0
    recall = TP / E if E > 0 else 1.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    metrics = {
        "TP": TP,
        "E": E,
        "L": L,
        "FP": FP,
        "FN": FN,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }

    if verbose:
        print("\n>>> ER Metrics (pair-based)")
        print(f"  Truth file          = {truth_file_path}")
        print(f"  Records in truth    = {len(truth)}")
        print(f"  True Pairs (TP)     = {TP}")
        print(f"  Expected Pairs (E)  = {E}")
        print(f"  Linked Pairs (L)    = {L}")
        print(f"  False Positives     = {FP}")
        print(f"  False Negatives     = {FN}")
        print(f"  Precision           = {metrics['precision']}")
        print(f"  Recall              = {metrics['recall']}")
        print(f"  F1-measure          = {metrics['f1']}")

    return metrics
