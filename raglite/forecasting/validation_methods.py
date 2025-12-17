"""Multi-metric forecasting validation methods.

Story 6.21: Unified Validation Script
Story 6.26: Multi-Metric Validation Enhancement

Contains validation metrics:
- MAPE: Mean Absolute Percentage Error (percentage deviation)
- MASE: Mean Absolute Scaled Error (scale-free, naïve benchmark)
- SMAPE: Symmetric MAPE (bounded 0-200%, handles zeros better)
- RMSE: Root Mean Square Error (penalizes large errors)
- MAE: Mean Absolute Error (simple absolute error)
- Bias: Mean Error (systematic over/under-prediction)

Plus three MAPE calculation methods:
- Holdout: Standard last-N validation (fully implemented)
- Walk-forward: Rolling origin cross-validation (MVP: falls back to holdout)
- CV: Time series k-fold cross-validation (MVP: falls back to holdout)

Note: Walk-forward and CV methods require async forecast functions. In this MVP,
they fall back to holdout validation while logging a warning. Full async
implementation is planned for future iterations.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from raglite.shared.models import ForecastPoint, TimeSeriesPoint

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Multi-Metric Result Dataclass
# =============================================================================


@dataclass
class MultiMetricResult:
    """Result container for all validation metrics.

    Attributes:
        mape: Mean Absolute Percentage Error (percentage, None if undefined)
        mase: Mean Absolute Scaled Error (scale-free, <1.0 means better than naïve)
        smape: Symmetric MAPE (bounded 0-200%)
        rmse: Root Mean Square Error (same units as data)
        mae: Mean Absolute Error (same units as data)
        bias: Mean Error (positive = over-prediction, negative = under-prediction)
    """

    mape: float | None
    mase: float | None
    smape: float | None
    rmse: float | None
    mae: float | None
    bias: float | None


# =============================================================================
# Core Metric Calculation Functions
# =============================================================================


def calculate_mape_from_arrays(
    actuals: np.ndarray,
    predictions: np.ndarray,
) -> float | None:
    """Calculate MAPE from numpy arrays.

    MAPE = mean(|actual - predicted| / |actual|) * 100

    Args:
        actuals: Array of actual values
        predictions: Array of predicted values

    Returns:
        MAPE as percentage, or None if all actuals are zero
    """
    if len(actuals) == 0 or len(predictions) == 0:
        return None

    # Filter out zero actuals to avoid division by zero
    non_zero_mask = actuals != 0
    if not np.any(non_zero_mask):
        return None

    filtered_actuals = actuals[non_zero_mask]
    filtered_predictions = predictions[non_zero_mask]

    mape = np.mean(np.abs((filtered_actuals - filtered_predictions) / filtered_actuals)) * 100
    return float(mape)


def calculate_mase(
    actuals: np.ndarray,
    predictions: np.ndarray,
    historical_data: np.ndarray,
    seasonality: int = 12,
) -> float | None:
    """Calculate Mean Absolute Scaled Error (MASE).

    MASE = MAE / naïve_MAE

    Where naïve_MAE is the mean absolute error of a seasonal naïve forecast
    (predicting the value from `seasonality` periods ago).

    MASE < 1.0 means the model outperforms the naïve baseline.
    MASE > 1.0 means the naïve forecast would be better.

    Reference: Hyndman & Koehler (2006) - "Another look at measures of forecast accuracy"

    Args:
        actuals: Array of actual values (test set)
        predictions: Array of predicted values
        historical_data: Array of historical values used for naïve error calculation
        seasonality: Seasonal period (default 12 for monthly data)

    Returns:
        MASE value, or None if calculation is not possible
    """
    if len(actuals) == 0 or len(predictions) == 0:
        return None

    if len(historical_data) <= seasonality:
        # Not enough historical data for seasonal naïve
        # Fall back to random walk naïve (1-step lag)
        seasonality = 1

    # Calculate naïve forecast error (seasonal random walk)
    naive_errors = np.abs(historical_data[seasonality:] - historical_data[:-seasonality])
    naive_mae = np.mean(naive_errors)

    if naive_mae == 0:
        # If naïve error is zero, series is constant - return infinity
        logger.warning("Naïve MAE is zero (constant series), MASE undefined")
        return float("inf")

    # Calculate forecast MAE
    forecast_mae = np.mean(np.abs(actuals - predictions))

    mase = forecast_mae / naive_mae
    return float(mase)


def calculate_smape(
    actuals: np.ndarray,
    predictions: np.ndarray,
) -> float | None:
    """Calculate Symmetric Mean Absolute Percentage Error (SMAPE).

    SMAPE = mean(2 * |actual - predicted| / (|actual| + |predicted|)) * 100

    SMAPE is bounded between 0 and 200%, and handles zeros better than MAPE
    because it uses the average of actual and predicted in the denominator.

    Args:
        actuals: Array of actual values
        predictions: Array of predicted values

    Returns:
        SMAPE as percentage (0-200), or None if all denominators are zero
    """
    if len(actuals) == 0 or len(predictions) == 0:
        return None

    denominator = np.abs(actuals) + np.abs(predictions)

    # Filter out cases where both actual and predicted are zero
    non_zero_mask = denominator != 0
    if not np.any(non_zero_mask):
        return 0.0  # Both are zero everywhere - perfect match

    filtered_actuals = actuals[non_zero_mask]
    filtered_predictions = predictions[non_zero_mask]
    filtered_denominator = denominator[non_zero_mask]

    smape = (
        np.mean(2 * np.abs(filtered_actuals - filtered_predictions) / filtered_denominator) * 100
    )
    return float(smape)


def calculate_rmse(
    actuals: np.ndarray,
    predictions: np.ndarray,
) -> float | None:
    """Calculate Root Mean Square Error (RMSE).

    RMSE = sqrt(mean((actual - predicted)^2))

    RMSE penalizes larger errors more than MAE due to squaring.
    Useful when large errors are particularly costly.

    Args:
        actuals: Array of actual values
        predictions: Array of predicted values

    Returns:
        RMSE in the same units as the data, or None if arrays are empty
    """
    if len(actuals) == 0 or len(predictions) == 0:
        return None

    rmse = np.sqrt(np.mean((actuals - predictions) ** 2))
    return float(rmse)


def calculate_mae(
    actuals: np.ndarray,
    predictions: np.ndarray,
) -> float | None:
    """Calculate Mean Absolute Error (MAE).

    MAE = mean(|actual - predicted|)

    Simple, interpretable error metric in the same units as the data.
    More robust to outliers than RMSE.

    Args:
        actuals: Array of actual values
        predictions: Array of predicted values

    Returns:
        MAE in the same units as the data, or None if arrays are empty
    """
    if len(actuals) == 0 or len(predictions) == 0:
        return None

    mae = np.mean(np.abs(actuals - predictions))
    return float(mae)


def calculate_bias(
    actuals: np.ndarray,
    predictions: np.ndarray,
) -> float | None:
    """Calculate Mean Error (Bias).

    Bias = mean(predicted - actual)

    Positive bias indicates systematic over-prediction.
    Negative bias indicates systematic under-prediction.
    Near-zero bias indicates well-calibrated forecasts.

    Args:
        actuals: Array of actual values
        predictions: Array of predicted values

    Returns:
        Bias in the same units as the data, or None if arrays are empty
    """
    if len(actuals) == 0 or len(predictions) == 0:
        return None

    bias = np.mean(predictions - actuals)
    return float(bias)


def validate_metric_consistency(
    holdout_mape: float | None,
    metrics_mape: float | None,
    threshold: float = 10.0,
    variable_name: str = "",
) -> bool:
    """Detect when metrics are calculated on misaligned data.

    Story 6.27: Sanity check for MAPE/MASE alignment.

    If holdout_mape (from Prophet CV or manual holdout) and metrics_mape
    (from calculate_all_metrics) differ by more than threshold×, something
    is wrong with data alignment - typically comparing different time periods.

    Args:
        holdout_mape: MAPE from holdout validation (percentage)
        metrics_mape: MAPE from calculate_all_metrics (percentage)
        threshold: Maximum acceptable ratio between the two (default 10×)
        variable_name: Optional variable name for logging

    Returns:
        True if metrics are consistent, False if misalignment detected
    """
    if holdout_mape is None or metrics_mape is None:
        return True

    # Avoid division by tiny numbers
    if holdout_mape < 0.01 or metrics_mape < 0.01:
        return True

    ratio = max(holdout_mape, metrics_mape) / min(holdout_mape, metrics_mape)

    if ratio > threshold:
        logger.error(
            f"MAPE consistency check FAILED{f' for {variable_name}' if variable_name else ''}: "
            f"holdout={holdout_mape:.2f}%, metrics={metrics_mape:.2f}% (ratio={ratio:.1f}×). "
            f"This indicates actuals/predictions may be from different time periods."
        )
        return False

    logger.debug(
        f"MAPE consistency OK{f' for {variable_name}' if variable_name else ''}: "
        f"holdout={holdout_mape:.2f}%, metrics={metrics_mape:.2f}% (ratio={ratio:.1f}×)"
    )
    return True


# =============================================================================
# FQS (Forecast Quality Score) Functions
# =============================================================================


def calculate_fqs(
    mape: float | None,
    mase: float | None,
    w_mape: float = 0.35,
    w_mase: float = 0.65,
) -> float | None:
    """Calculate Forecast Quality Score (FQS) - composite metric 0-100 scale.

    FQS combines MAPE and MASE into a single actionable quality score.
    Based on Hyndman (2006): MASE should dominate for cross-series comparison.

    Formula:
        FQS = 100 × [w_mape × A_MAPE + w_mase × A_MASE]
        Where:
            A_MAPE = max(0, 1 - MAPE/100)  # Accuracy from MAPE (capped at 100%)
            A_MASE = max(0, 1 - MASE/2)    # Accuracy from MASE (naïve = 50%, perfect = 100%)

    Args:
        mape: MAPE value (percentage, e.g., 10.0 for 10%)
        mase: MASE value (scale-free, <1.0 is better than naïve)
        w_mape: Weight for MAPE component (default 0.35)
        w_mase: Weight for MASE component (default 0.65)

    Returns:
        FQS score 0-100, or None if both inputs are None

    Reference:
        Hyndman, R.J. (2006) "Another Look at Measures of Forecast Accuracy"
    """
    if mape is None and mase is None:
        return None

    # Calculate accuracy components
    a_mape = max(0.0, 1.0 - (mape / 100.0)) if mape is not None else 0.5  # Default 50%
    a_mase = max(0.0, 1.0 - (mase / 2.0)) if mase is not None else 0.5  # Default 50%

    # Adjust weights if only one metric is available
    if mape is None:
        w_mape, w_mase = 0.0, 1.0
    elif mase is None:
        w_mape, w_mase = 1.0, 0.0

    fqs = 100.0 * (w_mape * a_mape + w_mase * a_mase)
    return float(fqs)


def calculate_system_fqs(
    variable_results: list[dict],
    exclude_exempt: bool = True,
) -> dict:
    """Calculate system-wide FQS aggregations.

    Args:
        variable_results: List of dicts with 'fqs', 'data_quality_exempt', 'passed' keys
        exclude_exempt: Whether to exclude data_quality_exempt variables from controllable FQS

    Returns:
        Dict with:
            - average_fqs: Average FQS across all variables
            - controllable_fqs: FQS excluding exempt variables
            - min_fqs: Minimum FQS
            - max_fqs: Maximum FQS
            - exempt_variables: List of excluded variable names
    """
    all_fqs = []
    controllable_fqs_list = []
    exempt_vars = []

    for var in variable_results:
        fqs = var.get("fqs")
        if fqs is None:
            continue

        all_fqs.append(fqs)

        is_exempt = var.get("data_quality_exempt", False)
        if exclude_exempt and is_exempt:
            exempt_vars.append(var.get("name", "unknown"))
        else:
            controllable_fqs_list.append(fqs)

    return {
        "average_fqs": float(np.mean(all_fqs)) if all_fqs else None,
        "controllable_fqs": float(np.mean(controllable_fqs_list))
        if controllable_fqs_list
        else None,
        "min_fqs": float(np.min(all_fqs)) if all_fqs else None,
        "max_fqs": float(np.max(all_fqs)) if all_fqs else None,
        "exempt_variables": exempt_vars,
    }


def calculate_all_metrics(
    actuals: np.ndarray,
    predictions: np.ndarray,
    historical_data: np.ndarray | None = None,
    seasonality: int = 12,
) -> MultiMetricResult:
    """Calculate all validation metrics at once.

    This is the main entry point for multi-metric validation.
    Returns a MultiMetricResult with all metrics calculated.

    Args:
        actuals: Array of actual values (test set)
        predictions: Array of predicted values
        historical_data: Array of historical values for MASE calculation
                        (if None, uses actuals)
        seasonality: Seasonal period for MASE (default 12 for monthly)

    Returns:
        MultiMetricResult with all metrics
    """
    # Convert to numpy arrays if needed
    actuals = np.asarray(actuals, dtype=float)
    predictions = np.asarray(predictions, dtype=float)

    if historical_data is None:
        historical_data = actuals
    else:
        historical_data = np.asarray(historical_data, dtype=float)

    return MultiMetricResult(
        mape=calculate_mape_from_arrays(actuals, predictions),
        mase=calculate_mase(actuals, predictions, historical_data, seasonality),
        smape=calculate_smape(actuals, predictions),
        rmse=calculate_rmse(actuals, predictions),
        mae=calculate_mae(actuals, predictions),
        bias=calculate_bias(actuals, predictions),
    )


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
