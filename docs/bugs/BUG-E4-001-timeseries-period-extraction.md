# BUG-E4-001: Time-Series Extraction Missing Period/Fiscal Year Metadata

**Reported:** 2025-11-28
**Severity:** High
**Status:** Open → Story 5.0.1 Created
**Epic:** Epic 4 - Forecasting & Proactive Insights
**Stories Affected:** 4.1, 4.2, 4.3, 4.4
**Fix Story:** [5.0.1 Fix Time-Series Period Extraction](/docs/stories/5-0-1-fix-timeseries-period-extraction.md)

---

## Summary

The `get_financial_forecast` MCP tool fails to generate forecasts because the time-series extraction function uses hybrid search + LLM extraction instead of querying the PostgreSQL `financial_tables` which contains structured temporal data.

## Root Cause Analysis (Updated 2025-11-28)

### Original Hypothesis (PARTIALLY CORRECT)
The `period` and `fiscal_year` columns in PostgreSQL are NULL.

### Actual Current State
```sql
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN period IS NOT NULL THEN 1 END) as with_period,
    COUNT(CASE WHEN fiscal_year IS NOT NULL THEN 1 END) as with_fiscal_year
FROM financial_tables;

 total  | with_period | with_fiscal_year
--------+-------------+------------------
 386466 |      344316 |            14022
```

- **Total rows:** 386,466
- **period populated:** 344,316 (89%) ← Actually GOOD
- **fiscal_year populated:** 14,022 (3.6%) ← Needs backfill

### TRUE Root Cause (CRITICAL)

The forecasting system's `extract_timeseries()` function in `raglite/forecasting/timeseries_extract.py` uses **hybrid search + LLM extraction** from document chunks. It does NOT query the PostgreSQL `financial_tables` table at all!

**Evidence from Code (lines 185-320 of `timeseries_extract.py`):**
```python
# Step 1: Retrieve relevant chunks using hybrid search
query = f"historical {metric} values by month quarter year"
results = await hybrid_search(query=query, top_k=10, ...)

# Step 2: Combine chunk texts for LLM extraction
combined_text = "\n\n---\n\n".join(...)

# Step 3: LLM extraction prompt
extraction_prompt = f"""Extract all {metric} values with their dates..."""
```

The function searches Qdrant for document chunks, then uses LLM to extract dates/values from unstructured text. This is unreliable because document chunks don't contain well-formatted time-series data.

**Meanwhile:** PostgreSQL `financial_tables` has 386,466 rows of structured metric/value/period data that is NEVER queried by the forecasting system.

## Expected Behavior

The forecasting tool should:
1. Query `financial_tables` for metric data with `period` and `fiscal_year`
2. Fall back to hybrid search only if SQL returns insufficient data

## Actual Behavior

- `extract_timeseries()` only uses hybrid search + LLM extraction
- LLM cannot reliably extract structured time-series from document chunks
- Error: "No documents found containing revenue data"

## Impact

- **get_financial_forecast** tool completely non-functional
- Stories 4.1-4.4 cannot be validated via UAT
- Forecasting feature unusable for end users

## Steps to Reproduce

1. Ingest "2025-08 Performance Review CONSO_v2.pdf"
2. Connect to Claude.ai with RAGLite MCP
3. Ask: "What's the revenue forecast for the next quarter?"
4. Observe error: "No documents found containing revenue data"

## Proposed Fix (Story 5.0.1)

**Two-Part Fix Required:**

### Part 1: SQL Migration
Backfill `fiscal_year` from `period` column:
```sql
UPDATE financial_tables
SET fiscal_year = 2000 + (regexp_match(period, '.*-(\d{2})$'))[1]::int
WHERE period IS NOT NULL
  AND period ~ '-\d{2}$'
  AND fiscal_year IS NULL;
```

### Part 2: SQL-Based Extraction Function
Add `extract_timeseries_from_sql()` function that queries `financial_tables`:
```python
async def extract_timeseries_from_sql(metric: str = "revenue") -> TimeSeriesData:
    """Extract time-series from PostgreSQL financial_tables."""
    query = """
        SELECT metric, value, period, fiscal_year, document_id
        FROM financial_tables
        WHERE LOWER(metric) LIKE %s
          AND period IS NOT NULL
          AND fiscal_year IS NOT NULL
        ORDER BY fiscal_year, period
    """
    # ... execute and return TimeSeriesData
```

### Part 3: Update MCP Tool
Modify `get_financial_forecast()` to try SQL extraction first, fall back to hybrid search.

## Workaround

For UAT testing, use `get_financial_insights` tool instead which works with document queries via hybrid search and doesn't require structured time-series data.

## Files to Modify

1. `scripts/migrations/001_backfill_fiscal_year.sql` (new)
2. `raglite/forecasting/timeseries_extract.py` - Add SQL extraction function
3. `raglite/main.py` - Modify `get_financial_forecast()` for SQL-first approach
4. `tests/unit/test_timeseries_extract.py` - Add tests
5. `tests/integration/test_forecast_query_integration.py` - Add integration tests

## Priority

**High** - Core Epic 4 feature is blocked

---

## Notes

- **NO RE-INGESTION REQUIRED** - `period` is already 89% populated
- Only `fiscal_year` needs backfill (simple SQL UPDATE from `period`)
- New SQL-based extraction provides deterministic, reliable data
- Fallback to hybrid search maintains backward compatibility
- Insights feature works fine (uses document queries, not time-series)

---

**Assigned To:** TBD
**Target Fix:** Story 5.0.1 (Epic 5 Prep Story)
**Estimated Effort:** 8 hours (5 story points)
