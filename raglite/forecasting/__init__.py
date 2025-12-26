"""Forecasting module for time-series data extraction and analysis.

Epic 4: Forecasting & Proactive Insights
Story 4.1: Time-Series Data Extraction
Story 4.2: Forecasting Engine Implementation
Story 4.3: Automated Forecast Updates
Story 6.21: Unified Validation Script
"""

from raglite.forecasting.auto_update import identify_affected_metrics, trigger_forecast_refresh
from raglite.forecasting.ensemble import generate_ensemble_forecast
from raglite.forecasting.hybrid import InsufficientDataError, explain_forecast, generate_forecast
from raglite.forecasting.timeseries import (
    ExtractionError,
    extract_timeseries,
    normalize_to_interval,
    parse_fiscal_date,
)
from raglite.forecasting.validation_methods import (
    calculate_cv_mape,
    calculate_holdout_mape,
    calculate_walkforward_mape,
)
from raglite.forecasting.validation_schema import (
    ModelPerformanceStats,
    QualityGateResult,
    UnifiedValidationResult,
    VariableConfig,
    VariableValidationResult,
)

__all__ = [
    # Story 4.1: Time-series extraction
    "extract_timeseries",
    "normalize_to_interval",
    "parse_fiscal_date",
    "ExtractionError",
    # Story 4.2: Forecasting engine
    "generate_forecast",
    "explain_forecast",
    "InsufficientDataError",
    # Story 4.3: Automated forecast updates
    "trigger_forecast_refresh",
    "identify_affected_metrics",
    # Story 6.4/6.21: Ensemble forecasting
    "generate_ensemble_forecast",
    # Story 6.21: Validation
    "calculate_holdout_mape",
    "calculate_walkforward_mape",
    "calculate_cv_mape",
    "UnifiedValidationResult",
    "VariableValidationResult",
    "ModelPerformanceStats",
    "QualityGateResult",
    "VariableConfig",
]
