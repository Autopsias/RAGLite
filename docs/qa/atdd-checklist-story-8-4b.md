# ATDD Checklist - Story 8.4b: Integration Test File Consolidation

**Story:** 8-4b-integration-test-file-consolidation
**Epic:** 8 - Technical Debt Reduction
**Status:** RED (Tests failing - implementation pending)
**Generated:** 2025-12-28
**Updated:** 2025-12-28 (Phase 3 ATDD tests generated)

## Acceptance Criteria Coverage

| AC ID | Description | Test IDs | Status |
|-------|-------------|----------|--------|
| AC-8.4b.1 | All Integration Test Files Under 500 LOC | TEST-AC-8.4b.1.1 - TEST-AC-8.4b.1.21 | RED |
| AC-8.4b.2 | Test Count Unchanged or Increased | TEST-AC-8.4b.2.1 - TEST-AC-8.4b.2.10 | RED |
| AC-8.4b.3 | Coverage Maintained at 80%+ | TEST-AC-8.4b.3.1 - TEST-AC-8.4b.3.7 | RED |
| AC-8.4b.4 | All Integration Tests Pass | TEST-AC-8.4b.4.1 - TEST-AC-8.4b.4.8 | RED |
| AC-8.4b.5 | Fixture Dependencies Preserved | TEST-AC-8.4b.5.1 - TEST-AC-8.4b.5.10 | RED |

## Test Summary

| Metric | Value |
|--------|-------|
| Total Tests | 56 |
| Passed | 0 |
| Failed | 56 (Expected - TDD RED phase) |
| Skipped | 0 |
| Duration | TBD |

## Test File Location

`tests/atdd/story_8_4b/`

## Pre-Implementation Baseline (Captured 2025-12-28)

| Metric | Value | Source |
|--------|-------|--------|
| **Test Count** | 282 integration tests | `pytest tests/integration/ --collect-only -q` |
| **Files Over 500 LOC** | 22 files | `python scripts/check_file_sizes.py --verbose` |
| **Coverage** | TBD (run `pytest tests/integration/ --cov=raglite`) |

### Current Files Exceeding 500 LOC (Top 15 to Refactor)

| Priority | File | LOC | Target Strategy |
|----------|------|-----|-----------------|
| Critical | test_forecast_query_integration.py | 1,233 | 3-way split (forecasting/) |
| Critical | test_ingestion_integration.py | 1,197 | 3-way split (ingestion/) |
| Critical | test_model_selection_cache_integration.py | 1,175 | 3-way split (model_selection/) |
| Severe | test_model_selection.py | 855 | 2-way split |
| Severe | test_story_6_23_final_validation.py | 837 | 2-way split |
| Severe | test_epic3_p0_scenarios.py | 780 | 2-way split |
| Severe | test_catboost_adaptive_weights.py | 740 | Fixture extraction |
| Severe | test_ecb_macroeconomic_integration.py | 698 | Fixture extraction |
| Severe | test_eurostat_api.py | 672 | Fixture extraction |
| Severe | test_fixed_chunking.py | 666 | Fixture extraction |
| Severe | test_epic6_accuracy_regression.py | 652 | Fixture extraction |
| Moderate | test_metadata_injection.py | 640 | Fixture extraction |
| Moderate | test_analytical_query_tool.py | 633 | Fixture extraction |
| Moderate | test_external_data_integration.py | 612 | Fixture extraction |
| Moderate | test_proactive_insights_integration.py | 605 | Fixture extraction |

---

## Test ID Mapping

### AC-8.4b.1: All Integration Test Files Under 500 LOC

