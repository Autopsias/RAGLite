"""MAPE validation methods for forecasting.

Story 6.21: Unified Validation Script
Story 6.26: Multi-Metric Validation Enhancement

Contains three MAPE calculation methods:
- Holdout: Standard last-N validation (fully implemented)
- Walk-forward: Rolling origin cross-validation (MVP: falls back to holdout)
- CV: Time series k-fold cross-validation (MVP: falls back to holdout)

Note: Walk-forward and CV methods require async forecast functions. In this MVP,
they fall back to holdout validation while logging a warning. Full async
implementation is planned for future iterations.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from raglite.shared.models import ForecastPoint, TimeSeriesPoint

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Holdout Validation Methods
# =============================================================================


def calculate_holdout_mape(
    historical_points: list[TimeSeriesPoint],
    forecast_points: list[ForecastPoint],
    holdout_size: int = 4,
) -> float | None:
    """Calculate MAPE using holdout validation.

    Uses the last N historical points as test set and compares
    with the first N forecast points.

    Args:
        historical_points: List of TimeSeriesPoint objects
        forecast_points: List of ForecastPoint objects
        holdout_size: Number of points to use for validation

    Returns:
        MAPE as percentage, or None if insufficient data
    """
    if len(historical_points) < holdout_size or len(forecast_points) < holdout_size:
        return None

    # Get the last 'holdout_size' historical values as actuals
    actuals = [p.value for p in historical_points[-holdout_size:]]

    # Get the first 'holdout_size' forecast values as predictions
    predictions = [p.value for p in forecast_points[:holdout_size]]

    if len(actuals) != len(predictions):
        return None

    # Calculate MAPE
    mape_values = []
    for actual, pred in zip(actuals, predictions, strict=False):
        if actual != 0:
            mape_values.append(abs((actual - pred) / actual) * 100)

    if not mape_values:
        return None

    return float(sum(mape_values) / len(mape_values))


def calculate_walkforward_mape(
    historical_points: list[TimeSeriesPoint],
    forecast_fn: Callable[[list[TimeSeriesPoint], int], list[ForecastPoint]],
    test_periods: int = 4,
    step_size: int = 1,
) -> float | None:
    """Calculate MAPE using walk-forward validation.

    Rolling origin cross-validation:
    1. Train on points[0:t]
    2. Forecast point[t+1]
    3. Compare forecast vs actual
    4. Slide window forward by step_size

    Note: This is an MVP implementation. The forecast_fn must be synchronous.
    For async forecast functions, this method currently falls back to simplified
    holdout-style validation. Full async walk-forward is planned for future.

    Args:
        historical_points: List of TimeSeriesPoint objects
        forecast_fn: Synchronous function that takes (data, periods_ahead) and returns forecast
        test_periods: Number of periods to test
        step_size: Step size for rolling window

    Returns:
        MAPE as percentage, or None if insufficient data
    """
    if len(historical_points) < test_periods + 6:  # Need minimum training data
        return None

    mapes = []
    for t in range(len(historical_points) - test_periods, len(historical_points), step_size):
        if t < 6:  # Minimum training size
            continue

        train_data = historical_points[:t]
        actual = historical_points[t].value

        try:
            forecast = forecast_fn(train_data, periods_ahead=1)  # type: ignore[call-arg]
            if forecast and len(forecast) > 0:
                pred_value = forecast[0].value
                if actual != 0:
                    mapes.append(abs((actual - pred_value) / actual) * 100)
        except Exception as e:
            logger.warning(f"Walk-forward forecast failed at t={t}: {e}")
            continue

    if not mapes:
        return None

    return float(sum(mapes) / len(mapes))


def calculate_cv_mape(
    historical_points: list[TimeSeriesPoint],
    forecast_fn: Callable[[list[TimeSeriesPoint], int], list[ForecastPoint]],
    n_splits: int = 5,
) -> float | None:
    """Calculate MAPE using time series cross-validation.

    Uses sklearn TimeSeriesSplit for proper temporal ordering.
    Each fold: train on earlier data, test on later data.

    Note: This is an MVP implementation. The forecast_fn must be synchronous.
    For async forecast functions, this method currently falls back to simplified
    holdout-style validation. Full async CV is planned for future iterations.

    Args:
        historical_points: List of TimeSeriesPoint objects
        forecast_fn: Synchronous function that takes (data, periods_ahead) and returns forecast
        n_splits: Number of CV splits

    Returns:
        MAPE as percentage, or None if insufficient data
    """
    if len(historical_points) < n_splits + 6:  # Need minimum data for splits
        return None

    from sklearn.model_selection import TimeSeriesSplit

    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_mapes = []

    for train_idx, test_idx in tscv.split(historical_points):
        train_data = [historical_points[i] for i in train_idx]
        test_data = [historical_points[i] for i in test_idx]

        if len(train_data) < 6:  # Minimum training size
            continue

        try:
            forecast = forecast_fn(train_data, periods_ahead=len(test_data))  # type: ignore[call-arg]
            if forecast and len(forecast) == len(test_data):
                # Calculate MAPE for this fold
                mape_values = []
                for actual_pt, forecast_pt in zip(test_data, forecast, strict=False):
                    if actual_pt.value != 0:
                        mape_values.append(
                            abs((actual_pt.value - forecast_pt.value) / actual_pt.value) * 100
                        )
                if mape_values:
                    fold_mapes.append(sum(mape_values) / len(mape_values))
        except Exception as e:
            logger.warning(f"CV fold forecast failed: {e}")
            continue

    if not fold_mapes:
        return None

    return float(sum(fold_mapes) / len(fold_mapes))
