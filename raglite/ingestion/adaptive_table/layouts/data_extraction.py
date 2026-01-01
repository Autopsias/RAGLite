"""Data cell extraction functions for transposed table layout."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem


def _get_unit_and_value(
    cell_text: str,
    row_idx: int,
    col_idx: int,
    row_unit_map: dict[int, str],
    column_unit_map: dict[int, str | None],
    col_unit_map_normal: dict[int, str],
) -> tuple[str | None, str | None]:
    """Get unit and value from cell using priority order.

    Priority order:
    1. Row-based unit map (column 1 - transposed tables)
    2. Column-based unit map (3rd header row - transposed tables)
    3. Normal table column units (dedicated unit row or metric names)
    4. Parse from data cell (fallback)

    Args:
        cell_text: Cell text content
        row_idx: Row index
        col_idx: Column index
        row_unit_map: Row-based unit mapping
        column_unit_map: Column-based unit mapping
        col_unit_map_normal: Normal table unit mapping

    Returns:
        Tuple of (value, unit)
    """
    from ..unit_inference import _parse_value_unit

    if row_unit_map and row_idx in row_unit_map:
        # Transposed table: unit from column 1 (same row)
        unit = row_unit_map.get(row_idx)
        value, _ = _parse_value_unit(cell_text)
    elif column_unit_map and col_idx in column_unit_map:
        # Transposed table: unit from column header (3rd row)
        unit = column_unit_map.get(col_idx)
        value, _ = _parse_value_unit(cell_text)
    elif col_unit_map_normal and col_idx in col_unit_map_normal:
        # Normal table: unit from dedicated unit row or column headers
        unit = col_unit_map_normal.get(col_idx)
        value, _ = _parse_value_unit(cell_text)
    else:
        # Fallback: parse value + unit from data cell
        value, unit = _parse_value_unit(cell_text)

    # Convert value to string for consistent return type
    value_str = str(value) if value is not None else None
    return value_str, unit


def _build_column_name(
    metric: str | None,
    entity: str | None,
    period: str | None,
) -> str | None:
    """Build column name from metric, entity, and period.

    Args:
        metric: Metric name
        entity: Entity name
        period: Period string

    Returns:
        Column name or None
    """
    if metric and entity and period:
        return f"{metric}_{entity}_{period}"
    elif metric and entity:
        return f"{metric}_{entity}"
    else:
        return None


def _extract_data_cells_to_rows(
    data_cells: list,
    column_mapping: dict[int, tuple[str | None, str | None]],
    row_metric_map: dict[int, str],
    row_unit_map: dict[int, str],
    column_unit_map: dict[int, str | None],
    col_unit_map_normal: dict[int, str],
    page_number: int,
    table_index: int,
    document_id: str,
    caption: str | None,
    table_item: TableItem,
    result: ConversionResult,
) -> list[dict[str, Any]]:
    """Extract data cells into structured rows.

    Args:
        data_cells: List of data cells to process
        column_mapping: Maps col_idx → (entity, period)
        row_metric_map: Maps row_idx → metric_name
        row_unit_map: Maps row_idx → unit (for transposed tables)
        column_unit_map: Maps col_idx → unit (from 3rd header row)
        col_unit_map_normal: Maps col_idx → unit (for normal tables)
        page_number: Page number
        table_index: Table index
        document_id: Document filename
        caption: Table caption
        table_item: Docling TableItem
        result: Docling ConversionResult

    Returns:
        List of structured row dictionaries
    """
    from ..core import extract_year, get_table_markdown

    rows: list[dict[str, Any]] = []

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

        # Get unit and value using priority order
        value, unit = _get_unit_and_value(
            cell.text, row_idx, col_idx, row_unit_map, column_unit_map, col_unit_map_normal
        )

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
            "column_name": _build_column_name(metric, cell_entity_transposed, cell_period),
            "chunk_text": get_table_markdown(table_item, result)[:500],
            "document_id": document_id,
            "extraction_method": "transposed_entity_cols_metric_row_labels",
        }

        rows.append(row_dict)

    return rows
