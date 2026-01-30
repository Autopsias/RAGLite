"""Core forecasting validation metrics calculation functions.

Story 6.21: Unified Validation Script
Story 6.26: Multi-Metric Validation Enhancement
EBITDA bug fix (2026-01-29): Added minimum data point validation for reliable metrics.

Contains validation metrics:
- MAPE: Mean Absolute Percentage Error (percentage deviation)
- MASE: Mean Absolute Scaled Error (scale-free, naïve benchmark)
- SMAPE: Symmetric MAPE (bounded 0-200%, handles zeros better)
- RMSE: Root Mean Square Error (penalizes large errors)
- MAE: Mean Absolute Error (simple absolute error)
- Bias: Mean Error (systematic over/under-prediction)
"""

from __future__ import annotations

import numpy as np

from raglite.forecasting.validation_types import MultiMetricResult
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# EBITDA bug fix: Minimum data points required for meaningful MAPE calculation
MIN_POINTS_FOR_RELIABLE_MAPE = 5


# =============================================================================
# Core Metric Calculation Functions
# =============================================================================


def calculate_mape_from_arrays(
    actuals: np.ndarray,
    predictions: np.ndarray,
    min_points: int = MIN_POINTS_FOR_RELIABLE_MAPE,
) -> float | None:
    """Calculate MAPE from numpy arrays.

    MAPE = mean(|actual - predicted| / |actual|) * 100

    EBITDA bug fix (2026-01-29): Added minimum data point validation and
    warning for high MAPE values indicating unreliable forecasts.

    Args:
        actuals: Array of actual values
        predictions: Array of predicted values
        min_points: Minimum points required for reliable MAPE (default: 5)

    Returns:
        MAPE as percentage, or None if insufficient data points
    """
    if len(actuals) == 0 or len(predictions) == 0:
        return None

    # Filter out zero actuals to avoid division by zero
    non_zero_mask = actuals != 0
    if not np.any(non_zero_mask):
        return None

    filtered_actuals = actuals[non_zero_mask]
    filtered_predictions = predictions[non_zero_mask]

    # EBITDA bug fix: Validate minimum data points for reliable metric
    if len(filtered_actuals) < min_points:
        logger.warning(
            "Insufficient data points for reliable MAPE calculation",
            extra={
                "n_points": len(filtered_actuals),
                "min_required": min_points,
                "original_points": len(actuals),
                "zeros_filtered": len(actuals) - len(filtered_actuals),
            },
        )
        return None

    mape = np.mean(np.abs((filtered_actuals - filtered_predictions) / filtered_actuals)) * 100

    # EBITDA bug fix: Warn when MAPE > 100% (forecast is essentially random)
    if mape > 100:
        logger.warning(
            "MAPE exceeds 100%% - forecast may be unreliable",
            extra={
                "mape": round(mape, 2),
                "n_points": len(filtered_actuals),
                "interpretation": "Average error exceeds actual values - consider data quality",
            },
        )

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

    Phase 4 Quality Fix (2026-01-29): Added sparse data warning.
    Research (Perplexity): MASE unreliable with <20-30 points; use with caution
    for very sparse data like EBITDA (6-8 points).

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

    # Phase 4: Warn for very sparse data where MASE may be unreliable
    if len(historical_data) < 8:
        logger.warning(
            "Sparse historical data for MASE calculation - metric may be unreliable",
            extra={
                "n_historical_points": len(historical_data),
                "min_recommended": 20,
                "interpretation": "MASE < 1.0 is still meaningful but confidence is lower",
            },
        )

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
    min_points: int = MIN_POINTS_FOR_RELIABLE_MAPE,
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
        min_points: Minimum points required for reliable MAPE (default: 5)
                   Use min_points=1 for edge case testing

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
        mape=calculate_mape_from_arrays(actuals, predictions, min_points=min_points),
        mase=calculate_mase(actuals, predictions, historical_data, seasonality),
        smape=calculate_smape(actuals, predictions),
        rmse=calculate_rmse(actuals, predictions),
        mae=calculate_mae(actuals, predictions),
        bias=calculate_bias(actuals, predictions),
    )
