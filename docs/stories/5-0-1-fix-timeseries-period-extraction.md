# Story 5.0.1: Fix Time-Series Period Extraction for Forecasting

**Status:** ready-for-dev

**Epic:** Epic 5 - Production Readiness & Real-Time Operations
**Type:** Bug Fix / Technical Debt (Post-Epic 4 UAT)
**Priority:** High
**Story Points:** 5
**Created:** 2025-11-28
**Updated:** 2025-11-28
**Bug Reference:** BUG-E4-001 (Epic 4 UAT - Forecasting blocked)

---

## Story

**As a** financial analyst using RAGLite,
**I want** the forecasting tool to correctly extract time-series data from ingested documents,
**So that** I can generate revenue, expense, and cash flow forecasts for future quarters.

---

## Background

During Epic 4 UAT testing (2025-11-28), the `get_financial_forecast` MCP tool failed to generate forecasts because the time-series extraction could not find temporal metadata.

### Root Cause Analysis (Updated 2025-11-28)

**Original Hypothesis (PARTIALLY CORRECT):**
The `period` and `fiscal_year` columns in PostgreSQL `financial_tables` are mostly NULL.

**Actual Current State:**
- 386,466 total rows in `financial_tables`
- 344,316 rows (89%) have `period` populated
- 14,022 rows (3.6%) have `fiscal_year` populated
- 121,373 rows (31%) have parseable `Mon-YY` date patterns in `column_name`

**TRUE Root Cause (CRITICAL):**
The forecasting system's `extract_timeseries()` function in `raglite/forecasting/timeseries_extract.py` uses **hybrid search + LLM extraction** from document chunks - it does NOT query the PostgreSQL `financial_tables` table at all!

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

The function searches Qdrant vector database for chunks, then uses LLM to extract dates/values. But document chunks don't contain well-structured time-series data that the LLM can reliably extract.

**Meanwhile:** PostgreSQL `financial_tables` has structured data with 386,466 rows of metric/value pairs, but it's never queried by the forecasting system.

### Solution Architecture

**Two-Part Fix Required:**

1. **Part 1: Backfill `fiscal_year` column** (SQL migration)
   - `fiscal_year` is only 3.6% populated vs `period` at 89%
   - Parse `period` column (e.g., "Jan-25") to populate `fiscal_year`

2. **Part 2: Add SQL-based time-series extraction** (NEW CODE)
   - Create `extract_timeseries_from_sql()` function
   - Query `financial_tables` for metric values with `period` and `fiscal_year`
   - Use as primary extraction method, fall back to hybrid search

**NO RE-INGESTION REQUIRED** - SQL UPDATE can backfill fiscal_year from existing `period` values.

**Impact:**
- `get_financial_forecast` tool completely non-functional
- Stories 4.1-4.4 cannot be validated
- Users cannot generate Prophet-based forecasts

[Source: UAT Epic 4 testing session 2025-11-28, root cause analysis by Ricardo/Dev]

---

## Acceptance Criteria

### AC1: SQL Migration Backfills fiscal_year Column

**Given** existing rows in `financial_tables` with `period` populated but `fiscal_year` NULL
**When** the SQL migration script is executed
**Then** `fiscal_year` is populated by parsing the year from `period` (e.g., "Jan-25" → 2025)
**And** 300,000+ rows are updated (89% of 344,316 rows with period)

**SQL Migration:**
```sql
-- Backfill fiscal_year from period column (e.g., "Jan-25" → 2025)
UPDATE financial_tables
SET fiscal_year = 2000 + (regexp_match(period, '.*-(\d{2})$'))[1]::int
WHERE period IS NOT NULL
  AND period ~ '-\d{2}$'
  AND fiscal_year IS NULL;

-- Verify results
SELECT COUNT(*) as updated_rows FROM financial_tables WHERE fiscal_year IS NOT NULL;
```

[Source: Story 2.6 SQL table extraction, PostgreSQL schema in docs/architecture/database-schema.md]

### AC2: SQL-Based Time-Series Extraction Function

**Given** the forecasting system needs historical metric data
**When** `extract_timeseries_from_sql(metric="revenue")` is called
**Then** it queries `financial_tables` for matching metric rows with valid `period` and `fiscal_year`
**And** returns `TimeSeriesData` with properly dated values
**And** falls back to hybrid search if SQL returns insufficient data (<8 points)

