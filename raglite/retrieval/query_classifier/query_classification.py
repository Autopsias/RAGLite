"""Query type classification for multi-index routing.

Story 2.7: Heuristic-based query type classification for multi-index search.
Story 2.10: Tightened SQL routing to reduce over-routing.
"""

import logging
import re
from enum import Enum

# Import from new modules
from raglite.retrieval.query_classifier.patterns import (
    METRIC_PATTERNS,
    NUMERIC_PATTERNS,
    PRECISION_KEYWORDS,
    SEMANTIC_KEYWORDS,
    TABLE_KEYWORDS,
    TEMPORAL_PATTERNS,
)
from raglite.retrieval.query_classifier.synonyms import (
    METRIC_SYNONYMS,
    expand_metric_synonyms,
    get_metric_ilike_pattern,
)

logger = logging.getLogger(__name__)


# Re-export for backward compatibility
__all__ = [
    "METRIC_SYNONYMS",
    "QueryType",
    "classify_query",
    "expand_metric_synonyms",
    "get_metric_ilike_pattern",
]


class QueryType(Enum):
    """Query type for multi-index routing (Story 2.7).

    Determines which index(es) to use for retrieval:
      - VECTOR_ONLY: Semantic search only (Qdrant)
      - SQL_ONLY: Table search only (PostgreSQL)
      - HYBRID: Both indexes with result fusion
    """

    VECTOR_ONLY = "vector_only"
    SQL_ONLY = "sql_only"
    HYBRID = "hybrid"


class _QueryFeatures:
    """Container for detected query features."""

    def __init__(
        self,
        has_table_keywords: bool,
        has_precision_keywords: bool,
        has_semantic_keywords: bool,
        has_numeric_refs: bool,
        has_temporal_terms: bool,
        has_metric_terms: bool,
    ):
        self.has_table_keywords = has_table_keywords
        self.has_precision_keywords = has_precision_keywords
        self.has_semantic_keywords = has_semantic_keywords
        self.has_numeric_refs = has_numeric_refs
        self.has_temporal_terms = has_temporal_terms
        self.has_metric_terms = has_metric_terms


def _detect_query_features(query_lower: str) -> _QueryFeatures:
    """Detect presence of various query features using regex patterns.

    Args:
        query_lower: Lowercased query string

    Returns:
        _QueryFeatures object with boolean flags for each detected feature
    """
    has_table_keywords = any(bool(re.search(keyword, query_lower)) for keyword in TABLE_KEYWORDS)
    has_precision_keywords = any(
        bool(re.search(keyword, query_lower)) for keyword in PRECISION_KEYWORDS
    )
    has_semantic_keywords = any(
        bool(re.search(keyword, query_lower)) for keyword in SEMANTIC_KEYWORDS
    )
    has_numeric_refs = any(
        bool(re.search(pattern, query_lower, re.IGNORECASE)) for pattern in NUMERIC_PATTERNS
    )
    has_temporal_terms = any(
        bool(re.search(pattern, query_lower, re.IGNORECASE)) for pattern in TEMPORAL_PATTERNS
    )
    has_metric_terms = any(
        bool(re.search(pattern, query_lower, re.IGNORECASE)) for pattern in METRIC_PATTERNS
    )

    return _QueryFeatures(
        has_table_keywords=has_table_keywords,
        has_precision_keywords=has_precision_keywords,
        has_semantic_keywords=has_semantic_keywords,
        has_numeric_refs=has_numeric_refs,
        has_temporal_terms=has_temporal_terms,
        has_metric_terms=has_metric_terms,
    )


def _determine_query_type(features: _QueryFeatures) -> QueryType:
    """Determine query type based on detected features.

    Story 2.10 Logic: Tightened SQL routing to reduce over-routing.
    Requires BOTH metric AND temporal for SQL_ONLY routing.

    Args:
        features: Detected query features

    Returns:
        QueryType enum (VECTOR_ONLY, SQL_ONLY, or HYBRID)
    """
    if features.has_table_keywords:
        # Strong SQL indicator UNLESS semantic keywords present
        if features.has_semantic_keywords:
            return QueryType.HYBRID  # Table + semantic = HYBRID
        else:
            return QueryType.SQL_ONLY  # Pure table query

    elif features.has_semantic_keywords:
        # Semantic keywords present
        if features.has_metric_terms or features.has_temporal_terms or features.has_numeric_refs:
            return QueryType.HYBRID  # Semantic + data = HYBRID
        else:
            return QueryType.VECTOR_ONLY  # Pure semantic

    elif features.has_metric_terms and features.has_temporal_terms:
        # Story 2.10: Require BOTH metric AND temporal for SQL_ONLY
        return QueryType.SQL_ONLY

    elif (
        features.has_precision_keywords
        and features.has_metric_terms
        and features.has_temporal_terms
    ):
        # Precision + metric + temporal (all three) → SQL_ONLY
        return QueryType.SQL_ONLY

    else:
        # DEFAULT: HYBRID for ambiguous cases (Story 2.10 change)
        return QueryType.HYBRID


def classify_query(query: str) -> QueryType:
    """Classify query type for multi-index routing using heuristic rules.

    Story 2.7 AC1: Fast heuristic-based classification (<50ms) to route queries
    to appropriate retrieval index(es). No LLM overhead for latency optimization.

    Story 2.10 Update: Tightened SQL routing to reduce over-routing from 48% → 8%.
    Now requires BOTH metric indicators AND temporal terms for SQL_ONLY routing.

    Classification Logic (Story 2.10 revised):
      1. SQL_ONLY: Table-heavy or metric+temporal queries requiring precise data lookups
         - Table keywords: table, row, column, cell
         - Metric + Temporal: "EBITDA for Q3 2024", "revenue in August 2025"
         - Precision keywords with data: "exact revenue for Q3"

      2. VECTOR_ONLY: Pure semantic/conceptual queries
         - Keywords: explain, summarize, why, describe, compare, analyze
         - No metric/temporal/numeric indicators
         - Example: "Explain the growth strategy"

      3. HYBRID: Ambiguous or combined queries (NEW DEFAULT)
         - Semantic + data indicators: "Why did revenue increase?"
         - Metric OR temporal (not both): "What is EBITDA?", "What happened in Q3?"
         - Default for unclear cases (safer fallback with graceful degradation)

    Args:
        query: Natural language query string

    Returns:
        QueryType enum (VECTOR_ONLY, SQL_ONLY, or HYBRID)

    Example:
        >>> classify_query("What is EBITDA margin for Q3 2024?")
        QueryType.SQL_ONLY  # metric + temporal

        >>> classify_query("What is EBITDA?")
        QueryType.HYBRID  # metric only, no temporal

        >>> classify_query("Explain the company's growth strategy")
        QueryType.VECTOR_ONLY  # pure semantic

        >>> classify_query("Why did revenue increase last quarter?")
        QueryType.HYBRID  # semantic + metric + temporal
    """
    query_lower = query.lower()

    # Detect query features using extracted helper
    features = _detect_query_features(query_lower)

    # Determine query type based on features
    result = _determine_query_type(features)

    # Log classification decision
    logger.debug(
        "Query classified",
        extra={
            "query": query[:100],
            "classification": result.value,
            "has_semantic_keywords": features.has_semantic_keywords,
            "has_table_keywords": features.has_table_keywords,
            "has_numeric_refs": features.has_numeric_refs,
            "has_temporal_terms": features.has_temporal_terms,
            "has_metric_terms": features.has_metric_terms,
        },
    )

    return result
