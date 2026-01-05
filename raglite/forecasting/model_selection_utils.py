"""Utility functions for model selection cross-validation.

Helper functions for fitting individual models during cross-validation.

This is a facade module that maintains backward compatibility by re-exporting
all functions from the refactored model selection modules.
"""

# Re-export all public APIs from the refactored modules
from raglite.forecasting.model_selection_bias import (
    apply_bias_correction,
    calculate_bias,
    detect_bias_regime_change,
    estimate_rolling_bias,
)
from raglite.forecasting.model_selection_features import (
    _build_prediction_features,
    create_lagged_features,
)
from raglite.forecasting.model_selection_fitting import (
    fit_chronos,
    fit_ml_model,
    fit_prophet,
    fit_tft,
)
from raglite.forecasting.model_selection_metrics import (
    calculate_mape,
    calculate_mase,
)

__all__ = [
    "fit_prophet",
    "fit_ml_model",
    "fit_chronos",
    "fit_tft",
    "calculate_mape",
    "calculate_mase",
    "create_lagged_features",
    "_build_prediction_features",
    "calculate_bias",
    "apply_bias_correction",
    "estimate_rolling_bias",
    "detect_bias_regime_change",
]
