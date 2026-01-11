"""
Multi-header table extraction for complex financial tables.

This module handles tables with multiple header rows, such as:
- Row 0 = Metrics (EBITDA, Revenue, etc.)
- Row 1 = Entities (Portugal, Angola, etc.)
- Row headers = Periods (YTD, Q1, etc.)

The extraction produces (entity, metric, period, value, unit) tuples.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem

logger = logging.getLogger(__name__)


def _identify_multi_header_structure(
    column_headers: list,
) -> tuple[dict[int, list], int, int] | tuple[None, None, None]:
    """Identify multi-header structure from column headers.

    Args:
        column_headers: List of column header cells

    Returns:
        Tuple of (headers_by_row, metric_row_idx, entity_row_idx) or (None, None, None)
        if structure is invalid (< 2 header rows)
    """
    # Build column mapping: col_idx → (metric, entity)
    headers_by_row: dict[int, list] = {}
    for cell in column_headers:
        row_idx = cell.start_row_offset_idx
        if row_idx not in headers_by_row:
            headers_by_row[row_idx] = []
        headers_by_row[row_idx].append(cell)

    row_levels = sorted(headers_by_row.keys())

    if len(row_levels) < 2:
        return None, None, None  # Cannot extract multi-header with < 2 header rows

    metric_row = row_levels[0]
    entity_row = row_levels[1]

    return headers_by_row, metric_row, entity_row


def _build_metric_column_mapping(
    headers_by_row: dict[int, list],
    metric_row: int,
    entity_row: int,
    safe_assign_metric: Callable[..., Any],
    safe_assign_entity: Callable[..., Any],
    page_number: int,
    table_index: int,
) -> dict[int, tuple[str | None, str | None]]:
    """Build column mapping from multi-header structure.

    Args:
        headers_by_row: Dictionary mapping row indices to header cells
        metric_row: Row index for metric names
        entity_row: Row index for entity names
        safe_assign_metric: Metric validation function
        safe_assign_entity: Entity validation function
        page_number: Page number for validation context
        table_index: Table index for validation context

    Returns:
        Dictionary mapping column indices to (metric, entity) tuples
    """
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
        entity_raw = cell.text.strip() if cell.text else None

        # Phase 2: Use safe wrapper function for entity validation
        # This ALWAYS validates and is IMPOSSIBLE to bypass
        entity = safe_assign_entity(
            entity_raw,
            source="multi_header_entity_row",
            page_number=page_number,
            table_index=table_index,
            row_idx=entity_row,
            col_idx=col_idx,
        )

        metric_raw = metric_map.get(col_idx)

        # Phase 2: Use safe wrapper function for metric validation
        # This ALWAYS validates and is IMPOSSIBLE to bypass
        metric = safe_assign_metric(
            metric_raw,
            source="multi_header_metric_row",
            page_number=page_number,
            table_index=table_index,
            row_idx=metric_row,
            col_idx=col_idx,
        )

        column_mapping[col_idx] = (metric, entity)

    return column_mapping


def _build_row_period_mapping(row_headers: list) -> dict[int, str | None]:
    """Build mapping from row indices to period labels.

    Args:
        row_headers: List of row header cells

    Returns:
        Dictionary mapping row indices to period text
    """
    row_period_map: dict[int, str | None] = {}
    for cell in row_headers:
        row_idx = cell.start_row_offset_idx
        row_period_map[row_idx] = cell.text.strip() if cell.text else None
    return row_period_map


def _extract_data_rows(
    data_cells: list,
    column_mapping: dict[int, tuple[str | None, str | None]],
    row_period_map: dict[int, str | None],
    parse_value_unit: Callable[..., Any],
    extract_year: Callable[..., Any],
    page_number: int,
    table_index: int,
    table_item: TableItem,
    result: ConversionResult,
    document_id: str,
) -> list[dict[str, Any]]:
    """Extract data rows from data cells using mappings.

    Args:
        data_cells: List of data cells (non-header cells)
        column_mapping: Column index to (metric, entity) mapping
        row_period_map: Row index to period mapping
        parse_value_unit: Value/unit parsing function
        extract_year: Year extraction function
        page_number: Page number in document
        table_index: Table index on page
        table_item: Docling table item
        result: Docling conversion result
        document_id: Document identifier

    Returns:
        List of extracted data rows as dictionaries
    """
    from .core import get_table_caption, get_table_markdown

    rows: list[dict[str, Any]] = []

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
        value, unit = parse_value_unit(cell.text)

        fiscal_year = extract_year(period) if period else None

        row_dict = {
            "entity": cell_entity,
            "metric": cell_metric,
            "period": period,
            "fiscal_year": fiscal_year,
            "value": value,
            "unit": unit,
            "page_number": page_number,
            "table_index": table_index,
            "table_caption": get_table_caption(table_item),
            "row_index": row_idx,
            "column_name": f"{cell_metric}_{cell_entity}" if cell_metric and cell_entity else None,
            "chunk_text": get_table_markdown(table_item, result)[:500],
            "document_id": document_id,
        }

        rows.append(row_dict)

    return rows


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
    from .core import extract_year
    from .unit_inference import _parse_value_unit

    # Phase 2: Import safe wrapper functions from centralized validation module
    from .validation import safe_assign_entity, safe_assign_metric

    column_headers = [cell for cell in table_cells if cell.column_header]
    row_headers = [cell for cell in table_cells if cell.row_header]
    data_cells = [cell for cell in table_cells if not cell.column_header and not cell.row_header]

    # Identify structure
    structure = _identify_multi_header_structure(column_headers)
    if structure[0] is None:
        return []
    headers_by_row, metric_row, entity_row = structure

    # Build column mapping
    column_mapping = _build_metric_column_mapping(
        headers_by_row=headers_by_row,
        metric_row=metric_row,
        entity_row=entity_row,
        safe_assign_metric=safe_assign_metric,
        safe_assign_entity=safe_assign_entity,
        page_number=page_number,
        table_index=table_index,
    )

    # Build row period mapping
    row_period_map = _build_row_period_mapping(row_headers)

    # Extract data rows
    rows = _extract_data_rows(
        data_cells=data_cells,
        column_mapping=column_mapping,
        row_period_map=row_period_map,
        parse_value_unit=_parse_value_unit,
        extract_year=extract_year,
        page_number=page_number,
        table_index=table_index,
        table_item=table_item,
        result=result,
        document_id=document_id,
    )

    return rows
