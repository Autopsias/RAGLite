"""
Adaptive table extraction package for diverse financial table structures.

This package provides robust, pattern-adaptive table extraction that handles:
1. Multi-header tables (Entity-Metric-Period combinations)
2. Standard pivot tables (various layouts)
3. Transposed tables (metrics as row labels)
4. Single-header tables

Main API:
- extract_table_data_adaptive: Async extraction with layout detection
- classify_header: Classify header cells as TEMPORAL, ENTITY, or METRIC
- detect_table_layout: Detect table layout pattern

Enums:
- HeaderType: Classification of header content
- TableLayout: Detected table layout pattern
"""

from .classification import (
    HeaderType,
    TableLayout,
    classify_header,
    detect_table_layout,
)
from .core import extract_table_data_adaptive

__all__ = [
    # Main API
    "extract_table_data_adaptive",
    # Classification
    "HeaderType",
    "TableLayout",
    "classify_header",
    "detect_table_layout",
]