| Test ID | Test Method | Description | Priority |
|---------|-------------|-------------|----------|
| TEST-AC-8.4b.1.1 | `test_ac_8_4b_1_1_forecast_query_integration_under_limit` | Verify test_forecast_query_integration.py (1233 LOC) split | [P0] |
| TEST-AC-8.4b.1.2 | `test_ac_8_4b_1_2_ingestion_integration_under_limit` | Verify test_ingestion_integration.py (1197 LOC) split | [P0] |
| TEST-AC-8.4b.1.3 | `test_ac_8_4b_1_3_model_selection_cache_integration_under_limit` | Verify test_model_selection_cache_integration.py (1175 LOC) split | [P0] |
| TEST-AC-8.4b.1.4 | `test_ac_8_4b_1_4_forecasting_subdirectory_created` | Verify forecasting/ subdirectory exists with proper structure | [P0] |
| TEST-AC-8.4b.1.5 | `test_ac_8_4b_1_5_ingestion_subdirectory_created` | Verify ingestion/ subdirectory exists with proper structure | [P0] |
| TEST-AC-8.4b.1.6 | `test_ac_8_4b_1_6_model_selection_subdirectory_created` | Verify model_selection/ subdirectory exists with proper structure | [P0] |
| TEST-AC-8.4b.1.7 | `test_ac_8_4b_1_7_model_selection_under_limit` | Verify test_model_selection.py (855 LOC) split or reduced | [P0] |
| TEST-AC-8.4b.1.8 | `test_ac_8_4b_1_8_story_6_23_final_validation_under_limit` | Verify test_story_6_23_final_validation.py (837 LOC) split | [P0] |
| TEST-AC-8.4b.1.9 | `test_ac_8_4b_1_9_epic3_p0_scenarios_under_limit` | Verify test_epic3_p0_scenarios.py (780 LOC) split | [P0] |
| TEST-AC-8.4b.1.10 | `test_ac_8_4b_1_10_catboost_adaptive_weights_under_limit` | Verify test_catboost_adaptive_weights.py (740 LOC) reduced | [P0] |
| TEST-AC-8.4b.1.11 | `test_ac_8_4b_1_11_ecb_macroeconomic_under_limit` | Verify test_ecb_macroeconomic_integration.py (698 LOC) reduced | [P0] |
| TEST-AC-8.4b.1.12 | `test_ac_8_4b_1_12_eurostat_api_under_limit` | Verify test_eurostat_api.py (672 LOC) reduced | [P0] |
| TEST-AC-8.4b.1.13 | `test_ac_8_4b_1_13_fixed_chunking_under_limit` | Verify test_fixed_chunking.py (666 LOC) reduced | [P0] |
| TEST-AC-8.4b.1.14 | `test_ac_8_4b_1_14_epic6_accuracy_regression_under_limit` | Verify test_epic6_accuracy_regression.py (652 LOC) reduced | [P0] |
| TEST-AC-8.4b.1.15 | `test_ac_8_4b_1_15_metadata_injection_under_limit` | Verify test_metadata_injection.py (640 LOC) reduced | [P0] |
| TEST-AC-8.4b.1.16 | `test_ac_8_4b_1_16_analytical_query_tool_under_limit` | Verify test_analytical_query_tool.py (633 LOC) reduced | [P0] |
| TEST-AC-8.4b.1.17 | `test_ac_8_4b_1_17_external_data_integration_under_limit` | Verify test_external_data_integration.py (612 LOC) reduced | [P0] |
| TEST-AC-8.4b.1.18 | `test_ac_8_4b_1_18_proactive_insights_integration_under_limit` | Verify test_proactive_insights_integration.py (605 LOC) reduced | [P0] |
| TEST-AC-8.4b.1.19 | `test_ac_8_4b_1_19_no_integration_files_exceed_limit` | Verify no integration test files exceed 500 LOC | [P0] |
| TEST-AC-8.4b.1.20 | `test_ac_8_4b_1_20_all_new_subdirs_have_conftest` | Verify all new subdirectories have conftest.py | [P0] |
| TEST-AC-8.4b.1.21 | `test_ac_8_4b_1_21_split_files_under_limit` | Verify all new split files are under 500 LOC | [P0] |

### AC-8.4b.2: Test Count Unchanged or Increased

| Test ID | Test Method | Description | Priority |
|---------|-------------|-------------|----------|
| TEST-AC-8.4b.2.1 | `test_ac_8_4b_2_1_test_count_meets_baseline` | Verify integration test count >= 282 baseline | [P0] |
| TEST-AC-8.4b.2.2 | `test_ac_8_4b_2_2_no_empty_test_files` | Verify no test files are empty | [P0] |
| TEST-AC-8.4b.2.3 | `test_ac_8_4b_2_3_all_test_modules_importable` | Verify all test modules are importable | [P0] |
| TEST-AC-8.4b.2.4 | `test_ac_8_4b_2_4_subdirectory_conftest_valid_syntax` | Verify conftest.py files have valid syntax | [P0] |
| TEST-AC-8.4b.2.5 | `test_ac_8_4b_2_5_forecasting_tests_exist` | Verify forecasting subdirectory contains expected files | [P0] |
| TEST-AC-8.4b.2.6 | `test_ac_8_4b_2_6_ingestion_tests_exist` | Verify ingestion subdirectory contains expected files | [P0] |
| TEST-AC-8.4b.2.7 | `test_ac_8_4b_2_7_model_selection_tests_exist` | Verify model selection subdirectory contains expected files | [P0] |
| TEST-AC-8.4b.2.8 | `test_ac_8_4b_2_8_forecast_query_tests_preserved` | Verify forecast query tests preserved in split files | [P1] |
| TEST-AC-8.4b.2.9 | `test_ac_8_4b_2_9_ingestion_tests_preserved` | Verify ingestion tests preserved in split files | [P1] |
| TEST-AC-8.4b.2.10 | `test_ac_8_4b_2_10_model_selection_tests_preserved` | Verify model selection tests preserved in split files | [P1] |

