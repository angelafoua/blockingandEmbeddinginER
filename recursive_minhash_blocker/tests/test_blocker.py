"""Unit tests for q-gram generation, MinHash determinism, and blocking logic.

Run with:
    python -m unittest recursive_minhash_blocker.tests.test_blocker
"""

from __future__ import annotations

import unittest
from typing import List

import pandas as pd

from recursive_minhash_blocker.blocking import RecursiveMinHashBlocker
from recursive_minhash_blocker.config import BlockerConfig
from recursive_minhash_blocker.minhash_utils import MinHasher, jaccard
from recursive_minhash_blocker.preprocess import (
    clean_text,
    qgrams,
    standardize_token,
    tokenize_record,
)


class TestQGrams(unittest.TestCase):
    def test_basic_qgrams_q2(self) -> None:
        self.assertEqual(qgrams("smith", 2), ["sm", "mi", "it", "th"])

    def test_qgrams_q3(self) -> None:
        self.assertEqual(qgrams("smith", 3), ["smi", "mit", "ith"])

    def test_token_shorter_than_q_returned_whole(self) -> None:
        self.assertEqual(qgrams("ab", 3), ["ab"])
        self.assertEqual(qgrams("a", 2), ["a"])

    def test_empty_token(self) -> None:
        self.assertEqual(qgrams("", 2), [])

    def test_invalid_q_raises(self) -> None:
        with self.assertRaises(ValueError):
            qgrams("smith", 0)


class TestPreprocess(unittest.TestCase):
    def test_clean_text(self) -> None:
        self.assertEqual(clean_text("  Hello, World!  "), "hello world")
        self.assertEqual(clean_text("12 Main St."), "12 main st")
        self.assertEqual(clean_text(""), "")

    def test_standardize_token(self) -> None:
        m = {"st": "street", "rd": "road"}
        self.assertEqual(standardize_token("st", m), "street")
        self.assertEqual(standardize_token("xyz", m), "xyz")

    def test_tokenize_record_handles_nan(self) -> None:
        row = pd.Series({"Name": "John Smith", "Address": float("nan")})
        toks = tokenize_record(row, ["Name", "Address"], {})
        self.assertEqual(toks, ["john", "smith"])

    def test_tokenize_record_applies_normalization(self) -> None:
        row = pd.Series({"Name": "ACME Co", "Address": "1 Main St"})
        toks = tokenize_record(
            row, ["Name", "Address"],
            {"co": "company", "st": "street"},
        )
        self.assertIn("company", toks)
        self.assertIn("street", toks)
        self.assertNotIn("co", toks)
        self.assertNotIn("st", toks)


class TestMinHasher(unittest.TestCase):
    def test_signature_deterministic(self) -> None:
        h1 = MinHasher(num_perm=32, seed=42)
        h2 = MinHasher(num_perm=32, seed=42)
        sig1, key1 = h1.hash_token("smith", qgrams("smith", 2))
        sig2, key2 = h2.hash_token("smith", qgrams("smith", 2))
        self.assertEqual(sig1, sig2)
        self.assertEqual(key1, key2)
        self.assertTrue(key1.startswith("MH_"))

    def test_different_tokens_yield_different_keys(self) -> None:
        h = MinHasher(num_perm=32, seed=42)
        _, k1 = h.hash_token("smith", qgrams("smith", 2))
        _, k2 = h.hash_token("jones", qgrams("jones", 2))
        self.assertNotEqual(k1, k2)

    def test_empty_qgrams_yield_sentinel_key(self) -> None:
        h = MinHasher(num_perm=32, seed=42)
        sig, key = h.hash_token("", [])
        self.assertEqual(key, "MH_EMPTY")
        self.assertEqual(sig, ())

    def test_jaccard_basic(self) -> None:
        self.assertEqual(jaccard(["a", "b"], ["a", "b"]), 1.0)
        self.assertEqual(jaccard(["a", "b"], ["c", "d"]), 0.0)
        self.assertAlmostEqual(jaccard(["a", "b"], ["b", "c"]), 1 / 3)
        self.assertEqual(jaccard([], []), 1.0)


