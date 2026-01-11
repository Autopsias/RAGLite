"""Task building and model execution for ensemble forecasting.

Extracted from ensemble_helpers.py (Story 8 refactoring).
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from logging import Logger
from typing import TYPE_CHECKING, Any, cast

import pandas as pd

from raglite.forecasting.models.chronos_model import fit_and_forecast_chronos
from raglite.forecasting.models.lightgbm_model import _fit_and_forecast_lightgbm
from raglite.forecasting.models.tft_model import fit_and_forecast_tft
from raglite.forecasting.models.xgboost_model import _fit_and_forecast_xgboost
from raglite.shared.models import ForecastResult, TimeSeriesData

if TYPE_CHECKING:
    pass

# Thread pool for running synchronous models in parallel
_sklearn_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="sklearn_forecast")


def _add_ml_model_task(
    model_name: str,
    models: list[str],
    X: pd.DataFrame,
    y: pd.Series,
    X_future: pd.DataFrame | None,
    periods_ahead: int,
    fast_mode: bool,
    loop: asyncio.AbstractEventLoop,
    logger: Logger,
    tasks: list[Any],
    task_names: list[str],
    failed_models: list[str],
) -> None:
    """Add ML model task if regressors available, else mark as failed.

    Args:
        model_name: Name of the model (linear, xgboost, lightgbm, catboost)
        models: List of model names to run
        X: Feature matrix
        y: Target series
        X_future: Future features (or None)
        periods_ahead: Number of periods to forecast
        fast_mode: Use fast hyperparameter grid
        loop: Event loop for ThreadPoolExecutor
        logger: Logger instance
        tasks: Tasks list to append to (mutated)
        task_names: Task names list to append to (mutated)
        failed_models: Failed models list to append to (mutated)
    """
    from raglite.forecasting.ensemble import _fit_and_forecast_catboost, _fit_and_forecast_linear

    if model_name not in models:
        return

    if len(X.columns) > 0 and X_future is not None:
        X_copy, y_copy, X_future_copy = X.copy(), y.copy(), X_future.copy()

        if model_name == "linear":
            feature_names = list(X.columns)

            def run_model() -> dict[str, Any]:
                return _fit_and_forecast_linear(
                    X_copy, y_copy, X_future_copy, feature_names, periods_ahead
                )

        elif model_name == "xgboost":

            def run_model() -> dict[str, Any]:
                return _fit_and_forecast_xgboost(
                    X_copy, y_copy, X_future_copy, periods_ahead, fast_mode
                )

        elif model_name == "lightgbm":

            def run_model() -> dict[str, Any]:
                return _fit_and_forecast_lightgbm(
                    X_copy, y_copy, X_future_copy, periods_ahead, fast_mode
                )

        elif model_name == "catboost":

            def run_model() -> dict[str, Any]:
                return _fit_and_forecast_catboost(
                    X_copy, y_copy, X_future_copy, periods_ahead, fast_mode
                )

        else:
            return

        tasks.append(loop.run_in_executor(_sklearn_executor, run_model))
        task_names.append(model_name)
    else:
        logger.info(f"{model_name.capitalize()} model skipped: requires external regressors")
        failed_models.append(model_name)


def build_model_tasks(
    models: list[str],
    metric: str,
    historical_data: TimeSeriesData,
    external_regressors: dict[str, pd.Series] | None,
    X: pd.DataFrame,
    y: pd.Series,
    periods_ahead: int,
    fast_mode: bool,
    loop: asyncio.AbstractEventLoop,
    logger: Logger,
) -> tuple[list[Any], list[str], list[str]]:
    """Build parallel task list for ensemble models.

    Args:
        models: List of model names to run
        metric: Metric name
        historical_data: Time-series data
        external_regressors: External regressors dict
        X: Feature matrix
        y: Target series
        periods_ahead: Number of periods to forecast
        fast_mode: Use fast hyperparameter grid
        loop: Event loop for ThreadPoolExecutor
        logger: Logger instance

    Returns:
        Tuple of (tasks, task_names, failed_models)
    """
    from raglite.forecasting.ensemble_helpers_data import prepare_future_features
    from raglite.forecasting.hybrid import generate_forecast

    tasks: list[Any] = []
    task_names: list[str] = []
    failed_models: list[str] = []

    # Prepare future feature values (constant extrapolation)
    X_future = prepare_future_features(X, periods_ahead)

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

    # ML models requiring regressors
    for model in ["linear", "xgboost", "lightgbm", "catboost"]:
        _add_ml_model_task(
            model,
            models,
            X,
            y,
            X_future,
            periods_ahead,
            fast_mode,
            loop,
            logger,
            tasks,
            task_names,
            failed_models,
        )

    # Chronos-2 task (works with or without regressors)
    if "chronos" in models:
        y_copy_chronos = y.copy()

        def run_chronos() -> dict[str, Any] | None:
            return fit_and_forecast_chronos(y_copy_chronos, periods_ahead, external_regressors=None)

        tasks.append(loop.run_in_executor(_sklearn_executor, run_chronos))
        task_names.append("chronos")

    # TFT task
    if "tft" in models:
        y_copy_tft = y.copy()
        X_copy_tft = X.copy() if len(X.columns) > 0 else None

        def run_tft() -> dict[str, Any] | None:
            return fit_and_forecast_tft(y_copy_tft, periods_ahead, external_regressors=X_copy_tft)

        tasks.append(loop.run_in_executor(_sklearn_executor, run_tft))
        task_names.append("tft")

    return tasks, task_names, failed_models


def process_model_results(
    task_names: list[str],
    results: list[Any],
    weights: dict[str, float],
    failed_models: list[str],
    logger: Logger,
) -> tuple[dict[str, list[float]], dict[str, dict[str, Any]], list[str], ForecastResult | None]:
    """Process results from parallel model execution.

    Args:
        task_names: Names of tasks executed
        results: Results from asyncio.gather
        weights: Model weights
        failed_models: List of already failed models
        logger: Logger instance

    Returns:
        Tuple of (predictions, metrics_results, successful_models, prophet_result)
    """
    predictions: dict[str, list[float]] = {}
    metrics_results: dict[str, dict[str, Any]] = {}
    successful_models: list[str] = []
    prophet_result: ForecastResult | None = None

    for name, result in zip(task_names, results, strict=False):
        if isinstance(result, Exception):
            logger.warning(f"{name.capitalize()} model failed: {result}")
            failed_models.append(name)
            continue

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
            result_dict = cast("dict[str, Any]", result)
            predictions[name] = result_dict["values"]
            metrics_value = result_dict.get("metrics")
            if metrics_value is not None:
                metrics_results[name] = cast("dict[str, Any]", metrics_value)
            successful_models.append(name)
            logger.info(f"{name.capitalize()} model succeeded (parallel)")

            if name == "chronos":
                logger.info(
                    "Chronos-2 participating in ensemble",
                    extra={
                        "ensemble_weight": weights.get("chronos", 0.0),
                        "forecast_periods": len(result_dict["values"]),
                    },
                )

    return predictions, metrics_results, successful_models, prophet_result


async def execute_ensemble_models(
    tasks: list[Any],
    task_names: list[str],
    failed_models: list[str],
    weights: dict[str, float],
    logger: Logger,
) -> tuple[dict[str, list[float]], dict[str, dict[str, Any]], list[str], ForecastResult | None]:
    """Execute ensemble models in parallel and process results.

    Args:
        tasks: List of async tasks to execute
        task_names: Names corresponding to tasks
        failed_models: List of already failed models
        weights: Model weights
        logger: Logger instance

    Returns:
        Tuple of (predictions, metrics_results, successful_models, prophet_result)
    """
    predictions: dict[str, list[float]] = {}
    metrics_results: dict[str, dict[str, Any]] = {}
    successful_models: list[str] = []
    prophet_result: ForecastResult | None = None

    if tasks:
        logger.info(
            "Running ensemble models in parallel",
            extra={"models": task_names, "parallel_count": len(tasks)},
        )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        predictions, metrics_results, successful_models, prophet_result = process_model_results(
            task_names, results, weights, failed_models, logger
        )
    else:
        logger.info("No models configured to run")

    return predictions, metrics_results, successful_models, prophet_result


async def handle_fallback(
    metric: str,
    historical_data: TimeSeriesData,
    external_regressors: dict[str, pd.Series] | None,
    periods_ahead: int,
    logger: Logger,
) -> ForecastResult:
    """Handle fallback when all ensemble models fail.

    Story 6.4 AC6: Fallback strategy.

    Args:
        metric: Metric name
        historical_data: Time-series data
        external_regressors: External regressors dict
        periods_ahead: Number of periods to forecast
        logger: Logger instance

    Returns:
        ForecastResult from fallback model
    """
    from raglite.forecasting.hybrid import generate_forecast

    logger.warning("All ensemble models failed, falling back to Prophet-multivariate")
    try:
        return await generate_forecast(
            metric=metric,
            historical_data=historical_data,
            external_regressors=external_regressors,
            periods_ahead=periods_ahead,
        )
    except Exception:
        logger.warning("Prophet-multivariate failed, falling back to Prophet-univariate")
        return await generate_forecast(
            metric=metric,
            historical_data=historical_data,
            external_regressors=None,
            periods_ahead=periods_ahead,
        )
