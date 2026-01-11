"""Weekly backtest job for adaptive weight calculation.

Story 6.12 AC3: Scheduled backtest (weekly Sunday 03:00 UTC) that:
1. Retrieves all registered metrics from PostgreSQL
2. Runs rolling backtest for each metric
3. Calculates and stores adaptive weights

The job runs after the weekly data refresh (06:00 UTC) to ensure fresh data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from raglite.shared.config import settings
from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.shared.models import TimeSeriesData

logger = get_logger(__name__)

# List of known metrics to backtest (from time-series extraction)
KNOWN_METRICS = [
    "cement_demand",
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
]


async def run_weekly_backtest() -> dict[str, int]:
    """Run weekly backtest job for all registered metrics.

    Story 6.12 AC3: Scheduled backtest that calculates adaptive weights.

    This function:
    1. Retrieves historical time-series data for each known metric from PostgreSQL
    2. Runs rolling backtest (75% train, 25% test)
    3. Calculates weights from backtest RMSE using inverse-RMSE formula
    4. Stores weights in PostgreSQL model_weights table with caps (5-50%)

    Returns:
        Dict with metrics_processed count and weights_updated count
    """
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.shared.database import get_session

    logger.info("Starting weekly backtest job")

    session = get_session()
    storage = ExternalDataStorage(session)

    metrics_processed = 0
    weights_updated = 0

    try:
        for metric in KNOWN_METRICS:
            try:
                logger.info(f"Processing backtest for metric: {metric}")

                # Retrieve and validate historical data
                historical_data = await _get_metric_historical_data(metric, storage)
                if not historical_data or not _validate_metric_data(metric, historical_data):
                    continue

                # Get external regressors and run backtest
                external_regressors = await _get_external_regressors(storage)
                results = await _execute_backtest_for_metric(
                    metric, historical_data, external_regressors
                )

                if not results:
                    logger.warning(f"No backtest results for metric: {metric}")
                    continue

                metrics_processed += 1

                # Store results in database
                weights_updated += _store_backtest_results(
                    storage,
                    metric,
                    results,  # type: ignore[arg-type]
                    external_regressors,
                )

                logger.info(
                    f"Backtest completed for {metric}",
                    extra={
                        "models": list(results.keys()),
                        "weights_stored": len(results),
                    },
                )

            except Exception as e:
                logger.warning(
                    f"Backtest failed for metric: {metric}",
                    extra={"error": str(e)},
                )
                continue

        logger.info(
            "Weekly backtest job completed",
            extra={
                "metrics_processed": metrics_processed,
                "weights_updated": weights_updated,
            },
        )

    finally:
        session.close()

    return {
        "metrics_processed": metrics_processed,
        "weights_updated": weights_updated,
    }


def _validate_metric_data(metric: str, historical_data: object | None) -> bool:
    """Validate that metric has sufficient historical data for backtest.

    Args:
        metric: Metric name
        historical_data: TimeSeriesData object or None

    Returns:
        True if data is sufficient, False otherwise
    """
    min_points = 12

    if historical_data is None or (
        hasattr(historical_data, "points") and len(historical_data.points) < min_points
    ):
        logger.info(
            f"Insufficient data for backtest: {metric}",
            extra={
                "data_points": len(historical_data.points)
                if historical_data and hasattr(historical_data, "points")
                else 0,
                "required": min_points,
            },
        )
        return False

    return True


async def _execute_backtest_for_metric(
    metric: str,
    historical_data: TimeSeriesData,
    external_regressors: dict[str, object] | None,
) -> dict[str, dict[str, float]]:
    """Execute backtest calculation for a single metric.

    Args:
        metric: Metric name
        historical_data: TimeSeriesData for the metric
        external_regressors: Optional external regressor series

    Returns:
        Dict of model results with weights and metrics
    """
    import asyncio

    from raglite.forecasting.adaptive_weights import calculate_backtest_weights

    # Run backtest in thread pool to avoid blocking event loop
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        None,
        calculate_backtest_weights,
        metric,
        historical_data,
        external_regressors,
        None,  # Use default models
    )

    return results


def _store_backtest_results(
    storage: ExternalDataStorage,
    metric: str,
    results: dict[str, dict[str, object]],
    external_regressors: dict[str, object] | None,
) -> int:
    """Store backtest results in model_weights table.

    Args:
        storage: ExternalDataStorage instance
        metric: Metric name
        results: Backtest results from calculate_backtest_weights
        external_regressors: External regressors used in backtest

    Returns:
        Number of weights updated
    """
    weights_updated = 0

    for model_name, model_results in results.items():
        storage.save_model_weight(
            metric_name=metric,
            model_name=model_name,
            weight=float(model_results["weight"]),  # type: ignore[arg-type]
            backtest_rmse=float(model_results["rmse"]) if model_results.get("rmse") else None,  # type: ignore[arg-type]
            backtest_mape=float(model_results["mape"]) if model_results.get("mape") else None,  # type: ignore[arg-type]
            has_regressors=external_regressors is not None and len(external_regressors) > 0,
            data_points=int(float(model_results["data_points"]))  # type: ignore[arg-type]
            if model_results.get("data_points")
            else None,
        )
        weights_updated += 1

    return weights_updated


async def _get_metric_historical_data(
    metric: str,
    storage: ExternalDataStorage,
) -> TimeSeriesData | None:
    """Retrieve historical time-series data for a metric.

    Args:
        metric: Metric name to retrieve
        storage: ExternalDataStorage instance

    Returns:
        TimeSeriesData or None if not available
    """
    from datetime import date, timedelta

    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    # Map metrics to external data sources
    # This mapping should be expanded as more sources are integrated
    metric_source_map = {
        "cement_demand": "ATIC_CementConsumption",
        "revenue": None,  # From internal documents
        "gross_profit": None,
        "operating_income": None,
        "net_income": None,
    }

    source_name = metric_source_map.get(metric)

    if source_name is None:
        # Try to get from internal forecasting cache or time-series extraction
        # For now, return None - internal metrics require document analysis
        return None

    try:
        # Query historical data based on configurable buffer
        end_date = date.today()
        buffer_days = settings.regressor_buffer_years * 365
        start_date = end_date - timedelta(days=buffer_days)

        data_points = storage.query_data_range(
            source_name=source_name,
            start_date=start_date,
            end_date=end_date,
        )

        if not data_points:
            return None

        # Convert to TimeSeriesData
        from datetime import datetime as dt

        points = [
            TimeSeriesPoint(
                date=dt.combine(dp.date, dt.min.time()),  # Convert date to datetime
                value=float(dp.value),
            )
            for dp in data_points
        ]

        return TimeSeriesData(
            metric_name=metric,
            points=points,
        )

    except Exception as e:
        logger.warning(
            f"Failed to retrieve historical data for {metric}",
            extra={"error": str(e)},
        )
        return None


async def _get_external_regressors(
    storage: ExternalDataStorage,
) -> dict[str, pd.Series] | None:
    """Retrieve external regressors for backtest.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        Dict of regressor name -> pandas Series, or None if none available
    """
    from datetime import date, timedelta

    regressors: dict[str, pd.Series] = {}

    # List of external data sources to use as regressors
    regressor_sources = [
        ("OMIE", "price"),  # Electricity prices
        ("IPMA", "temperature"),  # Weather data
    ]

    end_date = date.today()
    buffer_days = settings.regressor_buffer_years * 365
    start_date = end_date - timedelta(days=buffer_days)

    for source_name, metric_name in regressor_sources:
        try:
            data_points = storage.query_data_range(
                source_name=source_name,
                start_date=start_date,
                end_date=end_date,
                metric_name=metric_name,
            )

            if data_points:
                series = pd.Series(
                    [float(dp.value) for dp in data_points],
                    index=pd.DatetimeIndex([dp.date for dp in data_points]),
                    name=f"{source_name}_{metric_name}",
                )
                regressors[f"{source_name}_{metric_name}"] = series

        except Exception as e:
            logger.debug(
                f"Regressor source not available: {source_name}",
                extra={"error": str(e)},
            )
            continue

    return regressors if regressors else None


def run_backtest_for_metric(
    metric: str,
    historical_data: object,
    external_regressors: dict | None = None,
) -> dict[str, dict[str, float]]:
    """Run backtest for a single metric and store weights.

    Story 6.12 AC3: Helper function for single-metric backtest.

    Args:
        metric: Metric name to backtest
        historical_data: TimeSeriesData for the metric
        external_regressors: Optional external regressor series

    Returns:
        Dict of model results with weights
    """
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.forecasting.adaptive_weights import calculate_backtest_weights
    from raglite.shared.database import get_session
    from raglite.shared.models import TimeSeriesData

    if not isinstance(historical_data, TimeSeriesData):
        raise TypeError("historical_data must be TimeSeriesData")

    session = get_session()
    storage = ExternalDataStorage(session)

    try:
        # Calculate weights from backtest
        results = calculate_backtest_weights(
            metric=metric,
            historical_data=historical_data,
            external_regressors=external_regressors,
        )

        # Store weights in PostgreSQL
        for model_name, model_results in results.items():
            storage.save_model_weight(
                metric_name=metric,
                model_name=model_name,
                weight=model_results["weight"],
                backtest_rmse=model_results.get("rmse"),
                backtest_mape=model_results.get("mape"),
                data_points=int(model_results["data_points"])
                if model_results.get("data_points") is not None
                else None,
            )

        logger.info(
            f"Backtest completed for {metric}",
            extra={"models": list(results.keys())},
        )
        return results

    finally:
        session.close()


async def trigger_backtest_now(metrics: list[str] | None = None) -> dict:
    """Manually trigger backtest job.

    Story 6.12 AC5: Support for manual backtest trigger via MCP admin tool.

    Args:
        metrics: Optional list of metrics to backtest (default: all)

    Returns:
        Dict with results summary
    """
    logger.info(
        "Manual backtest triggered",
        extra={"metrics": metrics or "all"},
    )
    return await run_weekly_backtest()
