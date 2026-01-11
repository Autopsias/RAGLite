# ATDD Checklist - Story 8.4: Test File Consolidation

**Story:** 8.4 - Test File Consolidation
**Phase:** 3 (ATDD - TDD RED)
**Created:** 2025-12-27
**Status:** RED (All tests expected to fail - refactoring not yet implemented)

## Summary

This checklist tracks the ATDD tests for Story 8.4, which covers splitting 45+ test files that exceed the 500 LOC limit into smaller, more maintainable modules.

## Acceptance Criteria Mapping

| AC ID | Description | Test File | Test Count | Status |
|-------|-------------|-----------|------------|--------|
| AC-8.4.1 | All Test Files Under 500 LOC | `test_ac1_file_size_limit.py` | 6 | RED |
| AC-8.4.2 | Test Count Unchanged or Increased | `test_ac2_test_count.py` | 4 | RED |
| AC-8.4.3 | Coverage Maintained at 80%+ | `test_ac3_coverage.py` | 3 | RED |
| AC-8.4.4 | CI Pipeline Runs Successfully | `test_ac4_ci_pipeline.py` | 5 | RED |

**Total ATDD Tests:** 18

## Test Details

### AC-8.4.1: All Test Files Under 500 LOC (6 tests)

| Test ID | Description | Priority | Expected Failure Reason |
|---------|-------------|----------|-------------------------|
| TEST-AC-8.4.1.1 | No test files exceed 500 LOC | P0 | 70 test files currently exceed limit |
| TEST-AC-8.4.1.2 | Critical unit test files split | P0 | 6 critical files >1000 LOC exist |
| TEST-AC-8.4.1.3 | Critical integration test files split | P0 | 3 critical files >1000 LOC exist |
| TEST-AC-8.4.1.4 | Severe test files split | P0 | 8 severe files (750-1000 LOC) exist |
| TEST-AC-8.4.1.5 | Moderate test files split | P0 | 31+ moderate files exist |
| TEST-AC-8.4.1.6 | No test file exceptions | P0 | May have test exceptions |

### AC-8.4.2: Test Count Unchanged or Increased (4 tests)

| Test ID | Description | Priority | Expected Failure Reason |
|---------|-------------|----------|-------------------------|
| TEST-AC-8.4.2.1 | Test count meets baseline | P0 | N/A (should pass if no tests lost) |
| TEST-AC-8.4.2.2 | No collection errors | P0 | May have collection errors from split |
| TEST-AC-8.4.2.3 | All test directories discoverable | P0 | New directories need __init__.py |
| TEST-AC-8.4.2.4 | No orphaned test files | P0 | New directories need proper structure |

### AC-8.4.3: Coverage Maintained at 80%+ (3 tests)

| Test ID | Description | Priority | Expected Failure Reason |
|---------|-------------|----------|-------------------------|
| TEST-AC-8.4.3.1 | Overall coverage at 80% | P0 | Should pass if tests run correctly |
| TEST-AC-8.4.3.2 | No critical module coverage regression | P0 | Should pass if tests organized correctly |
| TEST-AC-8.4.3.3 | Coverage report generates | P0 | Should pass if no import errors |

### AC-8.4.4: CI Pipeline Runs Successfully (5 tests)

| Test ID | Description | Priority | Expected Failure Reason |
|---------|-------------|----------|-------------------------|
| TEST-AC-8.4.4.1 | No import errors | P0 | Split may cause import issues |
| TEST-AC-8.4.4.2 | All fixtures resolve | P0 | Fixture extraction may break resolution |
| TEST-AC-8.4.4.3 | No fixture dependency cycles | P0 | Hierarchy changes may create cycles |
| TEST-AC-8.4.4.4 | Conftest hierarchy proper | P0 | New directories need conftest.py |
| TEST-AC-8.4.4.5 | Full test suite passes | P0 | Split tests must all pass |

## Test Files Location

```
tests/atdd/story_8_4/
  __init__.py
  conftest.py
  test_ac1_file_size_limit.py
  test_ac2_test_count.py
  test_ac3_coverage.py
  test_ac4_ci_pipeline.py
```

## Running ATDD Tests

