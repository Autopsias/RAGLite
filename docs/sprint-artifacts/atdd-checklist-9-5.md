# ATDD Checklist - Story 9.5: Integration - Connect Classification to Extraction

**Story:** 9-5-integration-connect-classification-to-extraction
**Phase:** TDD RED (Tests Created, All Failing)
**Date:** 2026-02-01

## Test Summary

| Metric | Value |
|--------|-------|
| Total Tests | 60 |
| Test Files | 6 |
| ACs Covered | AC1, AC2, AC3, AC4, AC5, AC6 |
| Status | RED (all tests failing as expected) |

## Acceptance Criteria Coverage

### AC1: Classification Hook in Extraction Pipeline (9 tests)
**File:** `tests/acceptance/story_9_5/test_ac1_classification_hook_in_extraction.py`

| Test ID | Priority | Description | Status |
|---------|----------|-------------|--------|
| TEST-AC-9.5.1.1 | P0 | Integration module can be imported | FAIL |
| TEST-AC-9.5.1.2 | P0 | classify_row function exported | FAIL |
| TEST-AC-9.5.1.3 | P0 | classify_rows_batch function exported | FAIL |
| TEST-AC-9.5.1.4 | P0 | classify_row returns enriched row with fields | FAIL |
| TEST-AC-9.5.1.5 | P0 | classify_row preserves original fields | FAIL |
| TEST-AC-9.5.1.6 | P0 | classify_rows_batch processes multiple rows | FAIL |
| TEST-AC-9.5.1.7 | P1 | Classification invokes period classifier | FAIL |
| TEST-AC-9.5.1.8 | P1 | Classification invokes value_type classifier | FAIL |
| TEST-AC-9.5.1.9 | P1 | Classification invokes entity_level classifier | FAIL |

### AC2: Classification Field Population (14 tests)
**File:** `tests/acceptance/story_9_5/test_ac2_classification_field_population.py`

| Test ID | Priority | Description | Status |
|---------|----------|-------------|--------|
| TEST-AC-9.5.2.1 | P0 | Monthly actual period classified correctly | FAIL |
| TEST-AC-9.5.2.2 | P0 | Actual value type classified correctly | FAIL |
| TEST-AC-9.5.2.3 | P0 | Company entity level classified correctly | FAIL |
| TEST-AC-9.5.2.4 | P0 | All three fields populated | FAIL |
| TEST-AC-9.5.2.5 | P0 | UNKNOWN used for unclassifiable period (no NULLs) | FAIL |
| TEST-AC-9.5.2.6 | P0 | UNKNOWN used for unclassifiable value type (no NULLs) | FAIL |
| TEST-AC-9.5.2.7 | P0 | UNKNOWN used for unclassifiable entity (no NULLs) | FAIL |
| TEST-AC-9.5.2.8 | P1 | Budget period classified correctly | FAIL |
| TEST-AC-9.5.2.9 | P1 | YTD actual period classified correctly | FAIL |
| TEST-AC-9.5.2.10 | P1 | Consolidated entity level classified correctly | FAIL |
| TEST-AC-9.5.2.11 | P1 | Geographic entity level classified correctly | FAIL |
| TEST-AC-9.5.2.12 | P1 | Segment entity level classified correctly | FAIL |
| TEST-AC-9.5.2.13 | P1 | Empty period returns unknown | FAIL |
| TEST-AC-9.5.2.14 | P1 | None period returns unknown | FAIL |

### AC3: Classification Report Generation (12 tests)
**File:** `tests/acceptance/story_9_5/test_ac3_classification_report_generation.py`

| Test ID | Priority | Description | Status |
|---------|----------|-------------|--------|
| TEST-AC-9.5.3.1 | P0 | ClassificationSummary dataclass exists | FAIL |
| TEST-AC-9.5.3.2 | P0 | Summary has period_type breakdown | FAIL |
| TEST-AC-9.5.3.3 | P0 | Summary has value_type breakdown | FAIL |
| TEST-AC-9.5.3.4 | P0 | Summary has entity_level breakdown | FAIL |
| TEST-AC-9.5.3.5 | P0 | generate_classification_summary function exists | FAIL |
| TEST-AC-9.5.3.6 | P0 | generate_summary returns ClassificationSummary | FAIL |
| TEST-AC-9.5.3.7 | P0 | Summary counts total rows correctly | FAIL |
| TEST-AC-9.5.3.8 | P0 | Summary counts period types correctly | FAIL |
| TEST-AC-9.5.3.9 | P0 | Summary counts value types correctly | FAIL |
| TEST-AC-9.5.3.10 | P0 | Summary counts entity levels correctly | FAIL |
| TEST-AC-9.5.3.11 | P1 | Summary includes classification_duration_ms | FAIL |
| TEST-AC-9.5.3.12 | P1 | Empty rows returns zero counts | FAIL |

