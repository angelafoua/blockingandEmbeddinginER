"""Recursive MinHash Blocker package.

Public API:
    RecursiveMinHashBlocker - the main class
    BlockerConfig            - knobs / hyper-parameters
    compute_metrics          - post-run summary
"""

from .blocking import Block, RecursiveMinHashBlocker
from .config import BlockerConfig
from .metrics import BlockingMetrics, compute_metrics, print_metrics

__all__ = [
    "Block",
    "RecursiveMinHashBlocker",
    "BlockerConfig",
    "BlockingMetrics",
    "compute_metrics",
    "print_metrics",
]

__version__ = "0.1.0"