**New Function:**
```python
async def extract_timeseries_from_sql(
    metric: str = "revenue",
    min_points: int = 8,
) -> TimeSeriesData:
    """Extract time-series from PostgreSQL financial_tables.

    Primary extraction method for forecasting - uses structured SQL data
    rather than LLM extraction from document chunks.
    """
```

[Source: Story 4.1 time-series extraction requirements, Epic 4 PRD]

### AC3: Forecasting Tool Uses SQL Extraction

**Given** the SQL-based extraction is implemented
**When** a user asks "What's the revenue forecast for the next quarter?"
**Then** the `get_financial_forecast` tool:
1. Calls `extract_timeseries_from_sql()` first
2. Falls back to `extract_timeseries()` (hybrid search) if SQL fails
3. Returns forecast values with dates, confidence intervals, and methodology

[Source: Story 4.4 forecast query tool requirements, Epic 4 PRD]

### AC4: Integration Test Validates End-to-End Flow

**Given** the SQL migration has been applied
**And** the SQL-based extraction is implemented
**When** integration tests run
**Then** `test_forecast_query_with_sql_extraction()` passes
**And** forecast returns ≥8 data points for revenue metric

[Source: Story 4.10 testing strategy, docs/architecture/testing-strategy.md]

### AC5: Unit Tests for Period Parsing

**Given** the period parsing logic
**When** unit tests are run
**Then** all patterns are validated:
- `parse_period_to_date("Jan-25")` → datetime(2025, 1, 1)
- `parse_period_to_date("Aug-24")` → datetime(2024, 8, 1)
- `parse_period_to_date("Dec-23")` → datetime(2023, 12, 1)

[Source: docs/architecture/coding-standards.md unit testing requirements]

---

## Tasks / Subtasks

### Task 1: Write SQL Migration Script (AC: 1)

- [ ] 1.1 Create `scripts/migrations/001_backfill_fiscal_year.sql` with:
  - UPDATE statement to populate fiscal_year from period
  - Regex pattern: `.*-(\d{2})$` to extract 2-digit year
  - WHERE clause to filter valid period format
  - Verification SELECT query
- [ ] 1.2 Test migration on development database:
  - Run SELECT to count affected rows
  - Execute UPDATE in transaction
  - Verify counts before/after
  - Rollback and re-test if issues found
- [ ] 1.3 Document migration in `docs/database-migrations.md`:
  - Migration number and purpose
  - Expected row count change
  - Rollback procedure
- [ ] 1.4 Unit test: Create `tests/unit/test_sql_migrations.py`:
  - Test regex pattern extraction
  - Test edge cases (invalid formats, NULL values)
  - Verify no data loss

[Source: Story 2.6 SQL integration patterns, docs/architecture/coding-standards.md]

### Task 2: Implement SQL-Based Time-Series Extraction (AC: 2)

- [ ] 2.1 Add `extract_timeseries_from_sql()` to `raglite/forecasting/timeseries_extract.py`:
  - Import PostgreSQL connection from `raglite/shared/clients.py`
  - Query financial_tables for metric with LIKE pattern
  - Filter WHERE period IS NOT NULL AND fiscal_year IS NOT NULL
  - Order by fiscal_year, period for chronological sequence
- [ ] 2.2 Implement `parse_period_to_date()` helper function:
  - Regex pattern: `(Jan|Feb|...|Dec)-(\d{2})`
  - Month name to integer mapping
  - Return datetime for first day of period month
  - Handle edge cases (invalid format, missing year)
- [ ] 2.3 Add error handling:
  - Raise `ExtractionError` if insufficient data (<8 points)
  - Log extraction attempt with metric name
  - Handle SQL connection errors gracefully
- [ ] 2.4 Add structured logging:
  - Log: "Extracting time-series from SQL" with metric name
  - Log: Result count and date range extracted
  - Log: Fallback trigger if <8 points
- [ ] 2.5 Add Google-style docstring:
  - Args: metric, min_points
  - Returns: TimeSeriesData
  - Raises: ExtractionError
  - Example usage

[Source: docs/architecture/coding-standards.md, Story 4.1 time-series extraction]

### Task 3: Update MCP Tool for SQL-First Extraction (AC: 3)

- [ ] 3.1 Modify `get_financial_forecast()` in `raglite/main.py` (line ~1678):
  - Import `extract_timeseries_from_sql` function
  - Add try/except block around SQL extraction call
  - Call SQL extraction first with requested metric
  - Log success with point count if SQL succeeds
