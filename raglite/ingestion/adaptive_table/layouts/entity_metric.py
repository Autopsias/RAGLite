"""Entity-metric layout extraction functions.

This module handles tables with:
- Temporal columns + Metric rows (periods in columns, metrics in rows)
- Entity columns + Metric rows (entities in columns, metrics in rows)
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
    from ..core import extract_year, get_table_caption, get_table_markdown
    from ..unit_inference import _parse_value_unit

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
    from ..core import extract_year, get_table_caption, get_table_markdown
    from ..unit_inference import _parse_value_unit

    # Phase 2: Import safe wrapper function from centralized validation module
    from ..validation import safe_assign_entity

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
