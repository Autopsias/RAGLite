"""Ensemble forecasting orchestration.

Story 7.5: Extract ensemble orchestration from hybrid.py.
Story 8: Refactored generate_ensemble_forecast from 452 to ~100 lines using ensemble_helpers.py.

This module contains the main ensemble forecast generation logic that coordinates
multiple forecasting models (Prophet, Linear, XGBoost, LightGBM, CatBoost, Chronos-2, TFT)
and combines their predictions using weighted averaging.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd

from raglite.forecasting.ensemble_helpers import (
    aggregate_metrics,
    build_ensemble_result,
    build_forecast_points,
    build_model_tasks,
    calculate_ensemble_forecast,
    execute_ensemble_models,
    handle_fallback,
    initialize_ensemble_config,
    prepare_ensemble_data,
    renormalize_weights,
)
from raglite.shared.logging import get_logger
from raglite.shared.models import ForecastResult, TimeSeriesData

logger = get_logger(__name__)


def _calculate_weighted_average(
    predictions: dict[str, list[float]],
    weights: dict[str, float],
    models: list[str],
) -> list[float]:
    """Calculate weighted average of model predictions.

    Story 6.4 AC5: Ensemble voting with configurable weights.

    Args:
        predictions: Dict of model name -> list of predictions
        weights: Dict of model name -> weight
        models: List of successfully fitted model names

    Returns:
        List of weighted average predictions
    """
    # Normalize weights for available models only
    total_weight = sum(weights.get(m, 0.0) for m in models)
    if total_weight == 0:
        normalized = {m: 1.0 / len(models) for m in models}
    else:
        normalized = {m: weights.get(m, 0.0) / total_weight for m in models}

    if not predictions:
        return []

    n_periods = max(len(pred) for pred in predictions.values())
    result = [0.0] * n_periods

    for model in models:
        if model not in predictions:
            continue
        pred_values = predictions[model]
        for i in range(len(pred_values)):
            result[i] += pred_values[i] * normalized[model]

    return result


# Import helper functions from hybrid module (will be moved to proper modules in future refactoring)
def select_regressors(
    target_series: pd.Series, external_regressors: dict[str, pd.Series]
) -> list[str]:
    """Wrapper for select_regressors - imports from hybrid module."""
    from raglite.forecasting.hybrid import select_regressors as select_impl

    return select_impl(target_series, external_regressors)


def prepare_regressors(
    regressors: dict[str, pd.Series],
    target_index: pd.DatetimeIndex,
    target_series: pd.Series | None = None,
) -> dict[str, pd.Series]:
    """Wrapper for prepare_regressors - imports from hybrid module."""
    from raglite.forecasting.hybrid import prepare_regressors as prepare_impl

    return prepare_impl(regressors, target_index, target_series)


def _fit_and_forecast_linear(
    X: pd.DataFrame,
    y: pd.Series,
    X_future: pd.DataFrame,
    feature_names: list[str],
    periods_ahead: int,
) -> dict[str, Any]:
    """Wrapper for linear regression forecasting - imports from hybrid module."""
    from raglite.forecasting.hybrid import _fit_and_forecast_linear as linear_impl

    return linear_impl(X, y, X_future, feature_names, periods_ahead)


def _fit_and_forecast_catboost(
    X: pd.DataFrame,
    y: pd.Series,
    X_future: pd.DataFrame,
    periods_ahead: int,
    fast_mode: bool = False,
) -> dict[str, Any]:
    """Wrapper for CatBoost forecasting - imports from hybrid module."""
    from raglite.forecasting.hybrid import _fit_and_forecast_catboost as catboost_impl

    return catboost_impl(X, y, X_future, periods_ahead, fast_mode)


async def explain_forecast(result: ForecastResult, context: str) -> str:
    """Wrapper for LLM explanation - imports from hybrid module."""
    from raglite.forecasting.hybrid import explain_forecast as explain_impl

    return await explain_impl(result, context)


def _generate_explanation_context(
    metric: str, successful_models: list[str], selected: list[str] | None
) -> str:
    """Generate explanation context string for LLM.

    Args:
        metric: Metric name
        successful_models: List of successfully fitted model names
        selected: List of selected external regressor names

    Returns:
        Context string for LLM explanation
    """
    context = f"Ensemble forecast for {metric} using {', '.join(successful_models)}"
    if selected:
        context += f" with external regressors: {', '.join(selected)}"
    return context


def _build_historical_dataframe(historical_data: TimeSeriesData) -> pd.DataFrame:
    """Build DataFrame from historical time series data.

    Args:
        historical_data: Time-series data from extraction

    Returns:
        DataFrame with 'ds' (date) and 'y' (value) columns
    """
    return pd.DataFrame(
        {
            "ds": [p.date for p in historical_data.points],
            "y": [p.value for p in historical_data.points],
        }
    )


async def _finalize_ensemble_result(
    metric: str,
    historical_data: TimeSeriesData,
    forecast_points: list,
    successful_models: list[str],
    predictions: dict[str, list[float]],
    weights: dict[str, float],
    combined_metrics: dict[str, float],
    selected: list[str] | None,
    periods_ahead: int,
) -> ForecastResult:
    """Build final ensemble result with LLM explanation.

    Args:
        metric: Metric name
        historical_data: Time-series data from extraction
        forecast_points: List of forecast points
        successful_models: List of successfully fitted model names
        predictions: Dict of model predictions
        weights: Dict of model weights
        combined_metrics: Aggregated metrics
        selected: List of selected external regressor names
        periods_ahead: Number of forecast periods

    Returns:
        Complete ForecastResult with LLM explanation
    """
    # Build result object
    result = build_ensemble_result(
        metric,
        historical_data,
        forecast_points,
        successful_models,
        predictions,
        weights,
        combined_metrics,
        selected or [],
        periods_ahead,
    )

    # Generate LLM explanation
    context = _generate_explanation_context(metric, successful_models, selected)
    result.confidence_reasoning = await explain_forecast(result, context)

    return result


async def generate_ensemble_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    external_regressors: dict[str, pd.Series] | None = None,
    periods_ahead: int = 4,
    models: list[str] | None = None,
    weights: dict[str, float] | None = None,
    fast_mode: bool = False,
) -> ForecastResult:
    """Generate ensemble forecast using multiple models.

    Story 6.4 AC5: Ensemble voting with configurable weights.
    Story 6.4 AC6: Graceful degradation with fallback.
    Story 6.12: Added CatBoost to ensemble.
    Story 6.13: Added Chronos-2 to ensemble.
    Story 6.14: Added TFT to ensemble.
    Story 8: Refactored from 452 to ~100 lines using ensemble_helpers.py.

    Args:
        metric: Metric name (e.g., "cement_demand")
        historical_data: Time-series data from extraction
        external_regressors: Dict of regressor series from PostgreSQL
        periods_ahead: Number of periods to forecast (default: 4)
        models: Models to use (default: ["prophet", "linear", "xgboost", "lightgbm", "catboost", "chronos", "tft"])
        weights: Model weights (default from settings)
        fast_mode: Use fast hyperparameter grid for XGBoost/LightGBM/CatBoost (default: False)

    Returns:
        ForecastResult with ensemble predictions and per-model details

    Raises:
        InsufficientDataError: If <6 data points available
    """
    # Step 1: Initialize configuration
    models, weights, fast_mode = initialize_ensemble_config(
        models, weights, fast_mode, metric, external_regressors, logger
    )

    logger.info(
        "Generating ensemble forecast",
        extra={"metric": metric, "models": models, "weights": weights},
    )

    # Step 2: Prepare data
    X, y, selected, prepared = prepare_ensemble_data(historical_data, external_regressors, logger)

    # Build DataFrame for forecast point generation
    df = _build_historical_dataframe(historical_data)

    # Step 3: Build parallel tasks
    loop = asyncio.get_event_loop()
    tasks, task_names, failed_models = build_model_tasks(
        models,
        metric,
        historical_data,
        external_regressors,
        X,
        y,
        periods_ahead,
        fast_mode,
        loop,
        logger,
    )

    # Step 4: Execute models in parallel
    predictions, metrics_results, successful_models, prophet_result = await execute_ensemble_models(
        tasks, task_names, failed_models, weights, logger
    )

    # Step 5: Re-normalize weights
    weights = renormalize_weights(weights, failed_models, successful_models, logger)

    # Step 6: Handle fallback if all models failed
    if not successful_models:
        return await handle_fallback(
            metric, historical_data, external_regressors, periods_ahead, logger
        )

    # Step 7: Calculate weighted ensemble
    ensemble_values = calculate_ensemble_forecast(successful_models, predictions, weights)

    # Step 8: Build forecast points
    forecast_points = build_forecast_points(ensemble_values, prophet_result, df, periods_ahead)

    # Step 9: Aggregate metrics
    combined_metrics = aggregate_metrics(metrics_results)

    # Step 10: Finalize result with LLM explanation
    return await _finalize_ensemble_result(
        metric,
        historical_data,
        forecast_points,
        successful_models,
        predictions,
        weights,
        combined_metrics,
        selected,
        periods_ahead,
    )