### AC4: Performance Constraint (6 tests)
**File:** `tests/acceptance/story_9_5/test_ac4_performance_constraint.py`

| Test ID | Priority | Description | Status |
|---------|----------|-------------|--------|
| TEST-AC-9.5.4.1 | P0 | Classify 1000 rows under 100ms | FAIL |
| TEST-AC-9.5.4.2 | P1 | Classify 100 rows under 10ms | FAIL |
| TEST-AC-9.5.4.3 | P1 | Batch classification faster than individual | FAIL |
| TEST-AC-9.5.4.4 | P2 | Memory scales linearly with batch size | FAIL |
| TEST-AC-9.5.4.5 | P1 | Classification overhead under 20% | FAIL |
| TEST-AC-9.5.4.6 | P0 | Uses batch classification functions | FAIL |

### AC5: Row Dict Schema Extension (9 tests)
**File:** `tests/acceptance/story_9_5/test_ac5_row_dict_schema_extension.py`

| Test ID | Priority | Description | Status |
|---------|----------|-------------|--------|
| TEST-AC-9.5.5.1 | P0 | period_type is string not enum | FAIL |
| TEST-AC-9.5.5.2 | P0 | value_type is string not enum | FAIL |
| TEST-AC-9.5.5.3 | P0 | entity_level is string not enum | FAIL |
| TEST-AC-9.5.5.4 | P0 | Enriched row is JSON serializable | FAIL |
| TEST-AC-9.5.5.5 | P0 | Original fields unchanged | FAIL |
| TEST-AC-9.5.5.6 | P0 | Backward compatible with existing consumers | FAIL |
| TEST-AC-9.5.5.7 | P1 | New fields use valid enum values | FAIL |
| TEST-AC-9.5.5.8 | P1 | Extra fields preserved | FAIL |
| TEST-AC-9.5.5.9 | P1 | No modification of input row | FAIL |

### AC6: Integration with Existing Classifiers (10 tests)
**File:** `tests/acceptance/story_9_5/test_ac6_integration_with_existing_classifiers.py`

| Test ID | Priority | Description | Status |
|---------|----------|-------------|--------|
| TEST-AC-9.5.6.1 | P0 | Period classifier module used | FAIL |
| TEST-AC-9.5.6.2 | P0 | Value type classifier module used | FAIL |
| TEST-AC-9.5.6.3 | P0 | Entity level classifier module used | FAIL |
| TEST-AC-9.5.6.4 | P0 | BUDGET period coordinates to BUDGET value_type | FAIL |
| TEST-AC-9.5.6.5 | P0 | YTD_BUDGET period coordinates to BUDGET value_type | FAIL |
| TEST-AC-9.5.6.6 | P0 | Actual period coordinates to ACTUAL value_type | FAIL |
| TEST-AC-9.5.6.7 | P0 | YTD_ACTUAL period coordinates to ACTUAL value_type | FAIL |
| TEST-AC-9.5.6.8 | P1 | No duplicate classification logic | FAIL |
| TEST-AC-9.5.6.9 | P1 | Batch classification uses existing batch functions | FAIL |
| TEST-AC-9.5.6.10 | P1 | Passes period_type to value classifier | FAIL |

## Failure Reason (Expected)

All tests fail with:
```
ModuleNotFoundError: No module named 'raglite.ingestion.classification.integration'
```

This is the expected RED state - the integration module does not exist yet.

## Implementation Requirements

To make these tests pass, implement:

1. **Module:** `raglite/ingestion/classification/integration.py`
2. **Functions:**
   - `classify_row(row: dict) -> dict`
   - `classify_rows_batch(rows: list[dict]) -> list[dict]`
   - `generate_classification_summary(rows: list[dict]) -> ClassificationSummary`
3. **Dataclass:** `ClassificationSummary`
4. **Export:** Functions via `raglite/ingestion/classification/__init__.py`

## Run Tests

```bash
# Run all Story 9.5 ATDD tests
uv run pytest tests/acceptance/story_9_5/ -m "atdd or integration" -v

# Run specific AC tests
uv run pytest tests/acceptance/story_9_5/test_ac1_classification_hook_in_extraction.py -m "atdd or integration" -v
```

## Next Phase

After implementation completes, re-run tests to verify GREEN state.
