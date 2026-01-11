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


def _detect_frequency(y_train: pd.Series, frequency: str | None) -> str:
    """Auto-detect frequency from time series index.

    Args:
        y_train: Time series data with DatetimeIndex
        frequency: User-provided frequency (skip detection if not None)

    Returns:
        Frequency code ("M" for monthly, "Q" for quarterly)
    """
    if frequency is not None:
        return frequency

    # Auto-detect from index
    if hasattr(y_train, "index") and isinstance(y_train.index, pd.DatetimeIndex):
        inferred_freq = pd.infer_freq(y_train.index)
        if inferred_freq:
            if inferred_freq.startswith("M"):
                return "M"
            elif inferred_freq.startswith("Q"):
                return "Q"

    # Default to monthly if auto-detection fails
    return "M"


def _prepare_exogenous_forecast(
    X_train: pd.DataFrame | None,
    X_future: pd.DataFrame | None,
    forecast_horizon: int,
) -> pd.DataFrame | None:
    """Prepare exogenous variables for forecast period.

    Args:
        X_train: Training exogenous variables
        X_future: Future exogenous variables (may be None)
        forecast_horizon: Number of periods to forecast

    Returns:
        DataFrame with exogenous variables for forecast period

    Raises:
        ValueError: If X_future has wrong dimensions
    """
    if X_train is None:
        return None

    if X_future is not None:
        # Validate dimensions
        if len(X_future) != forecast_horizon:
            raise ValueError(
                f"X_future must have {forecast_horizon} rows to match forecast_horizon, "
                f"got {len(X_future)}"
            )
        return X_future

    # If X_train was used but X_future not provided, create naive forecast
    # Use last known values (simple forward-fill approach)
    logger.info("X_train provided but X_future missing. Using last known values for forecast.")
    last_row = X_train.iloc[-1:].values
    X_future_values = np.repeat(last_row, forecast_horizon, axis=0)
    return pd.DataFrame(X_future_values, columns=X_train.columns)


def _fit_arima_model(
    y_train: pd.Series,
    X_train: pd.DataFrame | None,
    seasonal_period: int,
) -> Any:
    """Fit ARIMA model using pmdarima auto_arima.

    Args:
        y_train: Historical time series data
        X_train: Exogenous regressors for training
        seasonal_period: Seasonal period (12 for monthly, 4 for quarterly)

    Returns:
        Fitted ARIMA model object
    """
    pm = _get_pmdarima()
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
    return model


def _generate_arima_predictions(
    model: Any,
    forecast_horizon: int,
    X_future: pd.DataFrame | None,
    confidence_level: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate predictions with confidence intervals.

    Args:
        model: Fitted ARIMA model
        forecast_horizon: Number of periods to forecast
        X_future: Exogenous regressors for forecast period
        confidence_level: Confidence interval level

    Returns:
        Tuple of (predictions, confidence_intervals)
    """
    # Round alpha to avoid floating point precision issues
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

    return predictions, conf_int


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
    frequency = _detect_frequency(y_train, frequency)

    # Set seasonal period based on frequency
    seasonal_period = 12 if frequency == "M" else 4

    # Prepare exogenous variables for forecast period
    X_future = _prepare_exogenous_forecast(X_train, X_future, forecast_horizon)

    try:
        # Fit ARIMA model
        model = _fit_arima_model(y_train, X_train, seasonal_period)

        # Generate predictions with confidence intervals
        predictions, conf_int = _generate_arima_predictions(
            model, forecast_horizon, X_future, confidence_level
        )

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
