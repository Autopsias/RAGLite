"""Period format normalization for query-to-database period mapping.

Bridges the gap between natural language period expressions (Q3 2025, August 2025)
and database period formats (Aug-25, Aug-25 YTD).

Usage:
    >>> from raglite.retrieval.period_normalizer import normalize_period, detect_period_in_query
    >>> period_variants = normalize_period("Q3 2025")
    >>> # Returns: ["Jul-25", "Aug-25", "Sep-25", "Jul-25 YTD", "Aug-25 YTD", "Q3-25"]

    >>> query_period = detect_period_in_query("What is the EBITDA for Q3 2025?")
    >>> # Returns: "Q3 2025"
"""

import re

# Period mapping definitions
PERIOD_MAPPINGS = {
    # Quarter mappings
    "Q1 2025": ["Jan-25", "Feb-25", "Mar-25", "Jan-25 YTD", "Mar-25 YTD", "Q1-25"],
    "Q2 2025": ["Apr-25", "May-25", "Jun-25", "Apr-25 YTD", "Jun-25 YTD", "Q2-25"],
    "Q3 2025": ["Jul-25", "Aug-25", "Sep-25", "Jul-25 YTD", "Aug-25 YTD", "Q3-25"],
    "Q4 2025": ["Oct-25", "Nov-25", "Dec-25", "Oct-25 YTD", "Dec-25 YTD", "Q4-25"],
    # Half-year mappings
    "H1 2025": ["Jan-25 YTD", "Feb-25 YTD", "Mar-25 YTD", "Apr-25 YTD", "May-25 YTD", "Jun-25 YTD"],
    "H2 2025": ["Jul-25 YTD", "Aug-25 YTD", "Sep-25 YTD", "Oct-25 YTD", "Nov-25 YTD", "Dec-25 YTD"],
    # Full year mappings
    "2025": ["Jan-25 YTD", "Dec-25 YTD", "2025"],
    "FY2025": ["Jan-25 YTD", "Dec-25 YTD", "2025"],
}

# Reverse mappings (database period → canonical)
REVERSE_MAPPINGS = {
    "Aug-25 YTD": "Q3 2025",
    "Aug-25": "Q3 2025",
    "Jun-25 YTD": "Q2 2025",
    "Jun-25": "Q2 2025",
    "Mar-25 YTD": "Q1 2025",
    "Mar-25": "Q1 2025",
    "Dec-25 YTD": "Q4 2025",
    "Dec-25": "Q4 2025",
}


def normalize_period(query_period: str) -> list[str]:
    """Expand query period to all database variants.

    Args:
        query_period: Period as expressed in query (e.g., "Q3 2025", "Aug-25")

    Returns:
        List of all matching period formats in database

    Examples:
        >>> normalize_period("Q3 2025")
        ["Jul-25", "Aug-25", "Sep-25", "Jul-25 YTD", "Aug-25 YTD", "Q3-25"]

        >>> normalize_period("Aug-25")
        ["Aug-25", "Aug-25 YTD"]

        >>> normalize_period("August 2025")
        ["Aug-25", "Aug-25 YTD"]

        >>> normalize_period("FY2025")
        ["Jan-25 YTD", "Dec-25 YTD", "2025"]
    """
    # Direct mapping
    if query_period in PERIOD_MAPPINGS:
        return PERIOD_MAPPINGS[query_period]

    # Quarter detection from text (handles "Q3 25", "Q3-25", "Q325", etc.)
    # MUST come before month-year detection to avoid "Q3" being treated as a month
    quarter_match = re.match(r"Q([1-4])[\s-]?(25|2025)", query_period, re.IGNORECASE)
    if quarter_match:
        quarter_num = quarter_match.group(1)
        canonical_period = f"Q{quarter_num} 2025"
        return PERIOD_MAPPINGS.get(canonical_period, [query_period])

    # Month-year format detection (e.g., "August 2025", "Aug 2025", "Aug-25")
    month_match = re.match(r"(\w+)[\s-]?(25|2025)", query_period, re.IGNORECASE)
    if month_match:
        month_name = month_match.group(1)
        year = month_match.group(2)

        # Normalize month name
        month_abbr = normalize_month(month_name)

        if year == "2025":
            year = "25"

        return [f"{month_abbr}-{year}", f"{month_abbr}-{year} YTD"]

    # Half-year detection
    half_year_match = re.match(r"H([12])[\s]?(25|2025)", query_period, re.IGNORECASE)
    if half_year_match:
        half_num = half_year_match.group(1)
        canonical_period = f"H{half_num} 2025"
        return PERIOD_MAPPINGS.get(canonical_period, [query_period])

    # Fiscal year detection
    fy_match = re.match(r"(FY|fiscal year)[\s]?(25|2025)", query_period, re.IGNORECASE)
    if fy_match:
        return PERIOD_MAPPINGS.get("FY2025", [query_period])

    # If no mapping found, return as-is (might be exact match)
    return [query_period]


