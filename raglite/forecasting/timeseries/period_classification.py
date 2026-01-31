"""Period classification for timeseries extraction.

EBITDA Data Quality Fix (2026-01-30):
Classifies period formats to enable proper filtering of budget data from actuals,
and YTD data from monthly data, preventing mixing of incompatible data types.

Period Types:
- MONTHLY_ACTUAL: "Dec-21", "Jan-25" - valid for forecasting
- YTD_ACTUAL: "YTD Dec-21", "YTD Jun-24" - needs conversion to monthly
- BUDGET: "B Dec-21", "Dec-21 B" - EXCLUDED (not actuals)
- YTD_BUDGET: "YTD B Dec-21" - EXCLUDED (not actuals)
- UNKNOWN: empty, "N/A", malformed - EXCLUDED
"""

import re
from dataclasses import dataclass
from enum import Enum

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class PeriodType(Enum):
    """Classification of period formats in financial data.

    Used to filter and normalize periods before forecasting.
    Only MONTHLY_ACTUAL and YTD_ACTUAL are usable for forecasting.
    """

    MONTHLY_ACTUAL = "monthly_actual"  # "Dec-21", "Jan-25"
    YTD_ACTUAL = "ytd_actual"  # "YTD Dec-21", "YTD Jun-24"
    BUDGET = "budget"  # "B Dec-21", "Dec-21 B"
    YTD_BUDGET = "ytd_budget"  # "YTD B Dec-21"
    UNKNOWN = "unknown"  # Empty, N/A, malformed


@dataclass
class ClassifiedPeriod:
    """Result of period classification with normalized form."""

    original: str
    period_type: PeriodType
    normalized: str | None  # None for excluded types (BUDGET, YTD_BUDGET, UNKNOWN)
    is_usable: bool  # True for MONTHLY_ACTUAL and YTD_ACTUAL


# Portuguese to English month abbreviation mapping
PORTUGUESE_MONTH_MAP: dict[str, str] = {
    "Fev": "Feb",
    "Abr": "Apr",
    "Mai": "May",
    "Ago": "Aug",
    "Set": "Sep",
    "Out": "Oct",
    "Dez": "Dec",
}


def _normalize_month_abbreviation(month_abbrev: str) -> str:
    """Convert Portuguese month abbreviations to English.

    Args:
        month_abbrev: Month abbreviation (e.g., "Dez", "Dec")

    Returns:
        English month abbreviation (e.g., "Dec")
    """
    # Capitalize first letter for consistency
    month_cap = month_abbrev.capitalize()
    return PORTUGUESE_MONTH_MAP.get(month_cap, month_cap)


def _convert_4digit_year_to_2digit(year_str: str) -> str:
    """Convert 4-digit year to 2-digit format.

    Args:
        year_str: Year string (e.g., "2017", "25")

    Returns:
        2-digit year string (e.g., "17", "25")
    """
    if len(year_str) == 4:
        return year_str[2:]  # "2017" -> "17"
    return year_str


def classify_period(period: str | None) -> ClassifiedPeriod:
    """Classify a period string into its type.

    Classification order (checked first to last):
    1. Empty/null -> UNKNOWN
    2. "YTD B " prefix -> YTD_BUDGET (excluded)
    3. "B " prefix or " B " or " B" suffix -> BUDGET (excluded)
    4. "YTD " prefix with Mon-YY -> YTD_ACTUAL
    5. Plain Mon-YY format -> MONTHLY_ACTUAL
    6. Everything else -> UNKNOWN

    Args:
        period: Period string to classify (may be None)

    Returns:
        ClassifiedPeriod with type and normalized form

    Examples:
        >>> classify_period("Dec-21")
        ClassifiedPeriod(original="Dec-21", period_type=MONTHLY_ACTUAL, normalized="Dec-21", is_usable=True)
        >>> classify_period("B Dec-21")
        ClassifiedPeriod(original="B Dec-21", period_type=BUDGET, normalized=None, is_usable=False)
    """
    # Step 1: Handle empty/null
    if period is None or not period.strip():
        return ClassifiedPeriod(
            original=period or "",
            period_type=PeriodType.UNKNOWN,
            normalized=None,
            is_usable=False,
        )

    period = period.strip()

    # Step 2: Check for YTD Budget (e.g., "YTD B Dec-21", "YTD  B Sep-25")
    if re.match(r"^YTD\s+B\s", period, re.IGNORECASE):
        return ClassifiedPeriod(
            original=period,
            period_type=PeriodType.YTD_BUDGET,
            normalized=None,
            is_usable=False,
        )

    # Step 3: Check for Budget (e.g., "B Dec-21", "Dec-21 B", "B  Apr-25")
    if re.match(r"^B\s", period, re.IGNORECASE):
        return ClassifiedPeriod(
            original=period,
            period_type=PeriodType.BUDGET,
            normalized=None,
            is_usable=False,
        )
    if re.search(r"\sB\s", period, re.IGNORECASE):
        return ClassifiedPeriod(
            original=period,
            period_type=PeriodType.BUDGET,
            normalized=None,
            is_usable=False,
        )
    if re.search(r"\sB$", period, re.IGNORECASE):
        return ClassifiedPeriod(
            original=period,
            period_type=PeriodType.BUDGET,
            normalized=None,
            is_usable=False,
        )

    # Step 4: Check for YTD Actual (e.g., "YTD Dec-21", "YTD  Sep-25")
    ytd_match = re.match(r"^YTD\s+([A-Za-z]{3})-(\d{2,4})$", period, re.IGNORECASE)
    if ytd_match:
        month_abbrev = ytd_match.group(1)
        year_str = ytd_match.group(2)
        normalized_month = _normalize_month_abbreviation(month_abbrev)
        normalized_year = _convert_4digit_year_to_2digit(year_str)
        normalized = f"{normalized_month}-{normalized_year}"
        return ClassifiedPeriod(
            original=period,
            period_type=PeriodType.YTD_ACTUAL,
            normalized=normalized,
            is_usable=True,
        )

    # Step 5: Check for Monthly Actual (e.g., "Dec-21", "Jan-25", "Dez-21", "Dec-2017")
    monthly_match = re.match(r"^([A-Za-z]{3})-(\d{2,4})$", period)
    if monthly_match:
        month_abbrev = monthly_match.group(1)
        year_str = monthly_match.group(2)
        normalized_month = _normalize_month_abbreviation(month_abbrev)
        normalized_year = _convert_4digit_year_to_2digit(year_str)
        normalized = f"{normalized_month}-{normalized_year}"
        return ClassifiedPeriod(
            original=period,
            period_type=PeriodType.MONTHLY_ACTUAL,
            normalized=normalized,
            is_usable=True,
        )

    # Step 6: Everything else is UNKNOWN
    # This includes: "N/A", "None", "2017 P", year-only formats, etc.
    return ClassifiedPeriod(
        original=period,
        period_type=PeriodType.UNKNOWN,
        normalized=None,
        is_usable=False,
    )


