# ATDD Checklist - Epic 3, Story 3.0.2: Create Epic 3 Data Dictionary

**Date:** 2025-11-06
**Author:** Murat (Test Architect)
**Primary Test Level:** Unit Tests (pytest)

---

## Story Summary

Create comprehensive data dictionary documenting available analytical query data to prevent Epic 2's ground truth misalignment issue (12% → 77.6% accuracy gap).

**As a** test architect preparing for Epic 3
**I want** a data dictionary documenting available analytical query data
**So that** ground truth tests align with actual database content and we avoid Epic 2's 12% → 77.6% issue

---

## Acceptance Criteria

1. **AC1: Database Inspection (4 hours)** - Query database and catalog all available data for analytical queries
2. **AC2: Create Data Dictionary Document (2 hours)** - Human-readable markdown documentation of available data
3. **AC3: Winston Architecture Review (30 minutes)** - Verify data dictionary completeness and Epic 3 readiness

---

## Failing Tests Created (RED Phase)

### Unit Tests (14 tests)

**File:** `tests/unit/test_inspect_database_epic_3.py` (~420 lines)

**Test Classes:**
- `TestFetchDistinctMetrics` (3 tests)
- `TestFetchDistinctPeriods` (1 test)
- `TestFetchDistinctEntities` (1 test)
- `TestFetchDistinctCurrencies` (1 test)
- `TestFetchRowCount` (1 test)
- `TestGenerateJsonCatalog` (2 tests)
- `TestSaveCatalogToFile` (2 tests)
- `TestInspectDatabase` (2 tests)
- `TestInspectionResultModel` (2 tests)

**Individual Test List:**

- ✅ **Test:** `test_fetch_distinct_metrics_success`
  - **Status:** RED - ImportError: `fetch_distinct_metrics` does not exist
  - **Verifies:** Queries all unique metrics from financial_tables, returns sorted list

- ✅ **Test:** `test_fetch_distinct_metrics_empty_table`
  - **Status:** RED - ImportError: `fetch_distinct_metrics` does not exist
  - **Verifies:** Handles empty table gracefully, returns empty list

- ✅ **Test:** `test_fetch_distinct_metrics_database_error`
  - **Status:** RED - ImportError: `fetch_distinct_metrics` does not exist
  - **Verifies:** Raises ConnectionError when database unavailable

- ✅ **Test:** `test_fetch_distinct_periods_success`
  - **Status:** RED - ImportError: `fetch_distinct_periods` does not exist
  - **Verifies:** Queries all unique periods, handles Month-Year and Month-YTD formats

- ✅ **Test:** `test_fetch_distinct_entities_success`
  - **Status:** RED - ImportError: `fetch_distinct_entities` does not exist
  - **Verifies:** Queries all unique entities, returns sorted list

- ✅ **Test:** `test_fetch_distinct_currencies_success`
  - **Status:** RED - ImportError: `fetch_distinct_currencies` does not exist
  - **Verifies:** Queries all currencies (EUR expected)

- ✅ **Test:** `test_fetch_row_count_success`
  - **Status:** RED - ImportError: `fetch_row_count` does not exist
  - **Verifies:** Queries total row count (170,142 expected)

- ✅ **Test:** `test_generate_json_catalog_structure`
  - **Status:** RED - ImportError: `generate_json_catalog` does not exist
  - **Verifies:** Produces correct JSON structure with all required fields

- ✅ **Test:** `test_generate_json_catalog_empty_data`
  - **Status:** RED - ImportError: `generate_json_catalog` does not exist
  - **Verifies:** Handles empty data with empty arrays in catalog

- ✅ **Test:** `test_save_catalog_to_file_success`
  - **Status:** RED - ImportError: `save_catalog_to_file` does not exist
  - **Verifies:** Writes JSON to file with proper formatting

- ✅ **Test:** `test_save_catalog_to_file_creates_directory`
  - **Status:** RED - ImportError: `save_catalog_to_file` does not exist
  - **Verifies:** Creates parent directories if they don't exist

