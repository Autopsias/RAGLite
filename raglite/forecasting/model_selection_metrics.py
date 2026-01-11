"""Forecast accuracy metrics for model evaluation."""

from __future__ import annotations

import numpy as np


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Mean Absolute Percentage Error.

    Args:
        y_true: Array of true values
        y_pred: Array of predicted values

    Returns:
        MAPE as a percentage (0-100+)

    Raises:
        ValueError: If arrays have different lengths
    """
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"Length mismatch: y_true has {len(y_true)} values, y_pred has {len(y_pred)} values"
        )

    mask = y_true != 0
    if not mask.any():
        return float("inf")
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    return float(mape)


def calculate_mase(y_train: np.ndarray, y_test: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Mean Absolute Scaled Error."""
    mae_pred = np.mean(np.abs(y_test - y_pred))
    naive_forecast = y_train[:-1]
    naive_actual = y_train[1:]
    mae_naive = np.mean(np.abs(naive_actual - naive_forecast))

    if mae_naive == 0:
        return float("inf") if mae_pred > 0 else 0.0

    return float(mae_pred / mae_naive)
