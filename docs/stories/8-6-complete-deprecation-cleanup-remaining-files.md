# Story 8.6: Complete Deprecation Cleanup (Remaining Files)

## Overview

**Epic:** 8 - Technical Debt Reduction
**Story Key:** 8-6
**Priority:** P2 (Medium)
**Effort:** 3-5 hours
**Status:** Ready for Dev

## Problem Statement

Story 8.5 migrated 9 test files from deprecated `historical_data` parameter to the new `metric` parameter. However, ATDD regression tests discovered **125 additional deprecated usages** across files outside the original scope. These remaining deprecations must be eliminated to:
1. Achieve zero deprecation warnings project-wide
2. Prepare for removal of deprecated API in Epic 7
3. Pass Story 8.5's ATDD quality gates

## Scope

### In Scope

1. **Remaining `historical_data` parameter deprecations** (125 occurrences)
   - Files discovered by ATDD tests:
     - `tests/unit/mcp/test_model_selection_mcp.py` (2 occurrences at lines 479, 507)
     - `tests/unit/forecasting/test_catboost_weights.py` (1 occurrence at line 415)
     - `tests/unit/forecasting/test_ensemble_api.py` (2 occurrences at lines 137, 183)
     - `tests/unit/forecasting/test_forecast_query_models.py` (1 occurrence at line 189)
     - `tests/integration/test_epic6_extended.py` (8 occurrences at lines 152, 198, 239, 249, 309, 372, 380, 388)
     - `tests/integration/test_epic6_core.py` (multiple occurrences - to be counted)
     - `tests/integration/test_catboost_adaptive_weights.py` (6 occurrences at lines 416, 443, 470, 506, 536, 568)
     - Additional files to be discovered via grep

### Out of Scope

- Production code changes (test-only migration)
- External library deprecations
- Files already migrated in Story 8.5

## Acceptance Criteria

### AC1: Complete historical_data Migration
**ID:** AC-8.6-1

**Given** test files using the deprecated `historical_data` parameter in `generate_forecast()` calls (125 occurrences across multiple files)
**When** all remaining files are updated to use the new `metric`-based API with mocked PostgreSQL data fetch
**Then** zero deprecated `historical_data` parameter usage remains in the codebase
**And** verification command `grep -r "historical_data=" tests/ | grep -v "__pycache__" | grep "generate_forecast" | wc -l` returns 0

### AC2: ATDD Regression Tests Pass
**ID:** AC-8.6-2

**Given** Story 8.5 ATDD tests that validate zero deprecation warnings
**When** all migrations from AC-8.6-1 are complete
**Then** `test_ac_8_5_4_2_historical_data_warnings_count_zero` passes (currently FAILING)
**And** `test_p1_no_new_historical_data_usage_in_new_tests` passes (currently FAILING)

### AC3: Test Behavior Preservation
**ID:** AC-8.6-3

**Given** all test files modified during migration
**When** the full test suite executes
**Then** all 4,944+ tests maintain their pass/fail status (no new failures introduced)
**And** test coverage remains at or above current levels
**And** no test behavior changes (same assertions validate same conditions)

### AC4: Documentation Update
**ID:** AC-8.6-4

**Given** Story 8.5 documented the initial 9-file migration
**When** Story 8.6 migration completes
**Then** migration summary is documented showing total files migrated (9 from 8.5 + N from 8.6)
**And** final verification confirms zero `historical_data` parameter usage project-wide

## Tasks

### Task 1: Discover All Remaining Deprecated Usages
**Links to:** AC-8.6-1
**Effort:** 30 minutes

**Actions:**
1. Run comprehensive grep: `grep -rn "historical_data=" tests/ --include="*.py" | grep "generate_forecast" | grep -v "__pycache__" > deprecated_files_8_6.txt`
2. Parse output to create file list with line numbers
3. Group by directory (unit/integration/validation/e2e)
4. Count total occurrences to verify 125+ matches ATDD findings

**Deliverables:**
- `deprecated_files_8_6.txt` - Complete inventory of remaining deprecated usages
- Categorized file list by test type

### Task 2: Migrate Unit Test Files
**Links to:** AC-8.6-1, AC-8.6-3
**Effort:** 1-2 hours

**Files:**
- `tests/unit/mcp/test_model_selection_mcp.py`
- `tests/unit/forecasting/test_catboost_weights.py`
- `tests/unit/forecasting/test_ensemble_api.py`
- `tests/unit/forecasting/test_forecast_query_models.py`

**Pattern (from Story 8.5):**
```python
# Before (deprecated):
result = await generate_forecast(metric="ebitda", historical_data=data, horizon=6)

# After (new API with mock):
with patch("raglite.forecasting.hybrid.ensemble.fetch_historical_data") as mock_fetch:
    mock_fetch.return_value = data
    result = await generate_forecast(metric="ebitda", horizon=6)
```

**Actions:**
1. Update each unit test file to use mocked data fetch pattern
2. Run incremental verification: `pytest <file> -v` after each file
3. Verify no new test failures introduced

**Deliverables:**
- 4+ updated unit test files using new API
- Per-file test verification reports

### Task 3: Migrate Integration Test Files
**Links to:** AC-8.6-1, AC-8.6-3
**Effort:** 1.5-2.5 hours