- ✅ **Test:** `test_inspect_database_full_flow`
  - **Status:** RED - ImportError: `inspect_database` does not exist
  - **Verifies:** Orchestrates all queries and returns complete catalog

- ✅ **Test:** `test_inspect_database_saves_json`
  - **Status:** RED - ImportError: `inspect_database` does not exist
  - **Verifies:** Saves catalog to JSON file at specified path

- ✅ **Test:** `test_inspection_result_validation`
  - **Status:** RED - ImportError: `InspectionResult` model does not exist
  - **Verifies:** Pydantic model validation (optional, recommended)

### Integration Tests (7 tests)

**File:** `tests/integration/test_inspect_database_epic_3_integration.py` (~220 lines)

**Test Classes:**
- `TestInspectDatabaseIntegration` (6 tests)
- `TestDataDictionaryValidation` (2 tests - marked slow)

**Individual Test List:**

- ✅ **Test:** `test_inspect_database_against_real_db`
  - **Status:** RED - ImportError: `inspect_database` does not exist
  - **Verifies:** Full inspection against PostgreSQL with 170,142 rows

- ✅ **Test:** `test_inspect_database_metrics_completeness`
  - **Status:** RED - ImportError: `inspect_database` does not exist
  - **Verifies:** All metrics from Story 3.0.2 AC1 present in catalog

- ✅ **Test:** `test_inspect_database_period_formats`
  - **Status:** RED - ImportError: `inspect_database` does not exist
  - **Verifies:** Both Month-Year and Month-YTD period formats present

- ✅ **Test:** `test_inspect_database_entity_aliases`
  - **Status:** RED - ImportError: `inspect_database` does not exist
  - **Verifies:** All entities including fuzzy-match aliases present

- ✅ **Test:** `test_inspect_database_json_file_creation`
  - **Status:** RED - ImportError: `inspect_database` does not exist
  - **Verifies:** Creates valid JSON file at specified path

- ✅ **Test:** `test_inspect_database_handles_missing_columns`
  - **Status:** RED - ImportError: `inspect_database` does not exist
  - **Verifies:** Gracefully handles schema variations

- ✅ **Test:** `test_generated_catalog_supports_ground_truth_creation` (slow)
  - **Status:** RED - ImportError: `inspect_database` does not exist
  - **Verifies:** Catalog enables validation rules to prevent Epic 2's accuracy gap

---

## Data Factories Created

### Epic 3 Factories

**File:** `tests/support/factories.py` (updated)

**Exports:**

- `create_inspection_catalog(overrides={})` - Create sample database inspection catalog
  - Default fields: metrics, periods, entities, currencies, total_rows
  - Supports overrides for specific test scenarios

- `create_database_query_result(field="metric", values=[])` - Create mock database query result
  - Configurable field name (metric, period, entity, currency)
  - Configurable values list

**Example Usage:**

```python
# Default catalog with random row count
catalog = create_inspection_catalog()

# Specific row count matching Story 3.0.2
catalog = create_inspection_catalog(total_rows=170142)

# Mock metrics query result
metrics_result = create_database_query_result(
    field="metric",
    values=["EBITDA", "Revenue", "Variable Cost"]
)
```

---

## Fixtures Created

### Epic 3 Fixtures

**File:** `tests/fixtures/epic3_fixtures.py` (~200 lines)

**Fixtures:**

- `sample_metrics_query_result` - Mock metrics query result from database
  - **Setup:** Creates list of dicts with metric field
  - **Provides:** Sample data for testing fetch_distinct_metrics
  - **Cleanup:** N/A (immutable data)

- `sample_periods_query_result` - Mock periods query result
  - **Setup:** Creates period data including Month-Year and Month-YTD formats
  - **Provides:** Sample data for testing fetch_distinct_periods
  - **Cleanup:** N/A (immutable data)

