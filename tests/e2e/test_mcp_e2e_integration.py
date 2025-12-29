"""E2E tests for MCP Model Selection Integration - Core Integration Tests.

Story 7b-6: MCP Integration with Model Selection

TDD Phase: RED - These tests are expected to FAIL until implementation complete.

Test IDs map to Acceptance Criteria:
- TEST-AC-7b.6.7.x: E2E integration tests

These tests verify the full integration between:
1. generate_forecast()
2. Model selection cache (PostgreSQL)
3. Model routing
4. MCP response schema

Prerequisites:
- PostgreSQL running on test port (5433)
- Model selection cache populated with test data
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

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
        "revenue": CachedModelSelection(
            variable_name="revenue",
            best_model="xgboost",
            best_mape=5.5,
            best_mase=0.65,
            use_regressors=True,
            regressor_list=["diesel_price", "construction_confidence"],
            candidate_results={},
            data_characteristics={"model_rationale": "XGBoost selected for revenue"},
            selected_at=now,
            expires_at=now + timedelta(days=7),
        ),
        "variable_cost": CachedModelSelection(
            variable_name="variable_cost",
            best_model="prophet",
            best_mape=3.5,
            best_mase=0.55,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics={"model_rationale": "Prophet selected: sparse data pattern"},
            selected_at=now,
            expires_at=now + timedelta(days=7),
        ),
    }


@pytest.fixture
def sample_regressors():
    """Create sample regressor data for testing."""
    import pandas as pd

    dates = pd.date_range(start="2022-01-01", periods=36, freq="MS")

    return {
        "ttf_gas": pd.Series([30 + i * 0.5 for i in range(36)], index=dates),
        "euribor": pd.Series([2.5 + i * 0.03 for i in range(36)], index=dates),
        "diesel_price": pd.Series([1.5 + i * 0.02 for i in range(36)], index=dates),
        "construction_confidence": pd.Series([100 + i * 0.3 for i in range(36)], index=dates),
    }


# -----------------------------------------------------------------------------
# TEST-AC-7b.6.7: E2E Integration Tests
# -----------------------------------------------------------------------------


class TestMCPModelSelectionE2E:
    """[P0] AC-7b.6.7: E2E tests for MCP model selection integration."""

    @pytest.mark.asyncio
    async def test_ac_7b_6_7_1_cache_hit_arima_model(
        self,
        e2e_time_series_data,
        populated_cache,
        sample_regressors,
    ) -> None:
        """TEST-AC-7b.6.7.1: E2E test - cache hit with ARIMA model."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch(
            "raglite.external_data.storage.model_selection.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = populated_cache["ebitda"]

            with patch(
                "raglite.forecasting.hybrid.model_generators._generate_arima_forecast"
            ) as mock_arima:
                # Create realistic ForecastResult mock
                from raglite.shared.models import ForecastPoint, ForecastResult

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
                    model_type="arima_1_1_1",
                )
                mock_arima.return_value = mock_result

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    with patch(
                        "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric"
                    ) as mock_fetch:
                        mock_fetch.return_value = e2e_time_series_data

                        result = await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            external_regressors=sample_regressors,
                            use_model_selection=True,
                        )

                    # Verify cache was used
                    assert result.model_source == "cached"
                    assert "arima" in result.model_type.lower()
                    assert result.model_selection_reason is not None
                    assert (
                        "ARIMA" in result.model_selection_reason
                        or "arima" in result.model_selection_reason.lower()
                    )

    @pytest.mark.asyncio
    async def test_ac_7b_6_7_2_cache_hit_prophet_model(
        self,
        e2e_time_series_data,
        populated_cache,
    ) -> None:
        """TEST-AC-7b.6.7.2: E2E test - cache hit with Prophet model."""
        from raglite.forecasting.hybrid import generate_forecast

        # Modify time series for variable_cost
        e2e_time_series_data.metric_name = "variable_cost"

        with patch(
            "raglite.external_data.storage.model_selection.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = populated_cache["variable_cost"]

            with patch(
                "raglite.forecasting.hybrid.model_generators._generate_prophet_forecast"
            ) as mock_prophet:
                from raglite.shared.models import ForecastPoint, ForecastResult

                mock_result = ForecastResult(
                    metric_name="variable_cost",
                    forecast=[
                        ForecastPoint(
                            date=datetime(2025, 1, 1),
                            value=85.5,
                            lower=80.0,
                            upper=91.0,
                            label="Jan 2025",
                        ),
                    ],
                    model_type="prophet_univariate",
                )
                mock_prophet.return_value = mock_result

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    with patch(
                        "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric"
                    ) as mock_fetch:
                        mock_fetch.return_value = e2e_time_series_data

                        result = await generate_forecast(
                            metric="variable_cost",
                            periods_ahead=4,
                            use_model_selection=True,
                        )

                    assert result.model_source == "cached"
                    assert "prophet" in result.model_type.lower()

    @pytest.mark.asyncio
    async def test_ac_7b_6_7_3_cache_hit_xgboost_with_regressors(
        self,
        e2e_time_series_data,
        populated_cache,
        sample_regressors,
    ) -> None:
        """TEST-AC-7b.6.7.3: E2E test - cache hit with XGBoost + regressors."""
        from raglite.forecasting.hybrid import generate_forecast

        e2e_time_series_data.metric_name = "revenue"

        with patch(
            "raglite.external_data.storage.model_selection.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = populated_cache["revenue"]

            with patch(
                "raglite.forecasting.hybrid.model_generators._generate_xgboost_forecast"
            ) as mock_xgboost:
                from raglite.shared.models import ForecastPoint, ForecastResult

                mock_result = ForecastResult(
                    metric_name="revenue",
                    forecast=[
                        ForecastPoint(
                            date=datetime(2025, 1, 1),
                            value=50000000,
                            lower=47000000,
                            upper=53000000,
                            label="Jan 2025",
                        ),
                    ],
                    model_type="xgboost",
                    regressors_used=["diesel_price", "construction_confidence"],
                )
                mock_xgboost.return_value = mock_result

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    with patch(
                        "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric"
                    ) as mock_fetch:
                        mock_fetch.return_value = e2e_time_series_data

                        result = await generate_forecast(
                            metric="revenue",
                            periods_ahead=4,
                            external_regressors=sample_regressors,
                            use_model_selection=True,
                        )

                    assert result.model_source == "cached"
                    assert result.regressors_used is not None
                    # Should only use cached regressor set (diesel_price, construction_confidence)
                    for reg in result.regressors_used:
                        assert reg in ["diesel_price", "construction_confidence"]

    @pytest.mark.asyncio
    async def test_ac_7b_6_7_4_cache_miss_fallback_prophet(
        self,
        e2e_time_series_data,
    ) -> None:
        """TEST-AC-7b.6.7.4: E2E test - cache miss falls back to Prophet."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch(
            "raglite.external_data.storage.model_selection.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = None  # Cache miss

            with patch(
                "raglite.forecasting.hybrid.lazy_imports._get_prophet_class"
            ) as mock_prophet_class:
                import pandas as pd

                mock_prophet = MagicMock()
                mock_prophet.fit.return_value = None

                # Create realistic future DataFrame
                future_df = pd.DataFrame(
                    {"ds": pd.date_range(start="2022-01-01", periods=40, freq="MS")}
                )
                mock_prophet.make_future_dataframe.return_value = future_df

                # Create realistic prediction DataFrame
                predict_df = pd.DataFrame(
                    {
                        "ds": future_df["ds"],
                        "yhat": [15000000 + i * 100000 for i in range(40)],
                        "yhat_lower": [14000000 + i * 100000 for i in range(40)],
                        "yhat_upper": [16000000 + i * 100000 for i in range(40)],
                    }
                )
                mock_prophet.predict.return_value = predict_df

                mock_prophet_class.return_value = mock_prophet

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Forecast based on Prophet model"

                    with patch(
                        "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric"
                    ) as mock_fetch:
                        mock_fetch.return_value = e2e_time_series_data

                        result = await generate_forecast(
                            metric="unknown_metric",
                            periods_ahead=4,
                            use_model_selection=True,
                        )

                    # Should use default Prophet and mark as "default"
                    assert result.model_source == "default"
                    assert "prophet" in result.model_type.lower()

    @pytest.mark.asyncio
    async def test_ac_7b_6_7_5_model_failure_fallback_prophet(
        self,
        e2e_time_series_data,
        populated_cache,
    ) -> None:
        """TEST-AC-7b.6.7.5: E2E test - model failure falls back to Prophet."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch(
            "raglite.external_data.storage.model_selection.get_cached_model_selection"
        ) as mock_get_cache:
            mock_get_cache.return_value = populated_cache["ebitda"]

            with patch("raglite.forecasting.hybrid.model_generators._route_to_model") as mock_route:
                mock_route.side_effect = Exception("ARIMA convergence failed")

                with patch(
                    "raglite.forecasting.hybrid.model_generators._generate_prophet_forecast"
                ) as mock_prophet_fallback:
                    from raglite.shared.models import ForecastPoint, ForecastResult

                    fallback_result = ForecastResult(
                        metric_name="ebitda",
                        forecast=[
                            ForecastPoint(
                                date=datetime(2025, 1, 1),
                                value=15500000,
                                lower=14000000,
                                upper=17000000,
                                label="Jan 2025",
                            ),
                        ],
                        model_type="prophet_univariate",
                    )
                    mock_prophet_fallback.return_value = fallback_result

                    with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                        mock_explain.return_value = "Fallback forecast"

                        with patch(
                            "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric"
                        ) as mock_fetch:
                            mock_fetch.return_value = e2e_time_series_data

                            result = await generate_forecast(
                                metric="ebitda",
                                periods_ahead=4,
                                use_model_selection=True,
                            )

                        # Should fall back to Prophet
                        assert result.model_source == "fallback"
                        assert "prophet" in result.model_type.lower()

    @pytest.mark.asyncio
    async def test_ac_7b_6_7_6_response_includes_all_metadata(
        self,
        e2e_time_series_data,
        populated_cache,
    ) -> None:
        """TEST-AC-7b.6.7.6: E2E test - response includes model_source and model_selection_reason."""
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

                    with patch(
                        "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric"
                    ) as mock_fetch:
                        mock_fetch.return_value = e2e_time_series_data

                        result = await generate_forecast(
                            metric="ebitda",
                            periods_ahead=4,
                            use_model_selection=True,
                        )

                    # Verify all expected fields are present
                    assert hasattr(result, "model_source")
                    assert hasattr(result, "model_selection_reason")
                    assert result.model_source in ["cached", "default", "fallback"]
                    # For cached selection, reason should be populated
                    if result.model_source == "cached":
                        assert result.model_selection_reason is not None
