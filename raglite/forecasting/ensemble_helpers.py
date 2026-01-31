"""Helper functions for generate_ensemble_forecast() - Facade for backward compatibility.

Story 8: Refactoring to reduce generate_ensemble_forecast from 452 to ~100 lines.

This module now serves as a facade that re-exports all helper functions from their
specialized modules to maintain backward compatibility.

Original 663 LOC file split into:
- ensemble_helpers_config.py: Configuration and weight management
- ensemble_helpers_data.py: Data preparation
- ensemble_helpers_execution.py: Task building and model execution
- ensemble_helpers_results.py: Result building and aggregation
"""

from __future__ import annotations

# Re-export all public APIs for backward compatibility
from raglite.forecasting.ensemble_helpers_config import (
    get_initial_weights,
    initialize_ensemble_config,
    renormalize_weights,
)
from raglite.forecasting.ensemble_helpers_data import prepare_ensemble_data, prepare_future_features
from raglite.forecasting.ensemble_helpers_execution import (
    build_model_tasks,
    execute_ensemble_models,
    handle_fallback,
    process_model_results,
)
from raglite.forecasting.ensemble_helpers_results import (
    aggregate_metrics,
    build_ensemble_result,
    build_forecast_points,
    calculate_ensemble_forecast,
    calculate_stratified_ensemble_forecast,
)

__all__ = [
    # Config
    "get_initial_weights",
    "initialize_ensemble_config",
    "renormalize_weights",
    # Data
    "prepare_ensemble_data",
    "prepare_future_features",
    # Execution
    "build_model_tasks",
    "execute_ensemble_models",
    "handle_fallback",
    "process_model_results",
    # Results
    "aggregate_metrics",
    "build_ensemble_result",
    "build_forecast_points",
    "calculate_ensemble_forecast",
    "calculate_stratified_ensemble_forecast",
]
