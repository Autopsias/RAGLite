"""Unit extraction functions for transposed table layout."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _get_unit_patterns() -> list[str]:
    """Get list of unit patterns for detection.

    Returns:
        List of unit pattern strings
    """
    return [
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


def _extract_units_type_a_transposed(
    table_cells: list,
    unit_patterns: list[str],
    page_number: int,
    table_index: int,
    orientation_confidence: float,
) -> tuple[dict[int, str], list]:
    """Extract units for Type A (transposed_metric) tables.

    Args:
        table_cells: List of all table cells
        unit_patterns: Unit pattern strings
        page_number: Page number for logging
        table_index: Table index for logging
        orientation_confidence: Orientation detection confidence

    Returns:
        Tuple of (row_unit_map, data_cells)
    """
    from ..unit_inference import _detect_unit_column_statistical

    row_unit_map: dict[int, str] = {}

    col_1_cells = [
        cell for cell in table_cells if cell.start_col_offset_idx == 1 and not cell.column_header
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

        # Exclude column 1 (contains units, not data)
        data_cells = [
            cell for cell in table_cells if not cell.column_header and cell.start_col_offset_idx > 1
        ]
    else:
        # No units in column 1, use default data cells
        data_cells = [
            cell for cell in table_cells if not cell.column_header and cell.start_col_offset_idx > 0
        ]

    return row_unit_map, data_cells


def _extract_units_fallback(
    table_cells: list,
    unit_patterns: list[str],
    page_number: int,
    table_index: int,
    orientation_confidence: float,
) -> tuple[dict[int, str], list]:
    """Extract units using fallback strategy for unknown orientation.

    Args:
        table_cells: List of all table cells
        unit_patterns: Unit pattern strings
        page_number: Page number for logging
        table_index: Table index for logging
        orientation_confidence: Orientation detection confidence

    Returns:
        Tuple of (row_unit_map, data_cells)
    """
    from ..unit_inference import _detect_unit_column_statistical

    row_unit_map: dict[int, str] = {}

    logger.warning(
        f"Unknown orientation (confidence={orientation_confidence:.3f}) - using fallback",
        extra={"page_number": page_number, "table_index": table_index},
    )

    col_1_cells = [
        cell for cell in table_cells if cell.start_col_offset_idx == 1 and not cell.column_header
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
            cell for cell in table_cells if not cell.column_header and cell.start_col_offset_idx > 1
        ]
    else:
        data_cells = [
            cell for cell in table_cells if not cell.column_header and cell.start_col_offset_idx > 0
        ]

    return row_unit_map, data_cells


def _detect_and_extract_units(
    table_cells: list,
    num_rows: int,
    num_cols: int,
    page_number: int,
    table_index: int,
) -> tuple[str, float, dict[int, str], dict[int, str], list]:
    """Detect table orientation and extract units using appropriate strategy.

    Args:
        table_cells: List of all table cells
        num_rows: Number of rows
        num_cols: Number of columns
        page_number: Page number for logging
        table_index: Table index for logging

    Returns:
        Tuple of (orientation, confidence, row_unit_map, col_unit_map_normal, data_cells)
    """
    from ..classification import _detect_table_orientation
    from ..unit_inference import _extract_units_entity_column_junk, _extract_units_normal

    unit_patterns = _get_unit_patterns()

    # Step 1: Detect table orientation
    orientation, orientation_confidence = _detect_table_orientation(
        table_cells, num_rows, num_cols, unit_patterns
    )

    # Step 2: Apply orientation-specific unit extraction strategy
    row_unit_map: dict[int, str] = {}
    col_unit_map_normal: dict[int, str] = {}

    # Initial data cells (exclude first column and headers)
    data_cells = [
        cell for cell in table_cells if not cell.column_header and cell.start_col_offset_idx > 0
    ]

    if orientation == "transposed_metric":
        # TYPE A: Transposed Metric-Entity (metrics in col 0, units in col 1)
        row_unit_map, data_cells = _extract_units_type_a_transposed(
            table_cells, unit_patterns, page_number, table_index, orientation_confidence
        )

    elif orientation == "entity_column_junk":
        # TYPE B: Entity-Column with Junk Column 0
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
        # UNKNOWN ORIENTATION: Fall back to transposed strategy
        row_unit_map, data_cells = _extract_units_fallback(
            table_cells, unit_patterns, page_number, table_index, orientation_confidence
        )

    return orientation, orientation_confidence, row_unit_map, col_unit_map_normal, data_cells
