"""Unit tests for time-series date and period parsing (Story 4.1).

Tests cover:
- AC4: Handles various date formats and fiscal period labels
- Story 5.0.1 AC5: Period string parsing to datetime (Mon-YY format)
"""

from datetime import datetime

import pytest

from raglite.forecasting.timeseries import (
    parse_fiscal_date,
    parse_period_to_date,
)


class TestParseFiscalDate:
    """Tests for parse_fiscal_date function (AC4)."""

    def test_fiscal_quarter_fy24_q3(self) -> None:
        """AC4: Parse 'Q3 FY24' -> January 2024 (fiscal Q3 = Jan-Mar)."""
        result = parse_fiscal_date("Q3 FY24")
        assert result == datetime(2024, 1, 1)

    def test_fiscal_quarter_fy24_q1(self) -> None:
        """AC4: Parse 'Q1 FY24' -> July 2023 (fiscal Q1 = Jul-Sep of previous year)."""
        result = parse_fiscal_date("Q1 FY24")
        assert result == datetime(2023, 7, 1)

    def test_fiscal_quarter_fy24_q2(self) -> None:
        """AC4: Parse 'Q2 FY24' -> October 2023 (fiscal Q2 = Oct-Dec of previous year)."""
        result = parse_fiscal_date("Q2 FY24")
        assert result == datetime(2023, 10, 1)

    def test_fiscal_quarter_fy24_q4(self) -> None:
        """AC4: Parse 'Q4 FY24' -> April 2024 (fiscal Q4 = Apr-Jun)."""
        result = parse_fiscal_date("Q4 FY24")
        assert result == datetime(2024, 4, 1)

    def test_fiscal_quarter_fy2024_format(self) -> None:
        """AC4: Parse 'FY2024 Q3' (reversed format)."""
        result = parse_fiscal_date("FY2024 Q3")
        assert result == datetime(2024, 1, 1)

    def test_fiscal_year_only(self) -> None:
        """AC4: Parse 'FY24' -> July 2023 (start of fiscal year)."""
        result = parse_fiscal_date("FY24")
        assert result == datetime(2023, 7, 1)

    def test_calendar_quarter_q3_2024(self) -> None:
        """AC4: Parse 'Q3 2024' (calendar quarter) -> July 2024."""
        result = parse_fiscal_date("Q3 2024")
        assert result == datetime(2024, 7, 1)

    def test_calendar_quarter_q1_2024(self) -> None:
        """AC4: Parse 'Q1 2024' (calendar quarter) -> January 2024."""
        result = parse_fiscal_date("Q1 2024")
        assert result == datetime(2024, 1, 1)

    def test_month_year_format_jan_2024(self) -> None:
        """AC4: Parse 'Jan 2024' -> January 2024."""
        result = parse_fiscal_date("Jan 2024")
        assert result.year == 2024
        assert result.month == 1

    def test_month_year_format_january_2024(self) -> None:
        """AC4: Parse 'January 2024' -> January 2024."""
        result = parse_fiscal_date("January 2024")
        assert result.year == 2024
        assert result.month == 1

    def test_iso_format_2024_01(self) -> None:
        """AC4: Parse '2024-01' -> January 2024."""
        result = parse_fiscal_date("2024-01")
        assert result.year == 2024
        assert result.month == 1

    def test_slash_format_1_2024(self) -> None:
        """AC4: Parse '1/2024' -> January 2024."""
        result = parse_fiscal_date("1/2024")
        assert result.year == 2024
        assert result.month == 1

    def test_full_iso_date(self) -> None:
        """AC4: Parse '2024-01-15' -> January 15, 2024."""
        result = parse_fiscal_date("2024-01-15")
        assert result == datetime(2024, 1, 15)

    def test_case_insensitive(self) -> None:
        """AC4: Parse handles case-insensitive input."""
        result = parse_fiscal_date("q3 fy24")
        assert result == datetime(2024, 1, 1)

    def test_whitespace_handling(self) -> None:
        """AC4: Parse handles leading/trailing whitespace."""
        result = parse_fiscal_date("  Q3 FY24  ")
        assert result == datetime(2024, 1, 1)

    def test_invalid_date_raises_error(self) -> None:
        """AC4: Invalid date string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse date"):
            parse_fiscal_date("not a date")


class TestParsePeriodToDate:
    """Test period string parsing to datetime (Mon-YY format) - Story 5.0.1 AC5."""

    @pytest.mark.parametrize(
        "period,fiscal_year,expected_month",
        [
            # All months in 2025
            ("Jan-25", 2025, 1),
            ("Feb-25", 2025, 2),
            ("Mar-25", 2025, 3),
            ("Apr-25", 2025, 4),
            ("May-25", 2025, 5),
            ("Jun-25", 2025, 6),
            ("Jul-25", 2025, 7),
            ("Aug-25", 2025, 8),
            ("Sep-25", 2025, 9),
            ("Oct-25", 2025, 10),
            ("Nov-25", 2025, 11),
            ("Dec-25", 2025, 12),
            # All months in 2024
            ("Jan-24", 2024, 1),
            ("Feb-24", 2024, 2),
            ("Mar-24", 2024, 3),
            ("Apr-24", 2024, 4),
            ("May-24", 2024, 5),
            ("Jun-24", 2024, 6),
            ("Jul-24", 2024, 7),
            ("Aug-24", 2024, 8),
            ("Sep-24", 2024, 9),
            ("Oct-24", 2024, 10),
            ("Nov-24", 2024, 11),
            ("Dec-24", 2024, 12),
        ],
    )
    def test_valid_period_formats_all_months(
        self, period: str, fiscal_year: int, expected_month: int
    ) -> None:
        """Test extraction from all valid Mon-YY month patterns."""
        result = parse_period_to_date(period, fiscal_year)

        assert result.year == fiscal_year
        assert result.month == expected_month
        assert result.day == 1  # Always first day of month
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_case_insensitivity(self) -> None:
        """Test that month abbreviations are case-insensitive."""
        test_cases = [
            ("jan-25", 2025, 1),
            ("JAN-25", 2025, 1),
            ("Jan-25", 2025, 1),
            ("jAn-25", 2025, 1),
        ]

        for period, fiscal_year, expected_month in test_cases:
            result = parse_period_to_date(period, fiscal_year)
            assert result.month == expected_month

    def test_whitespace_handling(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        result = parse_period_to_date("  Jan-25  ", 2025)
        assert result.month == 1
        assert result.year == 2025

    @pytest.mark.parametrize(
        "invalid_period",
        [
            "Var.",  # Non-date value
            "YTD",  # Non-date value
            "2024",  # Year only
            "Jan",  # Missing year
            "25",  # Year only
            "Jan 25",  # Space instead of hyphen
            "Jan_25",  # Underscore instead of hyphen
            "",  # Empty string
        ],
    )
    def test_invalid_period_formats(self, invalid_period: str) -> None:
        """Test that invalid period formats raise ValueError.

        Note: "Jan-2025" is now VALID (4-digit year support added for EBITDA data quality).
        """
        with pytest.raises(ValueError, match="Invalid period format"):
            parse_period_to_date(invalid_period, 2025)

    def test_invalid_month_abbreviation(self) -> None:
        """Test that unrecognized month abbreviations raise ValueError."""
        with pytest.raises(ValueError, match="Invalid month abbreviation"):
            parse_period_to_date("Xyz-25", 2025)
