"""Unit tests for Story 6.11 - MCP Multi-Variate Forecasting.

Story 6.11.1: MCP Multi-Variate Forecasting Interface
Story 6.11.2: Auto-Regressor Selection by Metric Type
Story 6.11.4: Fix INE Building Permits Indicator

Tests cover:
- Regressor configuration module
- Auto-selection by metric name
- Category-based keyword matching
- Request/Response model extensions
"""

from __future__ import annotations

import pytest


class TestRegressorConfig:
    """Tests for raglite.forecasting.regressor_config module."""

    def test_available_regressors_not_empty(self) -> None:
        """AC: Available regressors list should contain working APIs."""
        from raglite.forecasting.regressor_config import AVAILABLE_REGRESSORS

        assert len(AVAILABLE_REGRESSORS) >= 5
        assert "euribor_3m" in AVAILABLE_REGRESSORS
        assert "ttf_gas" in AVAILABLE_REGRESSORS
        assert "diesel" in AVAILABLE_REGRESSORS

    def test_metric_regressors_mapping_exists(self) -> None:
        """AC: Metric-to-regressor mapping should be defined."""
        from raglite.forecasting.regressor_config import METRIC_REGRESSORS

        assert len(METRIC_REGRESSORS) >= 10
        assert "revenue" in METRIC_REGRESSORS
        assert "ebitda" in METRIC_REGRESSORS
        assert "electricity_cost" in METRIC_REGRESSORS

    def test_get_default_regressors_revenue(self) -> None:
        """Story 6.11.2 AC2: Explicit mapping for revenue returns financial regressors."""
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("revenue")
        assert isinstance(regressors, list)
        assert len(regressors) >= 2
        assert "euribor_3m" in regressors

    def test_get_default_regressors_ebitda(self) -> None:
        """Story 6.11.2 AC2: Explicit mapping for ebitda returns appropriate regressors.

        Story 7b-7: Updated to reflect demand-side + cost-side regressor mix.
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("ebitda")
        assert isinstance(regressors, list)
        assert len(regressors) >= 3
        # Story 7b-7: Demand-side (construction) and cost-side (energy) regressors
        assert "construction_output" in regressors
        assert "building_permits" in regressors
        assert "construction_confidence" in regressors
        assert "housing_transactions" in regressors
        assert "ttf_gas" in regressors
        assert "diesel" in regressors

    def test_get_default_regressors_electricity_cost(self) -> None:
        """Story 6.11.2 AC2: Energy metrics should include electricity regressors."""
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("electricity_cost")
        assert (
            "ren_electricity" in regressors
        )  # Story 7.0: REN electricity replaces eurostat_electricity

    def test_get_default_regressors_unknown_metric(self) -> None:
        """Story 6.11.2 AC3: Unknown metrics should fallback to default regressors."""
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("completely_unknown_metric_xyz")
        assert isinstance(regressors, list)
        assert len(regressors) >= 3
        # Should return default economic indicators
        assert "euribor_3m" in regressors

    def test_get_default_regressors_case_insensitive(self) -> None:
        """Auto-selection should be case-insensitive."""
        from raglite.forecasting.regressor_config import get_default_regressors

        lower_result = get_default_regressors("revenue")
        upper_result = get_default_regressors("REVENUE")
        mixed_result = get_default_regressors("Revenue")

        assert lower_result == upper_result == mixed_result

    def test_get_default_regressors_category_matching_financial(self) -> None:
        """Story 6.11.2 AC1: Financial keywords should match financial category."""
        from raglite.forecasting.regressor_config import get_default_regressors

        # "profit" keyword should match financial category
        regressors = get_default_regressors("net_profit_margin")
        assert "euribor_3m" in regressors

    def test_get_default_regressors_category_matching_energy(self) -> None:
        """Story 6.11.2 AC1: Energy keywords should match energy category."""
        from raglite.forecasting.regressor_config import get_default_regressors

        # "power" keyword should match energy category
        regressors = get_default_regressors("power_consumption")
        assert any(
            r in regressors for r in ["ren_electricity", "ttf_gas", "api2_coal"]
        )  # Story 7.0: ren_electricity replaces eurostat_electricity

    def test_validate_regressor_names_valid(self) -> None:
        """Validation should accept valid regressor names."""
        from raglite.forecasting.regressor_config import validate_regressor_names

        valid, invalid = validate_regressor_names(["euribor_3m", "ttf_gas", "diesel"])
        assert len(valid) == 3
        assert len(invalid) == 0

    def test_validate_regressor_names_invalid(self) -> None:
        """Validation should reject invalid regressor names."""
        from raglite.forecasting.regressor_config import validate_regressor_names

        valid, invalid = validate_regressor_names(["euribor_3m", "fake_regressor"])
        assert "euribor_3m" in valid
        assert "fake_regressor" in invalid


class TestForecastQueryRequestExtensions:
    """Tests for ForecastQueryRequest model extensions (Story 6.11.1 AC1)."""

    def test_request_has_use_external_regressors_field(self) -> None:
        """AC1: Request should have use_external_regressors parameter."""
        from raglite.shared.models import ForecastQueryRequest

        request = ForecastQueryRequest(metric="revenue")
        assert hasattr(request, "use_external_regressors")
        # Default should be True (multi-variate by default)
        assert request.use_external_regressors is True

    def test_request_has_regressor_names_field(self) -> None:
        """AC1: Request should have regressor_names parameter."""
        from raglite.shared.models import ForecastQueryRequest

        request = ForecastQueryRequest(metric="revenue")
        assert hasattr(request, "regressor_names")
        # Default should be None (auto-select)
        assert request.regressor_names is None

    def test_request_has_future_regressor_strategy_field(self) -> None:
        """AC1: Request should have future_regressor_strategy parameter."""
        from raglite.shared.models import ForecastQueryRequest

        request = ForecastQueryRequest(metric="revenue")
        assert hasattr(request, "future_regressor_strategy")
        # Default should be "constant"
        assert request.future_regressor_strategy == "constant"

    def test_request_with_custom_regressors(self) -> None:
        """AC4: User can override with explicit regressor_names."""
        from raglite.shared.models import ForecastQueryRequest

        request = ForecastQueryRequest(
            metric="revenue",
            regressor_names=["euribor_3m", "diesel"],
        )
        assert request.regressor_names == ["euribor_3m", "diesel"]

    def test_request_disable_external_regressors(self) -> None:
        """User can disable external regressors for univariate forecast."""
        from raglite.shared.models import ForecastQueryRequest

        request = ForecastQueryRequest(
            metric="revenue",
            use_external_regressors=False,
        )
        assert request.use_external_regressors is False


class TestForecastQueryResponseExtensions:
    """Tests for ForecastQueryResponse model extensions (Story 6.11.1 AC4)."""

    def test_response_has_regressors_used_field(self) -> None:
        """AC4: Response should have regressors_used field."""
        from raglite.shared.models import ForecastQueryResponse

        # Check field exists in model
        assert "regressors_used" in ForecastQueryResponse.model_fields

    def test_response_has_model_type_field(self) -> None:
        """AC4: Response should have model_type field."""
        from raglite.shared.models import ForecastQueryResponse

        # Check field exists in model
        assert "model_type" in ForecastQueryResponse.model_fields

    def test_from_forecast_result_with_regressors(self) -> None:
        """Factory method should accept regressors_used parameter."""
        from raglite.shared.models import ForecastQueryResponse, ForecastResult

        # Create a minimal ForecastResult
        result = ForecastResult(
            metric_name="revenue",
            forecast=[],
            basis="Test basis",
            confidence_reasoning="Test reasoning",
            accuracy_estimate="±5%",
            periods_ahead=4,
        )

        response = ForecastQueryResponse.from_forecast_result(
            result=result,
            source_documents=["doc1.pdf"],
            regressors_used=["euribor_3m", "diesel"],
            model_type="prophet_multivariate",
        )

        assert response.regressors_used == ["euribor_3m", "diesel"]
        assert response.model_type == "prophet_multivariate"


class TestINEIndicatorFixes:
    """Tests for INE indicator fixes (Story 6.11.4)."""

    def test_ine_hpi_indicator_corrected(self) -> None:
        """AC1: INE HPI indicator should be 0009201, not 0010017."""
        from raglite.external_data.clients.ine import INEClient

        # 0010017 was returning death statistics instead of HPI
        assert INEClient.HOUSE_PRICE_INDEX_INDICATOR == "0009201"

    def test_ine_building_permits_indicator(self) -> None:
        """Building permits should use correct indicator 0012096."""
        from raglite.external_data.clients.ine import INEClient

        assert INEClient.BUILDING_PERMITS_INDICATOR == "0012096"


class TestRegressorFetch:
    """Tests for regressor fetch module (mocked)."""

    @pytest.mark.asyncio
    async def test_fetch_single_regressor_returns_none_for_unknown(self) -> None:
        """Unknown regressor should return None, not raise."""
        from datetime import date

        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            reg_name="completely_unknown_regressor",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 1, 1),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_regressors_for_metric_empty_on_failure(self) -> None:
        """Fetch should return empty dict on total failure, not raise."""
        from datetime import date

        from raglite.forecasting.regressor_fetch import fetch_regressors_for_metric

        # Using fake regressors that will all fail
        result = await fetch_regressors_for_metric(
            metric="test_metric",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 1, 1),
            regressor_names=["fake1", "fake2"],
        )
        # Should return empty dict, allowing graceful fallback
        assert isinstance(result, dict)
        assert len(result) == 0
