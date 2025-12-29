"""Expanded test coverage for MCP Model Selection - Edge Cases and Observability.

Story 7b-6: MCP Integration with Model Selection - EXPANDED COVERAGE

Test Categories:
- [P1] Model routing edge cases
- [P2] Metadata population
- [P2] Concurrent request scenarios
- [P3] Logging and observability
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


# =============================================================================
# Fixtures
# =============================================================================


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


# =============================================================================
# [P1] Model Routing Edge Cases
# =============================================================================


class TestModelRoutingEdgeCases:
    """[P1] Model routing edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_route_to_model_with_invalid_model_name(self, sample_time_series_data) -> None:
        """[P0] Invalid model name should raise ValueError with clear message."""
        from raglite.forecasting.hybrid import _route_to_model

        with pytest.raises(ValueError, match="Unknown model: invalid_model"):
            await _route_to_model(
                model_name="invalid_model",
                metric="ebitda",
                historical_data=sample_time_series_data,
                periods_ahead=4,
                external_regressors=None,
            )

    @pytest.mark.asyncio
    async def test_route_to_model_with_empty_string(self, sample_time_series_data) -> None:
        """[P1] Empty string model name should raise ValueError."""
        from raglite.forecasting.hybrid import _route_to_model

        with pytest.raises(ValueError):
            await _route_to_model(
                model_name="",
                metric="ebitda",
                historical_data=sample_time_series_data,
                periods_ahead=4,
                external_regressors=None,
            )

    @pytest.mark.asyncio
    async def test_route_to_model_case_sensitivity(self, sample_time_series_data) -> None:
        """[P2] Model names should be case-sensitive (ARIMA != arima)."""
        from raglite.forecasting.hybrid import _route_to_model

        # Uppercase should fail
        with pytest.raises(ValueError, match="Unknown model: ARIMA"):
            await _route_to_model(
                model_name="ARIMA",  # Should be lowercase "arima"
                metric="ebitda",
                historical_data=sample_time_series_data,
                periods_ahead=4,
                external_regressors=None,
            )

    @pytest.mark.asyncio
    async def test_not_implemented_error_fallback(self, sample_time_series_data) -> None:
        """[P1] NotImplementedError in model should fall back to Prophet gracefully."""
        from raglite.external_data.storage import CachedModelSelection
        from raglite.forecasting.hybrid import generate_forecast

        now = datetime.utcnow()
        cached_unimplemented_model = CachedModelSelection(
            variable_name="ebitda",
            best_model="tft",  # Assume TFT not fully implemented
            best_mape=5.0,
            best_mase=0.7,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        with patch(
            "raglite.external_data.storage.model_selection.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = cached_unimplemented_model

            with patch(
                "raglite.forecasting.hybrid.model_generators._generate_tft_forecast"
            ) as mock_tft:
                # Simulate NotImplementedError
                mock_tft.side_effect = NotImplementedError("TFT not yet implemented")

                with patch(
                    "raglite.forecasting.hybrid.lazy_imports._get_prophet_class"
                ) as mock_prophet_class:
                    mock_prophet = MagicMock()
                    mock_prophet.fit.return_value = None
                    mock_prophet.make_future_dataframe.return_value = MagicMock()
                    mock_prophet.predict.return_value = MagicMock()
                    mock_prophet_class.return_value = mock_prophet

                    with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                        mock_explain.return_value = "Test explanation"

                        with patch(
                            "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric"
                        ) as mock_fetch:
                            mock_fetch.return_value = sample_time_series_data
                            result = await generate_forecast(
                                metric="ebitda",
                                periods_ahead=4,
                                use_model_selection=True,
                            )

                        # Should fall back to Prophet
                        assert result.model_source == "fallback"
                        assert "not yet implemented" in result.model_selection_reason


# =============================================================================
# [P2] Metadata Population Tests
# =============================================================================


class TestMetadataPopulation:
    """[P2] Verify metadata is correctly populated in all scenarios."""

    @pytest.mark.asyncio
    async def test_model_source_fallback_has_detailed_reason(self, sample_time_series_data) -> None:
        """[P1] Fallback should include detailed error information in reason."""
        from raglite.external_data.storage import CachedModelSelection
        from raglite.forecasting.hybrid import generate_forecast

        now = datetime.utcnow()
        cached = CachedModelSelection(
            variable_name="ebitda",
            best_model="arima",
            best_mape=5.0,
            best_mase=0.7,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        with patch(
            "raglite.external_data.storage.model_selection.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = cached

            with patch("raglite.forecasting.hybrid.model_generators._route_to_model") as mock_route:
                # Detailed error
                mock_route.side_effect = RuntimeError(
                    "ARIMA convergence failed: data is non-stationary"
                )

                with patch(
                    "raglite.forecasting.hybrid.model_generators._generate_prophet_forecast"
                ) as mock_prophet:
                    mock_result = MagicMock()
                    mock_result.model_source = "fallback"
                    mock_prophet.return_value = mock_result

                    with patch(
                        "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric"
                    ) as mock_fetch:
                        mock_fetch.return_value = sample_time_series_data
                        result = await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            use_model_selection=True,
                        )

                    # Reason should include the error details
                    assert "arima" in result.model_selection_reason.lower()
                    assert (
                        "convergence" in result.model_selection_reason
                        or "failure" in result.model_selection_reason
                    )

    @pytest.mark.asyncio
    async def test_cached_model_preserves_reason_from_data_characteristics(
        self, sample_time_series_data
    ) -> None:
        """[P1] Cached model selection reason comes from data_characteristics."""
        from raglite.external_data.storage import CachedModelSelection
        from raglite.forecasting.hybrid import generate_forecast

        now = datetime.utcnow()
        expected_rationale = (
            "ARIMA selected: data is difference-stationary (ADF p=0.02), "
            "low seasonality (strength=0.12). CV MAPE: 8.2% vs Prophet 84.7%"
        )
        cached = CachedModelSelection(
            variable_name="ebitda",
            best_model="arima",
            best_mape=8.2,
            best_mase=0.75,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics={"model_rationale": expected_rationale},
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        with patch(
            "raglite.external_data.storage.model_selection.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = cached

            with patch("raglite.forecasting.hybrid.model_generators._route_to_model") as mock_route:
                mock_result = MagicMock()
                mock_route.return_value = mock_result

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    with patch(
                        "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric"
                    ) as mock_fetch:
                        mock_fetch.return_value = sample_time_series_data
                        result = await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            use_model_selection=True,
                        )

                    # Should preserve exact rationale
                    assert result.model_selection_reason == expected_rationale


# =============================================================================
# [P2] Concurrent Request Scenarios
# =============================================================================


class TestConcurrentRequests:
    """[P2] Test behavior under concurrent forecast requests."""

    @pytest.mark.asyncio
    async def test_concurrent_forecasts_same_metric(self, sample_time_series_data) -> None:
        """[P2] Concurrent forecasts for same metric should not interfere."""
        import asyncio

        from raglite.external_data.storage import CachedModelSelection
        from raglite.forecasting.hybrid import generate_forecast
        from raglite.shared.models import ForecastPoint, ForecastResult

        now = datetime.utcnow()
        cached = CachedModelSelection(
            variable_name="ebitda",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.7,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        with patch(
            "raglite.external_data.storage.model_selection.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = cached

            with patch(
                "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric"
            ) as mock_fetch:
                mock_fetch.return_value = sample_time_series_data

                with patch(
                    "raglite.forecasting.hybrid.model_generators._generate_prophet_forecast"
                ) as mock_prophet:
                    mock_result = ForecastResult(
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
                        model_type="prophet_univariate",
                    )
                    mock_prophet.return_value = mock_result

                    with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                        mock_explain.return_value = "Test explanation"

                        # Launch 5 concurrent forecasts
                        tasks = [
                            generate_forecast(
                                metric="ebitda",
                                periods_ahead=4,
                                use_model_selection=True,
                            )
                            for _ in range(5)
                        ]

                    results = await asyncio.gather(*tasks)

                    # All should succeed
                    assert len(results) == 5
                    for result in results:
                        assert result.model_source == "cached"


# =============================================================================
# [P3] Logging and Observability
# =============================================================================


class TestLoggingAndObservability:
    """[P3] Verify logging for debugging and monitoring."""

    @pytest.mark.asyncio
    async def test_cache_hit_logs_model_details(self, sample_time_series_data, caplog) -> None:
        """[P2] Cache hit should log model selection details."""
        from raglite.external_data.storage import CachedModelSelection
        from raglite.forecasting.hybrid import generate_forecast

        now = datetime.utcnow()
        cached = CachedModelSelection(
            variable_name="ebitda",
            best_model="arima",
            best_mape=5.0,
            best_mase=0.7,
            use_regressors=True,
            regressor_list=["gas_price", "euribor"],
            candidate_results={},
            data_characteristics=None,
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        with patch(
            "raglite.external_data.storage.model_selection.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = cached

            with patch("raglite.forecasting.hybrid.model_generators._route_to_model") as mock_route:
                mock_route.return_value = MagicMock()

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    import logging

                    with caplog.at_level(logging.INFO):
                        with patch(
                            "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric"
                        ) as mock_fetch:
                            mock_fetch.return_value = sample_time_series_data
                            await generate_forecast(
                                metric="ebitda",
                                periods_ahead=4,
                                use_model_selection=True,
                            )

                    # Verify logging occurred (implementation should log cache hit)
                    assert len(caplog.records) > 0

    @pytest.mark.asyncio
    async def test_fallback_logs_warning_with_error(self, sample_time_series_data, caplog) -> None:
        """[P2] Model failure fallback should log warning with error details."""
        from raglite.external_data.storage import CachedModelSelection
        from raglite.forecasting.hybrid import generate_forecast

        now = datetime.utcnow()
        cached = CachedModelSelection(
            variable_name="ebitda",
            best_model="arima",
            best_mape=5.0,
            best_mase=0.7,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        with patch(
            "raglite.external_data.storage.model_selection.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = cached

            with patch("raglite.forecasting.hybrid.model_generators._route_to_model") as mock_route:
                mock_route.side_effect = Exception("ARIMA convergence failed")

                with patch(
                    "raglite.forecasting.hybrid.model_generators._generate_prophet_forecast"
                ) as mock_prophet:
                    mock_result = MagicMock()
                    mock_result.model_source = "fallback"
                    mock_prophet.return_value = mock_result

                    import logging

                    with caplog.at_level(logging.WARNING):
                        with patch(
                            "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric"
                        ) as mock_fetch:
                            mock_fetch.return_value = sample_time_series_data
                            await generate_forecast(
                                metric="ebitda",
                                periods_ahead=4,
                                use_model_selection=True,
                            )

                    # Should have warning log
                    assert any(
                        "falling back" in record.message.lower()
                        or "fallback" in record.message.lower()
                        for record in caplog.records
                    )
