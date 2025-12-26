"""Timeseries extraction - External regressor extraction.

Part of Story 8.1 refactoring to split timeseries_extract.py.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from raglite.forecasting.regressor_fetch import fetch_single_regressor
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# External source mappings for timeseries data
# Maps metric names to their external data source configurations
EXTERNAL_SOURCE_MAPPINGS: dict[str, tuple[str, str]] = {
    "ttf_gas_price": ("external_data_points", "ttf_gas"),
    "petcoke_price": ("external_data_points", "petcoke"),
    "api2_coal_price": ("external_data_points", "api2_coal"),
    "co2_eua_price": ("external_data_points", "co2_eua"),
}


async def extract_external_timeseries(
    metric: str,
    min_points: int = 8,
) -> TimeSeriesData | None:
    """Extract time series from external_data_points table.

    Story 6.24: External Data Integration for Forecasting

    Queries external commodity data (TTF Gas, Petcoke/API2 Coal, CO2 EUA)
    from PostgreSQL external_data_points table.

    Args:
        metric: Forecast variable name (e.g., "ttf_gas_price", "petcoke_price")
        min_points: Minimum data points required (default 8)

    Returns:
        TimeSeriesData with extracted points, or None if insufficient data

    Example:
        >>> data = await extract_external_timeseries("ttf_gas_price")
        >>> print(f"{len(data.points)} points from {data.points[0].date}")
    """
    from raglite.shared.clients import get_postgresql_connection

    # Check if metric has external source mapping
    if metric not in EXTERNAL_SOURCE_MAPPINGS:
        logger.warning(f"No external source mapping for metric: {metric}")
        return None

    source_name, metric_name = EXTERNAL_SOURCE_MAPPINGS[metric]

    logger.info(
        "Extracting external time series",
        extra={"metric": metric, "source": source_name, "db_metric": metric_name},
    )

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT edp.date, edp.value, edp.unit
            FROM external_data_points edp
            JOIN external_data_sources eds ON edp.source_id = eds.id
            WHERE eds.source_name = %s
              AND edp.metric_name = %s
              AND edp.deleted_at IS NULL
            ORDER BY edp.date ASC
        """

        cursor.execute(query, (source_name, metric_name))
        rows = cursor.fetchall()

        if len(rows) < min_points:
            logger.warning(
                f"Insufficient external data for {metric}",
                extra={"found": len(rows), "required": min_points},
            )
            return None

        # Convert to TimeSeriesPoint objects
        points = []
        for date_val, value, unit in rows:
            # Convert date to datetime for consistency
            dt = datetime.combine(date_val, datetime.min.time())
            points.append(TimeSeriesPoint(date=dt, value=float(value), label=unit))

        # Story 6.24: Resample daily data to monthly to match SECIL internal data frequency
        # This is critical for consistent forecasting and MAPE comparison
        if len(points) > 50:  # Only resample if we have enough daily data
            import pandas as pd

            df = pd.DataFrame([(p.date, p.value) for p in points], columns=["date", "value"])
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")

            # Resample to month-end, taking the mean
            monthly = df.resample("ME").mean().dropna()

            if len(monthly) >= min_points:
                points = [
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
                        "daily_points": len(rows),
                        "monthly_points": len(points),
                    },
                )

        logger.info(
            "External time series extracted",
            extra={
                "metric": metric,
                "source": source_name,
                "points": len(points),
                "date_range": f"{points[0].date.date()} to {points[-1].date.date()}",
            },
        )

        return TimeSeriesData(
            metric_name=metric,
            points=points,
            interval="monthly",  # Resampled to monthly for consistency
            source_documents=[f"external:{source_name}"],
        )

    except Exception as e:
        logger.error(
            f"Failed to extract external time series for {metric}",
            extra={"error": str(e)},
            exc_info=True,
        )
        return None

    finally:
        cursor.close()


async def extract_external_regressor_timeseries(
    metric: str,
    min_points: int = 6,
) -> TimeSeriesData | None:
    """Extract external regressor as standalone time series for validation.

    Story 6.24.4: Enables validation of external-only metrics by reusing
    regressor fetch logic. This bridges the gap between regressor system
    and validation system.

    Args:
        metric: Regressor name (e.g., "euribor_3m", "diesel", "gdp_growth")
        min_points: Minimum data points required (default 6)

    Returns:
        TimeSeriesData with points, or None if insufficient data

    Example:
        >>> data = await extract_external_regressor_timeseries("euribor_3m")
        >>> print(f"{len(data.points)} points from {data.points[0].date}")

    Note:
        All external regressors are assumed to be monthly frequency.
        NaN and infinite values are filtered out during conversion.
    """
    import math
    from datetime import timedelta

    try:
        # Fetch last 5 years of data (sufficient for forecasting validation)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=int(365.25 * 5))  # Accounts for leap years

        logger.info(
            "Fetching external regressor as time series",
            extra={"metric": metric, "start_date": start_date, "end_date": end_date},
        )

        # Use regressor fetch infrastructure
        series = await fetch_single_regressor(metric, start_date, end_date)

        if series is None or len(series) == 0:
            logger.warning(
                "No data returned for external metric",
                extra={"metric": metric, "points": len(series) if series is not None else 0},
            )
            return None

        if len(series) < min_points:
            logger.warning(
                "Insufficient data for external metric",
                extra={"metric": metric, "points": len(series), "min_required": min_points},
            )
            return None

        # Convert pandas Series to TimeSeriesData, filtering NaN/Inf values
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

        if len(points) < min_points:
            logger.warning(
                "Insufficient valid data after filtering for external metric",
                extra={"metric": metric, "valid_points": len(points), "min_required": min_points},
            )
            return None

        logger.info(
            "Extracted time series for external regressor",
            extra={
                "metric": metric,
                "points": len(points),
                "date_range": f"{points[0].date.date()} to {points[-1].date.date()}",
            },
        )

        return TimeSeriesData(
            metric_name=metric,
            points=points,
            interval="monthly",  # External regressors are monthly
            source_documents=[f"external:{metric}"],
        )

    except Exception as e:
        logger.error(
            "Failed to extract external regressor time series",
            extra={"metric": metric, "error": str(e)},
            exc_info=True,
        )
        return None
