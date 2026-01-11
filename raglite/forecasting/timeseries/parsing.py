"""Timeseries extraction - Date and period parsing.

Part of Story 8.1 refactoring to split timeseries_extract.py.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from dateutil import parser as date_parser

from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


def parse_fiscal_date(date_str: str, fiscal_year_start_month: int = 7) -> datetime:
    """Parse fiscal period labels and date formats into datetime.

    Handles various date formats including:
    - Fiscal periods: "Q3 FY24", "FY2024 Q2", "FY24"
    - Standard dates: "Jan 2024", "2024-01", "1/2024", "January 2024"
    - ISO dates: "2024-01-15"

    Args:
        date_str: Date string to parse
        fiscal_year_start_month: Month when fiscal year starts (default: 7 = July)

    Returns:
        datetime object representing the start of the period

    Raises:
        ValueError: If date string cannot be parsed

    Example:
        >>> parse_fiscal_date("Q3 FY24")  # Fiscal Q3 = Jan-Mar (FY24 starts Jul 2023)
        datetime(2024, 1, 1)
        >>> parse_fiscal_date("Jan 2024")
        datetime(2024, 1, 1)
    """
    date_str = date_str.strip().upper()

    # Handle fiscal year patterns: "Q3 FY24", "FY2024 Q2", "FY24", "Q1 2024"
    import re

    # Pattern: Q[1-4] FY[YY|YYYY] or FY[YY|YYYY] Q[1-4]
    fiscal_pattern = r"(?:Q([1-4])\s*)?FY(\d{2,4})(?:\s*Q([1-4]))?"
    match = re.search(fiscal_pattern, date_str)

    if match:
        quarter = match.group(1) or match.group(3)
        year_str = match.group(2)

        # Handle 2-digit years
        year = int(year_str)
        if year < 100:
            year = 2000 + year

        if quarter:
            # Map fiscal quarters to calendar months (assuming July FY start)
            # FY Q1 = Jul-Sep, Q2 = Oct-Dec, Q3 = Jan-Mar, Q4 = Apr-Jun
            quarter_int = int(quarter)
            if fiscal_year_start_month == 7:
                quarter_to_month = {1: 7, 2: 10, 3: 1, 4: 4}
                month = quarter_to_month[quarter_int]
                # Q3 and Q4 are in the calendar year matching FY year
                # Q1 and Q2 are in the previous calendar year
                if quarter_int in (1, 2):
                    year -= 1
            else:
                # Generic fiscal year mapping (Jan start = calendar year)
                quarter_to_month = {1: 1, 2: 4, 3: 7, 4: 10}
                month = quarter_to_month[quarter_int]

            return datetime(year, month, 1)
        else:
            # Full fiscal year - return start of FY
            if fiscal_year_start_month == 7:
                return datetime(year - 1, 7, 1)
            return datetime(year, fiscal_year_start_month, 1)

    # Pattern: Q[1-4] [YYYY] (calendar quarter)
    calendar_q_pattern = r"Q([1-4])\s*(\d{4})"
    match = re.search(calendar_q_pattern, date_str)
    if match:
        quarter = int(match.group(1))
        year = int(match.group(2))
        month = (quarter - 1) * 3 + 1  # Q1=1, Q2=4, Q3=7, Q4=10
        return datetime(year, month, 1)

    # Fallback to dateutil parser for standard date formats
    try:
        parsed = date_parser.parse(date_str)
        return datetime(
            parsed.year,
            parsed.month,
            parsed.day,
            parsed.hour,
            parsed.minute,
            parsed.second,
        )
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot parse date: {date_str}") from e


def normalize_to_interval(data: TimeSeriesData, interval: str) -> TimeSeriesData:
    """Normalize time-series data to consistent time intervals.

    Aggregates data points to the specified interval using averaging.

    Args:
        data: TimeSeriesData with points at various intervals
        interval: Target interval: "monthly", "quarterly", "yearly"

    Returns:
        TimeSeriesData with points normalized to the specified interval

    Raises:
        ValueError: If interval is not supported

    Example:
        >>> data = TimeSeriesData(metric_name="revenue", points=[...], interval="daily")
        >>> normalized = normalize_to_interval(data, "monthly")
    """
    if interval not in ("monthly", "quarterly", "yearly"):
        raise ValueError(f"Unsupported interval: {interval}. Use 'monthly', 'quarterly', 'yearly'")

    if not data.points:
        return TimeSeriesData(
            metric_name=data.metric_name,
            points=[],
            interval=interval,
            source_documents=data.source_documents,
        )

    # Group points by interval bucket
    buckets: dict[str, list[TimeSeriesPoint]] = {}

    for point in data.points:
        if interval == "monthly":
            bucket_key = point.date.strftime("%Y-%m")
        elif interval == "quarterly":
            quarter = (point.date.month - 1) // 3 + 1
            bucket_key = f"{point.date.year}-Q{quarter}"
        else:  # yearly
            bucket_key = str(point.date.year)

        if bucket_key not in buckets:
            buckets[bucket_key] = []
        buckets[bucket_key].append(point)

    # Aggregate points in each bucket (average)
    normalized_points = []
    for bucket_key, points in sorted(buckets.items()):
        avg_value = sum(p.value for p in points) / len(points)

        # Use first point's date as representative
        if interval == "monthly":
            year, month = map(int, bucket_key.split("-"))
            bucket_date = datetime(year, month, 1)
        elif interval == "quarterly":
            year_str, q_str = bucket_key.split("-Q")
            quarter = int(q_str)
            bucket_date = datetime(int(year_str), (quarter - 1) * 3 + 1, 1)
        else:  # yearly
            bucket_date = datetime(int(bucket_key), 1, 1)

        normalized_points.append(
            TimeSeriesPoint(date=bucket_date, value=avg_value, label=bucket_key)
        )

    return TimeSeriesData(
        metric_name=data.metric_name,
        points=normalized_points,
        interval=interval,
        source_documents=data.source_documents,
    )


def parse_period_to_date(period: str, fiscal_year: int) -> datetime:
    """Parse period string (Mon-YY format) to datetime.

    Converts period strings like "Jan-25", "Dec-24" to datetime objects
    representing the first day of that month.

    BUG FIX (P0): Extract year from period suffix to prevent duplicate dates.
    Previously ignored year suffix and used fiscal_year parameter, causing
    "Jan-24" and "Jan-25" to both map to same date when processing multi-year data.

    Args:
        period: Period string in Mon-YY format (e.g., "Jan-25", "Dec-24")
        fiscal_year: Fiscal year as integer (DEPRECATED - now extracted from period suffix)

    Returns:
        datetime object for the first day of the period month

    Raises:
        ValueError: If period format is invalid or month name not recognized

    Example:
        >>> parse_period_to_date("Jan-25", 2025)
        datetime(2025, 1, 1)
        >>> parse_period_to_date("Dec-24", 2024)
        datetime(2024, 12, 1)
    """
    import re

    # BUG FIX: Parse period suffix to determine actual year
    # "Jan-24" → year = 2024, "Jan-25" → year = 2025
    match = re.match(r"^([A-Za-z]+)-(\d{2})$", period.strip())
    if not match:
        raise ValueError(
            f"Invalid period format: '{period}'. Expected Mon-YY format (e.g., Jan-25)"
        )

    month_abbrev = match.group(1).capitalize()
    year_suffix = int(match.group(2))
    year = 2000 + year_suffix  # 24 → 2024, 25 → 2025

    # Month name to integer mapping
    month_map = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }

    if month_abbrev not in month_map:
        raise ValueError(
            f"Invalid month abbreviation: '{month_abbrev}'. "
            f"Expected one of: {', '.join(month_map.keys())}"
        )

    month = month_map[month_abbrev]
    return datetime(year, month, 1)
