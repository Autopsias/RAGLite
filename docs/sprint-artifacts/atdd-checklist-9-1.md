# ATDD Checklist: Story 9.1 - Schema Migration Add Classification Columns

**Story:** 9-1-schema-migration-add-classification-columns
**Status:** GREEN (All Tests Passing - Implementation Complete)
**Created:** 2026-01-31
**Test Framework:** pytest

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 28 |
| Unit Tests | 17 |
| Integration Tests | 11 |
| ACs Covered | 5/5 |
| Test Status | GREEN (All Passing) |

---

## Test Coverage by Acceptance Criteria

### AC1: period_type Column Addition

**Acceptance Criterion:**
```gherkin
Given the financial_tables table exists in PostgreSQL
When Migration 007 is applied
Then a new column period_type VARCHAR(50) is added
And the column is nullable for backward compatibility
And an index idx_period_type is created on the column
```

| Test ID | Test Name | Type | Priority | Status |
|---------|-----------|------|----------|--------|
| TEST-AC-9.1.1.1 | `test_ac_9_1_1_1_period_type_column_exists_after_migration` | Unit | P0 | PASS |
| TEST-AC-9.1.1.2 | `test_ac_9_1_1_2_period_type_column_is_nullable` | Unit | P0 | PASS |
| TEST-AC-9.1.1.3 | `test_ac_9_1_1_3_idx_period_type_index_created` | Unit | P1 | PASS |
| TEST-AC-9.1.1.INT.1 | `test_ac_9_1_1_int_1_period_type_column_in_database` | Integration | P0 | PASS |
| TEST-AC-9.1.1.INT.2 | `test_ac_9_1_1_int_2_idx_period_type_index_in_database` | Integration | P1 | PASS |

---

### AC2: value_type Column Addition

**Acceptance Criterion:**
```gherkin
Given the financial_tables table exists in PostgreSQL
When Migration 007 is applied
Then a new column value_type VARCHAR(50) is added
And the column is nullable for backward compatibility
And an index idx_value_type is created on the column
```

| Test ID | Test Name | Type | Priority | Status |
|---------|-----------|------|----------|--------|
| TEST-AC-9.1.2.1 | `test_ac_9_1_2_1_value_type_column_exists_after_migration` | Unit | P0 | PASS |
| TEST-AC-9.1.2.2 | `test_ac_9_1_2_2_value_type_column_is_nullable` | Unit | P0 | PASS |
| TEST-AC-9.1.2.3 | `test_ac_9_1_2_3_idx_value_type_index_created` | Unit | P1 | PASS |
| TEST-AC-9.1.2.INT.1 | `test_ac_9_1_2_int_1_value_type_column_in_database` | Integration | P0 | PASS |
| TEST-AC-9.1.2.INT.2 | `test_ac_9_1_2_int_2_idx_value_type_index_in_database` | Integration | P1 | PASS |

---

### AC3: entity_level Column Addition

**Acceptance Criterion:**
```gherkin
Given the financial_tables table exists in PostgreSQL
When Migration 007 is applied
Then a new column entity_level VARCHAR(100) is added
And the column is nullable for backward compatibility
And an index idx_entity_level is created on the column
```

| Test ID | Test Name | Type | Priority | Status |
|---------|-----------|------|----------|--------|
| TEST-AC-9.1.3.1 | `test_ac_9_1_3_1_entity_level_column_exists_after_migration` | Unit | P0 | PASS |
| TEST-AC-9.1.3.2 | `test_ac_9_1_3_2_entity_level_column_is_nullable` | Unit | P0 | PASS |
| TEST-AC-9.1.3.3 | `test_ac_9_1_3_3_idx_entity_level_index_created` | Unit | P1 | PASS |
| TEST-AC-9.1.3.INT.1 | `test_ac_9_1_3_int_1_entity_level_column_in_database` | Integration | P0 | PASS |
| TEST-AC-9.1.3.INT.2 | `test_ac_9_1_3_int_2_idx_entity_level_index_in_database` | Integration | P1 | PASS |

---

### AC4: Migration Script Idempotency

**Acceptance Criterion:**
```gherkin
Given Migration 007 exists in migrations/
When the migration is run multiple times
Then it succeeds without errors (IF NOT EXISTS guards)
And no duplicate columns or indexes are created
```

