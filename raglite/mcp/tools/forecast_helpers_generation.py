"""Forecast generation helper functions for get_financial_forecast().

Story 8: Refactoring to reduce get_financial_forecast from 456 to ~150 lines.
Epic 8: Split into modules to comply with <500 LOC limit.

This module contains the three forecast generation strategies:
- Cached model selection
- Auto model selection
- Explicit model type
"""

from __future__ import annotations

from logging import Logger
from typing import TYPE_CHECKING

import pandas as pd

from raglite.external_data.storage import CachedModelSelection
from raglite.forecasting.hybrid import (
    _route_to_model,
    generate_ensemble_forecast,
    generate_forecast,
)

if TYPE_CHECKING:
    from raglite.shared.models import ForecastResult, TimeSeriesData


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
    mape_str = f"{cached_selection.best_mape:.1f}%" if cached_selection.best_mape else "N/A"
    model_selection_reason = f"Cached selection: {model_type} (MASE={mase_str}, MAPE={mape_str})"

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
    from raglite.forecasting.regressor_config import select_model_type

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


__all__ = [
    "generate_forecast_with_cache",
    "generate_forecast_auto_select",
    "generate_forecast_explicit_model",
]