- [ ] 3.2 Implement fallback to hybrid search:
  - Catch `ExtractionError` from SQL extraction
  - Log fallback message: "SQL extraction failed, falling back to hybrid search"
  - Call original `extract_timeseries()` with hybrid search
  - Continue with forecasting using either data source
- [ ] 3.3 Update tool docstring:
  - Document SQL-first extraction strategy
  - Note fallback behavior
  - Update examples if needed

[Source: Story 4.4 MCP forecast tool, docs/architecture/high-level-architecture.md]

### Task 4: Unit Tests for New Functions (AC: 5)

- [ ] 4.1 Create `tests/unit/test_timeseries_extract.py`:
  - Test `parse_period_to_date()` with all month patterns
  - Test edge cases: invalid format, case insensitivity
  - Test `extract_timeseries_from_sql()` with mocked SQL
  - Test insufficient data raises ExtractionError
- [ ] 4.2 Use pytest fixtures for test data:
  - Mock SQL connection and cursor
  - Sample rows with period, fiscal_year, metric, value
  - Edge cases: NULL values, single data point
- [ ] 4.3 Parametrize tests for all months:
  - Jan-25, Feb-25, ..., Dec-25
  - Verify correct month number extracted
  - Verify year 2025 parsed correctly
- [ ] 4.4 Achieve ≥80% coverage on new functions

[Source: docs/architecture/testing-strategy.md, Story 4.10 validation framework]

### Task 5: Integration Tests for End-to-End Flow (AC: 4)

- [ ] 5.1 Create `tests/integration/test_forecast_query_integration.py`:
  - Test `test_forecast_query_with_sql_extraction()`
  - Use real PostgreSQL test database (APP_ENV=test)
  - Insert sample time-series data with period/fiscal_year
  - Call `extract_timeseries_from_sql("revenue")`
  - Assert ≥8 data points returned
- [ ] 5.2 Test fallback behavior:
  - Test with metric that has <8 data points in SQL
  - Verify `ExtractionError` raised
  - Mock hybrid search fallback
  - Verify fallback called correctly
- [ ] 5.3 Test MCP tool integration:
  - Call `get_financial_forecast(metric="revenue", periods_ahead=4)`
  - Verify SQL extraction used (check logs)
  - Verify forecast returned with dates and confidence intervals
- [ ] 5.4 Add test fixture cleanup:
  - Delete test data after each test
  - Verify test isolation

[Source: Story 4.10 E2E validation patterns, docs/architecture/testing-strategy.md]

### Task 6: Run Migration on Production Database (AC: 1)

- [ ] 6.1 Backup production database:
  - Run `pg_dump` for financial_tables
  - Store backup with timestamp
  - Verify backup integrity
- [ ] 6.2 Execute migration script:
  - Run in transaction: BEGIN; UPDATE...; COMMIT;
  - Capture row count affected
  - Verify ≥300,000 rows updated
- [ ] 6.3 Verify migration success:
  - Run verification SELECT query
  - Compare before/after counts
  - Spot-check sample rows
- [ ] 6.4 Document migration execution:
  - Add entry to `docs/database-migrations.md`
  - Record: date, affected rows, execution time

[Source: Story 4.0.7 database safety protocols, docs/architecture/database-operation-modes.md]

### Task 7: UAT Re-Testing (AC: All)

- [ ] 7.1 Re-run Epic 4 UAT queries on Claude.ai:
  - UAT-E4-001: "What's the revenue forecast for the next quarter?"
  - UAT-E4-002: "Forecast expenses for the next 4 quarters"
  - UAT-E4-003: "What will cash flow be in Q2 2026?"
  - UAT-E4-004: "Forecast employee count" (should error gracefully)
  - UAT-E4-005: Structured query with metric="revenue", periods_ahead=4
- [ ] 7.2 Verify all forecasts return data:
  - Check forecast contains ≥4 prediction points
  - Verify dates are in future quarters
  - Verify confidence intervals present
- [ ] 7.3 Document UAT results:
  - Update UAT test plan with PASS/FAIL status
  - Note any edge cases discovered
- [ ] 7.4 Sign off on bug fix:
  - Mark BUG-E4-001 as RESOLVED
  - Update Epic 4 UAT status to COMPLETE

[Source: docs/uat/epic-4-uat-test-plan.md, Story 4.4 forecast tool requirements]

