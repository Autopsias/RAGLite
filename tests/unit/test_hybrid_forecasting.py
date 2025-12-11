"""Unit tests for hybrid forecasting engine (Story 4.2).

Tests cover:
- AC1: Hybrid approach (Prophet statistical + Mistral Large reasoning)
- AC2: Key indicators supported (revenue, cash_flow, expenses)
- AC3: Forecast predictions with confidence intervals
- AC4: Minimum data requirement (8 quarters) for accuracy
- AC6: 80%+ coverage on new code
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from raglite.forecasting.hybrid import (
    MIN_DATA_POINTS,
    InsufficientDataError,
    explain_forecast,
    generate_forecast,
)
from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesData, TimeSeriesPoint


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


class TestInsufficientDataError:
    """Tests for minimum data requirement (AC4)."""

    def test_min_data_points_constant(self) -> None:
        """AC4: MIN_DATA_POINTS is 6 (1.5 years quarterly)."""
        assert MIN_DATA_POINTS == 6

    @pytest.mark.asyncio
    async def test_insufficient_data_raises_error(self) -> None:
        """AC4: Raise InsufficientDataError when <3 data points.

        Story 6.13: With Chronos-2 cold-start, we support 3-5 data points.
        Only <3 data points raises an error.
        """
        # Only 2 data points (less than minimum 3 for Chronos-2)
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0),
            TimeSeriesPoint(date=datetime(2024, 4, 1), value=110.0),
        ]
        data = TimeSeriesData(
            metric_name="revenue",
            points=points,
            interval="quarterly",
            source_documents=["test.pdf"],
        )

        with pytest.raises(InsufficientDataError, match="minimum 3 data points"):
            await generate_forecast(metric="revenue", historical_data=data)

    @pytest.mark.asyncio
    async def test_insufficient_data_error_message(self) -> None:
        """AC4: Error message includes count of available data points."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0),
            TimeSeriesPoint(date=datetime(2024, 4, 1), value=110.0),
        ]
        data = TimeSeriesData(metric_name="revenue", points=points, interval="quarterly")

        with pytest.raises(InsufficientDataError, match="Got 2"):
            await generate_forecast(metric="revenue", historical_data=data)


