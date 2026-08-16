# ATDD Checklist - Story 9.6: Storage Extension - Store Classification Fields

**Story:** 9-6-storage-extension-store-classification-fields
**Phase:** TDD RED (Tests Created, All Failing)
**Date:** 2026-02-01

## Test Summary

| Metric | Value |
|--------|-------|
| Total Tests | 55 |
| Test Files | 5 |
| ACs Covered | AC1, AC2, AC3, AC4, AC5 |
| Status | RED (41 failed, 2 passed, 12 skipped) |

## Acceptance Criteria Coverage

### AC1: Classification Fields Included in INSERT Statement (8 tests)
**File:** `tests/acceptance/story_9_6/test_ac1_insert_statement_includes_classification.py`

| Test ID | Priority | Description | Status |
|---------|----------|-------------|--------|
| TEST-AC-9.6.1.1 | P0 | Storage module can be imported | PASS |
| TEST-AC-9.6.1.2 | P0 | store_tables_in_postgresql function exists | PASS |
| TEST-AC-9.6.1.3 | P0 | Row with classification stores period_type | FAIL |
| TEST-AC-9.6.1.4 | P0 | Row with classification stores value_type | FAIL |
| TEST-AC-9.6.1.5 | P0 | Row with classification stores entity_level | FAIL |
| TEST-AC-9.6.1.6 | P0 | All three classification fields in record tuple | FAIL |
| TEST-AC-9.6.1.7 | P0 | Record tuple has 16 fields (13 + 3 classification) | FAIL |
| TEST-AC-9.6.1.8 | P1 | Classification fields at end of tuple (positions 13-15) | FAIL |

### AC2: Backward Compatibility for Rows Without Classification (8 tests)
**File:** `tests/acceptance/story_9_6/test_ac2_backward_compatibility.py`

| Test ID | Priority | Description | Status |
|---------|----------|-------------|--------|
| TEST-AC-9.6.2.1 | P0 | Row without classification stores successfully with 16 fields | FAIL |
| TEST-AC-9.6.2.2 | P0 | Missing period_type becomes NULL at position 13 | FAIL |
| TEST-AC-9.6.2.3 | P0 | Missing value_type becomes NULL at position 14 | FAIL |
| TEST-AC-9.6.2.4 | P0 | Missing entity_level becomes NULL at position 15 | FAIL |
| TEST-AC-9.6.2.5 | P0 | All classification missing becomes three NULLs | FAIL |
| TEST-AC-9.6.2.6 | P0 | Mixed rows with/without classification processed | FAIL |
| TEST-AC-9.6.2.7 | P1 | Empty string classification preserved | FAIL |
| TEST-AC-9.6.2.8 | P0 | No error on legacy row format | FAIL |

### AC3: Classification Field Validation (17 tests)
**File:** `tests/acceptance/story_9_6/test_ac3_classification_field_validation.py`

| Test ID | Priority | Description | Status |
|---------|----------|-------------|--------|
| TEST-AC-9.6.3.1 | P0 | period_type monthly_actual stored | FAIL |
| TEST-AC-9.6.3.2 | P0 | period_type ytd_actual stored | FAIL |
| TEST-AC-9.6.3.3 | P0 | period_type budget stored | FAIL |
| TEST-AC-9.6.3.4 | P0 | period_type ytd_budget stored | FAIL |
| TEST-AC-9.6.3.5 | P0 | period_type unknown stored | FAIL |
| TEST-AC-9.6.3.6 | P0 | value_type actual stored | FAIL |
| TEST-AC-9.6.3.7 | P0 | value_type budget stored | FAIL |
| TEST-AC-9.6.3.8 | P0 | value_type forecast stored | FAIL |
| TEST-AC-9.6.3.9 | P0 | value_type variance stored | FAIL |
| TEST-AC-9.6.3.10 | P0 | value_type unknown stored | FAIL |
| TEST-AC-9.6.3.11 | P0 | entity_level consolidated stored | FAIL |
| TEST-AC-9.6.3.12 | P0 | entity_level company_only stored | FAIL |
| TEST-AC-9.6.3.13 | P0 | entity_level segment stored | FAIL |
| TEST-AC-9.6.3.14 | P0 | entity_level geographic stored | FAIL |
| TEST-AC-9.6.3.15 | P0 | entity_level unknown stored | FAIL |
| TEST-AC-9.6.3.16 | P1 | Storage does NOT validate enum membership | FAIL |
| TEST-AC-9.6.3.17 | P1 | Values stored case-sensitive | FAIL |

### AC4: Query Verification (12 tests)
**File:** `tests/acceptance/story_9_6/test_ac4_query_verification.py`

