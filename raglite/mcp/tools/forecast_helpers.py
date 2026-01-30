"""Helper functions for get_financial_forecast() to reduce function length.

Story 8: Refactoring to reduce get_financial_forecast from 456 to ~150 lines.
Epic 8: Split into modules to comply with <500 LOC limit.
Forecast debug fix (2026-01-28): Added target_year support for year-based forecasting.

These helpers extract cohesive logic blocks while preserving the original algorithm.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from logging import Logger
from typing import TYPE_CHECKING

import pandas as pd

from raglite.external_data.storage import CachedModelSelection, get_cached_model_selection
from raglite.forecasting.extraction_routing import (
    extract_historical_data_by_type,
    resolve_variable_alias,
)
from raglite.forecasting.hybrid import (
    _route_to_model,
    generate_ensemble_forecast,
    generate_forecast,
)
from raglite.forecasting.regressor_config import select_model_type
from raglite.forecasting.timeseries import (
    ExtractionError,
    MetricValidationError,
    extract_timeseries,
)
from raglite.mcp.tools.forecast_helpers_response import (
    build_enhanced_basis,
    build_response,
    handle_forecast_error,
)
from raglite.mcp.tools.query import parse_forecast_query
from raglite.retrieval.search import QueryError
from raglite.shared.models import ForecastQueryRequest, TimeSeriesData

if TYPE_CHECKING:
    from raglite.shared.models import ForecastResult


def parse_and_validate_metric(
    request: ForecastQueryRequest,
    logger: Logger,
) -> tuple[str, int]:
    """Parse natural language query and validate metric.

    Forecast debug fix (2026-01-28): Added support for target_year parameter.
    When target_year is set, periods_ahead is calculated dynamically based on
    last historical data point to cover the full target year.

    Args:
        request: Forecast query request
        logger: Logger instance

    Returns:
        Tuple of (metric, periods_ahead)

    Raises:
        QueryError: If metric cannot be determined
    """
    metric = request.metric
    periods_ahead = request.periods_ahead

    if request.query and not metric:
        parsed_metric, parsed_periods = parse_forecast_query(request.query)
        if parsed_metric:
            metric = parsed_metric
        if parsed_periods:
            periods_ahead = parsed_periods
        logger.info(
            "Parsed natural language query",
            extra={
                "original_query": request.query,
                "parsed_metric": metric,
                "parsed_periods": periods_ahead,
            },
        )

    if not metric:
        error_msg = (
            "Could not determine metric to forecast. Please specify a financial metric "
            "(e.g., revenue, turnover, ebitda, cash_flow, expenses, capex) or rephrase your query."
        )
        logger.warning("Forecast query failed - no metric", extra={"query": request.query})
        raise QueryError(error_msg)

    # Normalize aliases (e.g., "Turnover+VAT" -> "revenue")
    metric = resolve_variable_alias(metric)

    # Forecast debug fix: Handle target_year - periods_ahead will be recalculated
    # after historical data extraction when we know the last data point
    if request.target_year is not None:
        logger.info(
            "Target year specified - periods_ahead will be calculated dynamically",
            extra={
                "target_year": request.target_year,
                "initial_periods_ahead": periods_ahead,
            },
        )
        # Return a placeholder value; actual calculation happens after data extraction
        # Use 12 as a reasonable default for year-based forecasts
        periods_ahead = 12

    return metric, periods_ahead


def calculate_periods_for_target_year(
    target_year: int,
    historical_data: TimeSeriesData,
    logger: Logger,
) -> int:
    """Calculate periods_ahead to reach December of target year.

    Forecast debug fix (2026-01-28): Dynamically calculates the number of periods
    needed to forecast through the end of the specified target year.

    Args:
        target_year: Target year (e.g., 2026)
        historical_data: Historical time-series data with last data point
        logger: Logger instance

    Returns:
        Number of periods to forecast to reach December of target_year

    Example:
        If last data point is Nov-2025 and target_year=2026:
        - Dec-2025, Jan-2026, Feb-2026, ... Dec-2026 = 13 periods
    """
    if not historical_data.points:
        logger.warning("No historical data points, using default 12 periods")
        return 12

    # Find last historical data point
    last_point = max(historical_data.points, key=lambda p: p.date)
    last_date = last_point.date

    # Target is December of the target year
    target_date = datetime(target_year, 12, 1)

    # Calculate months between last date and target
    months_diff = (target_date.year - last_date.year) * 12 + (target_date.month - last_date.month)

    # Clamp to valid range (1-18)
    periods_ahead = max(1, min(18, months_diff))

    logger.info(
        "Calculated periods_ahead from target_year",
        extra={
            "target_year": target_year,
            "last_historical_date": last_date.strftime("%Y-%m-%d"),
            "target_date": target_date.strftime("%Y-%m-%d"),
            "calculated_periods": periods_ahead,
        },
    )

    return periods_ahead


async def extract_historical_data(
    metric: str,
    logger: Logger,
) -> TimeSeriesData:
    """Extract historical time-series data.

    Story 5.0.1: SQL-first with fallback to hybrid search.

    Args:
        metric: Metric name
        logger: Logger instance

    Returns:
        TimeSeriesData with historical points

    Raises:
        MetricValidationError: If metric validation fails
        ExtractionError: If extraction fails
    """
    logger.info("Extracting time-series data", extra={"metric": metric})

    try:
        logger.info(
            "Attempting type-routed extraction",
            extra={"metric": metric, "method": "type_routed"},
        )
        historical_data = await extract_historical_data_by_type(metric=metric, min_points=6)
        if historical_data is None:
            raise ExtractionError(f"Type-routed extraction returned None for {metric}")
        logger.info(
            "Type-routed extraction successful",
            extra={
                "metric": metric,
                "data_points": len(historical_data.points),
                "method": "type_routed",
            },
        )
        return historical_data
    except MetricValidationError:
        raise
    except ExtractionError as e:
        logger.warning(
            "SQL extraction failed, falling back to hybrid search",
            extra={
                "metric": metric,
                "reason": str(e),
                "fallback_method": "hybrid_search",
            },
        )
        historical_data = await extract_timeseries(docs=[], metric=metric)
        logger.info(
            "Hybrid search extraction successful",
            extra={
                "metric": metric,
                "data_points": len(historical_data.points),
                "source_docs": len(historical_data.source_documents),
                "method": "hybrid_search_fallback",
            },
        )
        return historical_data


async def fetch_external_regressors(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    regressor_names: list[str] | None,
    logger: Logger,
) -> tuple[dict[str, pd.Series] | None, list[str]]:
    """Fetch external regressors for the metric.

    Args:
        metric: Metric name
        historical_data: Historical time-series data
        periods_ahead: Number of periods to forecast
        regressor_names: Optional specific regressor names to fetch
        logger: Logger instance

    Returns:
        Tuple of (external_regressors dict, regressors_used list)
    """
    try:
        from raglite.forecasting.regressor_fetch import fetch_regressors_for_metric

        if historical_data.points:
            historical_dates = [
                p.date.date() if hasattr(p.date, "date") else p.date for p in historical_data.points
            ]
            start_date = min(historical_dates) - timedelta(days=365)
            end_date = max(historical_dates) + timedelta(days=30 * periods_ahead)
            external_regressors = await fetch_regressors_for_metric(
                metric=metric,
                start_date=start_date,
                end_date=end_date,
                regressor_names=regressor_names,
            )
            regressors_used = list(external_regressors.keys())
            logger.info(
                "External regressors fetched",
                extra={
                    "metric": metric,
                    "regressors": regressors_used,
                    "count": len(regressors_used),
                },
            )
            return external_regressors, regressors_used
    except Exception as e:
        logger.warning(
            "External regressor fetch failed, falling back to univariate",
            extra={"metric": metric, "error": str(e)},
        )

    return None, []


def check_model_selection_cache_for_forecast(
    metric: str,
    logger: Logger,
) -> CachedModelSelection | None:
    """Check model selection cache.

    Args:
        metric: Metric name
        logger: Logger instance

    Returns:
        CachedModelSelection if valid cache hit, None otherwise
    """
    try:
        cached_selection = get_cached_model_selection(metric)
        if cached_selection and not cached_selection.is_expired:
            logger.info(
                "Using cached model selection",
                extra={
                    "metric": metric,
                    "best_model": cached_selection.best_model,
                    "best_mase": cached_selection.best_mase,
                    "use_regressors": cached_selection.use_regressors,
                    "regressor_count": len(cached_selection.regressor_list),
                },
            )
            return cached_selection
        else:
            logger.debug(
                "Model selection cache miss or expired",
                extra={"metric": metric},
            )
    except Exception as e:
        logger.warning(
            "Error checking model selection cache, using fallback",
            extra={"metric": metric, "error": str(e)},
        )
    return None


async def generate_forecast_with_cache(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    cached_selection: CachedModelSelection,
    external_regressors: dict[str, pd.Series] | None,
    logger: Logger,
) -> tuple[ForecastResult, str, str, list[str]]:
    """Generate forecast using cached model selection.

    Args:
        metric: Metric name
        historical_data: Historical time-series data
        periods_ahead: Number of periods to forecast
        cached_selection: Cached model selection
        external_regressors: External regressors dict
        logger: Logger instance

    Returns:
        Tuple of (forecast_result, actual_model_type, model_desc, regressors_used)
    """
    # Filter regressors to only those in cached selection
    if cached_selection.use_regressors and external_regressors:
        filtered_regressors = {
            name: series
            for name, series in external_regressors.items()
            if name in cached_selection.regressor_list
        }
        regressors_used = list(filtered_regressors.keys())
    else:
        filtered_regressors = None
        regressors_used = []

    model_type = cached_selection.best_model
    mase_str = f"{cached_selection.best_mase:.2f}" if cached_selection.best_mase else "N/A"
    model_selection_reason = f"Cached selection: {model_type} (MASE={mase_str})"

    # Route to selected model
    if model_type == "ensemble":
        forecast_result = await generate_ensemble_forecast(
            metric=metric,
            historical_data=historical_data,
            periods_ahead=periods_ahead,
            fast_mode=True,
            external_regressors=filtered_regressors,
        )
        actual_model_type = "ensemble"
    else:
        try:
            forecast_result = await _route_to_model(
                model_name=model_type,
                metric=metric,
                historical_data=historical_data,
                periods_ahead=periods_ahead,
                external_regressors=filtered_regressors,
            )
            actual_model_type = model_type
        except Exception as e:
            # Fallback to Prophet on any error
            logger.warning(
                f"Cached model {model_type} failed, falling back to Prophet",
                extra={"error": str(e), "metric": metric},
            )
            forecast_result = await generate_forecast(
                metric=metric,
                historical_data=historical_data,
                periods_ahead=periods_ahead,
                external_regressors=filtered_regressors,
                use_model_selection=False,
            )
            actual_model_type = "prophet_fallback"
            model_selection_reason = f"Fallback from {model_type}: {str(e)}"

    return forecast_result, actual_model_type, model_selection_reason, regressors_used


async def generate_forecast_auto_select(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    prefer_accuracy: bool,
    external_regressors: dict[str, pd.Series] | None,
    future_regressor_strategy: str,
    regressors_used: list[str],
    logger: Logger,
) -> tuple[ForecastResult, str, str]:
    """Generate forecast with auto model selection (cache miss).

    Args:
        metric: Metric name
        historical_data: Historical time-series data
        periods_ahead: Number of periods to forecast
        prefer_accuracy: Whether to prefer accuracy over speed
        external_regressors: External regressors dict
        future_regressor_strategy: Strategy for future regressor values
        regressors_used: List of regressor names
        logger: Logger instance

    Returns:
        Tuple of (forecast_result, actual_model_type, model_selection_reason)
    """
    model_type, model_selection_reason = select_model_type(
        metric=metric,
        prefer_accuracy=prefer_accuracy,
        num_regressors=len(regressors_used),
    )
    logger.info(
        "Auto-selected model type (cache miss)",
        extra={
            "metric": metric,
            "selected_model": model_type,
            "reason": model_selection_reason,
            "prefer_accuracy": prefer_accuracy,
            "num_regressors": len(regressors_used),
        },
    )

    if model_type == "ensemble":
        forecast_result = await generate_ensemble_forecast(
            metric=metric,
            historical_data=historical_data,
            periods_ahead=periods_ahead,
            fast_mode=True,
            external_regressors=external_regressors,
        )
        actual_model_type = "ensemble"
    else:
        forecast_result = await generate_forecast(
            metric=metric,
            historical_data=historical_data,
            periods_ahead=periods_ahead,
            external_regressors=external_regressors if external_regressors else None,
            future_regressor_strategy=future_regressor_strategy,
        )
        actual_model_type = "prophet_multivariate" if external_regressors else "prophet_univariate"

    return forecast_result, actual_model_type, model_selection_reason


async def generate_forecast_explicit_model(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    model_type: str,
    external_regressors: dict[str, pd.Series] | None,
    future_regressor_strategy: str,
    logger: Logger,
) -> tuple[ForecastResult, str, str]:
    """Generate forecast with explicitly requested model type.

    Args:
        metric: Metric name
        historical_data: Historical time-series data
        periods_ahead: Number of periods to forecast
        model_type: Explicitly requested model type
        external_regressors: External regressors dict
        future_regressor_strategy: Strategy for future regressor values
        logger: Logger instance

    Returns:
        Tuple of (forecast_result, actual_model_type, model_selection_reason)
    """
    model_selection_reason = f"User explicitly requested {model_type}"

    if model_type == "ensemble":
        forecast_result = await generate_ensemble_forecast(
            metric=metric,
            historical_data=historical_data,
            periods_ahead=periods_ahead,
            fast_mode=True,
            external_regressors=external_regressors,
        )
        actual_model_type = "ensemble"
    else:
        forecast_result = await generate_forecast(
            metric=metric,
            historical_data=historical_data,
            periods_ahead=periods_ahead,
            external_regressors=external_regressors if external_regressors else None,
            future_regressor_strategy=future_regressor_strategy,
        )
        actual_model_type = "prophet_multivariate" if external_regressors else "prophet_univariate"

    return forecast_result, actual_model_type, model_selection_reason


# Public API - includes re-exported functions from forecast_helpers_response
__all__ = [
    # Query parsing and validation
    "parse_and_validate_metric",
    # Data extraction
    "extract_historical_data",
    "fetch_external_regressors",
    # Model selection and caching
    "check_model_selection_cache_for_forecast",
    # Forecast generation
    "generate_forecast_with_cache",
    "generate_forecast_auto_select",
    "generate_forecast_explicit_model",
    # Response building (re-exported from forecast_helpers_response)
    "build_enhanced_basis",
    "build_response",
    "handle_forecast_error",
]
