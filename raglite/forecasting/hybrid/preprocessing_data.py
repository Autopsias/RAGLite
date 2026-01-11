"""Data fetching utilities for preprocessing.

Part of Story 8.1 refactoring to reduce preprocessing.py file size.

Provides historical data fetching from PostgreSQL external data storage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.shared.models import TimeSeriesData as TimeSeriesDataType

from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesPoint

logger = get_logger(__name__)


async def fetch_historical_metric(
    metric: str,
    storage: ExternalDataStorage | None = None,
) -> TimeSeriesDataType | None:
    """Fetch historical time-series from PostgreSQL external data.

    Story 6.3 AC6: Data fetching from PostgreSQL.
    Story 8.5: Updated to return TimeSeriesData object for type consistency.

    Args:
        metric: Metric name to fetch
        storage: Optional ExternalDataStorage instance

    Returns:
        TimeSeriesData object with historical points, or None if not found

    Raises:
        ValueError: If metric not found or no data available
    """
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.shared.database import get_session
    from raglite.shared.models import TimeSeriesData

    if storage is None:
        session = get_session()
        storage = ExternalDataStorage(session)

    # Try to find a source containing this metric
    sources = storage.list_sources()
    for source in sources:
        source_name = str(source.source_name)  # Cast for mypy
        metrics = storage.get_metrics_for_source(source_name)
        if metric in metrics:
            # Query all data for this metric
            from datetime import date, timedelta

            end_date = date.today()
            start_date = end_date - timedelta(days=5 * 365)  # 5 years

            points = storage.query_data_range(
                source_name,
                start_date,
                end_date,
                metric_name=metric,
            )

            if points:
                # Convert ORM objects to TimeSeriesPoint objects
                from datetime import datetime as dt

                ts_points = [
                    TimeSeriesPoint(
                        date=dt.combine(p.date, dt.min.time()),  # Convert date to datetime
                        value=float(p.value),  # Convert Decimal to float
                    )
                    for p in points
                ]
                # Convert to TimeSeriesData object
                return TimeSeriesData(
                    metric_name=metric,
                    points=ts_points,
                    interval="unknown",  # Will be inferred from data
                    source_documents=[source_name],
                )

    raise ValueError(f"Metric '{metric}' not found in external data sources")


async def ensure_historical_data(
    metric: str, historical_data: TimeSeriesDataType | None, logger_instance: Any = None
) -> TimeSeriesDataType:
    """Ensure historical data is available, fetching from storage if needed.

    Story 8.5: Extracted from ensemble.py to reduce file size.

    Args:
        metric: Metric name for fetching
        historical_data: Existing TimeSeriesData or None
        logger_instance: Logger instance for logging

    Returns:
        TimeSeriesData object

    Raises:
        InsufficientDataError: If no data available
    """
    from raglite.forecasting.models.base import InsufficientDataError

    if historical_data is None:
        if logger_instance:
            logger_instance.info(f"Fetching historical data for metric: {metric}")
        historical_data = await fetch_historical_metric(metric)
        if historical_data is None:
            raise InsufficientDataError(
                f"No historical data available for metric '{metric}' in PostgreSQL. "
                "Either provide historical_data parameter or ensure data is ingested."
            )
    return historical_data
