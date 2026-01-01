"""
Header classification and table layout detection for adaptive table extraction.

This module provides:
1. Header cell classification (TEMPORAL, ENTITY, METRIC)
2. Table layout pattern detection
3. Table orientation detection

Used as the base module for all other table extraction modules.

FACADE PATTERN: This file re-exports all functions to maintain backward compatibility.
Actual implementations are in domain-specific modules:
- header.py: Header classification
- layout.py: Layout pattern detection
- orientation.py: Orientation detection
"""

# Re-export enums from header module
from .header import HeaderType, classify_header

# Re-export enums and functions from layout module
from .layout import TableLayout, detect_table_layout

# Re-export functions from orientation module
from .orientation import (
    _analyze_column,
    _detect_orientation,
    _detect_table_orientation,
    _is_numeric_value,
)

# Public API
__all__ = [
    # Enums
    "HeaderType",
    "TableLayout",
    # Public functions
    "classify_header",
    "detect_table_layout",
    # Internal functions (prefixed with _)
    "_detect_orientation",
    "_is_numeric_value",
    "_analyze_column",
    "_detect_table_orientation",
]
