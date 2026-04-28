"""MinHash helpers built on top of :mod:`datasketch`.

Step 4 of the algorithm: turn each token's q-gram set into a deterministic
MinHash signature, then collapse that signature to a string block key.

The wrapper exists for two reasons:

* `datasketch.MinHash` re-seeds itself per instance from a user-provided seed,
  so we centralize that here to guarantee reproducibility across runs.
* We cache signatures by token so a token that appears 1,000 times in the
  dataset is hashed exactly once.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

try:  # pragma: no cover - import guard
    from datasketch import MinHash
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "datasketch is required. Install with `pip install datasketch`."
    ) from exc

logger = logging.getLogger(__name__)


def _stable_hashfunc(data: bytes) -> int:
    """SHA1-based 32-bit hash. Independent of Python's PYTHONHASHSEED."""
    return int.from_bytes(hashlib.sha1(data).digest()[:4], "big")


class MinHasher:
    """Reproducible MinHash signature generator with per-token caching."""

    def __init__(self, num_perm: int = 64, seed: int = 42) -> None:
        if num_perm <= 0:
            raise ValueError("num_perm must be >= 1")
        self.num_perm = num_perm
        self.seed = seed
        # token -> (signature tuple, block-key string)
        self._cache: Dict[Tuple[str, int], Tuple[Tuple[int, ...], str]] = {}

    # ------------------------------------------------------------------ core
    def _signature(self, qgram_list: Sequence[str]) -> Tuple[int, ...]:
        """Build a MinHash signature for one q-gram set."""
        mh = MinHash(num_perm=self.num_perm, seed=self.seed, hashfunc=_stable_hashfunc)
        for gram in qgram_list:
            mh.update(gram.encode("utf-8"))
        return tuple(int(x) for x in mh.hashvalues)

    @staticmethod
    def signature_to_key(signature: Sequence[int]) -> str:
        """Deterministic short key for grouping (full sig hashed → 16 hex)."""
        arr = np.asarray(signature, dtype=np.uint64).tobytes()
        digest = hashlib.blake2b(arr, digest_size=8).hexdigest()
        return f"MH_{digest}"

    # ---------------------------------------------------------------- public
    def hash_token(self, token: str, qgram_list: Sequence[str]) -> Tuple[Tuple[int, ...], str]:
        """Return (signature, block_key) for one token, with caching."""
        cache_key = (token, len(qgram_list))
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        if not qgram_list:
            empty: Tuple[int, ...] = tuple()
            self._cache[cache_key] = (empty, "MH_EMPTY")
            return self._cache[cache_key]
        sig = self._signature(qgram_list)
        key = self.signature_to_key(sig)
        self._cache[cache_key] = (sig, key)
        return sig, key

    def hash_many(
        self,
        token_to_qgrams: Dict[str, Sequence[str]],
    ) -> Dict[str, str]:
        """Bulk-hash a {token: qgrams} dict and return {token: block_key}."""
        out: Dict[str, str] = {}
        for tok, grams in token_to_qgrams.items():
            _, key = self.hash_token(tok, grams)
            out[tok] = key
        logger.debug("MinHashed %d unique tokens", len(out))
        return out


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    """Plain Jaccard similarity on string sets — used for in-block scoring."""
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# --- Optional embeddings hook ------------------------------------------------
# Intentional placeholder for a future drop-in similarity module. Keep the
# signature simple so callers can swap in sentence-transformers, fastText,
# etc. without touching the blocker.
def embed_tokens(tokens: List[str]) -> List[float]:  # pragma: no cover - stub
    """Future hook for vector embeddings. Currently raises NotImplementedError."""
    raise NotImplementedError(
        "Embedding-based similarity not implemented. Plug in your model here."
    )
