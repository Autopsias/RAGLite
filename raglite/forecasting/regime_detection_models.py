"""Data models for regime change detection.

Story 6.8 AC6: Regime change detection data structures.
Story 7.5: Extracted from regime_detection.py for modularity.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


class RegimeChangePoint:
    """Detected regime change in time-series data.

    Story 6.8 AC6: Regime change detection for improved forecasting.

    Attributes:
        date: Date when regime change was detected
        change_type: Type of change ('mean_shift', 'variance_shift', 'trend_break')
        significance: Statistical significance (0-1, higher = more significant)
        pre_regime_mean: Mean value before change point
        post_regime_mean: Mean value after change point
        pre_regime_std: Standard deviation before change point
        post_regime_std: Standard deviation after change point
        description: Human-readable description of the change
    """

    def __init__(
        self,
        date: pd.Timestamp,
        change_type: str,
        significance: float,
        pre_regime_mean: float,
        post_regime_mean: float,
        pre_regime_std: float,
        post_regime_std: float,
        description: str = "",
    ) -> None:
        self.date = date
        self.change_type = change_type
        self.significance = significance
        self.pre_regime_mean = pre_regime_mean
        self.post_regime_mean = post_regime_mean
        self.pre_regime_std = pre_regime_std
        self.post_regime_std = post_regime_std
        self.description = description

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "date": self.date.isoformat(),
            "change_type": self.change_type,
            "significance": self.significance,
            "pre_regime_mean": self.pre_regime_mean,
            "post_regime_mean": self.post_regime_mean,
            "pre_regime_std": self.pre_regime_std,
            "post_regime_std": self.post_regime_std,
            "description": self.description,
        }


class RegimeDetectionResult:
    """Result of regime change detection analysis.

    Attributes:
        change_points: List of detected regime change points
        current_regime: Index of current regime (0-based)
        total_regimes: Total number of regimes detected
        recommendation: Recommendation for forecast model adjustment
    """

    def __init__(
        self,
        change_points: list[RegimeChangePoint],
        current_regime: int,
        total_regimes: int,
        recommendation: str,
    ) -> None:
        self.change_points = change_points
        self.current_regime = current_regime
        self.total_regimes = total_regimes
        self.recommendation = recommendation

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "change_points": [cp.to_dict() for cp in self.change_points],
            "current_regime": self.current_regime,
            "total_regimes": self.total_regimes,
            "recommendation": self.recommendation,
        }


# Story 6.8 AC6: Regime detection constants
MIN_REGIME_DATA_POINTS = 12  # Minimum data points for regime detection
DEFAULT_CUSUM_THRESHOLD = 5.0  # CUSUM threshold (tuned for financial data, higher = fewer changes)
DEFAULT_WINDOW_SIZE = 6  # Rolling window for variance detection (months)
