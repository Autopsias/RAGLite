"""Unit tests for period format normalization (Story 2.15 AC2).

Tests period mapping between query language (Q3 2025, August 2025) and
database formats (Aug-25, Aug-25 YTD).
"""

import pytest

from raglite.retrieval.period_normalizer import (
    detect_period_in_query,
    normalize_month,
    normalize_period,
)


class TestNormalizePeriod:
    """Tests for normalize_period function."""

    @pytest.mark.priority("P2")
    def test_normalize_period_q1_to_months(self):
        """Test Q1 quarter normalization to month variants."""
        result = normalize_period("Q1 2025")
        expected = ["Jan-25", "Feb-25", "Mar-25", "Jan-25 YTD", "Mar-25 YTD", "Q1-25"]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_q2_to_months(self):
        """Test Q2 quarter normalization to month variants."""
        result = normalize_period("Q2 2025")
        expected = ["Apr-25", "May-25", "Jun-25", "Apr-25 YTD", "Jun-25 YTD", "Q2-25"]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_q3_to_months(self):
        """Test Q3 quarter normalization to month variants (CRITICAL for Story 2.15)."""
        result = normalize_period("Q3 2025")
        expected = ["Jul-25", "Aug-25", "Sep-25", "Jul-25 YTD", "Aug-25 YTD", "Q3-25"]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_q4_to_months(self):
        """Test Q4 quarter normalization to month variants."""
        result = normalize_period("Q4 2025")
        expected = ["Oct-25", "Nov-25", "Dec-25", "Oct-25 YTD", "Dec-25 YTD", "Q4-25"]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_q3_short_year(self):
        """Test Q3 with 2-digit year (Q3 25)."""
        result = normalize_period("Q3 25")
        expected = ["Jul-25", "Aug-25", "Sep-25", "Jul-25 YTD", "Aug-25 YTD", "Q3-25"]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_month_full_year(self):
        """Test month-year format with full year (August 2025)."""
        result = normalize_period("August 2025")
        expected = ["Aug-25", "Aug-25 YTD"]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_month_short_year(self):
        """Test month-year format with 2-digit year (Aug-25)."""
        result = normalize_period("Aug-25")
        expected = ["Aug-25", "Aug-25 YTD"]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_month_abbrev(self):
        """Test month abbreviation normalization (Sep 2025)."""
        result = normalize_period("Sep 2025")
        expected = ["Sep-25", "Sep-25 YTD"]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_half_year_h1(self):
        """Test H1 half-year normalization."""
        result = normalize_period("H1 2025")
        expected = [
            "Jan-25 YTD",
            "Feb-25 YTD",
            "Mar-25 YTD",
            "Apr-25 YTD",
            "May-25 YTD",
            "Jun-25 YTD",
        ]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_half_year_h2(self):
        """Test H2 half-year normalization."""
        result = normalize_period("H2 2025")
        expected = [
            "Jul-25 YTD",
            "Aug-25 YTD",
            "Sep-25 YTD",
            "Oct-25 YTD",
            "Nov-25 YTD",
            "Dec-25 YTD",
        ]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_fiscal_year(self):
        """Test fiscal year normalization (FY2025)."""
        result = normalize_period("FY2025")
        expected = ["Jan-25 YTD", "Dec-25 YTD", "2025"]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_fiscal_year_spelled_out(self):
        """Test 'fiscal year 2025' normalization."""
        result = normalize_period("fiscal year 2025")
        expected = ["Jan-25 YTD", "Dec-25 YTD", "2025"]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_full_year(self):
        """Test full year normalization (2025)."""
        result = normalize_period("2025")
        expected = ["Jan-25 YTD", "Dec-25 YTD", "2025"]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_unknown_format(self):
        """Test unknown format returns as-is."""
        result = normalize_period("Unknown Period")
        expected = ["Unknown Period"]
        assert result == expected

    @pytest.mark.priority("P2")
    def test_normalize_period_empty_string(self):
        """Test empty string returns as-is."""
        result = normalize_period("")
        expected = [""]
        assert result == expected


class TestNormalizeMonth:
    """Tests for normalize_month function."""

    @pytest.mark.priority("P2")
    def test_normalize_month_january_full(self):
        """Test full month name normalization (January → Jan)."""
        assert normalize_month("January") == "Jan"

    @pytest.mark.priority("P2")
    def test_normalize_month_january_abbrev(self):
        """Test abbreviated month normalization (Jan → Jan)."""
        assert normalize_month("Jan") == "Jan"

    @pytest.mark.priority("P2")
    def test_normalize_month_august_lowercase(self):
        """Test lowercase month normalization (august → Aug)."""
        assert normalize_month("august") == "Aug"

    @pytest.mark.priority("P2")
    def test_normalize_month_december(self):
        """Test December normalization."""
        assert normalize_month("December") == "Dec"

    @pytest.mark.priority("P2")
    def test_normalize_month_may(self):
        """Test May normalization (no abbreviation)."""
        assert normalize_month("May") == "May"

    @pytest.mark.priority("P2")
    def test_normalize_month_unknown(self):
        """Test unknown month returns as-is."""
        assert normalize_month("Unknown") == "Unknown"