def normalize_month(month_str: str) -> str:
    """Normalize month name to 3-letter abbreviation.

    Args:
        month_str: Month name (full or abbreviated)

    Returns:
        3-letter month abbreviation (e.g., "Jan", "Feb", "Mar")

    Examples:
        >>> normalize_month("January")
        "Jan"

        >>> normalize_month("Aug")
        "Aug"

        >>> normalize_month("august")
        "Aug"
    """
    MONTH_MAPPINGS = {
        "january": "Jan",
        "jan": "Jan",
        "february": "Feb",
        "feb": "Feb",
        "march": "Mar",
        "mar": "Mar",
        "april": "Apr",
        "apr": "Apr",
        "may": "May",
        "june": "Jun",
        "jun": "Jun",
        "july": "Jul",
        "jul": "Jul",
        "august": "Aug",
        "aug": "Aug",
        "september": "Sep",
        "sep": "Sep",
        "october": "Oct",
        "oct": "Oct",
        "november": "Nov",
        "nov": "Nov",
        "december": "Dec",
        "dec": "Dec",
    }

    return MONTH_MAPPINGS.get(month_str.lower(), month_str)


def detect_period_in_query(query: str) -> str:
    """Extract period reference from natural language query.

    Args:
        query: Natural language query text

    Returns:
        Detected period string or empty string if not found

    Examples:
        >>> detect_period_in_query("What is the EBITDA for Q3 2025?")
        "Q3 2025"

        >>> detect_period_in_query("Portugal variable costs in August 2025")
        "August 2025"

        >>> detect_period_in_query("Show me fiscal year 2025 results")
        "FY2025"

        >>> detect_period_in_query("What is the EBITDA?")
        ""
    """
    # Database format patterns (Aug-25, Aug-25 YTD)
    # MUST come first to match exact database formats before month-year patterns
    db_pattern = r"[A-Z][a-z]{2}-\d{2}(\s+YTD)?"
    db_match = re.search(db_pattern, query)
    if db_match:
        # Return the full match (including YTD suffix if present)
        return db_match.group(0)

    # Quarter patterns
    quarter_pattern = r"Q([1-4])[\s]?(25|2025)"
    quarter_match = re.search(quarter_pattern, query, re.IGNORECASE)
    if quarter_match:
        quarter_num = quarter_match.group(1)
        return f"Q{quarter_num} 2025"

    # Half-year patterns
    half_year_pattern = r"H([12])[\s]?(25|2025)"
    half_year_match = re.search(half_year_pattern, query, re.IGNORECASE)
    if half_year_match:
        half_num = half_year_match.group(1)
        return f"H{half_num} 2025"

    # Month-year patterns
    month_pattern = r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\s-]?(25|2025)"
    month_match = re.search(month_pattern, query, re.IGNORECASE)
    if month_match:
        return month_match.group(0)

    # Fiscal year patterns
    fy_pattern = r"(FY|fiscal year)[\s]?(25|2025)"
    fy_match = re.search(fy_pattern, query, re.IGNORECASE)
    if fy_match:
        return "FY2025"

    return ""
