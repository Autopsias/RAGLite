"""ARIMA/SARIMA model implementation using pmdarima.

Story 7.1: Add ARIMA/ETS Model Wrappers
"""

from __future__ import annotations

import logging
from typing import Any, cast

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Lazy-load pmdarima to avoid import-time penalty during test collection
_pmdarima_module = None


def _get_pmdarima() -> Any:
    """Lazy-load pmdarima module on first use.

    Returns:
        pmdarima module
    """
    global _pmdarima_module
    if _pmdarima_module is None:
        import pmdarima as pm

        _pmdarima_module = pm
    return cast(Any, _pmdarima_module)


class ARIMAFittingError(Exception):
    """Raised when ARIMA fitting fails."""

    pass


async def fit_arima(
    y_train: pd.Series,
    X_train: pd.DataFrame | None = None,
    X_future: pd.DataFrame | None = None,
    forecast_horizon: int = 4,
    frequency: str | None = None,
    confidence_level: float = 0.95,
) -> tuple[Any, dict[str, Any], np.ndarray, np.ndarray]:
    """Fit ARIMA/SARIMA using pmdarima auto_arima.

    Args:
        y_train: Historical time series data
        X_train: Exogenous regressors for training (optional)
        X_future: Exogenous regressors for forecast period (optional)
        forecast_horizon: Number of periods to forecast
        frequency: Time frequency ("M" for monthly, "Q" for quarterly), auto-detected if None
        confidence_level: Confidence interval level (default 0.95)

    Returns:
        Tuple of (model, metrics_dict, predictions, confidence_intervals)
        - model: Fitted ARIMA model object
        - metrics_dict: {"aic": float, "order": tuple, "seasonal_order": tuple}
        - predictions: numpy array of point forecasts
        - confidence_intervals: 2D array [[lower, upper], ...]

    Raises:
        ValueError: If data is insufficient for ARIMA fitting
        ARIMAFittingError: If model convergence fails
    """
    # Validate data
    if len(y_train) == 0:
        raise ValueError("y_train cannot be empty")

    # Auto-detect frequency from index if not provided
    if frequency is None:
        if hasattr(y_train, "index") and isinstance(y_train.index, pd.DatetimeIndex):
            inferred_freq = pd.infer_freq(y_train.index)
            if inferred_freq:
                if inferred_freq.startswith("M"):
                    frequency = "M"
                elif inferred_freq.startswith("Q"):
                    frequency = "Q"
        # Default to monthly if auto-detection fails
        if frequency is None:
            frequency = "M"

    # Set seasonal period based on frequency
    seasonal_period = 12 if frequency == "M" else 4

    # Handle exogenous variables gracefully
    if X_train is not None:
        if X_future is not None:
            # Validate dimensions if X_future is provided
            if len(X_future) != forecast_horizon:
                raise ValueError(
                    f"X_future must have {forecast_horizon} rows to match forecast_horizon, "
                    f"got {len(X_future)}"
                )
        else:
            # If X_train was used but X_future not provided, create naive forecast
            # Use last known values (simple forward-fill approach)
            logger.info(
                "X_train provided but X_future missing. Using last known values for forecast."
            )
            last_row = X_train.iloc[-1:].values
            X_future_values = np.repeat(last_row, forecast_horizon, axis=0)
            X_future = pd.DataFrame(X_future_values, columns=X_train.columns)

    try:
        # Get pmdarima module
        pm = _get_pmdarima()

        # Fit auto_arima model
        model = pm.auto_arima(
            y_train,
            X=X_train,
            seasonal=True,
            m=seasonal_period,
            stepwise=True,
            suppress_warnings=True,
            max_p=3,
            max_q=3,
            max_d=2,
            max_P=2,
            max_Q=2,
            max_D=1,
            information_criterion="aic",
            error_action="ignore",
        )

        # Generate predictions with confidence intervals
        # Round alpha to avoid floating point precision issues (e.g., 0.050000000000000044)
        alpha = round(1 - confidence_level, 10)
        predictions, conf_int = model.predict(
            n_periods=forecast_horizon,
            X=X_future,
            return_conf_int=True,
            alpha=alpha,
        )

        # Convert to numpy array if it's a pandas Series
        if hasattr(predictions, "values"):
            predictions = predictions.values

        # Collect metrics
        metrics = {
            "aic": model.aic(),
            "order": model.order,
            "seasonal_order": model.seasonal_order,
        }

        return model, metrics, predictions, conf_int

    except Exception as e:
        logger.warning(f"ARIMA fitting failed: {e}")
        raise ARIMAFittingError(f"Failed to fit ARIMA: {e}") from e
