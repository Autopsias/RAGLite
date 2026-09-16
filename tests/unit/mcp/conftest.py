"""Pytest configuration for MCP unit tests.

Imports shared fixtures from forecasting_cache to make them available.
"""

# Import fixtures from forecasting_cache directory
from tests.unit.forecasting_cache.fixtures import (
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
