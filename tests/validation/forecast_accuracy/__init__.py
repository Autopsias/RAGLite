"""Forecast accuracy validation framework.

Story 4.10 AC1/AC2: Validates forecast accuracy using backtesting methodology.
Story 5.0.4 AC6: Extended with EBITDA and turnover metrics.
Target: MAPE ≤15% for revenue, expenses, cash_flow, ebitda, turnover (NFR10 requirement).

This module provides backward-compatible re-exports from the split test structure.
Original file: tests/validation/test_forecast_accuracy.py (673 LOC)
Split into: 8 modules under tests/validation/forecast_accuracy/
"""

# Re-export data models
from .models import ForecastValidationResult
from .test_backtesting import TestBacktestingWorkflow

# Re-export test data fixtures
from .test_data import (
    create_growth_data,
    create_seasonal_data,
    create_volatile_data,
)

# Re-export test classes (for pytest collection)
from .test_mape import TestMAPECalculation
from .test_per_period_errors import TestPerPeriodErrors
from .test_threshold import TestThresholdConfiguration

# Re-export validator
from .validator import ForecastAccuracyValidator

__all__ = [
    # Data models
    "ForecastValidationResult",
    # Validator
    "ForecastAccuracyValidator",
    # Test data fixtures
    "create_growth_data",
    "create_seasonal_data",
    "create_volatile_data",
    # Test classes
    "TestMAPECalculation",
    "TestPerPeriodErrors",
    "TestThresholdConfiguration",
    "TestBacktestingWorkflow",
]
