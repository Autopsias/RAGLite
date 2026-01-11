"""ATDD Tests for ARIMA Model Wrapper - Advanced Features (Part 2).

This file tests:
- AC3: Exogenous Variable Support
- AC4: Frequency Handling
- AC6: Graceful Fallback on Failure
- AC7: Module Exports
- Edge Cases
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("LIGHTWEIGHT_TESTS") == "true",
    reason="ARIMA tests require real pmdarima (not mocked)",
)
