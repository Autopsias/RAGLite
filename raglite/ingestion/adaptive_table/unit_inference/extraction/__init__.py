"""Unit extraction from table structures.

This module provides orientation-aware unit extraction strategies for:
- Normal tables (entities in columns, metrics in rows)
- Type B tables (junk column 0, entities in column 1)
- Statistical unit column detection
"""

from __future__ import annotations

import logging

from .detection import (
    _detect_by_extended_patterns,
    _detect_by_middle_section_concentration,
    _detect_by_statistical_threshold,
    _validate_sample_size,
)
from .strategies import (
    _extract_dedicated_unit_row,
    _extract_from_column_headers,
    _extract_from_headers_with_parens,
    _extract_from_metric_names,
)

logger = logging.getLogger(__name__)

__all__ = [
    # Main functions
    "_extract_units_normal",
    "_extract_units_entity_column_junk",
    "_detect_unit_column_statistical",
    # Detection helpers
    "_validate_sample_size",
    "_detect_by_statistical_threshold",
    "_detect_by_middle_section_concentration",
    "_detect_by_extended_patterns",
    # Strategy helpers
    "_extract_dedicated_unit_row",
    "_extract_from_metric_names",
    "_extract_from_column_headers",
    "_extract_from_headers_with_parens",
]


def _extract_units_normal(table_cells: list, unit_patterns: list[str]) -> dict[int, str]:
    """Extract units from normal table (entities in columns, metrics in rows).

    Strategy priorities for normal tables:
    1. Check for dedicated unit row (usually row 0, 1, or 2)
    2. Extract from row headers/metric names (e.g., "Revenue (EUR)")
    3. Extract from column headers

    Args:
        table_cells: List of table cells
        unit_patterns: List of unit pattern strings to match

    Returns:
        Dictionary mapping row index to unit string for normal tables

    Example:
        Normal table:
        Row 0: Entity    | GROUP   | PORTUGAL | ANGOLA
        Row 1: Unit      | EUR     | EUR      | EUR
        Row 2: Revenue   | 100M    | 50M      | 50M

        Returns: {0: 'EUR', 1: 'EUR', 2: 'EUR'} (from unit row)

        Alternative pattern (metric names with units):
        Row 0: Entity         | GROUP   | PORTUGAL | ANGOLA
        Row 1: Revenue (EUR)  | 100M    | 50M      | 50M

        Returns: {1: 'EUR'} (extracted from metric name)
    """
    # Strategy 1: Check for dedicated unit row (usually row 0, 1, or 2)
    units = _extract_dedicated_unit_row(table_cells, unit_patterns, row_indices=[0, 1, 2])
    if units:
        return units

    # Strategy 2: Extract from row headers (metric names with units in parentheses)
    units = _extract_from_metric_names(table_cells, unit_patterns, header_column=0)
    if units:
        return units

    # Strategy 3: Extract from column headers (if units appear there)
    units = _extract_from_column_headers(table_cells, unit_patterns)

    logger.info(
        "Normal table unit extraction completed",
        extra={
            "units_found": len(units),
            "extraction_strategies": "unit_row,metric_names,column_headers",
        },
    )

    return units


