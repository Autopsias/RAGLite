"""CatBoost model implementation for time-series forecasting.

Story 6.12 AC1: CatBoost with GridSearchCV (5-fold time-series split).
Story 7.5: Extracted from hybrid.py for better modularity.

This module provides a facade for backward compatibility with the original
catboost_model.py module. All public exports are re-exported from the
internal implementation modules.
"""

from raglite.forecasting.models.catboost.config import (
    CATBOOST_PARAM_GRID,
    CATBOOST_PARAM_GRID_FAST,
)
from raglite.forecasting.models.catboost.fitting import (
    _fit_and_forecast_catboost,
    fit_catboost,
)
from raglite.forecasting.models.catboost.lazy_loading import (
    _get_catboost_class,
    _get_grid_search_cv,
    _get_time_series_split,
)

__all__ = [
    "fit_catboost",
    "_fit_and_forecast_catboost",
    "_get_catboost_class",
    "_get_grid_search_cv",
    "_get_time_series_split",
    "CATBOOST_PARAM_GRID",
    "CATBOOST_PARAM_GRID_FAST",
]
