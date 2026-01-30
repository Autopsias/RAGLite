"""Unit tests for YTD-to-monthly conversion across year boundaries.

Regression tests for the year boundary logic in convert_ytd_to_monthly().
These tests ensure that YTD values are correctly converted to monthly values
when crossing from December to January of a new year.

Key scenario: YTD values accumulate within a year, but reset at year boundaries.
- Dec 2024 YTD = 150 (cumulative Jan-Dec)
- Jan 2025 YTD = 12 (new year, so this IS the January monthly value)

The Jan 2025 monthly value should be 12, NOT (12 - 150 = -138).
"""

from datetime import datetime

from raglite.forecasting.timeseries.sql_extraction_normalization_utils._preprocessing import (
    convert_ytd_to_monthly,
)
from raglite.shared.models import TimeSeriesPoint


class TestYTDYearBoundaryConversion:
    """Tests for YTD→monthly conversion at year boundaries."""

    def test_basic_year_boundary_reset(self) -> None:
        """January YTD should not subtract previous December YTD.

        This is the core regression test for the year boundary bug.
        When crossing Dec→Jan, the prev_ytd must reset to 0.
        """
        points = [
            TimeSeriesPoint(date=datetime(2024, 11, 1), value=120.0, label="Nov-24"),
            TimeSeriesPoint(date=datetime(2024, 12, 1), value=150.0, label="Dec-24"),
            TimeSeriesPoint(date=datetime(2025, 1, 1), value=12.0, label="Jan-25"),
        ]
        result = convert_ytd_to_monthly(points, "ebitda")

        # Extract values (skip any interpolated points)
        result_by_date = {p.date: p.value for p in result}

        # Nov is first point in its context = its YTD value
        assert result_by_date[datetime(2024, 11, 1)] == 120.0
        # Dec monthly = Dec YTD - Nov YTD = 150 - 120 = 30
        assert result_by_date[datetime(2024, 12, 1)] == 30.0
        # Jan monthly = Jan YTD (year reset, no prior to subtract)
        # CRITICAL: Must be 12.0, NOT -138.0 (12 - 150)
        assert result_by_date[datetime(2025, 1, 1)] == 12.0

    def test_multiple_year_boundaries(self) -> None:
        """Multiple year transitions should each reset correctly.

        Uses consecutive months to avoid interpolation effects.
        Note: Uses months other than December to avoid year-end-only filtering
        (Story 6.27 filters years with only December data).
        """
        points = [
            TimeSeriesPoint(date=datetime(2023, 10, 1), value=80.0, label="Oct-23"),
            TimeSeriesPoint(date=datetime(2023, 11, 1), value=100.0, label="Nov-23"),
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=15.0, label="Jan-24"),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=35.0, label="Feb-24"),
            TimeSeriesPoint(date=datetime(2025, 1, 1), value=12.0, label="Jan-25"),
        ]
        result = convert_ytd_to_monthly(points, "revenue")
        result_by_date = {p.date: p.value for p in result}

        # Oct 2023 is first = its YTD value
        assert result_by_date[datetime(2023, 10, 1)] == 80.0
        # Nov 2023 = Nov YTD - Oct YTD = 100 - 80 = 20
        assert result_by_date[datetime(2023, 11, 1)] == 20.0
        # Jan 2024 is new year = its YTD value (15)
        assert result_by_date[datetime(2024, 1, 1)] == 15.0
        # Feb 2024 = Feb YTD - Jan YTD = 35 - 15 = 20
        assert result_by_date[datetime(2024, 2, 1)] == 20.0
        # Jan 2025 is new year = its YTD value (12)
        assert result_by_date[datetime(2025, 1, 1)] == 12.0

    def test_negative_ytd_at_year_end(self) -> None:
        """Handle case where year-end YTD is negative (loss year).

        The new year's value should still be its own YTD, not affected
        by the previous year's negative value.

        Note: Uses November/December to have multiple months in 2024
        (Story 6.27 filters years with only December data).
        """
        points = [
            TimeSeriesPoint(date=datetime(2024, 11, 1), value=-30.0, label="Nov-24"),
            TimeSeriesPoint(date=datetime(2024, 12, 1), value=-50.0, label="Dec-24"),
            TimeSeriesPoint(date=datetime(2025, 1, 1), value=10.0, label="Jan-25"),
        ]
        result = convert_ytd_to_monthly(points, "net_income")
        result_by_date = {p.date: p.value for p in result}

        # Nov 2024 is first = its value (-30)
        assert result_by_date[datetime(2024, 11, 1)] == -30.0
        # Dec 2024 = Dec YTD - Nov YTD = -50 - (-30) = -20
        assert result_by_date[datetime(2024, 12, 1)] == -20.0
        # Jan 2025 = its YTD (10), NOT 10 - (-50) = 60
        assert result_by_date[datetime(2025, 1, 1)] == 10.0

    def test_single_point_unchanged(self) -> None:
        """Single point should be returned unchanged."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 6, 1), value=100.0, label="Jun-24"),
        ]
        result = convert_ytd_to_monthly(points, "ebitda")

        assert len(result) == 1
        assert result[0].value == 100.0

    def test_empty_list_unchanged(self) -> None:
        """Empty input should return empty output."""
        result = convert_ytd_to_monthly([], "test_metric")
        assert result == []

    def test_full_year_within_same_year(self) -> None:
        """Multiple months within same year should correctly compute deltas."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=10.0, label="Jan-24"),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=25.0, label="Feb-24"),
            TimeSeriesPoint(date=datetime(2024, 3, 1), value=45.0, label="Mar-24"),
        ]
        result = convert_ytd_to_monthly(points, "revenue")
        result_by_date = {p.date: p.value for p in result}

        # Jan is first = its YTD value
        assert result_by_date[datetime(2024, 1, 1)] == 10.0
        # Feb = 25 - 10 = 15
        assert result_by_date[datetime(2024, 2, 1)] == 15.0
        # Mar = 45 - 25 = 20
        assert result_by_date[datetime(2024, 3, 1)] == 20.0

    def test_labels_updated_with_monthly_suffix(self) -> None:
        """Labels should indicate conversion from YTD to monthly."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 6, 1), value=100.0, label="Jun-24"),
            TimeSeriesPoint(date=datetime(2024, 7, 1), value=120.0, label="Jul-24"),
        ]
        result = convert_ytd_to_monthly(points, "ebitda")

        for p in result:
            # Verify the label contains "Monthly" indication
            assert "Monthly" in p.label or "converted" in p.label.lower()
