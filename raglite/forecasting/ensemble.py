"""Ensemble forecasting orchestration.

Story 7.5: Extract ensemble orchestration from hybrid.py.

This module contains the main ensemble forecast generation logic that coordinates
multiple forecasting models (Prophet, Linear, XGBoost, LightGBM, CatBoost, Chronos-2, TFT)
and combines their predictions using weighted averaging.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

import numpy as np
import pandas as pd

from raglite.forecasting.models.base import MIN_DATA_POINTS, InsufficientDataError
from raglite.forecasting.models.chronos_model import fit_and_forecast_chronos
from raglite.forecasting.models.lightgbm_model import _fit_and_forecast_lightgbm
from raglite.forecasting.models.tft_model import fit_and_forecast_tft
from raglite.forecasting.models.xgboost_model import _fit_and_forecast_xgboost
from raglite.shared.logging import get_logger
from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesData

logger = get_logger(__name__)

# Thread pool for running synchronous models in parallel (XGBoost, LightGBM, CatBoost, Chronos-2, TFT)
_sklearn_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="sklearn_forecast")


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
        # Equal weights if no valid weights
        normalized = {m: 1.0 / len(models) for m in models}
    else:
        normalized = {m: weights.get(m, 0.0) / total_weight for m in models}

    # Weighted sum
    if not predictions:
        # No predictions available, return empty list
        return []

    # Use the maximum prediction length across all models
    n_periods = max(len(pred) for pred in predictions.values())
    result = [0.0] * n_periods

    for model in models:
        if model not in predictions:
            continue  # Skip models that don't have predictions
        pred_values = predictions[model]
        # Add predictions for available periods
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
    from raglite.forecasting.adaptive_weights import get_adaptive_weights, handle_model_failure
    from raglite.forecasting.hybrid import generate_forecast
    from raglite.shared.config import settings

    # Default models and weights from settings
    if models is None:
        models = settings.forecasting_models.split(",")

    # Story 6.12 AC4: Try adaptive weights, fallback to static if not available
    has_regressors = external_regressors is not None and len(external_regressors) > 0
    if weights is None:
        try:
            # Get adaptive weights from PostgreSQL (with static fallback)
            weights = get_adaptive_weights(metric, has_regressors=has_regressors)
            logger.info(
                "Using adaptive weights",
                extra={"metric": metric, "weights": weights, "has_regressors": has_regressors},
            )
        except Exception as e:
            logger.warning(
                f"Failed to get adaptive weights, using static: {e}",
                extra={"metric": metric},
            )
            weights = {
                "prophet": settings.ensemble_weight_prophet,
                "linear": settings.ensemble_weight_linear,
                "xgboost": settings.ensemble_weight_xgboost,
                "lightgbm": settings.ensemble_weight_lightgbm,  # Story 6.8 AC4
                "catboost": settings.ensemble_weight_catboost,  # Story 6.12
                "chronos": settings.ensemble_weight_chronos,  # Story 6.13
                "tft": settings.ensemble_weight_tft,  # Story 6.14
            }

    if fast_mode is False:
        fast_mode = settings.ensemble_fast_mode

    logger.info(
        "Generating ensemble forecast",
        extra={"metric": metric, "models": models, "weights": weights},
    )

    # Validate minimum data requirement
    if len(historical_data.points) < MIN_DATA_POINTS:
        raise InsufficientDataError(
            f"Insufficient data for forecast. Minimum {MIN_DATA_POINTS} data points required. "
            f"Got {len(historical_data.points)}."
        )

    # Prepare data
    df = pd.DataFrame(
        {
            "ds": [p.date for p in historical_data.points],
            "y": [p.value for p in historical_data.points],
        }
    )

    # Select and prepare regressors
    target_series = pd.Series(df["y"].values, index=pd.DatetimeIndex(df["ds"]))
    selected: list[str] = []
    prepared: dict[str, pd.Series] = {}

    if external_regressors:
        selected = select_regressors(target_series, external_regressors)
        if selected:
            prepared = prepare_regressors(
                {k: v for k, v in external_regressors.items() if k in selected},
                pd.DatetimeIndex(df["ds"]),
                target_series=target_series,  # Story 6.7: Enable YoY% auto-detection
            )

    # Build feature matrix for sklearn models
    X = pd.DataFrame(prepared) if prepared else pd.DataFrame()
    y = target_series

    # Track results
    predictions: dict[str, list[float]] = {}
    metrics_results: dict[str, dict[str, Any]] = {}
    successful_models: list[str] = []
    prophet_result: ForecastResult | None = None

    # Story 6.4 AC5: Parallel execution using asyncio.gather + ThreadPoolExecutor
    # Prophet is async-native, sklearn models run in ThreadPoolExecutor
    loop = asyncio.get_event_loop()

    # Prepare future feature values for sklearn models (constant extrapolation)
    # WARNING: Future regressors are extrapolated using last observed value.
    # This assumes regressors stay constant, which may lead to forecast error
    # for metrics with trending external factors.
    X_future: pd.DataFrame | None = None
    if len(X.columns) > 0:
        last_row = X.iloc[-1:].values
        X_future = pd.DataFrame(
            np.tile(last_row, (periods_ahead, 1)),
            columns=X.columns,
        )

    # Build parallel task list
    tasks: list[Any] = []
    task_names: list[str] = []
    # Story 6.12 AC4: Track failed models for weight re-normalization (initialize early)
    failed_models: list[str] = []

    # Prophet task (async native)
    if "prophet" in models:
        tasks.append(
            generate_forecast(
                metric=metric,
                historical_data=historical_data,
                external_regressors=external_regressors,
                periods_ahead=periods_ahead,
            )
        )
        task_names.append("prophet")

    # Linear Regression task (sync, via ThreadPoolExecutor)
    if "linear" in models:
        if len(X.columns) > 0 and X_future is not None:
            # Create explicit copies for thread safety
            X_copy = X.copy()
            y_copy = y.copy()
            X_future_copy = X_future.copy()
            feature_names = list(X.columns)

            def run_linear() -> dict[str, Any]:
                return _fit_and_forecast_linear(
                    X_copy, y_copy, X_future_copy, feature_names, periods_ahead
                )

            tasks.append(loop.run_in_executor(_sklearn_executor, run_linear))
            task_names.append("linear")
        else:
            # Story 6.12 AC4: Linear skipped due to no regressors - add to failed_models for weight re-normalization
            logger.info("Linear model skipped: requires external regressors (len(X.columns)=0)")
            failed_models.append("linear")

    # XGBoost task (sync, via ThreadPoolExecutor)
    if "xgboost" in models:
        if len(X.columns) > 0 and X_future is not None:
            # Create explicit copies for thread safety
            X_copy_xgb = X.copy()
            y_copy_xgb = y.copy()
            X_future_copy_xgb = X_future.copy()
            fast_mode_copy = fast_mode

            def run_xgboost() -> dict[str, Any]:
                return _fit_and_forecast_xgboost(
                    X_copy_xgb, y_copy_xgb, X_future_copy_xgb, periods_ahead, fast_mode_copy
                )

            tasks.append(loop.run_in_executor(_sklearn_executor, run_xgboost))
            task_names.append("xgboost")
        else:
            # Story 6.12 AC4: XGBoost skipped due to no regressors - add to failed_models for weight re-normalization
            logger.info("XGBoost model skipped: requires external regressors (len(X.columns)=0)")
            failed_models.append("xgboost")

    # LightGBM task (sync, via ThreadPoolExecutor) - Story 6.8 AC4
    if "lightgbm" in models:
        if len(X.columns) > 0 and X_future is not None:
            # Create explicit copies for thread safety
            X_copy_lgb = X.copy()
            y_copy_lgb = y.copy()
            X_future_copy_lgb = X_future.copy()
            fast_mode_copy_lgb = fast_mode

            def run_lightgbm() -> dict[str, Any]:
                return _fit_and_forecast_lightgbm(
                    X_copy_lgb, y_copy_lgb, X_future_copy_lgb, periods_ahead, fast_mode_copy_lgb
                )

            tasks.append(loop.run_in_executor(_sklearn_executor, run_lightgbm))
            task_names.append("lightgbm")
        else:
            # Story 6.12 AC4: LightGBM skipped due to no regressors - add to failed_models for weight re-normalization
            logger.info("LightGBM model skipped: requires external regressors (len(X.columns)=0)")
            failed_models.append("lightgbm")

    # CatBoost task (sync, via ThreadPoolExecutor) - Story 6.12
    if "catboost" in models:
        if len(X.columns) > 0 and X_future is not None:
            # Create explicit copies for thread safety
            X_copy_cat = X.copy()
            y_copy_cat = y.copy()
            X_future_copy_cat = X_future.copy()
            fast_mode_copy_cat = fast_mode

            def run_catboost() -> dict[str, Any]:
                return _fit_and_forecast_catboost(
                    X_copy_cat, y_copy_cat, X_future_copy_cat, periods_ahead, fast_mode_copy_cat
                )

            tasks.append(loop.run_in_executor(_sklearn_executor, run_catboost))
            task_names.append("catboost")
        else:
            # Story 6.12 AC4: CatBoost skipped due to no regressors - add to failed_models for weight re-normalization
            logger.info("CatBoost model skipped: requires external regressors (len(X.columns)=0)")
            failed_models.append("catboost")

    # Chronos-2 task (sync, via ThreadPoolExecutor) - Story 6.13
    # Chronos-2 works with OR without regressors (pure time-series model)
    if "chronos" in models:
        # Create explicit copy for thread safety
        y_copy_chronos = y.copy()
        periods_copy_chronos = periods_ahead

        def run_chronos() -> dict[str, Any] | None:
            return fit_and_forecast_chronos(
                y_copy_chronos,
                periods_copy_chronos,
                external_regressors=None,  # Not using covariates in v1
            )

        tasks.append(loop.run_in_executor(_sklearn_executor, run_chronos))
        task_names.append("chronos")

    # TFT task (sync, via ThreadPoolExecutor) - Story 6.14
    # TFT works with pre-trained checkpoint from offline training
    if "tft" in models:
        # Create explicit copy for thread safety
        y_copy_tft = y.copy()
        periods_copy_tft = periods_ahead
        X_copy_tft = X.copy() if len(X.columns) > 0 else None

        def run_tft() -> dict[str, Any] | None:
            return fit_and_forecast_tft(
                y_copy_tft,
                periods_copy_tft,
                external_regressors=X_copy_tft,
            )

        tasks.append(loop.run_in_executor(_sklearn_executor, run_tft))
        task_names.append("tft")

    # Execute all models in parallel
    if tasks:
        logger.info(
            "Running ensemble models in parallel",
            extra={"models": task_names, "parallel_count": len(tasks)},
        )
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results - Story 6.12 AC4: Handle failures with weight re-normalization
        for name, result in zip(task_names, results, strict=False):
            if isinstance(result, Exception):
                logger.warning(f"{name.capitalize()} model failed: {result}")
                failed_models.append(name)
                continue

            # Handle None return (graceful failure from model)
            if result is None:
                logger.warning(f"{name.capitalize()} model returned None (graceful failure)")
                failed_models.append(name)
                continue

            if name == "prophet":
                prophet_result = cast(ForecastResult, result)
                predictions["prophet"] = [p.value for p in prophet_result.forecast]
                metrics_results["prophet"] = prophet_result.accuracy_metrics
                successful_models.append("prophet")
                logger.info("Prophet model succeeded (parallel)")
            else:
                # Linear, XGBoost, LightGBM, CatBoost, or Chronos result is a dict with values and metrics
                result_dict = cast("dict[str, Any]", result)
                predictions[name] = result_dict["values"]
                metrics_value = result_dict.get("metrics")
                if metrics_value is not None:
                    metrics_results[name] = cast("dict[str, Any]", metrics_value)
                successful_models.append(name)
                logger.info(f"{name.capitalize()} model succeeded (parallel)")

                # Log Chronos-2 ensemble participation (Issue 7)
                if name == "chronos":
                    logger.info(
                        "Chronos-2 participating in ensemble",
                        extra={
                            "ensemble_weight": weights.get("chronos", 0.0),
                            "forecast_periods": len(result_dict["values"]),
                        },
                    )
    else:
        logger.info("No models configured to run")

    # Story 6.12 AC4: Re-normalize weights after model failures
    if failed_models and weights:
        for failed in failed_models:
            weights = handle_model_failure(weights, failed)
        logger.info(
            "Weights re-normalized after model failures",
            extra={"failed_models": failed_models, "new_weights": weights},
        )

    # Normalize weights to only include successful models
    # This ensures when only a subset of models are requested (e.g., prophet+catboost)
    # and one fails (e.g., catboost), the remaining model gets weight 1.0
    if successful_models and weights:
        remaining = {k: weights.get(k, 0.0) for k in successful_models if weights.get(k, 0.0) > 0}
        if remaining:
            total = sum(remaining.values())
            if total > 0:
                weights = {k: v / total for k, v in remaining.items()}
                logger.info(
                    "Weights normalized to successful models only",
                    extra={"successful_models": successful_models, "final_weights": weights},
                )

    # Story 6.4 AC6: Fallback strategy
    if not successful_models:
        logger.warning("All ensemble models failed, falling back to Prophet-multivariate")
        # Try Prophet-multivariate as final fallback
        try:
            fallback_result = await generate_forecast(
                metric=metric,
                historical_data=historical_data,
                external_regressors=external_regressors,
                periods_ahead=periods_ahead,
            )
            return fallback_result
        except Exception:
            # Ultimate fallback: Prophet-univariate
            logger.warning("Prophet-multivariate failed, falling back to Prophet-univariate")
            return await generate_forecast(
                metric=metric,
                historical_data=historical_data,
                external_regressors=None,  # Force univariate
                periods_ahead=periods_ahead,
            )

    # Calculate weighted ensemble if multiple models succeeded
    if len(successful_models) == 1:
        # Only one model, use its predictions directly
        ensemble_values = predictions[successful_models[0]]
    else:
        ensemble_values = _calculate_weighted_average(predictions, weights, successful_models)

    # Build forecast points (use Prophet structure if available)
    if prophet_result:
        forecast_points = [
            ForecastPoint(
                date=p.date,
                value=ensemble_values[i] if i < len(ensemble_values) else p.value,
                lower=p.lower,  # Use Prophet CI
                upper=p.upper,  # Use Prophet CI
                label=p.label,
            )
            for i, p in enumerate(prophet_result.forecast)
        ]
    else:
        # Build from scratch (no Prophet available)
        last_date = df["ds"].max()
        forecast_points = []
        for i in range(periods_ahead):
            # Estimate next quarter date
            next_date = last_date + pd.DateOffset(months=3 * (i + 1))
            quarter = (next_date.month - 1) // 3 + 1
            label = f"Q{quarter} {next_date.year}"

            # Simple CI estimate: ±20% of value
            value = ensemble_values[i] if i < len(ensemble_values) else 0.0
            forecast_points.append(
                ForecastPoint(
                    date=next_date.to_pydatetime(),
                    value=value,
                    lower=value * 0.8,
                    upper=value * 1.2,
                    label=label,
                )
            )

    # Aggregate accuracy metrics from individual models
    combined_metrics: dict[str, float] = {}
    if metrics_results:
        rmse_values = [
            float(m.get("rmse", 0))
            for m in metrics_results.values()
            if isinstance(m.get("rmse"), (int, float)) and m.get("rmse", 0) > 0
        ]
        mae_values = [
            float(m.get("mae", 0))
            for m in metrics_results.values()
            if isinstance(m.get("mae"), (int, float)) and m.get("mae", 0) > 0
        ]
        mape_values = [
            float(m.get("mape", 0))
            for m in metrics_results.values()
            if isinstance(m.get("mape"), (int, float)) and m.get("mape", 0) > 0
        ]
        if rmse_values:
            combined_metrics["rmse"] = float(np.mean(rmse_values))
        if mae_values:
            combined_metrics["mae"] = float(np.mean(mae_values))
        if mape_values:
            combined_metrics["mape"] = float(np.mean(mape_values))

    # Build ForecastResult
    basis_text = f"Ensemble of {len(successful_models)} models"
    if selected:
        basis_text += f" with {len(selected)} regressors"

    result = ForecastResult(
        metric_name=metric,
        historical_data=historical_data.points,
        forecast=forecast_points,
        model_type="ensemble",
        ensemble_models=successful_models,
        individual_predictions=predictions,
        ensemble_weights={k: weights.get(k, 0.0) for k in successful_models},
        accuracy_metrics=combined_metrics,
        regressors_used=selected,
        basis=basis_text,
        accuracy_estimate="±15% (NFR10 target)",
        periods_ahead=periods_ahead,
    )

    # Generate LLM explanation
    context = f"Ensemble forecast for {metric} using {', '.join(successful_models)}"
    if selected:
        context += f" with external regressors: {', '.join(selected)}"
    result.confidence_reasoning = await explain_forecast(result, context)

    return result
