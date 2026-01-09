"""Cross-validation metrics calculation utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from numpy.typing import NDArray


def calculate_cv_metrics(
    y_val: pd.Series,
    predictions: NDArray[Any],
    cv_rmse_scores: list[float],
    cv_mae_scores: list[float],
    cv_mape_scores: list[float],
) -> dict[str, float]:
    """Calculate cross-validation metrics."""
    # RMSE: Root Mean Squared Error
    rmse = float(np.sqrt(np.mean((y_val.values - predictions) ** 2)))

    # MAE: Mean Absolute Error
    mae = float(np.mean(np.abs(y_val.values - predictions)))

    # MAPE: Mean Absolute Percentage Error (avoid division by zero)
    y_vals = y_val.values
    non_zero_mask = y_vals != 0
    if non_zero_mask.any():
        mape = float(
            np.mean(
                np.abs((y_vals[non_zero_mask] - predictions[non_zero_mask]) / y_vals[non_zero_mask])
            )
            * 100
        )
    else:
        mape = 0.0

    return {
        "rmse": rmse,
        "mae": mae,
        "mape": mape,
    }


def calculate_fold_metrics(
    y_val: pd.Series, predictions: NDArray[Any]
) -> tuple[float, float, float]:
    """Calculate metrics for a single fold."""
    # RMSE
    rmse = float(np.sqrt(np.mean((y_val.values - predictions) ** 2)))

    # MAE
    mae = float(np.mean(np.abs(y_val.values - predictions)))

    # MAPE: Mean Absolute Percentage Error (avoid division by zero)
    y_vals = y_val.values
    non_zero_mask = y_vals != 0
    if non_zero_mask.any():
        mape = float(
            np.mean(
                np.abs((y_vals[non_zero_mask] - predictions[non_zero_mask]) / y_vals[non_zero_mask])
            )
            * 100
        )
    else:
        mape = 0.0

    return rmse, mae, mape


def append_fold_metrics(
    cv_rmse_scores: list[float],
    cv_mae_scores: list[float],
    cv_mape_scores: list[float],
    rmse: float,
    mae: float,
    mape: float,
) -> None:
    """Append fold metrics to CV scores."""
    cv_rmse_scores.append(rmse)
    cv_mae_scores.append(mae)
    cv_mape_scores.append(mape)
