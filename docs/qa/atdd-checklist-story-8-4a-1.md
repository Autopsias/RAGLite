# ATDD Checklist - Story 8.4a-1: Critical Priority Unit Test File Splitting

> **Phase:** TDD RED - All tests FAIL until implementation is complete
> **Created:** 2025-12-27
> **Story:** 8.4a-1 (Micro-story of 8.4a)
> **Epic:** 8 - Technical Debt Reduction

## Target Files

| File | Original LOC | Target Directory | Status |
|------|-------------|------------------|--------|
| `tests/unit/test_ingestion.py` | 1,817 | `tests/unit/ingestion/` | [ ] Pending |
| `tests/unit/test_model_selection_job.py` | 1,217 | `tests/unit/forecasting/model_selection/` | [ ] Pending |

**Total:** 3,034 LOC to refactor into <500 LOC modules

## Baseline Captured

| Metric | Value | Command |
|--------|-------|---------|
| Test Count (both files) | 97 | `pytest tests/unit/test_ingestion.py tests/unit/test_model_selection_job.py --collect-only -q` |
| test_ingestion.py LOC | 1,817 | `wc -l tests/unit/test_ingestion.py` |
| test_model_selection_job.py LOC | 1,217 | `wc -l tests/unit/test_model_selection_job.py` |
| Coverage Minimum | 80% | CI requirement |

## ATDD Test Files

All tests located in: `tests/atdd/story_8_4a_1/`

### AC-8.4a-1.1: Both Files Split to <500 LOC Each

| Test ID | Description | Priority | Status |
|---------|-------------|----------|--------|
| TEST-AC-8.4a-1.1.1 | Original test_ingestion.py removed or reduced to shim | P0 | [ ] RED |
| TEST-AC-8.4a-1.1.2 | Original test_model_selection_job.py removed or reduced | P0 | [ ] RED |
| TEST-AC-8.4a-1.1.3 | Ingestion tests directory created with test files | P0 | [ ] RED |
| TEST-AC-8.4a-1.1.4 | Model selection tests directory created | P0 | [ ] RED |
| TEST-AC-8.4a-1.1.5 | All ingestion split files under 500 LOC | P0 | [ ] RED |
| TEST-AC-8.4a-1.1.6 | All model_selection split files under 500 LOC | P0 | [ ] RED |

**Test File:** `test_ac1_file_splitting.py`

### AC-8.4a-1.2: Test Count Unchanged or Increased

| Test ID | Description | Priority | Status |
|---------|-------------|----------|--------|
| TEST-AC-8.4a-1.2.1 | Ingestion tests count preserved (>= 55) | P0 | [ ] RED |
| TEST-AC-8.4a-1.2.2 | Model selection tests count preserved (>= 36) | P0 | [ ] RED |
| TEST-AC-8.4a-1.2.3 | Combined test count meets baseline (>= 97) | P0 | [ ] RED |
| TEST-AC-8.4a-1.2.4 | No duplicate test names in split files | P0 | [ ] RED |

**Test File:** `test_ac2_test_count.py`

### AC-8.4a-1.3: Coverage Maintained at 80%+

| Test ID | Description | Priority | Status |
|---------|-------------|----------|--------|
| TEST-AC-8.4a-1.3.1 | Overall unit test coverage >= 80% | P0 | [ ] RED |
| TEST-AC-8.4a-1.3.2 | Ingestion module coverage adequate (>= 70%) | P0 | [ ] RED |
| TEST-AC-8.4a-1.3.3 | Forecasting module coverage adequate (>= 60%) | P0 | [ ] RED |

**Test File:** `test_ac3_coverage.py`

### AC-8.4a-1.4: All Unit Tests Pass

| Test ID | Description | Priority | Status |
|---------|-------------|----------|--------|
| TEST-AC-8.4a-1.4.1 | All ingestion tests pass | P0 | [ ] RED |
| TEST-AC-8.4a-1.4.2 | All model selection tests pass | P0 | [ ] RED |
| TEST-AC-8.4a-1.4.3 | No import errors in split test files | P0 | [ ] RED |
| TEST-AC-8.4a-1.4.4 | No fixture issues in split test files | P0 | [ ] RED |

**Test File:** `test_ac4_tests_pass.py`

### AC-8.4a-1.5: All Resulting Files <500 LOC Verified

| Test ID | Description | Priority | Status |
|---------|-------------|----------|--------|
| TEST-AC-8.4a-1.5.1 | check_file_sizes.py passes for all files | P0 | [ ] RED |
| TEST-AC-8.4a-1.5.2 | No new exceptions for target files | P0 | [ ] RED |
| TEST-AC-8.4a-1.5.3 | Ingestion conftest.py under limit (300 LOC) | P0 | [ ] RED |
| TEST-AC-8.4a-1.5.4 | Model selection conftest.py under limit (300 LOC) | P0 | [ ] RED |
| TEST-AC-8.4a-1.5.5 | Max file in each directory under 500 LOC | P0 | [ ] RED |

**Test File:** `test_ac5_file_size_verification.py`

## Test Summary

| Category | Count | Priority |
|----------|-------|----------|
| AC1 Tests (File Splitting) | 6 | P0 |
| AC2 Tests (Test Count) | 4 | P0 |
| AC3 Tests (Coverage) | 3 | P0 |
| AC4 Tests (Tests Pass) | 4 | P0 |
| AC5 Tests (File Size Verification) | 5 | P0 |
| **Total ATDD Tests** | **22** | All P0 |

## Running ATDD Tests

```bash
# Run all ATDD tests for story 8.4a-1 (expect ALL to fail in RED phase)
uv run pytest tests/atdd/story_8_4a_1/ -v

# Run specific AC tests
uv run pytest tests/atdd/story_8_4a_1/test_ac1_file_splitting.py -v
uv run pytest tests/atdd/story_8_4a_1/test_ac2_test_count.py -v
uv run pytest tests/atdd/story_8_4a_1/test_ac3_coverage.py -v
uv run pytest tests/atdd/story_8_4a_1/test_ac4_tests_pass.py -v
uv run pytest tests/atdd/story_8_4a_1/test_ac5_file_size_verification.py -v

# Run with ATDD marker only
uv run pytest tests/atdd/story_8_4a_1/ -m atdd -v
```

## Expected RED Phase Results

All 22 tests should FAIL because:

1. **AC1:** Original files still exist at 1,817 and 1,217 LOC
2. **AC2:** Target directories don't exist yet, can't verify test count
3. **AC3:** Target directories don't exist, can't run coverage
4. **AC4:** Target directories don't exist, can't run tests
5. **AC5:** Target directories don't exist, file size checks fail

## Transition to GREEN Phase

After implementation, update this checklist:

1. [ ] All AC1 tests pass (files split)
2. [ ] All AC2 tests pass (test count preserved)
3. [ ] All AC3 tests pass (coverage >= 80%)
4. [ ] All AC4 tests pass (all tests pass)
5. [ ] All AC5 tests pass (file sizes verified)

## Related Documentation

- Story File: `docs/stories/8-4a-1-critical-unit-test-files.md`
- Parent Story: `docs/stories/8-4a-unit-test-file-consolidation.md`
- File Size Rules: `.claude/rules/file-size-limits.md`
- Story 8.1 Reference (proven patterns): `docs/stories/8-1-critical-forecasting-module-refactoring.md`
