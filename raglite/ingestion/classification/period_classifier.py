"""Period classification for ingestion pipeline.

Adapted from raglite/forecasting/timeseries/period_classification.py
with added LLM fallback and batch processing capabilities.
"""

import re
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from functools import lru_cache

from raglite.ingestion.classification.models import (
    ClassificationReport,
    ClassifiedPeriod,
    PeriodType,
)
from raglite.shared.clients import get_mistral_client
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Known non-period patterns that should be classified as UNKNOWN immediately
# These patterns trigger LLM fallback unnecessarily, causing slow classification
# Derived from actual data distribution analysis showing ~31% of "unknown" rows
KNOWN_NON_PERIOD_PATTERNS: list[re.Pattern] = [
    re.compile(r"^Var\.?$", re.IGNORECASE),  # "Var." or "Var"
    re.compile(r"^%\s*LY$", re.IGNORECASE),  # "% LY" (vs last year)
    re.compile(r"^%\s*Bud\.?$", re.IGNORECASE),  # "% Bud" or "% Bud."
    re.compile(r"^Month$", re.IGNORECASE),  # "Month" header
    re.compile(r"^YTD$", re.IGNORECASE),  # Standalone "YTD" (not "YTD Dec-24")
    re.compile(r"^Total$", re.IGNORECASE),  # "Total" rows
    re.compile(r"^Currency.*$", re.IGNORECASE),  # "Currency (1000 EUR)"
    re.compile(r"^\d+$"),  # Pure numbers like row indices
    re.compile(r"^N/?A$", re.IGNORECASE),  # "N/A" or "NA"
    re.compile(r"^-+$"),  # Dashes only
    re.compile(r"^\.+$"),  # Dots only
    re.compile(r"^\s*$"),  # Whitespace only
]


def _is_known_non_period(text: str) -> bool:
    """Check if text matches known non-period patterns.

    Args:
        text: Period string to check

    Returns:
        True if text is definitely not a period
    """
    for pattern in KNOWN_NON_PERIOD_PATTERNS:
        if pattern.match(text):
            return True
    return False


def _has_month_indicator(text: str) -> bool:
    """Check if text contains any month or date indicator.

    Used to skip LLM fallback for strings that clearly don't contain periods.

    Args:
        text: Period string to check

    Returns:
        True if text contains month names, years, or quarter indicators
    """
    month_patterns = [
        r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec",  # English months
        r"Fev|Abr|Mai|Ago|Set|Out|Dez",  # Portuguese months
        r"\d{4}",  # 4-digit year like 2024, 2025
        r"\d{2}[-/]\d{2}",  # Date patterns like 24-25 or 24/25
        r"Q[1-4]",  # Quarter indicators
    ]
    for pattern in month_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


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


def _classify_with_llm(period: str) -> PeriodType:
    """Classify ambiguous period using LLM with exponential backoff.

    Args:
        period: Period string that could not be classified by regex

    Returns:
        PeriodType (UNKNOWN if all retries exhausted)
    """
    max_retries = 3  # Initial attempt + 2 retries = 3 total
    delays = [1, 2]  # Exponential backoff: 1s, 2s (total 3s < 5s timeout)

    for attempt in range(max_retries):
        try:
            from mistralai.models import SystemMessage, UserMessage

            client = get_mistral_client()

            system_prompt = """You are a financial period classifier. Classify the period into one of:
- monthly_actual: Monthly periods like "Dec-21", "Jan-25"
- ytd_actual: Year-to-date periods like "YTD Dec-21"
- budget: Budget periods with B indicator like "B Dec-21", "Dec-21 B"
- ytd_budget: YTD budget like "YTD B Dec-21"
- unknown: Anything else

Respond with ONLY the classification type, nothing else."""

            user_prompt = f"Classify this period: {period}"

            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=user_prompt),
                ],
                temperature=0.0,
            )

            result = response.choices[0].message.content.strip().lower()

            # Map response to PeriodType
            type_map = {
                "monthly_actual": PeriodType.MONTHLY_ACTUAL,
                "ytd_actual": PeriodType.YTD_ACTUAL,
                "budget": PeriodType.BUDGET,
                "ytd_budget": PeriodType.YTD_BUDGET,
                "unknown": PeriodType.UNKNOWN,
            }

            return type_map.get(result, PeriodType.UNKNOWN)

        except Exception as e:
            logger.warning(
                "LLM classification attempt failed",
                extra={
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "period": period,
                    "error": str(e),
                },
            )

            # If not last retry, wait with exponential backoff
            if attempt < max_retries - 1:
                time.sleep(delays[attempt])

    # All retries exhausted
    logger.error(
        "LLM classification failed after all retries",
        extra={"period": period, "max_retries": max_retries},
    )

    return PeriodType.UNKNOWN


