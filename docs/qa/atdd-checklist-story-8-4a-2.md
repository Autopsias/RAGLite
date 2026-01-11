# ATDD Checklist - Epic 8, Story 8.4a-2: Severe Priority Unit Test File Splitting

**Date:** 2025-12-27
**Author:** TEA Agent (Ricardo)
**Primary Test Level:** Unit (Python pytest)

---

## Story Summary

Split 5 severe priority unit test files (750-1000 LOC) into smaller modules under 500 LOC each to improve AI tool comprehension and test maintenance.

**As a** developer
**I want** the 5 severe priority unit test files split into modules under 500 LOC each
**So that** AI tools can comprehend the full test context and test maintenance is improved

---

## Acceptance Criteria

1. **AC-8.4a-2.1:** All 5 files split to <500 LOC each
2. **AC-8.4a-2.2:** Test count unchanged or increased (baseline: 271 tests)
3. **AC-8.4a-2.3:** Coverage maintained at 80%+
4. **AC-8.4a-2.4:** All unit tests pass
5. **AC-8.4a-2.5:** All resulting files <500 LOC verified by check_file_sizes.py

---

## Failing Tests Created (RED Phase)

### Unit Tests (14 tests)

**File:** `tests/atdd/test_story_8_4a_2_severe_files.py` (488 lines)

#### AC-8.4a-2.1 Tests (5 tests)

| Test ID | Test Name | Status | Failure Reason |
|---------|-----------|--------|----------------|
| TEST-AC-8.4a-2.1.1 | `test_proactive_insights_removed_or_reduced` | RED | File has 1,128 LOC (expected <=500) |
| TEST-AC-8.4a-2.1.2 | `test_trend_analysis_removed_or_reduced` | RED | File has 1,061 LOC (expected <=500) |
| TEST-AC-8.4a-2.1.3 | `test_model_selection_cache_removed_or_reduced` | RED | File has 986 LOC (expected <=500) |
| TEST-AC-8.4a-2.1.4 | `test_strategic_recommendations_removed_or_reduced` | RED | File has 949 LOC (expected <=500) |
| TEST-AC-8.4a-2.1.5 | `test_table_extraction_removed_or_reduced` | RED | File has 923 LOC (expected <=500) |

#### AC-8.4a-2.2 Tests (1 test)

| Test ID | Test Name | Status | Failure Reason |
|---------|-----------|--------|----------------|
| TEST-AC-8.4a-2.2.1 | `test_total_test_count_preserved` | RED | Original files still exist in oversized form |

#### AC-8.4a-2.3 Tests (1 test)

| Test ID | Test Name | Status | Failure Reason |
|---------|-----------|--------|----------------|
| TEST-AC-8.4a-2.3.1 | `test_coverage_above_80_percent` | RED | Coverage verification pending refactoring |

#### AC-8.4a-2.4 Tests (3 tests)

| Test ID | Test Name | Status | Failure Reason |
|---------|-----------|--------|----------------|
| TEST-AC-8.4a-2.4.1 | `test_insights_tests_pass` | RED | Only 1 test file exists (expected >=6) |
| TEST-AC-8.4a-2.4.2 | `test_model_selection_tests_pass` | RED | Cache test files not split yet |
| TEST-AC-8.4a-2.4.3 | `test_ingestion_tests_pass` | RED | Table test files not split yet |

#### AC-8.4a-2.5 Tests (4 tests)

| Test ID | Test Name | Status | Failure Reason |
|---------|-----------|--------|----------------|
| TEST-AC-8.4a-2.5.1 | `test_insights_files_under_500_loc` | RED | Expected >=6 test files after split |
| TEST-AC-8.4a-2.5.2 | `test_model_selection_files_under_500_loc` | RED | Cache test files not split |
| TEST-AC-8.4a-2.5.3 | `test_ingestion_files_under_500_loc` | RED | Table test files not split |
| TEST-AC-8.4a-2.5.4 | `test_check_file_sizes_script_passes` | PASS | Script runs (violations expected until refactoring) |

---

## Target File Structure