### AC-8.4b.3: Coverage Maintained at 80%+

| Test ID | Test Method | Description | Priority |
|---------|-------------|-------------|----------|
| TEST-AC-8.4b.3.1 | `test_ac_8_4b_3_1_coverage_above_80_percent` | Verify integration test coverage >= 80% | [P0] |
| TEST-AC-8.4b.3.2 | `test_ac_8_4b_3_2_no_coverage_regression_in_new_files` | Verify new split files have actual coverage | [P0] |
| TEST-AC-8.4b.3.3 | `test_ac_8_4b_3_3_test_coverage_includes_split_modules` | Verify split modules included in coverage | [P0] |
| TEST-AC-8.4b.3.4 | `test_ac_8_4b_3_4_no_duplicate_fixtures` | Verify no duplicate fixture definitions | [P0] |
| TEST-AC-8.4b.3.5 | `test_ac_8_4b_3_5_forecasting_tests_have_assertions` | Verify forecasting tests have proper assertions | [P1] |
| TEST-AC-8.4b.3.6 | `test_ac_8_4b_3_6_ingestion_tests_have_assertions` | Verify ingestion tests have proper assertions | [P1] |
| TEST-AC-8.4b.3.7 | `test_ac_8_4b_3_7_model_selection_tests_have_assertions` | Verify model selection tests have proper assertions | [P1] |

### AC-8.4b.4: All Integration Tests Pass

| Test ID | Test Method | Description | Priority |
|---------|-------------|-------------|----------|
| TEST-AC-8.4b.4.1 | `test_ac_8_4b_4_1_all_integration_tests_pass` | Verify all integration tests pass | [P0] |
| TEST-AC-8.4b.4.2 | `test_ac_8_4b_4_2_no_import_errors` | Verify no import errors during collection | [P0] |
| TEST-AC-8.4b.4.3 | `test_ac_8_4b_4_3_no_fixture_errors` | Verify no fixture resolution errors | [P0] |
| TEST-AC-8.4b.4.4 | `test_ac_8_4b_4_4_pytest_markers_valid` | Verify all pytest markers are valid | [P0] |
| TEST-AC-8.4b.4.5 | `test_ac_8_4b_4_5_test_isolation_maintained` | Verify test isolation (no cross-test imports) | [P0] |
| TEST-AC-8.4b.4.6 | `test_ac_8_4b_4_6_forecasting_tests_pass` | Verify forecasting subdirectory tests pass | [P1] |
| TEST-AC-8.4b.4.7 | `test_ac_8_4b_4_7_ingestion_tests_pass` | Verify ingestion subdirectory tests pass | [P1] |
| TEST-AC-8.4b.4.8 | `test_ac_8_4b_4_8_model_selection_tests_pass` | Verify model selection subdirectory tests pass | [P1] |

### AC-8.4b.5: Fixture Dependencies Preserved

| Test ID | Test Method | Description | Priority |
|---------|-------------|-------------|----------|
| TEST-AC-8.4b.5.1 | `test_ac_8_4b_5_1_root_conftest_exists` | Verify root integration conftest.py exists | [P0] |
| TEST-AC-8.4b.5.2 | `test_ac_8_4b_5_2_fixtures_available` | Verify all fixtures available via pytest --fixtures | [P0] |
| TEST-AC-8.4b.5.3 | `test_ac_8_4b_5_3_no_circular_dependencies` | Verify no circular import dependencies | [P0] |
| TEST-AC-8.4b.5.4 | `test_ac_8_4b_5_4_session_fixtures_in_correct_scope` | Verify session fixtures in correct location | [P0] |
| TEST-AC-8.4b.5.5 | `test_ac_8_4b_5_5_subdirectory_conftest_structure` | Verify subdirectory conftest.py structure | [P0] |
| TEST-AC-8.4b.5.6 | `test_ac_8_4b_5_6_shared_fixtures_accessible` | Verify shared fixtures accessible from subdirs | [P0] |
| TEST-AC-8.4b.5.7 | `test_ac_8_4b_5_7_forecasting_fixtures_isolated` | Verify forecasting fixtures in conftest.py | [P1] |
| TEST-AC-8.4b.5.8 | `test_ac_8_4b_5_8_ingestion_fixtures_isolated` | Verify ingestion fixtures in conftest.py | [P1] |
| TEST-AC-8.4b.5.9 | `test_ac_8_4b_5_9_model_selection_fixtures_isolated` | Verify model selection fixtures in conftest.py | [P1] |
| TEST-AC-8.4b.5.10 | `test_ac_8_4b_5_10_no_fixture_duplication_across_modules` | Verify no fixture duplication between subdirs and root | [P1] |

