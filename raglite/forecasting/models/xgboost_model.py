"""XGBoost model implementation for time-series forecasting.

Story 6.4 AC4: XGBoost with GridSearchCV (5-fold time-series split).
Story 7.5: Extracted from hybrid.py for better modularity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from xgboost import XGBRegressor

from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Lazy loading flag to avoid import overhead
_xgboost_loaded = False


def _get_xgboost_regressor() -> Any:
    """Lazy-load XGBRegressor from xgboost."""
    global _xgboost_loaded
    if not _xgboost_loaded:
        from xgboost import XGBRegressor

        _xgboost_loaded = True
        return XGBRegressor
    from xgboost import XGBRegressor

    return XGBRegressor


def _get_grid_search_cv() -> Any:
    """Lazy-load GridSearchCV from sklearn."""
    from sklearn.model_selection import GridSearchCV

    return GridSearchCV


def _get_time_series_split() -> Any:
    """Lazy-load TimeSeriesSplit from sklearn."""
    from sklearn.model_selection import TimeSeriesSplit

    return TimeSeriesSplit


# Story 6.4 AC4: Default XGBoost hyperparameter grid
XGBOOST_PARAM_GRID = {
    "n_estimators": [50, 100, 200],
    "max_depth": [3, 6, 9],
    "learning_rate": [0.01, 0.1, 0.2],
    "subsample": [0.7, 0.8, 0.9],
}

# Fast mode for testing (reduced grid)
XGBOOST_PARAM_GRID_FAST = {
    "n_estimators": [100],
    "max_depth": [6],
    "learning_rate": [0.1],
    "subsample": [0.8],
}


def fit_xgboost(
    X: pd.DataFrame,
    y: pd.Series,
    fast_mode: bool = False,
) -> tuple[XGBRegressor, dict[str, object]]:
    """Fit XGBoost regressor with hyperparameter tuning.

    Story 6.4 AC4: XGBoost with GridSearchCV (5-fold time-series split).

    Args:
        X: Feature DataFrame (regressors)
        y: Target series (metric values)
        fast_mode: Use reduced param grid for testing (default: False)

    Returns:
        Tuple of (best fitted XGBRegressor model, accuracy metrics dict with rmse/mae/mape/best_params)
    """
    XGBRegressor = _get_xgboost_regressor()
    GridSearchCV = _get_grid_search_cv()
    TimeSeriesSplit = _get_time_series_split()

    param_grid = XGBOOST_PARAM_GRID_FAST if fast_mode else XGBOOST_PARAM_GRID

    # Use fewer splits for small datasets
    n_splits = min(5, len(X) - 1)
    tscv = TimeSeriesSplit(n_splits=n_splits)

    # Use multiple scoring to get RMSE, MAE, and MAPE
    scoring = {
        "rmse": "neg_root_mean_squared_error",
        "mae": "neg_mean_absolute_error",
    }

    grid_search = GridSearchCV(
        XGBRegressor(random_state=42, verbosity=0),
        param_grid,
        cv=tscv,
        scoring=scoring,
        refit="rmse",  # Refit using best RMSE model
        n_jobs=-1,  # Parallel execution
    )

    grid_search.fit(X, y)

    best_model = grid_search.best_estimator_
    best_rmse = -grid_search.cv_results_["mean_test_rmse"][grid_search.best_index_]
    best_mae = -grid_search.cv_results_["mean_test_mae"][grid_search.best_index_]

    # Calculate MAPE manually using time-series cross-validation
    # (cross_val_predict doesn't work with TimeSeriesSplit as it's not a partition)
    mape_scores: list[float] = []
    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        # Refit best model on training fold
        best_model.fit(X_train, y_train)
        fold_predictions = best_model.predict(X_val)

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

    # Final refit on all data (GridSearchCV already did this, but ensure consistency)
    best_model.fit(X, y)
    mape = float(np.mean(mape_scores)) if mape_scores else 0.0

    metrics: dict[str, object] = {
        "rmse": float(best_rmse),
        "mae": float(best_mae),
        "mape": mape,
        "best_params": grid_search.best_params_,
    }

    logger.info(
        "XGBoost fitted",
        extra={
            "best_params": grid_search.best_params_,
            "cv_rmse": best_rmse,
            "cv_mae": best_mae,
            "fast_mode": fast_mode,
        },
    )

    return best_model, metrics


def _fit_and_forecast_xgboost(
    X: pd.DataFrame,
    y: pd.Series,
    X_future: pd.DataFrame,
    periods_ahead: int,
    fast_mode: bool = False,
) -> dict[str, Any]:
    """Fit XGBoost and generate forecast (for ThreadPoolExecutor).

    Story 6.4 AC5: Combined fit+forecast for parallel execution.

    Args:
        X: Training feature DataFrame
        y: Target series
        X_future: Future feature values for prediction
        periods_ahead: Number of periods to forecast
        fast_mode: Use reduced hyperparameter grid

    Returns:
        Dict with 'values' list and 'metrics' dict
    """
    model, metrics = fit_xgboost(X, y, fast_mode=fast_mode)
    predictions = model.predict(X_future)
    return {
        "values": predictions.tolist()[:periods_ahead],
        "metrics": metrics,
    }


def _run_xgboost_forecast(
    model: XGBRegressor,
    X_future: pd.DataFrame,
    periods_ahead: int,
) -> dict[str, object]:
    """Run XGBoost forecast prediction.

    This is a synchronous function designed to be called via ThreadPoolExecutor
    for parallel ensemble execution alongside async Prophet.

    Args:
        model: Fitted XGBRegressor model from xgboost
        X_future: Future feature values (regressors extrapolated forward)
        periods_ahead: Number of periods to forecast

    Returns:
        Dict with 'values' list of predictions and 'metrics' dict
    """
    try:
        predictions = model.predict(X_future)
        return {
            "values": predictions.tolist()[:periods_ahead],
            "metrics": {"model": "xgboost"},
        }
    except Exception as e:
        logger.warning(f"XGBoost forecast failed: {e}")
        raise