| Test ID | Priority | Description | Status |
|---------|----------|-------------|--------|
| TEST-AC-9.6.4.1 | P0 | Query by period_type returns filtered results | SKIP |
| TEST-AC-9.6.4.2 | P0 | Query by value_type returns filtered results | SKIP |
| TEST-AC-9.6.4.3 | P0 | Query by entity_level returns filtered results | SKIP |
| TEST-AC-9.6.4.4 | P0 | Combined filter on period_type AND value_type | SKIP |
| TEST-AC-9.6.4.5 | P0 | Combined filter on all three fields | SKIP |
| TEST-AC-9.6.4.6 | P1 | Query for rows with NULL classification | SKIP |
| TEST-AC-9.6.4.7 | P1 | Query for rows with non-NULL classification | SKIP |
| TEST-AC-9.6.4.8 | P1 | Query distinct period_type values | SKIP |
| TEST-AC-9.6.4.9 | P1 | Query distinct value_type values | SKIP |
| TEST-AC-9.6.4.10 | P1 | Query distinct entity_level values | SKIP |
| TEST-AC-9.6.4.11 | P1 | Query aggregation by period_type | SKIP |
| TEST-AC-9.6.4.12 | P2 | Index used for period_type filter query | SKIP |

**Note:** AC4 tests are skipped in RED phase because they require database infrastructure.
These tests will be enabled after implementation when integration test fixtures are available.

### AC5: Storage Metrics Include Classification (10 tests)
**File:** `tests/acceptance/story_9_6/test_ac5_storage_metrics.py`

| Test ID | Priority | Description | Status |
|---------|----------|-------------|--------|
| TEST-AC-9.6.5.1 | P0 | _count_classification_coverage function exists | FAIL |
| TEST-AC-9.6.5.2 | P0 | Rows with full classification counted | FAIL |
| TEST-AC-9.6.5.3 | P0 | Rows without classification counted | FAIL |
| TEST-AC-9.6.5.4 | P0 | Mixed rows counted correctly | FAIL |
| TEST-AC-9.6.5.5 | P0 | Partial classification counts as without | FAIL |
| TEST-AC-9.6.5.6 | P0 | Empty rows list returns zero counts | FAIL |
| TEST-AC-9.6.5.7 | P1 | Classification coverage percentage calculated | FAIL |
| TEST-AC-9.6.5.8 | P0 | Storage logging includes classification metrics | FAIL |
| TEST-AC-9.6.5.9 | P1 | Classification metrics in structured log extra | FAIL |
| TEST-AC-9.6.5.10 | P1 | Explicit None values treated as unclassified | FAIL |

## Failure Reasons (Expected)

### AC1, AC2, AC3: IndexError / AssertionError
```
IndexError: tuple index out of range
AssertionError: assert 13 == 16
```
Current implementation creates 13-field tuples. Tests expect 16 fields (13 original + 3 classification).

### AC5: ImportError / AssertionError
```
ImportError: cannot import name '_count_classification_coverage' from 'raglite.ingestion.storage.table_store'
AssertionError: assert False (hasattr check)
```
Function `_count_classification_coverage()` does not exist yet.

## Implementation Requirements

To make these tests pass, implement:

1. **Update `_prepare_table_records()`** in `raglite/ingestion/storage/table_store.py`:
   - Add `period_type`, `value_type`, `entity_level` to record tuple
   - Use `row.get("field_name")` with None default for backward compatibility
   - Record tuple: 16 fields (positions 13-15 for classification)

2. **Update INSERT statement** in `_insert_records_in_batches()`:
   - Add `period_type`, `value_type`, `entity_level` columns
   - Ensure VALUES placeholder count matches column count

3. **Add `_count_classification_coverage()` function**:
   - Count rows with all 3 classification fields populated
   - Count rows without classification (NULL or missing)
   - Calculate coverage percentage
   - Return dict with `rows_with_classification`, `rows_without_classification`, `classification_coverage_pct`

4. **Update `_log_storage_success()`**:
   - Accept classification_metrics parameter
   - Include metrics in log extra dict

## Run Tests

```bash
# Run all Story 9.6 ATDD tests
uv run pytest tests/acceptance/story_9_6/ -m "atdd or integration" -v

# Run specific AC tests
uv run pytest tests/acceptance/story_9_6/test_ac1_insert_statement_includes_classification.py -v
uv run pytest tests/acceptance/story_9_6/test_ac2_backward_compatibility.py -v
uv run pytest tests/acceptance/story_9_6/test_ac3_classification_field_validation.py -v
uv run pytest tests/acceptance/story_9_6/test_ac5_storage_metrics.py -v

# Run all tests (including skipped AC4)
uv run pytest tests/acceptance/story_9_6/ -v
```

## Next Phase

After implementation completes, re-run tests to verify GREEN state.
AC4 tests will require database fixtures to be enabled for integration testing.
