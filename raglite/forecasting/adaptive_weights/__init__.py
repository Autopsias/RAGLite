"""Adaptive weight calculation for ensemble forecasting.

Story 6.12: CatBoost Integration + Adaptive Weights

Provides backtest-driven weight optimization for ensemble models.
Weights are calculated from rolling backtest RMSE and stored in PostgreSQL.

Weight calculation formula:
    raw_weight = 1 / (RMSE + epsilon)
    normalized_weight = raw_weight / sum(raw_weights)
    capped_weight = max(MIN_WEIGHT, min(MAX_WEIGHT, normalized_weight))
    final_weight = re-normalized after capping

Weight caps maintain ensemble diversity:
    - MIN_WEIGHT = 5% (prevent model exclusion)
    - MAX_WEIGHT = 50% (prevent single model dominance)
"""

# Re-export public API and internal functions for testing
from raglite.forecasting.adaptive_weights.backtest import (
    EPSILON,
    MAX_WEIGHT,
    MIN_WEIGHT,
    _backtest_model,
    _backtest_prophet_model,
    _backtest_sklearn_model,
    _build_feature_matrix,
    _calculate_model_metrics,
    _prepare_train_test_split,
    calculate_backtest_weights,
)
from raglite.forecasting.adaptive_weights.weights import (
    _adjust_weights_no_regressors,
    _calculate_weights_from_rmse,
    _get_static_weights,
    apply_weight_caps,
    get_adaptive_weights,
    handle_model_failure,
)

__all__ = [
    # Public API
    "calculate_backtest_weights",
    "get_adaptive_weights",
    "apply_weight_caps",
    "handle_model_failure",
    # Internal functions (exported for testing)
    "_get_static_weights",
    "_adjust_weights_no_regressors",
    "_calculate_weights_from_rmse",
    "_prepare_train_test_split",
    "_build_feature_matrix",
    "_backtest_prophet_model",
    "_backtest_sklearn_model",
    "_backtest_model",
    "_calculate_model_metrics",
    # Constants
    "MIN_WEIGHT",
    "MAX_WEIGHT",
    "EPSILON",
]