def normalize_classified_period(period: str | None) -> str | None:
    """Convenience function to normalize a period if usable.

    Args:
        period: Period string to normalize

    Returns:
        Normalized period string (e.g., "Dec-21") or None if excluded

    Examples:
        >>> normalize_classified_period("YTD Dec-21")
        "Dec-21"
        >>> normalize_classified_period("B Dec-21")
        None
    """
    classified = classify_period(period)
    return classified.normalized


@dataclass
class ClassificationReport:
    """Summary of period classification results."""

    total_records: int
    usable_records: int
    monthly_actual_count: int
    ytd_actual_count: int
    budget_count: int
    ytd_budget_count: int
    unknown_count: int

    @property
    def usability_rate(self) -> float:
        """Percentage of records that are usable."""
        if self.total_records == 0:
            return 0.0
        return self.usable_records / self.total_records * 100

    @property
    def exclusion_breakdown(self) -> dict[str, int]:
        """Breakdown of excluded records by type."""
        return {
            "budget": self.budget_count,
            "ytd_budget": self.ytd_budget_count,
            "unknown": self.unknown_count,
        }


def generate_classification_report(
    periods: list[str | None],
) -> ClassificationReport:
    """Generate a classification report for a list of periods.

    Args:
        periods: List of period strings to classify

    Returns:
        ClassificationReport with counts by type
    """
    monthly_actual = 0
    ytd_actual = 0
    budget = 0
    ytd_budget = 0
    unknown = 0

    for period in periods:
        classified = classify_period(period)
        if classified.period_type == PeriodType.MONTHLY_ACTUAL:
            monthly_actual += 1
        elif classified.period_type == PeriodType.YTD_ACTUAL:
            ytd_actual += 1
        elif classified.period_type == PeriodType.BUDGET:
            budget += 1
        elif classified.period_type == PeriodType.YTD_BUDGET:
            ytd_budget += 1
        else:
            unknown += 1

    return ClassificationReport(
        total_records=len(periods),
        usable_records=monthly_actual + ytd_actual,
        monthly_actual_count=monthly_actual,
        ytd_actual_count=ytd_actual,
        budget_count=budget,
        ytd_budget_count=ytd_budget,
        unknown_count=unknown,
    )


def validate_period_homogeneity(
    classified_periods: list[ClassifiedPeriod],
) -> tuple[bool, str]:
    """Validate that all usable periods are homogeneous (same type).

    If mixing is detected, returns info about which type dominates.

    Args:
        classified_periods: List of classified period objects

    Returns:
        Tuple of (is_homogeneous, dominant_type_or_warning)

    Examples:
        >>> periods = [ClassifiedPeriod(..., period_type=MONTHLY_ACTUAL), ...]
        >>> validate_period_homogeneity(periods)
        (True, "monthly_actual")
    """
    usable = [p for p in classified_periods if p.is_usable]

    if not usable:
        return True, "no_usable_periods"

    monthly_count = sum(1 for p in usable if p.period_type == PeriodType.MONTHLY_ACTUAL)
    ytd_count = sum(1 for p in usable if p.period_type == PeriodType.YTD_ACTUAL)

    total = len(usable)

    # Check for pure homogeneity
    if monthly_count == total:
        return True, "monthly_actual"
    if ytd_count == total:
        return True, "ytd_actual"

    # Mixing detected - determine dominant type
    monthly_ratio = monthly_count / total
    ytd_ratio = ytd_count / total

    if monthly_ratio >= 0.6:
        dominant = "monthly_actual"
    elif ytd_ratio >= 0.6:
        dominant = "ytd_actual"
    else:
        dominant = "mixed"

    warning = (
        f"Period mixing detected: {monthly_count} monthly ({monthly_ratio:.0%}), "
        f"{ytd_count} YTD ({ytd_ratio:.0%}). Dominant: {dominant}"
    )

    return False, warning
