"""Data structures and types for forecasting validation.

Story 6.21: Unified Validation Script
Story 6.26: Multi-Metric Validation Enhancement

Contains result containers and type definitions for validation metrics.
"""

from __future__ import annotations

from dataclasses import dataclass

# =============================================================================
# Multi-Metric Result Dataclass
# =============================================================================


@dataclass
class MultiMetricResult:
    """Result container for all validation metrics.

    Attributes:
        mape: Mean Absolute Percentage Error (percentage, None if undefined)
        mase: Mean Absolute Scaled Error (scale-free, <1.0 means better than naïve)
        smape: Symmetric MAPE (bounded 0-200%)
        rmse: Root Mean Square Error (same units as data)
        mae: Mean Absolute Error (same units as data)
        bias: Mean Error (positive = over-prediction, negative = under-prediction)
    """

    mape: float | None
    mase: float | None
    smape: float | None
    rmse: float | None
    mae: float | None
    bias: float | None
