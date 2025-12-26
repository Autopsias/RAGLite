"""Hybrid forecasting package.

Story 8.1 refactoring: Split hybrid.py into modules < 500 LOC.
"""

# Re-export external dependencies that were previously in hybrid.py
# Re-export from sibling module for backward compatibility
from raglite.forecasting.ensemble import generate_ensemble_forecast  # noqa: F401

# Re-export public API
from raglite.forecasting.hybrid.ensemble import (
    MIN_DATA_POINTS,
    calculate_accuracy,
    explain_forecast,
    generate_forecast,
    get_baseline_rmse,
)
from raglite.forecasting.hybrid.lazy_imports import (
    _get_catboost_class,
    _get_grid_search_cv,
    _get_lasso_regression,
    _get_linear_regression,
    _get_prophet_class,
    _get_ridge_regression,
    _get_time_series_split,
    _get_xgboost_regressor,
    _sklearn_executor,
)
from raglite.forecasting.hybrid.ml_models import (
    _fit_and_forecast_catboost,
    _fit_and_forecast_linear,
    _run_linear_forecast,
    fit_catboost,
    fit_lasso_regression,
    fit_linear_regression,
    fit_ridge_regression,
)
from raglite.forecasting.hybrid.model_generators import (
    _generate_arima_forecast,
    _generate_catboost_forecast,
    _generate_chronos_forecast,
    _generate_ets_forecast,
    _generate_lightgbm_forecast,
    _generate_linear_forecast,
    _generate_prophet_forecast,
    _generate_tft_forecast,
    _generate_xgboost_forecast,
    _route_to_model,
)
from raglite.forecasting.hybrid.preprocessing import (
    _generate_future_regressors,
    detect_yoy_percentage,
    fetch_historical_metric,
    prepare_regressors,
    select_regressors,
    transform_yoy_to_index,
    validate_regressor_scale,
    validate_timeseries_for_forecast,
)
from raglite.forecasting.models.base import InsufficientDataError  # noqa: F401
from raglite.forecasting.models.catboost_model import (
    CATBOOST_PARAM_GRID,
    CATBOOST_PARAM_GRID_FAST,
)
from raglite.forecasting.models.chronos_model import (
    _get_chronos_pipeline,
    generate_chronos_cold_start_forecast,
)

# Re-export constants from other modules
from raglite.forecasting.models.xgboost_model import (
    XGBOOST_PARAM_GRID,
    XGBOOST_PARAM_GRID_FAST,
    _run_xgboost_forecast,
    fit_xgboost,
)

# Alias for backward compatibility
_generate_chronos_cold_start_forecast = generate_chronos_cold_start_forecast

# Module-level constants for backward compatibility
from raglite.shared.logging import get_logger  # noqa: E402

logger = get_logger(__name__)
MAX_MISSING_RATIO = 0.30  # Maximum 30% missing data allowed
MIN_CV_DATA_POINTS = 12  # Minimum points for cross-validation

# Lazy loading flags (for backward compatibility)
_sklearn_loaded = False
_xgboost_loaded = False
_catboost_class = None

__all__ = [
    # Public API
    "MIN_DATA_POINTS",
    "generate_forecast",
    "explain_forecast",
    "calculate_accuracy",
    "get_baseline_rmse",
    "prepare_regressors",
    "select_regressors",
    "validate_regressor_scale",
    "detect_yoy_percentage",
    "transform_yoy_to_index",
    "fetch_historical_metric",
    "validate_timeseries_for_forecast",
    "fit_linear_regression",
    "fit_ridge_regression",
    "fit_lasso_regression",
    "fit_catboost",
    "fit_xgboost",
    "InsufficientDataError",
    "generate_ensemble_forecast",
    # Internal functions (for backward compatibility)
    "_route_to_model",
    "_generate_arima_forecast",
    "_generate_ets_forecast",
    "_generate_prophet_forecast",
    "_generate_xgboost_forecast",
    "_generate_lightgbm_forecast",
    "_generate_catboost_forecast",
    "_generate_chronos_forecast",
    "_generate_tft_forecast",
    "_generate_linear_forecast",
    "_generate_future_regressors",
    "_fit_and_forecast_catboost",
    "_fit_and_forecast_linear",
    "_run_linear_forecast",
    "_run_xgboost_forecast",
    "_get_linear_regression",
    "_get_ridge_regression",
    "_get_lasso_regression",
    "_get_time_series_split",
    "_get_xgboost_regressor",
    "_get_grid_search_cv",
    "_get_catboost_class",
    "_get_prophet_class",
    "_generate_chronos_cold_start_forecast",
    "_get_chronos_pipeline",
    "_sklearn_executor",
    # Constants
    "XGBOOST_PARAM_GRID",
    "XGBOOST_PARAM_GRID_FAST",
    "CATBOOST_PARAM_GRID",
    "CATBOOST_PARAM_GRID_FAST",
    "MAX_MISSING_RATIO",
    "MIN_CV_DATA_POINTS",
    # Module-level variables
    "logger",
    "_sklearn_loaded",
    "_xgboost_loaded",
    "_catboost_class",
]