class TestGenerateForecast:
    """Tests for generate_forecast function (AC1, AC2, AC3)."""

    def _create_historical_data(
        self, num_points: int = 8, metric: str = "revenue"
    ) -> TimeSeriesData:
        """Helper to create historical time-series data for testing."""
        base_date = datetime(2022, 1, 1)
        points = []
        value = 1000000.0

        for i in range(num_points):
            month = ((i * 3) % 12) + 1
            year = base_date.year + (i * 3) // 12
            date = datetime(year, month, 1)
            points.append(TimeSeriesPoint(date=date, value=value, label=f"Q{(i % 4) + 1} {year}"))
            value *= 1.05  # 5% growth per quarter

        return TimeSeriesData(
            metric_name=metric,
            points=points,
            interval="quarterly",
            source_documents=["report.pdf"],
        )

    @pytest.mark.asyncio
    async def test_generate_forecast_with_mocked_prophet(self) -> None:
        """AC1: Generate forecast using Prophet (mocked) + Mistral Large."""
        historical_data = self._create_historical_data(num_points=8)

        # Mock Prophet model
        mock_prophet = MagicMock()

        # Create mock forecast DataFrame
        mock_forecast_df = pd.DataFrame(
            {
                "ds": pd.to_datetime(
                    [
                        "2024-01-01",
                        "2024-04-01",
                        "2024-07-01",
                        "2024-10-01",
                        "2025-01-01",
                        "2025-04-01",
                        "2025-07-01",
                        "2025-10-01",
                    ]
                ),
                "yhat": [
                    1100000,
                    1150000,
                    1200000,
                    1250000,
                    1300000,
                    1350000,
                    1400000,
                    1450000,
                ],
                "yhat_lower": [
                    1050000,
                    1100000,
                    1150000,
                    1200000,
                    1250000,
                    1300000,
                    1350000,
                    1400000,
                ],
                "yhat_upper": [
                    1150000,
                    1200000,
                    1250000,
                    1300000,
                    1350000,
                    1400000,
                    1450000,
                    1500000,
                ],
            }
        )

        mock_prophet.fit.return_value = mock_prophet
        mock_prophet.make_future_dataframe.return_value = pd.DataFrame(
            {"ds": mock_forecast_df["ds"]}
        )
        mock_prophet.predict.return_value = mock_forecast_df

        # Mock Mistral client
        mock_mistral_response = MagicMock()
        mock_mistral_response.choices = [MagicMock()]
        mock_mistral_response.choices[
            0
        ].message.content = '{"summary": "Forecast shows growth.", "confidence_rationale": "Based on 8 quarters of data."}'

        with (
            patch("prophet.Prophet", return_value=mock_prophet),
            patch("raglite.forecasting.hybrid.get_mistral_client") as mock_mistral_client,
        ):
            mock_mistral_client.return_value.chat.complete.return_value = mock_mistral_response

            result = await generate_forecast(
                metric="revenue",
                historical_data=historical_data,
                periods_ahead=4,
            )

            # Verify result structure (AC3)
            assert result.metric_name == "revenue"
            assert len(result.forecast) == 4  # 4 periods ahead
            assert result.periods_ahead == 4

            # Verify confidence intervals present (AC3)
            for point in result.forecast:
                assert point.value > 0
                assert point.lower < point.value < point.upper
                assert point.label is not None

    @pytest.mark.asyncio
    async def test_generate_forecast_supports_revenue(self) -> None:
        """AC2: Supports revenue metric."""
        historical_data = self._create_historical_data(num_points=8, metric="revenue")

        with (
            patch("prophet.Prophet") as mock_prophet_class,
            patch("raglite.forecasting.hybrid.get_mistral_client") as mock_mistral,
        ):
            # Setup mock Prophet
            mock_prophet = MagicMock()
            mock_prophet_class.return_value = mock_prophet
            mock_forecast_df = pd.DataFrame(
                {
                    "ds": pd.to_datetime(
                        [
                            "2024-01-01",
                            "2024-04-01",
                            "2024-07-01",
                            "2024-10-01",
                            "2025-01-01",
                            "2025-04-01",
                            "2025-07-01",
                            "2025-10-01",
                        ]
                    ),
                    "yhat": [1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.45],
                    "yhat_lower": [1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35],
                    "yhat_upper": [1.2, 1.25, 1.3, 1.35, 1.4, 1.45, 1.5, 1.55],
                }
            )
            mock_prophet.fit.return_value = mock_prophet
            mock_prophet.make_future_dataframe.return_value = pd.DataFrame(
                {"ds": mock_forecast_df["ds"]}
            )
            mock_prophet.predict.return_value = mock_forecast_df

            # Setup mock Mistral
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"summary": "Revenue forecast"}'
            mock_mistral.return_value.chat.complete.return_value = mock_response

            result = await generate_forecast(metric="revenue", historical_data=historical_data)

            assert result.metric_name == "revenue"

    @pytest.mark.asyncio
    async def test_generate_forecast_supports_cash_flow(self) -> None:
        """AC2: Supports cash_flow metric."""
        historical_data = self._create_historical_data(num_points=8, metric="cash_flow")

        with (
            patch("prophet.Prophet") as mock_prophet_class,
            patch("raglite.forecasting.hybrid.get_mistral_client") as mock_mistral,
        ):
            mock_prophet = MagicMock()
            mock_prophet_class.return_value = mock_prophet
            mock_forecast_df = pd.DataFrame(
                {
                    "ds": pd.to_datetime(
                        [
                            "2024-01-01",
                            "2024-04-01",
                            "2024-07-01",
                            "2024-10-01",
                            "2025-01-01",
                            "2025-04-01",
                            "2025-07-01",
                            "2025-10-01",
                        ]
                    ),
                    "yhat": [1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.45],
                    "yhat_lower": [1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35],
                    "yhat_upper": [1.2, 1.25, 1.3, 1.35, 1.4, 1.45, 1.5, 1.55],
                }
            )
            mock_prophet.fit.return_value = mock_prophet
            mock_prophet.make_future_dataframe.return_value = pd.DataFrame(
                {"ds": mock_forecast_df["ds"]}
            )
            mock_prophet.predict.return_value = mock_forecast_df

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"summary": "Cash flow forecast"}'
            mock_mistral.return_value.chat.complete.return_value = mock_response

            result = await generate_forecast(metric="cash_flow", historical_data=historical_data)

            assert result.metric_name == "cash_flow"

    @pytest.mark.asyncio
    async def test_generate_forecast_supports_expenses(self) -> None:
        """AC2: Supports expenses metric."""
        historical_data = self._create_historical_data(num_points=8, metric="expenses")

        with (
            patch("prophet.Prophet") as mock_prophet_class,
            patch("raglite.forecasting.hybrid.get_mistral_client") as mock_mistral,
        ):
            mock_prophet = MagicMock()
            mock_prophet_class.return_value = mock_prophet
            mock_forecast_df = pd.DataFrame(
                {
                    "ds": pd.to_datetime(
                        [
                            "2024-01-01",
                            "2024-04-01",
                            "2024-07-01",
                            "2024-10-01",
                            "2025-01-01",
                            "2025-04-01",
                            "2025-07-01",
                            "2025-10-01",
                        ]
                    ),
                    "yhat": [1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.45],
                    "yhat_lower": [1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35],
                    "yhat_upper": [1.2, 1.25, 1.3, 1.35, 1.4, 1.45, 1.5, 1.55],
                }
            )
            mock_prophet.fit.return_value = mock_prophet
            mock_prophet.make_future_dataframe.return_value = pd.DataFrame(
                {"ds": mock_forecast_df["ds"]}
            )
            mock_prophet.predict.return_value = mock_forecast_df

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"summary": "Expenses forecast"}'
            mock_mistral.return_value.chat.complete.return_value = mock_response

            result = await generate_forecast(metric="expenses", historical_data=historical_data)

            assert result.metric_name == "expenses"


