"""Forecasting module for time-series data extraction and analysis.

Epic 4: Forecasting & Proactive Insights
Story 4.1: Time-Series Data Extraction
Story 4.2: Forecasting Engine Implementation
"""

from raglite.forecasting.hybrid import (
    InsufficientDataError,
    explain_forecast,
    generate_forecast,
)
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
]
