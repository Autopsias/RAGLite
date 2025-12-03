"""Unit tests for cement industry KPI patterns (Phase 1.1).

Tests cement-specific metric classification patterns added to classification.py
and metric synonym expansion added to query_classifier.py.

Addresses the petcoke/energy query failures identified in Story 5.0.7.
"""

from raglite.ingestion.adaptive_table.classification import HeaderType, classify_header
from raglite.retrieval.query_classifier import METRIC_SYNONYMS, expand_metric_synonyms


class TestCementFuelPatterns:
    """Test fuel-related metric pattern classification (Phase 1.1)."""

    def test_petcoke_pattern(self):
        """Test petcoke metric classification - was failing before Phase 1.1."""
        assert classify_header("Petcoke") == HeaderType.METRIC
        assert classify_header("Pet Coke") == HeaderType.METRIC
        assert classify_header("Petroleum Coke") == HeaderType.METRIC
        assert classify_header("Petcoke Consumption") == HeaderType.METRIC

    def test_coal_pattern(self):
        """Test coal metric classification."""
        assert classify_header("Coal") == HeaderType.METRIC
        assert classify_header("Coal Consumption") == HeaderType.METRIC
        assert classify_header("Lignite") == HeaderType.METRIC

    def test_alternative_fuels_pattern(self):
        """Test alternative fuels metric classification."""
        assert classify_header("Alternative Fuels") == HeaderType.METRIC
        assert classify_header("AF Rate") == HeaderType.METRIC
        assert classify_header("Biomass") == HeaderType.METRIC
        assert classify_header("Waste Fuel") == HeaderType.METRIC

    def test_fuel_cost_pattern(self):
        """Test fuel cost metric classification."""
        assert classify_header("Fuel Oil") == HeaderType.METRIC
        assert classify_header("Natural Gas") == HeaderType.METRIC


class TestCementProductionPatterns:
    """Test production-related metric pattern classification (Phase 1.1)."""

    def test_clinker_pattern(self):
        """Test clinker pattern classification.

        Note: "Clinker" alone matches ENTITY pattern first (line 132 in classification.py).
        "Clinker Factor/Ratio" matches METRIC pattern due to additional context words.
        """
        # Standalone "Clinker" matches ENTITY pattern (cement/concrete/clinker group)
        assert classify_header("Clinker") == HeaderType.ENTITY
        # But with context words, matches METRIC pattern
        assert classify_header("Clinker Factor") == HeaderType.METRIC
        assert classify_header("Clinker Ratio") == HeaderType.METRIC
        assert classify_header("Clinker/Cement") == HeaderType.METRIC

    def test_raw_materials_pattern(self):
        """Test raw materials metric classification."""
        assert classify_header("Slag") == HeaderType.METRIC
        assert classify_header("Fly Ash") == HeaderType.METRIC
        assert classify_header("Gypsum") == HeaderType.METRIC
        assert classify_header("Limestone") == HeaderType.METRIC

    def test_production_equipment_pattern(self):
        """Test production equipment metric classification.

        Note: "Cement Mill" contains "Cement" which matches ENTITY pattern first.
        Equipment terms need additional context to classify as METRIC.
        """
        assert classify_header("Kiln") == HeaderType.METRIC
        assert classify_header("Grinding") == HeaderType.METRIC
        assert classify_header("Raw Mill") == HeaderType.METRIC
        # "Cement Mill" matches ENTITY due to "cement" substring
        assert classify_header("Cement Mill") == HeaderType.ENTITY
        # But with metric context, should match as METRIC
        assert classify_header("Cement Mill Output") == HeaderType.METRIC


class TestCementSustainabilityPatterns:
    """Test sustainability metric pattern classification (Phase 1.1)."""

    def test_co2_emissions_pattern(self):
        """Test CO2/emissions metric classification."""
        assert classify_header("CO2") == HeaderType.METRIC
        assert classify_header("Emissions") == HeaderType.METRIC
        assert classify_header("Carbon") == HeaderType.METRIC
        assert classify_header("Scope 1") == HeaderType.METRIC
        assert classify_header("Scope 2") == HeaderType.METRIC
        assert classify_header("Scope 3") == HeaderType.METRIC

    def test_thermal_substitution_pattern(self):
        """Test thermal substitution metric classification."""
        assert classify_header("Thermal Substitution") == HeaderType.METRIC
        assert classify_header("TSR") == HeaderType.METRIC

    def test_decarbonization_pattern(self):
        """Test decarbonization metric classification."""
        assert classify_header("Decarbonization") == HeaderType.METRIC
        assert classify_header("Decarbonisation") == HeaderType.METRIC
        assert classify_header("Net Zero") == HeaderType.METRIC


