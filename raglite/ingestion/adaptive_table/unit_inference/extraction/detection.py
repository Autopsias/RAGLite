"""Statistical unit column detection strategies.

This module provides production-grade statistical detection for identifying
unit columns in financial tables, replacing flawed positional sampling approaches.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Extended unit patterns for fallback detection
_EXTENDED_PATTERNS = [
    "million",
    "billion",
    "thousand",
    "M€",
    "k€",
    "bn",
    "mn",
    "ratio",
    "rate",
    "percentage",
    "pct",
    "pts",
    "bps",
    "basis points",
    "people",
    "FTE",
    "headcount",
    "employees",
    "staff",
    "hours",
    "days",
    "months",
    "years",
    "weeks",
]


def _validate_sample_size(cells: list, min_samples: int) -> tuple[bool, list]:
    """Validate that sufficient non-empty cells exist for analysis.

    Args:
        cells: List of cells to validate
        min_samples: Minimum number of cells required

    Returns:
        Tuple of (is_valid, non_empty_cells)
    """
    non_empty_cells = [cell for cell in cells if cell.text and cell.text.strip()]

    if len(non_empty_cells) < min_samples:
        logger.debug(
            "Insufficient samples for unit detection",
            extra={"cell_count": len(non_empty_cells), "min_required": min_samples},
        )
        return False, []

    return True, non_empty_cells


def _detect_by_statistical_threshold(
    cells: list, unit_patterns: list[str], threshold: float
) -> tuple[bool, float, list]:
    """Detect units using primary statistical analysis across all cells.

    Args:
        cells: List of non-empty cells to analyze
        unit_patterns: List of unit pattern strings to match
        threshold: Minimum ratio of cells with units

    Returns:
        Tuple of (detected: bool, confidence: float, matching_cells: list)
    """
    cells_with_units = [
        cell for cell in cells if any(pattern in cell.text for pattern in unit_patterns)
    ]

    unit_ratio = len(cells_with_units) / len(cells)

    if unit_ratio >= threshold:
        logger.info(
            "Units detected by statistical threshold",
            extra={
                "threshold": threshold,
                "ratio": round(unit_ratio, 3),
                "matching_cells": len(cells_with_units),
                "total_cells": len(cells),
            },
        )
        return True, unit_ratio, cells_with_units

    return False, unit_ratio, []


def _detect_by_middle_section_concentration(
    cells: list, unit_patterns: list[str]
) -> tuple[bool, float]:
    """Detect units based on concentration in middle section (rows 3-10).

    Units often concentrate in middle of table, sparse at edges.

    Args:
        cells: List of non-empty cells to analyze
        unit_patterns: List of unit pattern strings to match

    Returns:
        Tuple of (detected: bool, confidence: float)
    """
    middle_cells = [
        cell
        for cell in cells
        if hasattr(cell, "start_row_offset_idx") and 3 <= cell.start_row_offset_idx <= 10
    ]

    if len(middle_cells) < 3:
        return False, 0.0

    middle_with_units = [
        cell for cell in middle_cells if any(pattern in cell.text for pattern in unit_patterns)
    ]
    middle_ratio = len(middle_with_units) / len(middle_cells)

    if middle_ratio >= 0.70:  # 70% in middle section
        confidence = 0.50 + (middle_ratio * 0.30)  # 0.50-0.80 confidence range
        logger.info(
            "Units detected by middle section concentration",
            extra={
                "ratio": round(middle_ratio, 3),
                "confidence": round(confidence, 3),
                "middle_cells": len(middle_cells),
            },
        )
        return True, confidence

    return False, 0.0


def _detect_by_extended_patterns(cells: list) -> tuple[bool, float]:
    """Detect units using extended verbal unit indicators.

    Checks for verbal unit indicators that might be missed by
    standard patterns (e.g., "million", "people", "FTE").

    Args:
        cells: List of non-empty cells to analyze

    Returns:
        Tuple of (detected: bool, confidence: float)
    """
    extended_matches = [
        cell
        for cell in cells
        if any(pattern.lower() in cell.text.lower() for pattern in _EXTENDED_PATTERNS)
    ]

    extended_ratio = len(extended_matches) / len(cells)

    if extended_ratio >= 0.50:  # 50% threshold for extended patterns
        confidence = 0.30 + (extended_ratio * 0.30)  # 0.30-0.60 confidence range
        logger.info(
            "Units detected by extended patterns",
            extra={
                "ratio": round(extended_ratio, 3),
                "confidence": round(confidence, 3),
                "matching_cells": len(extended_matches),
            },
        )
        return True, confidence

    return False, 0.0
