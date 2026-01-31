"""Unit tests for period classification module.

EBITDA Data Quality Fix (2026-01-30): Comprehensive tests for period classification
to ensure budget data is properly excluded and YTD/monthly data is correctly classified.
"""

import pytest

from raglite.forecasting.timeseries.period_classification import (
    ClassificationReport,
    ClassifiedPeriod,
    PeriodType,
    classify_period,
    generate_classification_report,
    normalize_classified_period,
    validate_period_homogeneity,
)


class TestClassifyPeriod:
    """Tests for classify_period function."""

    # MONTHLY_ACTUAL tests
    @pytest.mark.parametrize(
        "period,expected_normalized",
        [
            ("Dec-21", "Dec-21"),
            ("Jan-25", "Jan-25"),
            ("Feb-24", "Feb-24"),
            ("Mar-23", "Mar-23"),
            ("Apr-22", "Apr-22"),
            ("May-21", "May-21"),
            ("Jun-20", "Jun-20"),
            ("Jul-19", "Jul-19"),
            ("Aug-18", "Aug-18"),
            ("Sep-17", "Sep-17"),
            ("Oct-16", "Oct-16"),
            ("Nov-15", "Nov-15"),
        ],
    )
    def test_monthly_actual_english(self, period: str, expected_normalized: str) -> None:
        """Test classification of standard English monthly periods."""
        result = classify_period(period)
        assert result.period_type == PeriodType.MONTHLY_ACTUAL
        assert result.normalized == expected_normalized
        assert result.is_usable is True

    @pytest.mark.parametrize(
        "period,expected_normalized",
        [
            ("Dez-21", "Dec-21"),  # Portuguese December
            ("Fev-24", "Feb-24"),  # Portuguese February
            ("Abr-23", "Apr-23"),  # Portuguese April
            ("Mai-22", "May-22"),  # Portuguese May
            ("Ago-21", "Aug-21"),  # Portuguese August
            ("Set-20", "Sep-20"),  # Portuguese September
            ("Out-19", "Oct-19"),  # Portuguese October
        ],
    )
    def test_monthly_actual_portuguese(self, period: str, expected_normalized: str) -> None:
        """Test classification of Portuguese monthly periods."""
        result = classify_period(period)
        assert result.period_type == PeriodType.MONTHLY_ACTUAL
        assert result.normalized == expected_normalized
        assert result.is_usable is True

    @pytest.mark.parametrize(
        "period,expected_normalized",
        [
            ("Dec-2017", "Dec-17"),  # 4-digit year
            ("Jan-2025", "Jan-25"),
            ("Dez-2021", "Dec-21"),  # Portuguese + 4-digit year
        ],
    )
    def test_monthly_actual_4digit_year(self, period: str, expected_normalized: str) -> None:
        """Test classification of monthly periods with 4-digit years."""
        result = classify_period(period)
        assert result.period_type == PeriodType.MONTHLY_ACTUAL
        assert result.normalized == expected_normalized
        assert result.is_usable is True

    # YTD_ACTUAL tests
    @pytest.mark.parametrize(
        "period,expected_normalized",
        [
            ("YTD Dec-21", "Dec-21"),
            ("YTD Jan-25", "Jan-25"),
            ("YTD  Sep-25", "Sep-25"),  # double space
            ("YTD Jun-24", "Jun-24"),
        ],
    )
    def test_ytd_actual(self, period: str, expected_normalized: str) -> None:
        """Test classification of YTD actual periods."""
        result = classify_period(period)
        assert result.period_type == PeriodType.YTD_ACTUAL
        assert result.normalized == expected_normalized
        assert result.is_usable is True

    @pytest.mark.parametrize(
        "period,expected_normalized",
        [
            ("YTD Dez-21", "Dec-21"),  # Portuguese
            ("YTD Fev-24", "Feb-24"),
        ],
    )
    def test_ytd_actual_portuguese(self, period: str, expected_normalized: str) -> None:
        """Test classification of YTD periods with Portuguese months."""
        result = classify_period(period)
        assert result.period_type == PeriodType.YTD_ACTUAL
        assert result.normalized == expected_normalized
        assert result.is_usable is True

    # BUDGET tests (excluded)
    @pytest.mark.parametrize(
        "period",
        [
            "B Dec-21",
            "B Jan-25",
            "B  Apr-25",  # double space
            "Dec-21 B",
            "Jan B 25",  # B in middle
        ],
    )
    def test_budget_excluded(self, period: str) -> None:
        """Test that budget periods are excluded."""
        result = classify_period(period)
        assert result.period_type == PeriodType.BUDGET
        assert result.normalized is None
        assert result.is_usable is False

    # YTD_BUDGET tests (excluded)
    @pytest.mark.parametrize(
        "period",
        [
            "YTD B Dec-21",
            "YTD B Jan-25",
            "YTD  B Sep-25",  # double space
        ],
    )
    def test_ytd_budget_excluded(self, period: str) -> None:
        """Test that YTD budget periods are excluded."""
        result = classify_period(period)
        assert result.period_type == PeriodType.YTD_BUDGET
        assert result.normalized is None
        assert result.is_usable is False

    # UNKNOWN tests (excluded)
    @pytest.mark.parametrize(
        "period",
        [
            "",
            "   ",  # whitespace only
            "N/A",
            "None",
            "2017 P",  # year with suffix
            "2017",  # year only
            "invalid",
        ],
    )
    def test_unknown_excluded(self, period: str) -> None:
        """Test that unknown periods are excluded."""
        result = classify_period(period)
        assert result.period_type == PeriodType.UNKNOWN
        assert result.normalized is None
        assert result.is_usable is False

    def test_none_period(self) -> None:
        """Test that None period is classified as UNKNOWN."""
        result = classify_period(None)
        assert result.period_type == PeriodType.UNKNOWN
        assert result.normalized is None
        assert result.is_usable is False


