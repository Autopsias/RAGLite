"""Query type classification for multi-index routing.

Story 2.7: Heuristic-based query type classification for multi-index search.
Story 2.10: Tightened SQL routing to reduce over-routing.
"""

import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# METRIC SYNONYMS DICTIONARY (Phase 1.2)
# Maps user query terms to actual database metric names for synonym expansion.
# This bridges the gap between how users ask questions and how metrics are stored.
# ============================================================================

METRIC_SYNONYMS: dict[str, list[str]] = {
    # ===== ENERGY METRICS =====
    "energy consumption": [
        "Electrical Energy",
        "Thermal Energy",
        "Fuel Energy",
        "Energy Cost",
        "Power Consumption",
        "Total Energy",
    ],
    "energy": [
        "Electrical Energy",
        "Thermal Energy",
        "Fuel Energy",
        "Energy Cost",
        "Power Consumption",
        "kWh",
        "MWh",
        "GJ",
    ],
    "electricity": ["Electrical Energy", "Power Consumption", "kWh", "MWh", "Electric"],
    "thermal energy": ["Thermal Energy", "Heat Consumption", "kcal", "GJ", "Thermal"],
    "power": ["Electrical Energy", "Power Consumption", "kWh", "MWh"],
    # ===== FUEL METRICS (CEMENT INDUSTRY) =====
    "petcoke": [
        "Petcoke Consumption",
        "Pet Coke",
        "Petroleum Coke",
        "Petcoke Cost",
        "Petcoke",
        "Pet coke",
    ],
    "petroleum coke": ["Petcoke", "Pet Coke", "Petroleum Coke", "Petcoke Consumption"],
    "coal": ["Coal Consumption", "Coal Cost", "Coal", "Lignite"],
    "fuel cost": ["Fuel Cost", "Petcoke Cost", "Coal Cost", "Energy Cost", "Fuel"],
    "alternative fuels": [
        "AF Rate",
        "Alternative Fuel",
        "Biomass",
        "Waste Fuel",
        "TSR",
        "Thermal Substitution",
    ],
    "af rate": ["AF Rate", "Alternative Fuel Rate", "TSR", "Thermal Substitution Rate"],
    # ===== FINANCIAL METRICS =====
    "working capital": [
        "Trade Working Capital",
        "Net Working Capital",
        "WC",
        "Working Capital/Turnover",
        "Working Capital",
        "Receivables",
        "Payables",
        "Inventory",
    ],
    "debt": [
        "Financial net debt",
        "Net Debt",
        "Gross Debt",
        "Bank Debt",
        "Total Debt",
        "Financial Debt",
    ],
    "net debt": ["Financial net debt", "Net Debt", "Net Financial Debt"],
    "ebitda": [
        "EBITDA IFRS",
        "EBITDA",
        "Cement Unit Ebitda",
        "Ready-Mix Unit Ebitda",
        "Unit EBITDA",
        "EBITDA Margin",
    ],
    "revenue": ["Revenue", "Sales", "Turnover", "Net Revenue", "Total Revenue"],
    "margin": [
        "Margin",
        "EBITDA Margin",
        "Gross Margin",
        "Net Margin",
        "Profit Margin",
    ],
    "cost": [
        "Cost",
        "Variable Cost",
        "Fixed Cost",
        "Total Cost",
        "Unit Cost",
        "Cost per ton",
    ],
    "variable cost": ["Variable Cost", "Variable Costs", "VC", "Variable"],
    "fixed cost": ["Fixed Cost", "Fixed Costs", "FC", "Fixed"],
    # ===== PRODUCTION METRICS (CEMENT INDUSTRY) =====
    "clinker ratio": [
        "Clinker Factor",
        "Clinker/Cement Ratio",
        "Clinker Ratio",
        "Clinker",
    ],
    "clinker": ["Clinker", "Clinker Factor", "Clinker Production", "Clinker Ratio"],
    "capacity utilization": [
        "Plant Utilization",
        "Kiln Utilization",
        "Capacity Rate",
        "Utilization",
        "Capacity",
    ],
    "utilization": [
        "Utilization",
        "Plant Utilization",
        "Kiln Utilization",
        "Capacity Utilization",
    ],
    "kiln utilization": [
        "Kiln Utilization",
        "Kiln Uptime",
        "Kiln Availability",
        "Kiln Operating Rate",
    ],
    "production volume": [
        "Cement Volume",
        "Clinker Production",
        "Production",
        "Volume",
        "Output",
    ],
    "production": [
        "Production",
        "Volume",
        "Output",
        "Cement Production",
        "Clinker Production",
    ],
    # ===== SUSTAINABILITY METRICS =====
    "co2": [
        "CO2",
        "Emissions",
        "Carbon",
        "CO2 per ton",
        "Scope 1",
        "Scope 2",
        "Scope 3",
    ],
    "emissions": [
        "Emissions",
        "CO2",
        "Carbon Emissions",
        "Scope 1",
        "Scope 2",
        "Scope 3",
        "GHG",
    ],
    "carbon": ["Carbon", "CO2", "Emissions", "Carbon Footprint"],
    "scope 1": ["Scope 1", "Scope1", "Direct Emissions"],
    "scope 2": ["Scope 2", "Scope2", "Indirect Emissions"],
    "scope 3": ["Scope 3", "Scope3", "Value Chain Emissions"],
    # ===== COST STRUCTURE =====
    "cost per ton": ["Cost per ton", "Unit Cost", "EUR/ton", "Cost/ton", "$/ton"],
    "fuel consumption": [
        "Fuel Consumption",
        "kcal/kg",
        "GJ/ton",
        "Fuel",
        "Thermal Consumption",
    ],
    "power cost": ["Power Cost", "Electricity Cost", "EUR/MWh", "Energy Cost"],
    # ===== FINANCIAL RATIOS =====
    "ebitda per ton": ["EBITDA per ton", "Unit EBITDA", "EBITDA/ton"],
    "return on capital": ["ROIC", "Return on Invested Capital", "ROI", "ROCE"],
    "leverage": ["Leverage", "Debt/Equity", "Leverage Ratio", "Gearing"],
    "free cash flow": ["Free Cash Flow", "FCF", "Cash Flow"],
}


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