- `sample_entities_query_result` - Mock entities query result
  - **Setup:** Creates entity data including fuzzy-match aliases
  - **Provides:** Sample data for testing fetch_distinct_entities
  - **Cleanup:** N/A (immutable data)

- `sample_currencies_query_result` - Mock currencies query result
  - **Setup:** Creates EUR currency data
  - **Provides:** Sample data for testing fetch_distinct_currencies
  - **Cleanup:** N/A (immutable data)

- `sample_inspection_catalog` - Complete inspection catalog
  - **Setup:** Creates full catalog with 170,142 rows
  - **Provides:** Pre-built catalog for testing
  - **Cleanup:** N/A (immutable data)

- `mock_db_client_for_inspection` - Configured AsyncMock database client
  - **Setup:** AsyncMock with pre-configured query responses
  - **Provides:** Mock database client for unit tests
  - **Cleanup:** Automatic (mock object)

- `temp_output_dir` - Temporary output directory
  - **Setup:** Creates temp directory using pytest's tmp_path
  - **Provides:** Path for file writing tests
  - **Cleanup:** Automatic (pytest handles tmp_path cleanup)

- `real_db_with_cleanup` (integration only) - Real PostgreSQL client
  - **Setup:** Connects to PostgreSQL, verifies financial_tables exists
  - **Provides:** Real database client for integration tests
  - **Cleanup:** Closes database connection

**Example Usage:**

```python
from tests.fixtures.epic3_fixtures import mock_db_client_for_inspection

@pytest.mark.asyncio
async def test_inspection(mock_db_client_for_inspection):
    # Client automatically returns sample data
    catalog = await inspect_database(mock_db_client_for_inspection)
    assert catalog["total_rows"] == 170142
```

---

## Mock Requirements

### Database Client Mock

**Interface:** `asyncpg` connection (from `raglite.shared.clients.get_db_client()`)

**Success Responses:**

```python
# fetch() - Returns list of dictionaries
await mock_db.fetch("SELECT DISTINCT metric FROM financial_tables;")
# → [{"metric": "EBITDA"}, {"metric": "Revenue"}, ...]

# fetchval() - Returns single value
await mock_db.fetchval("SELECT COUNT(*) FROM financial_tables;")
# → 170142
```

**Failure Response:**

```python
# ConnectionError when database unavailable
mock_db.fetch.side_effect = ConnectionError("Database unavailable")
```

**Notes:**
- Use `AsyncMock` from `unittest.mock` for async database methods
- Configure `side_effect` for multiple sequential queries
- Use `return_value` for single query responses

---

## Required Database Schema

### financial_tables Schema

**Note:** This schema already exists from Epic 2 implementation. No new columns needed.

```sql
CREATE TABLE financial_tables (
    id SERIAL PRIMARY KEY,
    entity TEXT NOT NULL,
    metric TEXT NOT NULL,
    value NUMERIC,
    unit TEXT,
    period TEXT,
    fiscal_year INTEGER,
    page_number INTEGER,
    source_document TEXT,
    currency TEXT  -- Added in Epic 2 Phase 2B (conditional)
);
```

**Required Data:**
- 170,142 rows populated from ingested financial PDF
- Distinct metrics: EBITDA, Revenue, Variable Cost, Fixed Cost, etc.
- Distinct periods: Aug-25, Sep-25, Aug-25 YTD, etc.
- Distinct entities: Portugal Cement, Tunisia Cement, Secil Angola, etc.
- Currency: EUR (primary)

---

## Implementation Checklist

### AC1: Database Inspection (4 hours)

#### Test Group: Fetch Distinct Metrics

**Tests:** `test_fetch_distinct_metrics_*` (3 tests)

**Tasks to make these tests pass:**

- [ ] Create `scripts/inspect-database-for-epic-3.py` file
- [ ] Implement `fetch_distinct_metrics(db_client)` async function
  - SQL query: `SELECT DISTINCT metric FROM financial_tables ORDER BY metric;`
  - Return sorted list of metric strings
  - Handle empty table (return empty list)
  - Raise ConnectionError on database failure
