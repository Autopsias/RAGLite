"""Transposed layout extraction functions.

This module handles tables with:
- Entities in column headers
- Metrics in first column (row labels)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem

# Re-export functions from submodules for backward compatibility
from .data_extraction import _build_column_name, _extract_data_cells_to_rows, _get_unit_and_value
from .header_mapping import (
    _build_column_header_mapping,
    _build_multi_header_mapping,
    _build_row_metric_mapping,
    _build_single_header_mapping,
    _check_unit_header_row,
)
from .unit_extraction import (
    _detect_and_extract_units,
    _extract_units_fallback,
    _extract_units_type_a_transposed,
    _get_unit_patterns,
)


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
    from ..core import get_table_caption

    # Extract cell groups
    column_headers = [cell for cell in table_cells if cell.column_header]
    first_col_cells = [
        cell for cell in table_cells if cell.start_col_offset_idx == 0 and not cell.column_header
    ]

    # Build column mapping (entity, period) and unit mapping
    column_mapping, column_unit_map = _build_column_header_mapping(
        column_headers, page_number, table_index
    )

    # Build row → metric mapping from first column
    row_metric_map = _build_row_metric_mapping(first_col_cells)

    # Detect orientation and extract units
    (
        orientation,
        orientation_confidence,
        row_unit_map,
        col_unit_map_normal,
        data_cells,
    ) = _detect_and_extract_units(table_cells, num_rows, num_cols, page_number, table_index)

    # Extract data cells into structured rows
    caption = get_table_caption(table_item)
    rows = _extract_data_cells_to_rows(
        data_cells,
        column_mapping,
        row_metric_map,
        row_unit_map,
        column_unit_map,
        col_unit_map_normal,
        page_number,
        table_index,
        document_id,
        caption,
        table_item,
        result,
    )

    return rows


# Export all public functions for backward compatibility
__all__ = [
    "_extract_transposed_entity_cols_metric_row_labels",
    "_build_column_header_mapping",
    "_build_multi_header_mapping",
    "_build_row_metric_mapping",
    "_build_single_header_mapping",
    "_check_unit_header_row",
    "_detect_and_extract_units",
    "_extract_units_fallback",
    "_extract_units_type_a_transposed",
    "_get_unit_patterns",
    "_get_unit_and_value",
    "_build_column_name",
    "_extract_data_cells_to_rows",
]
