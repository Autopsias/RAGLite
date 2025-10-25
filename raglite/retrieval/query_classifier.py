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

    # NEW: Temporal term patterns (Story 2.10 AC1)
    # Distinguishes temporal queries requiring structured table search from general semantic queries
    temporal_patterns = [
        # Explicit periods
        r"\bQ[1-4]\b",  # Q1, Q2, Q3, Q4
        r"\b(19|20)\d{2}\b",  # 2024, 2023, etc.
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-\s]?\d{2,4}\b",  # Aug-25, Aug 2025
        # Granularity terms
        r"\bYTD\b",  # Year-to-date
        r"\bH[1-2]\b",  # H1, H2 (half-year)
        r"\bFY\s*\d{2,4}\b",  # FY 2024, FY24
        # Relative temporal
        r"\blast\s+(quarter|year|month|week)\b",
        r"\bthis\s+(quarter|year|month|week)\b",
        r"\bprevious\s+(quarter|year|month|period)\b",
        r"\bnext\s+(quarter|year|month)\b",
        # Temporal modifiers
        r"\bcurrent\b",
        r"\blatest\b",
        r"\brecent\b",
        r"\bhistorical\b",
        # Date formats
        r"\d{4}-\d{2}-\d{2}\b",  # 2024-08-15
        r"\d{2}/\d{2}/\d{4}\b",  # 08/15/2024
    ]

    # NEW: Metric/financial term patterns (Story 2.10 AC1)
    # Financial and operational metrics that benefit from structured table search
    metric_patterns = [
        # Financial metrics
        r"\b(revenue|ebitda|profit|margin|cost|expense|capex|opex)\b",
        r"\b(cash\s+flow|balance\s+sheet|income\s+statement)\b",
        r"\b(assets|liabilities|equity|ratios)\b",
        # Operational metrics
        r"\b(production|volume|capacity|headcount|fte|employees)\b",
        r"\b(efficiency|utilization|throughput|output)\b",
        # Cost metrics
        r"\b(variable\s+cost|fixed\s+cost|unit\s+cost|per\s+ton)\b",
        r"\b(raw\s+materials?|packaging|energy|electricity|thermal)\b",
    ]

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

    # NEW: Check for temporal and metric terms (Story 2.10 AC1)
    has_temporal_terms = any(
        bool(re.search(pattern, query_lower, re.IGNORECASE)) for pattern in temporal_patterns
    )
    has_metric_terms = any(
        bool(re.search(pattern, query_lower, re.IGNORECASE)) for pattern in metric_patterns
    )

    # Story 2.10: Tightened classification logic
    # Priority: Table keywords > Semantic + data > Metric + temporal > Default to HYBRID
    # NEW: Requires BOTH metric AND temporal for SQL_ONLY (except table keywords)
    # NEW: Default changed from VECTOR_ONLY to HYBRID for safer fallback

    if has_table_keywords:
        # Strong SQL indicator UNLESS semantic keywords present
        if has_semantic_keywords:
            result = QueryType.HYBRID  # Table + semantic = HYBRID
        else:
            result = QueryType.SQL_ONLY  # Pure table query

    elif has_semantic_keywords:
        # Semantic keywords present
        if has_metric_terms or has_temporal_terms or has_numeric_refs:
            result = QueryType.HYBRID  # Semantic + data = HYBRID
        else:
            result = QueryType.VECTOR_ONLY  # Pure semantic

    elif has_metric_terms and has_temporal_terms:
        # NEW (Story 2.10): Require BOTH metric AND temporal for SQL_ONLY
        # Example: "What is the EBITDA margin for August 2025?"
        #   → has_metric_terms=True (EBITDA, margin)
        #   → has_temporal_terms=True (August 2025)
        #   → Route to SQL_ONLY for structured table search
        result = QueryType.SQL_ONLY

    elif has_precision_keywords and has_metric_terms and has_temporal_terms:
        # Precision + metric + temporal (all three) → SQL_ONLY
        # Story 2.10: Tightened to require all three for SQL routing
        # Example: "Show exact revenue for Q3 2024"
        result = QueryType.SQL_ONLY

    else:
        # DEFAULT: HYBRID for ambiguous cases (Story 2.10 change)
        # Old: Defaulted to VECTOR_ONLY
        # New: Default to HYBRID to use both indexes safely
        # Rationale: HYBRID gracefully degrades if SQL returns 0 results
        result = QueryType.HYBRID

    logger.debug(
        "Query classified",
        extra={
            "query": query[:100],
            "classification": result.value,
            "has_semantic_keywords": has_semantic_keywords,
            "has_table_keywords": has_table_keywords,
            "has_numeric_refs": has_numeric_refs,
            "has_temporal_terms": has_temporal_terms,  # NEW (Story 2.10)
            "has_metric_terms": has_metric_terms,  # NEW (Story 2.10)
        },
    )

    return result