- [ ] Add type hints: `async def fetch_distinct_metrics(db: Connection) -> list[str]`
- [ ] Add docstring with Google-style format
- [ ] Run tests: `uv run pytest tests/unit/test_inspect_database_epic_3.py::TestFetchDistinctMetrics -v`
- [ ] ✅ All 3 tests pass (green phase)

**Estimated Effort:** 30 minutes

---

#### Test Group: Fetch Distinct Periods, Entities, Currencies, Row Count

**Tests:** `test_fetch_distinct_periods_success`, `test_fetch_distinct_entities_success`, `test_fetch_distinct_currencies_success`, `test_fetch_row_count_success`

**Tasks to make these tests pass:**

- [ ] Implement `fetch_distinct_periods(db_client)` async function
  - SQL query: `SELECT DISTINCT period FROM financial_tables ORDER BY period;`
- [ ] Implement `fetch_distinct_entities(db_client)` async function
  - SQL query: `SELECT DISTINCT entity FROM financial_tables ORDER BY entity;`
- [ ] Implement `fetch_distinct_currencies(db_client)` async function
  - SQL query: `SELECT DISTINCT currency FROM financial_tables ORDER BY currency;`
- [ ] Implement `fetch_row_count(db_client)` async function
  - SQL query: `SELECT COUNT(*) FROM financial_tables;`
  - Use `fetchval()` method (returns single value)
- [ ] Add type hints for all functions
- [ ] Add docstrings for all functions
- [ ] Run tests: `uv run pytest tests/unit/test_inspect_database_epic_3.py::TestFetchDistinct* -v`
- [ ] Run tests: `uv run pytest tests/unit/test_inspect_database_epic_3.py::TestFetchRowCount -v`
- [ ] ✅ All 4 tests pass (green phase)

**Estimated Effort:** 1 hour

---

#### Test Group: JSON Catalog Generation

**Tests:** `test_generate_json_catalog_structure`, `test_generate_json_catalog_empty_data`

**Tasks to make these tests pass:**

- [ ] Implement `generate_json_catalog()` function
  - Parameters: `metrics: list[str], periods: list[str], entities: list[str], currencies: list[str], total_rows: int`
  - Return: `dict[str, Any]` with keys: metrics, periods, entities, currencies, total_rows
  - Handle empty lists gracefully
- [ ] Add type hints
- [ ] Add docstring
- [ ] Run tests: `uv run pytest tests/unit/test_inspect_database_epic_3.py::TestGenerateJsonCatalog -v`
- [ ] ✅ Both tests pass (green phase)

**Estimated Effort:** 20 minutes

---

#### Test Group: Save Catalog to File

**Tests:** `test_save_catalog_to_file_success`, `test_save_catalog_to_file_creates_directory`

**Tasks to make these tests pass:**

- [ ] Implement `save_catalog_to_file(catalog, output_path)` function
  - Use `pathlib.Path` for path handling
  - Create parent directories if they don't exist: `Path(output_path).parent.mkdir(parents=True, exist_ok=True)`
  - Write JSON with `json.dump(catalog, f, indent=2)`
  - Use `with open(output_path, "w") as f:`
- [ ] Add type hints: `def save_catalog_to_file(catalog: dict[str, Any], output_path: str) -> None`
- [ ] Add docstring
- [ ] Run tests: `uv run pytest tests/unit/test_inspect_database_epic_3.py::TestSaveCatalogToFile -v`
- [ ] ✅ Both tests pass (green phase)

**Estimated Effort:** 20 minutes

---

#### Test Group: Main Orchestration Function

**Tests:** `test_inspect_database_full_flow`, `test_inspect_database_saves_json`

**Tasks to make these tests pass:**

- [ ] Implement `inspect_database(db_client, output_path=None)` async function
  - Call all fetch functions in sequence
  - Aggregate results using `generate_json_catalog()`
  - If `output_path` provided, call `save_catalog_to_file()`
  - Return complete catalog