### Task 8: Documentation and Cleanup (AC: All)

- [ ] 8.1 Add Google-style docstrings to all new functions
- [ ] 8.2 Update `CHANGELOG.md` with bug fix entry
- [ ] 8.3 Update story file with Dev Agent Record
- [ ] 8.4 Verify all linting passes (`uv run ruff check .`)
- [ ] 8.5 Verify type checking passes (`uv run mypy raglite/`)
- [ ] 8.6 Run full test suite and verify no regressions

[Source: docs/architecture/coding-standards.md]

---

## Dev Notes

### Architecture Patterns and Constraints

**Database Safety (CRITICAL):**
- Story 4.0.7 established three-mode database operation system
- SQL migration MUST use production deploy mode (`--force-data-loss` flag required)
- All database operations must use `SafetyGuard` from `raglite/shared/safety.py`
- Integration tests MUST use `APP_ENV=test` and will FAIL if they detect production ports

**Forecasting System Architecture:**
- Current implementation: Hybrid search (Qdrant) + LLM extraction from chunks
- New approach: SQL-first extraction from structured `financial_tables`
- Fallback pattern: Try SQL → if fails → hybrid search (maintains backward compatibility)
- This follows "graceful degradation" pattern from high-level architecture

**SQL Query Patterns:**
- Use LIKE pattern matching for metric names (e.g., `LOWER(metric) LIKE '%revenue%'`)
- Filter WHERE period IS NOT NULL AND fiscal_year IS NOT NULL
- Order results chronologically: ORDER BY fiscal_year, period
- Handle NULL values gracefully (SQL won't return NULLs due to WHERE clause)

[Source: docs/architecture/high-level-architecture.md, docs/architecture/database-operation-modes.md, docs/architecture/database-schema.md]

### Coding Standards and Patterns

**Type Hints (MANDATORY):**
```python
async def extract_timeseries_from_sql(
    metric: str = "revenue",
    min_points: int = 8,
) -> TimeSeriesData:
```

**Google-Style Docstrings (MANDATORY):**
- Include: Summary, Args, Returns, Raises, Example
- Reference AC numbers in docstring if applicable
- See coding-standards.md for template

**Structured Logging:**
```python
logger.info("Extracting time-series from SQL", extra={"metric": metric})
logger.info("SQL extraction successful", extra={"points": len(points), "date_range": f"{min_date} to {max_date}"})
```

**Error Handling:**
- Raise specific exceptions with context: `ExtractionError(f"Insufficient SQL data...")`
- Use try/except for SQL connection errors
- Log errors before raising

[Source: docs/architecture/coding-standards.md]

### Testing Strategy

**Unit Tests (80%+ coverage target):**
- Mock all external dependencies (PostgreSQL, Qdrant)
- Test edge cases: NULL values, single data point, invalid formats
- Use pytest fixtures for reusable test data
- Parametrize tests for all month patterns

**Integration Tests:**
- Use real PostgreSQL test database (APP_ENV=test, port 5433)
- Insert sample data, run extraction, verify results
- Clean up test data in teardown
- Verify SQL-first extraction with real database queries

**UAT Re-Testing:**
- Run all Epic 4 UAT queries from Claude.ai
- Verify forecasts return valid data
- Document PASS/FAIL results

[Source: docs/architecture/testing-strategy.md, Story 4.10 validation framework patterns]

### Project Structure Notes

**Files to Create:**
1. `scripts/migrations/001_backfill_fiscal_year.sql` - SQL migration script (~30 lines)
2. `tests/unit/test_sql_migrations.py` - Migration validation tests (~50 lines)

**Files to Modify:**
1. `raglite/forecasting/timeseries_extract.py` - Add SQL extraction functions (~150 lines)
2. `raglite/main.py` (line ~1678) - Update `get_financial_forecast()` for SQL-first (~20 lines)
3. `tests/unit/test_timeseries_extract.py` - Add unit tests (~150 lines)
4. `tests/integration/test_forecast_query_integration.py` - Add integration tests (~100 lines)

**Estimated Lines:** ~500 new lines (well within MVP scope)

[Source: docs/architecture/repository-structure.md]

### Learnings from Previous Story (4.10)

**Story 4.10 Completion Summary:**
- **Status:** DONE (2025-11-27)
- **Created 7 files:** Validation framework (tests/validation/, scripts/)
- **Test Results:** 87 tests pass, 100% success rate
- **Key Pattern:** Orchestrator pattern for E2E validation (reusable validators)
- **Dependencies:** No new libraries added (used approved stack only)
- **Code Quality:** APPROVED - Google-style docstrings, full type annotations

**Key Learnings:**
1. **Reusable Patterns:** Validator classes are reusable across metrics (ForecastAccuracyValidator, InsightQualityValidator). Consider this pattern for SQL extraction if we need multiple extraction strategies.
2. **Edge Case Handling:** Story 4.10 used SMAPE fallback for zero values in MAPE calculation. Similarly, our period parsing should handle edge cases gracefully (invalid formats, missing data).
3. **Orchestration:** E2E tests used orchestrator pattern to coordinate multiple validators. Our integration test should coordinate SQL extraction → forecasting → validation.
4. **No New Dependencies:** Epic 4 maintained approved dependency list. This bug fix should also use only approved libraries (PostgreSQL driver already in stack).
5. **Mocking Strategy:** Story 4.10 noted that validation report showed 100% MAPE with mocked LLM. Ensure our tests clearly distinguish mocked vs. real database tests.

**Files Created in Story 4.10 (for reference):**
- `tests/validation/test_forecast_accuracy.py` (~400 lines)
- `tests/validation/test_insight_quality.py` (~730 lines)
- `tests/validation/test_recommendation_alignment.py` (~800 lines)
- `tests/validation/test_epic4_e2e_validation.py` (~686 lines)
- `scripts/generate_validation_report.py` (~380 lines)
- `tests/unit/test_validation_utilities.py` (~430 lines)
- `raglite/insights/recommendations.py` (~386 lines, supporting code from Story 4.8)

**Unresolved Review Items:** None (all APPROVED, no follow-ups)

[Source: docs/sprint-artifacts/4-10-forecasting-insights-test-suite.md, lines 400-477]

### References

[Source: docs/prd/epic-4-forecasting-proactive-insights.md] - Epic 4 PRD with Stories 4.1-4.10 requirements
[Source: docs/prd/epic-5-production-readiness-real-time-operations.md] - Epic 5 context
[Source: docs/architecture/high-level-architecture.md] - Microservices architecture, graceful degradation pattern
[Source: docs/architecture/coding-standards.md] - Type hints, docstrings, error handling, structured logging
[Source: docs/architecture/testing-strategy.md] - Unit/integration test requirements, 80%+ coverage target
[Source: docs/architecture/database-operation-modes.md] - Three-mode database safety system
[Source: docs/architecture/database-schema.md] - PostgreSQL financial_tables schema
[Source: docs/sprint-artifacts/4-10-forecasting-insights-test-suite.md] - Previous story learnings
[Source: UAT session 2025-11-28] - Bug discovery and root cause analysis

---

## Dev Agent Record

### Context Reference

**Story Context File:** docs/sprint-artifacts/5-0-1-fix-timeseries-period-extraction.context.xml (Generated: 2025-11-28)

**Story Context:** This bug fix story is part of Epic 5 prep work following Epic 4 UAT testing. The forecasting feature (Stories 4.1-4.4) is blocked due to time-series extraction failure.

**Prerequisites:**
- Epic 4 Stories 4.1-4.4 implementation complete
- PostgreSQL `financial_tables` populated from Story 2.6
- Forecasting engine implemented (Story 4.2)
- MCP tool `get_financial_forecast` exists but non-functional

**Related Stories:**
- Story 2.6: SQL Table Extraction & PostgreSQL Integration (source of `financial_tables`)
- Story 4.1: Time-Series Data Extraction (original implementation using hybrid search)
- Story 4.2: Forecasting Engine Implementation (Prophet forecasting)
- Story 4.4: Forecast Query Tool (MCP tool that's currently broken)
- Story 4.10: Forecasting & Insights Test Suite (validation framework)

### Agent Model Used

*To be filled by Dev agent during implementation*

### Debug Log References

*To be filled by Dev agent during implementation*

### Completion Notes

- [ ] SQL migration executed on production database
- [ ] New SQL extraction function implemented and tested
- [ ] MCP forecast tool updated to use SQL-first extraction
- [ ] All unit tests pass (≥80% coverage)
- [ ] All integration tests pass
- [ ] UAT queries re-tested and PASS
- [ ] BUG-E4-001 marked RESOLVED
- [ ] Epic 4 UAT status updated to COMPLETE

### File List

*To be filled by Dev agent during implementation with format:*

**NEW:**
- file_path (line count, description)

**MODIFIED:**
- file_path (lines changed, description)

---

## Definition of Done

- [ ] AC1: SQL migration executed, fiscal_year populated for 300,000+ rows
- [ ] AC2: `extract_timeseries_from_sql()` function implemented
- [ ] AC3: `get_financial_forecast` MCP tool uses SQL extraction first
- [ ] AC4: Integration tests pass for SQL-based extraction
- [ ] AC5: Unit tests pass for period parsing
- [ ] UAT-E4-001 through UAT-E4-005 re-tested and PASS
- [ ] All unit tests pass with ≥80% coverage
- [ ] All integration tests pass
- [ ] Code reviewed and approved
- [ ] Migration documented in CHANGELOG
- [ ] No linting errors (`uv run ruff check .`)
- [ ] No type errors (`uv run mypy raglite/`)
- [ ] Story updated with completion notes

---

## Test Plan

### SQL Migration Verification

```sql
-- Before migration
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN period IS NOT NULL THEN 1 END) as with_period,
    COUNT(CASE WHEN fiscal_year IS NOT NULL THEN 1 END) as with_fiscal_year
FROM financial_tables;
-- Expected: total=386466, with_period=344316, with_fiscal_year=14022

-- After migration
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN period IS NOT NULL THEN 1 END) as with_period,
    COUNT(CASE WHEN fiscal_year IS NOT NULL THEN 1 END) as with_fiscal_year
FROM financial_tables;
-- Expected: total=386466, with_period=344316, with_fiscal_year=~320000+
```

### Unit Tests

- `test_parse_period_to_date_jan_25()` - "Jan-25" → datetime(2025, 1, 1)
- `test_parse_period_to_date_aug_24()` - "Aug-24" → datetime(2024, 8, 1)
- `test_extract_timeseries_from_sql_revenue()` - Mocked SQL returns valid TimeSeriesData
- `test_extract_timeseries_from_sql_insufficient_data()` - Raises ExtractionError

### Integration Tests

- `test_sql_extraction_finds_revenue_data()` - Real database query returns data
- `test_forecast_tool_uses_sql_extraction()` - End-to-end MCP tool test
- `test_forecast_tool_fallback_to_hybrid()` - SQL fails, falls back gracefully

### UAT Re-Test (After Fix)

Re-run on Claude.ai with RAGLite MCP:
- **UAT-E4-001:** "What's the revenue forecast for the next quarter?"
- **UAT-E4-002:** "Forecast expenses for the next 4 quarters"
- **UAT-E4-003:** "What will cash flow be in Q2 2026?"
- **UAT-E4-004:** "Forecast employee count" (should error gracefully)
- **UAT-E4-005:** Structured query with metric="revenue", periods_ahead=4

---

## Dependencies

- None (standalone fix)

## Blocked By

- None

## Blocks

- Full Epic 4 sign-off
- Epic 5 production deployment (forecasting feature)

---

## Estimation

| Task | Estimate |
|------|----------|
| Write SQL migration script for fiscal_year | 30 min |
| Test migration on dev database | 30 min |
| Implement `extract_timeseries_from_sql()` | 2 hours |
| Implement `parse_period_to_date()` | 30 min |
| Modify `get_financial_forecast()` for SQL-first | 1 hour |
| Unit tests for new functions | 1 hour |
| Integration tests | 1 hour |
| Run migration on production | 15 min |
| UAT re-testing | 1 hour |
| Code review & merge | 30 min |
| **Total** | **~8 hours (1 day)** |

**Story Points: 5** (reflects complexity of database migration + new code + testing)

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-11-28 | Ricardo | Bug discovered during Epic 4 UAT testing |
| 2025-11-28 | SM (Bob) | Story created from bug report (initial draft) |
| 2025-11-28 | SM (Bob) | Story restructured to standard template (validation auto-improve) |

---

## Notes

- **NO RE-INGESTION REQUIRED** - Key finding from analysis
- The `period` column is already 89% populated
- SQL migration only needs to backfill `fiscal_year` from `period`
- **NEW CODE REQUIRED:** SQL-based extraction function to query `financial_tables`
- The original `extract_timeseries()` uses hybrid search + LLM (unreliable for structured data)
- Adding SQL-first extraction provides deterministic, reliable time-series data
- Fallback to hybrid search maintains backward compatibility
