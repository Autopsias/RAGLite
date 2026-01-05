"""Cross-validation utilities for model selection.

Private implementation details extracted to reduce main file size.
"""

import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from raglite.forecasting.model_selection_utils import (
    calculate_mape,
    calculate_mase,
    fit_chronos,
    fit_ml_model,
    fit_prophet,
    fit_tft,
)

logger = logging.getLogger(__name__)


async def _cv_evaluate(
    model_name: str,
    y: pd.Series,
    regressors: dict[str, pd.Series] | None,
    tscv: TimeSeriesSplit,
    use_recency_weights: bool = False,
) -> dict[str, float]:
    """Cross-validate a single model and return average metrics.

    Performs time-series cross-validation using the provided TimeSeriesSplit object,
    calculating MAPE and MASE for each fold and returning the (weighted) average.

    Epic 7 Enhancement: Supports recency-weighted averaging for volatile series.
    Recent folds get higher weights since recent patterns are more predictive
    for volatile time series.

    Args:
        model_name: Name of the model to evaluate (e.g., 'arima', 'prophet')
        y: Time series data with DatetimeIndex
        regressors: Optional dictionary mapping regressor names to aligned Series
        tscv: TimeSeriesSplit object for cross-validation fold generation
        use_recency_weights: If True, weight recent folds higher (for volatile series)

    Returns:
        Dictionary with average 'mape' and 'mase' scores across all folds

    Raises:
        Exception: Propagated from model fitting or prediction failures
    """
    mape_scores = []
    mase_scores = []

    for train_idx, test_idx in tscv.split(y):
        y_train = y.iloc[train_idx]
        y_test = y.iloc[test_idx]

        X_train = None
        X_test = None
        if regressors:
            X_train = pd.DataFrame({k: v.iloc[train_idx] for k, v in regressors.items()})
            X_test = pd.DataFrame({k: v.iloc[test_idx] for k, v in regressors.items()})

        # Fit and predict
        predictions = await _fit_and_predict(model_name, y_train, X_train, len(y_test), X_test)

        # Calculate metrics
        mape = calculate_mape(y_test.values, predictions)
        mase = calculate_mase(y_train.values, y_test.values, predictions)

        mape_scores.append(mape)
        mase_scores.append(mase)

    # Epic 7: Apply recency weights for volatile series
    # Weight scheme: older folds = 1.0, second-to-last = 1.5, last fold = 2.0
    if use_recency_weights and len(mape_scores) >= 3:
        n_folds = len(mape_scores)
        weights = [1.0] * (n_folds - 2) + [1.5, 2.0]
        logger.debug(
            "Using recency-weighted CV averaging",
            extra={"n_folds": n_folds, "weights": weights},
        )
        return {
            "mape": float(np.average(mape_scores, weights=weights)),
            "mase": float(np.average(mase_scores, weights=weights)),
        }

    return {
        "mape": float(np.mean(mape_scores)),
        "mase": float(np.mean(mase_scores)),
    }


async def _fit_and_predict(
    model_name: str,
    y_train: pd.Series,
    X_train: pd.DataFrame | None,
    horizon: int,
    X_future: pd.DataFrame | None,
) -> np.ndarray:
    """Fit model and generate predictions.

    Args:
        model_name: Name of the model to fit
        y_train: Training time series
        X_train: Training regressors (optional)
        horizon: Forecast horizon
        X_future: Future regressors (optional)

    Returns:
        Array of predictions
    """
    if model_name == "arima":
        from raglite.forecasting.models.arima_model import fit_arima

        _, _, predictions, _ = await fit_arima(
            y_train, X_train=X_train, X_future=X_future, forecast_horizon=horizon
        )
        return predictions

    elif model_name == "ets":
        from raglite.forecasting.models.ets_model import fit_ets

        _, _, predictions, _ = await fit_ets(y_train, forecast_horizon=horizon)
        return predictions

    elif model_name == "prophet":
        return await fit_prophet(y_train, X_train, horizon, X_future)

    elif model_name in ("xgboost", "lightgbm", "catboost", "linear"):
        return await fit_ml_model(model_name, y_train, X_train, horizon, X_future)

    elif model_name == "chronos":
        return await fit_chronos(y_train, horizon)

    elif model_name == "tft":
        # TFT uses pre-trained checkpoint for inference
        tft_regressors: dict[str, pd.Series] | None = None
        if X_train is not None and not X_train.empty:
            tft_regressors = {col: X_train[col] for col in X_train.columns}
        return await fit_tft(y_train, horizon, external_regressors=tft_regressors)

    else:
        raise ValueError(f"Unknown model: {model_name}")
