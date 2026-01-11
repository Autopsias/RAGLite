"""Header mapping functions for transposed table layout extraction."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def _check_unit_header_row(
    row_cells: list, unit_patterns: list[str], page_number: int, table_index: int
) -> dict[int, str | None]:
    """Check if a header row contains units and extract them.

    Args:
        row_cells: Cells from the potential unit header row
        unit_patterns: List of unit pattern strings to match
        page_number: Page number for debug logging
        table_index: Table index for debug logging

    Returns:
        Dictionary mapping col_idx → unit, or empty dict if not a unit row
    """
    column_unit_map: dict[int, str | None] = {}

    # DEBUG
    print(f"[DEBUG] Table on page {page_number}, table_index={table_index}")
    print("[DEBUG] Checking for units in 3rd header row")
    print(f"[DEBUG] Number of cells in unit row: {len(row_cells)}")

    # Sample a few cells to check if they look like units
    sample_cells = row_cells[: min(3, len(row_cells))]
    print("[DEBUG] Sample cells (first 3):")
    for i, cell in enumerate(sample_cells):
        print(f"[DEBUG]   Cell {i}: text='{cell.text}' (column {cell.start_col_offset_idx})")

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

    return column_unit_map


def _build_multi_header_mapping(
    headers_by_row: dict[int, list],
    row_levels: list[int],
    page_number: int,
    table_index: int,
) -> tuple[dict[int, tuple[str | None, str | None]], dict[int, str | None]]:
    """Build mappings for multi-header tables (2+ header rows).

    Args:
        headers_by_row: Dictionary mapping row_idx → list of cells
        row_levels: Sorted list of header row indices
        page_number: Page number for logging
        table_index: Table index for logging

    Returns:
        Tuple of (column_mapping, column_unit_map)
    """
    from ..validation import safe_assign_entity

    column_mapping: dict[int, tuple[str | None, str | None]] = {}
    column_unit_map: dict[int, str | None] = {}

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
        column_unit_map = _check_unit_header_row(row_cells, unit_patterns, page_number, table_index)

    return column_mapping, column_unit_map


def _build_single_header_mapping(
    headers_by_row: dict[int, list],
    row_levels: list[int],
    page_number: int,
    table_index: int,
) -> dict[int, tuple[str | None, str | None]]:
    """Build mapping for single header row tables.

    Args:
        headers_by_row: Dictionary mapping row_idx → list of cells
        row_levels: List with single header row index
        page_number: Page number for logging
        table_index: Table index for logging

    Returns:
        Column mapping dict: col_idx → (entity, None)
    """
    from ..validation import safe_assign_entity

    column_mapping: dict[int, tuple[str | None, str | None]] = {}

    # Single header row - assume entities (no periods)
    for cell in headers_by_row[row_levels[0]]:
        col_idx = cell.start_col_offset_idx
        header_entity_raw: str | None = cell.text.strip() if cell.text else None

        # Phase 2: Use safe wrapper function for entity validation
        header_entity = safe_assign_entity(
            header_entity_raw,
            source="standard_layouts_transposed_single_header",
            page_number=page_number,
            table_index=table_index,
            col_idx=col_idx,
        )

        column_mapping[col_idx] = (header_entity, None)

    return column_mapping


def _build_column_header_mapping(
    column_headers: list,
    page_number: int,
    table_index: int,
) -> tuple[dict[int, tuple[str | None, str | None]], dict[int, str | None]]:
    """Build column → (entity, period) and column → unit mappings from headers.

    Args:
        column_headers: List of column header cells
        page_number: Page number for logging
        table_index: Table index for logging

    Returns:
        Tuple of (column_mapping, column_unit_map)
        - column_mapping: Maps col_idx → (entity, period)
        - column_unit_map: Maps col_idx → unit (for 3+ header rows)
    """
    # Build column header mapping by row level
    headers_by_row: dict[int, list] = {}
    for cell in column_headers:
        row_idx = cell.start_row_offset_idx
        if row_idx not in headers_by_row:
            headers_by_row[row_idx] = []
        headers_by_row[row_idx].append(cell)

    row_levels = sorted(headers_by_row.keys())

    # Build mappings based on number of header rows
    if len(row_levels) >= 2:
        return _build_multi_header_mapping(headers_by_row, row_levels, page_number, table_index)
    elif len(row_levels) == 1:
        column_mapping = _build_single_header_mapping(
            headers_by_row, row_levels, page_number, table_index
        )
        return column_mapping, {}
    else:
        # No headers - return empty mappings
        return {}, {}


def _build_row_metric_mapping(first_col_cells: list) -> dict[int, str]:
    """Build row → metric mapping from first column cells.

    Args:
        first_col_cells: List of cells in first column (not headers)

    Returns:
        Dictionary mapping row_idx → metric_name
    """
    row_metric_map: dict[int, str] = {}
    for cell in first_col_cells:
        row_idx = cell.start_row_offset_idx
        # Parse metric name and unit from cell text
        metric_text = cell.text.strip() if cell.text else None
        if metric_text:
            row_metric_map[row_idx] = metric_text

    return row_metric_map
