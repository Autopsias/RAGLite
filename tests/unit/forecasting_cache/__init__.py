"""Model selection cache MCP integration tests.

This package contains tests for Story 7b-6, covering:
- CachedModelSelection dataclass behavior
- Cache integration with MCP forecast tool
- Model router implementations
"""

# Import fixtures for conftest.py discovery
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
