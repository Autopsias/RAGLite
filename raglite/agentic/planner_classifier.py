"""Query complexity classification for workflow planning."""

import logging
import re

from raglite.agentic.planner_models import QueryComplexity

logger = logging.getLogger(__name__)

# Keywords that indicate analytical/multi-step queries (module-level constant)
ANALYTICAL_KEYWORDS: frozenset[str] = frozenset(
    {
        # Calculation keywords
        "calculate",
        "compute",
        "determine",
        # Growth/change keywords
        "growth",
        "grow",
        "grew",
        "change",
        "increase",
        "increased",
        "decrease",
        "decreased",
        "yoy",
        "year-over-year",
        "quarter-over-quarter",
        "qoq",
        # Variance/analysis keywords
        "variance",
        "difference",
        "delta",
        "deviation",
        # Trend keywords
        "trend",
        "pattern",
        "forecast",
        "predict",
        "projection",
        # Comparison keywords
        "compare",
        "comparison",
        "versus",
        "vs",
        "vs.",
        "between",
        # Explanation/reasoning keywords
        "explain",
        "why",
        "reason",
        "cause",
        "driver",
        "impact",
        # Analysis keywords
        "analyze",
        "analysis",
        "assess",
        "evaluate",
        # Percentage/ratio keywords
        "percentage",
        "percent",
        "%",
        "ratio",
        "margin",
        "rate",
        # Superlative keywords
        "highest",
        "lowest",
        "strongest",
        "weakest",
        "best",
        "worst",
        "greatest",
        "least",
        "most",
        "fewest",
        "largest",
        "smallest",
        "maximum",
        "minimum",
        # Ranking keywords
        "top",
        "bottom",
        "rank",
        "ranking",
        "ranked",
        "leading",
        "trailing",
        "first",
        "last",
        # Comparative keywords
        "better",
        "worse",
        "higher",
        "lower",
        "more than",
        "less than",
        "greater than",
        "smaller than",
        "relative to",
        "compared to",
        "outperform",
        "underperform",
    }
)

# Regex patterns for analytical query detection
SUPERLATIVE_PATTERN = re.compile(
    r"\b(which|what|who|show|list|identify)\b.*(strongest|highest|lowest|best|worst|top|most|least|greatest|largest|smallest)\b"
)
TOP_N_PATTERN = re.compile(r"\b(top|bottom)\s+\d+\b|rank(ed|ing)?\s+(the\s+)?[a-z]+")


async def classify_query_complexity(query: str) -> QueryComplexity:
    """Classify query as simple or analytical based on keyword matching (AC1).

    This classifier distinguishes between:
    - **Simple queries:** Direct retrieval (e.g., "What is revenue?")
    - **Analytical queries:** Multi-step reasoning (e.g., "Calculate YoY growth")

    Args:
        query: Natural language user query

    Returns:
        QueryComplexity.SIMPLE or QueryComplexity.ANALYTICAL

    AC1: Classifier accuracy >90% on test queries from ground truth set
    """
    query_lower = query.lower()

    # Check if any analytical keyword is present
    if any(keyword in query_lower for keyword in ANALYTICAL_KEYWORDS):
        return QueryComplexity.ANALYTICAL

    # Pattern detection: Superlative questions
    if SUPERLATIVE_PATTERN.search(query_lower):
        logger.debug(f"Query classified as ANALYTICAL via superlative pattern: '{query[:50]}...'")
        return QueryComplexity.ANALYTICAL

    # Pattern detection: Top-N queries
    if TOP_N_PATTERN.search(query_lower):
        logger.debug(f"Query classified as ANALYTICAL via top-N/ranking pattern: '{query[:50]}...'")
        return QueryComplexity.ANALYTICAL

    return QueryComplexity.SIMPLE
