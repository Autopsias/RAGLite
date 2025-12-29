"""
Standard pivot table layout extraction.

This module handles common financial table layouts:
1. Temporal columns + Metric rows (periods in columns, metrics in rows)
2. Entity columns + Metric rows (entities in columns, metrics in rows)
3. Transposed tables (metrics as row labels, entities as column headers)

All extraction functions produce (entity, metric, period, value, unit) tuples.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem

logger = logging.getLogger(__name__)


def _extract_temporal_cols_metric_rows(
    table_cells: list,
    num_rows: int,
    num_cols: int,
    metadata: dict,
    document_id: str,
    page_number: int,
    table_index: int,
    table_item: TableItem,
    result: ConversionResult,
) -> list[dict[str, Any]]:
    """Extract temporal columns + metric rows layout (common in financial reports).

    Pattern:
              | YTD      | Q1       | Q2       |
        ------|----------|----------|----------|
        EBITDA|  1.2M    |  0.5M    |  0.7M    |
        Sales |  5.4M    |  2.1M    |  3.3M    |
    """
    from .core import extract_year, get_table_caption, get_table_markdown
    from .unit_inference import _parse_value_unit

    rows: list[dict[str, Any]] = []

    column_headers = [cell for cell in table_cells if cell.column_header]
    row_headers = [cell for cell in table_cells if cell.row_header]
    data_cells = [cell for cell in table_cells if not cell.column_header and not cell.row_header]

    # Build column → period mapping
    col_period_map: dict[int, str | None] = {}
    for cell in column_headers:
        col_idx = cell.start_col_offset_idx
        col_period_map[col_idx] = cell.text.strip() if cell.text else None

    # Build row → metric mapping
    row_metric_map: dict[int, str | None] = {}
    for cell in row_headers:
        row_idx = cell.start_row_offset_idx
        row_metric_map[row_idx] = cell.text.strip() if cell.text else None

    # Extract data cells
    for cell in data_cells:
        if not cell.text or not cell.text.strip():
            continue

        row_idx = cell.start_row_offset_idx
        col_idx = cell.start_col_offset_idx

        period = col_period_map.get(col_idx)
        metric = row_metric_map.get(row_idx)
        entity = None  # Will need inference or caption extraction

        value, unit = _parse_value_unit(cell.text)
        fiscal_year = extract_year(period) if period else None

        row_dict = {
            "entity": entity,
            "metric": metric,
            "period": period,
            "fiscal_year": fiscal_year,
            "value": value,
            "unit": unit,
            "page_number": page_number,
            "table_index": table_index,
            "table_caption": get_table_caption(table_item),
            "row_index": row_idx,
            "column_name": f"{metric}_{period}" if metric and period else None,
            "chunk_text": get_table_markdown(table_item, result)[:500],
            "document_id": document_id,
        }

        rows.append(row_dict)

    return rows


def _extract_entity_cols_metric_rows(
    table_cells: list,
    num_rows: int,
    num_cols: int,
    metadata: dict,
    document_id: str,
    page_number: int,
    table_index: int,
    table_item: TableItem,
    result: ConversionResult,
) -> list[dict[str, Any]]:
    """Extract entity columns + metric rows layout.

    Pattern:
          | Portugal | Angola | Brazil |
    ------|----------|--------|--------|
    EBITDA|   1.2M   |  0.8M  |  2.1M  |
    Sales |   5.4M   |  3.2M  |  7.8M  |
    """
    from .core import extract_year, get_table_caption, get_table_markdown
    from .unit_inference import _parse_value_unit

    # Phase 2: Import safe wrapper function from centralized validation module
    from .validation import safe_assign_entity

    rows: list[dict[str, Any]] = []

    column_headers = [cell for cell in table_cells if cell.column_header]
    row_headers = [cell for cell in table_cells if cell.row_header]
    data_cells = [cell for cell in table_cells if not cell.column_header and not cell.row_header]

    # Build column → entity mapping
    col_entity_map: dict[int, str | None] = {}
    for cell in column_headers:
        col_idx = cell.start_col_offset_idx
        entity_raw = cell.text.strip() if cell.text else None

        # Phase 2: Use safe wrapper function for entity validation
        # This ALWAYS validates and is IMPOSSIBLE to bypass
        entity = safe_assign_entity(
            entity_raw,
            source="standard_layouts_entity_cols",
            page_number=page_number,
            table_index=table_index,
            col_idx=col_idx,
        )

        col_entity_map[col_idx] = entity

    # Build row → metric mapping
    row_metric_map: dict[int, str | None] = {}
    for cell in row_headers:
        row_idx = cell.start_row_offset_idx
        row_metric_map[row_idx] = cell.text.strip() if cell.text else None

    # Try to infer period from table caption
    caption = get_table_caption(table_item)
    period = None
    fiscal_year = None
    if caption:
        # Extract year if present
        fiscal_year = extract_year(caption)
        # Use caption as period if it contains temporal info
        if fiscal_year or any(
            keyword in caption.lower()
            for keyword in ["ytd", "q1", "q2", "q3", "q4", "budget", "forecast"]
        ):
            period = caption

    # Extract data cells
    for cell in data_cells:
        if not cell.text or not cell.text.strip():
            continue

        row_idx = cell.start_row_offset_idx
        col_idx = cell.start_col_offset_idx

        entity = col_entity_map.get(col_idx)
        metric = row_metric_map.get(row_idx)

        value, unit = _parse_value_unit(cell.text)

        row_dict = {
            "entity": entity,
            "metric": metric,
            "period": period,  # May be NULL - acceptable for Entity-Metric tables
            "fiscal_year": fiscal_year,
            "value": value,
            "unit": unit,
            "page_number": page_number,
            "table_index": table_index,
            "table_caption": caption,
            "row_index": row_idx,
            "column_name": f"{metric}_{entity}" if metric and entity else None,
            "chunk_text": get_table_markdown(table_item, result)[:500],
            "document_id": document_id,
        }

        rows.append(row_dict)

    return rows


def _extract_transposed_entity_cols_metric_row_labels(
    table_cells: list,
    num_rows: int,
    num_cols: int,
    metadata: dict,
    document_id: str,
    page_number: int,
    table_index: int,
    table_item: TableItem,
    result: ConversionResult,
) -> list[dict[str, Any]]:
    """Extract transposed table: Entities in column headers, metrics in first column (row labels).

    Pattern (pages 20-21 "Cost per ton" tables):
                            Portugal        Tunisia         Lebanon         Brazil
                        Aug-25  Budget  Aug-25  Budget  Aug-25  Budget  Aug-25  Budget
    Variable Cost       -23.4   -20.4   -29.1   -27.3   -50.9   -44.4   -20.7   -22.0
    Thermal Energy      -5.9    -5.9    -11.1   -10.5   -9.7    -12.3   -8.8    -9.1

    Strategy:
    1. Extract entities from Row 0 column headers (Portugal, Tunisia, etc.)
    2. Extract periods from Row 1 sub-headers if present (Aug-25, Budget, Aug-24)
    3. Extract metrics from first column cells (col_idx=0)
    4. Map data cells to (entity, metric, period) tuples

    Args:
        table_cells: List of table cells
        num_rows: Number of rows
        num_cols: Number of columns
        metadata: Layout metadata from detect_table_layout
        document_id: Document filename
        page_number: Page number
        table_index: Table index on page
        table_item: Docling TableItem
        result: Docling ConversionResult

    Returns:
        List of structured row dicts ready for SQL insertion
    """
    from .classification import _detect_table_orientation
    from .core import extract_year, get_table_caption, get_table_markdown
    from .unit_inference import (
        _detect_unit_column_statistical,
        _extract_units_entity_column_junk,
        _extract_units_normal,
        _parse_value_unit,
    )

    # Phase 2: Import safe wrapper function from centralized validation module
    from .validation import safe_assign_entity

    rows: list[dict[str, Any]] = []

    column_headers = [cell for cell in table_cells if cell.column_header]
    first_col_cells = [
        cell for cell in table_cells if cell.start_col_offset_idx == 0 and not cell.column_header
    ]
    data_cells = [
        cell
        for cell in table_cells
        if not cell.column_header and cell.start_col_offset_idx > 0  # Exclude first column
    ]

    # Build column header mapping by row level
    headers_by_row: dict[int, list] = {}
    for cell in column_headers:
        row_idx = cell.start_row_offset_idx
        if row_idx not in headers_by_row:
            headers_by_row[row_idx] = []
        headers_by_row[row_idx].append(cell)

    row_levels = sorted(headers_by_row.keys())

    # Build column → (entity, period) mapping
    column_mapping: dict[int, tuple[str | None, str | None]] = {}
    # Build column → unit mapping (for 3+ header row tables)
    column_unit_map: dict[int, str | None] = {}

    if len(row_levels) >= 2:
        # Multi-header: Row 0 = Entities, Row 1 = Periods
        entity_row = row_levels[0]
        period_row = row_levels[1]

        # Build entity mapping (may span columns)
        entity_map: dict[int, str] = {}
        for cell in headers_by_row[entity_row]:
            start_col = cell.start_col_offset_idx
            end_col = cell.end_col_offset_idx
            entity_raw = cell.text.strip() if cell.text else None

            # Phase 2: Use safe wrapper function for entity validation
            # This ALWAYS validates and is IMPOSSIBLE to bypass
            entity_text = safe_assign_entity(
                entity_raw,
                source="standard_layouts_transposed_multi_header",
                page_number=page_number,
                table_index=table_index,
                row_idx=entity_row,
                col_idx=start_col,
            )

            # Skip None entities (empty cells)
            if entity_text is not None:
                for col_idx in range(start_col, end_col):
                    entity_map[col_idx] = entity_text

        # Build final mapping with periods
        for cell in headers_by_row[period_row]:
            col_idx = cell.start_col_offset_idx
            period = cell.text.strip() if cell.text else None
            entity = entity_map.get(col_idx, "Unknown")
            column_mapping[col_idx] = (entity, period)

        # Check for 3rd header row containing units
        if len(row_levels) >= 3:
            unit_row = row_levels[2]
            # Check if this row contains unit patterns
            unit_patterns = [
                "EUR",
                "ton",
                "Meur",
                "kt",
                "%",
                "GJ",
                "€",
                "$",
                "USD",
                "kWh",
                "m3",
                "MW",
            ]
            row_cells = headers_by_row[unit_row]

            # DEBUG
            print(f"[DEBUG] Table on page {page_number}, table_index={table_index}")
            print(f"[DEBUG] len(row_levels)={len(row_levels)}, checking for units in row_levels[2]")
            print(f"[DEBUG] Number of cells in unit row: {len(row_cells)}")

            # Sample a few cells to check if they look like units
            sample_cells = row_cells[: min(3, len(row_cells))]
            print("[DEBUG] Sample cells (first 3):")
            for i, cell in enumerate(sample_cells):
                print(
                    f"[DEBUG]   Cell {i}: text='{cell.text}' (column {cell.start_col_offset_idx})"
                )

            looks_like_units = any(
                cell.text and any(pattern in cell.text for pattern in unit_patterns)
                for cell in sample_cells
                if cell.text
            )

            print(f"[DEBUG] looks_like_units={looks_like_units}")

            if looks_like_units:
                # This is a unit header row - extract units
                print(f"[DEBUG] Extracting units from {len(row_cells)} cells")
                for cell in row_cells:
                    col_idx = cell.start_col_offset_idx
                    unit_text = cell.text.strip() if cell.text else None
                    if unit_text:
                        column_unit_map[col_idx] = unit_text
                        print(f"[DEBUG]   column_unit_map[{col_idx}] = '{unit_text}'")
                print(f"[DEBUG] Total units extracted: {len(column_unit_map)}")
            else:
                print("[DEBUG] Unit patterns NOT detected in sample cells")

    elif len(row_levels) == 1:
        # Single header row - assume entities (no periods)
        for cell in headers_by_row[row_levels[0]]:
            col_idx = cell.start_col_offset_idx
            header_entity_raw: str | None = cell.text.strip() if cell.text else None

            # Phase 2: Use safe wrapper function for entity validation
            # This ALWAYS validates and is IMPOSSIBLE to bypass
            header_entity = safe_assign_entity(
                header_entity_raw,
                source="standard_layouts_transposed_single_header",
                page_number=page_number,
                table_index=table_index,
                col_idx=col_idx,
            )

            column_mapping[col_idx] = (header_entity, None)

    # Build row → metric mapping from first column
    row_metric_map: dict[int, str] = {}
    for cell in first_col_cells:
        row_idx = cell.start_row_offset_idx
        # Parse metric name and unit from cell text
        metric_text = cell.text.strip() if cell.text else None
        if metric_text:
            row_metric_map[row_idx] = metric_text

    # PHASE 2.7.4: ADAPTIVE ORIENTATION-AWARE UNIT DETECTION
    # Research-validated approach: Detect orientation FIRST, then apply appropriate extraction strategy
    # Industry standard: TableRAG, FinRAG, Bloomberg all use this pattern

    unit_patterns = [
        "EUR",
        "ton",
        "Meur",
        "kt",
        "%",
        "GJ",
        "€",
        "$",
        "USD",
        "kWh",
        "m3",
        "MW",
        "kton",
        "m²",
        "m³",
        "kg",
        "g",
        "t",
        "l",
        "ml",
        "h",
        "min",
        "s",
        "kW",
        "GW",
        "MWh",
        "GWh",
        "million",
        "billion",
        "thousand",
        "M€",
        "k€",
        "bn",
        "mn",
        "ratio",
        "rate",
        "pts",
        "bps",
        "basis points",
        "percentage",
        "pct",
        "people",
        "FTE",
        "headcount",
        "units",
    ]

    # Step 1: Detect table orientation
    orientation, orientation_confidence = _detect_table_orientation(
        table_cells, num_rows, num_cols, unit_patterns
    )

    # Step 2: Apply orientation-specific unit extraction strategy (V2 - 4-type taxonomy)
    row_unit_map: dict[int, str] = {}
    col_unit_map_normal: dict[int, str] = {}  # For normal/Type B tables (column-based units)

    if orientation == "transposed_metric":
        # TYPE A: Transposed Metric-Entity (metrics in col 0, units in col 1)
        # Example: Row 0: Sales Volumes | kton | 1.381 | 1.378
        col_1_cells = [
            cell
            for cell in table_cells
            if cell.start_col_offset_idx == 1 and not cell.column_header
        ]

        col_1_has_units, unit_detection_confidence = _detect_unit_column_statistical(
            col_1_cells, unit_patterns, threshold=0.60, min_samples=3
        )

        logger.info(
            f"Type A (transposed_metric) unit detection: {len(row_unit_map)} units found",
            extra={
                "page_number": page_number,
                "table_index": table_index,
                "confidence": round(orientation_confidence, 3),
                "col_1_cells": len(col_1_cells),
                "has_units": col_1_has_units,
                "unit_confidence": round(unit_detection_confidence, 3),
            },
        )

        if col_1_has_units:
            # Extract units from column 1
            for cell in col_1_cells:
                row_idx = cell.start_row_offset_idx
                unit_text = cell.text.strip() if cell.text else None
                if unit_text:
                    row_unit_map[row_idx] = unit_text

            # Update data_cells to exclude column 1 (since it contains units, not data)
            data_cells = [
                cell
                for cell in table_cells
                if not cell.column_header and cell.start_col_offset_idx > 1
            ]

    elif orientation == "entity_column_junk":
        # TYPE B: Entity-Column with Junk Column 0
        # Example: Col 0: 14.003 | Col 1: Portugal | Col 2+: Data
        col_unit_map_normal = _extract_units_entity_column_junk(table_cells, unit_patterns)

        logger.info(
            f"Type B (entity_column_junk) unit detection: {len(col_unit_map_normal)} units found",
            extra={
                "page_number": page_number,
                "table_index": table_index,
                "confidence": round(orientation_confidence, 3),
                "units_found": len(col_unit_map_normal),
            },
        )

        # For Type B, skip column 0 (junk) and start from column 1
        data_cells = [
            cell
            for cell in table_cells
            if not cell.column_header and cell.start_col_offset_idx >= 1
        ]

    elif orientation == "normal_metric":
        # TYPE C: Normal Metric-Entity (metrics in col 0, data in col 1+)
        # Example: Col 0: EBITDA IFRS | Col 1+: 128.825, 91.438, etc.
        col_unit_map_normal = _extract_units_normal(table_cells, unit_patterns)

        logger.info(
            f"Type C (normal_metric) unit detection: {len(col_unit_map_normal)} units found",
            extra={
                "page_number": page_number,
                "table_index": table_index,
                "confidence": round(orientation_confidence, 3),
                "units_found": len(col_unit_map_normal),
            },
        )

    else:
        # UNKNOWN ORIENTATION: Fall back to transposed strategy (legacy behavior)
        logger.warning(
            f"Unknown orientation (confidence={orientation_confidence:.3f}) - using fallback",
            extra={"page_number": page_number, "table_index": table_index},
        )

        col_1_cells = [
            cell
            for cell in table_cells
            if cell.start_col_offset_idx == 1 and not cell.column_header
        ]

        col_1_has_units, unit_detection_confidence = _detect_unit_column_statistical(
            col_1_cells, unit_patterns, threshold=0.60, min_samples=3
        )

        if col_1_has_units:
            for cell in col_1_cells:
                row_idx = cell.start_row_offset_idx
                unit_text = cell.text.strip() if cell.text else None
                if unit_text:
                    row_unit_map[row_idx] = unit_text

            data_cells = [
                cell
                for cell in table_cells
                if not cell.column_header and cell.start_col_offset_idx > 1
            ]

    # Extract data cells
    caption = get_table_caption(table_item)

    for cell in data_cells:
        if not cell.text or not cell.text.strip():
            continue

        row_idx = cell.start_row_offset_idx
        col_idx = cell.start_col_offset_idx

        # Get entity and period from column mapping
        entity_period = column_mapping.get(col_idx, (None, None))
        cell_entity_transposed: str | None = entity_period[0]
        cell_period: str | None = entity_period[1]

        # Get metric from first column
        metric = row_metric_map.get(row_idx)

        # Get unit - priority order (PHASE 2.7.4 - Orientation-aware):
        # 1. From row-based unit map (column 1 - transposed tables)
        # 2. From column-based unit map (3rd header row - transposed tables)
        # 3. From normal table column units (dedicated unit row or metric names)
        # 4. Parse from data cell (fallback)
        if row_unit_map and row_idx in row_unit_map:
            # Transposed table: unit from column 1 (same row)
            unit = row_unit_map.get(row_idx)
            # Parse only value from data cell
            value, _ = _parse_value_unit(cell.text)
        elif column_unit_map and col_idx in column_unit_map:
            # Transposed table: unit from column header (3rd row)
            unit = column_unit_map.get(col_idx)
            # Parse only value from data cell
            value, _ = _parse_value_unit(cell.text)
        elif col_unit_map_normal and col_idx in col_unit_map_normal:
            # Normal table: unit from dedicated unit row or column headers
            unit = col_unit_map_normal.get(col_idx)
            # Parse only value from data cell
            value, _ = _parse_value_unit(cell.text)
        else:
            # Fallback: parse value + unit from data cell
            value, unit = _parse_value_unit(cell.text)

        # Extract fiscal year
        fiscal_year = extract_year(cell_period) if cell_period else None

        row_dict = {
            "entity": cell_entity_transposed,
            "metric": metric,
            "period": cell_period,
            "fiscal_year": fiscal_year,
            "value": value,
            "unit": unit,
            "page_number": page_number,
            "table_index": table_index,
            "table_caption": caption,
            "row_index": row_idx,
            "column_name": (
                f"{metric}_{cell_entity_transposed}_{cell_period}"
                if metric and cell_entity_transposed and cell_period
                else f"{metric}_{cell_entity_transposed}"
                if metric and cell_entity_transposed
                else None
            ),
            "chunk_text": get_table_markdown(table_item, result)[:500],
            "document_id": document_id,
            "extraction_method": "transposed_entity_cols_metric_row_labels",
        }

        rows.append(row_dict)

    return rows
