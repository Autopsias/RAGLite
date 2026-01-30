"""Tests for unit-based normalization (Phase 2 data quality).

Tests the explicit unit-based scaling that replaces value-based heuristics.
"""

from datetime import datetime

from raglite.forecasting.timeseries.sql_extraction_config import (
    UNIT_SCALING_FACTORS,
    get_unit_scaling_factor,
)
from raglite.forecasting.timeseries.sql_extraction_normalization_utils import (
    normalize_by_unit,
)
from raglite.forecasting.timeseries.sql_extraction_parsing import (
    ParsedTimeSeriesData,
    parse_sql_rows_with_units,
)
from raglite.shared.models import TimeSeriesPoint


class TestGetUnitScalingFactor:
    """Test unit scaling factor lookup."""

    def test_eur_to_meur_scaling(self) -> None:
        """EUR should scale by 0.000001 to M EUR."""
        assert get_unit_scaling_factor("EUR") == 0.000001

    def test_keur_to_meur_scaling(self) -> None:
        """kEUR variants should scale by 0.001 to M EUR."""
        assert get_unit_scaling_factor("K EUR") == 0.001
        assert get_unit_scaling_factor("kEUR") == 0.001
        assert get_unit_scaling_factor("KEUR") == 0.001
        assert get_unit_scaling_factor("1000 EUR") == 0.001

    def test_meur_no_scaling(self) -> None:
        """M EUR variants should not scale (factor = 1.0)."""
        assert get_unit_scaling_factor("M EUR") == 1.0
        assert get_unit_scaling_factor("MEUR") == 1.0
        assert get_unit_scaling_factor("Million EUR") == 1.0

    def test_percentage_no_scaling(self) -> None:
        """Percentage units should not scale."""
        assert get_unit_scaling_factor("%") == 1.0

    def test_per_unit_metrics_no_scaling(self) -> None:
        """Per-unit metrics should not scale."""
        assert get_unit_scaling_factor("EUR/ton") == 1.0
        assert get_unit_scaling_factor("EUR/MWh") == 1.0

    def test_none_and_empty_no_scaling(self) -> None:
        """None and empty strings should return 1.0."""
        assert get_unit_scaling_factor(None) == 1.0
        assert get_unit_scaling_factor("") == 1.0

    def test_case_insensitive_lookup(self) -> None:
        """Lookup should be case-insensitive."""
        # These exact cases are in the lookup
        assert get_unit_scaling_factor("meur") == 1.0
        assert get_unit_scaling_factor("k eur") == 0.001

    def test_unknown_unit_returns_1(self) -> None:
        """Unknown units should return 1.0 (no scaling)."""
        assert get_unit_scaling_factor("UNKNOWN_UNIT_XYZ") == 1.0

    def test_whitespace_handling(self) -> None:
        """Whitespace should be stripped before lookup."""
        assert get_unit_scaling_factor("  EUR  ") == 0.000001


