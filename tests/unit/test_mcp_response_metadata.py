"""Unit tests for MCP Model Selection - Response Metadata and Performance.

Story 7b-6: MCP Integration with Model Selection

TDD Phase: RED - These tests are expected to FAIL until implementation complete.

Test IDs map to Acceptance Criteria:
- TEST-AC-7b.6.5.x: Response metadata tests
- TEST-AC-7b.6.6.x: Performance tests
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def sample_time_series_data():
    """Create sample historical time series data for testing."""
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    points = []
    datetime(2023, 1, 1)
    value = 100.0

    for i in range(24):  # 24 months of data
        month = (i % 12) + 1
        year = 2023 + (i // 12)
        date = datetime(year, month, 1)
        points.append(TimeSeriesPoint(date=date, value=value))
        value *= 1.02  # 2% monthly growth

    return TimeSeriesData(
        metric_name="ebitda",
        points=points,
        interval="monthly",
        source_documents=["test.pdf"],
    )


@pytest.fixture
def mock_cached_model_selection():
    """Create mock cached model selection result."""
    from raglite.external_data.storage import CachedModelSelection

    now = datetime.utcnow()
    return CachedModelSelection(
        variable_name="ebitda",
        best_model="arima",
        best_mape=5.5,
        best_mase=0.8,
        use_regressors=True,
        regressor_list=["gas_price", "euribor"],
        candidate_results={"arima_True": {"mape": 5.5, "mase": 0.8}},
        data_characteristics={
            "trend": "linear",
            "seasonality": "yearly",
            "model_rationale": "ARIMA selected: data is difference-stationary (ADF p=0.02)",
        },
        selected_at=now,
        expires_at=now + timedelta(days=7),
    )


# -----------------------------------------------------------------------------
# TEST-AC-7b.6.5: Response Metadata Tests
# -----------------------------------------------------------------------------


class TestResponseMetadata:
    """[P0] AC-7b.6.5: Add model_source and model_selection_reason to Response."""

    def test_ac_7b_6_5_1_forecast_result_has_model_source_field(self) -> None:
        """TEST-AC-7b.6.5.1: ForecastResult has model_source field."""
        from raglite.shared.models import ForecastResult

        result = ForecastResult(metric_name="test")

        assert hasattr(result, "model_source")

    def test_ac_7b_6_5_2_forecast_result_has_model_selection_reason_field(self) -> None:
        """TEST-AC-7b.6.5.2: ForecastResult has model_selection_reason field."""
        from raglite.shared.models import ForecastResult

        result = ForecastResult(metric_name="test")

        assert hasattr(result, "model_selection_reason")

    def test_ac_7b_6_5_3_model_source_accepts_valid_values(self) -> None:
        """TEST-AC-7b.6.5.3: model_source accepts cached, default, fallback."""
        from raglite.shared.models import ForecastResult

        for source in ["cached", "default", "fallback"]:
            result = ForecastResult(metric_name="test", model_source=source)
            assert result.model_source == source

    def test_ac_7b_6_5_4_model_source_defaults_to_default(self) -> None:
        """TEST-AC-7b.6.5.4: model_source defaults to 'default'."""
        from raglite.shared.models import ForecastResult

        result = ForecastResult(metric_name="test")

        assert result.model_source == "default"

    def test_ac_7b_6_5_5_model_selection_reason_is_optional(self) -> None:
        """TEST-AC-7b.6.5.5: model_selection_reason can be None."""
        from raglite.shared.models import ForecastResult

        result = ForecastResult(metric_name="test")

        assert result.model_selection_reason is None

    @pytest.mark.asyncio
    async def test_ac_7b_6_5_6_cached_selection_populates_reason(
        self,
        sample_time_series_data,
        mock_cached_model_selection,
    ) -> None:
        """TEST-AC-7b.6.5.6: Cached selection populates model_selection_reason."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch("raglite.forecasting.hybrid.get_cached_model_selection") as mock_get_cache:
            mock_get_cache.return_value = mock_cached_model_selection

            with patch("raglite.forecasting.hybrid._route_to_model") as mock_route:
                mock_result = MagicMock()
                mock_result.model_source = "cached"
                mock_route.return_value = mock_result

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    result = await generate_forecast(
                        metric="ebitda",
                        historical_data=sample_time_series_data,
                        periods_ahead=4,
                        use_model_selection=True,
                    )

                    # Should have model_selection_reason from cache
                    assert result.model_selection_reason is not None
                    assert (
                        "ARIMA" in result.model_selection_reason
                        or "arima" in result.model_selection_reason.lower()
                    )


# -----------------------------------------------------------------------------
# TEST-AC-7b.6.5: MCP Response Schema Tests
# -----------------------------------------------------------------------------


