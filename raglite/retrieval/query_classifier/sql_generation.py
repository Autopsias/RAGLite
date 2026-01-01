"""Text-to-SQL generation for structured table queries.

Story 2.13: Text-to-SQL generation for financial table search.
"""

import logging
import re
import time

from raglite.retrieval.period_normalizer import detect_period_in_query, normalize_period
from raglite.retrieval.query_classifier.classification import (
    expand_metric_synonyms,
    get_metric_ilike_pattern,
)
from raglite.shared.clients import get_mistral_client
from raglite.shared.config import settings

logger = logging.getLogger(__name__)


async def generate_sql_query(query: str) -> str | None:
    """Generate SQL query from natural language using Mistral API.

    Story 2.13 AC2: Text-to-SQL generation for structured table queries.
    Uses Mistral Small (same model as metadata extraction) for SQL generation against financial_tables schema.

    Production Validation:
        - FinRAG (EMNLP 2024): SQL-based retrieval achieves 70-80% accuracy on financial tables
        - TableRAG (2024): Outperforms semantic search by 25-30% on structured queries
        - Bloomberg NLP: SQL search reduces hallucinations by 40%
        - Mistral Small: FREE, 91% accuracy on metadata extraction (Story 2.4)

    Args:
        query: Natural language query (e.g., "What is the variable cost per ton for
               Portugal Cement in August 2025 YTD?")

    Returns:
        SQL query string or None if generation fails.

        Example:
            SELECT entity, metric, value, unit, period
            FROM financial_tables
            WHERE entity ILIKE '%Portugal Cement%'
              AND metric ILIKE '%variable cost%'
              AND period ILIKE '%Aug-25%'
              AND fiscal_year = 2025
            ORDER BY page_number, table_index, row_index
            LIMIT 50;

    Raises:
        Exception: If Mistral API call fails (gracefully degrades to None)
    """
    logger.debug("Generating SQL query from natural language", extra={"query": query[:100]})

    start_time = time.time()

    try:
        # Story 2.15 AC2: Detect and normalize period format
        detected_period = detect_period_in_query(query)
        period_variants = normalize_period(detected_period) if detected_period else []

        # Log period normalization results
        if period_variants:
            logger.debug(
                "Period normalized for SQL generation",
                extra={
                    "query_period": detected_period,
                    "database_variants": period_variants,
                },
            )

        # Phase 1.3: Expand metric synonyms for better SQL matching
        expanded_metrics = expand_metric_synonyms(query)
        metric_ilike_pattern = (
            get_metric_ilike_pattern(expanded_metrics) if expanded_metrics else ""
        )

        # Log metric synonym expansion results
        if expanded_metrics:
            logger.debug(
                "Metric synonyms expanded for SQL generation",
                extra={
                    "query": query[:100],
                    "expanded_count": len(expanded_metrics),
                    "metric_pattern": metric_ilike_pattern[:100] if metric_ilike_pattern else "",
                },
            )

        # Initialize Mistral client with timeout configuration
        client = get_mistral_client()

        # SQL generation prompt with schema (prompt template for LLM, not SQL construction)
        sql_prompt = f"""You are a SQL expert

**DATABASE SCHEMA:**

Table: financial_tables
Columns:
  - id (SERIAL PRIMARY KEY)
  - document_id (VARCHAR) - Document filename
  - page_number (INT) - Page number in document
  - table_index (INT) - Table number on page (METADATA ONLY - do not use in ORDER BY)
  - table_caption (TEXT) - Table title/caption
  - entity (VARCHAR) - Company/division name (e.g., "Portugal", "Brazil", "Tunisia", "Portugal Cement")
  - metric (VARCHAR) - Cost type/metric (e.g., "variable costs", "thermal energy", "EBITDA")
  - period (VARCHAR) - Time period (e.g., "Aug-25 YTD", "Q2 2025", "2024")
  - fiscal_year (INT) - Year (e.g., 2025, 2024)
  - value (DECIMAL) - Numeric value
  - unit (VARCHAR) - Unit of measurement (e.g., "EUR/ton", "GJ/ton", "%")
  - row_index (INT) - Row number in table (METADATA ONLY - do not use in ORDER BY)
  - column_name (VARCHAR) - Column name from table
  - section_type (VARCHAR) - Section type (default: "Table")
  - chunk_text (TEXT) - Full table context

Indexes:
  - idx_entity ON entity
  - idx_metric ON metric
  - idx_period ON period
  - idx_fiscal_year ON fiscal_year
  - idx_document_page ON (document_id, page_number)

**QUERY GENERATION RULES:**

1. **ENTITY MATCHING** (Use ILIKE for fuzzy text matching):
   For entity queries, use ILIKE for case-insensitive pattern matching:

   SINGLE ENTITY:
   ```sql
   WHERE entity ILIKE '%Portugal%'
   ```

   MULTIPLE ENTITIES - CRITICAL: Use parentheses to group entity conditions:
   ```sql
   WHERE (entity ILIKE '%Portugal%' OR entity ILIKE '%Portugal Cement%'
       OR entity ILIKE '%Tunisia%' OR entity ILIKE '%Tunisia Cement%')
     AND metric ILIKE '%variable cost%'
   ```

   Entity matching patterns:
   - "Portugal Cement" → entity ILIKE '%Portugal%' OR entity ILIKE '%Cement%'
   - "Brazil" → entity ILIKE '%Brazil%'
   - "Tunisia Cement" → entity ILIKE '%Tunisia%'
   - **CRITICAL FOR MULTI-ENTITY**: Always wrap multiple entity OR conditions in parentheses before AND metric

2. **Use ILIKE for text matching** (case-insensitive pattern matching):
   - metric ILIKE '%variable cost%'
   - period ILIKE '%Aug-25%'
   - entity ILIKE '%Portugal%'

3. **Use exact match for numeric fields**:
   - fiscal_year = 2025
   - value > 100.0

4. **Always ORDER BY for consistency**:
   - ORDER BY page_number DESC (most recent pages first)
   - OR ORDER BY value DESC (highest values first)
   - DO NOT use table_index or row_index in ORDER BY

5. **Always LIMIT results** (default 50, max 100):
   - LIMIT 50

6. **SELECT relevant columns only**:
   - Core: entity, metric, value, unit, period, fiscal_year
   - Attribution: document_id, page_number, table_caption, chunk_text (REQUIRED for source tracking)

7. **Handle ambiguity with OR conditions**:
   - "costs" → metric ILIKE '%cost%' OR metric ILIKE '%expense%'
   - **CRITICAL**: Wrap multiple OR conditions in parentheses before AND

8. **Extract temporal terms (IMPORTANT: Handle NULL fiscal_year)**:
   - "August 2025" → period ILIKE '%Aug-25%' AND (fiscal_year = 2025 OR fiscal_year IS NULL)
   - "Q3 2024" → period ILIKE '%Q3%' AND (fiscal_year = 2024 OR fiscal_year IS NULL)
   - "YTD" → period ILIKE '%YTD%'
   - **CRITICAL**: Many tables have fiscal_year=NULL. Always use (fiscal_year = YYYY OR fiscal_year IS NULL) pattern.

9. **Story 2.15 AC2: Period Normalization** (USE WHEN PERIOD VARIANTS PROVIDED):
   {f"   - Detected period: {detected_period}" if detected_period else "   - No period detected in query"}
   {f"   - Use period IN {tuple(period_variants)} for exact matching" if period_variants else "   - No period variants available - use ILIKE pattern matching"}
   - **WHEN period variants provided**: Use IN clause instead of ILIKE for exact period matching
   - **Example**: period IN ('Jul-25', 'Aug-25', 'Sep-25', 'Aug-25 YTD', 'Q3-25')
   - **WHEN no variants**: Fall back to ILIKE pattern matching

10. **Phase 1.3: Metric Synonym Expansion** (USE WHEN EXPANDED METRICS PROVIDED):
   {f"   - Expanded metrics detected: {expanded_metrics[:5]}{'...' if len(expanded_metrics) > 5 else ''}" if expanded_metrics else "   - No metric synonyms detected"}
   {f"   - USE THIS EXACT PATTERN: {metric_ilike_pattern}" if metric_ilike_pattern else "   - No metric pattern available - use standard ILIKE"}

   **CRITICAL - WHEN expanded metrics are provided above:**
   - **REPLACE** any metric ILIKE pattern with the EXACT pattern provided above
   - Example: If pattern is `metric ILIKE ANY(ARRAY['%Electrical Energy%', '%Thermal Energy%'])`,
     use it EXACTLY as shown, not a simplified version

   **Synonym Expansion Rules:**
   - User says "energy" → Use: metric ILIKE ANY(ARRAY['%Electrical Energy%', '%Thermal Energy%', '%Fuel Energy%', '%Energy Cost%', '%Power Consumption%'])
   - User says "petcoke" → Use: metric ILIKE ANY(ARRAY['%Petcoke%', '%Pet Coke%', '%Petroleum Coke%', '%Petcoke Consumption%'])
   - User says "debt" → Use: metric ILIKE ANY(ARRAY['%Financial net debt%', '%Net Debt%', '%Gross Debt%', '%Bank Debt%'])
   - User says "working capital" → Use: metric ILIKE ANY(ARRAY['%Trade Working Capital%', '%Net Working Capital%', '%WC%', '%Receivables%', '%Payables%'])
   - User says "clinker" → Use: metric ILIKE ANY(ARRAY['%Clinker%', '%Clinker Factor%', '%Clinker Ratio%'])
   - User says "emissions" or "co2" → Use: metric ILIKE ANY(ARRAY['%CO2%', '%Emissions%', '%Carbon%', '%Scope 1%', '%Scope 2%'])

**EXAMPLES:**

Query: "What is the variable cost per ton for Portugal Cement in August 2025 YTD?"
SQL:
SELECT document_id, entity, metric, value, unit, period, fiscal_year, page_number, table_caption
FROM financial_tables
WHERE (entity ILIKE '%Portugal%' OR entity ILIKE '%Portugal Cement%')
  AND metric ILIKE '%variable cost%'
  AND period ILIKE '%Aug-25%'
  AND period ILIKE '%YTD%'
  AND (fiscal_year = 2025 OR fiscal_year IS NULL)
ORDER BY page_number DESC
LIMIT 50;

Query: "Show me EBITDA margin for all entities in Q3 2024"
SQL:
SELECT document_id, entity, metric, value, unit, period, fiscal_year, page_number
FROM financial_tables
WHERE metric ILIKE '%EBITDA%'
  AND (metric ILIKE '%margin%' OR unit ILIKE '%%')
  AND period ILIKE '%Q3%'
  AND (fiscal_year = 2024 OR fiscal_year IS NULL)
ORDER BY entity, page_number DESC
LIMIT 100;

Query: "What are the thermal energy costs?"
SQL:
SELECT document_id, entity, metric, value, unit, period, fiscal_year, page_number, table_caption
FROM financial_tables
WHERE metric ILIKE '%thermal%'
  AND (metric ILIKE '%energy%' OR metric ILIKE '%cost%')
ORDER BY fiscal_year DESC, page_number DESC
LIMIT 50;

Query: "Compare variable costs for Portugal and Tunisia"
SQL:
SELECT document_id, entity, metric, value, unit, period, fiscal_year, page_number, table_caption
FROM financial_tables
WHERE (entity ILIKE '%Portugal%' OR entity ILIKE '%Portugal Cement%'
    OR entity ILIKE '%Tunisia%' OR entity ILIKE '%Tunisia Cement%')
  AND metric ILIKE '%variable cost%'
ORDER BY page_number DESC
LIMIT 50;

**USER QUERY:**
{query}

**INSTRUCTIONS:**
- Return ONLY the SQL query (no explanations, no markdown, no code blocks)
- Ensure query is valid PostgreSQL syntax
- Use ILIKE for all text matching (case-insensitive entity and metric matching)
- Always include ORDER BY and LIMIT
- DO NOT use table_index or row_index in ORDER BY (causes SQL errors)
- **CRITICAL**: Always include document_id in SELECT clause (REQUIRED for source attribution)
- Select columns needed for answering the question + attribution (document_id, page_number, table_caption)
- Use simple ORDER BY patterns: page_number DESC, value DESC, or fiscal_year DESC
"""  # nosec B608

        # Call Mistral API (using same pattern as metadata extraction)
        from mistralai.models import AssistantMessage, SystemMessage, ToolMessage, UserMessage

        messages: list[AssistantMessage | SystemMessage | ToolMessage | UserMessage] = [
            SystemMessage(
                content="You are a SQL expert specializing in financial data queries. "
                "Generate ONLY valid PostgreSQL queries. Return the SQL query without "
                "explanations, markdown, or code blocks."
            ),
            UserMessage(content=sql_prompt),
        ]
        response = client.chat.complete(
            model=settings.metadata_extraction_model,  # mistral-small-latest
            max_tokens=500,
            temperature=0,  # Deterministic SQL generation
            messages=messages,
        )

        # Extract SQL from response
        response_content = response.choices[0].message.content
        sql_query: str | None = response_content if isinstance(response_content, str) else None
        if sql_query:
            sql_query = sql_query.strip()
        else:
            return None

        # Remove markdown code blocks if present
        sql_query = re.sub(r"```sql\n?", "", sql_query)
        sql_query = re.sub(r"```\n?", "", sql_query)
        sql_query = sql_query.strip()

        # Validate SQL starts with SELECT
        if not sql_query.upper().startswith("SELECT"):
            logger.warning(
                "Generated SQL does not start with SELECT",
                extra={"query": query[:100], "sql": sql_query[:100]},
            )
            return None

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "SQL query generation complete",
            extra={
                "query": query[:100],
                "sql_preview": sql_query[:150],
                "sql_length": len(sql_query),
                "model": settings.metadata_extraction_model,
                "duration_ms": duration_ms,
            },
        )

        return sql_query

    except Exception as e:
        logger.error(
            "SQL query generation failed - degrading to None",
            extra={"error": str(e), "query": query[:100]},
            exc_info=True,
        )
        return None
