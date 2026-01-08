"""Resampling helpers for external timeseries data.

Part of Story 8.1 refactoring to split timeseries_extract.py.
Extracted from external.py to reduce function length.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from raglite.shared.models import TimeSeriesPoint

if TYPE_CHECKING:
    pass


def resample_daily_to_monthly(
    points: list[TimeSeriesPoint],
    metric: str,
    min_points: int,
) -> list[TimeSeriesPoint] | None:
    """Resample daily data points to monthly frequency.

    Story 6.24: Resample daily data to monthly to match SECIL internal data frequency.
    This is critical for consistent forecasting and MAPE comparison.

    Args:
        points: Daily TimeSeriesPoint objects
        metric: Metric name for logging
        min_points: Minimum points required after resampling

    Returns:
        Monthly TimeSeriesPoint objects, or None if insufficient data
    """
    import pandas as pd

    from raglite.shared.logging import get_logger

    logger = get_logger(__name__)

    if len(points) <= 50:
        # Not enough daily data to resample
        return points

    df = pd.DataFrame([(p.date, p.value) for p in points], columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    # Resample to month-end, taking the mean
    monthly = df.resample("ME").mean().dropna()

    if len(monthly) < min_points:
        logger.warning(
            "Insufficient data after resampling to monthly",
            extra={
                "metric": metric,
                "daily_points": len(points),
                "monthly_points": len(monthly),
                "min_required": min_points,
            },
        )
        return None

    monthly_points = [
        TimeSeriesPoint(
            date=datetime.combine(idx.date(), datetime.min.time()),
            value=float(row["value"]),
            label="monthly_avg",
        )
        for idx, row in monthly.iterrows()
    ]

    logger.info(
        "Resampled external data from daily to monthly",
        extra={
            "metric": metric,
            "daily_points": len(points),
            "monthly_points": len(monthly_points),
        },
    )

    return monthly_points
