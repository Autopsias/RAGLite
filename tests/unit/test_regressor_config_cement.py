"""Unit tests for cement industry regressor configuration.

Story 6.20: Update Regressor Configuration for Cement Industry
- AC1: All new regressors registered in AVAILABLE_REGRESSORS
- AC2: METRIC_REGRESSORS updated with optimal mappings per variable
"""

from __future__ import annotations

# Lazy import pattern: defer heavy module import until test execution
# This avoids slow imports during test collection for VS Code Test Explorer
_regressor_config = None


def _get_regressor_config():
    """Lazy load regressor_config module."""
    global _regressor_config
    if _regressor_config is None:
        from raglite.forecasting import regressor_config

        _regressor_config = regressor_config
    return _regressor_config


class TestAC1NewRegressorsRegistered:
    """AC1: All 6 new regressors registered in AVAILABLE_REGRESSORS."""

    def test_construction_output_registered(self) -> None:
        """Construction output regressor is registered."""
        assert "construction_output" in _get_regressor_config().AVAILABLE_REGRESSORS

    def test_industrial_production_registered(self) -> None:
        """Industrial production regressor is registered."""
        assert "industrial_production" in _get_regressor_config().AVAILABLE_REGRESSORS

    def test_gdp_growth_registered(self) -> None:
        """GDP growth regressor is registered."""
        assert "gdp_growth" in _get_regressor_config().AVAILABLE_REGRESSORS

    def test_inflation_registered(self) -> None:
        """Inflation regressor is registered."""
        assert "inflation" in _get_regressor_config().AVAILABLE_REGRESSORS

    def test_building_permits_registered(self) -> None:
        """Building permits regressor is registered."""
        assert "building_permits" in _get_regressor_config().AVAILABLE_REGRESSORS

    def test_construction_confidence_registered(self) -> None:
        """Construction confidence regressor is registered."""
        assert "construction_confidence" in _get_regressor_config().AVAILABLE_REGRESSORS


class TestAC2MetricRegressorMappings:
    """AC2: METRIC_REGRESSORS updated with optimal mappings per variable."""

    def test_revenue_has_construction_output(self) -> None:
        """Revenue mapping includes construction_output."""
        assert "construction_output" in _get_regressor_config().METRIC_REGRESSORS["revenue"]

    def test_revenue_has_gdp_growth(self) -> None:
        """Revenue mapping includes gdp_growth."""
        assert "gdp_growth" in _get_regressor_config().METRIC_REGRESSORS["revenue"]

    def test_sales_volume_has_building_permits(self) -> None:
        """Sales volume mapping includes building_permits."""
        assert "building_permits" in _get_regressor_config().METRIC_REGRESSORS["sales_volume"]

    def test_variable_cost_has_api2_coal(self) -> None:
        """Variable cost mapping includes api2_coal."""
        assert "api2_coal" in _get_regressor_config().METRIC_REGRESSORS["variable_cost"]

    def test_variable_cost_has_industrial_production(self) -> None:
        """Variable cost mapping includes industrial_production."""
        assert "industrial_production" in _get_regressor_config().METRIC_REGRESSORS["variable_cost"]

    def test_electricity_cost_has_ren_electricity(self) -> None:
        """Electricity cost mapping includes ren_electricity."""
        assert "ren_electricity" in _get_regressor_config().METRIC_REGRESSORS["electricity_cost"]

    def test_electricity_cost_has_ttf_gas(self) -> None:
        """Electricity cost mapping includes ttf_gas."""
        assert "ttf_gas" in _get_regressor_config().METRIC_REGRESSORS["electricity_cost"]

    def test_thermal_cost_has_all_energy_indicators(self) -> None:
        """Thermal cost mapping includes api2_coal, ttf_gas, industrial_production."""
        cfg = _get_regressor_config()
        assert "api2_coal" in cfg.METRIC_REGRESSORS["thermal_cost"]
        assert "ttf_gas" in cfg.METRIC_REGRESSORS["thermal_cost"]
        assert "industrial_production" in cfg.METRIC_REGRESSORS["thermal_cost"]

    def test_avg_selling_price_has_construction_confidence(self) -> None:
        """Avg selling price mapping includes construction_confidence."""
        assert (
            "construction_confidence"
            in _get_regressor_config().METRIC_REGRESSORS["avg_selling_price"]
        )

    def test_avg_selling_price_has_inflation(self) -> None:
        """Avg selling price mapping includes inflation."""
        assert "inflation" in _get_regressor_config().METRIC_REGRESSORS["avg_selling_price"]

    def test_capacity_utilization_has_construction_output(self) -> None:
        """Capacity utilization mapping includes construction_output."""
        assert (
            "construction_output"
            in _get_regressor_config().METRIC_REGRESSORS["capacity_utilization"]
        )


class TestCategoryBasedSelection:
    """Test category-based regressor selection."""

    def test_financial_category_has_construction_output(self) -> None:
        """Financial category includes construction_output."""
        assert (
            "construction_output"
            in _get_regressor_config().METRIC_CATEGORIES["financial"]["regressors"]
        )

    def test_energy_category_has_industrial_production(self) -> None:
        """Energy category includes industrial_production."""
        assert (
            "industrial_production"
            in _get_regressor_config().METRIC_CATEGORIES["energy"]["regressors"]
        )

    def test_production_category_has_building_permits(self) -> None:
        """Production category includes building_permits."""
        assert (
            "building_permits"
            in _get_regressor_config().METRIC_CATEGORIES["production"]["regressors"]
        )

    def test_pricing_category_has_construction_confidence(self) -> None:
        """Pricing category includes construction_confidence."""
        assert (
            "construction_confidence"
            in _get_regressor_config().METRIC_CATEGORIES["pricing"]["regressors"]
        )


class TestDefaultRegressors:
    """Test default regressor selection."""

    def test_default_regressors_are_construction_focused(self) -> None:
        """Default regressors prioritize construction indicators."""
        assert "construction_output" in _get_regressor_config().DEFAULT_REGRESSORS

    def test_get_default_regressors_for_unknown_metric(self) -> None:
        """Unknown metrics get default regressors."""
        cfg = _get_regressor_config()
        regressors = cfg.get_default_regressors("unknown_metric_xyz")
        assert regressors == cfg.DEFAULT_REGRESSORS

    def test_get_default_regressors_for_revenue(self) -> None:
        """Revenue metric gets explicit mapping."""
        regressors = _get_regressor_config().get_default_regressors("revenue")
        assert "construction_output" in regressors
        assert "gdp_growth" in regressors
