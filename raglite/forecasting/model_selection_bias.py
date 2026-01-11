"""Bias correction utilities for forecast post-processing.

Epic 7 Enhancement: Reduces systematic over/under-prediction through bias detection
and correction.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_bias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate forecast bias (mean error).

    Positive bias = model tends to over-predict
    Negative bias = model tends to under-predict

    Args:
        y_true: Array of true values
        y_pred: Array of predicted values

    Returns:
        Mean error (bias) in original units
    """
    return float(np.mean(y_pred - y_true))


def apply_bias_correction(
    predictions: np.ndarray,
    historical_bias: float,
    correction_factor: float = 1.0,
) -> np.ndarray:
    """Apply bias correction to predictions.

    Epic 7 Enhancement: Reduces systematic over/under-prediction by subtracting
    historical bias from predictions.

    Args:
        predictions: Array of predictions to correct
        historical_bias: Measured bias from validation (positive = over-predicting)
        correction_factor: Fraction of bias to correct (0.0-1.0, default 1.0)
            Use <1.0 for partial correction to avoid over-correction

    Returns:
        Bias-corrected predictions
    """
    correction = historical_bias * correction_factor
    return predictions - correction


def estimate_rolling_bias(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    window: int = 6,
) -> np.ndarray:
    """Estimate rolling bias over a sliding window.

    Useful for detecting if bias is changing over time (e.g., regime changes).

    Args:
        y_true: Array of true values
        y_pred: Array of predicted values
        window: Rolling window size

    Returns:
        Array of rolling bias values
    """
    errors = y_pred - y_true
    rolling_bias = pd.Series(errors).rolling(window=window, min_periods=1).mean()
    return np.asarray(rolling_bias)


def detect_bias_regime_change(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    threshold: float = 2.0,
) -> tuple[bool, float, float]:
    """Detect if there's a significant bias regime change.

    Compares bias in first half vs second half of the series.

    Args:
        y_true: Array of true values
        y_pred: Array of predicted values
        threshold: Ratio threshold for detecting change (default 2.0 = 2x difference)

    Returns:
        Tuple of (regime_change_detected, first_half_bias, second_half_bias)
    """
    mid_point = len(y_true) // 2

    first_half_bias = calculate_bias(y_true[:mid_point], y_pred[:mid_point])
    second_half_bias = calculate_bias(y_true[mid_point:], y_pred[mid_point:])

    # Avoid division by zero
    if abs(first_half_bias) < 1e-10:
        regime_change = abs(second_half_bias) > threshold
    else:
        ratio = abs(second_half_bias / first_half_bias)
        regime_change = ratio > threshold or ratio < 1 / threshold

    return regime_change, first_half_bias, second_half_bias