def _extract_units_entity_column_junk(
    table_cells: list, unit_patterns: list[str]
) -> dict[int, str]:
    """Extract units from Type B tables (junk column 0, entities in column 1).

    Structure:
    - Column 0: Numeric junk/indices (14.003, 8.430, 26, etc.)
    - Column 1: Entity names (Portugal, Portugal Cement, etc.)
    - Headers: Metric categories (Total R SUSTAINING, Total D DEVELOPMENT, etc.)

    Strategy:
    1. Check column headers for unit patterns (e.g., "CAPEX (EUR million)")
    2. Check rows 3-5 for dedicated unit row (beyond typical 0-2)
    3. Fallback to cell-level parsing

    Args:
        table_cells: List of table cells
        unit_patterns: List of unit pattern strings

    Returns:
        Dictionary mapping column index to unit string
    """
    units = {}

    # Strategy 1: Check column headers for unit patterns
    units = _extract_from_headers_with_parens(table_cells, unit_patterns)
    if units:
        return units

    # Strategy 2: Check rows 3-5 for dedicated unit row (beyond typical 0-2)
    for row_idx in [3, 4, 5]:
        row_cells = [
            c for c in table_cells if c.start_row_offset_idx == row_idx and not c.column_header
        ]

        if not row_cells:
            continue

        # Count cells with unit patterns
        unit_count = sum(
            1
            for c in row_cells
            if c.text and any(p.lower() in c.text.lower() for p in unit_patterns)
        )

        # If >70% of cells contain units, it's a unit row
        if unit_count / len(row_cells) > 0.70:
            logger.info(
                "Found dedicated unit row in Type B table",
                extra={
                    "row_index": row_idx,
                    "unit_count": unit_count,
                    "total_cells": len(row_cells),
                    "ratio": round(unit_count / len(row_cells), 3),
                },
            )

            # Extract units from this row
            for cell in row_cells:
                if cell.text and cell.text.strip():
                    units[cell.start_col_offset_idx] = cell.text.strip()

            return units

    # Strategy 3: Check if all data cells have embedded units
    # (This means units might be in the data itself)
    if not units:
        logger.info(
            "No explicit units found in Type B table - units may be embedded in data",
            extra={"table_type": "entity_column_junk"},
        )

    return units


def _detect_unit_column_statistical(
    cells: list, unit_patterns: list[str], threshold: float = 0.60, min_samples: int = 3
) -> tuple[bool, float]:
    """Detect if a column contains units using statistical threshold analysis.

    This implements a production-grade framework for unit detection that works
    for ANY financial document, replacing the flawed "first 3 cells" positional
    sampling approach.

    Strategy:
    1. PRIMARY: Statistical analysis across ALL cells with configurable threshold
    2. SECONDARY: Pattern concentration in middle section (rows 3-10)
    3. FALLBACK: Extended unit patterns for edge cases

    Args:
        cells: List of cells to analyze
        unit_patterns: List of unit pattern strings to match
        threshold: Minimum ratio of cells with units (default: 0.60 = 60%)
        min_samples: Minimum number of cells required for analysis

    Returns:
        Tuple of (has_units: bool, confidence: float)
        - has_units: True if column contains units above threshold
        - confidence: Detection confidence score (0.0-1.0)

    Example:
        >>> cells = [cell1, cell2, cell3, ...] # 14 cells
        >>> patterns = ['EUR', 'ton', 'kt', '%']
        >>> has_units, confidence = _detect_unit_column_statistical(cells, patterns)
        >>> # has_units=True, confidence=0.857 if 12/14 cells match
    """
    if not cells:
        return False, 0.0

    # Validate sample size
    is_valid, non_empty_cells = _validate_sample_size(cells, min_samples)
    if not is_valid:
        return False, 0.0

    # STRATEGY 1: Statistical analysis across ALL cells
    detected, confidence, _ = _detect_by_statistical_threshold(
        non_empty_cells, unit_patterns, threshold
    )
    if detected:
        return True, confidence

    # STRATEGY 2: Check middle section concentration (rows 3-10)
    detected, confidence = _detect_by_middle_section_concentration(non_empty_cells, unit_patterns)
    if detected:
        return True, confidence

    # STRATEGY 3: Extended unit patterns (fallback)
    detected, confidence = _detect_by_extended_patterns(non_empty_cells)
    if detected:
        return True, confidence

    # NO DETECTION: Column does not contain units
    # Calculate actual ratio for logging
    actual_ratio = (
        len([c for c in non_empty_cells if any(p in c.text for p in unit_patterns)])
        / len(non_empty_cells)
        if non_empty_cells
        else 0.0
    )
    return False, actual_ratio
