"""Base classes and shared types for forecasting models.

Story 7.5: Forecasting model base module extraction.
"""

from __future__ import annotations


class InsufficientDataError(ValueError):
    """Raised when insufficient data for forecasting.

    Story 4.2 AC1: Error handling for data requirements.
    """

    pass


# Minimum data points required for reliable forecasting
# FIX (2025-12-01): Lowered from 8 to 6 to allow GROUP-level SQL data
# with occasional missing months (e.g., 7 months Feb-Sep missing June)
# Prophet can produce reasonable forecasts with 6+ monthly data points
MIN_DATA_POINTS = 6
