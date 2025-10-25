"""Query classifier for multi-index routing and metadata extraction.

This module provides two types of query classification:
  1. Query Type Classification (Story 2.7): Route queries to appropriate index
     (VECTOR_ONLY, SQL_ONLY, or HYBRID)
  2. Metadata Extraction (Story 2.4): Extract metadata filters from natural language

Story 2.7: Heuristic-based query type classification for multi-index search
Story 2.4: LLM-based metadata extraction for filtered retrieval

Research Validation:
    - FinRAG (EMNLP 2024): 40% reduction in hallucinations via metadata-driven retrieval
    - RAF (ACL 2025): Schema-aware hashing for tabular time series retrieval
    - Expected accuracy gain: +20-25% over baseline semantic search
"""

import json
import logging
import re
import time
from enum import Enum

from mistralai import Mistral

from raglite.shared.config import settings

logger = logging.getLogger(__name__)


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


async def classify_query_metadata(query: str) -> dict[str, str]:
    """Extract metadata filters from natural language query using Mistral Small.

    Uses FREE Mistral Small API with JSON mode for zero-cost query classification.
    Extracts relevant metadata fields from the 15-field rich schema based on
    query content and intent.

    Args:
        query: Natural language financial query (e.g., "What is the variable cost
               per ton for Portugal Cement in August 2025 YTD?")

    Returns:
        Dictionary of metadata field filters (only populated fields included).
        Empty dict if no metadata can be extracted.

        Example:
            {
                "metric_category": "Operating Expenses",
                "company_name": "Portugal Cement",
                "time_granularity": "YTD",
                "reporting_period": "Aug-25"
            }

    Raises:
        Exception: If Mistral API call fails (gracefully degrades to no filters)
    """
    logger.debug("Classifying query for metadata extraction", extra={"query": query[:100]})

    start_time = time.time()

    try:
        # Initialize Mistral client
        client = Mistral(api_key=settings.mistral_api_key)

        # Query classification prompt (optimized for financial document metadata)
        from typing import Any

        from mistralai.models import SystemMessage, UserMessage

        messages: list[Any] = [
            SystemMessage(
                content=(
                    "Extract metadata filters from financial document queries for RAG retrieval.\n"
                    "Return ONLY valid JSON with relevant fields. Use ONLY fields with clear evidence in query.\n"
                    "Omit fields with no evidence. Return {} if no metadata detected.\n\n"
                    "AVAILABLE FIELDS (15 total - only use when query clearly indicates):\n\n"
                    "DOCUMENT-LEVEL (7 fields):\n"
                    "- document_type: Income Statement | Balance Sheet | Cash Flow Statement | "
                    "Operational Report | Earnings Call | Management Discussion | Financial Notes\n"
                    "- reporting_period: Q1 2024 | Aug-25 | Aug-25 YTD | FY 2023 | 2024 Annual | H1 2025\n"
                    "- time_granularity: Daily | Weekly | Monthly | Quarterly | YTD | Annual | Rolling 12-Month\n"
                    "- company_name: Portugal Cement | CIMPOR | Cimpor Trading | InterCement | Secil | "
                    "Secil Group | Tunisia Cement\n"
                    "- geographic_jurisdiction: Portugal | EU | APAC | Americas | Global | Tunisia | Angola | Lebanon\n"
                    "- data_source_type: Audited | Internal Report | Regulatory Filing | Management Estimate | Preliminary\n"
                    "- version_date: 2025-08-15 | 2024-Q3-Final | 2024-12-31-Revised\n\n"
                    "SECTION-LEVEL (5 fields):\n"
                    "- section_type: Narrative | Table | Footnote | Chart Caption | Summary | List | Formula\n"
                    "- metric_category: Revenue | EBITDA | Operating Expenses | Capital Expenditure | Cash Flow | "
                    "Assets | Liabilities | Equity | Ratios | Production Volume | Cost per Unit\n"
                    "- units: EUR | USD | GBP | EUR/ton | USD/MWh | Percentage | Count | Tonnes | MWh | m³\n"
                    "- department_scope: Operations | Finance | Production | Sales | Corporate | HR | IT | Supply Chain\n\n"
                    "TABLE-SPECIFIC (3 fields - ONLY for explicit table requests):\n"
                    "- table_context: Brief keywords about table content (NOT full description)\n"
                    "- table_name: Table title keywords (e.g., 'Variable Costs', 'EBITDA Breakdown')\n"
                    "- statistical_summary: Statistical keywords (e.g., 'Mean', 'Trend', 'Variance')\n\n"
                    "EXAMPLES:\n\n"
                    "Query: 'What is the variable cost per ton for Portugal Cement in August 2025 YTD?'\n"
                    'Output: {"metric_category": "Operating Expenses", "company_name": "Portugal Cement", '
                    '"time_granularity": "YTD", "reporting_period": "Aug-25", "units": "EUR/ton"}\n\n'
                    "Query: 'Show me EBITDA margin for Portugal operations'\n"
                    'Output: {"metric_category": "EBITDA", "geographic_jurisdiction": "Portugal"}\n\n'
                    "Query: 'What are the thermal energy costs?'\n"
                    'Output: {"metric_category": "Operating Expenses"}\n\n'
                    "Query: 'What is the total revenue?'\n"
                    'Output: {"metric_category": "Revenue"}\n\n'
                    "Query: 'Show financial tables'\n"
                    'Output: {"section_type": "Table"}\n\n'
                    "Query: 'How many employees work in Tunisia?'\n"
                    'Output: {"geographic_jurisdiction": "Tunisia", "department_scope": "HR"}\n\n'
                    "Query: 'Explain the cash flow statement'\n"
                    'Output: {"document_type": "Cash Flow Statement"}\n\n'
                    "RULES:\n"
                    "- Only include fields with CLEAR evidence in query\n"
                    "- Cost/expense queries → metric_category: 'Operating Expenses'\n"
                    "- Revenue queries → metric_category: 'Revenue'\n"
                    "- Margin/profitability queries → metric_category: 'EBITDA'\n"
                    "- Company names → Exact match from list above\n"
                    "- Dates → Normalize to format (e.g., 'August 2025' → 'Aug-25')\n"
                    "- YTD/Annual/Quarterly → time_granularity field\n"
                    "- Return {} if query is too general or no metadata evident"
                )
            ),
            UserMessage(content=f"Extract metadata filters from this query:\n\n{query}"),
        ]

        response = client.chat.complete(
            model=settings.metadata_extraction_model,  # "mistral-small-latest" (FREE)
            messages=messages,
            response_format={
                "type": "json_object"  # JSON mode (Mistral's structured output)
            },
            temperature=0,  # Deterministic classification
            max_tokens=300,  # Sufficient for filter dict
        )

        # Parse JSON response
        response_content = response.choices[0].message.content
        if not response_content:
            logger.warning("Empty response from Mistral query classifier")
            return {}

        # Type guard: ensure response_content is a string before json.loads
        if not isinstance(response_content, str):
            logger.warning("Response content is not a string, cannot parse JSON")
            return {}

        filters = json.loads(response_content)

        # Remove None/null values
        filters = {k: v for k, v in filters.items() if v is not None and v != ""}

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "Query metadata classification complete",
            extra={
                "query": query[:100],
                "extracted_filters": filters,
                "filter_count": len(filters),
                "model": settings.metadata_extraction_model,
                "duration_ms": duration_ms,
                "estimated_cost_usd": 0.0,  # Mistral Small is FREE
            },
        )

        return dict(filters)  # Explicitly convert to dict for mypy

    except json.JSONDecodeError as e:
        logger.warning(
            "Failed to parse metadata filters from Mistral response",
            extra={"error": str(e), "query": query[:100]},
        )
        return {}

    except Exception as e:
        logger.error(
            "Query metadata classification failed - degrading to no filters",
            extra={"error": str(e), "query": query[:100]},
        )
        return {}


