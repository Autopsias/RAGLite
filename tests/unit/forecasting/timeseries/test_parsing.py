"""Unit tests for timeseries parsing module.

EBITDA Data Quality Fix (2026-01-30): Tests for Portuguese month support
and 4-digit year handling in parse_period_to_date.
"""

from datetime import datetime

import pytest

from raglite.forecasting.timeseries.parsing import (
    normalize_to_interval,
    parse_fiscal_date,
    parse_period_to_date,
)
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint


class TestParsePeriodToDate:
    """Tests for parse_period_to_date function."""

    # Standard English month abbreviations (2-digit year)
    @pytest.mark.parametrize(
        "period,expected_year,expected_month",
        [
            ("Jan-25", 2025, 1),
            ("Feb-24", 2024, 2),
            ("Mar-23", 2023, 3),
            ("Apr-22", 2022, 4),
            ("May-21", 2021, 5),
            ("Jun-20", 2020, 6),
            ("Jul-19", 2019, 7),
            ("Aug-18", 2018, 8),
            ("Sep-17", 2017, 9),
            ("Oct-16", 2016, 10),
            ("Nov-15", 2015, 11),
            ("Dec-14", 2014, 12),
        ],
    )
    def test_english_months_2digit_year(
        self, period: str, expected_year: int, expected_month: int
    ) -> None:
        """Test parsing of standard English month abbreviations with 2-digit years."""
        result = parse_period_to_date(period, fiscal_year=expected_year)
        assert result == datetime(expected_year, expected_month, 1)

    # Portuguese month abbreviations (EBITDA Data Quality Fix)
    @pytest.mark.parametrize(
        "period,expected_year,expected_month",
        [
            ("Fev-24", 2024, 2),  # Fevereiro
            ("Abr-23", 2023, 4),  # Abril
            ("Mai-22", 2022, 5),  # Maio
            ("Ago-21", 2021, 8),  # Agosto
            ("Set-20", 2020, 9),  # Setembro
            ("Out-19", 2019, 10),  # Outubro
            ("Dez-18", 2018, 12),  # Dezembro
        ],
    )
    def test_portuguese_months(self, period: str, expected_year: int, expected_month: int) -> None:
        """Test parsing of Portuguese month abbreviations."""
        result = parse_period_to_date(period, fiscal_year=expected_year)
        assert result == datetime(expected_year, expected_month, 1)

    # 4-digit year support (EBITDA Data Quality Fix)
    @pytest.mark.parametrize(
        "period,expected_year,expected_month",
        [
            ("Dec-2017", 2017, 12),
            ("Jan-2025", 2025, 1),
            ("Jul-2020", 2020, 7),
            ("Dec-2016", 2016, 12),
        ],
    )
    def test_4digit_year(self, period: str, expected_year: int, expected_month: int) -> None:
        """Test parsing of periods with 4-digit years."""
        result = parse_period_to_date(period, fiscal_year=expected_year)
        assert result == datetime(expected_year, expected_month, 1)

    # Combined: Portuguese month + 4-digit year
    @pytest.mark.parametrize(
        "period,expected_year,expected_month",
        [
            ("Dez-2017", 2017, 12),
            ("Fev-2024", 2024, 2),
            ("Ago-2021", 2021, 8),
        ],
    )
    def test_portuguese_months_4digit_year(
        self, period: str, expected_year: int, expected_month: int
    ) -> None:
        """Test parsing of Portuguese months with 4-digit years."""
        result = parse_period_to_date(period, fiscal_year=expected_year)
        assert result == datetime(expected_year, expected_month, 1)

    # Case insensitivity
    def test_case_variations(self) -> None:
        """Test that month abbreviations are case-insensitive."""
        # Lowercase
        assert parse_period_to_date("dec-21", 2021) == datetime(2021, 12, 1)
        # Uppercase
        assert parse_period_to_date("DEC-21", 2021) == datetime(2021, 12, 1)
        # Mixed
        assert parse_period_to_date("DeC-21", 2021) == datetime(2021, 12, 1)

    # Year extraction from period (bug fix verification)
    def test_year_extracted_from_period_not_fiscal_year(self) -> None:
        """Test that year is extracted from period suffix, not fiscal_year parameter."""
        # fiscal_year parameter should be ignored
        result = parse_period_to_date("Jan-25", fiscal_year=2020)
        assert result.year == 2025  # From period, not fiscal_year
        assert result.month == 1

    # Error cases - format errors
    @pytest.mark.parametrize(
        "invalid_period",
        [
            "",  # Empty
            "   ",  # Whitespace
            "Dec",  # No year
            "25",  # No month
            "12-25",  # Numeric month
            "Dec-2",  # 1-digit year
            "Dec-12345",  # 5-digit year
            "YTD Dec-21",  # YTD prefix (should be stripped before calling)
            "B Dec-21",  # Budget prefix
        ],
    )
    def test_invalid_format_raises_valueerror(self, invalid_period: str) -> None:
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError, match="Invalid period format"):
            parse_period_to_date(invalid_period, fiscal_year=2024)

    def test_full_month_name_raises_valueerror(self) -> None:
        """Test that full month names (not abbreviations) raise ValueError."""
        # "December-25" matches the regex but fails on month lookup
        with pytest.raises(ValueError, match="Invalid month abbreviation"):
            parse_period_to_date("December-25", fiscal_year=2025)

    def test_invalid_month_raises_valueerror(self) -> None:
        """Test that invalid month abbreviations raise ValueError."""
        with pytest.raises(ValueError, match="Invalid month abbreviation"):
            parse_period_to_date("Xyz-21", fiscal_year=2021)