### 1. test_proactive_insights.py (1,128 LOC) -> tests/unit/insights/

```
tests/unit/insights/
  __init__.py
  conftest.py                      # Shared fixtures (mock metrics, insights data)
  test_insight_generation.py       # Core insight generation tests
  test_insight_types.py            # Tests by insight type (trend, anomaly, pattern)
  test_insight_formatting.py       # Output formatting and serialization tests
```

### 2. test_trend_analysis.py (1,061 LOC) -> tests/unit/insights/

```
tests/unit/insights/
  test_trend_detection.py          # Trend detection algorithm tests
  test_trend_classification.py     # Trend type classification tests
  test_trend_metrics.py            # Trend metrics calculation tests
```

### 3. test_model_selection_cache.py (986 LOC) -> tests/unit/forecasting/model_selection/

```
tests/unit/forecasting/model_selection/
  test_cache_storage.py            # Cache storage and retrieval tests
  test_cache_invalidation.py       # Cache invalidation and refresh tests
  test_cache_integration.py        # Integration with model selection tests
```

### 4. test_strategic_recommendations.py (949 LOC) -> tests/unit/insights/

```
tests/unit/insights/
  test_recommendation_engine.py    # Recommendation generation tests
  test_recommendation_ranking.py   # Ranking and prioritization tests
```

### 5. test_table_extraction.py (923 LOC) -> tests/unit/ingestion/

```
tests/unit/ingestion/
  test_table_detection.py          # Table detection tests
  test_table_parsing.py            # Table parsing and structure tests
```

---

## Baseline Metrics

| Metric | Value | Source |
|--------|-------|--------|
| Total LOC | 5,047 | `wc -l` on 5 files |
| Test count | 271 | `pytest --collect-only` |
| Coverage | 80%+ | `pytest --cov=raglite` |

---

## Implementation Checklist

### Task 1: Baseline Capture [AC-8.4a-2.2, AC-8.4a-2.3, AC-8.4a-2.4]

- [ ] Record test count for 5 files (baseline: 271)
- [ ] Record coverage baseline: `pytest tests/unit/ --cov=raglite`
- [ ] Document current LOC for each file
- [ ] Check if any target directories already exist from Story 8.4a-1

### Task 2: Split test_proactive_insights.py (1,128 LOC) [AC-8.4a-2.1]

- [ ] Create `tests/unit/insights/` directory structure (if not exists)
- [ ] Create `tests/unit/insights/conftest.py` with shared fixtures
- [ ] Split by test class/feature: generation, types, formatting
- [ ] Update imports in all new files
- [ ] Verify tests pass: `pytest tests/unit/insights/ -v`
- [ ] Delete or convert original file to shim
- [ ] Run ATDD test: `pytest tests/atdd/test_story_8_4a_2_severe_files.py::TestAC1FileSizeLimits::test_proactive_insights_removed_or_reduced`
- [ ] Test passes (green phase)

### Task 3: Split test_trend_analysis.py (1,061 LOC) [AC-8.4a-2.1]

- [ ] Determine target directory (insights/ or forecasting/)
- [ ] Split by functionality: detection, classification, metrics
- [ ] Update imports in all new files
- [ ] Verify tests pass
- [ ] Delete or convert original file to shim
- [ ] Run ATDD test: `pytest tests/atdd/test_story_8_4a_2_severe_files.py::TestAC1FileSizeLimits::test_trend_analysis_removed_or_reduced`
- [ ] Test passes (green phase)

### Task 4: Split test_model_selection_cache.py (986 LOC) [AC-8.4a-2.1]

- [ ] Extend `tests/unit/forecasting/model_selection/` (if exists from 8.4a-1)
- [ ] Split by functionality: storage, invalidation, integration
- [ ] Update imports in all new files
- [ ] Verify tests pass
- [ ] Delete or convert original file to shim
- [ ] Run ATDD test: `pytest tests/atdd/test_story_8_4a_2_severe_files.py::TestAC1FileSizeLimits::test_model_selection_cache_removed_or_reduced`
- [ ] Test passes (green phase)