```bash
# Run all Story 8.4 ATDD tests
uv run pytest tests/atdd/story_8_4/ -v

# Run specific AC tests
uv run pytest tests/atdd/story_8_4/test_ac1_file_size_limit.py -v
uv run pytest tests/atdd/story_8_4/test_ac2_test_count.py -v
uv run pytest tests/atdd/story_8_4/test_ac3_coverage.py -v
uv run pytest tests/atdd/story_8_4/test_ac4_ci_pipeline.py -v

# Run with ATDD marker
uv run pytest -m atdd tests/atdd/story_8_4/ -v
```

## Current State (Baseline)

### Files Exceeding 500 LOC (Sample)

| File | LOC | Priority |
|------|-----|----------|
| tests/unit/test_ingestion.py | 1,817 | Critical |
| tests/integration/test_forecast_query_integration.py | 1,233 | Critical |
| tests/unit/test_model_selection_job.py | 1,217 | Critical |
| tests/integration/test_ingestion_integration.py | 1,197 | Critical |
| tests/integration/test_model_selection_cache_integration.py | 1,175 | Critical |
| tests/unit/test_proactive_insights.py | 1,128 | Severe |
| tests/unit/test_trend_analysis.py | 1,061 | Severe |
| tests/unit/test_model_selection_cache.py | 986 | Severe |
| ... | ... | ... |

**Total files exceeding 500 LOC:** 67
**Total excess LOC:** 14,329 LOC over limit
**Baseline test count:** ~3,482 tests

### Test Results Summary (RED Phase)

**Run Date:** 2025-12-27
**Tests Run:** 16 (excluding 2 slow tests)
**Passed:** 5 | **Failed:** 11

| Test ID | Result | Failure Reason |
|---------|--------|----------------|
| TEST-AC-8.4.1.1 | FAILED | 67 test files exceeding 500 LOC |
| TEST-AC-8.4.1.2 | FAILED | 5 critical unit test files >500 LOC |
| TEST-AC-8.4.1.3 | FAILED | 3 critical integration test files >500 LOC |
| TEST-AC-8.4.1.4 | FAILED | 8 severe priority test files >500 LOC |
| TEST-AC-8.4.1.5 | FAILED | Moderate priority files exceed limit |
| TEST-AC-8.4.1.6 | PASSED | No test file exceptions currently |
| TEST-AC-8.4.2.1 | PASSED | Test count exceeds baseline |
| TEST-AC-8.4.2.2 | FAILED | 2 collection errors present |
| TEST-AC-8.4.2.3 | FAILED | Missing __init__.py in some directories |
| TEST-AC-8.4.2.4 | FAILED | Orphaned test files found |
| TEST-AC-8.4.3.2 | FAILED | Critical module coverage issues |
| TEST-AC-8.4.3.3 | PASSED | Coverage report generates |
| TEST-AC-8.4.4.1 | FAILED | 2 collection errors during pytest collect |
| TEST-AC-8.4.4.2 | PASSED | No fixture resolution errors |
| TEST-AC-8.4.4.3 | PASSED | No fixture dependency cycles |
| TEST-AC-8.4.4.4 | FAILED | Missing conftest.py in unit/ and unit/ingestion/ |

## TDD Cycle Tracking

### Phase 3: RED (Current)
- [x] All ATDD tests written
- [x] All tests expected to FAIL
- [x] Checklist created

### Phase 4: GREEN (Pending)
- [ ] Implement Task 1: Baseline Capture
- [ ] Implement Task 2: Split Critical Unit Test Files
- [ ] Implement Task 3: Split Critical Integration Test Files
- [ ] Implement Task 4: Split Severe Priority Files
- [ ] Implement Task 5: Split Moderate Priority Files
- [ ] Implement Task 6: Fixture Consolidation
- [ ] Implement Task 7: Update .file-size-exceptions
- [ ] Implement Task 8: Final Validation

### Phase 5: REFACTOR (Pending)
- [ ] Review fixture organization
- [ ] Optimize conftest hierarchy
- [ ] Remove redundant fixtures

## Definition of Done

- [ ] All 18 ATDD tests pass (GREEN)
- [ ] All 45+ test files < 500 LOC
- [ ] Test count >= 3,482 (baseline)
- [ ] Coverage >= 80%
- [ ] CI pipeline passes
- [ ] No fixture resolution errors
- [ ] .file-size-exceptions has 0 test entries
