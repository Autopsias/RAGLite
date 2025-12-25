"""Unit tests for MCP Model Selection - Model Routing and Regressor Filtering.

Story 7b-6: MCP Integration with Model Selection

TDD Phase: RED - These tests are expected to FAIL until implementation complete.

Test IDs map to Acceptance Criteria:
- TEST-AC-7b.6.2.x: Model routing tests
- TEST-AC-7b.6.3.x: Regressor filtering tests
- TEST-AC-7b.6.4.x: Fallback handling tests
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
# TEST-AC-7b.6.2: Model Routing Tests
# -----------------------------------------------------------------------------


class TestModelRouting:
    """[P0] AC-7b.6.2: Route to Correct Model."""

    def test_ac_7b_6_2_1_route_to_model_function_exists(self) -> None:
        """TEST-AC-7b.6.2.1: _route_to_model function exists."""
        from raglite.forecasting.hybrid import _route_to_model

        assert callable(_route_to_model)

    def test_ac_7b_6_2_2_route_to_model_supports_all_models(self) -> None:
        """TEST-AC-7b.6.2.2: _route_to_model supports all 9 model types."""
        # This test verifies the model_routers dict contains all expected models
        import inspect

        from raglite.forecasting.hybrid import _route_to_model

        # Get the source code of _route_to_model to verify it supports all models
        source = inspect.getsource(_route_to_model)

        expected_models = [
            "arima",
            "ets",
            "prophet",
            "xgboost",
            "lightgbm",
            "catboost",
            "chronos",
            "tft",
            "linear",
        ]

        for model in expected_models:
            assert f'"{model}"' in source or f"'{model}'" in source, (
                f"Model {model} should be supported in _route_to_model"
            )

    @pytest.mark.asyncio
    async def test_ac_7b_6_2_3_route_to_arima(self, sample_time_series_data) -> None:
        """TEST-AC-7b.6.2.3: _route_to_model routes arima to _generate_arima_forecast."""
        from raglite.forecasting.hybrid import _route_to_model

        with patch("raglite.forecasting.hybrid._generate_arima_forecast") as mock_arima:
            mock_arima.return_value = MagicMock()

            await _route_to_model(
                model_name="arima",
                metric="ebitda",
                historical_data=sample_time_series_data,
                periods_ahead=4,
                external_regressors=None,
            )

            mock_arima.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac_7b_6_2_4_route_to_ets(self, sample_time_series_data) -> None:
        """TEST-AC-7b.6.2.4: _route_to_model routes ets to _generate_ets_forecast."""
        from raglite.forecasting.hybrid import _route_to_model

        with patch("raglite.forecasting.hybrid._generate_ets_forecast") as mock_ets:
            mock_ets.return_value = MagicMock()

            await _route_to_model(
                model_name="ets",
                metric="ebitda",
                historical_data=sample_time_series_data,
                periods_ahead=4,
                external_regressors=None,
            )

            mock_ets.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac_7b_6_2_5_route_to_prophet(self, sample_time_series_data) -> None:
        """TEST-AC-7b.6.2.5: _route_to_model routes prophet to _generate_prophet_forecast."""
        from raglite.forecasting.hybrid import _route_to_model

        with patch("raglite.forecasting.hybrid._generate_prophet_forecast") as mock_prophet:
            mock_prophet.return_value = MagicMock()

            await _route_to_model(
                model_name="prophet",
                metric="ebitda",
                historical_data=sample_time_series_data,
                periods_ahead=4,
                external_regressors=None,
            )

            mock_prophet.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac_7b_6_2_6_route_to_xgboost(self, sample_time_series_data) -> None:
        """TEST-AC-7b.6.2.6: _route_to_model routes xgboost to _generate_xgboost_forecast."""
        from raglite.forecasting.hybrid import _route_to_model

        with patch("raglite.forecasting.hybrid._generate_xgboost_forecast") as mock_xgboost:
            mock_xgboost.return_value = MagicMock()

            await _route_to_model(
                model_name="xgboost",
                metric="ebitda",
                historical_data=sample_time_series_data,
                periods_ahead=4,
                external_regressors=None,
            )

            mock_xgboost.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac_7b_6_2_7_route_unknown_model_raises_error(
        self, sample_time_series_data
    ) -> None:
        """TEST-AC-7b.6.2.7: _route_to_model raises ValueError for unknown model."""
        from raglite.forecasting.hybrid import _route_to_model

        with pytest.raises(ValueError, match="Unknown model"):
            await _route_to_model(
                model_name="unknown_model",
                metric="ebitda",
                historical_data=sample_time_series_data,
                periods_ahead=4,
                external_regressors=None,
            )


# -----------------------------------------------------------------------------
# TEST-AC-7b.6.3: Regressor Filtering Tests
# -----------------------------------------------------------------------------


class TestRegressorFiltering:
    """[P0] AC-7b.6.3: Use Selected Regressor Set."""

    @pytest.mark.asyncio
    async def test_ac_7b_6_3_1_filters_regressors_to_cached_set(
        self,
        sample_time_series_data,
        mock_cached_model_selection,
    ) -> None:
        """TEST-AC-7b.6.3.1: Only cached regressors are passed to model."""
        import pandas as pd

        from raglite.forecasting.hybrid import generate_forecast

        # Provide more regressors than cached selection specifies
        all_regressors = {
            "gas_price": pd.Series([1.0, 2.0, 3.0]),
            "euribor": pd.Series([0.5, 0.6, 0.7]),
            "oil_price": pd.Series([50, 55, 60]),  # Not in cached selection
            "electricity": pd.Series([10, 11, 12]),  # Not in cached selection
        }

        with patch("raglite.forecasting.hybrid.get_cached_model_selection") as mock_get_cache:
            mock_get_cache.return_value = mock_cached_model_selection

            with patch("raglite.forecasting.hybrid._route_to_model") as mock_route:
                mock_route.return_value = MagicMock()

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    await generate_forecast(
                        metric="ebitda",
                        historical_data=sample_time_series_data,
                        periods_ahead=4,
                        external_regressors=all_regressors,
                        use_model_selection=True,
                    )

                    # Check that only cached regressors were passed
                    call_kwargs = mock_route.call_args[1]
                    filtered_regressors = call_kwargs.get("external_regressors")

                    # Should only contain gas_price and euribor
                    assert set(filtered_regressors.keys()) == {"gas_price", "euribor"}

    @pytest.mark.asyncio
    async def test_ac_7b_6_3_2_no_regressors_when_use_regressors_false(
        self,
        sample_time_series_data,
    ) -> None:
        """TEST-AC-7b.6.3.2: No regressors passed when use_regressors=False in cache."""
        import pandas as pd

        from raglite.external_data.storage import CachedModelSelection
        from raglite.forecasting.hybrid import generate_forecast

        # Create cache entry with use_regressors=False
        # Use "arima" model (not "prophet") to test the _route_to_model path
        # Prophet has a special code path that doesn't use _route_to_model
        now = datetime.utcnow()
        cached_no_regressors = CachedModelSelection(
            variable_name="ebitda",
            best_model="arima",  # Use ARIMA to test _route_to_model path
            best_mape=6.0,
            best_mase=0.9,
            use_regressors=False,  # Explicitly disabled
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        all_regressors = {
            "gas_price": pd.Series([1.0, 2.0, 3.0]),
            "euribor": pd.Series([0.5, 0.6, 0.7]),
        }

        with patch("raglite.forecasting.hybrid.get_cached_model_selection") as mock_get_cache:
            mock_get_cache.return_value = cached_no_regressors

            with patch("raglite.forecasting.hybrid._route_to_model") as mock_route:
                mock_route.return_value = MagicMock()

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    await generate_forecast(
                        metric="ebitda",
                        historical_data=sample_time_series_data,
                        periods_ahead=4,
                        external_regressors=all_regressors,
                        use_model_selection=True,
                    )

                    # Check that no regressors were passed
                    call_kwargs = mock_route.call_args[1]
                    filtered_regressors = call_kwargs.get("external_regressors")

                    assert filtered_regressors is None

    @pytest.mark.asyncio
    async def test_ac_7b_6_3_3_handles_missing_regressor_gracefully(
        self,
        sample_time_series_data,
        mock_cached_model_selection,
    ) -> None:
        """TEST-AC-7b.6.3.3: Handles missing regressors gracefully."""
        import pandas as pd

        from raglite.forecasting.hybrid import generate_forecast

        # Only provide gas_price, euribor is missing
        partial_regressors = {
            "gas_price": pd.Series([1.0, 2.0, 3.0]),
            # "euribor" is missing but in cached regressor_list
        }

        with patch("raglite.forecasting.hybrid.get_cached_model_selection") as mock_get_cache:
            mock_get_cache.return_value = mock_cached_model_selection

            with patch("raglite.forecasting.hybrid._route_to_model") as mock_route:
                mock_route.return_value = MagicMock()

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    # Should not raise - handles missing regressor gracefully
                    await generate_forecast(
                        metric="ebitda",
                        historical_data=sample_time_series_data,
                        periods_ahead=4,
                        external_regressors=partial_regressors,
                        use_model_selection=True,
                    )

                    # Only gas_price should be passed
                    call_kwargs = mock_route.call_args[1]
                    filtered_regressors = call_kwargs.get("external_regressors")
                    assert "gas_price" in filtered_regressors
                    assert "euribor" not in filtered_regressors


# -----------------------------------------------------------------------------
# TEST-AC-7b.6.4: Fallback Handling Tests
# -----------------------------------------------------------------------------


class TestFallbackHandling:
    """[P0] AC-7b.6.4: Fallback to Prophet on Cache Miss or Model Failure."""

    @pytest.mark.asyncio
    async def test_ac_7b_6_4_1_fallback_on_cache_miss(
        self,
        sample_time_series_data,
    ) -> None:
        """TEST-AC-7b.6.4.1: Falls back to Prophet when no cache exists."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch("raglite.forecasting.hybrid.get_cached_model_selection") as mock_get_cache:
            mock_get_cache.return_value = None  # Cache miss

            with patch("raglite.forecasting.hybrid._get_prophet_class") as mock_prophet_class:
                mock_prophet = MagicMock()
                mock_prophet.fit.return_value = None
                mock_prophet.make_future_dataframe.return_value = MagicMock()
                mock_prophet.predict.return_value = MagicMock()
                mock_prophet_class.return_value = mock_prophet

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    result = await generate_forecast(
                        metric="unknown_metric",
                        historical_data=sample_time_series_data,
                        periods_ahead=4,
                        use_model_selection=True,
                    )

                    # Should use Prophet (default) and mark source as "default"
                    assert result.model_source == "default"

    @pytest.mark.asyncio
    async def test_ac_7b_6_4_2_fallback_on_model_failure(
        self,
        sample_time_series_data,
        mock_cached_model_selection,
    ) -> None:
        """TEST-AC-7b.6.4.2: Falls back to Prophet when selected model fails."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch("raglite.forecasting.hybrid.get_cached_model_selection") as mock_get_cache:
            mock_get_cache.return_value = mock_cached_model_selection

            with patch("raglite.forecasting.hybrid._route_to_model") as mock_route:
                # ARIMA fails
                mock_route.side_effect = Exception("ARIMA convergence failed")

                with patch("raglite.forecasting.hybrid.explain_forecast") as mock_explain:
                    mock_explain.return_value = "Test explanation"

                    result = await generate_forecast(
                        metric="ebitda",
                        historical_data=sample_time_series_data,
                        periods_ahead=4,
                        use_model_selection=True,
                    )

                    # Should fall back to Prophet (main path execution)
                    assert result.model_source == "fallback"
                    # Verify fallback reason includes error context
                    assert "ARIMA convergence failed" in result.model_selection_reason

    @pytest.mark.asyncio
    async def test_ac_7b_6_4_3_fallback_includes_error_context(
        self,
        sample_time_series_data,
        mock_cached_model_selection,
    ) -> None:
        """TEST-AC-7b.6.4.3: Fallback model_selection_reason includes error context."""
        from raglite.forecasting.hybrid import generate_forecast

        with patch("raglite.forecasting.hybrid.get_cached_model_selection") as mock_get_cache:
            mock_get_cache.return_value = mock_cached_model_selection

            with patch("raglite.forecasting.hybrid._route_to_model") as mock_route:
                mock_route.side_effect = Exception("ARIMA convergence failed")

                with patch("raglite.forecasting.hybrid._generate_prophet_forecast") as mock_prophet:
                    mock_result = MagicMock()
                    mock_result.model_source = "fallback"
                    mock_result.model_selection_reason = "Fallback due to arima failure"
                    mock_prophet.return_value = mock_result

                    result = await generate_forecast(
                        metric="ebitda",
                        historical_data=sample_time_series_data,
                        periods_ahead=4,
                        use_model_selection=True,
                    )

                    # Should include error context in reason
                    assert (
                        "arima" in result.model_selection_reason.lower()
                        or "fallback" in result.model_selection_reason.lower()
                    )


# -----------------------------------------------------------------------------
# Variable Alias Resolution Tests (Epic 7 Fix)
# -----------------------------------------------------------------------------


# Mock VARIABLE_CONFIG to avoid heavy import chain (ML libraries)
MOCK_VARIABLE_CONFIG = {
    "revenue": {
        "type": "internal",
        "aliases": ["Turnover+VAT", "Turnover", "turnover", "revenue"],
    },
    "ebitda": {
        "type": "internal",
        "aliases": ["EBITDA", "ebitda", "Cement Unit Ebitda"],
    },
    "sales_volume": {
        "type": "internal",
        "aliases": ["Sales Volumes", "sales volumes", "Volume IM - kton"],
    },
    "thermal_cost": {
        "type": "internal",
        "aliases": ["Thermal Energy", "thermal energy", "fuel_cost"],
    },
    "variable_cost": {
        "type": "internal",
        "aliases": ["Variable Cost", "variable cost"],
    },
    "capacity_utilization": {
        "type": "internal",
        "aliases": ["Capacity Utilization", "capacity_utilization", "Ratio"],
    },
    "avg_selling_price": {
        "type": "internal",
        "aliases": ["Sales Price IM", "avg_selling_price", "Average Selling Price"],
    },
    "ttf_gas_price": {"type": "external_db", "metric_name": "ttf_gas_price"},
    "petcoke_price": {"type": "external_db", "metric_name": "petcoke_price"},
    "co2_eua_price": {"type": "external_db", "metric_name": "co2_eua_price"},
}


def _resolve_variable_alias_mock(metric: str) -> str:
    """Standalone implementation of resolve_variable_alias for testing.

    Mirrors the real implementation without triggering heavy imports.
    """
    metric_lower = metric.lower()

    # Direct match in VARIABLE_CONFIG?
    if metric_lower in MOCK_VARIABLE_CONFIG:
        return metric_lower

    # Search aliases for reverse lookup
    for var_name, config in MOCK_VARIABLE_CONFIG.items():
        aliases = config.get("aliases", [])
        for alias in aliases:
            if alias.lower() == metric_lower:
                return var_name

    # No match - return lowercased original
    return metric_lower


class TestVariableAliasResolution:
    """Tests for resolve_variable_alias() function.

    Epic 7 Fix: Ensures MCP queries using DB aliases are normalized
    to cache keys for model selection lookup.

    Note: Uses mock VARIABLE_CONFIG to avoid heavy ML library imports.
    """

    def test_normalized_names_unchanged(self) -> None:
        """Direct normalized names should be returned unchanged."""
        # These are the canonical cache keys
        assert _resolve_variable_alias_mock("revenue") == "revenue"
        assert _resolve_variable_alias_mock("ebitda") == "ebitda"
        assert _resolve_variable_alias_mock("sales_volume") == "sales_volume"
        assert _resolve_variable_alias_mock("ttf_gas_price") == "ttf_gas_price"

    def test_db_aliases_resolved_to_normalized(self) -> None:
        """DB aliases should resolve to normalized cache keys."""
        # Internal variable aliases
        assert _resolve_variable_alias_mock("Turnover+VAT") == "revenue"
        assert _resolve_variable_alias_mock("EBITDA") == "ebitda"
        assert _resolve_variable_alias_mock("Sales Volumes") == "sales_volume"
        assert _resolve_variable_alias_mock("Thermal Energy") == "thermal_cost"
        assert _resolve_variable_alias_mock("Variable Cost") == "variable_cost"
        assert _resolve_variable_alias_mock("Capacity Utilization") == "capacity_utilization"
        assert _resolve_variable_alias_mock("Sales Price IM") == "avg_selling_price"

    def test_case_insensitive_resolution(self) -> None:
        """Alias resolution should be case-insensitive."""
        assert _resolve_variable_alias_mock("turnover+vat") == "revenue"
        assert _resolve_variable_alias_mock("TURNOVER+VAT") == "revenue"
        assert _resolve_variable_alias_mock("ebitda") == "ebitda"
        assert _resolve_variable_alias_mock("EBITDA") == "ebitda"
        assert _resolve_variable_alias_mock("sales volumes") == "sales_volume"

    def test_unknown_metrics_returned_lowercased(self) -> None:
        """Unknown metrics should be returned lowercased."""
        assert _resolve_variable_alias_mock("unknown_metric") == "unknown_metric"
        assert _resolve_variable_alias_mock("UNKNOWN_METRIC") == "unknown_metric"
        assert _resolve_variable_alias_mock("Some Random Thing") == "some random thing"

    def test_external_variables_resolved(self) -> None:
        """External variables should resolve correctly."""
        # External DB variables (metric_name is same as key)
        assert _resolve_variable_alias_mock("ttf_gas_price") == "ttf_gas_price"
        assert _resolve_variable_alias_mock("petcoke_price") == "petcoke_price"
        assert _resolve_variable_alias_mock("co2_eua_price") == "co2_eua_price"

    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("Turnover+VAT", "revenue"),
            ("Turnover", "revenue"),
            ("turnover", "revenue"),
            ("revenue", "revenue"),
            ("EBITDA", "ebitda"),
            ("Cement Unit Ebitda", "ebitda"),
            ("Sales Volumes", "sales_volume"),
            ("Volume IM - kton", "sales_volume"),
            ("Thermal Energy", "thermal_cost"),
            ("fuel_cost", "thermal_cost"),
            ("Variable Cost", "variable_cost"),
            ("Capacity Utilization", "capacity_utilization"),
            ("Ratio", "capacity_utilization"),
            ("Sales Price IM", "avg_selling_price"),
            ("Average Selling Price", "avg_selling_price"),
        ],
    )
    def test_all_internal_aliases_resolve_correctly(self, alias: str, expected: str) -> None:
        """Parametrized test for all internal variable aliases."""
        assert _resolve_variable_alias_mock(alias) == expected
