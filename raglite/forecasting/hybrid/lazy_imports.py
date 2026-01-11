"""Hybrid forecasting - Lazy loading helpers for optional dependencies.

Part of Story 8.1 refactoring to split hybrid.py.

This module provides:
- Lazy loading functions for heavy ML dependencies (Prophet, sklearn, XGBoost, CatBoost)
- Shared ThreadPoolExecutor for non-async model operations
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from catboost import CatBoostRegressor
    from prophet import Prophet

from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Story 6.4: Module-level executor for sklearn/xgboost (not async-native)
# Limited to 2 workers to manage memory when running models in parallel
# Story 8.1: Consolidated to single shared instance across all hybrid modules
_sklearn_executor = ThreadPoolExecutor(max_workers=2)

# Lazy-load Prophet to avoid import-time penalty during test collection
# Prophet takes 3-5s to import due to Stan backend dependencies
_prophet_class = None
_catboost_class = None

# Cached sklearn classes
_linear_regression_class = None
_ridge_class = None
_lasso_class = None
_time_series_split_class = None
_grid_search_cv_class = None
_xgboost_class = None


def _get_prophet_class() -> type[Prophet]:
    """Lazy-load Prophet class on first use.

    Returns:
        Prophet class from prophet library
    """
    global _prophet_class
    if _prophet_class is None:
        from prophet import Prophet

        _prophet_class = Prophet
    return cast("type[Prophet]", _prophet_class)


def _get_linear_regression() -> Any:
    """Lazy-load LinearRegression from sklearn."""
    global _linear_regression_class
    if _linear_regression_class is None:
        from sklearn.linear_model import LinearRegression

        _linear_regression_class = LinearRegression
    return _linear_regression_class


def _get_ridge_regression() -> Any:
    """Lazy-load Ridge regression from sklearn.

    Story 6.8 AC5: Ridge regression for regularized linear models.
    """
    global _ridge_class
    if _ridge_class is None:
        from sklearn.linear_model import Ridge

        _ridge_class = Ridge
    return _ridge_class


def _get_lasso_regression() -> Any:
    """Lazy-load Lasso regression from sklearn.

    Story 6.8 AC5: Lasso regression for L1 regularization (feature selection).
    """
    global _lasso_class
    if _lasso_class is None:
        from sklearn.linear_model import Lasso

        _lasso_class = Lasso
    return _lasso_class


def _get_time_series_split() -> Any:
    """Lazy-load TimeSeriesSplit from sklearn."""
    global _time_series_split_class
    if _time_series_split_class is None:
        from sklearn.model_selection import TimeSeriesSplit

        _time_series_split_class = TimeSeriesSplit
    return _time_series_split_class


def _get_xgboost_regressor() -> Any:
    """Lazy-load XGBRegressor from xgboost."""
    global _xgboost_class
    if _xgboost_class is None:
        from xgboost import XGBRegressor

        _xgboost_class = XGBRegressor
    return _xgboost_class


def _get_grid_search_cv() -> Any:
    """Lazy-load GridSearchCV from sklearn."""
    global _grid_search_cv_class
    if _grid_search_cv_class is None:
        from sklearn.model_selection import GridSearchCV

        _grid_search_cv_class = GridSearchCV
    return _grid_search_cv_class


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
