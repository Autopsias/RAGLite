"""Value type classification for ingestion pipeline.

Classifies financial values into types:
- ACTUAL: Realized/historical values
- BUDGET: Planned/budgeted values
- FORECAST: Predicted/projected values
- VARIANCE: Difference calculations
- UNKNOWN: Cannot determine type
"""

import re
from functools import lru_cache

from raglite.ingestion.classification.models import (
    ClassifiedValueType,
    PeriodType,
    ValueType,
    ValueTypeReport,
)

# Portuguese to English value type mapping
PORTUGUESE_VALUE_TYPE_MAP: dict[str, ValueType] = {
    "real": ValueType.ACTUAL,
    "actual": ValueType.ACTUAL,
    "orcamento": ValueType.BUDGET,
    "budget": ValueType.BUDGET,
    "plano": ValueType.BUDGET,
    "previsao": ValueType.FORECAST,
    "forecast": ValueType.FORECAST,
    "variacao": ValueType.VARIANCE,
    "variance": ValueType.VARIANCE,
    "var": ValueType.VARIANCE,
    "delta": ValueType.VARIANCE,
}


def classify_value_type(
    period: str,
    header: str | None = None,
    period_type: PeriodType | None = None,
) -> ClassifiedValueType:
    """Classify a period string into its value type.

    Classification hierarchy (checked first to last):
    0. Empty/whitespace/unknown patterns -> UNKNOWN
    1. period_type (if provided): BUDGET/YTD_BUDGET -> BUDGET, MONTHLY_ACTUAL/YTD_ACTUAL -> ACTUAL
    2. Period prefix/keywords: "B ", "Budget", "F ", "Forecast", "Var", "Variance", etc.
    3. Column header (secondary): "Budget", "Forecast", "Variance", "Actual"
    4. Default: ACTUAL (no modifiers present)

    Args:
        period: Period string to classify
        header: Optional column header for context
        period_type: Optional PeriodType from period_classifier

    Returns:
        ClassifiedValueType with value type and source attribution

    Examples:
        >>> classify_value_type("B Dec-21")
        ClassifiedValueType(original="B Dec-21", value_type=BUDGET, source="period_prefix")
        >>> classify_value_type("Dec-21", period_type=PeriodType.BUDGET)
        ClassifiedValueType(original="Dec-21", value_type=BUDGET, source="period_type")
        >>> classify_value_type("Dec-21", header="Forecast")
        ClassifiedValueType(original="Dec-21", value_type=FORECAST, source="header")
        >>> classify_value_type("Dec-21")
        ClassifiedValueType(original="Dec-21", value_type=ACTUAL, source="default")
    """
    # Step 0: Handle empty/whitespace/unknown patterns
    if not period or not period.strip():
        return ClassifiedValueType(
            original=period,
            value_type=ValueType.UNKNOWN,
            source="empty",
        )

    period_stripped = period.strip()

    # Check for common unknown markers
    if period_stripped.lower() in ("n/a", "none", "null", ""):
        return ClassifiedValueType(
            original=period,
            value_type=ValueType.UNKNOWN,
            source="unknown_marker",
        )

    # Check for patterns that don't match any value type (just letters/numbers without valid period format)
    # If it doesn't contain a month abbreviation pattern, it's likely invalid
    has_month_pattern = bool(
        re.search(
            r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|fev|abr|mai|ago|set|out|dez)\b",
            period_stripped,
            re.IGNORECASE,
        )
    )
    has_value_type_keyword = bool(
        re.search(
            r"\b(budget|forecast|actual|variance|orcamento|previsao|real|variacao|var|delta)\b",
            period_stripped,
            re.IGNORECASE,
        )
    )
    has_valid_prefix = bool(re.match(r"^[bf]\s", period_stripped, re.IGNORECASE))

    # If no month pattern and no value type keywords and not a valid prefix, likely unknown
    if not has_month_pattern and not has_value_type_keyword and not has_valid_prefix:
        # Check if it's just a year (4 digits) or random text
        if re.match(r"^\d{4}$", period_stripped) or not re.search(r"\d", period_stripped):
            return ClassifiedValueType(
                original=period,
                value_type=ValueType.UNKNOWN,
                source="invalid_format",
            )

    # Step 1: Use period_type if provided (highest priority)
    if period_type is not None:
        if period_type in (PeriodType.BUDGET, PeriodType.YTD_BUDGET):
            return ClassifiedValueType(
                original=period,
                value_type=ValueType.BUDGET,
                source="period_type",
            )
        elif period_type in (PeriodType.MONTHLY_ACTUAL, PeriodType.YTD_ACTUAL):
            return ClassifiedValueType(
                original=period,
                value_type=ValueType.ACTUAL,
                source="period_type",
            )

    # Step 2: Check period prefix/keywords (case-insensitive)
    period_lower = period.lower().strip()

    # Variance keywords: "Var", "%Var", "% Var", "Delta", "Variance", "Variacao", "Diff"
    # Check variance FIRST to avoid "Var vs Budget" being caught by budget keywords
    if re.match(r"^(%\s*var|var|delta)", period_lower):
        return ClassifiedValueType(
            original=period,
            value_type=ValueType.VARIANCE,
            source="period_prefix",
        )
    if re.search(r"\bvariance\b|\bvariacao\b|\bdiff\b", period_lower):
        return ClassifiedValueType(
            original=period,
            value_type=ValueType.VARIANCE,
            source="period_prefix",
        )

    # Budget keywords: "B Dec-21", "Budget Dec-21", "Orcamento Dez-21", "Dec-21 B"
    if re.match(r"^b\s", period_lower):
        return ClassifiedValueType(
            original=period,
            value_type=ValueType.BUDGET,
            source="period_prefix",
        )
    if re.search(r"\sbud(get)?\s|\sbud(get)?$|^bud(get)\s", period_lower):
        return ClassifiedValueType(
            original=period,
            value_type=ValueType.BUDGET,
            source="period_prefix",
        )
    if re.search(r"\borcamento\b|\bplano\b", period_lower):
        return ClassifiedValueType(
            original=period,
            value_type=ValueType.BUDGET,
            source="period_prefix",
        )
    # Check for "Dec-21 B" pattern (trailing B)
    if re.search(r"\s+b$", period_lower):
        return ClassifiedValueType(
            original=period,
            value_type=ValueType.BUDGET,
            source="period_prefix",
        )

    # Forecast keywords: "F Dec-21", "Forecast Dec-21", "Previsao Dez-21", "Projected Dec-21"
    if re.match(r"^f\s", period_lower):
        return ClassifiedValueType(
            original=period,
            value_type=ValueType.FORECAST,
            source="period_prefix",
        )
    if re.search(r"\bforecast\b|\bprevisao\b|\bprojected\b", period_lower):
        return ClassifiedValueType(
            original=period,
            value_type=ValueType.FORECAST,
            source="period_prefix",
        )

    # Actual keywords: "Actual Dec-21", "Real Dez-21"
    if re.search(r"\bactual\b|\breal\b", period_lower):
        return ClassifiedValueType(
            original=period,
            value_type=ValueType.ACTUAL,
            source="period_prefix",
        )

    # Step 3: Check column header if provided (secondary signal)
    if header:
        header_lower = header.lower().strip()

        # Try Portuguese mapping first
        if header_lower in PORTUGUESE_VALUE_TYPE_MAP:
            return ClassifiedValueType(
                original=period,
                value_type=PORTUGUESE_VALUE_TYPE_MAP[header_lower],
                source="column_header",
            )

        # Budget header keywords
        if re.search(r"\bbudget\b|\borcamento\b|\bplano\b", header_lower):
            return ClassifiedValueType(
                original=period,
                value_type=ValueType.BUDGET,
                source="column_header",
            )

        # Forecast header keywords
        if re.search(r"\bforecast\b|\bprevisao\b|\bprojected\b", header_lower):
            return ClassifiedValueType(
                original=period,
                value_type=ValueType.FORECAST,
                source="column_header",
            )

        # Variance header keywords
        if re.search(r"\bvariance\b|\bvariacao\b|\bdiff\b", header_lower):
            return ClassifiedValueType(
                original=period,
                value_type=ValueType.VARIANCE,
                source="column_header",
            )

        # Actual header keywords
        if re.search(r"\bactual\b|\breal\b", header_lower):
            return ClassifiedValueType(
                original=period,
                value_type=ValueType.ACTUAL,
                source="column_header",
            )

    # Step 4: Default to ACTUAL (no modifiers present)
    return ClassifiedValueType(
        original=period,
        value_type=ValueType.ACTUAL,
        source="default",
    )