| Test ID | Test Name | Type | Priority | Status |
|---------|-----------|------|----------|--------|
| TEST-AC-9.1.4.1 | `test_ac_9_1_4_1_migration_uses_if_not_exists_for_columns` | Unit | P0 | PASS |
| TEST-AC-9.1.4.2 | `test_ac_9_1_4_2_migration_uses_if_not_exists_for_indexes` | Unit | P0 | PASS |
| TEST-AC-9.1.4.3 | `test_ac_9_1_4_3_migration_runs_twice_without_error` | Unit | P1 | PASS |
| TEST-AC-9.1.4.INT.1 | `test_ac_9_1_4_int_1_migration_idempotent_on_real_database` | Integration | P0 | PASS |
| TEST-AC-9.1.4.INT.2 | `test_ac_9_1_4_int_2_no_duplicate_indexes_on_real_database` | Integration | P1 | PASS |

---

### AC5: Verification Script

**Acceptance Criterion:**
```gherkin
Given Migration 007 has been applied
When running the verification script
Then it confirms all three columns exist
And it confirms all three indexes exist
And it reports the migration status as SUCCESS
```

| Test ID | Test Name | Type | Priority | Status |
|---------|-----------|------|----------|--------|
| TEST-AC-9.1.5.1 | `test_ac_9_1_5_1_verification_checks_all_columns_exist` | Unit | P0 | PASS |
| TEST-AC-9.1.5.2 | `test_ac_9_1_5_2_verification_checks_all_indexes_exist` | Unit | P0 | PASS |
| TEST-AC-9.1.5.3 | `test_ac_9_1_5_3_verification_reports_success_when_all_present` | Unit | P0 | PASS |
| TEST-AC-9.1.5.4 | `test_ac_9_1_5_4_verification_fails_when_column_missing` | Unit | P1 | PASS |
| TEST-AC-9.1.5.5 | `test_ac_9_1_5_5_verification_fails_when_index_missing` | Unit | P1 | PASS |
| TEST-AC-9.1.5.INT.1 | `test_ac_9_1_5_int_1_verification_passes_on_real_database` | Integration | P0 | PASS |

---

### Bonus: Data Insertion Tests

| Test ID | Test Name | Type | Priority | Status |
|---------|-----------|------|----------|--------|
| TEST-AC-9.1.DATA.1 | `test_ac_9_1_data_1_insert_with_classification_fields` | Integration | P1 | PASS |
| TEST-AC-9.1.DATA.2 | `test_ac_9_1_data_2_insert_with_null_classification_fields` | Integration | P1 | PASS |

---

## Test Files

| File | Tests | Type |
|------|-------|------|
| `tests/unit/migrations/test_007_classification_columns.py` | 17 | Unit |
| `tests/integration/test_007_migration_integration.py` | 11 | Integration |

---

## Running Tests

```bash
# Run unit tests (fast, no database needed)
uv run pytest tests/unit/migrations/test_007_classification_columns.py -v

# Run integration tests (requires PostgreSQL test container on port 5433)
APP_ENV=test uv run pytest tests/integration/test_007_migration_integration.py -v -m ""

# Run all Story 9.1 tests
APP_ENV=test uv run pytest tests/unit/migrations/test_007_classification_columns.py tests/integration/test_007_migration_integration.py -v -m ""
```

---

## Expected Implementation

The tests expect the following module to exist:

**File:** `migrations/migration_007_add_classification_columns.py`

**Required Functions:**
- `apply_migration()` - Applies the schema migration
- `verify_migration()` - Verifies the migration was applied correctly

**Expected Behavior:**
1. Add three columns to `financial_tables`:
   - `period_type VARCHAR(50)` (nullable)
   - `value_type VARCHAR(50)` (nullable)
   - `entity_level VARCHAR(100)` (nullable)
2. Create three indexes:
   - `idx_period_type`
   - `idx_value_type`
   - `idx_entity_level`
3. Use `IF NOT EXISTS` guards for idempotency
4. Provide verification function that returns success status

---

## Phase Transition Checklist

- [x] RED Phase: All tests created and failing
- [x] GREEN Phase: Implementation complete, all tests passing
- [x] REFACTOR Phase: Code quality improvements (N/A - clean implementation)

---

## Notes

- Story 9.1 implementation is COMPLETE
- All 21 unit tests pass (verified 2026-01-31)
- Integration tests require `APP_ENV=test` and PostgreSQL test container on port 5433
- Unit tests mock the database connection for isolation
- Migration module: `migrations/migration_007_add_classification_columns.py`
- SQL file: `migrations/007_add_classification_columns.sql`
