"""Unit tests for MCP Model Selection - Cache Lookup.

Story 7b-6: MCP Integration with Model Selection

TDD Phase: RED - These tests are expected to FAIL until implementation complete.

Test IDs map to Acceptance Criteria:
- TEST-AC-7b.6.1.x: Cache lookup tests
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


@pytest.fixture
def expired_cached_model_selection():
    """Create expired cached model selection result."""
    from raglite.external_data.storage import CachedModelSelection

    now = datetime.utcnow()
    return CachedModelSelection(
        variable_name="ebitda",
        best_model="arima",
        best_mape=5.5,
        best_mase=0.8,
        use_regressors=False,
        regressor_list=[],
        candidate_results={},
        data_characteristics=None,
        selected_at=now - timedelta(days=10),
        expires_at=now - timedelta(days=3),  # Expired 3 days ago
    )


# -----------------------------------------------------------------------------
# TEST-AC-7b.6.1: Cache Lookup Tests
# -----------------------------------------------------------------------------


class TestCacheLookup:
    """[P0] AC-7b.6.1: Check Model Selection Cache First."""

    def test_ac_7b_6_1_1_generate_forecast_accepts_use_model_selection_param(
        self,
    ) -> None:
        """TEST-AC-7b.6.1.1: generate_forecast accepts use_model_selection parameter."""
        import inspect

        from raglite.forecasting.hybrid import generate_forecast

        sig = inspect.signature(generate_forecast)
        param_names = list(sig.parameters.keys())

        assert "use_model_selection" in param_names, (
            "generate_forecast should accept use_model_selection parameter"
        )

    def test_ac_7b_6_1_2_use_model_selection_defaults_to_true(self) -> None:
        """TEST-AC-7b.6.1.2: use_model_selection defaults to True."""
        import inspect

        from raglite.forecasting.hybrid import generate_forecast

        sig = inspect.signature(generate_forecast)
        param = sig.parameters.get("use_model_selection")

        assert param is not None
        assert param.default is True, "use_model_selection should default to True"

    @pytest.mark.asyncio
    async def test_ac_7b_6_1_3_cache_lookup_called_when_enabled(
        self,
        sample_time_series_data,
        mock_cached_model_selection,
    ) -> None:
        """TEST-AC-7b.6.1.3: get_cached_model_selection is called when use_model_selection=True."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch(
            "raglite.forecasting.hybrid.ensemble.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = mock_cached_model_selection

            # Mock the model routing to avoid actual model execution
            with patch("raglite.forecasting.model_selection.select_model_type") as mock_route:
                mock_route.return_value = MagicMock()

                # Mock explain_forecast to avoid LLM calls
                with patch("raglite.forecasting.hybrid.ensemble.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    with patch(
                        "raglite.forecasting.hybrid.preprocessing_data.fetch_historical_metric"
                    ) as mock_fetch:
                        mock_fetch.return_value = sample_time_series_data
                        await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            use_model_selection=True,
                        )

                    mock_get_cache.assert_called_once_with("ebitda")

    @pytest.mark.asyncio
    async def test_ac_7b_6_1_4_cache_lookup_skipped_when_disabled(
        self,
        sample_time_series_data,
    ) -> None:
        """TEST-AC-7b.6.1.4: get_cached_model_selection NOT called when use_model_selection=False."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch(
            "raglite.forecasting.hybrid.ensemble.get_cached_model_selection"
        ) as mock_get_cache:
            # Mock Prophet to avoid actual model execution
            with patch(
                "raglite.forecasting.hybrid.lazy_imports._get_prophet_class"
            ) as mock_prophet_class:
                mock_prophet = MagicMock()
                mock_prophet.fit.return_value = None
                mock_prophet.make_future_dataframe.return_value = MagicMock()
                mock_prophet.predict.return_value = MagicMock()
                mock_prophet_class.return_value = mock_prophet

                # Mock explain_forecast
                with patch("raglite.forecasting.hybrid.ensemble.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    with patch(
                        "raglite.forecasting.hybrid.preprocessing_data.fetch_historical_metric"
                    ) as mock_fetch:
                        mock_fetch.return_value = sample_time_series_data
                        await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            use_model_selection=False,
                        )

                    mock_get_cache.assert_not_called()

    @pytest.mark.asyncio
    async def test_ac_7b_6_1_5_uses_cached_model_when_valid(
        self,
        sample_time_series_data,
        mock_cached_model_selection,
    ) -> None:
        """TEST-AC-7b.6.1.5: Uses cached model configuration when cache is valid."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch(
            "raglite.forecasting.hybrid.ensemble.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = mock_cached_model_selection

            # Mock ensure_historical_data to return our sample data (Story 8.1: historical_data required)
            with patch(
                "raglite.forecasting.hybrid.ensemble.ensure_historical_data"
            ) as mock_ensure_data:
                mock_ensure_data.return_value = sample_time_series_data

                with patch(
                    "raglite.forecasting.hybrid.model_generators._route_to_model"
                ) as mock_route:
                    mock_result = MagicMock()
                    mock_route.return_value = mock_result

                    with patch(
                        "raglite.forecasting.hybrid.ensemble.explain_forecast"
                    ) as mock_explain:
                        mock_explain.return_value = "Test explanation"

                        await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            use_model_selection=True,
                        )

                        # Should route to ARIMA (from cached selection)
                        mock_route.assert_called_once()
                        call_kwargs = mock_route.call_args[1]
                        assert call_kwargs["model_name"] == "arima"

    @pytest.mark.asyncio
    async def test_ac_7b_6_1_6_ignores_expired_cache(
        self,
        sample_time_series_data,
        expired_cached_model_selection,
    ) -> None:
        """TEST-AC-7b.6.1.6: Falls back to Prophet when cache is expired."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch(
            "raglite.forecasting.hybrid.ensemble.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = expired_cached_model_selection

            # Mock Prophet for fallback
            with patch(
                "raglite.forecasting.hybrid.lazy_imports._get_prophet_class"
            ) as mock_prophet_class:
                mock_prophet = MagicMock()
                mock_prophet.fit.return_value = None
                mock_prophet.make_future_dataframe.return_value = MagicMock()
                mock_prophet.predict.return_value = MagicMock()
                mock_prophet_class.return_value = mock_prophet

                with patch("raglite.forecasting.hybrid.ensemble.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    with patch(
                        "raglite.forecasting.hybrid.preprocessing_data.fetch_historical_metric"
                    ) as mock_fetch:
                        mock_fetch.return_value = sample_time_series_data
                        result = await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            use_model_selection=True,
                        )

                    # Should fall back to default (Prophet) when cache expired
                    assert result.model_source == "default"
