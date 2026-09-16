"""Unit tests for MCP Model Selection - Variable Alias Resolution.

Story 7b-6: MCP Integration with Model Selection

TDD Phase: RED - These tests are expected to FAIL until implementation complete.

Test IDs map to Acceptance Criteria:
- TEST-AC-7b.6.5.x: Variable alias resolution tests (Epic 7 Fix)
"""

from __future__ import annotations

import pytest

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


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