class TestNormalizeClassifiedPeriod:
    """Tests for normalize_classified_period convenience function."""

    def test_usable_period(self) -> None:
        """Test normalization of usable period."""
        assert normalize_classified_period("Dec-21") == "Dec-21"
        assert normalize_classified_period("YTD Dec-21") == "Dec-21"
        assert normalize_classified_period("Dez-21") == "Dec-21"

    def test_excluded_period(self) -> None:
        """Test normalization of excluded period returns None."""
        assert normalize_classified_period("B Dec-21") is None
        assert normalize_classified_period("YTD B Dec-21") is None
        assert normalize_classified_period(None) is None
        assert normalize_classified_period("N/A") is None


class TestGenerateClassificationReport:
    """Tests for generate_classification_report function."""

    def test_empty_list(self) -> None:
        """Test report generation with empty list."""
        report = generate_classification_report([])
        assert report.total_records == 0
        assert report.usable_records == 0
        assert report.usability_rate == 0.0

    def test_all_monthly_actual(self) -> None:
        """Test report with all monthly actual periods."""
        periods = ["Dec-21", "Jan-22", "Feb-22"]
        report = generate_classification_report(periods)
        assert report.total_records == 3
        assert report.usable_records == 3
        assert report.monthly_actual_count == 3
        assert report.ytd_actual_count == 0
        assert report.budget_count == 0
        assert report.usability_rate == 100.0

    def test_mixed_periods(self) -> None:
        """Test report with mixed period types."""
        periods = [
            "Dec-21",  # MONTHLY_ACTUAL
            "YTD Jan-22",  # YTD_ACTUAL
            "B Feb-22",  # BUDGET
            "YTD B Mar-22",  # YTD_BUDGET
            "N/A",  # UNKNOWN
        ]
        report = generate_classification_report(periods)
        assert report.total_records == 5
        assert report.usable_records == 2
        assert report.monthly_actual_count == 1
        assert report.ytd_actual_count == 1
        assert report.budget_count == 1
        assert report.ytd_budget_count == 1
        assert report.unknown_count == 1
        assert report.usability_rate == 40.0

    def test_exclusion_breakdown(self) -> None:
        """Test exclusion breakdown property."""
        periods = ["B Dec-21", "YTD B Jan-22", "N/A"]
        report = generate_classification_report(periods)
        breakdown = report.exclusion_breakdown
        assert breakdown["budget"] == 1
        assert breakdown["ytd_budget"] == 1
        assert breakdown["unknown"] == 1