class TestParseFiscalDate:
    """Tests for parse_fiscal_date function."""

    def test_fiscal_quarter(self) -> None:
        """Test parsing fiscal quarter formats."""
        # Q3 FY24 with July fiscal year start
        result = parse_fiscal_date("Q3 FY24")
        assert result.year == 2024
        assert result.month == 1  # Q3 is Jan-Mar for July FY

    def test_full_fiscal_year(self) -> None:
        """Test parsing full fiscal year formats."""
        result = parse_fiscal_date("FY24")
        assert result.year == 2023
        assert result.month == 7  # Start of FY24 (July 2023)

    def test_calendar_quarter(self) -> None:
        """Test parsing calendar quarter formats."""
        result = parse_fiscal_date("Q1 2024")
        assert result.year == 2024
        assert result.month == 1

    def test_standard_date_formats(self) -> None:
        """Test parsing standard date formats via dateutil fallback."""
        result = parse_fiscal_date("January 2024")
        assert result.year == 2024
        assert result.month == 1


class TestNormalizeToInterval:
    """Tests for normalize_to_interval function."""

    def test_monthly_normalization(self) -> None:
        """Test normalization to monthly intervals."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=100, label="Jan-24"),
            TimeSeriesPoint(date=datetime(2024, 1, 15), value=110, label="mid-Jan-24"),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=120, label="Feb-24"),
        ]
        data = TimeSeriesData(
            metric_name="test", points=points, interval="daily", source_documents=set()
        )
        normalized = normalize_to_interval(data, "monthly")
        assert len(normalized.points) == 2
        assert normalized.points[0].value == 105  # Avg of 100 and 110

    def test_quarterly_normalization(self) -> None:
        """Test normalization to quarterly intervals."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=100, label="Jan"),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=120, label="Feb"),
            TimeSeriesPoint(date=datetime(2024, 3, 1), value=140, label="Mar"),
        ]
        data = TimeSeriesData(
            metric_name="test", points=points, interval="monthly", source_documents=set()
        )
        normalized = normalize_to_interval(data, "quarterly")
        assert len(normalized.points) == 1
        assert normalized.points[0].value == 120  # Avg of 100, 120, 140

    def test_yearly_normalization(self) -> None:
        """Test normalization to yearly intervals."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=100, label="2024-01"),
            TimeSeriesPoint(date=datetime(2024, 6, 1), value=200, label="2024-06"),
        ]
        data = TimeSeriesData(
            metric_name="test", points=points, interval="monthly", source_documents=set()
        )
        normalized = normalize_to_interval(data, "yearly")
        assert len(normalized.points) == 1
        assert normalized.points[0].value == 150  # Avg of 100 and 200

    def test_empty_data(self) -> None:
        """Test normalization with empty data."""
        data = TimeSeriesData(
            metric_name="test", points=[], interval="daily", source_documents=set()
        )
        normalized = normalize_to_interval(data, "monthly")
        assert len(normalized.points) == 0

    def test_invalid_interval_raises(self) -> None:
        """Test that invalid interval raises ValueError."""
        data = TimeSeriesData(
            metric_name="test", points=[], interval="daily", source_documents=set()
        )
        with pytest.raises(ValueError, match="Unsupported interval"):
            normalize_to_interval(data, "weekly")
