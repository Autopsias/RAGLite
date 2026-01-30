"""Unit tests for year-end-only data point filter (Story 6.27).

Tests cover:
- AC1: Years with only December data are filtered (unreliable year-end data)
- AC2: December is NOT filtered when other months exist in the same year
- Bug fix (2026-01-27): Count months per year, not points per year
"""

from datetime import datetime

import pytest

from raglite.forecasting.timeseries.sql_extraction_normalization_utils._utils import (
    filter_year_end_only_points,
)
from raglite.shared.models import TimeSeriesPoint


class TestFilterYearEndOnlyPoints:
    """Tests for filter_year_end_only_points function (Story 6.27)."""

    def test_december_not_filtered_when_other_months_exist(self) -> None:
        """Bug fix (2026-01-27): December should NOT be filtered when other months exist.

        This test verifies the fix for the bug where December 2025 was being filtered
        because the original logic counted points per year, not months per year.
        After YTD-to-monthly conversion, if December ended up being the only remaining
        point for 2025 (due to other filtering), the entire year would be incorrectly
        filtered as "year-end only".
        """
        points = [
            TimeSeriesPoint(date=datetime(2025, 9, 1), value=100.0, label="Sep-25"),
            TimeSeriesPoint(date=datetime(2025, 10, 1), value=110.0, label="Oct-25"),
            TimeSeriesPoint(date=datetime(2025, 11, 1), value=120.0, label="Nov-25"),
            TimeSeriesPoint(date=datetime(2025, 12, 1), value=130.0, label="Dec-25"),
        ]
        result = filter_year_end_only_points(points, "ebitda")

        # December should NOT be removed - 2025 has multiple months
        assert len(result) == 4
        assert any(p.date.month == 12 for p in result)
        # All original points should be preserved
        result_dates = {(p.date.year, p.date.month) for p in result}
        assert result_dates == {(2025, 9), (2025, 10), (2025, 11), (2025, 12)}

    def test_december_filtered_when_sole_month_in_year(self) -> None:
        """Story 6.27: December SHOULD be filtered when it's the only month in a year.

        Years with only December data are unreliable (often annual reports
        with incomplete or aggregated figures).
        """
        points = [
            TimeSeriesPoint(date=datetime(2024, 6, 1), value=80.0, label="Jun-24"),
            TimeSeriesPoint(date=datetime(2024, 9, 1), value=100.0, label="Sep-24"),
            TimeSeriesPoint(
                date=datetime(2023, 12, 1), value=50.0, label="Dec-23"
            ),  # Only month for 2023
        ]
        result = filter_year_end_only_points(points, "ebitda")

        # 2023 December should be filtered (only month), 2024 months kept
        assert len(result) == 2
        assert not any(p.date.year == 2023 for p in result)
        # 2024 points should be preserved
        result_years = {p.date.year for p in result}
        assert result_years == {2024}

    def test_multiple_december_only_years_filtered(self) -> None:
        """Multiple years with only December data should all be filtered."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 3, 1), value=100.0, label="Mar-24"),
            TimeSeriesPoint(date=datetime(2024, 6, 1), value=110.0, label="Jun-24"),
            TimeSeriesPoint(
                date=datetime(2023, 12, 1), value=50.0, label="Dec-23"
            ),  # Only for 2023
            TimeSeriesPoint(
                date=datetime(2022, 12, 1), value=45.0, label="Dec-22"
            ),  # Only for 2022
        ]
        result = filter_year_end_only_points(points, "revenue")

        # Both 2022 and 2023 December-only years should be filtered
        assert len(result) == 2
        result_years = {p.date.year for p in result}
        assert result_years == {2024}

    def test_empty_list_returns_empty(self) -> None:
        """Empty input should return empty output."""
        result = filter_year_end_only_points([], "test_metric")
        assert result == []

    def test_single_december_point_filtered(self) -> None:
        """Single December point should be filtered as it's year-end only.

        NOTE: Exception - if the single December is the MOST RECENT year,
        it will be PRESERVED for forecasting value. See next test.
        """
        # 2023 December only, but 2024 data exists -> 2023 can be filtered
        points = [
            TimeSeriesPoint(date=datetime(2023, 12, 1), value=100.0, label="Dec-23"),
            TimeSeriesPoint(date=datetime(2024, 6, 1), value=110.0, label="Jun-24"),
        ]
        result = filter_year_end_only_points(points, "test_metric")

        # 2023 December-only should be filtered, 2024 preserved
        assert len(result) == 1
        assert result[0].date.year == 2024

    def test_most_recent_december_only_year_preserved(self) -> None:
        """Most recent year with only December data should be PRESERVED.

        Issue Fix: December 2025 data was being filtered incorrectly.
        The most recent year's data is valuable for forecasting even if
        only December exists (common pattern for latest financial reports).
        """
        points = [
            TimeSeriesPoint(date=datetime(2024, 6, 1), value=100.0, label="Jun-24"),
            TimeSeriesPoint(date=datetime(2024, 9, 1), value=110.0, label="Sep-24"),
            TimeSeriesPoint(
                date=datetime(2025, 12, 1), value=130.0, label="Dec-25"
            ),  # Most recent, Dec-only
        ]
        result = filter_year_end_only_points(points, "ebitda")

        # 2025 December should be PRESERVED (most recent year exception)
        assert len(result) == 3
        assert any(p.date.year == 2025 and p.date.month == 12 for p in result)
        # All original points should be kept
        result_dates = {(p.date.year, p.date.month) for p in result}
        assert result_dates == {(2024, 6), (2024, 9), (2025, 12)}

    def test_single_non_december_point_preserved(self) -> None:
        """Single non-December point should be preserved."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 6, 1), value=100.0, label="Jun-24"),
        ]
        result = filter_year_end_only_points(points, "test_metric")

        assert len(result) == 1
        assert result[0].date.month == 6

    def test_full_year_preserved(self) -> None:
        """A year with multiple months including December should be fully preserved."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0, label="Jan-24"),
            TimeSeriesPoint(date=datetime(2024, 6, 1), value=120.0, label="Jun-24"),
            TimeSeriesPoint(date=datetime(2024, 12, 1), value=150.0, label="Dec-24"),
        ]
        result = filter_year_end_only_points(points, "test_metric")

        assert len(result) == 3
        result_months = {p.date.month for p in result}
        assert result_months == {1, 6, 12}

    def test_mixed_years_correct_filtering(self) -> None:
        """Complex scenario: some years December-only, some have multiple months."""
        points = [
            # 2022: December only - should be filtered
            TimeSeriesPoint(date=datetime(2022, 12, 1), value=40.0, label="Dec-22"),
            # 2023: Multiple months including December - should be preserved
            TimeSeriesPoint(date=datetime(2023, 6, 1), value=60.0, label="Jun-23"),
            TimeSeriesPoint(date=datetime(2023, 12, 1), value=80.0, label="Dec-23"),
            # 2024: Multiple months - should be preserved
            TimeSeriesPoint(date=datetime(2024, 3, 1), value=90.0, label="Mar-24"),
            TimeSeriesPoint(date=datetime(2024, 9, 1), value=110.0, label="Sep-24"),
            TimeSeriesPoint(date=datetime(2024, 12, 1), value=130.0, label="Dec-24"),
            # 2025: Multiple months (the bug fix scenario) - should be preserved
            TimeSeriesPoint(date=datetime(2025, 10, 1), value=140.0, label="Oct-25"),
            TimeSeriesPoint(date=datetime(2025, 11, 1), value=145.0, label="Nov-25"),
            TimeSeriesPoint(date=datetime(2025, 12, 1), value=150.0, label="Dec-25"),
        ]
        result = filter_year_end_only_points(points, "ebitda")

        # 2022 should be filtered (December only)
        # 2023, 2024, 2025 should be preserved (multiple months)
        assert len(result) == 8
        result_years = {p.date.year for p in result}
        assert result_years == {2023, 2024, 2025}
        # Verify December 2025 is present (the bug fix scenario)
        assert any(p.date.year == 2025 and p.date.month == 12 for p in result)

    def test_logging_on_filter(self, caplog: pytest.LogCaptureFixture) -> None:
        """Filtered year-end points should be logged for debugging."""
        import logging

        caplog.set_level(logging.WARNING)

        points = [
            TimeSeriesPoint(date=datetime(2024, 6, 1), value=100.0, label="Jun-24"),
            TimeSeriesPoint(
                date=datetime(2023, 12, 1), value=50.0, label="Dec-23"
            ),  # Will be filtered
        ]
        filter_year_end_only_points(points, "test_metric")

        # Check that filtering was logged
        warning_logs = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warning_logs) >= 1
        log_messages = " ".join(r.message for r in warning_logs)
        assert "year-end" in log_messages.lower() or "filtered" in log_messages.lower()