def classify_period(period: str | None) -> ClassifiedPeriod:
    """Classify a period string into its type.

    Classification order (checked first to last):
    1. Empty/null -> UNKNOWN
    2. "YTD B " prefix -> YTD_BUDGET (excluded)
    3. "B " prefix or " B " or " B" suffix -> BUDGET (excluded)
    4. "YTD " prefix with Mon-YY -> YTD_ACTUAL
    5. Plain Mon-YY format -> MONTHLY_ACTUAL
    6. Everything else -> UNKNOWN (with optional LLM fallback)

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

    # Strip regular spaces and NBSP (non-breaking space U+00A0)
    period = period.strip().replace("\u00a0", " ").strip()

    # Step 2: Check for YTD Budget patterns
    # Patterns: "YTD B Dec-21", "YTD Budget 2025", "YTD Budget Dec-21"
    if re.match(r"^YTD\s+(B\s|Budget\s+)", period, re.IGNORECASE):
        return ClassifiedPeriod(
            original=period,
            period_type=PeriodType.YTD_BUDGET,
            normalized=None,
            is_usable=False,
        )

    # Step 3: Check for Budget patterns
    # Patterns: "B Dec-21", "Budget 2025", "Dec-21 B", "Jan B 25"
    if re.match(r"^(B\s|Budget\s+)", period, re.IGNORECASE):
        return ClassifiedPeriod(
            original=period,
            period_type=PeriodType.BUDGET,
            normalized=None,
            is_usable=False,
        )
    if re.search(r"\sB\s", period, re.IGNORECASE):  # Matches "Jan B 25" format
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

    # Step 6: Fast-path for known non-period patterns
    # Skip LLM entirely for patterns like "Var.", "% LY", pure numbers, etc.
    if _is_known_non_period(period):
        return ClassifiedPeriod(
            original=period,
            period_type=PeriodType.UNKNOWN,
            normalized=None,
            is_usable=False,
        )

    # Step 7: Skip LLM if no month/date indicators present
    # Strings without months/years/quarters can't be valid periods
    if not _has_month_indicator(period):
        return ClassifiedPeriod(
            original=period,
            period_type=PeriodType.UNKNOWN,
            normalized=None,
            is_usable=False,
        )

    # Step 8: Everything else - attempt LLM classification
    # This includes: "2017 P", year-only formats, complex date cases, etc.
    # Per AC3: Try LLM classification for ambiguous cases
    # Per AC4: Catch all exceptions and enforce 5s timeout (no pipeline blocking)
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        # AC4.1: Enforce <5s timeout for LLM classification (4.9s to account for overhead)
        future = executor.submit(_classify_with_llm, period)
        llm_result = future.result(timeout=4.9)
    except (FuturesTimeoutError, TimeoutError) as e:
        logger.warning(
            "LLM classification timed out",
            extra={"period": period, "error": str(e), "timeout_seconds": 4.9},
        )
        llm_result = PeriodType.UNKNOWN
    except Exception as e:
        logger.warning(
            "LLM classification failed",
            extra={"period": period, "error": str(e), "error_type": type(e).__name__},
        )
        llm_result = PeriodType.UNKNOWN
    finally:
        # Don't wait for executor shutdown - abandon thread if it timed out
        executor.shutdown(wait=False)

    if llm_result != PeriodType.UNKNOWN:
        # LLM successfully classified - return with is_usable based on type
        is_usable = llm_result in {PeriodType.MONTHLY_ACTUAL, PeriodType.YTD_ACTUAL}
        return ClassifiedPeriod(
            original=period,
            period_type=llm_result,
            normalized=None,  # LLM doesn't provide normalized form
            is_usable=is_usable,
        )

    # LLM also failed - return UNKNOWN
    return ClassifiedPeriod(
        original=period,
        period_type=PeriodType.UNKNOWN,
        normalized=None,
        is_usable=False,
    )


# Module-level cache (persistent across calls)
@lru_cache(maxsize=10000)
def _classify_cached(normalized_period: str | None) -> ClassifiedPeriod:
    """Cache wrapper for classify_period.

    Args:
        normalized_period: Whitespace-stripped period string

    Returns:
        ClassifiedPeriod result
    """
    return classify_period(normalized_period)


def classify_periods_batch(periods: list[str | None]) -> ClassificationReport:
    """Classify a batch of periods with caching.

    Args:
        periods: List of period strings to classify

    Returns:
        ClassificationReport with counts by type

    Performance:
        - Caches by normalized input (whitespace-stripped)
        - Duplicate periods classified only once
        - Target: <500ms for 1000 periods
    """
    monthly_actual = 0
    ytd_actual = 0
    budget = 0
    ytd_budget = 0
    unknown = 0

    for period in periods:
        # Normalize input for caching (strip whitespace)
        normalized_input = period.strip() if period else None
        classified = _classify_cached(normalized_input)

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
