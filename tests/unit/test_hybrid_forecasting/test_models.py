"""Tests for Pydantic forecast models (AC3)."""

import os
from datetime import datetime

import pytest

from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesPoint

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests require real Prophet for hybrid forecasting
pytestmark = pytest.mark.skipif(
    os.environ.get("LIGHTWEIGHT_TESTS") == "true",
    reason="Hybrid forecasting tests require real Prophet (not mocked)",
)


class TestForecastModels:
    """Tests for Pydantic forecast models (AC3)."""

    def test_forecast_point_creation(self) -> None:
        """AC3: ForecastPoint contains date, value, lower, upper, label."""
        point = ForecastPoint(
            date=datetime(2025, 1, 1),
            value=1500000.0,
            lower=1400000.0,
            upper=1600000.0,
            label="Q1 2025",
        )

        assert point.date == datetime(2025, 1, 1)
        assert point.value == 1500000.0
        assert point.lower == 1400000.0
        assert point.upper == 1600000.0
        assert point.label == "Q1 2025"

    def test_forecast_point_optional_label(self) -> None:
        """AC3: ForecastPoint label is optional."""
        point = ForecastPoint(
            date=datetime(2025, 1, 1),
            value=1500000.0,
            lower=1400000.0,
            upper=1600000.0,
        )

        assert point.label is None

    def test_forecast_result_creation(self) -> None:
        """AC3: ForecastResult contains all required fields."""
        historical = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=1000000.0),
            TimeSeriesPoint(date=datetime(2024, 4, 1), value=1100000.0),
        ]
        forecast = [
            ForecastPoint(
                date=datetime(2025, 1, 1),
                value=1500000.0,
                lower=1400000.0,
                upper=1600000.0,
            ),
        ]

        result = ForecastResult(
            metric_name="revenue",
            historical_data=historical,
            forecast=forecast,
            confidence_reasoning="Test reasoning",
            basis="Prophet model trained on 8 quarters",
            accuracy_estimate="±15%",
            periods_ahead=4,
        )

        assert result.metric_name == "revenue"
        assert len(result.historical_data) == 2
        assert len(result.forecast) == 1
        assert result.confidence_reasoning == "Test reasoning"
        assert result.basis == "Prophet model trained on 8 quarters"
        assert result.accuracy_estimate == "±15%"
        assert result.periods_ahead == 4

    def test_forecast_result_defaults(self) -> None:
        """AC3: ForecastResult has sensible defaults."""
        result = ForecastResult(metric_name="revenue")

        assert result.historical_data == []
        assert result.forecast == []
        assert result.confidence_reasoning == ""
        assert result.basis == ""
        assert result.accuracy_estimate == "±15%"
        assert result.periods_ahead == 4
