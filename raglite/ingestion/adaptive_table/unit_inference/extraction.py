"""Unit extraction from table structures.

This module provides orientation-aware unit extraction strategies for:
- Normal tables (entities in columns, metrics in rows)
- Type B tables (junk column 0, entities in column 1)
- Statistical unit column detection
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


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
    units = {}

    # Strategy 1: Check for dedicated unit row (usually row 0, 1, or 2)
    for row_idx in [0, 1, 2]:
        row_cells = [c for c in table_cells if c.start_row_offset_idx == row_idx]

        if not row_cells:
            continue

        # Count cells with unit patterns
        unit_count = sum(
            1
            for c in row_cells
            if c.text and any(p.lower() in c.text.lower() for p in unit_patterns)
        )

        # If >60% of cells in this row contain units, it's a unit row
        if unit_count / len(row_cells) > 0.60:
            logger.info(
                "Found dedicated unit row in normal table",
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

    # Strategy 2: Extract from row headers (metric names with units in parentheses)
    row_headers = [c for c in table_cells if c.start_col_offset_idx == 0]

    for cell in row_headers:
        if not cell.text:
            continue

        # Parse "Metric (Unit)" pattern
        match = re.search(r"\(([^)]+)\)", cell.text)
        if match:
            unit = match.group(1).strip()
            # Verify it's a valid unit pattern
            if any(p.lower() in unit.lower() for p in unit_patterns):
                units[cell.start_row_offset_idx] = unit
                logger.debug(
                    "Extracted unit from metric name",
                    extra={
                        "row_index": cell.start_row_offset_idx,
                        "metric": cell.text,
                        "unit": unit,
                    },
                )

    # Strategy 3: Extract from column headers (if units appear there)
    col_headers = [c for c in table_cells if c.column_header]
    for cell in col_headers:
        if not cell.text:
            continue

        # Check if header contains unit pattern
        for pattern in unit_patterns:
            if pattern.lower() in cell.text.lower():
                units[cell.start_col_offset_idx] = pattern
                break

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
    headers = [c for c in table_cells if c.column_header]
    for header in headers:
        if not header.text:
            continue

        # Check for pattern like "Total R SUSTAINING (EUR million)"
        match = re.search(r"\(([^)]+)\)", header.text)
        if match:
            potential_unit = match.group(1).strip()
            if any(p.lower() in potential_unit.lower() for p in unit_patterns):
                units[header.start_col_offset_idx] = potential_unit
                logger.debug(
                    "Extracted unit from header",
                    extra={
                        "col_idx": header.start_col_offset_idx,
                        "unit": potential_unit,
                    },
                )

    # Strategy 2: Check rows 3-5 for dedicated unit row (beyond typical 0-2)
    if not units:
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

    # Filter to non-empty cells
    non_empty_cells = [cell for cell in cells if cell.text and cell.text.strip()]

    if len(non_empty_cells) < min_samples:
        # Not enough samples for statistical analysis
        return False, 0.0

    # STRATEGY 1: Statistical analysis across ALL cells
    cells_with_units = [
        cell for cell in non_empty_cells if any(pattern in cell.text for pattern in unit_patterns)
    ]

    unit_ratio = len(cells_with_units) / len(non_empty_cells)

    if unit_ratio >= threshold:
        # HIGH CONFIDENCE: Meets statistical threshold
        return True, unit_ratio

    # STRATEGY 2: Check middle section concentration (rows 3-10)
    # Units often concentrated in middle of table, sparse at edges
    middle_cells = [
        cell
        for cell in non_empty_cells
        if hasattr(cell, "start_row_offset_idx") and 3 <= cell.start_row_offset_idx <= 10
    ]

    if len(middle_cells) >= 3:
        middle_with_units = [
            cell for cell in middle_cells if any(pattern in cell.text for pattern in unit_patterns)
        ]
        middle_ratio = len(middle_with_units) / len(middle_cells)

        if middle_ratio >= 0.70:  # 70% in middle section
            # MEDIUM CONFIDENCE: Strong concentration in middle
            return True, 0.50 + (middle_ratio * 0.30)  # 0.50-0.80 confidence range

    # STRATEGY 3: Extended unit patterns (fallback)
    # Check for verbal unit indicators that might be missed
    extended_patterns = [
        "million",
        "billion",
        "thousand",
        "M€",
        "k€",
        "bn",
        "mn",
        "ratio",
        "rate",
        "percentage",
        "pct",
        "pts",
        "bps",
        "basis points",
        "people",
        "FTE",
        "headcount",
        "employees",
        "staff",
        "hours",
        "days",
        "months",
        "years",
        "weeks",
    ]

    extended_matches = [
        cell
        for cell in non_empty_cells
        if any(pattern.lower() in cell.text.lower() for pattern in extended_patterns)
    ]

    extended_ratio = len(extended_matches) / len(non_empty_cells)

    if extended_ratio >= 0.50:  # 50% threshold for extended patterns
        # LOW-MEDIUM CONFIDENCE: Extended patterns detected
        return True, 0.30 + (extended_ratio * 0.30)  # 0.30-0.60 confidence range

    # NO DETECTION: Column does not contain units
    return False, unit_ratio  # Return actual ratio for logging
