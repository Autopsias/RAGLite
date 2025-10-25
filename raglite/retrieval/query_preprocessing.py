"""Query preprocessing for PostgreSQL table search.

Extracts keywords and metadata filters from natural language queries
to improve table retrieval accuracy.

Story 2.7 Enhancement: Query preprocessing bridges the gap between natural
language queries and PostgreSQL full-text search by:
1. Extracting core business keywords (what to search for)
2. Identifying temporal/filter criteria (when/where to look)
3. Mapping query terms to metadata fields for precise filtering
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Common stopwords to remove from queries (basic list, not exhaustive)
STOPWORDS = {
    "what",
    "is",
    "the",
    "in",
    "for",
    "per",
    "of",
    "and",
    "or",
    "a",
    "an",
    "show",
    "me",
    "find",
    "get",
}

# Month name mappings for date normalization
MONTH_MAPPINGS = {
    "january": "Jan",
    "february": "Feb",
    "march": "Mar",
    "april": "Apr",
    "may": "May",
    "june": "Jun",
    "july": "Jul",
    "august": "Aug",
    "september": "Sep",
    "october": "Oct",
    "november": "Nov",
    "december": "Dec",
    "jan": "Jan",
    "feb": "Feb",
    "mar": "Mar",
    "apr": "Apr",
    "jun": "Jun",
    "jul": "Jul",
    "aug": "Aug",
    "sep": "Sep",
    "oct": "Oct",
    "nov": "Nov",
    "dec": "Dec",
}


def preprocess_query_for_table_search(query: str) -> tuple[str, dict[str, Any] | None]:
    """Preprocess natural language query for PostgreSQL table search.

    Extracts core business keywords and temporal filters from the query.
    This allows PostgreSQL full-text search to focus on business terms while
    using metadata filtering for dates and other qualifiers.

    Args:
        query: Natural language query (e.g., "What is the variable cost per ton in August 2025?")

    Returns:
        Tuple of (keywords, filters):
          - keywords: Simplified keyword string for full-text search
          - filters: Optional metadata filters dict or None

    Example:
        >>> keywords, filters = preprocess_query_for_table_search(
        ...     "What is the EBITDA margin for the Secil Group in August 2025?"
        ... )
        >>> print(keywords)
        'EBITDA margin'
        >>> print(filters)
        {'reporting_period': 'Aug-25'}

    Implementation Notes:
        - Removes common stopwords ("what", "is", "the", etc.)
        - Extracts temporal qualifiers and maps to metadata filters
        - Normalizes month names (August → Aug) and years (2025 → 25)
        - Preserves critical business terms (EBITDA, margin, cost, revenue, etc.)
    """
    logger.debug("Preprocessing query for table search", extra={"original_query": query})

    # Lowercase for processing (but preserve for keyword extraction)
    query_lower = query.lower()

    # Extract temporal information (month + year)
    # Pattern: "August 2025", "Aug 2025", "2025", etc.
    temporal_filters = _extract_temporal_filters(query_lower)

    # Remove question marks and normalize whitespace
    cleaned = query.replace("?", "").strip()

    # Split into tokens
    tokens = cleaned.split()

    # Remove stopwords and temporal terms
    keywords_tokens = []
    temporal_terms = {
        "august",
        "2025",
        "aug",
        "25",
        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "sep",
        "oct",
        "nov",
        "dec",
        "january",
        "february",
        "march",
        "april",
        "june",
        "july",
        "september",
        "october",
        "november",
        "december",
    }

    for token in tokens:
        token_lower = token.lower()
        # Keep token if it's not a stopword and not a temporal term
        if token_lower not in STOPWORDS and token_lower not in temporal_terms:
            # Preserve original case for business terms
            keywords_tokens.append(token)

    # Join remaining keywords
    keywords = " ".join(keywords_tokens)

    logger.info(
        "Query preprocessed",
        extra={
            "original_query": query[:100],
            "extracted_keywords": keywords,
            "temporal_filters": temporal_filters,
        },
    )

    return keywords, temporal_filters


def _extract_temporal_filters(query_lower: str) -> dict[str, Any] | None:
    """Extract temporal filters from query.

    Looks for month+year patterns and maps them to database metadata format.

    Args:
        query_lower: Lowercased query string

    Returns:
        Dict with reporting_period filter or None

    Examples:
        >>> _extract_temporal_filters("what is ebitda in august 2025")
        {'reporting_period': 'Aug-25%'}
        >>> _extract_temporal_filters("show me revenue in Q3 2024")
        None  # Quarter extraction not yet implemented
    """
    # Pattern 1: Month name + full year (e.g., "August 2025", "Aug 2025")
    # This matches: January|February|...|December|Jan|Feb|...|Dec followed by 2024|2025|etc.
    month_year_pattern = r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})\b"

    match = re.search(month_year_pattern, query_lower)
    if match:
        month_name = match.group(1)
        year = match.group(2)

        # Normalize month name to abbreviated form (August → Aug)
        month_abbr = MONTH_MAPPINGS.get(month_name, month_name.capitalize()[:3])

        # Normalize year to 2-digit (2025 → 25)
        year_short = year[-2:]

        # Map to database format: "Aug-25" (matches "Aug-25 YTD", "Aug-25", etc.)
        reporting_period_pattern = f"{month_abbr}-{year_short}%"

        # Use LIKE pattern matching for flexibility
        return {"reporting_period": reporting_period_pattern}

    # Pattern 2: Just year (e.g., "2025")
    # Less specific, but can still help filter
    year_pattern = r"\b(202[0-9])\b"
    match = re.search(year_pattern, query_lower)
    if match:
        year = match.group(1)
        year_short = year[-2:]
        # Match any reporting period containing this year
        return {"reporting_period": f"%-{year_short}%"}

    # No temporal information found
    return None
