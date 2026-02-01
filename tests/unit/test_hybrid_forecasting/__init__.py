"""Unit tests for hybrid forecasting engine (Story 4.2).

This package contains tests for:
- AC1: Hybrid approach (Prophet statistical + Mistral Large reasoning)
- AC2: Key indicators supported (revenue, cash_flow, expenses)
- AC3: Forecast predictions with confidence intervals
- AC4: Minimum data requirement (8 quarters) for accuracy
- AC6: 80%+ coverage on new code
"""

# Re-export all test classes from individual modules for backward compatibility
from .test_legacy import *  # noqa: F401, F403
from .test_models import TestForecastModels  # noqa: F401

__all__ = [
    "TestForecastModels",
]
