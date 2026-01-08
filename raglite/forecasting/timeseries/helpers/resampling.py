"""Time series resampling helpers (Story 8.1).

This module contains resampling logic for converting daily data to monthly.
"""

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def resample_daily_to_monthly(
    points: list,
    metric: str,
    min_points: int,
) -> tuple[list, bool]:
    """Resample daily time series data to monthly frequency.

    Story 6.24: Resample daily data to monthly to match SECIL internal
    data frequency. This is critical for consistent forecasting and MAPE
    comparison.

    Args:
        points: List of TimeSeriesPoint objects with daily data
        metric: Metric name for logging
        min_points: Minimum points required after resampling

    Returns:
        Tuple of (resampled_points, success_flag)

    Example:
        >>> from raglite.shared.models import TimeSeriesPoint
        >>> points = [TimeSeriesPoint(...), ...]
        >>> monthly, success = resample_daily_to_monthly(points, "ttf_gas_price", 6)
        >>> if success:
        ...     print(f"Resampled to {len(monthly)} monthly points")
    """
    if len(points) <= 50:
        # Not enough daily data to resample
        return points, False

    import pandas as pd

    from raglite.shared.logging import get_logger
    from raglite.shared.models import TimeSeriesPoint

    logger = get_logger(__name__)

    df = pd.DataFrame([(p.date, p.value) for p in points], columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    # Resample to month-end, taking the mean
    monthly = df.resample("ME").mean().dropna()

    if len(monthly) < min_points:
        return points, False

    resampled_points = [
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
            "monthly_points": len(resampled_points),
        },
    )

    return resampled_points, True
