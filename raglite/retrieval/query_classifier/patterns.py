"""Query pattern definitions for heuristic classification.

Story 2.7 & 2.10: Regex patterns used to detect query features for routing.
"""

# ============================================================================
# QUERY PATTERN DEFINITIONS (Story 2.7 & 2.10)
# Heuristic patterns for query classification - extracted for clarity
# ============================================================================

TABLE_KEYWORDS = [r"\btable\b", r"\brow\b", r"\bcolumn\b", r"\bcell\b"]

PRECISION_KEYWORDS = [r"\bexact\b", r"\bprecise\b", r"\bspecific\b"]

SEMANTIC_KEYWORDS = [
    r"\bexplain\b",
    r"\bsummarize\b",
    r"\bwhy\b",
    r"\bdescribe\b",
    r"\bcompare\b",
    r"\banalyze\b",
    r"\bhow\b",
]

NUMERIC_PATTERNS = [
    r"\d+\.?\d*\s*%",  # 15%, 10.5%
    r"\$\d+\.?\d*[MBK]?",  # $1.2M, $500K
    r"\d+\.?\d*\s+(eur|usd|gbp|ton|tonnes|mwh)",  # 23.5 EUR, 500 tonnes
    r"\d+[KM]\s+(tonnes|units|items)",  # 500K tonnes
    r"Q[1-4]",  # Q1, Q3, etc.
    r"\b(19|20)\d{2}\b",  # Years: 2024, 2023, etc.
]

TEMPORAL_PATTERNS = [
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

METRIC_PATTERNS = [
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