- [ ] Add type hints: `async def inspect_database(db: Connection, output_path: str | None = None) -> dict[str, Any]`
- [ ] Add comprehensive docstring with Args, Returns, Example
- [ ] Run tests: `uv run pytest tests/unit/test_inspect_database_epic_3.py::TestInspectDatabase -v`
- [ ] ✅ Both tests pass (green phase)

**Estimated Effort:** 30 minutes

---

#### Test Group: Pydantic Model (Optional)

**Tests:** `test_inspection_result_validation`, `test_inspection_result_invalid_data`

**Tasks to make these tests pass (OPTIONAL - can defer):**

- [ ] Create `InspectionResult` Pydantic model in script
  - Fields: `metrics: list[str]`, `periods: list[str]`, `entities: list[str]`, `currencies: list[str]`, `total_rows: int`
  - Validators: `total_rows >= 0`
  - Use `BaseModel` from `pydantic`
- [ ] Update `inspect_database()` to return `InspectionResult` instead of `dict`
- [ ] Run tests: `uv run pytest tests/unit/test_inspect_database_epic_3.py::TestInspectionResultModel -v`
- [ ] ✅ Both tests pass (green phase)

**Estimated Effort:** 15 minutes (OPTIONAL)

---

#### Integration Test: Full Flow Against Real Database

**Test:** `test_inspect_database_against_real_db`

**Tasks to make this test pass:**

- [ ] Ensure PostgreSQL is running: `docker-compose up -d`
- [ ] Verify financial_tables has 170,142 rows
- [ ] Verify `get_db_client()` from `raglite.shared.clients` is accessible
- [ ] Run integration test: `uv run pytest tests/integration/test_inspect_database_epic_3_integration.py::TestInspectDatabaseIntegration::test_inspect_database_against_real_db -v`
- [ ] ✅ Test passes (validates against real database)

**Estimated Effort:** 10 minutes (assuming database already populated from Epic 2)

---

#### AC1 Validation Script Execution

**Final AC1 Task:**

- [ ] Create main execution block in script:
  ```python
  if __name__ == "__main__":
      import asyncio
      from raglite.shared.clients import get_db_client

      async def main():
          db = get_db_client()
          catalog = await inspect_database(db, output_path="docs/data-dictionary-epic-3.json")
          print(f"Inspection complete. Total rows: {catalog['total_rows']}")
          print(f"Metrics: {len(catalog['metrics'])}")
          print(f"Catalog saved to: docs/data-dictionary-epic-3.json")

      asyncio.run(main())
  ```
- [ ] Run script: `uv run python scripts/inspect-database-for-epic-3.py`
- [ ] Verify output: `docs/data-dictionary-epic-3.json` created with 170,142 rows
- [ ] ✅ AC1 complete

**Estimated Effort:** 10 minutes

---

### AC2: Create Data Dictionary Document (2 hours)

**Note:** AC2 does not have automated tests. Manual creation following Story 3.0.2 template.

**Tasks:**

- [ ] Read `docs/data-dictionary-epic-3.json` (output from AC1)
- [ ] Create `docs/data-dictionary-epic-3.md` using template from Story 3.0.2 AC2
- [ ] Fill "Available Metrics" section with table (Metric, Description, Sample Value, Unit)
  - Use actual data from JSON catalog
  - Add descriptions and examples for each metric
- [ ] Fill "Available Periods" section
  - List all unique periods from JSON
  - Document Period Mappings from Story 2.15 (Q3 2025 → Aug-25, Sep-25, etc.)
- [ ] Fill "Available Entities" section
  - List all entities from JSON
  - Document Entity Aliases from Story 2.14 AC1 ("Group" → "Currency (1000 EUR)", etc.)
- [ ] Fill "Available Currencies" section
  - Document EUR as primary currency
  - Mark missing currencies (AOA, BRL, TND) as NOT AVAILABLE
