"""Unit tests for hybrid forecasting engine (Story 4.2).

Tests cover:
- AC1: Hybrid approach (Prophet statistical + Mistral Large reasoning)
- AC2: Key indicators supported (revenue, cash_flow, expenses)
- AC3: Forecast predictions with confidence intervals
- AC4: Minimum data requirement (8 quarters) for accuracy
- AC6: 80%+ coverage on new code
"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from raglite.forecasting.hybrid import (  # noqa: E402
    MIN_DATA_POINTS,
    InsufficientDataError,
    explain_forecast,
    generate_forecast,
)
from raglite.shared.models import (  # noqa: E402
    ForecastPoint,
    ForecastResult,
    TimeSeriesData,
    TimeSeriesPoint,
)

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests require real Prophet for hybrid forecasting
pytestmark = pytest.mark.skipif(
    os.environ.get("LIGHTWEIGHT_TESTS") == "true",
    reason="Hybrid forecasting tests require real Prophet (not mocked)",
)


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
            with patch(
                "raglite.forecasting.hybrid.ensemble.ensure_historical_data",
                new_callable=AsyncMock,
            ) as mock_ensure:
                mock_ensure.return_value = data
                await generate_forecast(metric="revenue")

    @pytest.mark.asyncio
    async def test_insufficient_data_error_message(self) -> None:
        """AC4: Error message includes count of available data points."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0),
            TimeSeriesPoint(date=datetime(2024, 4, 1), value=110.0),
        ]
        data = TimeSeriesData(metric_name="revenue", points=points, interval="quarterly")

        with pytest.raises(InsufficientDataError, match="Got 2"):
            with patch(
                "raglite.forecasting.hybrid.ensemble.ensure_historical_data",
                new_callable=AsyncMock,
            ) as mock_ensure:
                mock_ensure.return_value = data
                await generate_forecast(metric="revenue")


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
            patch("raglite.forecasting.hybrid.ensemble.explain_forecast") as mock_explain,
            patch(
                "raglite.forecasting.hybrid.ensemble.ensure_historical_data",
                new_callable=AsyncMock,
            ) as mock_ensure,
        ):
            mock_explain.return_value = '{"summary": "Forecast shows growth.", "confidence_rationale": "Based on 8 quarters of data."}'
            mock_ensure.return_value = historical_data

            result = await generate_forecast(
                metric="revenue",
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
            patch("raglite.forecasting.hybrid.ensemble.explain_forecast") as mock_mistral,
            patch(
                "raglite.forecasting.hybrid.ensemble.ensure_historical_data",
                new_callable=AsyncMock,
            ) as mock_ensure,
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

            mock_ensure.return_value = historical_data
            result = await generate_forecast(metric="revenue")

            assert result.metric_name == "revenue"

    @pytest.mark.asyncio
    async def test_generate_forecast_supports_cash_flow(self) -> None:
        """AC2: Supports cash_flow metric."""
        historical_data = self._create_historical_data(num_points=8, metric="cash_flow")

        with (
            patch("prophet.Prophet") as mock_prophet_class,
            patch("raglite.forecasting.hybrid.ensemble.explain_forecast") as mock_mistral,
            patch(
                "raglite.forecasting.hybrid.ensemble.ensure_historical_data",
                new_callable=AsyncMock,
            ) as mock_ensure,
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

            mock_ensure.return_value = historical_data
            result = await generate_forecast(metric="cash_flow")

            assert result.metric_name == "cash_flow"

    @pytest.mark.asyncio
    async def test_generate_forecast_supports_expenses(self) -> None:
        """AC2: Supports expenses metric."""
        historical_data = self._create_historical_data(num_points=8, metric="expenses")

        with (
            patch("prophet.Prophet") as mock_prophet_class,
            patch("raglite.forecasting.hybrid.ensemble.explain_forecast") as mock_mistral,
            patch(
                "raglite.forecasting.hybrid.ensemble.ensure_historical_data",
                new_callable=AsyncMock,
            ) as mock_ensure,
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

            mock_ensure.return_value = historical_data
            result = await generate_forecast(metric="expenses")

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

        # Patch where get_mistral_client is used (in ensemble module)
        with patch("raglite.forecasting.hybrid.ensemble.get_mistral_client") as mock_client:
            # get_mistral_client returns a synchronous client
            mock_mistral = MagicMock()
            mock_mistral.chat.complete.return_value = mock_response
            mock_client.return_value = mock_mistral

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

        # Patch Mistral client to raise an error during chat.complete()
        with patch("raglite.forecasting.hybrid.ensemble.get_mistral_client") as mock_client:
            mock_mistral = MagicMock()
            mock_mistral.chat.complete.side_effect = Exception("API error")
            mock_client.return_value = mock_mistral

            # Function should handle exception and return fallback
            explanation = await explain_forecast(forecast, "Context")
            # Fallback should mention data points and periods
            assert (
                "1 historical data points" in explanation
                or "1 historical data point" in explanation
            )
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

        # Patch Mistral client to return invalid JSON
        with patch("raglite.forecasting.hybrid.ensemble.get_mistral_client") as mock_client:
            # get_mistral_client returns a synchronous client
            mock_mistral = MagicMock()
            mock_mistral.chat.complete.return_value = mock_response
            mock_client.return_value = mock_mistral

            explanation = await explain_forecast(forecast, "Context")

            # Should return the raw text when JSON parsing fails
            assert "Not valid JSON" in explanation