### Task 5: Split test_strategic_recommendations.py (949 LOC) [AC-8.4a-2.1]

- [ ] Add to `tests/unit/insights/` directory
- [ ] Split by functionality: engine, ranking
- [ ] Update imports in all new files
- [ ] Verify tests pass
- [ ] Delete or convert original file to shim
- [ ] Run ATDD test: `pytest tests/atdd/test_story_8_4a_2_severe_files.py::TestAC1FileSizeLimits::test_strategic_recommendations_removed_or_reduced`
- [ ] Test passes (green phase)

### Task 6: Split test_table_extraction.py (923 LOC) [AC-8.4a-2.1]

- [ ] Add to `tests/unit/ingestion/` directory (if exists from 8.4a-1)
- [ ] Split by functionality: detection, parsing
- [ ] Update imports in all new files
- [ ] Verify tests pass
- [ ] Delete or convert original file to shim
- [ ] Run ATDD test: `pytest tests/atdd/test_story_8_4a_2_severe_files.py::TestAC1FileSizeLimits::test_table_extraction_removed_or_reduced`
- [ ] Test passes (green phase)

### Task 7: File Size Validation [AC-8.4a-2.5]

- [ ] Run `python scripts/check_file_sizes.py --verbose`
- [ ] Verify all new files under 500 LOC
- [ ] Update `.file-size-exceptions` if needed (remove old entries)
- [ ] Document any exceptions with justification
- [ ] Run ATDD tests: `pytest tests/atdd/test_story_8_4a_2_severe_files.py::TestAC5AllFilesUnder500LOC`

### Task 8: Final Validation (MANDATORY) [All ACs]

- [ ] Verify test count >= baseline (271): `pytest tests/unit/ --collect-only -q | tail -1`
- [ ] Run `pytest tests/unit/ -x` - all tests pass
- [ ] Run `pytest tests/unit/ --cov=raglite --cov-fail-under=80` - coverage maintained
- [ ] Run `python scripts/check_file_sizes.py` - all files pass
- [ ] Run ALL ATDD tests: `pytest tests/atdd/test_story_8_4a_2_severe_files.py -v`
- [ ] All 14 ATDD tests pass (green phase)
- [ ] Update sprint-status.yaml

---

## Running Tests

```bash
# Run all ATDD tests for this story (should all FAIL initially)
uv run pytest tests/atdd/test_story_8_4a_2_severe_files.py -v

# Run specific AC tests
uv run pytest tests/atdd/test_story_8_4a_2_severe_files.py::TestAC1FileSizeLimits -v
uv run pytest tests/atdd/test_story_8_4a_2_severe_files.py::TestAC2TestCountPreserved -v
uv run pytest tests/atdd/test_story_8_4a_2_severe_files.py::TestAC3CoverageMaintained -v
uv run pytest tests/atdd/test_story_8_4a_2_severe_files.py::TestAC4AllTestsPass -v
uv run pytest tests/atdd/test_story_8_4a_2_severe_files.py::TestAC5AllFilesUnder500LOC -v

# Run with verbose failure output
uv run pytest tests/atdd/test_story_8_4a_2_severe_files.py -v --tb=long

# Verify original file test counts
uv run pytest tests/unit/test_proactive_insights.py tests/unit/test_trend_analysis.py tests/unit/test_model_selection_cache.py tests/unit/test_strategic_recommendations.py tests/unit/test_table_extraction.py --collect-only -q | tail -1
```

---

## Red-Green-Refactor Workflow

### RED Phase (Complete)

**TEA Agent Responsibilities:**

- All 14 ATDD tests written and failing
- Test structure maps to acceptance criteria
- Clear failure messages guide implementation

**Verification:**

```
12 failed, 2 passed (expected - tests validate refactoring not done)
```

---

### GREEN Phase (DEV Team - Next Steps)

**DEV Agent Responsibilities:**

1. **Pick one file to split** from implementation checklist (start with smallest: test_table_extraction.py at 923 LOC)
2. **Read the tests** in original file to understand expected behavior
3. **Create target directory structure** (tests/unit/ingestion/ if not exists)
4. **Split tests by functionality** maintaining test isolation
5. **Run tests after each split** to verify no regressions
6. **Check ATDD test** to verify progress

