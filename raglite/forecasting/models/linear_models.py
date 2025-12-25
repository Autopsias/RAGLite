"""Linear regression models for time-series forecasting.

Story 6.4 AC3: Linear Regression, Ridge, Lasso for ensemble.
Story 6.8 AC5: Ridge and Lasso regularization.
Story 7.5: Extracted from hybrid.py for modularity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from sklearn.linear_model import LinearRegression

logger = get_logger(__name__)

# Global flag for lazy loading
_sklearn_loaded = False


def _get_linear_regression() -> Any:
    """Lazy-load LinearRegression from sklearn."""
    global _sklearn_loaded
    if not _sklearn_loaded:
        from sklearn.linear_model import LinearRegression

        _sklearn_loaded = True
        return LinearRegression
    from sklearn.linear_model import LinearRegression

    return LinearRegression


def _get_ridge_regression() -> Any:
    """Lazy-load Ridge regression from sklearn.

    Story 6.8 AC5: Ridge regression for regularized linear models.
    """
    from sklearn.linear_model import Ridge

    return Ridge


def _get_lasso_regression() -> Any:
    """Lazy-load Lasso regression from sklearn.

    Story 6.8 AC5: Lasso regression for L1 regularization (feature selection).
    """
    from sklearn.linear_model import Lasso

    return Lasso


def _get_time_series_split() -> Any:
    """Lazy-load TimeSeriesSplit from sklearn."""
    from sklearn.model_selection import TimeSeriesSplit

    return TimeSeriesSplit


def fit_linear_regression(
    X: pd.DataFrame,
    y: pd.Series,
    feature_names: list[str],
) -> tuple[LinearRegression, dict[str, float]]:
    """Fit Linear Regression with external regressors.

    Story 6.4 AC3: Linear Regression for ensemble.

    Args:
        X: Feature DataFrame (regressors)
        y: Target series (metric values)
        feature_names: Names of features for logging

    Returns:
        Tuple of (fitted LinearRegression model, accuracy metrics dict with rmse/mae/mape)
    """
    LinearRegression = _get_linear_regression()
    TimeSeriesSplit = _get_time_series_split()

    model = LinearRegression()

    # Time-series cross-validation (5-fold)
    tscv = TimeSeriesSplit(n_splits=min(5, len(X) - 1))
    cv_rmse_scores: list[float] = []
    cv_mae_scores: list[float] = []
    cv_mape_scores: list[float] = []

    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model.fit(X_train, y_train)
        predictions = model.predict(X_val)

        # RMSE: Root Mean Squared Error
        rmse = float(np.sqrt(np.mean((y_val.values - predictions) ** 2)))
        cv_rmse_scores.append(rmse)

        # MAE: Mean Absolute Error
        mae = float(np.mean(np.abs(y_val.values - predictions)))
        cv_mae_scores.append(mae)

        # MAPE: Mean Absolute Percentage Error (avoid division by zero)
        y_vals = y_val.values
        non_zero_mask = y_vals != 0
        if non_zero_mask.any():
            mape = float(
                np.mean(
                    np.abs(
                        (y_vals[non_zero_mask] - predictions[non_zero_mask]) / y_vals[non_zero_mask]
                    )
                )
                * 100
            )
        else:
            mape = 0.0
        cv_mape_scores.append(mape)

    # Final fit on all data
    model.fit(X, y)

    metrics = {
        "rmse": float(np.mean(cv_rmse_scores)) if cv_rmse_scores else 0.0,
        "mae": float(np.mean(cv_mae_scores)) if cv_mae_scores else 0.0,
        "mape": float(np.mean(cv_mape_scores)) if cv_mape_scores else 0.0,
    }

    logger.info(
        "Linear Regression fitted",
        extra={"features": feature_names, "cv_rmse": metrics["rmse"], "cv_mae": metrics["mae"]},
    )

    return model, metrics


def fit_ridge_regression(
    X: pd.DataFrame,
    y: pd.Series,
    feature_names: list[str],
    alpha: float = 1.0,
) -> tuple[Any, dict[str, float]]:
    """Fit Ridge Regression with L2 regularization.

    Story 6.8 AC5: Ridge regression for regularized linear models.

    Ridge regression adds L2 penalty to prevent overfitting:
    - Reduces coefficient magnitudes
    - Works well with multicollinearity
    - Never zeroes out coefficients

    Args:
        X: Feature DataFrame (regressors)
        y: Target series (metric values)
        feature_names: Names of features for logging
        alpha: Regularization strength (default: 1.0)

    Returns:
        Tuple of (fitted Ridge model, accuracy metrics dict with rmse/mae/mape)
    """
    Ridge = _get_ridge_regression()
    TimeSeriesSplit = _get_time_series_split()

    model = Ridge(alpha=alpha)

    # Time-series cross-validation (5-fold)
    tscv = TimeSeriesSplit(n_splits=min(5, len(X) - 1))
    cv_rmse_scores: list[float] = []
    cv_mae_scores: list[float] = []
    cv_mape_scores: list[float] = []

    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model.fit(X_train, y_train)
        predictions = model.predict(X_val)

        rmse = float(np.sqrt(np.mean((y_val.values - predictions) ** 2)))
        cv_rmse_scores.append(rmse)

        mae = float(np.mean(np.abs(y_val.values - predictions)))
        cv_mae_scores.append(mae)

        y_vals = y_val.values
        non_zero_mask = y_vals != 0
        if non_zero_mask.any():
            mape = float(
                np.mean(
                    np.abs(
                        (y_vals[non_zero_mask] - predictions[non_zero_mask]) / y_vals[non_zero_mask]
                    )
                )
                * 100
            )
        else:
            mape = 0.0
        cv_mape_scores.append(mape)

    # Final fit on all data
    model.fit(X, y)

    metrics = {
        "rmse": float(np.mean(cv_rmse_scores)) if cv_rmse_scores else 0.0,
        "mae": float(np.mean(cv_mae_scores)) if cv_mae_scores else 0.0,
        "mape": float(np.mean(cv_mape_scores)) if cv_mape_scores else 0.0,
    }

    logger.info(
        "Ridge Regression fitted",
        extra={
            "features": feature_names,
            "alpha": alpha,
            "cv_rmse": metrics["rmse"],
            "cv_mae": metrics["mae"],
        },
    )

    return model, metrics


def fit_lasso_regression(
    X: pd.DataFrame,
    y: pd.Series,
    feature_names: list[str],
    alpha: float = 1.0,
) -> tuple[Any, dict[str, float]]:
    """Fit Lasso Regression with L1 regularization.

    Story 6.8 AC5: Lasso regression for L1 regularization (feature selection).

    Lasso regression adds L1 penalty for automatic feature selection:
    - Can zero out coefficients (sparse models)
    - Good for high-dimensional data
    - Built-in feature selection

    Args:
        X: Feature DataFrame (regressors)
        y: Target series (metric values)
        feature_names: Names of features for logging
        alpha: Regularization strength (default: 1.0)

    Returns:
        Tuple of (fitted Lasso model, accuracy metrics dict with rmse/mae/mape)
    """
    Lasso = _get_lasso_regression()
    TimeSeriesSplit = _get_time_series_split()

    model = Lasso(alpha=alpha, max_iter=10000)

    # Time-series cross-validation (5-fold)
    tscv = TimeSeriesSplit(n_splits=min(5, len(X) - 1))
    cv_rmse_scores: list[float] = []
    cv_mae_scores: list[float] = []
    cv_mape_scores: list[float] = []

    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model.fit(X_train, y_train)
        predictions = model.predict(X_val)

        rmse = float(np.sqrt(np.mean((y_val.values - predictions) ** 2)))
        cv_rmse_scores.append(rmse)

        mae = float(np.mean(np.abs(y_val.values - predictions)))
        cv_mae_scores.append(mae)

        y_vals = y_val.values
        non_zero_mask = y_vals != 0
        if non_zero_mask.any():
            mape = float(
                np.mean(
                    np.abs(
                        (y_vals[non_zero_mask] - predictions[non_zero_mask]) / y_vals[non_zero_mask]
                    )
                )
                * 100
            )
        else:
            mape = 0.0
        cv_mape_scores.append(mape)

    # Final fit on all data
    model.fit(X, y)

    metrics = {
        "rmse": float(np.mean(cv_rmse_scores)) if cv_rmse_scores else 0.0,
        "mae": float(np.mean(cv_mae_scores)) if cv_mae_scores else 0.0,
        "mape": float(np.mean(cv_mape_scores)) if cv_mape_scores else 0.0,
    }

    # Log non-zero coefficients for Lasso (feature selection insight)
    non_zero_coefs = sum(1 for c in model.coef_ if abs(c) > 1e-10)

    logger.info(
        "Lasso Regression fitted",
        extra={
            "features": feature_names,
            "alpha": alpha,
            "cv_rmse": metrics["rmse"],
            "cv_mae": metrics["mae"],
            "selected_features": non_zero_coefs,
            "total_features": len(feature_names),
        },
    )

    return model, metrics


def _fit_and_forecast_linear(
    X: pd.DataFrame,
    y: pd.Series,
    X_future: pd.DataFrame,
    feature_names: list[str],
    periods_ahead: int,
) -> dict[str, Any]:
    """Fit Linear Regression and generate forecast (for ThreadPoolExecutor).

    Story 6.4 AC5: Combined fit+forecast for parallel execution.

    Args:
        X: Training feature DataFrame
        y: Target series
        X_future: Future feature values for prediction
        feature_names: Names of features
        periods_ahead: Number of periods to forecast

    Returns:
        Dict with 'values' list and 'metrics' dict
    """
    model, metrics = fit_linear_regression(X, y, feature_names)
    predictions = model.predict(X_future)
    return {
        "values": predictions.tolist()[:periods_ahead],
        "metrics": metrics,
    }


def _run_linear_forecast(
    model: LinearRegression,
    X_future: pd.DataFrame,
    periods_ahead: int,
) -> dict[str, object]:
    """Run Linear Regression forecast prediction.

    This is a synchronous function designed to be called via ThreadPoolExecutor
    for parallel ensemble execution alongside async Prophet.

    Args:
        model: Fitted LinearRegression model from sklearn
        X_future: Future feature values (regressors extrapolated forward)
        periods_ahead: Number of periods to forecast

    Returns:
        Dict with 'values' list of predictions and 'metrics' dict
    """
    try:
        predictions = model.predict(X_future)
        return {
            "values": predictions.tolist()[:periods_ahead],
            "metrics": {"model": "linear"},
        }
    except Exception as e:
        logger.warning(f"Linear forecast failed: {e}")
        raise