class TestExplainForecast:
    """Tests for explain_forecast function (AC1: LLM reasoning layer)."""

    @pytest.mark.asyncio
    async def test_explain_forecast_with_mock_mistral(self) -> None:
        """AC1: LLM reasoning generates confidence explanation."""
        forecast = ForecastResult(
            metric_name="revenue",
            historical_data=[
                TimeSeriesPoint(date=datetime(2024, 1, 1), value=1000000.0),
            ],
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=1500000.0,
                    lower=1400000.0,
                    upper=1600000.0,
                    label="Q1 2025",
                ),
            ],
            periods_ahead=4,
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"summary": "Revenue is projected to grow by 50%.", "confidence_rationale": "Based on historical trends."}'

        with patch("raglite.forecasting.hybrid.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_response

            explanation = await explain_forecast(forecast, "Financial context")

            assert "Revenue is projected to grow" in explanation
            assert "Based on historical trends" in explanation

    @pytest.mark.asyncio
    async def test_explain_forecast_fallback_on_error(self) -> None:
        """AC1: Fallback explanation when LLM fails."""
        forecast = ForecastResult(
            metric_name="revenue",
            historical_data=[
                TimeSeriesPoint(date=datetime(2024, 1, 1), value=1000000.0),
            ],
            forecast=[],
            periods_ahead=4,
        )

        with patch("raglite.forecasting.hybrid.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.side_effect = Exception("API error")

            explanation = await explain_forecast(forecast, "Context")

            # Fallback should mention data points and periods
            assert "1 historical data points" in explanation
            assert "4 periods" in explanation

    @pytest.mark.asyncio
    async def test_explain_forecast_handles_invalid_json(self) -> None:
        """AC1: Handle invalid JSON response gracefully."""
        forecast = ForecastResult(
            metric_name="revenue",
            historical_data=[],
            forecast=[],
            periods_ahead=4,
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not valid JSON - just plain text explanation"

        with patch("raglite.forecasting.hybrid.get_mistral_client") as mock_client:
            mock_client.return_value.chat.complete.return_value = mock_response

            explanation = await explain_forecast(forecast, "Context")

            # Should return the raw text when JSON parsing fails
            assert "Not valid JSON" in explanation
