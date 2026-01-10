"""Regression model fitting functions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from sklearn.linear_model import LinearRegression

from raglite.forecasting.hybrid.lazy_imports import (
    _get_lasso_regression,
    _get_linear_regression,
    _get_ridge_regression,
    _get_time_series_split,
)
from raglite.forecasting.hybrid.ml_models_utils._cv_metrics import (
    append_fold_metrics,
    calculate_cv_metrics,
    calculate_fold_metrics,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


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

        rmse, mae, mape = calculate_fold_metrics(y_val, predictions)
        append_fold_metrics(cv_rmse_scores, cv_mae_scores, cv_mape_scores, rmse, mae, mape)

    # Final fit on all data
    model.fit(X, y)

    # Calculate final metrics on full dataset
    final_predictions = model.predict(X)
    metrics = calculate_cv_metrics(
        y, final_predictions, cv_rmse_scores, cv_mae_scores, cv_mape_scores
    )

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

        rmse, mae, mape = calculate_fold_metrics(y_val, predictions)
        append_fold_metrics(cv_rmse_scores, cv_mae_scores, cv_mape_scores, rmse, mae, mape)

    # Final fit on all data
    model.fit(X, y)

    # Calculate final metrics on full dataset
    final_predictions = model.predict(X)
    metrics = calculate_cv_metrics(
        y, final_predictions, cv_rmse_scores, cv_mae_scores, cv_mape_scores
    )

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

        rmse, mae, mape = calculate_fold_metrics(y_val, predictions)
        append_fold_metrics(cv_rmse_scores, cv_mae_scores, cv_mape_scores, rmse, mae, mape)

    # Final fit on all data
    model.fit(X, y)

    # Calculate final metrics on full dataset
    final_predictions = model.predict(X)
    metrics = calculate_cv_metrics(
        y, final_predictions, cv_rmse_scores, cv_mae_scores, cv_mape_scores
    )

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
