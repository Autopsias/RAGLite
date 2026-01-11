"""Regressor data filtering helpers (Story 8.1).

This module contains filtering logic for cleaning external regressor data.
"""

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from raglite.shared.models import TimeSeriesPoint

from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesPoint

logger = get_logger(__name__)


def filter_invalid_values(
    series_items: list[tuple],
    metric: str,
) -> tuple[list[TimeSeriesPoint], int]:
    """Filter NaN and infinite values from external regressor data.

    Args:
        series_items: List of (index, value) tuples from pandas Series
        metric: Metric name for logging

    Returns:
        Tuple of (filtered_points, filtered_count)

    Example:
        >>> items = [(idx1, 1.0), (idx2, float('nan')), (idx3, 3.0)]
        >>> points, count = filter_invalid_values(items, "test_metric")
        >>> print(f"Filtered {count} invalid values")
    """
    points = []
    filtered_count = 0

    for idx, val in series_items:
        # Filter out NaN and infinite values (Issue #4 fix)
        if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
            filtered_count += 1
            logger.debug(
                "Filtered invalid value from external regressor",
                extra={"metric": metric, "date": idx, "value": val},
            )
            continue

        points.append(
            TimeSeriesPoint(
                date=idx.to_pydatetime(),
                value=float(val),
                label=f"{metric}_{idx.strftime('%Y-%m')}",
            )
        )

    if filtered_count > 0:
        logger.warning(
            "Filtered NaN/Inf values from external regressor",
            extra={"metric": metric, "filtered": filtered_count, "retained": len(points)},
        )

    return points, filtered_count


def validate_filtered_points(
    points: list[TimeSeriesPoint],
    metric: str,
    min_points: int,
) -> bool:
    """Validate that filtered data has sufficient points.

    Args:
        points: Filtered TimeSeriesPoint list
        metric: Metric name for logging
        min_points: Minimum required points

    Returns:
        True if sufficient points, False otherwise

    Example:
        >>> if not validate_filtered_points(points, "test_metric", 6):
        ...     print("Insufficient data after filtering")
    """
    if len(points) < min_points:
        logger.warning(
            "Insufficient valid data after filtering for external metric",
            extra={"metric": metric, "valid_points": len(points), "min_required": min_points},
        )
        return False

    return True