def expand_metric_synonyms(query: str) -> list[str]:
    """Expand user query terms to database metric names using synonym dictionary.

    Phase 1.2: This function enables SQL queries to find metrics even when users
    use different terminology than what's stored in the database.

    Args:
        query: Natural language query from user

    Returns:
        List of expanded metric names that should be searched in the database.
        Returns empty list if no synonyms match.

    Example:
        >>> expand_metric_synonyms("What is the energy consumption?")
        ['Electrical Energy', 'Thermal Energy', 'Fuel Energy', 'Energy Cost', ...]

        >>> expand_metric_synonyms("Show me petcoke costs")
        ['Petcoke Consumption', 'Pet Coke', 'Petroleum Coke', 'Petcoke Cost', ...]
    """
    expanded: list[str] = []
    query_lower = query.lower()

    for user_term, db_terms in METRIC_SYNONYMS.items():
        # Check if user term appears in the query
        if user_term in query_lower:
            # Add all database terms for this synonym
            for term in db_terms:
                if term not in expanded:
                    expanded.append(term)

    logger.debug(
        "Metric synonyms expanded",
        extra={
            "query": query[:100],
            "expanded_count": len(expanded),
            "expanded_terms": expanded[:10] if expanded else [],  # Log first 10
        },
    )

    return expanded


def get_metric_ilike_pattern(expanded_terms: list[str]) -> str:
    """Generate SQL ILIKE ANY pattern from expanded metric terms.

    Phase 1.2: Creates a PostgreSQL ILIKE ANY clause for fuzzy matching
    multiple metric synonyms.

    Args:
        expanded_terms: List of metric names from expand_metric_synonyms()

    Returns:
        SQL pattern string for use in WHERE clause.

    Example:
        >>> get_metric_ilike_pattern(['Electrical Energy', 'Thermal Energy'])
        "metric ILIKE ANY(ARRAY['%Electrical Energy%', '%Thermal Energy%'])"
    """
    if not expanded_terms:
        return ""

    # Create ILIKE patterns for each term
    patterns = [f"'%{term}%'" for term in expanded_terms]
    return f"metric ILIKE ANY(ARRAY[{', '.join(patterns)}])"


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