# Module-level cache (persistent across calls)
@lru_cache(maxsize=10000)
def _classify_cached(
    normalized_period: str,
    normalized_header: str | None,
    period_type: PeriodType | None,
) -> ClassifiedValueType:
    """Cache wrapper for classify_value_type.

    Args:
        normalized_period: Whitespace-stripped period string
        normalized_header: Whitespace-stripped header string (or None)
        period_type: Optional PeriodType

    Returns:
        ClassifiedValueType result
    """
    return classify_value_type(normalized_period, normalized_header, period_type)


def classify_value_types_batch(
    periods: list[str],
    headers: list[str | None] | None = None,
    period_types: list[PeriodType | None] | None = None,
) -> tuple[list[ClassifiedValueType], ValueTypeReport]:
    """Classify a batch of periods with caching.

    Args:
        periods: List of period strings to classify
        headers: Optional list of column headers (same length as periods)
        period_types: Optional list of PeriodTypes (same length as periods)

    Returns:
        Tuple of (list of ClassifiedValueType, ValueTypeReport)

    Performance:
        - Caches by normalized inputs
        - Duplicate combinations classified only once
        - Target: <100ms for 1000 periods
    """
    # Initialize counters
    actual = 0
    budget = 0
    forecast = 0
    variance = 0
    unknown = 0

    results: list[ClassifiedValueType] = []

    # Handle None inputs
    if headers is None:
        headers = [None] * len(periods)
    if period_types is None:
        period_types = [None] * len(periods)

    # Validate lengths
    if len(headers) != len(periods):
        raise ValueError("headers must be same length as periods")
    if len(period_types) != len(periods):
        raise ValueError("period_types must be same length as periods")

    for period, header, p_type in zip(periods, headers, period_types, strict=False):
        # Normalize inputs for caching
        normalized_period = period.strip() if period else ""
        normalized_header = header.strip() if header else None

        # Classify with caching
        classified = _classify_cached(normalized_period, normalized_header, p_type)
        results.append(classified)

        # Update counters
        if classified.value_type == ValueType.ACTUAL:
            actual += 1
        elif classified.value_type == ValueType.BUDGET:
            budget += 1
        elif classified.value_type == ValueType.FORECAST:
            forecast += 1
        elif classified.value_type == ValueType.VARIANCE:
            variance += 1
        else:
            unknown += 1

    report = ValueTypeReport(
        total_records=len(periods),
        actual_count=actual,
        budget_count=budget,
        forecast_count=forecast,
        variance_count=variance,
        unknown_count=unknown,
    )

    return results, report
