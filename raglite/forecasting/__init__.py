"""Forecasting module for time-series data extraction and analysis.

Epic 4: Forecasting & Proactive Insights
Story 4.1: Time-Series Data Extraction
"""

from raglite.forecasting.timeseries_extract import (
    ExtractionError,
    extract_timeseries,
    normalize_to_interval,
    parse_fiscal_date,
)

__all__ = [
    "extract_timeseries",
    "normalize_to_interval",
    "parse_fiscal_date",
    "ExtractionError",
]