class TestDetectPeriodInQuery:
    """Tests for detect_period_in_query function."""

    @pytest.mark.priority("P2")
    def test_detect_period_q3_2025(self):
        """Test Q3 2025 detection in query."""
        query = "What is the EBITDA for Q3 2025?"
        result = detect_period_in_query(query)
        assert result == "Q3 2025"

    @pytest.mark.priority("P2")
    def test_detect_period_q2_short_year(self):
        """Test Q2 25 detection (short year)."""
        query = "Show me Q2 25 results"
        result = detect_period_in_query(query)
        assert result == "Q2 2025"

    @pytest.mark.priority("P2")
    def test_detect_period_august_2025(self):
        """Test 'August 2025' detection."""
        query = "Portugal variable costs in August 2025"
        result = detect_period_in_query(query)
        assert result == "August 2025"

    @pytest.mark.priority("P2")
    def test_detect_period_aug_25(self):
        """Test 'Aug-25' database format detection."""
        query = "What is the value for Aug-25?"
        result = detect_period_in_query(query)
        assert result == "Aug-25"

    @pytest.mark.priority("P2")
    def test_detect_period_aug_25_ytd(self):
        """Test 'Aug-25 YTD' database format detection."""
        query = "Show me Aug-25 YTD data"
        result = detect_period_in_query(query)
        assert result == "Aug-25 YTD"

    @pytest.mark.priority("P2")
    def test_detect_period_fiscal_year(self):
        """Test fiscal year detection (FY2025)."""
        query = "Show me fiscal year 2025 results"
        result = detect_period_in_query(query)
        assert result == "FY2025"

    @pytest.mark.priority("P2")
    def test_detect_period_fy_short(self):
        """Test FY abbreviation detection."""
        query = "FY 2025 summary"
        result = detect_period_in_query(query)
        assert result == "FY2025"

    @pytest.mark.priority("P2")
    def test_detect_period_half_year_h1(self):
        """Test H1 half-year detection."""
        query = "What is the H1 2025 performance?"
        result = detect_period_in_query(query)
        assert result == "H1 2025"

    @pytest.mark.priority("P2")
    def test_detect_period_half_year_h2(self):
        """Test H2 half-year detection."""
        query = "Show me H2 25 metrics"
        result = detect_period_in_query(query)
        assert result == "H2 2025"

    @pytest.mark.priority("P2")
    def test_detect_period_no_period(self):
        """Test query with no period returns empty string."""
        query = "What is the EBITDA?"
        result = detect_period_in_query(query)
        assert result == ""

    @pytest.mark.priority("P2")
    def test_detect_period_case_insensitive(self):
        """Test case-insensitive quarter detection (q3 2025)."""
        query = "What is the ebitda for q3 2025?"
        result = detect_period_in_query(query)
        assert result == "Q3 2025"

    @pytest.mark.priority("P2")
    def test_detect_period_multiple_periods_first_match(self):
        """Test multiple periods - should detect first match."""
        query = "Compare Q2 2025 vs Q3 2025"
        result = detect_period_in_query(query)
        assert result == "Q2 2025"


class TestPeriodNormalizerIntegration:
    """Integration tests for period normalizer workflow."""

    @pytest.mark.priority("P2")
    def test_integration_q3_workflow(self):
        """Test complete Q3 2025 normalization workflow."""
        # 1. Detect period in query
        query = "What is the EBITDA for Q3 2025?"
        detected = detect_period_in_query(query)
        assert detected == "Q3 2025"

        # 2. Normalize to database variants
        variants = normalize_period(detected)
        assert "Aug-25" in variants
        assert "Aug-25 YTD" in variants
        assert "Jul-25" in variants
        assert "Sep-25" in variants

        # 3. Verify SQL IN clause can use these
        sql_fragment = f"period IN ({', '.join(repr(v) for v in variants)})"
        assert "period IN ('Jul-25', 'Aug-25', 'Sep-25'" in sql_fragment

    @pytest.mark.priority("P2")
    def test_integration_august_workflow(self):
        """Test complete August 2025 normalization workflow."""
        query = "Portugal costs in August 2025"
        detected = detect_period_in_query(query)
        assert detected == "August 2025"

        variants = normalize_period(detected)
        assert variants == ["Aug-25", "Aug-25 YTD"]

    @pytest.mark.priority("P2")
    def test_integration_no_period_workflow(self):
        """Test workflow when no period detected."""
        query = "What is the EBITDA?"
        detected = detect_period_in_query(query)
        assert detected == ""

        # Should handle empty string gracefully
        variants = normalize_period(detected) if detected else []
        assert variants == []
