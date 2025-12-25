# ATDD Checklist: Story 7b-4 Model Selection Cache in PostgreSQL

## Story Information

- **Story ID:** 7b-4
- **Epic:** 7b - Intelligent Model Selection Framework
- **Priority:** P0
- **Status:** TDD RED Phase (Tests Created, Implementation Pending)
- **Created:** 2024-12-21
- **Dependencies:** 7b-3 (Per-Variable Model Selection via Cross-Validation)

## Acceptance Criteria Summary

| AC ID | Description | Unit Tests | Integration Tests | Status |
|-------|-------------|------------|-------------------|--------|
| AC-7b.4.1 | New `model_selection` PostgreSQL table with columns and indexes | 5 tests | 4 tests | RED |
| AC-7b.4.2 | Store best_model, regressors, MAPE, MASE per variable (upsert) | 3 tests | 4 tests | RED |
| AC-7b.4.3 | `get_cached_model_selection()` with <100ms lookup | 6 tests | 4 tests | RED |
| AC-7b.4.4 | `invalidate_model_selection()` for manual refresh | 4 tests | 3 tests | RED |
| AC-7b.4.5 | 7-day TTL with automatic expiration | 9 tests | 3 tests | RED |
| AC-7b.4.6 | Migration script (idempotent) | N/A | 5 tests | RED |

**Total Tests:** 46 (26 unit + 20 integration)

---

## Test Files Created

### Unit Tests
- **File:** `tests/unit/test_model_selection_cache.py`
- **Count:** 26 tests
- **Markers:** `@pytest.mark.unit`

### Integration Tests
- **File:** `tests/integration/test_model_selection_cache_integration.py`
- **Count:** 20 tests
- **Markers:** `@pytest.mark.integration`, `@pytest.mark.preserve_collection`

---

## Detailed Test Coverage

### AC-7b.4.1: model_selection PostgreSQL Table

**Unit Tests (test_model_selection_cache.py):**
- [ ] TEST-AC-7b.4.1.1: ModelSelectionORM class exists
- [ ] TEST-AC-7b.4.1.2: ModelSelectionORM has correct table name
- [ ] TEST-AC-7b.4.1.3: ModelSelectionORM has all required columns
- [ ] TEST-AC-7b.4.1.4: variable_name column is unique
- [ ] TEST-AC-7b.4.1.5: expires_at column is not nullable

**Integration Tests (test_model_selection_cache_integration.py):**
- [ ] TEST-AC-7b.4.6.1: model_selection table exists after migration
- [ ] TEST-AC-7b.4.6.2: Table has correct columns
- [ ] TEST-AC-7b.4.6.3: idx_model_selection_variable index exists
- [ ] TEST-AC-7b.4.6.4: idx_model_selection_expires index exists

### AC-7b.4.2: cache_model_selection()

**Unit Tests (Mocked):**
- [ ] TEST-AC-7b.4.2.1: cache_model_selection function exists
- [ ] TEST-AC-7b.4.2.2: cache_model_selection accepts ModelSelectionResult
- [ ] TEST-AC-7b.4.2.3: cache_model_selection sets expires_at correctly

**Integration Tests:**
- [ ] TEST-AC-7b.4.2.4: cache_model_selection stores result in database
- [ ] TEST-AC-7b.4.2.5: cache_model_selection upserts (updates existing)
- [ ] TEST-AC-7b.4.2.6: regressor_list is stored as JSONB array
- [ ] TEST-AC-7b.4.2.7: candidate_results is stored as JSONB

### AC-7b.4.3: get_cached_model_selection()

**Unit Tests (Mocked):**
- [ ] TEST-AC-7b.4.3.1: CachedModelSelection dataclass exists
- [ ] TEST-AC-7b.4.3.2: CachedModelSelection has all required fields
- [ ] TEST-AC-7b.4.3.3: CachedModelSelection can be instantiated
- [ ] TEST-AC-7b.4.3.4: get_cached_model_selection function exists
- [ ] TEST-AC-7b.4.3.5: get_cached_model_selection returns None for missing
- [ ] TEST-AC-7b.4.3.6: get_cached_model_selection returns CachedModelSelection

**Integration Tests:**
- [ ] TEST-AC-7b.4.3.7: get_cached_model_selection returns CachedModelSelection
- [ ] TEST-AC-7b.4.3.8: get_cached_model_selection returns None for missing
- [ ] TEST-AC-7b.4.3.9: **PERFORMANCE** get_cached_model_selection completes in <100ms
- [ ] TEST-AC-7b.4.3.10: get_cached_model_selection returns expired entry with is_expired=True

### AC-7b.4.4: invalidate_model_selection()

**Unit Tests (Mocked):**
- [ ] TEST-AC-7b.4.4.1: invalidate_model_selection function exists
- [ ] TEST-AC-7b.4.4.2: invalidate_model_selection deletes single variable
- [ ] TEST-AC-7b.4.4.3: invalidate_model_selection(None) deletes all
- [ ] TEST-AC-7b.4.4.4: invalidate_model_selection returns 0 for missing

