"""Additional tests for regressor configuration with Story 6.16 indicators.

Story 6.16: Add Eurostat Construction & Industrial Indicators

This test file focuses on:
- [P0] Configuration of new construction_output and industrial_production regressors
- [P1] Auto-selection for production/volume metrics
- [P2] Metric category matching with new indicators
- [P3] Edge cases for regressor validation

Complements tests/unit/test_story_6_11_mcp_multivariate.py with Story 6.16 specific tests.

Run with: pytest tests/unit/test_regressor_config_story_6_16.py -v
"""

from __future__ import annotations


class TestConstructionOutputRegressorConfig:
    """[P0] Configuration tests for construction_output regressor."""

    def test_p0_construction_output_in_available_list(self) -> None:
        """
        [P0] construction_output must be in AVAILABLE_REGRESSORS.

        Given: regressor_config module
        When: Checking AVAILABLE_REGRESSORS
        Then: "construction_output" is present
        """
        from raglite.forecasting.regressor_config import AVAILABLE_REGRESSORS

        assert "construction_output" in AVAILABLE_REGRESSORS

    def test_p0_construction_output_in_production_category(self) -> None:
        """
        [P0] construction_output should be in production category regressors.

        Given: METRIC_CATEGORIES configuration
        When: Checking "production" category regressors
        Then: construction_output is included
        """
        from raglite.forecasting.regressor_config import METRIC_CATEGORIES

        production_regressors = METRIC_CATEGORIES["production"]["regressors"]
        assert "construction_output" in production_regressors

    def test_p1_sales_volume_auto_selects_construction(self) -> None:
        """
        [P1] sales_volume metric should auto-select construction_output.

        Given: Metric "sales_volume"
        When: get_default_regressors() is called
        Then: Returns construction_output as a regressor
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("sales_volume")
        assert "construction_output" in regressors

    def test_p1_sales_volumes_with_space_auto_selects_construction(self) -> None:
        """
        [P1] "sales volumes" (with space) should also select construction_output.

        Given: Metric "sales volumes" (space-separated)
        When: get_default_regressors() is called
        Then: Returns construction_output
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("sales volumes")
        assert "construction_output" in regressors

    def test_p2_production_keyword_matches_construction(self) -> None:
        """
        [P2] Metrics with "production" keyword should include construction_output.

        Given: Metric containing "production"
        When: get_default_regressors() is called
        Then: construction_output is in returned regressors
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("cement_production_monthly")
        assert "construction_output" in regressors or "industrial_production" in regressors

    def test_p2_volume_keyword_matches_construction(self) -> None:
        """
        [P2] Metrics with "volume" keyword should include construction_output.

        Given: Metric containing "volume"
        When: get_default_regressors() is called
        Then: construction_output is in returned regressors
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("total_sales_volume")
        assert "construction_output" in regressors