---

## Test Files Summary

| File | Tests | Priority |
|------|-------|----------|
| `tests/atdd/story_8_4b/test_ac1_file_size_limits.py` | 21 | P0 |
| `tests/atdd/story_8_4b/test_ac2_test_count.py` | 10 | P0-P1 |
| `tests/atdd/story_8_4b/test_ac3_coverage.py` | 7 | P0-P1 |
| `tests/atdd/story_8_4b/test_ac4_tests_pass.py` | 8 | P0-P1 |
| `tests/atdd/story_8_4b/test_ac5_fixture_dependencies.py` | 10 | P0-P1 |
| **Total** | **56** | |

---

## Expected Directory Structure After Refactoring

```
tests/integration/
  conftest.py                           # Root fixtures (<100 LOC)
  fixtures/
    session_fixtures.py                 # Session-scoped fixtures
    ...
  forecasting/
    __init__.py
    conftest.py                         # Forecasting-specific fixtures
    test_forecast_query_types.py        # Query type tests (~350 LOC)
    test_forecast_workflows.py          # Workflow tests (~350 LOC)
    test_forecast_edge_cases.py         # Edge cases (~350 LOC)
  ingestion/
    __init__.py
    conftest.py                         # Ingestion-specific fixtures
    test_pdf_pipeline.py                # PDF tests (~350 LOC)
    test_excel_pipeline.py              # Excel tests (~300 LOC)
    test_ingestion_workflow.py          # Workflow tests (~300 LOC)
  model_selection/
    __init__.py
    conftest.py                         # Model selection fixtures
    test_cache_operations.py            # Cache tests (~350 LOC)
    test_cache_invalidation.py          # Invalidation tests (~300 LOC)
    test_selection_integration.py       # Integration tests (~300 LOC)
```

---

## Verification Commands

```bash
# Run ATDD tests for Story 8.4b (should all FAIL in RED phase)
uv run pytest tests/atdd/story_8_4b/ -v

# Run specific AC tests
uv run pytest tests/atdd/story_8_4b/test_ac1_file_size_limits.py -v
uv run pytest tests/atdd/story_8_4b/test_ac2_test_count.py -v
uv run pytest tests/atdd/story_8_4b/test_ac3_coverage.py -v
uv run pytest tests/atdd/story_8_4b/test_ac4_tests_pass.py -v
uv run pytest tests/atdd/story_8_4b/test_ac5_fixture_dependencies.py -v

# Check file sizes
python scripts/check_file_sizes.py --verbose | grep tests/integration/

# Collect integration test count
uv run pytest tests/integration/ --collect-only -q | tail -5

# Run integration tests with coverage
uv run pytest tests/integration/ --cov=raglite --cov-fail-under=80
```

---

## TDD RED Phase Validation

All 56 ATDD tests are expected to FAIL in the RED phase because:

1. **AC-8.4b.1 (File Size):** 15+ integration test files exceed 500 LOC
2. **AC-8.4b.2 (Test Count):** Expected subdirectory structure not yet created
3. **AC-8.4b.3 (Coverage):** Depends on successful test execution
4. **AC-8.4b.4 (Tests Pass):** Depends on AC-8.4b.1-3 being resolved
5. **AC-8.4b.5 (Fixtures):** New conftest.py files not yet created

---

## Transition to GREEN

To transition from RED to GREEN:

1. Create subdirectory structure (forecasting/, ingestion/, model_selection/)
2. Split critical files (>900 LOC) into 3 files each
3. Split severe files (550-900 LOC) into 2 files or extract fixtures
4. Extract fixtures from moderate files (500-550 LOC)
5. Create conftest.py in each new subdirectory
6. Verify test count >= baseline (282)
7. Verify coverage >= 80%
8. Remove integration test entries from .file-size-exceptions

---

## Definition of Done Checklist

- [ ] All ATDD tests passing (GREEN)
- [ ] AC-8.4b.1: 0 integration test files > 500 LOC
- [ ] AC-8.4b.2: Test count >= 282
- [ ] AC-8.4b.3: Coverage >= 80%
- [ ] AC-8.4b.4: All integration tests pass
- [ ] AC-8.4b.5: All fixtures accessible from new locations
- [ ] `.file-size-exceptions` updated (entries removed)
- [ ] All CI checks passing

---

## Notes

- Story 8.4b is a sub-story of Story 8.4 (Test File Consolidation)
- Focus is specifically on `tests/integration/` directory
- Story 8.4a (unit tests) patterns should be followed
- Story 8.4c will cover ATDD/E2E tests
- Integration tests have more complex fixture dependencies (Docker containers)
- Session-scoped fixtures must be preserved in fixtures/session_fixtures.py
