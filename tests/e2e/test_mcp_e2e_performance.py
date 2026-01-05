"""E2E tests for MCP Model Selection - Performance and Response Format Tests.

Story 7b-6: MCP Integration with Model Selection

TDD Phase: RED - These tests are expected to FAIL until implementation complete.

Test IDs map to Acceptance Criteria:
- TEST-AC-7b.6.6.x: Performance tests
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

# Mark all tests as E2E and integration
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.integration,
    pytest.mark.slow,  # E2E tests may be slow
]


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def e2e_time_series_data():
    """Create realistic time series data for E2E testing."""
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    points = []
    datetime(2022, 1, 1)
    value = 15000000.0  # 15M EUR

    for i in range(36):  # 3 years of monthly data
        month = (i % 12) + 1
        year = 2022 + (i // 12)
        date = datetime(year, month, 1)
        # Add some seasonality and trend
        seasonal = 1.0 + 0.1 * (1 if month in [6, 7, 8, 12] else 0)  # Summer/December boost
        trend = 1.02 ** (i / 12)  # 2% annual growth
        points.append(TimeSeriesPoint(date=date, value=value * seasonal * trend))

    return TimeSeriesData(
        metric_name="ebitda",
        points=points,
        interval="monthly",
        source_documents=["SECIL_Financial_Report_2024.pdf"],
    )


@pytest.fixture
def populated_cache():
    """Fixture to populate model selection cache with test data."""
    from raglite.external_data.storage import CachedModelSelection

    now = datetime.utcnow()

    return {
        "ebitda": CachedModelSelection(
            variable_name="ebitda",
            best_model="arima",
            best_mape=8.2,
            best_mase=0.75,
            use_regressors=True,
            regressor_list=["ttf_gas", "euribor"],
            candidate_results={
                "arima_True": {"mape": 8.2, "mase": 0.75},
                "prophet_True": {"mape": 84.7, "mase": 2.1},
            },
            data_characteristics={
                "trend": "linear",
                "seasonality_type": "yearly",
                "adf_statistic": -3.2,
                "adf_pvalue": 0.02,
                "seasonality_strength": 0.12,
                "model_rationale": "ARIMA selected: data is difference-stationary (ADF p=0.02), low seasonality (strength=0.12). CV MAPE: 8.2% vs Prophet 84.7%",
            },
            selected_at=now,
            expires_at=now + timedelta(days=7),
        ),
    }


# -----------------------------------------------------------------------------
# Performance Tests
# -----------------------------------------------------------------------------


class TestMCPPerformance:
    """[P1] AC-7b.6.6: Performance tests for MCP model selection."""

    @pytest.mark.asyncio
    async def test_ac_7b_6_6_3_end_to_end_under_5s(
        self,
        e2e_time_series_data,
        populated_cache,
    ) -> None:
        """TEST-AC-7b.6.6.3: E2E response time is <5s with cache hit."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch(
            "raglite.external_data.storage.model_selection.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = populated_cache["ebitda"]

            with patch(
                "raglite.forecasting.hybrid.model_generators._generate_arima_forecast"
            ) as mock_arima:
                from raglite.shared.models import ForecastPoint, ForecastResult

                mock_result = ForecastResult(
                    metric_name="ebitda",
                    forecast=[
                        ForecastPoint(
                            date=datetime(2025, 1, 1),
                            value=16000000,
                            lower=15000000,
                            upper=17000000,
                        ),
                    ],
                    model_type="arima_1_1_1",
                )
                mock_arima.return_value = mock_result

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    start = time.time()
                    with patch(
                        "raglite.forecasting.model_selection.fetch_historical_data"
                    ) as mock_fetch:
                        mock_fetch.return_value = e2e_time_series_data
                        result = await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            use_model_selection=True,
                        )
                    elapsed = time.time() - start

                    assert result.model_source == "cached"
                    assert elapsed < 5.0, f"Response took {elapsed:.2f}s, expected <5s"

    @pytest.mark.asyncio
    async def test_ac_7b_6_6_4_p50_under_3s(
        self,
        e2e_time_series_data,
        populated_cache,
    ) -> None:
        """TEST-AC-7b.6.6.4: p50 response time is <3s."""
        import statistics

        from raglite.forecasting.hybrid import generate_forecast

        timings = []

        with patch(
            "raglite.external_data.storage.model_selection.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = populated_cache["ebitda"]

            with patch(
                "raglite.forecasting.hybrid.model_generators._generate_arima_forecast"
            ) as mock_arima:
                from raglite.shared.models import ForecastPoint, ForecastResult

                mock_result = ForecastResult(
                    metric_name="ebitda",
                    forecast=[
                        ForecastPoint(
                            date=datetime(2025, 1, 1),
                            value=16000000,
                            lower=15000000,
                            upper=17000000,
                        ),
                    ],
                    model_type="arima_1_1_1",
                )
                mock_arima.return_value = mock_result

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    # Run 10 iterations to measure p50
                    for _ in range(10):
                        start = time.time()
                        with patch(
                            "raglite.forecasting.model_selection.fetch_historical_data"
                        ) as mock_fetch:
                            mock_fetch.return_value = e2e_time_series_data
                            await generate_forecast(
                                metric="ebitda",
                                periods_ahead=4,
                                use_model_selection=True,
                            )
                        timings.append(time.time() - start)

        p50 = statistics.median(timings)
        assert p50 < 3.0, f"p50 was {p50:.2f}s, expected <3s"


# -----------------------------------------------------------------------------
# MCP Tool Response Format Tests
# -----------------------------------------------------------------------------


class TestMCPToolResponse:
    """[P1] Tests for MCP tool response format integration."""

    def test_forecast_query_response_from_forecast_result(self) -> None:
        """ForecastQueryResponse.from_forecast_result includes model selection fields."""
        from raglite.shared.models import (
            ForecastPoint,
            ForecastQueryResponse,
            ForecastResult,
        )

        forecast_result = ForecastResult(
            metric_name="ebitda",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=16000000,
                    lower=15000000,
                    upper=17000000,
                    label="Jan 2025",
                ),
            ],
            model_type="arima_1_1_1",
            basis="ARIMA model trained on 36 months",
            confidence_reasoning="High confidence due to stationary data",
            periods_ahead=4,
        )

        # Create response using factory method
        response = ForecastQueryResponse.from_forecast_result(
            result=forecast_result,
            source_documents=["report.pdf"],
            model_type="arima",
            model_selection_reason="ARIMA selected: difference-stationary data",
        )

        # Verify model selection fields are passed through
        assert response.model_type == "arima"
        assert response.model_selection_reason == "ARIMA selected: difference-stationary data"

    def test_forecast_query_response_json_serializable(self) -> None:
        """ForecastQueryResponse can be serialized to JSON."""
        import json

        from raglite.shared.models import ForecastPoint, ForecastQueryResponse

        response = ForecastQueryResponse(
            metric_name="ebitda",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=16000000,
                    lower=15000000,
                    upper=17000000,
                    label="Jan 2025",
                ),
            ],
            basis="ARIMA model trained on 36 months",
            periods_ahead=4,
            model_type="arima",
            model_selection_reason="ARIMA selected: difference-stationary data",
        )

        # Should not raise - Pydantic handles datetime serialization
        json_str = response.model_dump_json()
        assert isinstance(json_str, str)

        # Parse back and verify fields
        parsed = json.loads(json_str)
        assert parsed["model_type"] == "arima"
        assert "ARIMA" in parsed["model_selection_reason"]
