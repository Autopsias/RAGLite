"""Data Characteristics Analyzer for Time-Series Model Selection.

This module analyzes time-series data to extract characteristics needed for
intelligent model selection. It performs statistical tests on stationarity,
seasonality, trend, and volatility to recommend appropriate forecasting models.

Exports:
    - Stationarity: Enum for stationarity classification
    - SeasonalityType: Enum for seasonality type classification
    - VolatilityLevel: Enum for volatility level classification
    - TrendDirection: Enum for trend direction classification
    - DataCharacteristics: Dataclass containing all analysis results
    - analyze_data_characteristics: Main analysis function
"""

# Re-export public API
from .models import (
    DataCharacteristics,
    DataQualityResult,
    SeasonalityResult,
    Stationarity,
    StationarityResult,
    TrendDirection,
    TrendResult,
    VolatilityLevel,
    VolatilityResult,
)
from .public_api import analyze_data_characteristics

__all__ = [
    # Enums
    "Stationarity",
    "SeasonalityType",
    "VolatilityLevel",
    "TrendDirection",
    # Data Classes
    "DataCharacteristics",
    "StationarityResult",
    "SeasonalityResult",
    "TrendResult",
    "VolatilityResult",
    "DataQualityResult",
    # Main Function
    "analyze_data_characteristics",
]

# Import SeasonalityType for backward compatibility
from .models import SeasonalityType  # noqa: E402

__all__.append("SeasonalityType")
