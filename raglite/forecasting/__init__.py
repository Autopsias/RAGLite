"""Forecasting module for time-series data extraction and analysis.

Epic 4: Forecasting & Proactive Insights
Story 4.1: Time-Series Data Extraction
Story 4.2: Forecasting Engine Implementation
Story 4.3: Automated Forecast Updates
"""

from raglite.forecasting.auto_update import identify_affected_metrics, trigger_forecast_refresh
from raglite.forecasting.hybrid import InsufficientDataError, explain_forecast, generate_forecast
from raglite.forecasting.timeseries_extract import (
    ExtractionError,
    extract_timeseries,
    normalize_to_interval,
    parse_fiscal_date,
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
]
