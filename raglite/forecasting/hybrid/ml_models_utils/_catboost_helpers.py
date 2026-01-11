"""CatBoost-specific helper functions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    pass

from raglite.forecasting.hybrid.lazy_imports import (
    _get_catboost_class,
    _get_grid_search_cv,
    _get_time_series_split,
)


def create_catboost_grid_search(X: pd.DataFrame, fast_mode: bool = False) -> tuple[Any, Any]:
    """Create GridSearchCV instance for CatBoost.

    Story 6.12 AC1: Grid search setup with time-series split.

    Args:
        X: Feature DataFrame (regressors)
        fast_mode: Use reduced param grid for testing

    Returns:
        Tuple of (GridSearchCV instance, TimeSeriesSplit instance)
    """
    CatBoostRegressor = _get_catboost_class()
    GridSearchCV = _get_grid_search_cv()
    TimeSeriesSplit = _get_time_series_split()

    # CatBoost parameter grids
    CATBOOST_PARAM_GRID = {
        "iterations": [300, 500, 800],
        "learning_rate": [0.01, 0.03, 0.1],
        "depth": [4, 6, 8],
        "l2_leaf_reg": [1, 3, 5],
    }
    CATBOOST_PARAM_GRID_FAST = {
        "iterations": [500],
        "learning_rate": [0.03],
        "depth": [6],
        "l2_leaf_reg": [3],
    }

    param_grid = CATBOOST_PARAM_GRID_FAST if fast_mode else CATBOOST_PARAM_GRID
    n_splits = min(5, len(X) - 1)
    tscv = TimeSeriesSplit(n_splits=n_splits)

    scoring = {
        "rmse": "neg_root_mean_squared_error",
        "mae": "neg_mean_absolute_error",
    }

    grid_search = GridSearchCV(
        CatBoostRegressor(
            random_state=42,
            verbose=False,
            loss_function="RMSE",
            allow_writing_files=False,
        ),
        param_grid,
        cv=tscv,
        scoring=scoring,
        refit="rmse",
        n_jobs=-1,
    )

    return grid_search, tscv


def calculate_catboost_mape(model: Any, X: pd.DataFrame, y: pd.Series, tscv: Any) -> float:
    """Calculate MAPE using time-series cross-validation.

    Story 6.12 AC1: MAPE calculation for CatBoost metrics.

    Args:
        model: Fitted CatBoost model
        X: Feature DataFrame
        y: Target series
        tscv: TimeSeriesSplit instance

    Returns:
        MAPE score (float)
    """
    mape_scores = []

    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model.fit(X_train, y_train)
        fold_predictions = model.predict(X_val)

        y_vals = y_val.values
        non_zero_mask = y_vals != 0
        if non_zero_mask.any():
            fold_mape = float(
                np.mean(
                    np.abs(
                        (y_vals[non_zero_mask] - fold_predictions[non_zero_mask])
                        / y_vals[non_zero_mask]
                    )
                )
                * 100
            )
            mape_scores.append(fold_mape)

    return float(np.mean(mape_scores)) if mape_scores else 0.0


def fit_and_forecast_catboost(
    X: pd.DataFrame,
    y: pd.Series,
    X_future: pd.DataFrame,
    periods_ahead: int,
    fast_mode: bool = False,
) -> dict[str, Any]:
    """Fit CatBoost and generate forecast (for ThreadPoolExecutor).

    Story 6.12 AC1: Combined fit+forecast for parallel execution.

    Args:
        X: Training feature DataFrame
        y: Target series
        X_future: Future feature values for prediction
        periods_ahead: Number of periods to forecast
        fast_mode: Use reduced hyperparameter grid

    Returns:
        Dict with 'values' list and 'metrics' dict
    """
    # This is a helper function - the actual fit_catboost is in the main module
    from ..ml_models import fit_catboost

    model, metrics = fit_catboost(X, y, fast_mode=fast_mode)
    predictions = model.predict(X_future)
    return {
        "values": predictions.tolist()[:periods_ahead],
        "metrics": metrics,
    }
