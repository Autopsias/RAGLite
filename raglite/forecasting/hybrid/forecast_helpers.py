"""Helper functions for generate_forecast() to reduce function length.

Story 8: Refactoring to reduce generate_forecast from 659 lines to ~150 lines.

These helpers extract cohesive logic blocks while preserving the original algorithm.

This module serves as the main facade - high-level orchestration functions live here,
with specialized helpers extracted to domain-specific modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

# Re-export all functions for backward compatibility
from raglite.forecasting.hybrid.forecast_helpers_forecasting import (
    generate_forecast_points_by_frequency,
)
from raglite.forecasting.hybrid.forecast_helpers_prophet import (
    filter_regressors_for_cache,
    prepare_and_fit_prophet_model,
)
from raglite.forecasting.hybrid.forecast_helpers_setup import (
    check_model_selection_cache,
    handle_deprecation_warning,
    handle_initial_setup,
)

if TYPE_CHECKING:
    from logging import Logger

    from raglite.shared.models import ForecastResult, TimeSeriesData


async def try_non_prophet_model(
    selected_model: str | None,
    selected_regressors: list[str] | None,
    external_regressors: dict[str, pd.Series] | None,
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    model_source: str,
    model_selection_reason: str | None,
    explain_forecast_func: Any,
    logger: Logger,
) -> tuple[ForecastResult | None, str, str | None, dict[str, pd.Series] | None]:
    """Try non-Prophet model with fallback to Prophet on failure.

    Story 8.1: Extracted from generate_forecast (Steps 3-4).

    Args:
        selected_model: Model from cache (or None)
        selected_regressors: Regressors from cache (or None)
        external_regressors: Available external regressors
        metric: Metric name
        historical_data: Time-series data
        periods_ahead: Number of periods to forecast
        model_source: Source of model selection
        model_selection_reason: Reason for selection
        explain_forecast_func: Function to generate LLM explanation
        logger: Logger instance

    Returns:
        Tuple of (result_or_none, model_source, model_selection_reason, external_regressors)
        If result_or_none is not None, caller should return it immediately (non-Prophet succeeded)
        If None, caller should proceed with Prophet path
    """
    # Filter regressors based on cache selection
    filtered_regressors = filter_regressors_for_cache(
        selected_model, selected_regressors, external_regressors
    )

    # Try non-Prophet model if selected
    if selected_model is not None and selected_model != "prophet":
        try:
            result = await route_to_non_prophet_model(
                selected_model,
                metric,
                historical_data,
                periods_ahead,
                filtered_regressors,
                model_source,
                model_selection_reason,
                explain_forecast_func,
                logger,
            )
            return (result, model_source, model_selection_reason, filtered_regressors)
        except (NotImplementedError, Exception) as e:
            # Fallback to Prophet
            logger.warning(f"Model {selected_model} failed, falling back to Prophet: {e}")
            model_source = "fallback"
            model_selection_reason = f"Fallback from {selected_model}: {str(e)}"
            return (None, model_source, model_selection_reason, filtered_regressors)
    elif selected_model == "prophet":
        return (None, model_source, model_selection_reason, filtered_regressors)

    # No model selected - use Prophet with original regressors
    return (None, model_source, model_selection_reason, external_regressors)


async def route_to_non_prophet_model(
    selected_model: str,
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    filtered_regressors: dict[str, pd.Series] | None,
    model_source: str,
    model_selection_reason: str | None,
    explain_forecast_func: Any,
    logger: Logger,
) -> ForecastResult:
    """Route to non-Prophet model and add LLM explanation.

    Story 8.1: Extracted from generate_forecast to reduce function length.

    Args:
        selected_model: Model name to route to
        metric: Metric name
        historical_data: Time-series data
        periods_ahead: Number of periods to forecast
        filtered_regressors: Filtered external regressors
        model_source: Source of model selection
        model_selection_reason: Reason for selection
        explain_forecast_func: Function to generate explanation
        logger: Logger instance

    Returns:
        ForecastResult with explanation

    Raises:
        NotImplementedError, Exception: If model fails (caller should handle fallback)
    """
    from raglite.forecasting.hybrid.model_generators import _route_to_model

    result = await _route_to_model(
        model_name=selected_model,
        metric=metric,
        historical_data=historical_data,
        periods_ahead=periods_ahead,
        external_regressors=filtered_regressors,
    )
    result.model_source = model_source  # type: ignore[assignment]
    if model_selection_reason:
        result.model_selection_reason = model_selection_reason
    context = f"Historical {metric} data with {len(historical_data.points)} points"
    result.confidence_reasoning = await explain_forecast_func(forecast=result, context=context)
    return result


def calculate_accuracy_and_improvement(
    is_multivariate: bool,
    model: Any,
    df: pd.DataFrame,
    metric: str,
    get_baseline_rmse_func: Any,
) -> tuple[dict[str, float], float | None]:
    """Calculate accuracy metrics and improvement vs baseline.

    Story 8.1: Extracted from generate_forecast to reduce function length.

    Args:
        is_multivariate: Whether forecast uses external regressors
        model: Fitted Prophet model
        df: Training DataFrame
        metric: Metric name
        get_baseline_rmse_func: Function to get baseline RMSE

    Returns:
        Tuple of (accuracy_metrics, improvement_vs_baseline)
    """
    from raglite.forecasting.hybrid.ensemble import calculate_accuracy

    accuracy_metrics: dict[str, float] = {}
    improvement_vs_baseline: float | None = None

    if is_multivariate:
        accuracy_metrics = calculate_accuracy(model, df)
        baseline_rmse = get_baseline_rmse_func(metric)
        if baseline_rmse and accuracy_metrics.get("rmse", 0) > 0:
            improvement_vs_baseline = (
                (baseline_rmse - accuracy_metrics["rmse"]) / baseline_rmse
            ) * 100

    return accuracy_metrics, improvement_vs_baseline


def build_forecast_result(
    metric: str,
    historical_data: TimeSeriesData,
    forecast_points: list[Any],
    periods_ahead: int,
    regressors_used: list[str],
    accuracy_metrics: dict[str, float],
    improvement_vs_baseline: float | None,
    model_source: str,
    model_selection_reason: str | None,
) -> ForecastResult:
    """Build ForecastResult object from components.

    Story 8.1: Extracted from generate_forecast to reduce function length.

    Args:
        metric: Metric name
        historical_data: Original time-series data
        forecast_points: List of forecast points
        periods_ahead: Number of periods forecasted
        regressors_used: List of regressor names used
        accuracy_metrics: Dict of accuracy metrics
        improvement_vs_baseline: Improvement percentage vs baseline
        model_source: Model source ('cached', 'default', 'fallback')
        model_selection_reason: Reason for model selection

    Returns:
        ForecastResult object
    """
    from raglite.shared.models import ForecastResult

    model_type = "prophet_multivariate" if regressors_used else "prophet_univariate"
    basis_text = f"Prophet model trained on {len(historical_data.points)} data points"
    if regressors_used:
        basis_text += f" with {len(regressors_used)} external regressors"

    return ForecastResult(
        metric_name=metric,
        historical_data=historical_data.points,
        forecast=forecast_points,
        basis=basis_text,
        accuracy_estimate="±15% (NFR10 target)",
        periods_ahead=periods_ahead,
        model_type=model_type,
        accuracy_metrics=accuracy_metrics,
        regressors_used=regressors_used,
        improvement_vs_baseline=improvement_vs_baseline,
        model_source=model_source,  # type: ignore[arg-type]
        model_selection_reason=model_selection_reason,
    )


def build_explanation_context(
    metric: str,
    historical_data: TimeSeriesData,
    regressors_used: list[str],
) -> str:
    """Build context string for LLM explanation.

    Story 8.1: Extracted from generate_forecast to reduce function length.

    Args:
        metric: Metric name
        historical_data: Original time-series data
        regressors_used: List of regressor names used

    Returns:
        Context string for LLM
    """
    context = f"Historical {metric} data from {len(historical_data.source_documents)} documents"
    if regressors_used:
        context += f". Multi-variate forecast using: {', '.join(regressors_used)}"
    return context


# Export all public functions
__all__ = [
    # Setup functions
    "handle_deprecation_warning",
    "check_model_selection_cache",
    "handle_initial_setup",
    # Prophet functions
    "filter_regressors_for_cache",
    "prepare_and_fit_prophet_model",
    # Forecasting functions
    "generate_forecast_points_by_frequency",
    # Orchestration functions
    "try_non_prophet_model",
    "route_to_non_prophet_model",
    "calculate_accuracy_and_improvement",
    "build_forecast_result",
    "build_explanation_context",
]
