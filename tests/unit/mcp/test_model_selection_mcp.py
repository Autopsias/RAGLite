"""Unit tests for Story 7b-6: Model Selection Cache MCP Integration.

Tests the integration between model selection cache and MCP forecast tool,
including cache hits, cache misses, regressor filtering, and fallback behavior.

NOTE: All dependencies are mocked - no database required.

REFACTORED: This file now serves as a facade that imports from:
- test_model_selection_mcp_fixtures.py (shared fixtures)
- test_model_selection_mcp_cache.py (cache integration tests)
- test_model_selection_mcp_routers.py (router tests)

The original tests have been split into these modules to reduce file size
while maintaining backward compatibility with existing imports.
"""

# Re-export all test classes for backward compatibility
from tests.unit.mcp.test_model_selection_mcp_cache import (
    TestCachedModelSelection,
    TestModelSelectionCacheIntegration,
)

# Re-export all fixtures for backward compatibility
from tests.unit.mcp.test_model_selection_mcp_fixtures import (
    cached_selection_with_regressors,
    cached_selection_without_regressors,
    expired_cached_selection,
    mock_regressor_fetch,
    sample_forecast_result,
    sample_historical_data,
)
from tests.unit.mcp.test_model_selection_mcp_routers import TestModelRouters

__all__ = [
    # Fixtures
    "mock_regressor_fetch",
    "sample_historical_data",
    "sample_forecast_result",
    "cached_selection_with_regressors",
    "cached_selection_without_regressors",
    "expired_cached_selection",
    # Test classes
    "TestCachedModelSelection",
    "TestModelSelectionCacheIntegration",
    "TestModelRouters",
]

# Unit tests - all external dependencies are mocked
pytestmark: list[object] = []