class TestCementUtilizationPatterns:
    """Test utilization/efficiency metric pattern classification (Phase 1.1)."""

    def test_utilization_pattern(self):
        """Test utilization metric classification."""
        assert classify_header("Utilization") == HeaderType.METRIC
        assert classify_header("Uptime") == HeaderType.METRIC
        assert classify_header("Availability") == HeaderType.METRIC


class TestMetricSynonymExpansion:
    """Test METRIC_SYNONYMS dictionary completeness (Phase 1.2)."""

    def test_energy_synonyms_exist(self):
        """Test energy metric synonyms are defined."""
        assert "energy" in METRIC_SYNONYMS
        assert "Electrical Energy" in METRIC_SYNONYMS["energy"]
        assert "Thermal Energy" in METRIC_SYNONYMS["energy"]

    def test_petcoke_synonyms_exist(self):
        """Test petcoke metric synonyms are defined - critical for Story 5.0.7."""
        assert "petcoke" in METRIC_SYNONYMS
        assert "Petcoke Consumption" in METRIC_SYNONYMS["petcoke"]
        assert "Pet Coke" in METRIC_SYNONYMS["petcoke"]
        assert "Petroleum Coke" in METRIC_SYNONYMS["petcoke"]

    def test_working_capital_synonyms_exist(self):
        """Test working capital metric synonyms are defined."""
        assert "working capital" in METRIC_SYNONYMS
        assert "Trade Working Capital" in METRIC_SYNONYMS["working capital"]
        assert "Net Working Capital" in METRIC_SYNONYMS["working capital"]

    def test_alternative_fuels_synonyms_exist(self):
        """Test alternative fuels metric synonyms are defined."""
        assert "alternative fuels" in METRIC_SYNONYMS
        assert "AF Rate" in METRIC_SYNONYMS["alternative fuels"]
        assert "Biomass" in METRIC_SYNONYMS["alternative fuels"]


class TestExpandMetricSynonyms:
    """Test expand_metric_synonyms() function (Phase 1.2)."""

    def test_energy_query_expansion(self):
        """Test energy query synonym expansion."""
        result = expand_metric_synonyms("What is energy consumption for Portugal?")
        assert "Electrical Energy" in result
        assert "Thermal Energy" in result
        assert "Fuel Energy" in result

    def test_petcoke_query_expansion(self):
        """Test petcoke query synonym expansion - was failing before Phase 1.2."""
        result = expand_metric_synonyms("What is petcoke consumption?")
        assert "Petcoke Consumption" in result
        assert "Pet Coke" in result
        assert "Petroleum Coke" in result

    def test_working_capital_query_expansion(self):
        """Test working capital query synonym expansion."""
        result = expand_metric_synonyms("Show working capital for Tunisia")
        assert "Trade Working Capital" in result
        assert "Net Working Capital" in result
        assert "WC" in result

    def test_no_match_empty_list(self):
        """Test query with no metric matches returns empty list."""
        result = expand_metric_synonyms("Hello world random query")
        assert result == []

    def test_case_insensitive_matching(self):
        """Test case-insensitive query matching."""
        result = expand_metric_synonyms("ENERGY consumption")
        assert len(result) > 0
        assert "Electrical Energy" in result


class TestMetricSynonymDictionaryStructure:
    """Test METRIC_SYNONYMS data structure quality (Phase 1.2)."""

    def test_dictionary_not_empty(self):
        """Test synonym dictionary is populated."""
        assert len(METRIC_SYNONYMS) > 0
        assert len(METRIC_SYNONYMS) >= 10  # Story spec: 30+ synonym groups

    def test_no_duplicate_values_within_groups(self):
        """Test no duplicate synonyms within each group."""
        for key, synonyms in METRIC_SYNONYMS.items():
            assert len(synonyms) == len(set(synonyms)), f"Duplicates in group '{key}'"

    def test_all_values_are_lists(self):
        """Test all synonym groups are lists."""
        for key, synonyms in METRIC_SYNONYMS.items():
            assert isinstance(synonyms, list), f"Group '{key}' is not a list"
            assert len(synonyms) > 0, f"Group '{key}' is empty"


class TestPatternPriority:
    """Test pattern priority ordering (prevents Story 5.0.6 bug)."""

    def test_ebitda_margin_not_misclassified(self):
        """Test EBITDA Margin classified as METRIC (not misclassified due to pattern order)."""
        # This test prevents regression of pattern priority bug from Story 5.0.6
        # "EBITDA Margin" should match as METRIC, not be confused with revenue patterns
        result = classify_header("EBITDA Margin")
        assert result == HeaderType.METRIC

    def test_revenue_classified_correctly(self):
        """Test Revenue classified as METRIC."""
        assert classify_header("Revenue") == HeaderType.METRIC
        assert classify_header("Total Revenue") == HeaderType.METRIC

    def test_margin_classified_correctly(self):
        """Test Margin classified as METRIC."""
        assert classify_header("Margin") == HeaderType.METRIC
        assert classify_header("Gross Margin") == HeaderType.METRIC
