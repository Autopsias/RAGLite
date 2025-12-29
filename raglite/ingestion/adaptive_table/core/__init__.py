"""
Core package for adaptive table extraction.

This package provides the main API and helper functions for adaptive table extraction,
refactored from the original monolithic core.py file (903 LOC).

Public API:
- extract_table_data_adaptive: Main async extraction API

Internal modules:
- api: Main API functions
- context: Context helpers and table context management
- fallback: Fallback extraction logic
- processing: Table processing utilities
"""

from __future__ import annotations

# Public exports
from .api import extract_table_data_adaptive
from .context import extract_page_context, get_table_caption, get_table_markdown
from .fallback import extract_fallback
from .processing import (
    extract_year,
    infer_entity_from_context,
    infer_metric_from_context,
    validate_entity,
    validate_metric,
)

__all__ = [
    # Main API
    "extract_table_data_adaptive",
    # Context extraction
    "extract_page_context",
    "get_table_caption",
    "get_table_markdown",
    # Fallback extraction
    "extract_fallback",
    # Processing utilities
    "extract_year",
    "infer_entity_from_context",
    "infer_metric_from_context",
    "validate_entity",
    "validate_metric",
]
