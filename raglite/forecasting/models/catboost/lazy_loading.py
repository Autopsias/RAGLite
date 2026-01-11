"""Lazy-loading utilities for CatBoost and sklearn dependencies.

Story 6.12 AC1: Lazy-load CatBoost to avoid import penalties.
Story 6.12 Issue #7 fix: Graceful handling if CatBoost not installed.
Story 6.12 CI fix: Add __sklearn_tags__ compatibility for scikit-learn 1.7+ and 1.8+.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

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
