"""Aggregate metrics + pretty-print the run summary.

The blocking algorithm itself is in :mod:`blocking`; this module only consumes
its output (the list of :class:`Block`) plus the original record count and a
runtime, and produces both a dict and a printable report.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Iterable, List

from .blocking import Block

logger = logging.getLogger(__name__)


@dataclass
class BlockingMetrics:
    """Summary statistics for one blocking run."""

    total_records: int
    num_blocks: int
    avg_block_size: float
    largest_block: int
    smallest_block: int
    reduction_ratio: float    # 1 - (candidate pairs / all pairs)
    candidate_pairs: int
    runtime_seconds: float
    max_depth_reached: int

    def to_dict(self) -> dict:
        return asdict(self)


def _pair_count(size: int) -> int:
    """Number of unordered pairs in a block of given size."""
    if size < 2:
        return 0
    return size * (size - 1) // 2


def compute_metrics(
    blocks: Iterable[Block],
    total_records: int,
    runtime_seconds: float,
    max_depth_reached: int,
) -> BlockingMetrics:
    """Crunch numbers from blocks + runtime into a :class:`BlockingMetrics`."""
    block_list: List[Block] = list(blocks)
    num_blocks = len(block_list)
    sizes = [b.size for b in block_list]

    total_pairs = _pair_count(total_records)
    candidate_pairs = sum(_pair_count(s) for s in sizes)
    reduction = 1.0 - (candidate_pairs / total_pairs) if total_pairs > 0 else 0.0

    return BlockingMetrics(
        total_records=total_records,
        num_blocks=num_blocks,
        avg_block_size=(sum(sizes) / num_blocks) if num_blocks else 0.0,
        largest_block=max(sizes) if sizes else 0,
        smallest_block=min(sizes) if sizes else 0,
        reduction_ratio=reduction,
        candidate_pairs=candidate_pairs,
        runtime_seconds=runtime_seconds,
        max_depth_reached=max_depth_reached,
    )


def print_metrics(metrics: BlockingMetrics) -> None:
    """Pretty single-screen summary."""
    print("\n" + "=" * 60)
    print("BLOCKING METRICS")
    print("=" * 60)
    print(f"Total records       : {metrics.total_records}")
    print(f"Number of blocks    : {metrics.num_blocks}")
    print(f"Avg block size      : {metrics.avg_block_size:.2f}")
    print(f"Largest block       : {metrics.largest_block}")
    print(f"Smallest block      : {metrics.smallest_block}")
    print(f"Candidate pairs     : {metrics.candidate_pairs}")
    print(f"Reduction ratio     : {metrics.reduction_ratio:.6f}")
    print(f"Runtime (s)         : {metrics.runtime_seconds:.4f}")
    print(f"Max depth reached   : {metrics.max_depth_reached}")
    print("=" * 60)