**Files:**
- `tests/integration/test_epic6_extended.py` (8 occurrences)
- `tests/integration/test_epic6_core.py` (multiple occurrences)
- `tests/integration/test_catboost_adaptive_weights.py` (6 occurrences)
- Additional integration files from Task 1 discovery

**Actions:**
1. Update each integration test file to use mocked data fetch pattern
2. Handle Epic 6-specific test fixtures (may require fixture updates in conftest.py)
3. Run incremental verification: `pytest <file> -v` after each file
4. Verify integration test isolation maintained

**Deliverables:**
- 3+ updated integration test files using new API
- Integration test verification reports
- Updated conftest.py fixtures (if needed)

### Task 4: Verify ATDD Tests Pass
**Links to:** AC-8.6-2
**Effort:** 30 minutes

**Actions:**
1. Run Story 8.5 ATDD tests: `pytest tests/atdd/test_story_8_5_deprecation_cleanup.py -v`
2. Verify `test_ac_8_5_4_2_historical_data_warnings_count_zero` shows 0 deprecated usages
3. Run edge case tests: `pytest tests/atdd/test_story_8_5_edge_cases.py -v`
4. Verify `test_p1_no_new_historical_data_usage_in_new_tests` passes
5. Confirm all 32 ATDD tests pass (currently 30/32)

**Deliverables:**
- ATDD test run report showing 32/32 passing
- Screenshot or output of zero deprecation warnings

### Task 5: Final Verification
**Links to:** AC-8.6-3, AC-8.6-4
**Effort:** 30 minutes

**Actions:**
1. Run full test suite: `uv run pytest tests/ -v`
2. Verify total test count unchanged (4,944+ tests)
3. Verify no new failures introduced
4. Run deprecation check: `grep -r "historical_data=" tests/ | grep "generate_forecast" | wc -l` -> expect 0
5. Update migration documentation

**Deliverables:**
- Full test suite execution report
- Migration completion summary (total files: 9 from 8.5 + N from 8.6)
- Updated docs/sprint-artifacts/sprint-status.yaml

## Testing Requirements

### Test Execution Strategy
1. **Incremental validation:** Run tests after each file migration to catch regressions early
2. **ATDD gate:** Story 8.5 ATDD tests MUST pass before marking story complete
3. **Behavior preservation:** Verify same test assertions pass/fail before and after changes
4. **Isolation verification:** Ensure no cross-test dependencies introduced by mock changes

### Test Scope by Task
- **Task 2:** Unit test files only (fast feedback loop)
- **Task 3:** Integration test files (may require database fixtures)
- **Task 4:** ATDD tests (quality gate validation)
- **Task 5:** Full test suite (final verification)

### Expected Test Behavior
- **Before migration:** 125+ deprecation warnings from `historical_data` parameter
- **After migration:** 0 deprecation warnings from RAGLite code
- **Test count:** 4,944+ tests (unchanged)
- **Pass rate:** Same or improved (no new failures)

### Validation Commands
```bash
# Count remaining deprecated usages (expect 125 initially, 0 after completion)
grep -r "historical_data=" tests/ --include="*.py" | grep "generate_forecast" | wc -l

# Run ATDD quality gate tests
pytest tests/atdd/test_story_8_5_deprecation_cleanup.py::TestAC854FullSuiteCoverage::test_ac_8_5_4_2_historical_data_warnings_count_zero -v
pytest tests/atdd/test_story_8_5_edge_cases.py::TestDeprecationRegressionPrevention::test_p1_no_new_historical_data_usage_in_new_tests -v

# Verify full suite
uv run pytest tests/ -v --tb=short
```

## Dev Notes

### Architecture References
- **Story 8.5 Migration Pattern:** `docs/stories/8-5-deprecation-cleanup.md` (Technical Notes section)
- **Forecasting module:** `raglite/forecasting/hybrid/ensemble.py` (`generate_forecast` function)
- **Mock pattern:** Use `patch("raglite.forecasting.hybrid.ensemble.fetch_historical_data")` for data fetch mocks

### Migration Dependencies
- **Story 8.5 completion:** Pattern established and validated (COMPLETE)
- **ATDD tests:** Regression detection in place (`tests/atdd/test_story_8_5_*.py`)
- **Epic 6 test fixtures:** May need updates in `tests/integration/conftest.py` for Epic 6 tests

### Known Challenges
1. **Epic 6 test complexity:** Integration tests for multi-variate forecasting may have complex fixture dependencies
2. **Test count:** 125 occurrences across multiple files requires systematic approach
3. **Mock consistency:** Ensure all mocks return compatible data structures (TimeSeriesData vs pd.Series)

## Definition of Done

- [x] Story file created with complete acceptance criteria
- [ ] All 125+ deprecated `historical_data` usages eliminated
- [ ] Story 8.5 ATDD tests pass (32/32)
- [ ] Full test suite passes (4,944+ tests)
- [ ] Migration documentation updated

## References

- Story 8.5: Deprecation Warning Cleanup (initial 9 files)
- ATDD test failures: `test_ac_8_5_4_2_historical_data_warnings_count_zero`, `test_p1_no_new_historical_data_usage_in_new_tests`
- Epic 7: Planned removal of `historical_data` parameter (future work)