**Key Principles:**

- One file at a time (don't try to split all at once)
- Maintain fixture dependencies (conftest.py properly organized)
- Run tests frequently (immediate feedback)
- Use implementation checklist as roadmap

---

### REFACTOR Phase (DEV Team - After All Tests Pass)

1. **Verify all 14 ATDD tests pass** (green phase complete)
2. **Consolidate shared fixtures** into appropriate conftest.py files
3. **Remove duplicate test utilities** (DRY principle)
4. **Verify no circular imports** in test modules
5. **Ensure tests still pass** after each cleanup

---

## Test Execution Evidence

### Initial Test Run (RED Phase Verification)

**Command:** `uv run pytest tests/atdd/test_story_8_4a_2_severe_files.py -v`

**Results:**

```
12 failed, 2 passed

FAILED tests/atdd/test_story_8_4a_2_severe_files.py::TestAC1FileSizeLimits::test_proactive_insights_removed_or_reduced
  - test_proactive_insights.py has 1128 LOC (expected <=500)

FAILED tests/atdd/test_story_8_4a_2_severe_files.py::TestAC1FileSizeLimits::test_trend_analysis_removed_or_reduced
  - test_trend_analysis.py has 1061 LOC (expected <=500)

FAILED tests/atdd/test_story_8_4a_2_severe_files.py::TestAC1FileSizeLimits::test_model_selection_cache_removed_or_reduced
  - test_model_selection_cache.py has 986 LOC (expected <=500)

FAILED tests/atdd/test_story_8_4a_2_severe_files.py::TestAC1FileSizeLimits::test_strategic_recommendations_removed_or_reduced
  - test_strategic_recommendations.py has 949 LOC (expected <=500)

FAILED tests/atdd/test_story_8_4a_2_severe_files.py::TestAC1FileSizeLimits::test_table_extraction_removed_or_reduced
  - test_table_extraction.py has 923 LOC (expected <=500)

FAILED tests/atdd/test_story_8_4a_2_severe_files.py::TestAC4AllTestsPass::test_insights_tests_pass
  - tests/unit/insights/ has 1 test files, expected at least 6

FAILED tests/atdd/test_story_8_4a_2_severe_files.py::TestAC4AllTestsPass::test_model_selection_tests_pass
  - Expected at least 2 cache test files in model_selection/

FAILED tests/atdd/test_story_8_4a_2_severe_files.py::TestAC4AllTestsPass::test_ingestion_tests_pass
  - Expected at least 2 table test files in ingestion/

FAILED tests/atdd/test_story_8_4a_2_severe_files.py::TestAC5AllFilesUnder500LOC::test_insights_files_under_500_loc
  - Expected at least 6 test files in insights/ after split

FAILED tests/atdd/test_story_8_4a_2_severe_files.py::TestAC5AllFilesUnder500LOC::test_model_selection_files_under_500_loc
  - Expected at least 2 cache test files

FAILED tests/atdd/test_story_8_4a_2_severe_files.py::TestAC5AllFilesUnder500LOC::test_ingestion_files_under_500_loc
  - Expected at least 2 table test files
```

**Summary:**

- Total tests: 14
- Passing: 2 (expected - validates infrastructure exists)
- Failing: 12 (expected - refactoring not complete)
- Status: RED phase verified

---

## Notes

- Story 8.4a-1 (critical priority files) may have created some of the target directories
- Fixture organization is critical - use conftest.py at appropriate scope
- Test isolation must be maintained - no shared state between test files
- Coverage must remain >= 80% throughout the refactoring

---

## Contact

**Questions or Issues?**

- Refer to story file: `docs/stories/8-4a-2-severe-unit-test-files.md`
- Check parent story: `docs/stories/8-4a-unit-test-file-consolidation.md`
- File size limits: `.claude/rules/file-size-limits.md`

---

**Generated by BMad TEA Agent** - 2025-12-27
