"""Data models for data characteristics analysis.

This module contains all enums and dataclasses used for representing
time-series analysis results.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# -----------------------------------------------------------------------------
# Enums for Classification
# -----------------------------------------------------------------------------


class Stationarity(Enum):
    """Stationarity classification based on ADF + KPSS tests."""

    STATIONARY = "stationary"  # ADF rejects, KPSS fails to reject
    TREND_STATIONARY = "trend_stationary"  # Both reject or conflicting
    DIFFERENCE_STATIONARY = "difference_stationary"  # Needs differencing
    NON_STATIONARY = "non_stationary"  # ADF fails to reject, KPSS rejects


class SeasonalityType(Enum):
    """Seasonality classification."""

    NONE = "none"
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"


class VolatilityLevel(Enum):
    """Volatility classification."""

    LOW = "low"  # CV < 0.1
    MEDIUM = "medium"  # 0.1 <= CV < 0.3
    HIGH = "high"  # CV >= 0.3


class TrendDirection(Enum):
    """Trend direction classification."""

    UP = "up"
    DOWN = "down"
    FLAT = "flat"


# -----------------------------------------------------------------------------
# Data Classes
# -----------------------------------------------------------------------------


@dataclass
class DataCharacteristics:
    """Complete data characteristics for model selection."""

    # Stationarity
    stationarity: Stationarity
    adf_pvalue: float
    kpss_pvalue: float
    suggested_differencing: int

    # Seasonality
    seasonality_type: SeasonalityType
    seasonal_period: int | None
    seasonal_strength: float  # 0-1

    # Trend
    trend_slope: float
    trend_significance: float
    trend_direction: TrendDirection

    # Volatility
    coefficient_of_variation: float
    volatility_level: VolatilityLevel
    rolling_volatility: float | None

    # Data quality
    data_length: int
    missing_ratio: float
    outlier_count: int

    # Recommendations
    recommended_models: list[str]
    model_rationale: str


@dataclass
class StationarityResult:
    """Stationarity test results."""

    stationarity: Stationarity
    adf_pvalue: float
    kpss_pvalue: float
    suggested_differencing: int


@dataclass
class SeasonalityResult:
    """Seasonality detection results."""

    seasonality_type: SeasonalityType
    seasonal_period: int | None
    seasonal_strength: float


@dataclass
class TrendResult:
    """Trend detection results."""

    slope: float
    significance: float
    direction: TrendDirection


@dataclass
class VolatilityResult:
    """Volatility measurement results."""

    cv: float
    level: VolatilityLevel
    rolling_volatility: float | None = None


@dataclass
class DataQualityResult:
    """Data quality assessment results."""

    data_length: int
    missing_ratio: float
    outlier_count: int
