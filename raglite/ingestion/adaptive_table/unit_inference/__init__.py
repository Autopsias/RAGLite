"""
Unit extraction and inference for table data.

This package provides:
1. Unit pattern extraction from table structures
2. Statistical unit detection
3. LLM-based context-aware unit inference
4. Async batch processing for performance

Handles orientation-aware unit detection for transposed, normal, and junk-column tables.
"""

from __future__ import annotations

from .async_batch import (
    MISTRAL_SEMAPHORE,
    _apply_context_aware_unit_inference_async,
    _infer_unit_from_context_async,
    _infer_units_batch_async,
)
from .extraction import (
    _detect_unit_column_statistical,
    _extract_units_entity_column_junk,
    _extract_units_normal,
)
from .llm_inference import _apply_context_aware_unit_inference, _infer_unit_from_context
from .parsers import _parse_value_unit
from .rules import UNIT_RULES, infer_unit_from_rules

__all__ = [
    # Constants
    "MISTRAL_SEMAPHORE",
    # Rules
    "UNIT_RULES",
    "infer_unit_from_rules",
    # Extraction
    "_extract_units_normal",
    "_extract_units_entity_column_junk",
    "_detect_unit_column_statistical",
    # Parsers
    "_parse_value_unit",
    # LLM Inference (sync)
    "_infer_unit_from_context",
    "_apply_context_aware_unit_inference",
    # Async Batch
    "_infer_unit_from_context_async",
    "_infer_units_batch_async",
    "_apply_context_aware_unit_inference_async",
]