class TestValidatePeriodHomogeneity:
    """Tests for validate_period_homogeneity function."""

    def test_empty_list(self) -> None:
        """Test homogeneity with no usable periods."""
        periods = [classify_period("B Dec-21"), classify_period("N/A")]
        is_homogeneous, info = validate_period_homogeneity(periods)
        assert is_homogeneous is True
        assert info == "no_usable_periods"

    def test_all_monthly_actual(self) -> None:
        """Test homogeneity with all monthly actual."""
        periods = [classify_period(p) for p in ["Dec-21", "Jan-22", "Feb-22"]]
        is_homogeneous, info = validate_period_homogeneity(periods)
        assert is_homogeneous is True
        assert info == "monthly_actual"

    def test_all_ytd_actual(self) -> None:
        """Test homogeneity with all YTD actual."""
        periods = [classify_period(p) for p in ["YTD Dec-21", "YTD Jan-22", "YTD Feb-22"]]
        is_homogeneous, info = validate_period_homogeneity(periods)
        assert is_homogeneous is True
        assert info == "ytd_actual"

    def test_mixed_with_monthly_dominant(self) -> None:
        """Test mixing with monthly as dominant type."""
        # 3 monthly, 1 YTD = 75% monthly
        periods = [
            classify_period("Dec-21"),
            classify_period("Jan-22"),
            classify_period("Feb-22"),
            classify_period("YTD Mar-22"),
        ]
        is_homogeneous, info = validate_period_homogeneity(periods)
        assert is_homogeneous is False
        assert "monthly_actual" in info
        assert "75%" in info or "3 monthly" in info

    def test_mixed_with_ytd_dominant(self) -> None:
        """Test mixing with YTD as dominant type."""
        # 1 monthly, 3 YTD = 75% YTD
        periods = [
            classify_period("Dec-21"),
            classify_period("YTD Jan-22"),
            classify_period("YTD Feb-22"),
            classify_period("YTD Mar-22"),
        ]
        is_homogeneous, info = validate_period_homogeneity(periods)
        assert is_homogeneous is False
        assert "ytd_actual" in info

    def test_mixed_evenly(self) -> None:
        """Test mixing with even split (neither dominant)."""
        periods = [
            classify_period("Dec-21"),
            classify_period("Jan-22"),
            classify_period("YTD Feb-22"),
            classify_period("YTD Mar-22"),
        ]
        is_homogeneous, info = validate_period_homogeneity(periods)
        assert is_homogeneous is False
        assert "mixed" in info


class TestClassifiedPeriodDataclass:
    """Tests for ClassifiedPeriod dataclass."""

    def test_usable_period(self) -> None:
        """Test ClassifiedPeriod for usable period."""
        cp = ClassifiedPeriod(
            original="Dec-21",
            period_type=PeriodType.MONTHLY_ACTUAL,
            normalized="Dec-21",
            is_usable=True,
        )
        assert cp.original == "Dec-21"
        assert cp.period_type == PeriodType.MONTHLY_ACTUAL
        assert cp.normalized == "Dec-21"
        assert cp.is_usable is True

    def test_excluded_period(self) -> None:
        """Test ClassifiedPeriod for excluded period."""
        cp = ClassifiedPeriod(
            original="B Dec-21",
            period_type=PeriodType.BUDGET,
            normalized=None,
            is_usable=False,
        )
        assert cp.original == "B Dec-21"
        assert cp.period_type == PeriodType.BUDGET
        assert cp.normalized is None
        assert cp.is_usable is False


class TestClassificationReportProperties:
    """Tests for ClassificationReport dataclass properties."""

    def test_usability_rate_zero_records(self) -> None:
        """Test usability rate with zero total records."""
        report = ClassificationReport(
            total_records=0,
            usable_records=0,
            monthly_actual_count=0,
            ytd_actual_count=0,
            budget_count=0,
            ytd_budget_count=0,
            unknown_count=0,
        )
        assert report.usability_rate == 0.0

    def test_usability_rate_calculation(self) -> None:
        """Test usability rate calculation."""
        report = ClassificationReport(
            total_records=10,
            usable_records=6,
            monthly_actual_count=4,
            ytd_actual_count=2,
            budget_count=2,
            ytd_budget_count=1,
            unknown_count=1,
        )
        assert report.usability_rate == 60.0

    def test_exclusion_breakdown_property(self) -> None:
        """Test exclusion breakdown dictionary."""
        report = ClassificationReport(
            total_records=10,
            usable_records=5,
            monthly_actual_count=3,
            ytd_actual_count=2,
            budget_count=2,
            ytd_budget_count=2,
            unknown_count=1,
        )
        breakdown = report.exclusion_breakdown
        assert breakdown == {
            "budget": 2,
            "ytd_budget": 2,
            "unknown": 1,
        }
