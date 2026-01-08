"""Backtest functions for adaptive weight calculation.

Contains helper functions for running backtests on individual models
and calculating metrics from backtest results.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from raglite.shared.models import TimeSeriesData

logger = get_logger(__name__)

# Weight caps
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
    from raglite.shared.config import settings

    if models is None:
        models = settings.forecasting_models.split(",")

    # Need at least 12 data points for meaningful backtest
    if len(historical_data.points) < 12:
        logger.warning(
            "Insufficient data for backtest",
            extra={"metric": metric, "data_points": len(historical_data.points)},
        )
        return {}

    # Prepare data and split
    df = pd.DataFrame(
        {
            "ds": [p.date for p in historical_data.points],
            "y": [p.value for p in historical_data.points],
        }
    )
    df = df.sort_values("ds").reset_index(drop=True)

    split_result = _prepare_train_test_split(df, metric)
    if split_result is None:
        return {}
    train_df, test_df = split_result

    # Build feature matrix
    feature_data = _build_feature_matrix(train_df, test_df, external_regressors)
    if feature_data is None:
        return {}
    X_train, X_test, y_train, y_test = feature_data

    # Evaluate each model
    results: dict[str, dict[str, float]] = {}
    has_features = len(X_train.columns) > 0

    for model_name in models:
        try:
            result = _backtest_model(
                model_name,
                train_df,
                test_df,
                X_train,
                X_test,
                y_train,
                y_test,
                has_features,
                metric,
            )
            if result:
                results[model_name] = result

        except Exception as e:
            logger.warning(
                f"Backtest failed for {model_name}",
                extra={"metric": metric, "error": str(e)},
            )
            continue

    # Calculate weights from RMSE
    if results:
        from raglite.forecasting.adaptive_weights.weights import _calculate_weights_from_rmse

        results = _calculate_weights_from_rmse(results)

    return results


def _prepare_train_test_split(
    df: pd.DataFrame, metric: str
) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Prepare train/test split for backtesting.

    Rolling backtest: train on first 75%, test on last 25%.
    0.75 is a standard ML practice for time series train/test splits (AC3 requirement).

    Args:
        df: Input DataFrame with 'ds' and 'y' columns
        metric: Metric name for logging

    Returns:
        Tuple of (train_df, test_df) or None if test set too small
    """
    train_size = int(len(df) * 0.75)
    train_df = df.iloc[:train_size]
    test_df = df.iloc[train_size:]

    if len(test_df) < 3:
        logger.warning(
            "Test set too small for backtest",
            extra={"metric": metric, "test_size": len(test_df)},
        )
        return None

    return train_df, test_df


def _build_feature_matrix(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    external_regressors: dict[str, pd.Series] | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, np.ndarray] | None:
    """Build feature matrix for sklearn models from external regressors.

    Args:
        train_df: Training DataFrame with 'ds' and 'y' columns
        test_df: Test DataFrame with 'ds' and 'y' columns
        external_regressors: Optional external regressor series

    Returns:
        Tuple of (X_train, X_test, y_train, y_test) or None if no features
    """
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

    return X_train, X_test, y_train, y_test


def _backtest_prophet_model(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    y_test: np.ndarray,
    metric: str,
) -> dict[str, float] | None:
    """Backtest Prophet model.

    Prophet uses synchronous fitting for backtest (no async needed).
    Story 6.12 AC3 fix: Include Prophet in backtest.

    Args:
        train_df: Training DataFrame with 'ds' and 'y' columns
        test_df: Test DataFrame with 'ds' column for prediction
        y_test: Actual test values
        metric: Metric name for logging

    Returns:
        Dict with 'rmse', 'mape', 'data_points' or None if failed
    """
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
        rmse, mape = _calculate_model_metrics(y_test, predictions)

        result = {
            "rmse": rmse,
            "mape": mape,
            "data_points": len(y_test),
        }

        logger.info(
            "Backtest completed for prophet",
            extra={"metric": metric, "rmse": rmse, "mape": mape},
        )
        return result

    except ImportError:
        logger.warning("Prophet not available for backtest")
        return None
    except Exception as e:
        logger.warning(
            "Prophet backtest failed",
            extra={"metric": metric, "error": str(e)},
        )
        return None


def _backtest_sklearn_model(
    model_name: str,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: np.ndarray,
    metric: str,
) -> dict[str, float] | None:
    """Backtest sklearn-based model (linear, catboost, etc.).

    Args:
        model_name: Name of the model ('linear', 'catboost', etc.)
        X_train: Training features
        X_test: Test features
        y_train: Training target values
        y_test: Actual test values
        metric: Metric name for logging

    Returns:
        Dict with 'rmse', 'mape', 'data_points' or None if not supported
    """
    from raglite.forecasting.hybrid import fit_catboost, fit_linear_regression

    if model_name == "linear":
        model, _ = fit_linear_regression(X_train, y_train, list(X_train.columns))
        predictions = model.predict(X_test)

    # TODO: Implement XGBoost and LightGBM models in hybrid.py
    # elif model_name == "xgboost":
    #     model, _ = fit_xgboost(X_train, y_train, fast_mode=True)
    #     predictions = model.predict(X_test)

    # elif model_name == "lightgbm":
    #     model, _ = fit_lightgbm(X_train, y_train, fast_mode=True)
    #     predictions = model.predict(X_test)

    elif model_name == "catboost":
        model, _ = fit_catboost(X_train, y_train, fast_mode=True)
        predictions = model.predict(X_test)

    else:
        return None

    # Calculate metrics
    rmse, mape = _calculate_model_metrics(y_test, predictions)

    result = {
        "rmse": rmse,
        "mape": mape,
        "data_points": len(y_test),
    }

    logger.info(
        f"Backtest completed for {model_name}",
        extra={"metric": metric, "rmse": rmse, "mape": mape},
    )
    return result


def _backtest_model(
    model_name: str,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: np.ndarray,
    has_features: bool,
    metric: str,
) -> dict[str, float] | None:
    """Backtest a single model.

    Routes to appropriate backtest function based on model type.

    Args:
        model_name: Name of the model to backtest
        train_df: Training DataFrame
        test_df: Test DataFrame
        X_train: Training features
        X_test: Test features
        y_train: Training target values
        y_test: Actual test values
        has_features: Whether external features are available
        metric: Metric name for logging

    Returns:
        Dict with 'rmse', 'mape', 'data_points' or None if skipped/failed
    """
    if model_name == "prophet":
        return _backtest_prophet_model(train_df, test_df, y_test, metric)

    # Sklearn-based models need features
    if has_features and model_name in ("linear", "catboost"):
        return _backtest_sklearn_model(model_name, X_train, X_test, y_train, y_test, metric)

    # Skip models that require features when none available
    return None


def _calculate_model_metrics(y_test: np.ndarray, predictions: np.ndarray) -> tuple[float, float]:
    """Calculate RMSE and MAPE for model predictions.

    Args:
        y_test: Actual test values
        predictions: Predicted values

    Returns:
        Tuple of (rmse, mape)
    """
    rmse = float(np.sqrt(np.mean((y_test - predictions) ** 2)))
    non_zero_mask = y_test != 0
    if non_zero_mask.any():
        mape = float(
            np.mean(
                np.abs((y_test[non_zero_mask] - predictions[non_zero_mask]) / y_test[non_zero_mask])
            )
            * 100
        )
    else:
        mape = 0.0

    return rmse, mape
