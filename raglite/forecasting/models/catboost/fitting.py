"""CatBoost model fitting and forecasting functions.

Story 6.12 AC1: CatBoost with GridSearchCV (5-fold time-series split).
Story 7.5: Extracted from hybrid.py for better modularity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from catboost import CatBoostRegressor

from raglite.forecasting.models.catboost.config import (
    CATBOOST_PARAM_GRID,
    CATBOOST_PARAM_GRID_FAST,
)
from raglite.forecasting.models.catboost.lazy_loading import (
    _get_catboost_class,
    _get_grid_search_cv,
    _get_time_series_split,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def _calculate_cross_validation_mape(
    model: CatBoostRegressor, X: pd.DataFrame, y: pd.Series, tscv: Any
) -> float:
    """Calculate MAPE using time-series cross-validation.

    Args:
        model: Fitted CatBoost model
        X: Feature DataFrame
        y: Target series
        tscv: TimeSeriesSplit object

    Returns:
        Mean Absolute Percentage Error (MAPE) across all folds
    """
    mape_scores: list[float] = []

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


def fit_catboost(
    X: pd.DataFrame,
    y: pd.Series,
    fast_mode: bool = False,
) -> tuple[CatBoostRegressor, dict[str, object]]:
    """Fit CatBoost regressor with hyperparameter tuning.

    Story 6.12 AC1: CatBoost with GridSearchCV (5-fold time-series split).

    CatBoost advantages:
    - Native categorical feature support (no encoding needed)
    - Handles missing values automatically
    - Ordered boosting reduces overfitting on small datasets
    - Symmetric trees for fast inference

    Args:
        X: Feature DataFrame (regressors)
        y: Target series (metric values)
        fast_mode: Use reduced param grid for testing (default: False)

    Returns:
        Tuple of (best fitted CatBoostRegressor model, accuracy metrics dict with rmse/mae/mape/best_params)
    """
    CatBoostRegressor = _get_catboost_class()
    GridSearchCV = _get_grid_search_cv()
    TimeSeriesSplit = _get_time_series_split()

    param_grid = CATBOOST_PARAM_GRID_FAST if fast_mode else CATBOOST_PARAM_GRID
    n_splits = min(5, len(X) - 1)
    tscv = TimeSeriesSplit(n_splits=n_splits)

    scoring = {"rmse": "neg_root_mean_squared_error", "mae": "neg_mean_absolute_error"}

    grid_search = GridSearchCV(
        CatBoostRegressor(
            random_state=42, verbose=False, loss_function="RMSE", allow_writing_files=False
        ),
        param_grid,
        cv=tscv,
        scoring=scoring,
        refit="rmse",
        n_jobs=-1,
    )

    grid_search.fit(X, y)
    best_model = grid_search.best_estimator_

    best_rmse = -grid_search.cv_results_["mean_test_rmse"][grid_search.best_index_]
    best_mae = -grid_search.cv_results_["mean_test_mae"][grid_search.best_index_]
    mape = _calculate_cross_validation_mape(best_model, X, y, tscv)

    best_model.fit(X, y)

    metrics: dict[str, object] = {
        "rmse": float(best_rmse),
        "mae": float(best_mae),
        "mape": mape,
        "best_params": grid_search.best_params_,
    }

    logger.info(
        "CatBoost fitted",
        extra={
            "best_params": grid_search.best_params_,
            "cv_rmse": best_rmse,
            "cv_mae": best_mae,
            "fast_mode": fast_mode,
        },
    )

    return best_model, metrics


def _fit_and_forecast_catboost(
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
    model, metrics = fit_catboost(X, y, fast_mode=fast_mode)
    predictions = model.predict(X_future)
    return {
        "values": predictions.tolist()[:periods_ahead],
        "metrics": metrics,
    }
