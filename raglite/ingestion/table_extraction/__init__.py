"""Table extraction and SQL structuring for financial documents.

Story 2.13 AC1: Extract tables from Docling output and parse into structured SQL format.

This facade preserves backward compatibility for all imports.
"""

from __future__ import annotations

# Re-export adaptive table extraction for test mocking compatibility
from raglite.ingestion.adaptive_table_extraction import extract_table_data_adaptive

# Re-export main class from extraction module
from .extraction import TableExtractor

# Re-export parsing utilities for any direct usage
from .parsing import (
    build_column_mapping,
    extract_caption,
    extract_year,
    get_row_period,
    parse_markdown_row,
    parse_table_structure,
    parse_value_unit,
)

__all__ = [
    # Main extractor class
    "TableExtractor",
    # Parsing functions (for backward compatibility and testing)
    "parse_table_structure",
    "build_column_mapping",
    "get_row_period",
    "extract_caption",
    "parse_markdown_row",
    "parse_value_unit",
    "extract_year",
    # Adaptive table extraction (for test mocking)
    "extract_table_data_adaptive",
]
