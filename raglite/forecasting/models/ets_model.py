"""ETS (Exponential Smoothing) model implementation using statsmodels.

Story 7.1: Add ARIMA/ETS Model Wrappers
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

logger = logging.getLogger(__name__)


class ETSFittingError(Exception):
    """Raised when ETS fitting fails."""

    pass


async def fit_ets(
    y_train: pd.Series,
    forecast_horizon: int = 4,
    frequency: str = "M",
    trend: str | None = "add",
    seasonal: str | None = "add",
    damped_trend: bool = True,
    confidence_level: float = 0.95,
) -> tuple[Any, dict[str, Any], np.ndarray, np.ndarray]:
    """Fit ETS using statsmodels ExponentialSmoothing.

    Args:
        y_train: Historical time series data
        forecast_horizon: Number of periods to forecast
        frequency: Time frequency ("M" for monthly, "Q" for quarterly)
        trend: Trend component type ("add", "mul", None)
        seasonal: Seasonal component type ("add", "mul", None)
        damped_trend: Whether to use damped trend
        confidence_level: Confidence interval level (default 0.95)

    Returns:
        Tuple of (model, metrics_dict, predictions, confidence_intervals)
        - model: Fitted ETS model object
        - metrics_dict: {"aic": float, "bic": float, "sse": float}
        - predictions: numpy array of point forecasts
        - confidence_intervals: 2D array [[lower, upper], ...]

    Raises:
        ValueError: If data is insufficient for ETS fitting
        ETSFittingError: If model optimization fails
    """
    # Validate data
    if len(y_train) == 0:
        raise ValueError("y_train cannot be empty")

    # Set seasonal periods based on frequency
    seasonal_periods = 12 if frequency == "M" else 4

    # Ensure data length supports seasonality
    if len(y_train) < 2 * seasonal_periods:
        seasonal = None  # Disable seasonality for short series

    # Validate for multiplicative components (require positive values)
    if trend == "mul" or seasonal == "mul":
        if (y_train <= 0).any():
            raise ValueError("Multiplicative trend/seasonal components require all positive values")

    try:
        # Fit ETS model
        model = ExponentialSmoothing(
            y_train,
            trend=trend,
            seasonal=seasonal,
            damped_trend=damped_trend if trend else False,
            seasonal_periods=seasonal_periods if seasonal else None,
        ).fit(optimized=True)

        # Generate forecast using forecast() method
        # Note: ExponentialSmoothing uses forecast(), not get_forecast()
        predictions = model.forecast(steps=forecast_horizon)

        # Convert to numpy array if it's a pandas Series
        if hasattr(predictions, "values"):
            predictions = predictions.values

        # Generate confidence intervals using simulation or approximation
        # statsmodels ExponentialSmoothing doesn't have built-in CI via get_forecast()
        # Use standard error from model residuals as approximation
        from scipy import stats

        # Use standard error from model residuals
        if hasattr(model, "fittedvalues") and len(model.fittedvalues) > 0:
            residuals = y_train - model.fittedvalues
            std_error = np.std(residuals)
        else:
            # Fallback for mocked models or when fittedvalues unavailable
            std_error = np.std(y_train) * 0.1  # Conservative estimate

        # Calculate confidence intervals
        z_score = stats.norm.ppf(1 - (1 - confidence_level) / 2)
        lower = predictions - z_score * std_error
        upper = predictions + z_score * std_error
        conf_int = np.column_stack([lower, upper])

        # Collect metrics
        metrics = {
            "aic": model.aic,
            "bic": model.bic,
            "sse": model.sse,
        }

        return model, metrics, predictions, conf_int

    except Exception as e:
        logger.warning(f"ETS fitting failed: {e}")
        raise ETSFittingError(f"Failed to fit ETS: {e}") from e
