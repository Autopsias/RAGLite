"""MCP Model Routing test suite - facade for backward compatibility.

This package contains tests for MCP Model Selection - Model Routing and Regressor Filtering.
The original test_mcp_model_routing_core.py has been split into smaller modules:
- fixtures: Shared test fixtures
- test_model_routing: Model routing tests (AC-7b.6.2.x)
- test_regressor_filtering: Regressor filtering tests (AC-7b.6.3.x)
- test_fallback_handling: Fallback handling tests (AC-7b.6.4.x)
"""

# Import all test classes from split modules to preserve test discovery
from .test_fallback_handling import TestFallbackHandling
from .test_model_routing import TestModelRouting
from .test_regressor_filtering import TestRegressorFiltering

# Explicit public API
__all__ = [
    # Test classes
    "TestModelRouting",
    "TestRegressorFiltering",
    "TestFallbackHandling",
]
