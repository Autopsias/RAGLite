"""Helper functions for external regressor timeseries extraction.

Part of Story 8.1 refactoring to split timeseries_extract.py.
Extracted from external.py to reduce function length.
"""

import math
from typing import TYPE_CHECKING

import pandas as pd

from raglite.shared.models import TimeSeriesPoint

if TYPE_CHECKING:
    pass


def convert_series_to_timeseries_points(
    series: pd.Series,
    metric: str,
) -> tuple[list[TimeSeriesPoint], int]:
    """Convert pandas Series to TimeSeriesPoint objects, filtering NaN/Inf.

    Args:
        series: pandas Series with datetime index
        metric: Metric name for labels

    Returns:
        Tuple of (points list, filtered count)
    """
    from raglite.shared.logging import get_logger

    logger = get_logger(__name__)

    points = []
    filtered_count = 0
    for idx, val in series.items():
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

    return points, filtered_count


def validate_regressor_data(
    series: pd.Series | None,
    points: list[TimeSeriesPoint],
    metric: str,
    min_points: int,
    filtered_count: int,
) -> bool:
    """Validate external regressor data has sufficient valid points.

    Args:
        series: Original pandas Series
        points: Filtered TimeSeriesPoint list
        metric: Metric name for logging
        min_points: Minimum required points
        filtered_count: Number of filtered invalid values

    Returns:
        True if sufficient data, False otherwise
    """
    from raglite.shared.logging import get_logger

    logger = get_logger(__name__)

    # Check if series is None or empty
    if series is None or len(series) == 0:
        logger.warning(
            "No data returned for external metric",
            extra={"metric": metric, "points": len(series) if series is not None else 0},
        )
        return False

    # Check if we have enough points before filtering
    if len(series) < min_points:
        logger.warning(
            "Insufficient data for external metric",
            extra={"metric": metric, "points": len(series), "min_required": min_points},
        )
        return False

    # Log if we filtered any invalid values
    if filtered_count > 0:
        logger.warning(
            "Filtered NaN/Inf values from external regressor",
            extra={"metric": metric, "filtered": filtered_count, "retained": len(points)},
        )

    # Check if we have enough points after filtering
    if len(points) < min_points:
        logger.warning(
            "Insufficient valid data after filtering for external metric",
            extra={"metric": metric, "valid_points": len(points), "min_required": min_points},
        )
        return False

    return True
