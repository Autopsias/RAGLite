"""Field assignment functions for orientation-aware table extraction.

This module contains logic for assigning entity, metric, period, and fiscal_year
fields based on detected table orientation and header classification.
"""

from __future__ import annotations

import logging

from ..classification import HeaderType, classify_header
from .processing import extract_year

logger = logging.getLogger(__name__)


def _assign_for_known_orientation(
    orientation: str,
    col_header: str | None,
    row_header: str | None,
    caption_period: str | None,
    caption_year: str | None,
) -> tuple[str | None, str | None, str | None, str | None, str] | None:
    """Assign fields for known table orientations.

    Args:
        orientation: Detected table orientation
        col_header: Column header text
        row_header: Row header text
        caption_period: Period from caption
        caption_year: Year from caption

    Returns:
        Tuple of (entity, metric, period, fiscal_year, confidence) or None if unknown orientation
    """
    if orientation == "temporal_rows_entity_cols":
        # Dates in rows, entities in columns
        fiscal_year = extract_year(row_header)
        return (
            col_header,  # entity
            None,  # metric
            row_header,  # period
            str(fiscal_year) if fiscal_year is not None else None,  # fiscal_year
            "high",  # confidence
        )

    if orientation == "metric_rows_temporal_cols":
        # Metrics in rows, periods in columns
        fiscal_year = extract_year(col_header)
        return (
            None,  # entity
            row_header,  # metric
            col_header,  # period
            str(fiscal_year) if fiscal_year is not None else None,  # fiscal_year
            "high",  # confidence
        )

    if orientation == "metric_rows_entity_cols":
        # Metrics in rows, entities in columns
        return (
            col_header,  # entity
            row_header,  # metric
            caption_period,  # period
            caption_year,  # fiscal_year
            "high",  # confidence
        )

    if orientation == "entity_rows_metric_cols":
        # Entities in rows, metrics in columns
        return (
            row_header,  # entity
            col_header,  # metric
            caption_period,  # period
            caption_year,  # fiscal_year
            "high",  # confidence
        )

    if orientation == "entity_rows_temporal_cols":
        # Entities in rows, periods in columns
        fiscal_year = extract_year(col_header)
        return (
            row_header,  # entity
            None,  # metric
            col_header,  # period
            str(fiscal_year) if fiscal_year is not None else None,  # fiscal_year
            "high",  # confidence
        )

    if orientation == "temporal_rows_temporal_cols":
        # Both temporal - row as period, column as comparison
        period = row_header
        if col_header:
            period = f"{row_header} {col_header}" if row_header else col_header
        fiscal_year = extract_year(row_header)
        return (
            None,  # entity
            None,  # metric
            period,  # period
            str(fiscal_year) if fiscal_year is not None else None,  # fiscal_year
            "medium",  # confidence
        )

    return None  # Unknown orientation


def _assign_for_unknown_orientation(
    col_header: str | None,
    row_header: str | None,
    caption_period: str | None,
    caption_year: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Assign fields using classification-based fallback for unknown orientations.

    Args:
        col_header: Column header text
        row_header: Row header text
        caption_period: Period from caption
        caption_year: Year from caption

    Returns:
        Tuple of (entity, metric, period, fiscal_year)
    """
    entity = None
    metric = None
    period = None
    fiscal_year = None

    # Classify headers
    col_type = classify_header(col_header) if col_header else HeaderType.UNKNOWN
    row_type = classify_header(row_header) if row_header else HeaderType.UNKNOWN

    # Column-based assignment
    if col_type == HeaderType.ENTITY:
        entity = col_header
    elif col_type == HeaderType.METRIC:
        metric = col_header
    elif col_type == HeaderType.TEMPORAL:
        period = col_header
        year = extract_year(col_header)
        fiscal_year = str(year) if year is not None else None

    # Row-based assignment (only if not set by column)
    if row_type == HeaderType.ENTITY and not entity:
        entity = row_header
    elif row_type == HeaderType.METRIC and not metric:
        metric = row_header
    elif row_type == HeaderType.TEMPORAL and not period:
        period = row_header
        year = extract_year(row_header)
        fiscal_year = str(year) if year is not None else None

    # Last resort: use caption
    if not period and caption_period:
        period = caption_period
        fiscal_year = caption_year

    return entity, metric, period, fiscal_year


def _assign_fields_by_orientation(
    orientation: str,
    col_header: str | None,
    row_header: str | None,
    caption_period: str | None,
    caption_year: str | None,
) -> tuple[str | None, str | None, str | None, str | None, str]:
    """Assign entity, metric, period, fiscal_year based on table orientation.

    Args:
        orientation: Detected table orientation
        col_header: Column header text
        row_header: Row header text
        caption_period: Period from caption
        caption_year: Year from caption

    Returns:
        Tuple of (entity, metric, period, fiscal_year, confidence)
    """
    # Try known orientation patterns first
    result = _assign_for_known_orientation(
        orientation, col_header, row_header, caption_period, caption_year
    )

    if result:
        return result

    # Fallback to classification-based assignment
    entity, metric, period, fiscal_year = _assign_for_unknown_orientation(
        col_header, row_header, caption_period, caption_year
    )

    return entity, metric, period, fiscal_year, "low"
