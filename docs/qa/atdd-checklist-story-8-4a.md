# ATDD Checklist - Story 8.4a: Unit Test File Consolidation

**Story:** 8-4a-unit-test-file-consolidation
**Epic:** 8 - Technical Debt Reduction
**Status:** RED (Tests failing - implementation pending)
**Generated:** 2025-12-27

## Acceptance Criteria Coverage

| AC ID | Description | Test IDs | Status |
|-------|-------------|----------|--------|
| AC-8.4a.1 | All Unit Test Files Under 500 LOC | TEST-AC-8.4a.1.1 - TEST-AC-8.4a.1.6 | RED |
| AC-8.4a.2 | Test Count Unchanged or Increased | TEST-AC-8.4a.2.1 - TEST-AC-8.4a.2.4 | RED |
| AC-8.4a.3 | Coverage Maintained at 80%+ | TEST-AC-8.4a.3.1 - TEST-AC-8.4a.3.4 | RED |
| AC-8.4a.4 | All Unit Tests Pass | TEST-AC-8.4a.4.1 - TEST-AC-8.4a.4.5 | RED |

## Test Summary

| Metric | Value |
|--------|-------|
| Total Tests | 19 |
| Passed | 0 |
| Failed | 19 (Expected - TDD RED phase) |
| Skipped | 0 |
| Duration | TBD |

## Test File Location

`tests/atdd/story_8_4a/`

## Test ID Mapping

### AC-8.4a.1: All Unit Test Files Under 500 LOC

| Test ID | Test Method | Description | Priority |
|---------|-------------|-------------|----------|
| TEST-AC-8.4a.1.1 | `test_ac84a1_1_no_unit_test_files_exceed_500_loc` | Verify no unit test files exceed 500 LOC | [P0] |
| TEST-AC-8.4a.1.2 | `test_ac84a1_2_critical_unit_test_files_split` | Verify critical unit test files (>1000 LOC) are split | [P0] |
| TEST-AC-8.4a.1.3 | `test_ac84a1_3_severe_unit_test_files_split` | Verify severe priority files (750-1000 LOC) are split | [P0] |
| TEST-AC-8.4a.1.4 | `test_ac84a1_4_moderate_unit_test_files_split` | Verify moderate priority files (500-750 LOC) are split | [P0] |
| TEST-AC-8.4a.1.5 | `test_ac84a1_5_no_unit_test_file_exceptions` | Verify .file-size-exceptions has no unit test entries | [P0] |
| TEST-AC-8.4a.1.6 | `test_ac84a1_6_total_unit_test_file_count` | Verify total exceeding files is 0 | [P0] |

### AC-8.4a.2: Test Count Unchanged or Increased

| Test ID | Test Method | Description | Priority |
|---------|-------------|-------------|----------|
| TEST-AC-8.4a.2.1 | `test_ac84a2_1_unit_test_count_meets_baseline` | Verify unit test count >= 3151 baseline | [P0] |
| TEST-AC-8.4a.2.2 | `test_ac84a2_2_no_test_functions_removed` | Verify critical test functions still exist | [P0] |
| TEST-AC-8.4a.2.3 | `test_ac84a2_3_test_modules_importable` | Verify all test modules are importable | [P0] |
| TEST-AC-8.4a.2.4 | `test_ac84a2_4_subdirectory_conftest_files_valid` | Verify conftest.py files have valid syntax | [P0] |

### AC-8.4a.3: Coverage Maintained at 80%+

| Test ID | Test Method | Description | Priority |
|---------|-------------|-------------|----------|
| TEST-AC-8.4a.3.1 | `test_ac84a3_1_unit_test_coverage_above_80_percent` | Verify coverage >= 80% | [P0] |
| TEST-AC-8.4a.3.2 | `test_ac84a3_2_no_coverage_regression_in_refactored_modules` | Verify all key modules have test coverage | [P0] |
| TEST-AC-8.4a.3.3 | `test_ac84a3_3_fixture_coverage_maintained` | Verify subdirs with tests have __init__.py | [P0] |
| TEST-AC-8.4a.3.4 | `test_ac84a3_4_no_duplicate_fixtures` | Verify no duplicate fixture definitions | [P0] |