class TestNormalizeByUnit:
    """Test unit-based normalization function."""

    def test_keur_to_meur_conversion(self) -> None:
        """kEUR values should be converted to M EUR."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 15), value=1000.0, label="Jan-24"),
            TimeSeriesPoint(date=datetime(2024, 2, 15), value=2000.0, label="Feb-24"),
        ]
        units = ["K EUR", "K EUR"]

        result = normalize_by_unit(points, units, "test_metric")

        assert len(result) == 2
        assert result[0].value == 1.0  # 1000 * 0.001 = 1.0
        assert result[1].value == 2.0  # 2000 * 0.001 = 2.0
        assert "K EUR→M EUR" in result[0].label

    def test_mixed_units_normalization(self) -> None:
        """Mixed units should each apply their own scaling."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 15), value=1000.0, label="Jan-24"),
            TimeSeriesPoint(date=datetime(2024, 2, 15), value=5.0, label="Feb-24"),
        ]
        units = ["K EUR", "M EUR"]

        result = normalize_by_unit(points, units, "test_metric")

        assert len(result) == 2
        assert result[0].value == 1.0  # 1000 kEUR → 1 M EUR
        assert result[1].value == 5.0  # 5 M EUR stays 5 M EUR

    def test_empty_points_returns_empty(self) -> None:
        """Empty points list should return empty."""
        result = normalize_by_unit([], [], "test_metric")
        assert result == []

    def test_length_mismatch_returns_original(self) -> None:
        """Mismatched points/units length should return original points."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 15), value=1000.0, label="Jan-24"),
        ]
        units = ["K EUR", "M EUR"]  # Length mismatch

        result = normalize_by_unit(points, units, "test_metric")

        # Should return original points unchanged
        assert len(result) == 1
        assert result[0].value == 1000.0

    def test_all_valid_values_normalized(self) -> None:
        """All valid points should be normalized."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 15), value=500.0, label="Jan-24"),
            TimeSeriesPoint(date=datetime(2024, 2, 15), value=1000.0, label="Feb-24"),
        ]
        units = ["K EUR", "K EUR"]

        result = normalize_by_unit(points, units, "test_metric")

        assert len(result) == 2
        assert result[0].value == 0.5  # 500 * 0.001 = 0.5
        assert result[1].value == 1.0  # 1000 * 0.001 = 1.0

    def test_factor_1_no_label_change(self) -> None:
        """When factor is 1.0, label should not be modified."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 15), value=5.0, label="Jan-24"),
        ]
        units = ["M EUR"]

        result = normalize_by_unit(points, units, "test_metric")

        assert len(result) == 1
        assert result[0].value == 5.0
        assert result[0].label == "Jan-24"  # Unchanged


class TestParseSqlRowsWithUnits:
    """Test SQL row parsing with unit extraction."""

    def test_parse_7_tuple_with_unit(self) -> None:
        """7-tuple rows should extract unit correctly."""
        rows = [
            ("Jan-24", 2024, 1000.0, 1, "Jan 2024 Report", False, "K EUR"),
            ("Feb-24", 2024, 1500.0, 1, "Feb 2024 Report", False, "K EUR"),
        ]

        result = parse_sql_rows_with_units(rows, "test_metric")

        assert isinstance(result, ParsedTimeSeriesData)
        assert len(result.points) == 2
        assert len(result.units) == 2
        assert result.units[0] == "K EUR"
        assert result.units[1] == "K EUR"

    def test_parse_6_tuple_backwards_compatible(self) -> None:
        """6-tuple rows (old format) should work with None units."""
        rows = [
            ("Jan-24", 2024, 1000.0, 1, "Jan 2024 Report", False),
            ("Feb-24", 2024, 1500.0, 1, "Feb 2024 Report", False),
        ]

        result = parse_sql_rows_with_units(rows, "test_metric")

        assert len(result.points) == 2
        assert len(result.units) == 2
        assert result.units[0] is None
        assert result.units[1] is None

    def test_parse_mixed_tuple_lengths(self) -> None:
        """Mixed tuple lengths should be handled gracefully."""
        rows = [
            ("Jan-24", 2024, 1000.0, 1, "Jan 2024 Report", False, "K EUR"),
            ("Feb-24", 2024, 1500.0, 1, "Feb 2024 Report", False),  # No unit
        ]

        result = parse_sql_rows_with_units(rows, "test_metric")

        assert len(result.points) == 2
        assert result.units[0] == "K EUR"
        assert result.units[1] is None

    def test_year_values_filtered(self) -> None:
        """Year-like values (2000-2099) should be filtered."""
        rows = [
            ("Jan-24", 2024, 2024.0, 1, "Jan 2024 Report", False, "K EUR"),  # Year value
            ("Feb-24", 2024, 2000.0, 1, "Feb 2024 Report", False, "K EUR"),  # Filtered
        ]

        result = parse_sql_rows_with_units(rows, "test_metric")

        assert len(result.points) == 0  # Both filtered
        assert len(result.units) == 0


class TestUnitScalingFactorsCompleteness:
    """Test that all expected units are covered."""

    def test_all_eur_variants_covered(self) -> None:
        """Common EUR unit variants should be in the lookup."""
        eur_variants = ["EUR", "K EUR", "kEUR", "KEUR", "M EUR", "MEUR"]
        for variant in eur_variants:
            assert variant in UNIT_SCALING_FACTORS, f"Missing: {variant}"

    def test_percentage_covered(self) -> None:
        """Percentage unit should be covered."""
        assert "%" in UNIT_SCALING_FACTORS

    def test_none_and_empty_covered(self) -> None:
        """None and empty string should be covered."""
        assert None in UNIT_SCALING_FACTORS
        assert "" in UNIT_SCALING_FACTORS
