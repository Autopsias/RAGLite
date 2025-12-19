"""CatBoost model implementation for time-series forecasting.

Story 6.12 AC1: CatBoost with GridSearchCV (5-fold time-series split).
Story 7.5: Extracted from hybrid.py for better modularity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from catboost import CatBoostRegressor

from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Lazy loading for CatBoost class
_catboost_class: type[CatBoostRegressor] | None = None


def _get_catboost_class() -> type[CatBoostRegressor]:
    """Lazy-load CatBoostRegressor class on first use.

    Story 6.12 AC1: Lazy-load CatBoost to avoid import penalties.
    Story 6.12 Issue #7 fix: Graceful handling if CatBoost not installed.
    Story 6.12 CI fix: Add __sklearn_tags__ compatibility for scikit-learn 1.7+ and 1.8+.

    sklearn 1.8+ requires proper Tags object with regressor-specific fields.
    Fallback to sklearn 1.7.x approach if Tags import fails.

    Returns:
        CatBoostRegressor class from catboost library

    Raises:
        ImportError: If catboost is not installed with helpful message
    """
    global _catboost_class
    if _catboost_class is None:
        try:
            from catboost import CatBoostRegressor

            # Fix sklearn 1.7+ and 1.8+ compatibility: CatBoostRegressor lacks __sklearn_tags__
            # sklearn 1.8+ requires proper Tags object with regressor-specific fields
            # The most robust solution is to create a wrapper class that inherits from
            # sklearn's BaseEstimator to get proper __sklearn_tags__ method resolution
            if not hasattr(CatBoostRegressor, "__sklearn_tags__"):
                from sklearn.base import BaseEstimator

                # Create a wrapper class that adds sklearn compatibility
                # BaseEstimator must be AFTER CatBoostRegressor in MRO to avoid conflicts
                class SklearnCompatibleCatBoost(CatBoostRegressor, BaseEstimator):
                    """CatBoost wrapper with sklearn __sklearn_tags__ compatibility.

                    sklearn 1.7+ and 1.8+ require __sklearn_tags__ method.
                    By inheriting from BaseEstimator, we get proper method resolution.
                    """

                    pass

                # Keep the original class name for compatibility with tests and logging
                SklearnCompatibleCatBoost.__name__ = "CatBoostRegressor"
                SklearnCompatibleCatBoost.__qualname__ = "CatBoostRegressor"
                _catboost_class = SklearnCompatibleCatBoost
            else:
                _catboost_class = CatBoostRegressor
        except ImportError as e:
            logger.error(
                "CatBoost not installed. Install with: pip install catboost>=1.2",
                extra={"error": str(e)},
            )
            raise ImportError(
                "CatBoost is required for Story 6.12 ensemble forecasting. "
                "Install with: pip install catboost>=1.2"
            ) from e
    return cast("type[CatBoostRegressor]", _catboost_class)


def _get_grid_search_cv() -> Any:
    """Lazy-load GridSearchCV from sklearn."""
    from sklearn.model_selection import GridSearchCV

    return GridSearchCV


def _get_time_series_split() -> Any:
    """Lazy-load TimeSeriesSplit from sklearn."""
    from sklearn.model_selection import TimeSeriesSplit

    return TimeSeriesSplit


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
    CatBoostRegressor = _get_catboost_class()
    GridSearchCV = _get_grid_search_cv()
    TimeSeriesSplit = _get_time_series_split()

    param_grid = CATBOOST_PARAM_GRID_FAST if fast_mode else CATBOOST_PARAM_GRID

    # Use fewer splits for small datasets
    n_splits = min(5, len(X) - 1)
    tscv = TimeSeriesSplit(n_splits=n_splits)

    # Use multiple scoring to get RMSE, MAE
    scoring = {
        "rmse": "neg_root_mean_squared_error",
        "mae": "neg_mean_absolute_error",
    }

    # CatBoost-specific parameters: silent mode and random state
    grid_search = GridSearchCV(
        CatBoostRegressor(
            random_state=42,
            verbose=False,
            loss_function="RMSE",
            allow_writing_files=False,  # Don't create temp files
        ),
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

    # Final refit on all data
    best_model.fit(X, y)
    mape = float(np.mean(mape_scores)) if mape_scores else 0.0

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