class TestIndustrialProductionRegressorConfig:
    """[P0] Configuration tests for industrial_production regressor."""

    def test_p0_industrial_production_in_available_list(self) -> None:
        """
        [P0] industrial_production must be in AVAILABLE_REGRESSORS.

        Given: regressor_config module
        When: Checking AVAILABLE_REGRESSORS
        Then: "industrial_production" is present
        """
        from raglite.forecasting.regressor_config import AVAILABLE_REGRESSORS

        assert "industrial_production" in AVAILABLE_REGRESSORS

    def test_p0_industrial_production_in_production_category(self) -> None:
        """
        [P0] industrial_production should be in production category regressors.

        Given: METRIC_CATEGORIES configuration
        When: Checking "production" category regressors
        Then: industrial_production is included
        """
        from raglite.forecasting.regressor_config import METRIC_CATEGORIES

        production_regressors = METRIC_CATEGORIES["production"]["regressors"]
        assert "industrial_production" in production_regressors

    def test_p1_capacity_utilization_auto_selects_industrial(self) -> None:
        """
        [P1] capacity_utilization metric should auto-select industrial_production.

        Given: Metric "capacity_utilization"
        When: get_default_regressors() is called
        Then: Returns industrial_production as a regressor
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("capacity_utilization")
        assert "industrial_production" in regressors

    def test_p1_frequency_ratio_auto_selects_industrial(self) -> None:
        """
        [P1] frequency ratio metric should auto-select industrial_production.

        Given: Metric "frequency ratio"
        When: get_default_regressors() is called
        Then: Returns industrial_production
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("frequency ratio")
        assert "industrial_production" in regressors

    def test_p2_utilization_keyword_matches_industrial(self) -> None:
        """
        [P2] Metrics with "utilization" keyword should include industrial_production.

        Given: Metric containing "utilization"
        When: get_default_regressors() is called
        Then: industrial_production is in returned regressors
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("plant_utilization_rate")
        assert "industrial_production" in regressors

    def test_p2_output_keyword_matches_industrial(self) -> None:
        """
        [P2] Metrics with "output" keyword should include industrial_production.

        Given: Metric containing "output"
        When: get_default_regressors() is called
        Then: industrial_production is in returned regressors
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("monthly_output_index")
        assert "industrial_production" in regressors or "construction_output" in regressors


