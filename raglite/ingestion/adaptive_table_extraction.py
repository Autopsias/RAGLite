"""
COMPATIBILITY SHIM - Temporary during refactoring transition.

This module re-exports all functions from the refactored table_extraction package
to maintain backward compatibility with existing imports.

Original file (3109 lines) has been split into 5 focused modules:
- adaptive_table/classification.py (778 lines) - Header & layout classification
- adaptive_table/multi_header.py (143 lines) - Multi-header extraction
- adaptive_table/standard_layouts.py (592 lines) - Standard pivot extraction
- adaptive_table/unit_inference.py (1074 lines) - Unit extraction & inference
- adaptive_table/core.py (648 lines) - Main API & helpers

TODO: Remove this shim after updating all imports to use adaptive_table package directly.
"""

# Re-export all public APIs for backward compatibility
from .adaptive_table import (  # noqa: F401
    HeaderType,
    TableLayout,
    classify_header,
    detect_table_layout,
    extract_table_data_adaptive,
)

# Re-export internal functions needed by tests
from .adaptive_table.standard_layouts import (  # noqa: F401
    _extract_transposed_entity_cols_metric_row_labels,
)

__all__ = [
    "HeaderType",
    "TableLayout",
    "classify_header",
    "detect_table_layout",
    "extract_table_data_adaptive",
    "_extract_transposed_entity_cols_metric_row_labels",
]
