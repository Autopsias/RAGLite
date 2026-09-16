"""TEST-AC-7: Module Exports and Integration.

Tests for AC7 acceptance criteria from Story 7b.2:
- TEST-AC-7.1: data_analyzer.py exports DataCharacteristics
- TEST-AC-7.2: data_analyzer.py exports Stationarity enum
- TEST-AC-7.3: data_analyzer.py exports SeasonalityType enum
- TEST-AC-7.4: data_analyzer.py exports VolatilityLevel enum
- TEST-AC-7.5: data_analyzer.py exports TrendDirection enum
- TEST-AC-7.6: data_analyzer.py exports analyze_data_characteristics function
"""

from __future__ import annotations


class TestModuleExports:
    """AC7: Module Export and Integration tests."""

    def test_ac7_1_export_datacharacteristics(self) -> None:
        """TEST-AC-7.1: data_analyzer.py exports DataCharacteristics.

        Given: The data_analyzer module
        When: Importing DataCharacteristics
        Then: The dataclass should be importable
        """
        from raglite.forecasting.data_analyzer import DataCharacteristics

        assert DataCharacteristics is not None

    def test_ac7_2_export_stationarity_enum(self) -> None:
        """TEST-AC-7.2: data_analyzer.py exports Stationarity enum.

        Given: The data_analyzer module
        When: Importing Stationarity
        Then: The enum should be importable
        """
        from raglite.forecasting.data_analyzer import Stationarity

        assert hasattr(Stationarity, "STATIONARY")
        assert hasattr(Stationarity, "NON_STATIONARY")
        assert hasattr(Stationarity, "TREND_STATIONARY")
        assert hasattr(Stationarity, "DIFFERENCE_STATIONARY")

    def test_ac7_3_export_seasonality_type_enum(self) -> None:
        """TEST-AC-7.3: data_analyzer.py exports SeasonalityType enum.

        Given: The data_analyzer module
        When: Importing SeasonalityType
        Then: The enum should be importable
        """
        from raglite.forecasting.data_analyzer import SeasonalityType

        assert hasattr(SeasonalityType, "NONE")
        assert hasattr(SeasonalityType, "ADDITIVE")
        assert hasattr(SeasonalityType, "MULTIPLICATIVE")

    def test_ac7_4_export_volatility_level_enum(self) -> None:
        """TEST-AC-7.4: data_analyzer.py exports VolatilityLevel enum.

        Given: The data_analyzer module
        When: Importing VolatilityLevel
        Then: The enum should be importable
        """
        from raglite.forecasting.data_analyzer import VolatilityLevel

        assert hasattr(VolatilityLevel, "LOW")
        assert hasattr(VolatilityLevel, "MEDIUM")
        assert hasattr(VolatilityLevel, "HIGH")

    def test_ac7_5_export_trend_direction_enum(self) -> None:
        """TEST-AC-7.5: data_analyzer.py exports TrendDirection enum.

        Given: The data_analyzer module
        When: Importing TrendDirection
        Then: The enum should be importable
        """
        from raglite.forecasting.data_analyzer import TrendDirection

        assert hasattr(TrendDirection, "UP")
        assert hasattr(TrendDirection, "DOWN")
        assert hasattr(TrendDirection, "FLAT")

    def test_ac7_6_export_analyze_data_characteristics_function(self) -> None:
        """TEST-AC-7.6: data_analyzer.py exports analyze_data_characteristics.

        Given: The data_analyzer module
        When: Importing analyze_data_characteristics
        Then: The function should be importable and callable
        """
        from raglite.forecasting.data_analyzer import analyze_data_characteristics

        assert callable(analyze_data_characteristics)
