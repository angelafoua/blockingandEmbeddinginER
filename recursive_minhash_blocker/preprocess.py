"""Text preprocessing for the Recursive MinHash Blocker.

The functions here implement Steps 1-3 of the algorithm:

    1. Extract tokens (concat selected columns, lowercase, split).
    2. Clean tokens (replace non-word chars, collapse whitespace).
    3. Standardize tokens via a configurable abbreviation map.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Iterable, List, Sequence

import pandas as pd

logger = logging.getLogger(__name__)

# Anything that is not a unicode word character becomes a space. Digits stay.
_NON_WORD_RE = re.compile(r"[^\w]+", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")


def _safe_str(value: object) -> str:
    """Coerce arbitrary cell values (including NaN/None) to a clean string."""
    if value is None:
        return ""
    # pandas / numpy NaN check without importing numpy here.
    if isinstance(value, float) and value != value:
        return ""
    return str(value)


def clean_text(text: str) -> str:
    """Lowercase + non-word→space + whitespace squeeze.

    Used both for the joined record string and for individual tokens so the
    cleanup stays consistent across the pipeline.
    """
    text = text.lower()
    text = _NON_WORD_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def standardize_token(token: str, normalization_map: Dict[str, str]) -> str:
    """Apply the abbreviation map to a single token. No-op if no entry."""
    return normalization_map.get(token, token)


def tokenize_record(
    row: pd.Series,
    columns: Sequence[str],
    normalization_map: Dict[str, str],
) -> List[str]:
    """Return the cleaned, standardized token list for one record.

    Missing values are silently treated as empty strings; empty tokens are
    dropped so they never reach the q-gram / MinHash stage.
    """
    parts = [_safe_str(row[c]) for c in columns if c in row.index]
    joined = " ".join(parts)
    cleaned = clean_text(joined)
    if not cleaned:
        return []

    tokens: List[str] = []
    for raw in cleaned.split(" "):
        if not raw:
            continue
        tokens.append(standardize_token(raw, normalization_map))
    return tokens


def tokenize_dataframe(
    df: pd.DataFrame,
    columns: Sequence[str],
    normalization_map: Dict[str, str],
) -> Dict[object, List[str]]:
    """Tokenize every row, keyed by the DataFrame index.

    Returning a plain dict keeps downstream code free of pandas dependencies
    and is faster than repeatedly indexing a Series.
    """
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise KeyError(f"Blocking columns missing from input: {missing}")

    out: Dict[object, List[str]] = {}
    for idx, row in df.iterrows():
        out[idx] = tokenize_record(row, columns, normalization_map)
    logger.debug("Tokenized %d records over columns=%s", len(out), list(columns))
    return out


def qgrams(token: str, q: int) -> List[str]:
    """Character q-grams for a single token.

    Tokens shorter than q yield the token itself as a single q-gram; this is a
    common convention that keeps short tokens (initials, "co", etc.) usable.
    """
    if q <= 0:
        raise ValueError("q must be >= 1")
    if len(token) < q:
        return [token] if token else []
    return [token[i : i + q] for i in range(len(token) - q + 1)]


def qgrams_for_tokens(tokens: Iterable[str], q: int) -> Dict[str, List[str]]:
    """Map every distinct token to its q-gram list (cached per token)."""
    cache: Dict[str, List[str]] = {}
    for tok in tokens:
        if tok not in cache:
            cache[tok] = qgrams(tok, q)
    return cache
