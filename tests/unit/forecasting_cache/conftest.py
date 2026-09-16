"""Pytest configuration for forecasting_cache tests."""

# Import fixtures to make them available to all tests in this package
from .fixtures import (
    cached_selection_with_regressors,
    cached_selection_without_regressors,
    expired_cached_selection,
    sample_forecast_result,
    sample_historical_data,
)

__all__ = [
    "cached_selection_with_regressors",
    "cached_selection_without_regressors",
    "expired_cached_selection",
    "sample_forecast_result",
    "sample_historical_data",
]
