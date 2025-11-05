"""
Multi-header table extraction for complex financial tables.

This module handles tables with multiple header rows, such as:
- Row 0 = Metrics (EBITDA, Revenue, etc.)
- Row 1 = Entities (Portugal, Angola, etc.)
- Row headers = Periods (YTD, Q1, etc.)

The extraction produces (entity, metric, period, value, unit) tuples.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem


def _extract_multi_header_metric_entity(
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
    """Extract multi-header table: Row 0=Metrics, Row 1=Entities, Row headers=Periods.

    This function handles tables where:
    - First header row contains metric names
    - Second header row contains entity names
    - Row headers contain period/time information

    Args:
        table_cells: List of table cells from Docling
        num_rows: Number of rows in table
        num_cols: Number of columns in table
        metadata: Layout detection metadata
        document_id: Document identifier
        page_number: Page number in document
        table_index: Table index on page
        table_item: Docling table item
        result: Docling conversion result

    Returns:
        List of extracted data rows as dictionaries
    """
    # Import helper functions from other modules
    # These are imported locally to avoid circular dependencies
    from .core import (
        _extract_year,
        _get_table_caption,
        _get_table_markdown,
    )
    from .unit_inference import _parse_value_unit

    rows: list[dict[str, Any]] = []

    column_headers = [cell for cell in table_cells if cell.column_header]
    row_headers = [cell for cell in table_cells if cell.row_header]
    data_cells = [cell for cell in table_cells if not cell.column_header and not cell.row_header]

    # Build column mapping: col_idx → (metric, entity)
    headers_by_row: dict[int, list] = {}
    for cell in column_headers:
        row_idx = cell.start_row_offset_idx
        if row_idx not in headers_by_row:
            headers_by_row[row_idx] = []
        headers_by_row[row_idx].append(cell)

    row_levels = sorted(headers_by_row.keys())

    if len(row_levels) < 2:
        return rows  # Cannot extract multi-header with < 2 header rows

    metric_row = row_levels[0]
    entity_row = row_levels[1]

    # Build metric mapping (may span columns)
    metric_map: dict[int, str] = {}
    for cell in headers_by_row[metric_row]:
        start_col = cell.start_col_offset_idx
        end_col = cell.end_col_offset_idx
        metric_text = cell.text.strip() if cell.text else "Unknown"
        for col_idx in range(start_col, end_col):
            metric_map[col_idx] = metric_text

    # Build column mapping
    column_mapping: dict[int, tuple[str | None, str | None]] = {}
    for cell in headers_by_row[entity_row]:
        col_idx = cell.start_col_offset_idx
        entity = cell.text.strip() if cell.text else "Unknown"
        metric = metric_map.get(col_idx, "Unknown")
        column_mapping[col_idx] = (metric, entity)

    # Build row period mapping
    row_period_map: dict[int, str | None] = {}
    for cell in row_headers:
        row_idx = cell.start_row_offset_idx
        row_period_map[row_idx] = cell.text.strip() if cell.text else None

    # Extract data cells
    for cell in data_cells:
        if not cell.text or not cell.text.strip():
            continue

        row_idx = cell.start_row_offset_idx
        col_idx = cell.start_col_offset_idx

        metric_entity = column_mapping.get(col_idx, (None, None))
        cell_metric: str | None = metric_entity[0]
        cell_entity: str | None = metric_entity[1]
        period = row_period_map.get(row_idx)

        # Parse value + unit
        value, unit = _parse_value_unit(cell.text)

        fiscal_year = _extract_year(period) if period else None

        row_dict = {
            "entity": cell_entity,
            "metric": cell_metric,
            "period": period,
            "fiscal_year": fiscal_year,
            "value": value,
            "unit": unit,
            "page_number": page_number,
            "table_index": table_index,
            "table_caption": _get_table_caption(table_item),
            "row_index": row_idx,
            "column_name": f"{cell_metric}_{cell_entity}" if cell_metric and cell_entity else None,
            "chunk_text": _get_table_markdown(table_item, result)[:500],
            "document_id": document_id,
        }

        rows.append(row_dict)

    return rows
