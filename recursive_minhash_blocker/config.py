"""Configuration objects for the Recursive MinHash Blocker.

All tunables live here so the algorithm stays library-agnostic and easy to
override from the CLI or from user code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Default address / company normalization map. Editable by the caller via
# BlockerConfig.normalization_map.
DEFAULT_NORMALIZATION_MAP: Dict[str, str] = {
    "st": "street",
    "str": "street",
    "rd": "road",
    "ave": "avenue",
    "av": "avenue",
    "blvd": "boulevard",
    "boul": "boulevard",
    "ln": "lane",
    "dr": "drive",
    "ct": "court",
    "pl": "place",
    "sq": "square",
    "hwy": "highway",
    "pkwy": "parkway",
    "apt": "apartment",
    "ste": "suite",
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "co": "company",
    "inc": "incorporated",
    "corp": "corporation",
    "llc": "limitedliabilitycompany",
    "ltd": "limited",
    "intl": "international",
    "mfg": "manufacturing",
    "&": "and",
}


@dataclass
class BlockerConfig:
    """Holds every parameter that influences blocking behavior."""

    # ---- Input shape -----------------------------------------------------
    id_column: str = "RecID"
    blocking_columns: List[str] = field(default_factory=lambda: ["Name", "Address"])

    # ---- Tokenization & normalization -----------------------------------
    normalization_map: Dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_NORMALIZATION_MAP)
    )

    # ---- Q-grams and MinHash --------------------------------------------
    q: int = 2
    num_perm: int = 64
    minhash_seed: int = 42  # Reproducibility.

    # ---- Stop-word policy -----------------------------------------------
    auto_stopword_top_percentile: float = 0.005  # Top 0.5% by frequency.
    manual_stopwords: List[str] = field(default_factory=list)

    # ---- Blocking-key thresholds ----------------------------------------
    alpha: int = 2          # min frequency for a useful blocking signature
    beta: int = 1000        # max frequency for a useful blocking signature

    # ---- Recursion -------------------------------------------------------
    max_depth: int = 5
    min_block_size: int = 2

    # ---- Multi-block membership -----------------------------------------
    # Max blocking keys to use *per recursion level* (top-N least-frequent).
    # Increase for higher recall, decrease for fewer candidate pairs.
    max_keys_per_level: int = 3

    # ---- Optional similarity scoring ------------------------------------
    score_jaccard: bool = False

    # ---- Global token correction (DWM25-style) --------------------------
    # When True, applies global_replace() after tokenization and before
    # q-gram / MinHash computation.  Corrects low-frequency tokens that are
    # within edit-distance 1 of a high-frequency token.
    run_global_correction: bool = False
    gc_word_list_path: Optional[str] = None   # path to DWM_WordList.txt (optional)
    gc_min_freq_std: int = 10    # min frequency to be a standard (correct) token
    gc_min_len_std: int = 3      # min token length to be a standard token
    gc_max_freq_err: int = 3     # max frequency to be an error-token candidate

    # ---- Output ----------------------------------------------------------
    output_csv: Optional[str] = None
    print_report: bool = True

    # ---- Logging ---------------------------------------------------------
    log_level: str = "INFO"

    def update_normalization(self, mapping: Dict[str, str]) -> None:
        """Merge user-provided abbreviations into the active map."""
        self.normalization_map.update({k.lower(): v.lower() for k, v in mapping.items()})
