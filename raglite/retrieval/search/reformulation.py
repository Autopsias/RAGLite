"""Query reformulation and fallback chain for RAGLite.

Provides automatic query reformulation when SQL searches return 0 results,
using synonym expansion and time period removal strategies.
"""

import re

from raglite.ingestion.entity_normalizer import expand_entity_synonyms
from raglite.retrieval.query_classifier import (
    expand_metric_synonyms,
    generate_sql_query,
)
from raglite.retrieval.sql_table_search import search_tables_sql
from raglite.shared.logging import get_logger
from raglite.shared.models import QueryResult

logger = get_logger(__name__)

# Time period patterns for fallback 3 (query reformulation)
TIME_PERIOD_PATTERNS = [
    r"\bin\s+\d{4}\b",  # "in 2024"
    r"\bfor\s+\d{4}\b",  # "for 2024"
    r"\bfor\s+Q[1-4]\b",  # "for Q3"
    r"\bin\s+Q[1-4]\b",  # "in Q1"
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}\b",
    r"\b\d{4}\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b",
    r"\bQ[1-4]\s+\d{4}\b",  # "Q3 2024"
    r"\b\d{4}\s+Q[1-4]\b",  # "2024 Q3"
    r"\blast\s+year\b",  # "last year"
    r"\bthis\s+year\b",  # "this year"
    r"\blast\s+quarter\b",  # "last quarter"
    r"\bthis\s+quarter\b",  # "this quarter"
]


def _remove_time_periods(query: str) -> str:
    """Remove time period references from query for fallback 3.

    Args:
        query: Original query with time references

    Returns:
        Query with time references removed

    Example:
        >>> _remove_time_periods("What is EBITDA for Q3 2024?")
        "What is EBITDA?"
    """
    result = query
    for pattern in TIME_PERIOD_PATTERNS:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)
    # Clean up extra whitespace
    result = re.sub(r"\s+", " ", result).strip()
    # Clean up dangling punctuation
    result = re.sub(r"\s+\?$", "?", result)
    result = re.sub(r"\s+\.$", ".", result)
    return result


async def reformulate_query(
    original_query: str,
    fallback_level: int = 1,
) -> tuple[str, str]:
    """Reformulate query using fallback chain when SQL returns 0 rows.

    Story 5.0.7 Phase 5.3: Implements 3-stage fallback chain for query reformulation.

    Fallback Chain:
        1. Fallback 1: Expand metric synonyms (e.g., "petcoke" -> "Petcoke Consumption")
        2. Fallback 2: Expand entity synonyms (e.g., "PT" -> "Portugal")
        3. Fallback 3: Remove time period filters (e.g., "for Q3 2024" -> "")

    Args:
        original_query: Original query that returned 0 results
        fallback_level: Which fallback to apply (1, 2, or 3)

    Returns:
        Tuple of (reformulated_query, fallback_description)

    Example:
        >>> query, desc = await reformulate_query("What is petcoke for Q3?", 1)
        >>> # query: "What is Petcoke Consumption for Q3?"
        >>> # desc: "metric_synonym_expansion"
    """
    if fallback_level == 1:
        # Fallback 1: Expand metric synonyms
        synonyms = expand_metric_synonyms(original_query)
        if synonyms:
            # Add first synonym to query for broader matching
            expanded = f"{original_query} {' '.join(synonyms[:3])}"
            logger.info(
                "Query reformulation: metric synonym expansion",
                extra={
                    "original": original_query[:50],
                    "synonyms_added": synonyms[:3],
                    "fallback_level": 1,
                },
            )
            return expanded, "metric_synonym_expansion"
        # No synonyms found, return original
        return original_query, "no_metric_synonyms"

    elif fallback_level == 2:
        # Fallback 2: Expand entity synonyms
        entity_synonyms = expand_entity_synonyms(original_query)
        if entity_synonyms:
            # Add entity variations to query
            expanded = f"{original_query} {' '.join(entity_synonyms[:3])}"
            logger.info(
                "Query reformulation: entity synonym expansion",
                extra={
                    "original": original_query[:50],
                    "entities_added": entity_synonyms[:3],
                    "fallback_level": 2,
                },
            )
            return expanded, "entity_synonym_expansion"
        # No entity synonyms found, return original
        return original_query, "no_entity_synonyms"

    elif fallback_level == 3:
        # Fallback 3: Remove time period filters
        stripped = _remove_time_periods(original_query)
        if stripped != original_query:
            logger.info(
                "Query reformulation: time period removal",
                extra={
                    "original": original_query[:50],
                    "stripped": stripped[:50],
                    "fallback_level": 3,
                },
            )
            return stripped, "time_period_removal"
        # No time periods to remove
        return original_query, "no_time_periods"

    # Invalid fallback level
    return original_query, "invalid_fallback_level"


async def search_with_reformulation(
    query: str,
    top_k: int = 5,
    max_fallbacks: int = 3,
) -> tuple[list[QueryResult], str | None]:
    """Execute SQL search with automatic query reformulation fallback chain.

    Story 5.0.7 Phase 5.3: Wraps SQL table search with automatic reformulation
    when initial query returns 0 results.

    Args:
        query: Natural language query
        top_k: Number of results to return
        max_fallbacks: Maximum number of reformulation attempts (default: 3)

    Returns:
        Tuple of (results, successful_reformulation_type)
        - results: List of QueryResult objects
        - successful_reformulation_type: Which fallback succeeded (or None if original worked)

    Example:
        >>> results, reformulation = await search_with_reformulation(
        ...     "What is petcoke consumption for Q3 2024?", top_k=5
        ... )
        >>> if reformulation:
        ...     print(f"Found via: {reformulation}")
    """
    # Try original query first
    sql = await generate_sql_query(query)
    if sql:
        results = await search_tables_sql(sql, top_k=top_k)
        if results:
            logger.info(
                "SQL search succeeded with original query",
                extra={"query": query[:50], "results_count": len(results)},
            )
            return results, None

    # Original query returned 0 results - try reformulation chain
    logger.info(
        "SQL returned 0 results - starting reformulation fallback chain",
        extra={"query": query[:50], "max_fallbacks": max_fallbacks},
    )

    for fallback_level in range(1, max_fallbacks + 1):
        reformulated, fallback_type = await reformulate_query(query, fallback_level)

        # Skip if reformulation didn't change the query
        if reformulated == query or fallback_type.startswith("no_"):
            logger.debug(
                f"Fallback {fallback_level} skipped (no change)",
                extra={"fallback_type": fallback_type},
            )
            continue

        # Try reformulated query
        sql = await generate_sql_query(reformulated)
        if sql:
            results = await search_tables_sql(sql, top_k=top_k)
            if results:
                logger.info(
                    "Query reformulation succeeded",
                    extra={
                        "original_query": query[:50],
                        "reformulated_query": reformulated[:50],
                        "fallback_level": fallback_level,
                        "fallback_type": fallback_type,
                        "results_count": len(results),
                    },
                )
                return results, fallback_type

        logger.debug(
            f"Fallback {fallback_level} did not produce results",
            extra={"fallback_type": fallback_type},
        )

    # All fallbacks exhausted - return empty with helpful message
    logger.warning(
        "All query reformulation fallbacks exhausted",
        extra={"query": query[:50], "fallbacks_tried": max_fallbacks},
    )
    return [], None
