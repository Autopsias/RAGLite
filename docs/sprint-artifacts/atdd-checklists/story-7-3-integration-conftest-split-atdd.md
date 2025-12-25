# ATDD Checklist: Story 7.3 - Split Integration conftest.py

**Story:** 7-3-split-integration-conftest
**Status:** RED (Tests Created - Failing)
**Test File:** `tests/atdd/test_story_7_3_integration_conftest_split.py`
**Tests Created:** 26
**Tests Passing:** 5 (pre-existing conditions met)
**Tests Failing:** 21 (expected - new structure not yet implemented)

---

## TDD Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| **RED** | COMPLETE | 26 acceptance tests created, 21 failing as expected |
| **GREEN** | PENDING | Implement refactoring to make tests pass |
| **REFACTOR** | PENDING | Code cleanup and optimization |

---

## Acceptance Criteria Test Mapping

### AC1: File Size Reduction (7 tests)

| Test | Status | Description |
|------|--------|-------------|
| `test_root_conftest_under_350_loc` | FAIL | Root conftest.py has 1,462 LOC (target: <350) |
| `test_session_state_module_under_500_loc` | FAIL | Module not created yet |
| `test_service_checking_module_under_500_loc` | FAIL | Module not created yet |
| `test_session_fixtures_module_under_500_loc` | FAIL | Module not created yet |
| `test_test_isolation_module_under_500_loc` | FAIL | Module not created yet |
| `test_module_fixtures_module_under_500_loc` | FAIL | Module not created yet |
| `test_helper_fixtures_module_under_500_loc` | FAIL | Module not created yet |

### AC2: New Module Structure (4 tests)

| Test | Status | Description |
|------|--------|-------------|
| `test_fixtures_directory_exists` | FAIL | fixtures/ directory not created |
| `test_fixtures_init_exists` | FAIL | __init__.py not created |
| `test_all_expected_modules_exist` | FAIL | 6 modules missing |
| `test_pytest_plugins_configured_in_root_conftest` | FAIL | pytest_plugins not configured |

### AC3: Functionality Preserved (3 tests)

| Test | Status | Description |
|------|--------|-------------|
| `test_fixtures_are_importable` | FAIL | Modules don't exist to import |
| `test_key_fixtures_defined` | FAIL | Fixtures not in expected locations |
| `test_restoration_helper_defined` | FAIL | _do_restoration not in test_isolation.py |

### AC4: Shared State Preserved (4 tests)

| Test | Status | Description |
|------|--------|-------------|
| `test_session_state_module_exists` | FAIL | session_state.py not created |
| `test_session_state_variables_defined` | FAIL | Variables not in dedicated module |
| `test_session_state_imported_by_dependent_modules` | FAIL | Imports not set up |
| `test_no_circular_imports` | FAIL | __init__.py doesn't exist |

### AC5: CI Compatibility (4 tests)

| Test | Status | Description |
|------|--------|-------------|
| `test_pytestmark_preserved` | PASS | Already present in root conftest |
| `test_environment_setup_in_root_conftest` | PASS | Env vars already set correctly |
| `test_settings_reload_in_root_conftest` | PASS | Settings reload already present |
| `test_fixtures_valid_python_syntax` | PASS | Current file has valid syntax |

### AC6: Documentation (2 tests)

| Test | Status | Description |
|------|--------|-------------|
| `test_all_modules_have_docstrings` | FAIL | New modules not created |
| `test_root_conftest_has_docstring` | PASS | Docstring already present |

### Summary Validation (2 tests)

| Test | Status | Description |
|------|--------|-------------|
| `test_total_loc_reduction_achieved` | FAIL | fixtures/ directory missing |
| `test_all_original_content_distributed` | FAIL | Content not distributed yet |

---

## Implementation Checklist

### Task 1: Create Module Structure
- [ ] Create `tests/integration/fixtures/` directory
- [ ] Create `tests/integration/fixtures/__init__.py`
- [ ] Create `tests/integration/fixtures/session_state.py` (~30 LOC)

### Task 2: Extract Service Checking
- [ ] Create `tests/integration/fixtures/service_checking.py` (~80 LOC)
- [ ] Move: `check_service_available`, `get_service_availability`, `check_and_skip_if_unavailable`
- [ ] Move: `QDRANT_HOST`, `QDRANT_PORT`, `POSTGRES_HOST`, `POSTGRES_PORT`
- [ ] Move: `qdrant_available`, `postgres_available` globals

### Task 3: Extract Session Fixtures
- [ ] Create `tests/integration/fixtures/session_fixtures.py` (~350 LOC)
- [ ] Move: `ensure_test_database_schema`, `warmup_embedding_model`, `session_ingested_collection`
- [ ] Import session state from session_state.py

### Task 4: Extract Test Isolation
- [ ] Create `tests/integration/fixtures/test_isolation.py` (~280 LOC)
- [ ] Move: `_do_restoration`, `ensure_qdrant_test_isolation`
- [ ] Import session state from session_state.py

### Task 5: Extract Module Fixtures
- [ ] Create `tests/integration/fixtures/module_fixtures.py` (~250 LOC)
- [ ] Move: `ingested_160_page_pdf`, `ingested_excerpt_pdf`

### Task 6: Extract Helper Fixtures
- [ ] Create `tests/integration/fixtures/helper_fixtures.py` (~120 LOC)
- [ ] Move: `qdrant_with_sample_docs`, `mock_synthesis_agent`, `sample_ground_truth`

### Task 7: Update Root conftest.py
- [ ] Add pytest_plugins list referencing all fixture modules
- [ ] Remove extracted functions/fixtures
- [ ] Keep: env setup, Settings reload, pytestmark
- [ ] Verify <350 LOC

### Task 8: Final Validation
- [ ] All 26 ATDD tests pass
- [ ] All ~115 integration tests pass
- [ ] `pytest tests/integration/ --collect-only` shows same test count

---

## Commands for Validation

```bash
# Run ATDD tests (should all pass when complete)
pytest tests/atdd/test_story_7_3_integration_conftest_split.py -v

# Check file sizes after refactoring
wc -l tests/integration/conftest.py tests/integration/fixtures/*.py

# Verify fixture discovery
pytest tests/integration/ --fixtures | grep -E "^(ensure_|warmup_|session_|ingested_)"

# Verify test discovery unchanged
pytest tests/integration/ --collect-only -q | tail -5

# Run integration tests with existing data
pytest tests/integration/ --skip-ingestion -v
```

---

## Expected Final File Sizes

| File | Target LOC | Max LOC |
|------|------------|---------|
| `conftest.py` | ~300 | 350 |
| `session_state.py` | ~30 | 500 |
| `service_checking.py` | ~80 | 500 |
| `session_fixtures.py` | ~350 | 500 |
| `test_isolation.py` | ~280 | 500 |
| `module_fixtures.py` | ~250 | 500 |
| `helper_fixtures.py` | ~120 | 500 |

---

## References

- Story file: `docs/sprint-artifacts/stories/7-3-split-integration-conftest.md`
- Test file: `tests/atdd/test_story_7_3_integration_conftest_split.py`
- Original conftest: `tests/integration/conftest.py` (1,462 LOC)