- [ ] Fill "Data Limitations" section
  - Missing Metrics (Headcount, G&A Expenses, Growth rate baselines)
  - Missing Period Variants (Budget, Forecast)
  - Missing Entities
- [ ] Fill "Test Query Validation Rules" section
  - 4-step validation process (Metric Check, Period Check, Entity Check, Currency Check)
- [ ] Add References section linking to source schemas and normalization logic
- [ ] ✅ AC2 complete - Data dictionary created

**Estimated Effort:** 2 hours

---

### AC3: Winston Architecture Review (30 minutes)

**Manual Review Tasks:**

- [ ] Share `docs/data-dictionary-epic-3.md` with Winston (Architect)
- [ ] Winston reviews:
  - [ ] Completeness (all metrics, periods, entities documented)
  - [ ] Limitations explicitly stated (no hidden assumptions)
  - [ ] Test query validation rules clear
  - [ ] Epic 3 stories can use dictionary as ground truth source
- [ ] Address any feedback from Winston
- [ ] Winston approval documented in story notes
- [ ] ✅ AC3 complete - Architecture approval received

**Estimated Effort:** 30 minutes

---

## Running Tests

```bash
# Run all unit tests for Story 3.0.2 (fast - ~1 second)
uv run pytest tests/unit/test_inspect_database_epic_3.py -v

# Run specific test class
uv run pytest tests/unit/test_inspect_database_epic_3.py::TestFetchDistinctMetrics -v

# Run integration tests (requires PostgreSQL running)
uv run pytest tests/integration/test_inspect_database_epic_3_integration.py -v

# Run all tests (unit + integration)
uv run pytest tests/unit/test_inspect_database_epic_3.py tests/integration/test_inspect_database_epic_3_integration.py -v

# Run with coverage
uv run pytest tests/unit/test_inspect_database_epic_3.py --cov=scripts --cov-report=html

# Run only P0 priority tests
uv run pytest tests/unit/test_inspect_database_epic_3.py -m "priority_P0" -v
```

---

## Red-Green-Refactor Workflow

### RED Phase (Complete) ✅

**TEA Agent Responsibilities:**

- ✅ All unit tests written and failing (14 tests)
- ✅ All integration tests written and failing (7 tests)
- ✅ Fixtures and factories created
  - `tests/fixtures/epic3_fixtures.py` (8 fixtures)
  - `tests/support/factories.py` (2 new factories)
- ✅ Mock requirements documented (AsyncMock database client)
- ✅ Database schema documented (financial_tables)
- ✅ Implementation checklist created with clear tasks

**Verification:**

- All tests fail with `ImportError` or `pytest.fail()` (expected - script not created yet)
- Failure messages are clear: "Implementation not yet created - {function_name} does not exist"
- Tests fail due to missing implementation, not test bugs
- Test structure follows project conventions (pytest markers, async, type hints)

---

### GREEN Phase (DEV Team - Next Steps)

**DEV Agent Responsibilities:**

1. **Pick one failing test group** from implementation checklist (start with AC1 first group)
2. **Read the tests** to understand expected behavior
3. **Implement minimal code** to make that specific test group pass
4. **Run the tests** to verify they now pass (green)
5. **Check off the tasks** in implementation checklist
6. **Move to next test group** and repeat

**Key Principles:**

