"""Adaptive weight calculation for ensemble forecasting.

Story 6.12: CatBoost Integration + Adaptive Weights

Provides backtest-driven weight optimization for ensemble models.
Weights are calculated from rolling backtest RMSE and stored in PostgreSQL.

Weight calculation formula:
    raw_weight = 1 / (RMSE + epsilon)
    normalized_weight = raw_weight / sum(raw_weights)
    capped_weight = max(MIN_WEIGHT, min(MAX_WEIGHT, normalized_weight))
    final_weight = re-normalized after capping

Weight caps maintain ensemble diversity:
    - MIN_WEIGHT = 5% (prevent model exclusion)
    - MAX_WEIGHT = 50% (prevent single model dominance)
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from raglite.shared.config import settings
from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from raglite.shared.models import TimeSeriesData

from sqlalchemy.orm import Session

logger = get_logger(__name__)

# Weight caps per AC4
MIN_WEIGHT = 0.05  # 5% minimum
MAX_WEIGHT = 0.50  # 50% maximum
EPSILON = 0.001  # Prevent division by zero


def calculate_backtest_weights(
    metric: str,
    historical_data: TimeSeriesData,
    external_regressors: dict[str, pd.Series] | None = None,
    models: list[str] | None = None,
) -> dict[str, dict[str, float]]:
    """Calculate model weights from rolling backtest.

    Story 6.12 AC3: Implement rolling backtest: train on months 1-9, test on 10-12.

    Args:
        metric: Target metric name
        historical_data: Full historical time-series data
        external_regressors: Optional external regressor series
        models: List of models to evaluate (default: all ensemble models)

    Returns:
        Dict with structure:
        {
            "model_name": {
                "weight": float,  # Normalized, capped weight
                "rmse": float,    # Backtest RMSE
                "mape": float,    # Backtest MAPE (%)
                "data_points": int,
            },
            ...
        }
    """
    from raglite.forecasting.hybrid import (
        fit_catboost,
        fit_lightgbm,
        fit_linear_regression,
        fit_xgboost,
    )

    if models is None:
        models = settings.forecasting_models.split(",")

    # Need at least 12 data points for meaningful backtest
    if len(historical_data.points) < 12:
        logger.warning(
            "Insufficient data for backtest",
            extra={"metric": metric, "data_points": len(historical_data.points)},
        )
        return {}

    # Prepare data
    df = pd.DataFrame(
        {
            "ds": [p.date for p in historical_data.points],
            "y": [p.value for p in historical_data.points],
        }
    )
    df = df.sort_values("ds").reset_index(drop=True)

    # Rolling backtest: train on first 75%, test on last 25%
    train_size = int(len(df) * 0.75)
    train_df = df.iloc[:train_size]
    test_df = df.iloc[train_size:]

    if len(test_df) < 3:
        logger.warning(
            "Test set too small for backtest",
            extra={"metric": metric, "test_size": len(test_df)},
        )
        return {}

    # Build feature matrix
    target_series = pd.Series(train_df["y"].values, index=pd.DatetimeIndex(train_df["ds"]))
    X_train: pd.DataFrame = pd.DataFrame()
    X_test: pd.DataFrame = pd.DataFrame()

    if external_regressors:
        from raglite.forecasting.hybrid import prepare_regressors, select_regressors

        selected = select_regressors(target_series, external_regressors)
        if selected:
            # Prepare regressors for both train and test
            train_idx = pd.DatetimeIndex(train_df["ds"])
            test_idx = pd.DatetimeIndex(test_df["ds"])

            prepared_train = prepare_regressors(
                {k: v for k, v in external_regressors.items() if k in selected},
                train_idx,
                target_series=target_series,
            )
            X_train = pd.DataFrame(prepared_train)

            # For test set, extrapolate regressors
            if len(X_train.columns) > 0:
                test_target = pd.Series(test_df["y"].values, index=test_idx)
                prepared_test = prepare_regressors(
                    {k: v for k, v in external_regressors.items() if k in selected},
                    test_idx,
                    target_series=test_target,
                )
                X_test = pd.DataFrame(prepared_test)

    y_train = pd.Series(train_df["y"].values, index=pd.DatetimeIndex(train_df["ds"]))
    y_test = test_df["y"].values

    # Evaluate each model
    results: dict[str, dict[str, float]] = {}

    # Sklearn-based models need features
    has_features = len(X_train.columns) > 0

    for model_name in models:
        try:
            if model_name == "prophet":
                # Prophet uses synchronous fitting for backtest (no async needed)
                # Story 6.12 AC3 fix: Include Prophet in backtest
                try:
                    from raglite.forecasting.hybrid import _get_prophet_class

                    Prophet = _get_prophet_class()

                    # Prophet requires specific DataFrame format
                    prophet_train = train_df[["ds", "y"]].copy()
                    prophet_train["ds"] = pd.to_datetime(prophet_train["ds"])

                    # Fit Prophet model
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        prophet_model = Prophet(
                            yearly_seasonality=True,
                            weekly_seasonality=False,
                            daily_seasonality=False,
                        )
                        prophet_model.fit(prophet_train)

                    # Generate predictions for test period
                    future = pd.DataFrame({"ds": pd.to_datetime(test_df["ds"])})
                    forecast = prophet_model.predict(future)
                    predictions = forecast["yhat"].values

                    # Calculate metrics
                    rmse = float(np.sqrt(np.mean((y_test - predictions) ** 2)))
                    non_zero_mask = y_test != 0
                    if non_zero_mask.any():
                        mape = float(
                            np.mean(
                                np.abs(
                                    (y_test[non_zero_mask] - predictions[non_zero_mask])
                                    / y_test[non_zero_mask]
                                )
                            )
                            * 100
                        )
                    else:
                        mape = 0.0

                    results[model_name] = {
                        "rmse": rmse,
                        "mape": mape,
                        "data_points": len(y_test),
                    }

                    logger.info(
                        f"Backtest completed for {model_name}",
                        extra={"metric": metric, "rmse": rmse, "mape": mape},
                    )
                    continue  # Move to next model

                except ImportError:
                    logger.warning("Prophet not available for backtest")
                    continue
                except Exception as e:
                    logger.warning(
                        "Prophet backtest failed",
                        extra={"metric": metric, "error": str(e)},
                    )
                    continue

            elif model_name == "linear" and has_features:
                model, _ = fit_linear_regression(X_train, y_train, list(X_train.columns))
                predictions = model.predict(X_test)

            elif model_name == "xgboost" and has_features:
                model, _ = fit_xgboost(X_train, y_train, fast_mode=True)
                predictions = model.predict(X_test)

            elif model_name == "lightgbm" and has_features:
                model, _ = fit_lightgbm(X_train, y_train, fast_mode=True)
                predictions = model.predict(X_test)

            elif model_name == "catboost" and has_features:
                model, _ = fit_catboost(X_train, y_train, fast_mode=True)
                predictions = model.predict(X_test)

            else:
                # Skip models that require features when none available
                continue

            # Calculate metrics
            rmse = float(np.sqrt(np.mean((y_test - predictions) ** 2)))
            non_zero_mask = y_test != 0
            if non_zero_mask.any():
                mape = float(
                    np.mean(
                        np.abs(
                            (y_test[non_zero_mask] - predictions[non_zero_mask])
                            / y_test[non_zero_mask]
                        )
                    )
                    * 100
                )
            else:
                mape = 0.0

            results[model_name] = {
                "rmse": rmse,
                "mape": mape,
                "data_points": len(y_test),
            }

            logger.info(
                f"Backtest completed for {model_name}",
                extra={"metric": metric, "rmse": rmse, "mape": mape},
            )

        except Exception as e:
            logger.warning(
                f"Backtest failed for {model_name}",
                extra={"metric": metric, "error": str(e)},
            )
            continue

    # Calculate weights from RMSE
    if results:
        results = _calculate_weights_from_rmse(results)

    return results


def _calculate_weights_from_rmse(
    results: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    """Calculate normalized, capped weights from backtest RMSE.

    Story 6.12 AC3: Weight formula: weight = 1 / (RMSE + epsilon)

    Args:
        results: Dict with model results containing 'rmse'

    Returns:
        Same dict with 'weight' added to each model
    """
    # Calculate raw weights (inverse RMSE)
    raw_weights: dict[str, float] = {}
    for model, metrics in results.items():
        rmse = metrics.get("rmse", float("inf"))
        raw_weights[model] = 1.0 / (rmse + EPSILON)

    # Normalize to sum to 1.0
    total = sum(raw_weights.values())
    if total > 0:
        normalized = {k: v / total for k, v in raw_weights.items()}
    else:
        # Equal weights if all failed
        n = len(raw_weights)
        equal_weight = 1.0 / n
        normalized = dict.fromkeys(raw_weights, equal_weight)

    # Apply caps (AC4)
    capped = {k: max(MIN_WEIGHT, min(MAX_WEIGHT, v)) for k, v in normalized.items()}

    # Re-normalize after capping
    total_capped = sum(capped.values())
    final_weights = {k: v / total_capped for k, v in capped.items()}

    # Add weights to results
    for model in results:
        results[model]["weight"] = final_weights.get(model, 0.0)

    return results


def get_adaptive_weights(
    metric: str,
    has_regressors: bool = True,
    session: Session | None = None,
) -> dict[str, float]:
    """Get adaptive weights for a metric from PostgreSQL.

    Story 6.12 AC4: Retrieve stored weights with fallback logic.

    Behavior:
    - If weights exist in model_weights table, use them
    - If no weights exist, return static weights from config
    - If has_regressors=False, boost Prophet (or Chronos) weight per AC4

    Args:
        metric: Target metric name
        has_regressors: Whether external regressors are available
        session: Optional SQLAlchemy session (creates new if None)

    Returns:
        Dict mapping model_name -> weight (float)
    """
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.shared.database import get_session

    # Get session
    if session is None:
        session = get_session()

    storage = ExternalDataStorage(session)
    weights = storage.get_weights_for_metric(metric)

    if weights:
        # Adaptive weights exist
        logger.info(
            "Using adaptive weights from database",
            extra={"metric": metric, "weights": weights},
        )

        if not has_regressors:
            # Apply regressor-dependent adjustment per AC4
            weights = _adjust_weights_no_regressors(weights)

        return weights

    # Fallback to static weights from config
    logger.info(
        "No adaptive weights found, using static config weights",
        extra={"metric": metric},
    )
    return _get_static_weights()


def _get_static_weights() -> dict[str, float]:
    """Get static weights from config.py.

    Returns:
        Dict of model weights from settings
    """
    return {
        "prophet": settings.ensemble_weight_prophet,
        "linear": settings.ensemble_weight_linear,
        "xgboost": settings.ensemble_weight_xgboost,
        "lightgbm": settings.ensemble_weight_lightgbm,
        "catboost": settings.ensemble_weight_catboost,
    }


def _adjust_weights_no_regressors(weights: dict[str, float]) -> dict[str, float]:
    """Adjust weights when no external regressors are available.

    Story 6.12 AC4: No regressors → Prophet/Chronos weight x2,
    regressor-dependent models x0.3

    Regressor-dependent models: linear, xgboost, lightgbm, catboost
    Non-regressor models: prophet (and future chronos)

    Args:
        weights: Current model weights

    Returns:
        Adjusted weights (re-normalized)
    """
    regressor_dependent = {"linear", "xgboost", "lightgbm", "catboost"}
    non_regressor = {"prophet", "chronos"}  # Chronos prep for 6.13

    adjusted: dict[str, float] = {}
    for model, weight in weights.items():
        if model in non_regressor:
            adjusted[model] = weight * 2.0
        elif model in regressor_dependent:
            adjusted[model] = weight * 0.3
        else:
            adjusted[model] = weight

    # Re-normalize
    total = sum(adjusted.values())
    if total > 0:
        adjusted = {k: v / total for k, v in adjusted.items()}

    logger.info(
        "Adjusted weights for no-regressor scenario",
        extra={"original": weights, "adjusted": adjusted},
    )
    return adjusted


def apply_weight_caps(weights: dict[str, float]) -> dict[str, float]:
    """Apply minimum and maximum weight caps.

    Story 6.12 AC4: Weight caps: Min 5%, Max 50% per model.

    Args:
        weights: Uncapped weights

    Returns:
        Capped and re-normalized weights
    """
    # Apply caps
    capped = {k: max(MIN_WEIGHT, min(MAX_WEIGHT, v)) for k, v in weights.items()}

    # Re-normalize
    total = sum(capped.values())
    if total > 0:
        capped = {k: v / total for k, v in capped.items()}

    return capped


def handle_model_failure(
    weights: dict[str, float],
    failed_model: str,
) -> dict[str, float]:
    """Handle model failure by removing and re-normalizing weights.

    Story 6.12 AC4: Model fails during forecast → Removed from ensemble,
    weights re-normalized.

    Args:
        weights: Current model weights
        failed_model: Name of failed model to remove

    Returns:
        Re-normalized weights without failed model
    """
    if failed_model not in weights:
        return weights

    # Remove failed model
    remaining = {k: v for k, v in weights.items() if k != failed_model}

    if not remaining:
        logger.error("All models failed, cannot re-normalize")
        return {}

    # Re-normalize
    total = sum(remaining.values())
    if total > 0:
        remaining = {k: v / total for k, v in remaining.items()}

    logger.info(
        "Re-normalized weights after model failure",
        extra={"failed_model": failed_model, "remaining": remaining},
    )
    return remaining
