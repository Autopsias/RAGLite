"""Async batch processing for high-performance LLM unit inference.

This module provides async batch processing with rate limiting and connection pooling
to achieve 41x speedup over synchronous sequential inference (62 min → 1.5 min).

Implements:
- Milestone 1: Async concurrent processing (10x speedup)
- Milestone 2: Batch inference (4x additional speedup)
- Story 5.0.6 AC3: Cross-document unit cache (30% additional API reduction)
"""

from ._legacy import (
    MISTRAL_SEMAPHORE,
    _apply_context_aware_unit_inference_async,
    _infer_unit_from_context_async,
    _infer_units_batch_async,
)

__all__ = [
    "MISTRAL_SEMAPHORE",
    "_infer_unit_from_context_async",
    "_infer_units_batch_async",
    "_apply_context_aware_unit_inference_async",
]