def classify_query(query: str) -> QueryType:
    """Classify query type for multi-index routing using heuristic rules.

    Story 2.7 AC1: Fast heuristic-based classification (<50ms) to route queries
    to appropriate retrieval index(es). No LLM overhead for latency optimization.

    Classification Logic:
      1. SQL_ONLY: Table-heavy queries requiring precise data lookups
         - Keywords: table, row, column, cell, exact, precise, specific
         - Numeric references: $1.2M, 15%, Q3 2024, etc.
         - "What is..." or "Show me..." patterns

      2. VECTOR_ONLY: Semantic/conceptual queries
         - Keywords: explain, summarize, why, describe, compare, analyze
         - Multi-paragraph understanding required
         - No numeric precision needed

      3. HYBRID: Combination queries needing both context and precision
         - Semantic keywords + numeric references
         - Example: "Why did revenue increase 15% in Q3?"

    Args:
        query: Natural language query string

    Returns:
        QueryType enum (VECTOR_ONLY, SQL_ONLY, or HYBRID)

    Example:
        >>> classify_query("What is the exact revenue in Q3 2024?")
        QueryType.SQL_ONLY

        >>> classify_query("Explain the company's growth strategy")
        QueryType.VECTOR_ONLY

        >>> classify_query("Why did EBITDA increase 15% last quarter?")
        QueryType.HYBRID
    """
    query_lower = query.lower()

    # Heuristic patterns (use word boundaries for accurate matching)
    table_keywords = [r"\btable\b", r"\brow\b", r"\bcolumn\b", r"\bcell\b"]
    precision_keywords = [r"\bexact\b", r"\bprecise\b", r"\bspecific\b"]
    semantic_keywords = [
        r"\bexplain\b",
        r"\bsummarize\b",
        r"\bwhy\b",
        r"\bdescribe\b",
        r"\bcompare\b",
        r"\banalyze\b",
        r"\bhow\b",
    ]

    # Enhanced numeric pattern to catch more formats
    # Matches: 15%, $1.2M, 23.5 EUR/ton, 500K, Q3, 2024, etc.
    numeric_patterns = [
        r"\d+\.?\d*\s*%",  # 15%, 10.5%
        r"\$\d+\.?\d*[MBK]?",  # $1.2M, $500K
        r"\d+\.?\d*\s+(eur|usd|gbp|ton|tonnes|mwh)",  # 23.5 EUR, 500 tonnes
        r"\d+[KM]\s+(tonnes|units|items)",  # 500K tonnes
        r"Q[1-4]",  # Q1, Q3, etc.
        r"\b(19|20)\d{2}\b",  # Years: 2024, 2023, etc.
    ]

    question_patterns = ["what is", "show me", "give me", "display", "list"]

    # Count matches using regex for word boundaries
    has_table_keywords = any(bool(re.search(keyword, query_lower)) for keyword in table_keywords)
    has_precision_keywords = any(
        bool(re.search(keyword, query_lower)) for keyword in precision_keywords
    )
    has_semantic_keywords = any(
        bool(re.search(keyword, query_lower)) for keyword in semantic_keywords
    )
    has_numeric_refs = any(
        bool(re.search(pattern, query_lower, re.IGNORECASE)) for pattern in numeric_patterns
    )
    has_precision_question = any(pattern in query_lower for pattern in question_patterns)

    # Classification logic with improved scoring
    # Priority: Table keywords are strongest SQL_ONLY indicator
    # HYBRID requires semantic keywords + data indicators (but NOT if table keyword present)

    if has_table_keywords:
        # Table keywords are strong SQL_ONLY indicators UNLESS there are semantic keywords
        if has_semantic_keywords:
            result = QueryType.HYBRID
        else:
            result = QueryType.SQL_ONLY
    elif has_semantic_keywords:
        # Semantic keywords present
        if has_numeric_refs or has_precision_question:
            result = QueryType.HYBRID  # Semantic + data = HYBRID
        else:
            result = QueryType.VECTOR_ONLY  # Pure semantic
    elif has_precision_keywords or (has_precision_question and has_numeric_refs):
        # Precision indicators without semantic → SQL_ONLY
        result = QueryType.SQL_ONLY
    elif has_numeric_refs or has_precision_question:
        # Some data indicators → SQL_ONLY
        result = QueryType.SQL_ONLY
    else:
        # Default to VECTOR_ONLY (safe default)
        result = QueryType.VECTOR_ONLY

    logger.debug(
        "Query classified",
        extra={
            "query": query[:100],
            "classification": result.value,
            "has_semantic_keywords": has_semantic_keywords,
            "has_table_keywords": has_table_keywords,
            "has_numeric_refs": has_numeric_refs,
        },
    )

    return result
