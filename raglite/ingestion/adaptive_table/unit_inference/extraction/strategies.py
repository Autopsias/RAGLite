"""Unit extraction strategies for different table orientations.

This module provides orientation-aware unit extraction strategies for:
- Normal tables (entities in columns, metrics in rows)
- Type B tables (junk column 0, entities in column 1)
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def _extract_dedicated_unit_row(
    table_cells: list, unit_patterns: list[str], row_indices: list[int]
) -> dict[int, str]:
    """Extract units from dedicated unit row(s).

    Checks specified row indices for unit rows by counting cells
    with unit patterns. If >60% of cells contain units, treats
    as dedicated unit row.

    Args:
        table_cells: List of table cells
        unit_patterns: List of unit pattern strings to match
        row_indices: Row indices to check (e.g., [0, 1, 2])

    Returns:
        Dictionary mapping column index to unit string, or empty dict
    """
    for row_idx in row_indices:
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
                "Found dedicated unit row",
                extra={
                    "row_index": row_idx,
                    "unit_count": unit_count,
                    "total_cells": len(row_cells),
                    "ratio": round(unit_count / len(row_cells), 3),
                },
            )

            # Extract units from this row
            units = {}
            for cell in row_cells:
                if cell.text and cell.text.strip():
                    units[cell.start_col_offset_idx] = cell.text.strip()

            return units

    return {}


def _extract_from_metric_names(
    table_cells: list, unit_patterns: list[str], header_column: int
) -> dict[int, str]:
    """Extract units from metric names with units in parentheses.

    Parses patterns like "Revenue (EUR)", "EBITDA (Meur)", etc.

    Args:
        table_cells: List of table cells
        unit_patterns: List of unit pattern strings to match
        header_column: Column index containing row headers/metric names

    Returns:
        Dictionary mapping row index to unit string
    """
    units = {}
    row_headers = [c for c in table_cells if c.start_col_offset_idx == header_column]

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

    return units


def _extract_from_column_headers(table_cells: list, unit_patterns: list[str]) -> dict[int, str]:
    """Extract units from column headers.

    Args:
        table_cells: List of table cells
        unit_patterns: List of unit pattern strings to match

    Returns:
        Dictionary mapping column index to unit string
    """
    units = {}
    col_headers = [c for c in table_cells if c.column_header]

    for cell in col_headers:
        if not cell.text:
            continue

        # Check if header contains unit pattern
        for pattern in unit_patterns:
            if pattern.lower() in cell.text.lower():
                units[cell.start_col_offset_idx] = pattern
                break

    return units


def _extract_from_headers_with_parens(
    table_cells: list, unit_patterns: list[str]
) -> dict[int, str]:
    """Extract units from headers containing parenthesized units.

    Checks for patterns like "Total R SUSTAINING (EUR million)" in
    column headers.

    Args:
        table_cells: List of table cells
        unit_patterns: List of unit pattern strings to match

    Returns:
        Dictionary mapping column index to unit string
    """
    units = {}
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

    return units