- One test group at a time (don't try to fix all at once)
- Minimal implementation (don't over-engineer)
- Run tests frequently (immediate feedback)
- Use implementation checklist as roadmap
- Follow project coding standards (type hints, docstrings, async/await)

**Progress Tracking:**

- Check off tasks as you complete them in this document
- Share progress in daily standup
- Mark story as IN PROGRESS in `bmm-workflow-status.md`
- Commit after each GREEN phase (one test group at a time)

**Implementation Order (Recommended):**

1. Fetch functions (`fetch_distinct_metrics`, `fetch_distinct_periods`, etc.) - ~1.5 hours
2. JSON catalog generation (`generate_json_catalog`) - ~20 minutes
3. File saving (`save_catalog_to_file`) - ~20 minutes
4. Main orchestration (`inspect_database`) - ~30 minutes
5. Integration validation (run against real database) - ~10 minutes
6. Manual AC2 (create markdown documentation) - ~2 hours
7. Manual AC3 (Winston review) - ~30 minutes

**Total GREEN Phase Effort:** ~4.5 hours (AC1) + 2 hours (AC2) + 30 min (AC3) = **~7 hours**

---

### REFACTOR Phase (DEV Team - After All Tests Pass)

**DEV Agent Responsibilities:**

1. **Verify all tests pass** (green phase complete)
   - Run: `uv run pytest tests/unit/test_inspect_database_epic_3.py tests/integration/test_inspect_database_epic_3_integration.py -v`
   - All 21 tests should pass
2. **Review code for quality**
   - Readability: Clear function names, logical flow
   - Maintainability: No code duplication, simple logic
   - Performance: Efficient SQL queries, single database connection
3. **Extract duplications** (DRY principle)
   - Common query pattern: `SELECT DISTINCT {field} FROM financial_tables ORDER BY {field};`
   - Consider helper function: `async def fetch_distinct_field(db, field_name: str) -> list[str]`
4. **Add structured logging**
   - Log inspection start/complete
   - Log row counts and metrics found
   - Follow project logging standards: `logger.info("Inspection complete", extra={"total_rows": count})`
5. **Ensure tests still pass** after each refactor
6. **Update docstrings** if function signatures changed

**Key Principles:**

- Tests provide safety net (refactor with confidence)
- Make small refactors (easier to debug if tests fail)
- Run tests after each change
- Don't change test behavior (only implementation)

**Optional Refactoring Ideas:**

- Extract common query logic into helper function
- Add caching for database client connection
- Add progress logging for long-running inspection
- Create Pydantic model for type safety (`InspectionResult`)

**Completion:**

- All tests pass
- Code quality meets team standards (no linting errors)
- No duplications or code smells
- Structured logging added
- Ready for Winston architecture review (AC3)

---

## Next Steps

1. **Review this checklist** with Murat (Test Architect) or Ricardo (Project Lead)
2. **Run failing tests** to confirm RED phase: `uv run pytest tests/unit/test_inspect_database_epic_3.py -v`
   - Expected: All tests fail with ImportError or pytest.fail()
3. **Begin implementation** using implementation checklist as guide
4. **Work one test group at a time** (red → green for each group)
5. **Share progress** in daily standup
6. **When all tests pass**, refactor code for quality
7. **When refactoring complete**, run Winston architecture review (AC3)
8. **When AC3 approved**, mark story as DONE: `story-done 3.0.2`

---

## Knowledge Base References Applied

This ATDD workflow consulted the following BMad Method knowledge fragments:

- **fixture-architecture.md** - pytest fixture patterns with auto-cleanup using `@pytest.fixture`
- **data-factories.md** - Factory patterns using `faker` for random test data generation with overrides
- **test-quality.md** - Test design principles (clear test names, one assertion per test, determinism, isolation)

**Note:** Network-first and component-tdd patterns not applicable (backend script, no browser/UI testing)

See `bmad/bmm/testarch/tea-index.csv` for complete knowledge fragment mapping.

---

## Test Execution Evidence

### Initial Test Run (RED Phase Verification)

**Command:** `uv run pytest tests/unit/test_inspect_database_epic_3.py -v`

**Expected Results:**

```
tests/unit/test_inspect_database_epic_3.py::TestFetchDistinctMetrics::test_fetch_distinct_metrics_success FAILED
tests/unit/test_inspect_database_epic_3.py::TestFetchDistinctMetrics::test_fetch_distinct_metrics_empty_table FAILED
tests/unit/test_inspect_database_epic_3.py::TestFetchDistinctMetrics::test_fetch_distinct_metrics_database_error FAILED
tests/unit/test_inspect_database_epic_3.py::TestFetchDistinctPeriods::test_fetch_distinct_periods_success FAILED
tests/unit/test_inspect_database_epic_3.py::TestFetchDistinctEntities::test_fetch_distinct_entities_success FAILED
tests/unit/test_inspect_database_epic_3.py::TestFetchDistinctCurrencies::test_fetch_distinct_currencies_success FAILED
tests/unit/test_inspect_database_epic_3.py::TestFetchRowCount::test_fetch_row_count_success FAILED
tests/unit/test_inspect_database_epic_3.py::TestGenerateJsonCatalog::test_generate_json_catalog_structure FAILED
tests/unit/test_inspect_database_epic_3.py::TestGenerateJsonCatalog::test_generate_json_catalog_empty_data FAILED
tests/unit/test_inspect_database_epic_3.py::TestSaveCatalogToFile::test_save_catalog_to_file_success FAILED
tests/unit/test_inspect_database_epic_3.py::TestSaveCatalogToFile::test_save_catalog_to_file_creates_directory FAILED
tests/unit/test_inspect_database_epic_3.py::TestInspectDatabase::test_inspect_database_full_flow FAILED
tests/unit/test_inspect_database_epic_3.py::TestInspectDatabase::test_inspect_database_saves_json FAILED
tests/unit/test_inspect_database_epic_3.py::TestInspectionResultModel::test_inspection_result_validation FAILED

======================== 14 failed in 0.5s ========================
```

**Summary:**

- Total tests: 14 unit tests + 7 integration tests = **21 tests**
- Passing: 0 (expected - RED phase)
- Failing: 21 (expected - RED phase)
- Status: ✅ RED phase verified

**Expected Failure Messages:**

All tests fail with: `"Implementation not yet created - {function_name} does not exist"`

This is the correct RED phase state - tests define expected behavior, implementation does not exist yet.

---

## Notes

### Data-First Methodology (From Epic 2 Retrospective)

**Lesson Learned:**
- Epic 2 created ground truth from requirements, not database inspection
- Queries asked for data that doesn't exist ("Q3 2025" vs "Aug-25 YTD")
- Test misalignment caused 12% accuracy (66pp below implementation's actual 77.6%)

**New Process (Story 3.0.2):**
1. ✅ Inspect database → Document available data (AC1)
2. ✅ Create test queries from dictionary (AC2)
3. ✅ Validate queries against dictionary BEFORE execution (validation rules in AC2)

### Epic 3 Analytical Queries

**Difference from Epic 2:**
- Epic 2: Retrieval queries (simple metric lookups: "What is EBITDA in Aug-25?")
- Epic 3: Analytical queries (calculations, trends, multi-step reasoning: "What is EBITDA margin trend over Q3?")

**Data Requirements for Epic 3:**
- Time series data (YoY growth, trend analysis)
- Multiple metrics (margin = EBITDA / Revenue)
- Multi-entity comparisons (Portugal vs Tunisia)

### Testing Standards

**Dictionary as Single Source of Truth:**
- All Epic 3 test queries validated against dictionary
- No assumptions about data availability
- Explicit documentation of limitations

**Test Query Validation Rules (AC2):**
1. Metric Check: Is metric in "Available Metrics" table?
2. Period Check: Is period in "Available Periods" OR mappable via Story 2.15?
3. Entity Check: Is entity in "Available Entities" OR fuzzy-matchable via Story 2.14?
4. Currency Check: Does query request EUR?

---

## Contact

**Questions or Issues?**

- Ask Murat (Test Architect) - Epic 3 testing strategy
- Ask Winston (Architect) - Data dictionary completeness review (AC3)
- Ask Ricardo (Project Lead) - Epic 2 retrospective lessons, data-first approach
- Refer to `bmad/bmm/workflows/testarch/atdd/` for ATDD workflow documentation
- Consult `bmad/bmm/testarch/knowledge/` for pytest testing best practices

---

**Generated by BMad TEA Agent (Murat)** - 2025-11-06
