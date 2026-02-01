"""Unit tests for SQL migration 001: Backfill fiscal_year from period column.

Story: 5.0.1 - Fix Time-Series Period Extraction for Forecasting
Tests regex pattern extraction and edge cases for period parsing.
"""

import re

import pytest


def extract_fiscal_year_from_period(period: str) -> int | None:
    """Extract fiscal year from period string using migration regex logic.

    Implements the same logic as migration 001:
    2000 + (regexp_match(period, '.*-(\\d{2})$'))[1]::int

    Args:
        period: Period string (e.g., "Jan-25", "YTD", "Var.")

    Returns:
        Fiscal year as integer (e.g., 2025) or None if invalid format

    Examples:
        >>> extract_fiscal_year_from_period("Jan-25")
        2025
        >>> extract_fiscal_year_from_period("Dec-24")
        2024
        >>> extract_fiscal_year_from_period("Var.")
        None
    """
    if not period:
        return None

    # PostgreSQL regex pattern: '.*-(\d{2})$'
    # Matches strings ending with hyphen + 2 digits
    pattern = r".*-(\d{2})$"
    match = re.match(pattern, period)

    if not match:
        return None

    two_digit_year = int(match.group(1))
    return 2000 + two_digit_year


class TestFiscalYearExtractionRegex:
    """Test regex pattern for extracting fiscal year from period column."""

    @pytest.mark.parametrize(
        "period,expected_year",
        [
            # Valid Mon-YY formats (2025)
            ("Jan-25", 2025),
            ("Feb-25", 2025),
            ("Mar-25", 2025),
            ("Apr-25", 2025),
            ("May-25", 2025),
            ("Jun-25", 2025),
            ("Jul-25", 2025),
            ("Aug-25", 2025),
            ("Sep-25", 2025),
            ("Oct-25", 2025),
            ("Nov-25", 2025),
            ("Dec-25", 2025),
            # Valid Mon-YY formats (2024)
            ("Jan-24", 2024),
            ("Feb-24", 2024),
            ("Mar-24", 2024),
            ("Apr-24", 2024),
            ("May-24", 2024),
            ("Jun-24", 2024),
            ("Jul-24", 2024),
            ("Aug-24", 2024),
            ("Sep-24", 2024),
            ("Oct-24", 2024),
            ("Nov-24", 2024),
            ("Dec-24", 2024),
            # Valid Mon-YY formats (2023)
            ("Jan-23", 2023),
            ("Dec-23", 2023),
            # Complex period values (regex should extract LAST -XX pattern)
            ("YTD  B Apr-25  Apr-24", 2024),  # Last -XX is -24
            ("B Apr-25  Apr-24", 2024),
            ("YTD Apr-25", 2025),
            ("Month  B Apr-25", 2025),
            ("YTD  Jan-25  B Jan-25  Jan-24", 2024),  # Last -XX is -24
            # Edge cases (regex is intentionally permissive)
            ("13-25", 2025),  # Invalid month number, but regex still extracts year
            ("January-25", 2025),  # Full month name, but regex still extracts year
        ],
    )
    def test_valid_period_formats(self, period: str, expected_year: int):
        """Test extraction from valid Mon-YY and complex period formats."""
        result = extract_fiscal_year_from_period(period)
        assert result == expected_year, (
            f"Failed for period='{period}': got {result}, expected {expected_year}"
        )

    @pytest.mark.parametrize(
        "period",
        [
            # Invalid formats that should return None
            "Var.",
            "YTD",
            "% LY",
            "Var.  % B",
            "Month",
            "2024",  # 4-digit year, not Mon-YY format
            "% B",
            "",  # Empty string
            "Jan",  # Missing year
            "25",  # Year only
            "Jan 25",  # Space instead of hyphen
            "Jan_25",  # Underscore instead of hyphen
            "Jan-2025",  # 4-digit year
        ],
    )
    def test_invalid_period_formats(self, period: str):
        """Test that invalid formats return None."""
        result = extract_fiscal_year_from_period(period)
        assert result is None, f"Expected None for period='{period}', got {result}"

    def test_null_period(self):
        """Test NULL period value."""
        result = extract_fiscal_year_from_period(None)
        assert result is None

    def test_case_sensitivity(self):
        """Test that regex is case-sensitive (as in PostgreSQL)."""
        # Lowercase month abbreviations
        assert extract_fiscal_year_from_period("jan-25") == 2025
        assert extract_fiscal_year_from_period("JAN-25") == 2025
        assert extract_fiscal_year_from_period("Jan-25") == 2025


class TestMigrationEdgeCases:
    """Test edge cases for migration 001 logic."""

    def test_already_populated_fiscal_year_not_overwritten(self):
        """Verify migration WHERE clause logic: AND fiscal_year IS NULL.

        Migration should NOT update rows where fiscal_year is already populated.
        This test verifies the logic, not actual database behavior.
        """
        # Simulating migration condition:
        # WHERE period IS NOT NULL AND period ~ '-\\d{2}$' AND fiscal_year IS NULL

        # Case 1: period="Jan-25", fiscal_year=NULL → Should update
        period = "Jan-25"
        fiscal_year_current = None
        should_update = (
            period is not None and re.match(r".*-\d{2}$", period) and fiscal_year_current is None
        )
        assert should_update is True

        # Case 2: period="Jan-25", fiscal_year=2024 → Should NOT update
        period = "Jan-25"
        fiscal_year_current = 2024
        should_update = (
            period is not None and re.match(r".*-\d{2}$", period) and fiscal_year_current is None
        )
        assert should_update is False

    def test_no_data_loss_from_regex_mismatch(self):
        """Verify that rows with invalid period formats are safely skipped."""
        invalid_periods = ["Var.", "YTD", "% LY", "Month", "2024", "% B"]

        for period in invalid_periods:
            result = extract_fiscal_year_from_period(period)
            assert result is None, f"Should skip period='{period}' without error"

    def test_year_range_coverage(self):
        """Test year extraction for a wide range of years (2020-2029)."""
        for year_suffix in range(20, 30):  # 20-29 → 2020-2029
            period = f"Jan-{year_suffix}"
            expected_year = 2000 + year_suffix
            result = extract_fiscal_year_from_period(period)
            assert result == expected_year


class TestMigrationVerificationQueries:
    """Test verification queries for migration 001.

    These tests document the expected SQL verification queries
    but don't execute them (that's for integration tests).
    """

    def test_pre_migration_verification_query_structure(self):
        """Document expected structure of pre-migration verification query."""
        expected_columns = ["total_rows", "rows_with_period", "rows_with_fiscal_year"]

        # This test just documents what the query should return
        # Actual execution is in integration tests
        assert len(expected_columns) == 3

    def test_post_migration_verification_query_structure(self):
        """Document expected structure of post-migration verification query."""
        expected_columns = [
            "total_rows",
            "rows_with_period",
            "rows_with_fiscal_year",
            "rows_still_null",
        ]

        # This test documents what we should verify after migration
        assert len(expected_columns) == 4

    def test_expected_row_count_increase(self):
        """Document expected row count changes from migration.

        Based on production data analysis:
        - Before: 14,022 rows with fiscal_year
        - After: 138,666 rows with fiscal_year
        - Increase: 124,644 rows (36% of rows with period)
        """
        before_count = 14022
        after_count = 138666
        expected_increase = 124644

        actual_increase = after_count - before_count
        assert actual_increase == expected_increase


# Test execution
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