class TestMetricRegressorMappingUpdates:
    """[P1] Tests for updated METRIC_REGRESSORS mappings with Story 6.16."""

    def test_p1_sales_volume_includes_construction_and_industrial(self) -> None:
        """
        [P1] sales_volume mapping should include both new indicators.

        Given: METRIC_REGRESSORS configuration
        When: Checking "sales_volume" mapping
        Then: Includes construction_output and industrial_production
        """
        from raglite.forecasting.regressor_config import METRIC_REGRESSORS

        if "sales_volume" in METRIC_REGRESSORS:
            regressors = METRIC_REGRESSORS["sales_volume"]
            assert "construction_output" in regressors
            assert "industrial_production" in regressors

    def test_p1_capacity_utilization_includes_industrial(self) -> None:
        """
        [P1] capacity_utilization mapping should include industrial_production.

        Given: METRIC_REGRESSORS configuration
        When: Checking "capacity_utilization" mapping
        Then: Includes industrial_production
        """
        from raglite.forecasting.regressor_config import METRIC_REGRESSORS

        if "capacity_utilization" in METRIC_REGRESSORS:
            regressors = METRIC_REGRESSORS["capacity_utilization"]
            assert "industrial_production" in regressors

    def test_p2_sales_with_construction_output_regressor(self) -> None:
        """
        [P2] Generic "sales" metric should include construction_output.

        Given: Metric "sales"
        When: get_default_regressors() is called
        Then: construction_output is included
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("sales")
        # Either explicit mapping or category match should include it
        assert "construction_output" in regressors or any("construction" in r for r in regressors)


class TestRegressorValidation:
    """[P1] Validation tests for new regressors."""

    def test_p1_construction_output_validates_as_valid(self) -> None:
        """
        [P1] "construction_output" should pass validation.

        Given: Regressor name "construction_output"
        When: validate_regressor_names() is called
        Then: Returns it in valid list
        """
        from raglite.forecasting.regressor_config import validate_regressor_names

        valid, invalid = validate_regressor_names(["construction_output"])
        assert "construction_output" in valid
        assert len(invalid) == 0

    def test_p1_industrial_production_validates_as_valid(self) -> None:
        """
        [P1] "industrial_production" should pass validation.

        Given: Regressor name "industrial_production"
        When: validate_regressor_names() is called
        Then: Returns it in valid list
        """
        from raglite.forecasting.regressor_config import validate_regressor_names

        valid, invalid = validate_regressor_names(["industrial_production"])
        assert "industrial_production" in valid
        assert len(invalid) == 0

    def test_p1_mixed_validation_with_new_regressors(self) -> None:
        """
        [P1] Validation should handle mix of old and new regressors.

        Given: List with euribor_3m, construction_output, fake_regressor
        When: validate_regressor_names() is called
        Then: Returns correct valid/invalid split
        """
        from raglite.forecasting.regressor_config import validate_regressor_names

        names = ["euribor_3m", "construction_output", "industrial_production", "fake_one"]
        valid, invalid = validate_regressor_names(names)

        assert "euribor_3m" in valid
        assert "construction_output" in valid
        assert "industrial_production" in valid
        assert "fake_one" in invalid

    def test_p2_case_insensitive_validation_for_new_regressors(self) -> None:
        """
        [P2] Validation should be case-insensitive for new regressors.

        Given: Uppercase/mixed-case regressor names
        When: validate_regressor_names() is called
        Then: Accepts variations of case
        """
        from raglite.forecasting.regressor_config import validate_regressor_names

        valid, invalid = validate_regressor_names(["CONSTRUCTION_OUTPUT", "Industrial_Production"])

        # Should match case-insensitively
        assert len(valid) == 2
        assert len(invalid) == 0


class TestProductionCategoryKeywords:
    """[P2] Tests for "production" category keyword matching."""

    def test_p2_production_category_has_correct_keywords(self) -> None:
        """
        [P2] Production category should have comprehensive keywords.

        Given: METRIC_CATEGORIES configuration
        When: Checking "production" category keywords
        Then: Includes volume, capacity, utilization, production, output
        """
        from raglite.forecasting.regressor_config import METRIC_CATEGORIES

        keywords = METRIC_CATEGORIES["production"]["keywords"]
        assert "volume" in keywords
        assert "capacity" in keywords
        assert "utilization" in keywords
        assert "production" in keywords
        assert "output" in keywords

    def test_p2_production_category_has_correct_regressors(self) -> None:
        """
        [P2] Production category should return construction + industrial + euribor.

        Given: METRIC_CATEGORIES configuration
        When: Checking "production" category regressors
        Then: Includes construction_output, industrial_production, euribor_3m
        """
        from raglite.forecasting.regressor_config import METRIC_CATEGORIES

        regressors = METRIC_CATEGORIES["production"]["regressors"]
        assert "construction_output" in regressors
        assert "industrial_production" in regressors
        assert "euribor_3m" in regressors


class TestRegressorAvailabilityCount:
    """[P3] Tests to ensure regressor list completeness."""

    def test_p3_available_regressors_includes_at_least_seven(self) -> None:
        """
        [P3] AVAILABLE_REGRESSORS should have at least 7 items (Story 6.16 adds 2).

        Given: regressor_config module
        When: Counting AVAILABLE_REGRESSORS
        Then: Has >= 7 items (euribor, ttf, api2, diesel, eurostat_electricity, construction, industrial)
        """
        from raglite.forecasting.regressor_config import AVAILABLE_REGRESSORS

        assert len(AVAILABLE_REGRESSORS) >= 7

    def test_p3_all_new_regressors_present(self) -> None:
        """
        [P3] Both new Story 6.16 regressors must be in AVAILABLE_REGRESSORS.

        Given: regressor_config module
        When: Checking AVAILABLE_REGRESSORS
        Then: Both construction_output and industrial_production are present
        """
        from raglite.forecasting.regressor_config import AVAILABLE_REGRESSORS

        new_regressors = ["construction_output", "industrial_production"]
        for reg in new_regressors:
            assert reg in AVAILABLE_REGRESSORS, f"{reg} missing from AVAILABLE_REGRESSORS"

    def test_p3_get_available_regressors_returns_copy(self) -> None:
        """
        [P3] get_available_regressors() should return a copy, not original list.

        Given: get_available_regressors() function
        When: Calling it twice and modifying one result
        Then: Other result is unaffected (proves it's a copy)
        """
        from raglite.forecasting.regressor_config import get_available_regressors

        list1 = get_available_regressors()
        list2 = get_available_regressors()

        list1.append("fake_regressor")

        assert "fake_regressor" not in list2, "Should return a copy, not the original"


class TestEdgeCasesForNewRegressors:
    """[P3] Edge cases for construction_output and industrial_production."""

    def test_p3_whitespace_in_metric_name_still_matches(self) -> None:
        """
        [P3] Metric names with extra whitespace should still match.

        Given: Metric "  sales_volume  " (with spaces)
        When: get_default_regressors() is called
        Then: Correctly selects construction_output (after strip)
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("  sales_volume  ")
        assert "construction_output" in regressors

    def test_p3_metric_with_underscores_and_spaces_normalized(self) -> None:
        """
        [P3] Metrics with mixed underscores/spaces should match.

        Given: Metric "sales volume" (space) vs "sales_volume" (underscore)
        When: get_default_regressors() is called for both
        Then: Both return same regressors (normalized)
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        space_result = get_default_regressors("sales volume")
        underscore_result = get_default_regressors("sales_volume")

        # Both should match to same regressors
        assert set(space_result) == set(underscore_result)

    def test_p3_empty_string_metric_returns_default(self) -> None:
        """
        [P3] Empty string metric should return DEFAULT_REGRESSORS.

        Given: Metric is empty string ""
        When: get_default_regressors() is called
        Then: Returns DEFAULT_REGRESSORS (fallback)
        """
        from raglite.forecasting.regressor_config import (
            DEFAULT_REGRESSORS,
            get_default_regressors,
        )

        regressors = get_default_regressors("")
        assert regressors == DEFAULT_REGRESSORS

    def test_p3_numeric_metric_name_returns_default(self) -> None:
        """
        [P3] Numeric metric names should fallback to defaults.

        Given: Metric "12345"
        When: get_default_regressors() is called
        Then: Returns DEFAULT_REGRESSORS
        """
        from raglite.forecasting.regressor_config import (
            DEFAULT_REGRESSORS,
            get_default_regressors,
        )

        regressors = get_default_regressors("12345")
        assert regressors == DEFAULT_REGRESSORS


class TestBackwardCompatibility:
    """[P2] Ensure Story 6.16 changes don't break existing configurations."""

    def test_p2_revenue_still_has_financial_regressors(self) -> None:
        """
        [P2] revenue metric should include construction and financial regressors.

        Given: Metric "revenue" (Story 6.20: Cement industry focus)
        When: get_default_regressors() is called
        Then: Returns construction-focused financial regressors
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("revenue")
        assert "euribor_3m" in regressors
        assert "construction_output" in regressors
        assert "gdp_growth" in regressors

    def test_p2_ebitda_still_has_energy_regressors(self) -> None:
        """
        [P2] ebitda metric should still include ttf_gas, api2_coal.

        Given: Metric "ebitda"
        When: get_default_regressors() is called
        Then: Returns existing energy/financial regressors
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("ebitda")
        assert "euribor_3m" in regressors
        assert "ttf_gas" in regressors

    def test_p2_electricity_cost_uses_ren_electricity(self) -> None:
        """
        [P2] electricity_cost should use ren_electricity (Story 7.0).

        Given: Metric "electricity_cost"
        When: get_default_regressors() is called
        Then: Returns ren_electricity (Story 7.0: 9 points → 60+ monthly)
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("electricity_cost")
        assert "ren_electricity" in regressors
        assert "ttf_gas" in regressors

    def test_p2_default_regressors_unchanged(self) -> None:
        """
        [P2] DEFAULT_REGRESSORS should be construction-focused.

        Given: DEFAULT_REGRESSORS constant (Story 6.20: Cement industry focus)
        When: Checking its value
        Then: Has construction-focused regressors
        """
        from raglite.forecasting.regressor_config import DEFAULT_REGRESSORS

        assert "euribor_3m" in DEFAULT_REGRESSORS
        assert "construction_output" in DEFAULT_REGRESSORS
        assert "gdp_growth" in DEFAULT_REGRESSORS