**Integration Tests:**
- [ ] TEST-AC-7b.4.4.5: invalidate_model_selection deletes single variable
- [ ] TEST-AC-7b.4.4.6: invalidate_model_selection(None) deletes all entries
- [ ] TEST-AC-7b.4.4.7: invalidate_model_selection returns 0 for nonexistent

### AC-7b.4.5: 7-day TTL with Automatic Expiration

**Unit Tests:**
- [ ] TEST-AC-7b.4.5.1: is_expired=False for entries within TTL
- [ ] TEST-AC-7b.4.5.2: is_expired=True for entries past TTL
- [ ] TEST-AC-7b.4.5.3: is_expired boundary condition at exact expiry time
- [ ] TEST-AC-7b.4.5.4: MODEL_SELECTION_TTL_DAYS constant exists
- [ ] TEST-AC-7b.4.5.5: MODEL_SELECTION_TTL_DAYS equals 7
- [ ] TEST-AC-7b.4.5.6: Calculate expires_at = selected_at + 7 days
- [ ] TEST-AC-7b.4.5.7: cleanup_expired_model_selections function exists
- [ ] TEST-AC-7b.4.5.8: cleanup_expired_model_selections removes expired entries (mocked)
- [ ] TEST-AC-7b.4.5.9: cleanup_expired_model_selections returns 0 when none expired (mocked)

**Integration Tests:**
- [ ] TEST-AC-7b.4.5.10: expires_at is set to selected_at + 7 days
- [ ] TEST-AC-7b.4.5.11: cleanup_expired_model_selections removes expired entries
- [ ] TEST-AC-7b.4.5.12: cleanup_expired_model_selections returns 0 when none expired

### AC-7b.4.6: Migration Script (Idempotent)

**Integration Tests:**
- [ ] TEST-AC-7b.4.6.1: model_selection table exists after migration
- [ ] TEST-AC-7b.4.6.2: Table has correct columns
- [ ] TEST-AC-7b.4.6.3: idx_model_selection_variable index exists
- [ ] TEST-AC-7b.4.6.4: idx_model_selection_expires index exists
- [ ] TEST-AC-7b.4.6.5: Migration can run multiple times without error

---

## Performance Test Summary

| Operation | Target Time | Test ID |
|-----------|-------------|---------|
| get_cached_model_selection() | <100ms | TEST-AC-7b.4.3.9 |
| cache_model_selection() | <500ms | test_cache_performance_under_500ms |
| invalidate_model_selection() | <200ms | test_invalidate_performance_under_200ms |
| cleanup_expired_model_selections() | <1s | test_cleanup_performance_under_1s |

---

## Implementation Artifacts Required

### Files to Create

1. **Migration Script:** `migrations/006_add_model_selection.sql`
   ```sql
   CREATE TABLE IF NOT EXISTS model_selection (
       id SERIAL PRIMARY KEY,
       variable_name VARCHAR(100) NOT NULL UNIQUE,
       best_model VARCHAR(50) NOT NULL,
       best_mape NUMERIC(8,4) NOT NULL,
       best_mase NUMERIC(8,4),
       use_regressors BOOLEAN DEFAULT FALSE,
       regressor_list JSONB,
       candidate_results JSONB,
       data_characteristics JSONB,
       selected_at TIMESTAMP DEFAULT NOW(),
       expires_at TIMESTAMP NOT NULL
   );

   CREATE INDEX IF NOT EXISTS idx_model_selection_variable ON model_selection(variable_name);
   CREATE INDEX IF NOT EXISTS idx_model_selection_expires ON model_selection(expires_at);
   ```

### Files to Modify

1. **ORM Models:** `raglite/external_data/orm_models.py`
   - Add `ModelSelectionORM` class

2. **Storage Functions:** `raglite/external_data/storage.py`
   - Add `MODEL_SELECTION_TTL_DAYS = 7` constant
   - Add `CachedModelSelection` dataclass
   - Add `cache_model_selection()` async function
   - Add `get_cached_model_selection()` async function
   - Add `invalidate_model_selection()` async function
   - Add `cleanup_expired_model_selections()` async function

---

## Run Commands

```bash
# Run unit tests (expected to FAIL in RED phase)
uv run pytest tests/unit/test_model_selection_cache.py -v

# Run integration tests (expected to FAIL in RED phase)
APP_ENV=test uv run pytest tests/integration/test_model_selection_cache_integration.py -v

# Run performance tests only
uv run pytest tests/integration/test_model_selection_cache_integration.py -v -k "performance"

# Run all tests for this story
uv run pytest tests/unit/test_model_selection_cache.py tests/integration/test_model_selection_cache_integration.py -v
```

---

## TDD Workflow Status

- [x] **RED Phase:** Acceptance tests created and expected to fail
- [ ] **GREEN Phase:** Implementation complete, all tests passing
- [ ] **REFACTOR Phase:** Code cleaned up, edge cases handled

---

## Notes

1. Tests are designed to fail initially because the implementation does not exist
2. Unit tests use mocking to avoid database dependencies
3. Integration tests require test PostgreSQL (port 5433) with raglite_ci credentials
4. Performance tests have explicit timing requirements from the story spec
5. Migration must be idempotent (use `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`)
