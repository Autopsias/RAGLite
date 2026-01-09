"""Parallel forecasting utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from sklearn.linear_model import LinearRegression

from raglite.forecasting.hybrid.ml_models_utils._regression_models import fit_linear_regression
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


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
