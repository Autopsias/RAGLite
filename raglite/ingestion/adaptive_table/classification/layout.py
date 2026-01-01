"""
Table layout pattern detection for adaptive table extraction.

This module provides table layout pattern detection based on header classifications.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from .header import HeaderType, classify_header

logger = logging.getLogger(__name__)


class TableLayout(Enum):
    """Detected table layout pattern."""

    # Multi-header: Row 0=Metrics, Row 1=Entities, Rows=Periods
    MULTI_HEADER_METRIC_ENTITY = "multi_header_metric_entity"

    # Multi-header generic: 2+ header rows + metric rows (relaxed detection)
    MULTI_HEADER_GENERIC = "multi_header_generic"

    # Standard pivots
    TEMPORAL_COLS_METRIC_ROWS = "temporal_cols_metric_rows"  # Cols=Periods, Rows=Metrics
    ENTITY_COLS_METRIC_ROWS = "entity_cols_metric_rows"  # Cols=Entities, Rows=Metrics
    METRIC_COLS_ENTITY_ROWS = "metric_cols_entity_rows"  # Cols=Metrics, Rows=Entities

    # Phase 2.7: Transposed table - metrics as row labels (first column), entities as column headers
    TRANSPOSED_ENTITY_COLS_METRIC_ROW_LABELS = "transposed_entity_cols_metric_row_labels"

    # Fallback
    UNKNOWN = "unknown"


def detect_table_layout(
    table_cells: list, num_rows: int, num_cols: int
) -> tuple[TableLayout, dict[str, Any]]:
    """Detect table layout pattern from header classifications.

    Analyzes header cells to determine table structure and return layout metadata.

    Args:
        table_cells: List of table cells from Docling
        num_rows: Number of rows
        num_cols: Number of columns

    Returns:
        Tuple of (TableLayout, metadata_dict)
        metadata_dict contains:
            - col_header_types: {row_idx: [HeaderType, ...]}
            - row_header_types: [HeaderType, ...]
            - entity_location: 'rows' | 'cols' | 'multi_header_row1'
            - metric_location: 'rows' | 'cols' | 'multi_header_row0'
            - period_location: 'rows' | 'cols' | 'row_headers'
    """
    # Separate header types
    column_headers = [cell for cell in table_cells if cell.column_header]
    row_headers = [cell for cell in table_cells if cell.row_header]

    # Classify column headers by row level
    col_header_by_row: dict[int, list] = {}
    for cell in column_headers:
        row_idx = cell.start_row_offset_idx
        if row_idx not in col_header_by_row:
            col_header_by_row[row_idx] = []
        col_header_by_row[row_idx].append(cell)

    # Classify each row of column headers
    col_header_types: dict[int, dict[HeaderType, int]] = {}
    for row_idx, cells in col_header_by_row.items():
        type_counts: dict[HeaderType, int] = {}
        for cell in cells:
            h_type = classify_header(cell.text)
            type_counts[h_type] = type_counts.get(h_type, 0) + 1
        col_header_types[row_idx] = type_counts

    # Classify row headers
    row_header_type_counts: dict[HeaderType, int] = {}
    for cell in row_headers:
        h_type = classify_header(cell.text)
        row_header_type_counts[h_type] = row_header_type_counts.get(h_type, 0) + 1

    # Detect layout pattern
    is_multi_header = len(col_header_by_row) > 1

    metadata = {
        "col_header_types": col_header_types,
        "row_header_types": row_header_type_counts,
        "is_multi_header": is_multi_header,
    }

    # Pattern 1: Multi-header with Metric (Row 0) + Entity (Row 1) - STRICT
    if is_multi_header and len(col_header_by_row) >= 2:
        row_levels = sorted(col_header_by_row.keys())
        row0_types = col_header_types.get(row_levels[0], {})
        row1_types = col_header_types.get(row_levels[1], {})

        row0_dominant = (
            max(row0_types.items(), key=lambda x: x[1])[0] if row0_types else HeaderType.UNKNOWN
        )
        row1_dominant = (
            max(row1_types.items(), key=lambda x: x[1])[0] if row1_types else HeaderType.UNKNOWN
        )

        if row0_dominant == HeaderType.METRIC and row1_dominant == HeaderType.ENTITY:
            metadata.update(
                {
                    "entity_location": "multi_header_row1",
                    "metric_location": "multi_header_row0",
                    "period_location": "row_headers",
                }
            )
            return TableLayout.MULTI_HEADER_METRIC_ENTITY, metadata

    # Pattern 1b: Phase 2.7 - TRANSPOSED table detection (PRIORITY: Check before relaxed multi-header)
    # CRITICAL: This must run BEFORE Pattern 1c (relaxed multi-header) to prevent being overridden
    # Check if first column (col_idx=0) contains metric names (NOT marked as row_header)
    # This handles the "Cost per ton" table pattern where metrics are row labels
    first_col_cells = [
        cell for cell in table_cells if cell.start_col_offset_idx == 0 and not cell.column_header
    ]
    if first_col_cells and len(first_col_cells) >= 3:  # At least 3 data rows
        # Classify first column cells
        first_col_types: dict[HeaderType, int] = {}
        for cell in first_col_cells:
            if cell.text and cell.text.strip():
                h_type = classify_header(cell.text)
                first_col_types[h_type] = first_col_types.get(h_type, 0) + 1

        # Check if first column is predominantly metrics
        metric_count = first_col_types.get(HeaderType.METRIC, 0)
        total_count = sum(first_col_types.values())
        is_first_col_metrics = (metric_count / total_count) > 0.5 if total_count > 0 else False

        # Check if column headers are entities or temporal
        col_header_entity_count = sum(
            count
            for htype, count in col_header_types.get(0, {}).items()
            if htype == HeaderType.ENTITY
        )
        col_header_temporal_count = sum(
            count
            for htype, count in col_header_types.get(0, {}).items()
            if htype == HeaderType.TEMPORAL
        )

        # Pattern match: First column = metrics + column headers = entities/temporal
        if is_first_col_metrics and (col_header_entity_count > 0 or col_header_temporal_count > 0):
            metadata.update(
                {
                    "entity_location": "cols",  # Entities in column headers
                    "metric_location": "first_column",  # Metrics in first column (row labels)
                    "period_location": "multi_header" if is_multi_header else "cols",
                    "transposed_pattern": True,
                    "first_col_metric_ratio": metric_count / total_count if total_count > 0 else 0,
                }
            )
            return TableLayout.TRANSPOSED_ENTITY_COLS_METRIC_ROW_LABELS, metadata

    # Pattern 1c: Multi-header RELAXED - Accept mixed column headers if rows are metrics
    # Key insight: Financial tables often have 2+ header rows + metric row headers
    # Don't require exact type matches - structure matters more than content types
    # MOVED AFTER transposed detection to prevent overriding transposed tables
    if is_multi_header and len(col_header_by_row) >= 2:
        # Check if row headers are predominantly metrics
        row_metric_count = row_header_type_counts.get(HeaderType.METRIC, 0)
        row_total = sum(row_header_type_counts.values())
        row_is_metrics = (row_metric_count / row_total) > 0.5 if row_total > 0 else False

        if row_is_metrics:
            # Accept as multi-header variant even with mixed column types
            metadata.update(
                {
                    "entity_location": "multi_header_mixed",  # Will try to extract from headers
                    "metric_location": "multi_header_mixed",  # Will try to extract from headers
                    "period_location": "row_headers",
                    "relaxed_detection": True,
                    "confidence": "medium",
                }
            )
            return TableLayout.MULTI_HEADER_GENERIC, metadata

    # Pattern 2: Single column header row
    if not is_multi_header and col_header_by_row:
        row0_types = col_header_types.get(0, {})
        row0_dominant = (
            max(row0_types.items(), key=lambda x: x[1])[0] if row0_types else HeaderType.UNKNOWN
        )

        row_dominant = (
            max(row_header_type_counts.items(), key=lambda x: x[1])[0]
            if row_header_type_counts
            else HeaderType.UNKNOWN
        )

        # TEMPORAL columns + METRIC rows
        if row0_dominant == HeaderType.TEMPORAL and row_dominant == HeaderType.METRIC:
            metadata.update(
                {
                    "entity_location": "unknown",  # May need inference
                    "metric_location": "rows",
                    "period_location": "cols",
                }
            )
            return TableLayout.TEMPORAL_COLS_METRIC_ROWS, metadata

        # ENTITY columns + METRIC rows
        if row0_dominant == HeaderType.ENTITY and row_dominant == HeaderType.METRIC:
            metadata.update(
                {
                    "entity_location": "cols",
                    "metric_location": "rows",
                    "period_location": "unknown",  # May need inference
                }
            )
            return TableLayout.ENTITY_COLS_METRIC_ROWS, metadata

        # METRIC columns + ENTITY rows
        if row0_dominant == HeaderType.METRIC and row_dominant == HeaderType.ENTITY:
            metadata.update(
                {
                    "entity_location": "rows",
                    "metric_location": "cols",
                    "period_location": "unknown",
                }
            )
            return TableLayout.METRIC_COLS_ENTITY_ROWS, metadata

    # Fallback: Unknown layout
    metadata.update(
        {
            "entity_location": "unknown",
            "metric_location": "unknown",
            "period_location": "unknown",
        }
    )
    return TableLayout.UNKNOWN, metadata
