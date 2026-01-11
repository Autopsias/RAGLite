"""External regressor validation helpers.

Part of technical debt reduction - extract helper functions from external.py
to reduce extract_external_regressor_timeseries() from 112 LOC to <100 LOC.
"""

import math

import pandas as pd

from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesPoint

logger = get_logger(__name__)


def filter_invalid_values(
    series: pd.Series,
    metric: str,
) -> tuple[list[TimeSeriesPoint], int]:
    """Filter NaN and infinite values from series.

    Args:
        series: pandas Series to filter
        metric: Metric name for logging

    Returns:
        Tuple of (filtered TimeSeriesPoint list, filtered_count)
    """
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

    if filtered_count > 0:
        logger.warning(
            "Filtered NaN/Inf values from external regressor",
            extra={"metric": metric, "filtered": filtered_count, "retained": len(points)},
        )

    return points, filtered_count
