"""
Table processing utilities.

This module provides helper functions for processing table data, including
year extraction, context inference, and validation.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def extract_year(period_text: str | None) -> int | None:
    """Extract fiscal year from period text.

    Examples:
        >>> extract_year("Oct-25")
        2025

        >>> extract_year("Q2 2025")
        2025

        >>> extract_year("2024")
        2024

        >>> extract_year("YTD Jan-25")
        2025
    """
    if not period_text:
        return None

    # Look for 4-digit year (2024, 2025, etc.)
    match_4digit = re.search(r"\b(20\d{2})\b", period_text)
    if match_4digit:
        return int(match_4digit.group(1))

    # Look for 2-digit year after dash (Oct-25, Jan-24, etc.) and convert to 20XX
    match_2digit = re.search(r"-(\d{2})\b", period_text)
    if match_2digit:
        year_2digit = int(match_2digit.group(1))
        # Assume 20XX for years 00-99
        return 2000 + year_2digit

    # Look for standalone 2-digit year at end
    match_standalone = re.search(r"\b(\d{2})$", period_text)
    if match_standalone:
        year_2digit = int(match_standalone.group(1))
        return 2000 + year_2digit

    return None


def infer_metric_from_context(page_context: dict) -> str | None:
    """Infer metric from page/section context when not present in headers.

    Production-validated approach: Extract from section headings and nearby text.
    Used as fallback when orientation detection produces NULL metric.

    Args:
        page_context: Dict from extract_page_context() with section_heading, nearby_text

    Returns:
        Inferred metric name or None
    """
    # Combine all available context
    context_text = []
    if page_context.get("section_heading"):
        context_text.append(page_context["section_heading"])
    if page_context.get("nearby_text"):
        context_text.extend(page_context["nearby_text"])
    if page_context.get("page_title"):
        context_text.append(page_context["page_title"])

    if not context_text:
        return None

    combined_text = " ".join(context_text).lower()

    # Common financial metrics (universal patterns)
    metric_keywords = {
        "revenue": "Revenue",
        "sales": "Sales",
        "turnover": "Turnover",
        "ebitda": "EBITDA",
        "ebit": "EBIT",
        "profit": "Profit",
        "margin": "Margin",
        "cost": "Cost",
        "expense": "Expense",
        "capex": "CAPEX",
        "opex": "OPEX",
        "cash": "Cash",
        "debt": "Debt",
        "equity": "Equity",
        "volume": "Volume",
        "production": "Production",
        "capacity": "Capacity",
        "price": "Price",
        "exchange": "Exchange Rate",
        "rate": "Rate",
        "ratio": "Ratio",
        "investment": "Investment",
        "balance": "Balance",
        "asset": "Assets",
        "liability": "Liabilities",
        "inventory": "Inventory",
        "receivable": "Receivables",
        "payable": "Payables",
        "indicator": "Indicator",
        "frequency": "Frequency",
        "severity": "Severity",
    }

    # Check for exact keyword matches in combined context
    for keyword, metric_name in metric_keywords.items():
        if keyword in combined_text:
            return metric_name

    # Fallback: use first meaningful text from section heading
    if page_context.get("section_heading"):
        words = [w for w in page_context["section_heading"].split() if len(w) > 2][:3]
        if words:
            return " ".join(words)

    return None


def infer_entity_from_context(page_context: dict) -> str | None:
    """Infer entity from page/section context when not present in headers.

    Production-validated approach: Extract from section headings and nearby text.
    Used as fallback when orientation detection produces NULL entity.

    Args:
        page_context: Dict from extract_page_context() with section_heading, nearby_text

    Returns:
        Inferred entity name or None
    """
    # Combine all available context
    context_text = []
    if page_context.get("section_heading"):
        context_text.append(page_context["section_heading"])
    if page_context.get("nearby_text"):
        context_text.extend(page_context["nearby_text"])
    if page_context.get("page_title"):
        context_text.append(page_context["page_title"])

    if not context_text:
        return None

    combined_text = " ".join(context_text).lower()

    # Common entity patterns (universal)
    entity_patterns = [
        # Geographic entities
        (
            r"\b(portugal|spain|france|italy|germany|uk|brazil|usa|canada|china|india|japan|angola|tunisia|lebanon)\b",
            "country",
        ),
        (r"\b(europe|asia|americas|africa|oceania)\b", "region"),
        (r"\b(north|south|east|west|central)\b", "direction"),
        # Corporate entities
        (r"\b(group|consolidated|conso|total|corporate)\b", "group"),
        (r"\b(division|segment|unit|department)\b", "division"),
        (r"\b(subsidiary|affiliate|joint\s*venture)\b", "subsidiary"),
        # Industry-specific (cement example, but add more universal)
        (r"\b(cement|concrete|aggregates|ready-mix|clinker)\b", "product"),
        # Multi-entity indicators
        (r"\bby\s+(country|region|entity|division|segment)\b", "multi-entity"),
    ]

    for pattern, _entity_type in entity_patterns:
        match = re.search(pattern, combined_text)
        if match:
            # Return the matched text capitalized
            return match.group(1).capitalize()

    # Check if context contains "by [something]" pattern
    by_match = re.search(r"\bby\s+([a-z]+)", combined_text)
    if by_match:
        return by_match.group(1).capitalize()

    # Fallback: if section heading mentions a specific entity term, use it
    section_heading_value = page_context.get("section_heading")
    if section_heading_value and isinstance(section_heading_value, str):
        # Simple heuristic: if section heading is short (< 5 words), use it as entity
        heading_words = section_heading_value.split()
        if 1 <= len(heading_words) <= 4:
            # Type narrowing: section_heading_value is confirmed str at this point
            result: str = section_heading_value
            return result

    return None


def validate_entity(entity: str | None) -> bool:
    """Validate that an entity value is semantically valid.

    Returns False for values that are clearly NOT entities:
    - Unit descriptors (Currency, EUR, kton, etc.)
    - Numeric values
    - Common non-entity patterns

    This is a safety net to catch misclassified headers that slip through
    the primary classification logic. (Fix for June 2025 PDF table extraction bug)

    Args:
        entity: The entity value to validate

    Returns:
        True if entity appears valid, False if it's likely misclassified
    """
    if not entity or not entity.strip():
        return False

    entity_lower = entity.lower().strip()

    # Reject known unit descriptor patterns
    invalid_entity_patterns = [
        # CRITICAL: Placeholder values
        r"^\s*unknown\s*$",  # "Unknown" placeholder
        # CRITICAL: Temporal descriptors (most common data quality issue)
        r"^\s*ytd\s*$",  # Year-to-date
        r"^\s*mtd\s*$",  # Month-to-date
        r"^\s*qtd\s*$",  # Quarter-to-date
        r"^\s*%\s*(ly|py|b)\s*$",  # % LY, % PY, % B
        r"^\s*b\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",  # B Oct-25
        r"^\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-\s]?\d{2,4}$",  # Oct-24, Mar-25
        # CRITICAL: Currency descriptors
        r"^\s*currency\b",  # "Currency (1000 EUR)"
        r"\(\s*\d+\s*(eur|usd|gbp|brl)\b",  # Parenthetical currency ANYWHERE: "Others (1000 BRL)"
        r"^\s*\d+\s*(eur|usd|gbp)",  # "1000 EUR"
        r"^\s*(eur|usd|gbp)/",  # "EUR/ton"
        # HIGH: Standalone currency codes and common units
        r"^\s*(eur|usd|gbp|brl|akz)\s*$",  # Standalone currency codes
        r"^\s*m(eur|usd|gbp)\s*$",  # Million currency: Meur, Musd
        r"^\s*unit\s*$",  # "Unit"
        r"^\s*(kton|mton|ton|gwh|mwh|gj)\s*$",  # Energy/weight units
        r"^\s*%\s*$",  # Percentage symbol alone
        r"^\s*days?\s*$",  # "day" or "days"
        r"^\s*fte\s*$",  # FTE
        # MEDIUM: Null representations and placeholders
        r"^\s*(n/?a|null|none|-|#)\s*$",  # N/A, NA, null, -, #
        # LOW: Numeric and measurement descriptors
        r"^\s*\d+[\.,]?\d*\s*$",  # Pure numeric values
        r"^\s*measurement\s*$",  # "Measurement"
        r"^\s*uom\s*$",  # "UOM" (Unit of Measure)
    ]

    for pattern in invalid_entity_patterns:
        if re.search(pattern, entity_lower):
            return False

    return True


def validate_metric(metric: str) -> bool:
    """Validate metric name to filter out temporal patterns, units, placeholders.

    This function mirrors validate_entity() but for metric validation.
    Rejects values that are clearly not metric names (temporal descriptors,
    currency codes, placeholders, units, etc.).

    Args:
        metric: Metric name to validate

    Returns:
        True if valid metric name, False if should be rejected

    Examples:
        >>> validate_metric("EBITDA")
        True
        >>> validate_metric("Unknown")
        False
        >>> validate_metric("YTD")
        False
        >>> validate_metric("EUR")
        False
    """
    if not metric or not metric.strip():
        return False

    metric_lower = metric.strip().lower()

    # Reject invalid metric patterns
    invalid_metric_patterns = [
        # CRITICAL: Placeholder values
        r"^\s*unknown\s*$",  # "Unknown" placeholder
        # CRITICAL: Temporal descriptors (most common data quality issue)
        r"^\s*ytd\s*$",  # Year-to-date
        r"^\s*mtd\s*$",  # Month-to-date
        r"^\s*qtd\s*$",  # Quarter-to-date
        r"^\s*%\s*(ly|py|b)\s*$",  # % LY, % PY, % B
        r"^\s*b\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",  # B Oct-25
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-\s]?\d{2,4}\b",  # Oct-25, Mar-24
        r"\b(q[1-4]|h[12])\s*\d{4}\b",  # Q1 2025, H1 2024
        r"^\s*var\.?\s*%",  # Var. % B
        # CRITICAL: Currency descriptors
        r"^\s*currency\b",  # "Currency (1000 EUR)"
        r"\(\s*\d+\s*(eur|usd|gbp|brl|akz|mzn)\b",  # Parenthetical currency
        r"^\s*\d+\s*(eur|usd|gbp)",  # "1000 EUR"
        r"^\s*(eur|usd|gbp)/",  # "EUR/ton"
        # HIGH: Standalone currency codes and common units
        r"^\s*(eur|usd|gbp|brl|akz|mzn)\s*$",  # Standalone currency codes
        r"^\s*m(eur|usd|gbp)\s*$",  # Million currency: Meur, Musd
        r"^\s*unit\s*$",  # "Unit"
        r"^\s*(kton|mton|ton|gwh|mwh|gj)\s*$",  # Energy/weight units
        r"^\s*%\s*$",  # Percentage symbol alone
        r"^\s*days?\s*$",  # "day" or "days"
        r"^\s*fte\s*$",  # FTE
        # MEDIUM: Null representations and placeholders
        r"^\s*(n/?a|null|none|-|#)\s*$",  # N/A, NA, null, -, #
        # LOW: Numeric and measurement descriptors
        r"^\s*\d+[\.,]?\d*\s*$",  # Pure numeric values
        r"^\s*measurement\s*$",  # "Measurement"
        r"^\s*uom\s*$",  # "UOM" (Unit of Measure)
    ]

    for pattern in invalid_metric_patterns:
        if re.search(pattern, metric_lower, re.IGNORECASE):
            return False

    return True
