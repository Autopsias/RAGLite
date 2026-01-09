"""Hybrid forecasting - Machine learning model fitting and forecasting.

Part of Story 8.1 refactoring to split hybrid.py.

Provides:
- fit_linear_regression: Linear regression with cross-validation
- fit_ridge_regression: Ridge (L2) regression with regularization
- fit_lasso_regression: Lasso (L1) regression for feature selection
- fit_catboost: CatBoost with hyperparameter tuning
- Helper functions for parallel model execution
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from catboost import CatBoostRegressor

from raglite.forecasting.hybrid.ml_models_utils import (
    _fit_and_forecast_catboost,
    _fit_and_forecast_linear,
    _run_linear_forecast,
    calculate_catboost_mape,
    create_catboost_grid_search,
    fit_lasso_regression,
    fit_linear_regression,
    fit_ridge_regression,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Story 6.12: CatBoost default hyperparameter grid
# CatBoost parameters tuned for time-series forecasting with categorical support
CATBOOST_PARAM_GRID = {
    "iterations": [300, 500, 800],
    "learning_rate": [0.01, 0.03, 0.1],
    "depth": [4, 6, 8],
    "l2_leaf_reg": [1, 3, 5],
}

# Fast mode for testing (reduced grid)
CATBOOST_PARAM_GRID_FAST = {
    "iterations": [500],
    "learning_rate": [0.03],
    "depth": [6],
    "l2_leaf_reg": [3],
}


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
    grid_search, tscv = create_catboost_grid_search(X, fast_mode)
    grid_search.fit(X, y)

    best_model = grid_search.best_estimator_
    best_rmse = -grid_search.cv_results_["mean_test_rmse"][grid_search.best_index_]
    best_mae = -grid_search.cv_results_["mean_test_mae"][grid_search.best_index_]

    mape = calculate_catboost_mape(best_model, X, y, tscv)

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


# Export functions from utils
__all__ = [
    "fit_linear_regression",
    "fit_ridge_regression",
    "fit_lasso_regression",
    "fit_catboost",
    "_fit_and_forecast_catboost",
    "_fit_and_forecast_linear",
    "_run_linear_forecast",
    "CATBOOST_PARAM_GRID",
    "CATBOOST_PARAM_GRID_FAST",
]