### AC-8.4a.4: All Unit Tests Pass

| Test ID | Test Method | Description | Priority |
|---------|-------------|-------------|----------|
| TEST-AC-8.4a.4.1 | `test_ac84a4_1_all_unit_tests_pass` | Verify all unit tests pass | [P0] |
| TEST-AC-8.4a.4.2 | `test_ac84a4_2_no_import_errors` | Verify no import errors during collection | [P0] |
| TEST-AC-8.4a.4.3 | `test_ac84a4_3_no_fixture_errors` | Verify no fixture resolution errors | [P0] |
| TEST-AC-8.4a.4.4 | `test_ac84a4_4_pytest_markers_valid` | Verify all pytest markers are valid | [P0] |
| TEST-AC-8.4a.4.5 | `test_ac84a4_5_test_isolation_maintained` | Verify test isolation (no cross-test imports) | [P0] |

## Baseline Values

| Metric | Baseline Value | Source |
|--------|----------------|--------|
| Unit Test Count | 3151 | `pytest tests/unit/ --collect-only -q` |
| Files Exceeding 500 LOC | 39 | Story 8.4a specification |
| Coverage Threshold | 80% | `.claude/rules/quality-gates.md` |

## Critical Files to Refactor

### Priority 1 - Critical (>1000 LOC)

| File | Current LOC | Target Split |
|------|-------------|--------------|
| test_ingestion.py | 1,817 | ingestion/ |
| test_timeseries_extract.py | 1,413 | timeseries/ |
| test_model_selection_job.py | 1,217 | model_selection/ |
| test_proactive_insights.py | 1,128 | insights/ |
| test_trend_analysis.py | 1,061 | trend/ |
| test_model_selection_cache.py | 1,012 | model_selection/ |

### Priority 2 - Severe (750-1000 LOC)

| File | Current LOC |
|------|-------------|
| test_strategic_recommendations.py | 949 |
| test_table_extraction.py | 921 |
| test_forecast_query_tool.py | 864 |
| test_parallel_ingestion.py | 858 |
| test_eurostat_indicators_edge_cases.py | 815 |
| test_anomaly_detection.py | 811 |
| test_housing_transactions.py | 767 |
| test_multi_metric_validation.py | 760 |
| test_model_selection_utils.py | 750 |

## Verification Commands

```bash
# Run ATDD tests for Story 8.4a (should all FAIL in RED phase)
uv run pytest tests/atdd/story_8_4a/ -v

# Run specific AC tests
uv run pytest tests/atdd/story_8_4a/test_ac1_unit_file_size.py -v
uv run pytest tests/atdd/story_8_4a/test_ac2_test_count.py -v
uv run pytest tests/atdd/story_8_4a/test_ac3_coverage.py -v
uv run pytest tests/atdd/story_8_4a/test_ac4_tests_pass.py -v

# Check file sizes
python scripts/check_file_sizes.py --verbose

# Collect unit test count
uv run pytest tests/unit/ --collect-only -q | tail -5

# Run unit tests with coverage
uv run pytest tests/unit/ --cov=raglite --cov-fail-under=80
```

## TDD RED Phase Validation

All 19 ATDD tests are expected to FAIL in the RED phase because:

1. **AC-8.4a.1 (File Size):** 39 unit test files exceed 500 LOC
2. **AC-8.4a.2 (Test Count):** Tests will pass once count >= baseline maintained
3. **AC-8.4a.3 (Coverage):** Depends on successful test execution
4. **AC-8.4a.4 (Tests Pass):** Depends on AC-8.4a.1-3 being resolved

## Transition to GREEN

To transition from RED to GREEN:

1. Split critical files (>1000 LOC) into subdirectories
2. Split severe files (750-1000 LOC)
3. Split moderate files (500-750 LOC)
4. Consolidate fixtures into conftest.py files
5. Verify test count >= baseline
6. Verify coverage >= 80%
7. Remove unit test entries from .file-size-exceptions

## Notes

- Story 8.4a is a sub-story of Story 8.4 (Test File Consolidation)
- Focus is specifically on `tests/unit/` directory
- Story 8.4b will cover integration tests
- Story 8.4c will cover e2e tests
- Follow patterns from Story 8.1 (forecasting module refactoring)