class TestBlockingLogic(unittest.TestCase):
    """End-to-end: build a tiny dataset with planted duplicates, expect grouping."""

    def _dataset(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"RecID": 1, "Name": "John Smith",  "Address": "12 Main Street"},
            {"RecID": 2, "Name": "Jon Smith",   "Address": "12 Main St"},
            {"RecID": 3, "Name": "J Smith",     "Address": "12 Main Street"},
            {"RecID": 4, "Name": "Mary Jones",  "Address": "9 Oak Avenue"},
            {"RecID": 5, "Name": "Mary Jones",  "Address": "9 Oak Ave"},
            {"RecID": 6, "Name": "Robert Lee",  "Address": "55 Pine Road"},
            {"RecID": 7, "Name": "Bob Lee",     "Address": "55 Pine Rd"},
        ])

    def test_duplicates_share_a_block(self) -> None:
        cfg = BlockerConfig(
            blocking_columns=["Name", "Address"],
            alpha=2, beta=10, q=2, num_perm=64,
            max_depth=2, min_block_size=2,
            auto_stopword_top_percentile=0.0,
            # Use all valid signatures so the test verifies recall, not the
            # top-N heuristic.
            max_keys_per_level=100,
        )
        blocker = RecursiveMinHashBlocker(cfg).fit(self._dataset())
        # Smith duplicates (1, 2, 3) should land in at least one common block.
        smith_blocks = [
            set(b.member_record_ids) for b in blocker.blocks
            if {1, 2, 3}.issubset(set(b.member_record_ids))
        ]
        self.assertTrue(smith_blocks, "Expected a block containing all three Smiths")

        jones_blocks = [
            set(b.member_record_ids) for b in blocker.blocks
            if {4, 5}.issubset(set(b.member_record_ids))
        ]
        self.assertTrue(jones_blocks, "Expected a block containing both Joneses")

    def test_blocking_key_history_prevents_reuse(self) -> None:
        cfg = BlockerConfig(
            blocking_columns=["Name", "Address"],
            alpha=2, beta=100, q=2, num_perm=64,
            max_depth=4, min_block_size=2,
            auto_stopword_top_percentile=0.0,
        )
        blocker = RecursiveMinHashBlocker(cfg).fit(self._dataset())
        # For each block, no ancestor's blocking key should appear again.
        by_id = {b.block_id: b for b in blocker.blocks}
        for b in blocker.blocks:
            ancestor_keys: List[str] = []
            cur = b
            while cur.parent_block is not None and cur.parent_block in by_id:
                cur = by_id[cur.parent_block]
                if cur.blocking_key is not None:
                    ancestor_keys.append(cur.blocking_key)
            self.assertNotIn(b.blocking_key, ancestor_keys,
                             f"Block {b.block_id} reused ancestor key")

    def test_handles_missing_id_column(self) -> None:
        df = pd.DataFrame([{"Name": "x", "Address": "y"}])
        cfg = BlockerConfig()
        with self.assertRaises(KeyError):
            RecursiveMinHashBlocker(cfg).fit(df)

    def test_jaccard_scoring_populates_scores(self) -> None:
        cfg = BlockerConfig(
            blocking_columns=["Name", "Address"],
            alpha=2, beta=10, q=2, num_perm=64,
            max_depth=2, min_block_size=2,
            auto_stopword_top_percentile=0.0,
            score_jaccard=True,
        )
        blocker = RecursiveMinHashBlocker(cfg).fit(self._dataset())
        self.assertTrue(
            any(b.similarity_scores for b in blocker.blocks),
            "Expected at least one block with Jaccard scores populated",
        )

    def test_export_csv_writes_rows(self) -> None:
        import os
        import tempfile

        cfg = BlockerConfig(
            blocking_columns=["Name", "Address"],
            alpha=2, beta=10, max_depth=2, min_block_size=2,
            auto_stopword_top_percentile=0.0,
        )
        blocker = RecursiveMinHashBlocker(cfg).fit(self._dataset())
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "blocks.csv")
            blocker.export_csv(out)
            df = pd.read_csv(out)
            self.assertGreater(len(df), 0)
            for col in ("block_id", "depth", "blocking_key", "RecID"):
                self.assertIn(col, df.columns)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
