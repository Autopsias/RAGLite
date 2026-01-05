"""Date range parsing utilities for external data queries."""

from datetime import date, datetime, timedelta


def _parse_date_range(date_range: str) -> tuple[date, date]:
    """Parse date range string into start and end dates.

    Supports both ISO format (YYYY-MM-DD:YYYY-MM-DD) and shortcut keywords.

    Args:
        date_range: Date range string in ISO format or shortcut.
                   Shortcuts: last_30_days, last_90_days, last_year,
                             last_quarter, ytd (year-to-date)

    Returns:
        Tuple of (start_date, end_date)

    Raises:
        ValueError: If date_range format is invalid or unrecognized

    Examples:
        >>> _parse_date_range("2024-01-01:2024-12-31")
        (datetime.date(2024, 1, 1), datetime.date(2024, 12, 31))

        >>> _parse_date_range("last_30_days")
        (datetime.date(2024, 12, 2), datetime.date(2025, 1, 1))
    """
    today = date.today()
    shortcuts = {
        "last_30_days": (today - timedelta(days=30), today),
        "last_90_days": (today - timedelta(days=90), today),
        "last_year": (today - timedelta(days=365), today),
        "last_quarter": (today - timedelta(days=90), today),
        "ytd": (date(today.year, 1, 1), today),
    }
    if date_range.lower() in shortcuts:
        return shortcuts[date_range.lower()]
    if ":" in date_range:
        parts = date_range.split(":")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid date range format: {date_range}. Expected 'YYYY-MM-DD:YYYY-MM-DD'"
            )
        try:
            start = datetime.strptime(parts[0].strip(), "%Y-%m-%d").date()
            end = datetime.strptime(parts[1].strip(), "%Y-%m-%d").date()
            return start, end
        except ValueError as e:
            raise ValueError(f"Invalid date format in range: {e}") from e
    raise ValueError(
        f"Invalid date_range: '{date_range}'. "
        "Use ISO format 'YYYY-MM-DD:YYYY-MM-DD' or shortcuts: last_30_days, last_90_days, last_year, last_quarter, ytd"
    )