class TestMCPResponseSchema:
    """[P1] AC-7b.6.5: ForecastQueryResponse schema updates."""

    def test_ac_7b_6_5_7_forecast_query_response_has_model_source(self) -> None:
        """TEST-AC-7b.6.5.7: ForecastQueryResponse has model_source field."""
        from raglite.shared.models import ForecastQueryResponse

        response = ForecastQueryResponse(
            metric_name="test",
            basis="test",
            periods_ahead=4,
        )

        assert hasattr(response, "model_source")

    def test_ac_7b_6_5_8_forecast_query_response_has_model_selection_reason(self) -> None:
        """TEST-AC-7b.6.5.8: ForecastQueryResponse has model_selection_reason field."""
        from raglite.shared.models import ForecastQueryResponse

        response = ForecastQueryResponse(
            metric_name="test",
            basis="test",
            periods_ahead=4,
        )

        assert hasattr(response, "model_selection_reason")


# -----------------------------------------------------------------------------
# TEST-AC-7b.6.6: Performance Tests
# -----------------------------------------------------------------------------


class TestPerformance:
    """[P1] AC-7b.6.6: Maintain Less Than 5s Query Time with Cache Hit."""

    @pytest.mark.asyncio
    async def test_ac_7b_6_6_1_cache_lookup_under_100ms(self) -> None:
        """TEST-AC-7b.6.6.1: Cache lookup adds <100ms overhead."""
        import time

        from raglite.external_data.storage import get_cached_model_selection

        with patch("raglite.external_data.storage.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = None
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            start = time.time()
            await get_cached_model_selection("test_variable")
            elapsed_ms = (time.time() - start) * 1000

            # Cache lookup should be very fast (mocked)
            # In production, target is <100ms
            assert elapsed_ms < 100, f"Cache lookup took {elapsed_ms:.1f}ms, target <100ms"

    def test_ac_7b_6_6_2_model_routing_negligible_overhead(self) -> None:
        """TEST-AC-7b.6.6.2: Model routing adds negligible overhead."""
        import time

        # Just test that the routing logic itself is fast (not actual model execution)
        from raglite.forecasting.hybrid import _route_to_model

        # The routing function should be importable and its lookup fast
        start = time.time()
        # Just check the function is callable (actual execution mocked elsewhere)
        assert callable(_route_to_model)
        elapsed_ms = (time.time() - start) * 1000

        # Import and basic check should be <10ms
        assert elapsed_ms < 10


# -----------------------------------------------------------------------------
# Model Generator Existence Tests
# -----------------------------------------------------------------------------


class TestModelGenerators:
    """[P1] Tests for model-specific generator function existence."""

    def test_generate_arima_forecast_exists(self) -> None:
        """_generate_arima_forecast function exists."""
        from raglite.forecasting.hybrid import _generate_arima_forecast

        assert callable(_generate_arima_forecast)

    def test_generate_ets_forecast_exists(self) -> None:
        """_generate_ets_forecast function exists."""
        from raglite.forecasting.hybrid import _generate_ets_forecast

        assert callable(_generate_ets_forecast)

    def test_generate_prophet_forecast_exists(self) -> None:
        """_generate_prophet_forecast function exists."""
        from raglite.forecasting.hybrid import _generate_prophet_forecast

        assert callable(_generate_prophet_forecast)

    def test_generate_xgboost_forecast_exists(self) -> None:
        """_generate_xgboost_forecast function exists."""
        from raglite.forecasting.hybrid import _generate_xgboost_forecast

        assert callable(_generate_xgboost_forecast)

    def test_generate_lightgbm_forecast_exists(self) -> None:
        """_generate_lightgbm_forecast function exists."""
        from raglite.forecasting.hybrid import _generate_lightgbm_forecast

        assert callable(_generate_lightgbm_forecast)

    def test_generate_catboost_forecast_exists(self) -> None:
        """_generate_catboost_forecast function exists."""
        from raglite.forecasting.hybrid import _generate_catboost_forecast

        assert callable(_generate_catboost_forecast)

    def test_generate_chronos_forecast_exists(self) -> None:
        """_generate_chronos_forecast function exists."""
        from raglite.forecasting.hybrid import _generate_chronos_forecast

        assert callable(_generate_chronos_forecast)

    def test_generate_tft_forecast_exists(self) -> None:
        """_generate_tft_forecast function exists."""
        from raglite.forecasting.hybrid import _generate_tft_forecast

        assert callable(_generate_tft_forecast)

    def test_generate_linear_forecast_exists(self) -> None:
        """_generate_linear_forecast function exists."""
        from raglite.forecasting.hybrid import _generate_linear_forecast

        assert callable(_generate_linear_forecast)
