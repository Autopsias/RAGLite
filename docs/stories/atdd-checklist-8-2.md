# ATDD Checklist - Story 8.2: External Data Client Refactoring

## Story Summary
Split large external data files (storage.py, basegov.py, ecb.py, eurostat.py) into modules under 500 LOC each with a shared base class for common patterns.

## Test Status: RED (Pre-Refactoring)

All acceptance tests are designed to FAIL initially. They will PASS after refactoring is complete.

---

## Acceptance Criteria Test Mapping

### AC-8.2.1: All Production Files Under 500 LOC

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-AC-8.2.1-A | `test_ac_8_2_1_storage_converted_to_shim` | RED | storage.py should be < 100 LOC |
| TEST-AC-8.2.1-B | `test_ac_8_2_1_basegov_converted_to_shim` | RED | basegov.py should be < 100 LOC |
| TEST-AC-8.2.1-C | `test_ac_8_2_1_ecb_converted_to_shim` | RED | ecb.py should be < 100 LOC |
| TEST-AC-8.2.1-D | `test_ac_8_2_1_eurostat_converted_to_shim` | RED | eurostat.py should be < 100 LOC |
| TEST-AC-8.2.1-E | `test_ac_8_2_1_storage_package_exists` | RED | storage/ package with 6 modules |
| TEST-AC-8.2.1-F | `test_ac_8_2_1_basegov_package_exists` | RED | basegov/ package with 4 modules |
| TEST-AC-8.2.1-G | `test_ac_8_2_1_ecb_package_exists` | RED | ecb/ package with 5 modules |
| TEST-AC-8.2.1-H | `test_ac_8_2_1_eurostat_package_exists` | RED | eurostat/ package with 5 modules |
| TEST-AC-8.2.1-I | `test_ac_8_2_1_base_client_under_limit` | RED | base.py should be < 500 LOC |
| TEST-AC-8.2.1-J | `test_ac_8_2_1_storage_modules_under_limit` | RED | All storage/ modules < 500 LOC |
| TEST-AC-8.2.1-K | `test_ac_8_2_1_basegov_modules_under_limit` | RED | All basegov/ modules < 500 LOC |
| TEST-AC-8.2.1-L | `test_ac_8_2_1_ecb_modules_under_limit` | RED | All ecb/ modules < 500 LOC |
| TEST-AC-8.2.1-M | `test_ac_8_2_1_eurostat_modules_under_limit` | RED | All eurostat/ modules < 500 LOC |
| TEST-AC-8.2.1-N | `test_ac_8_2_1_no_new_exceptions_for_external_data` | GREEN | No exceptions needed |

**Current State:**
- `storage.py`: 1,633 LOC (target: < 100 as shim)
- `basegov.py`: 1,066 LOC (target: < 100 as shim)
- `ecb.py`: 1,033 LOC (target: < 100 as shim)
- `eurostat.py`: 957 LOC (target: < 100 as shim)

---

### AC-8.2.2: All Test Files Under 500 LOC

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-AC-8.2.2-A | `test_ac_8_2_2_external_data_test_files_exist` | GREEN | Test dir exists |
| TEST-AC-8.2.2-B | `test_ac_8_2_2_all_external_data_tests_under_limit` | GREEN | Current tests OK |
| TEST-AC-8.2.2-C | `test_ac_8_2_2_storage_test_modules_exist` | RED | New test structure |
| TEST-AC-8.2.2-D | `test_ac_8_2_2_basegov_test_modules_exist` | RED | New test structure |
| TEST-AC-8.2.2-E | `test_ac_8_2_2_ecb_test_modules_exist` | RED | New test structure |
| TEST-AC-8.2.2-F | `test_ac_8_2_2_eurostat_test_modules_exist` | RED | New test structure |
| TEST-AC-8.2.2-G | `test_ac_8_2_2_base_client_tests_exist` | RED | New test file |
| TEST-AC-8.2.2-H | `test_ac_8_2_2_conftest_files_exist` | RED | Shared fixtures |

---

### AC-8.2.3: Shared Base Class for Common Client Patterns

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-AC-8.2.3-A | `test_ac_8_2_3_base_client_file_exists` | RED | base.py file |
| TEST-AC-8.2.3-B | `test_ac_8_2_3_base_client_under_limit` | RED | < 500 LOC |
| TEST-AC-8.2.3-C | `test_ac_8_2_3_base_client_has_class` | RED | BaseExternalClient class |
| TEST-AC-8.2.3-D | `test_ac_8_2_3_base_has_retry_method` | RED | _fetch_with_retry method |
| TEST-AC-8.2.3-E | `test_ac_8_2_3_base_has_cache_init` | RED | Caching infrastructure |
| TEST-AC-8.2.3-F | `test_ac_8_2_3_base_has_error_handling` | RED | HTTP error handling |
| TEST-AC-8.2.3-G | `test_ac_8_2_3_base_has_logging` | RED | Logging patterns |
| TEST-AC-8.2.3-H | `test_ac_8_2_3_basegov_inherits_base` | RED | Inheritance check |
| TEST-AC-8.2.3-I | `test_ac_8_2_3_ecb_inherits_base` | RED | Inheritance check |
| TEST-AC-8.2.3-J | `test_ac_8_2_3_eurostat_inherits_base` | RED | Inheritance check |
| TEST-AC-8.2.3-K | `test_ac_8_2_3_no_duplicate_retry_in_clients` | RED | DRY validation |

---

### AC-8.2.4: Storage Operations Isolated and Testable

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-AC-8.2.4-A | `test_ac_8_2_4_storage_package_exists` | RED | Package structure |
| TEST-AC-8.2.4-B | `test_ac_8_2_4_core_module_exists` | RED | CRUD operations |
| TEST-AC-8.2.4-C | `test_ac_8_2_4_freshness_module_exists` | RED | Freshness tracking |
| TEST-AC-8.2.4-D | `test_ac_8_2_4_tier2_module_exists` | RED | Tier 2 storage |
| TEST-AC-8.2.4-E | `test_ac_8_2_4_model_weights_module_exists` | RED | Model weights |
| TEST-AC-8.2.4-F | `test_ac_8_2_4_model_selection_module_exists` | RED | Model selection |
| TEST-AC-8.2.4-G | `test_ac_8_2_4_constants_module_exists` | RED | Constants |
| TEST-AC-8.2.4-H | `test_ac_8_2_4_core_importable` | RED | Independent import |
| TEST-AC-8.2.4-I | `test_ac_8_2_4_freshness_importable` | RED | Independent import |
| TEST-AC-8.2.4-J | `test_ac_8_2_4_tier2_importable` | RED | Independent import |
| TEST-AC-8.2.4-K | `test_ac_8_2_4_model_weights_importable` | RED | Independent import |
| TEST-AC-8.2.4-L | `test_ac_8_2_4_model_selection_importable` | RED | Independent import |
| TEST-AC-8.2.4-M | `test_ac_8_2_4_constants_importable` | RED | Independent import |
| TEST-AC-8.2.4-N | `test_ac_8_2_4_no_circular_deps_in_storage` | RED | Circular dep check |
| TEST-AC-8.2.4-O | `test_ac_8_2_4_constants_has_no_internal_imports` | RED | Leaf node check |
| TEST-AC-8.2.4-P | `test_ac_8_2_4_core_has_crud_methods` | RED | CRUD methods exist |
| TEST-AC-8.2.4-Q | `test_ac_8_2_4_freshness_has_tracking_methods` | RED | Freshness methods |
| TEST-AC-8.2.4-R | `test_ac_8_2_4_tier2_has_tier2_methods` | RED | Tier 2 methods |
| TEST-AC-8.2.4-S | `test_ac_8_2_4_model_weights_has_weight_methods` | RED | Weight methods |
| TEST-AC-8.2.4-T | `test_ac_8_2_4_model_selection_has_cache_methods` | RED | Cache methods |

---

### AC-8.2.5: All Health Checks Pass

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-AC-8.2.5-A | `test_ac_8_2_5_health_test_file_exists` | GREEN | File exists |
| TEST-AC-8.2.5-B | `test_ac_8_2_5_health_test_has_test_classes` | GREEN | Classes exist |
| TEST-AC-8.2.5-C | `test_ac_8_2_5_basegov_client_importable` | GREEN | Current import works |
| TEST-AC-8.2.5-D | `test_ac_8_2_5_ecb_client_importable` | GREEN | Current import works |
| TEST-AC-8.2.5-E | `test_ac_8_2_5_eurostat_client_importable` | GREEN | Current import works |
| TEST-AC-8.2.5-F | `test_ac_8_2_5_storage_importable` | GREEN | Current import works |
| TEST-AC-8.2.5-G | `test_ac_8_2_5_basegov_instantiable` | GREEN | Current works |
| TEST-AC-8.2.5-H | `test_ac_8_2_5_ecb_instantiable` | GREEN | Current works |
| TEST-AC-8.2.5-I | `test_ac_8_2_5_eurostat_instantiable` | GREEN | Current works |
| TEST-AC-8.2.5-J | `test_ac_8_2_5_basegov_has_fetch_method` | GREEN | API methods exist |
| TEST-AC-8.2.5-K | `test_ac_8_2_5_ecb_has_fetch_methods` | GREEN | API methods exist |
| TEST-AC-8.2.5-L | `test_ac_8_2_5_eurostat_has_fetch_methods` | GREEN | API methods exist |

---

### AC-8.2.6: Test File Structure Mirrors Production

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-AC-8.2.6-A | `test_ac_8_2_6_storage_core_has_test` | RED | 1:1 mapping |
| TEST-AC-8.2.6-B | `test_ac_8_2_6_storage_freshness_has_test` | RED | 1:1 mapping |
| TEST-AC-8.2.6-C | `test_ac_8_2_6_storage_tier2_has_test` | RED | 1:1 mapping |
| TEST-AC-8.2.6-D | `test_ac_8_2_6_storage_model_weights_has_test` | RED | 1:1 mapping |
| TEST-AC-8.2.6-E | `test_ac_8_2_6_storage_model_selection_has_test` | RED | 1:1 mapping |
| TEST-AC-8.2.6-F | `test_ac_8_2_6_base_client_has_test` | RED | 1:1 mapping |
| TEST-AC-8.2.6-G | `test_ac_8_2_6_basegov_client_has_test` | RED | 1:1 mapping |
| TEST-AC-8.2.6-H | `test_ac_8_2_6_ecb_client_has_test` | RED | 1:1 mapping |
| TEST-AC-8.2.6-I | `test_ac_8_2_6_eurostat_client_has_test` | RED | 1:1 mapping |
| TEST-AC-8.2.6-J | `test_ac_8_2_6_storage_test_dir_exists` | RED | Dir structure |
| TEST-AC-8.2.6-K | `test_ac_8_2_6_clients_test_dir_exists` | RED | Dir structure |
| TEST-AC-8.2.6-L | `test_ac_8_2_6_basegov_test_dir_exists` | RED | Dir structure |
| TEST-AC-8.2.6-M | `test_ac_8_2_6_ecb_test_dir_exists` | RED | Dir structure |
| TEST-AC-8.2.6-N | `test_ac_8_2_6_eurostat_test_dir_exists` | RED | Dir structure |
| TEST-AC-8.2.6-O | `test_ac_8_2_6_external_data_conftest_exists` | GREEN | Already exists |
| TEST-AC-8.2.6-P | `test_ac_8_2_6_storage_conftest_exists` | RED | New conftest |
| TEST-AC-8.2.6-Q | `test_ac_8_2_6_clients_conftest_exists` | RED | New conftest |
| TEST-AC-8.2.6-R | `test_ac_8_2_6_conftest_provides_mock_fixtures` | GREEN | Already exists |
| TEST-AC-8.2.6-S | `test_ac_8_2_6_all_test_dirs_have_init` | RED | Package markers |
| TEST-AC-8.2.6-T | `test_ac_8_2_6_test_files_follow_naming` | GREEN | Current naming OK |

---

## Baseline Tests (Should PASS Before Refactoring)

| Test Name | Status | Purpose |
|-----------|--------|---------|
| `test_baseline_storage_exceeds_limit` | GREEN | Documents current state |
| `test_baseline_basegov_exceeds_limit` | GREEN | Documents current state |
| `test_baseline_ecb_exceeds_limit` | GREEN | Documents current state |
| `test_baseline_eurostat_exceeds_limit` | GREEN | Documents current state |
| `test_baseline_storage_package_does_not_exist` | GREEN | Package not created |
| `test_baseline_basegov_package_does_not_exist` | GREEN | Package not created |
| `test_baseline_ecb_package_does_not_exist` | GREEN | Package not created |
| `test_baseline_eurostat_package_does_not_exist` | GREEN | Package not created |
| `test_baseline_base_client_does_not_exist` | GREEN | Base class not created |
| `test_baseline_old_storage_import_works` | GREEN | Current import works |
| `test_baseline_old_basegov_import_works` | GREEN | Current import works |
| `test_baseline_old_ecb_import_works` | GREEN | Current import works |
| `test_baseline_old_eurostat_import_works` | GREEN | Current import works |

---

## Test File Location

```
tests/unit/story_8_2/
  __init__.py                            # Package marker (~10 LOC)
  conftest.py                            # Shared fixtures and utilities (~120 LOC)
  test_ac_8_2_1_production_files.py      # AC-8.2.1 tests (~220 LOC)
  test_ac_8_2_2_test_files.py            # AC-8.2.2 tests (~120 LOC)
  test_ac_8_2_3_base_class.py            # AC-8.2.3 tests (~200 LOC)
  test_ac_8_2_4_storage_isolation.py     # AC-8.2.4 tests (~280 LOC)
  test_ac_8_2_5_health_checks.py         # AC-8.2.5 tests (~180 LOC)
  test_ac_8_2_6_test_structure.py        # AC-8.2.6 tests (~220 LOC)
  test_baseline.py                       # Baseline tests (~150 LOC)
```

## How to Run Tests

```bash
# Run all Story 8.2 acceptance tests
pytest tests/unit/story_8_2/ -v

# Run specific AC tests
pytest tests/unit/story_8_2/test_ac_8_2_1_production_files.py -v
pytest tests/unit/story_8_2/test_ac_8_2_2_test_files.py -v
pytest tests/unit/story_8_2/test_ac_8_2_3_base_class.py -v
pytest tests/unit/story_8_2/test_ac_8_2_4_storage_isolation.py -v
pytest tests/unit/story_8_2/test_ac_8_2_5_health_checks.py -v
pytest tests/unit/story_8_2/test_ac_8_2_6_test_structure.py -v

# Run baseline tests only
pytest tests/unit/story_8_2/test_baseline.py -v

# Quick validation (should fail ~60+ tests before refactoring)
pytest tests/unit/story_8_2/ -q --tb=no
```

---

## Expected Test Results

### Before Refactoring (Current State)
- **RED Tests:** ~60+ tests failing (acceptance criteria not met)
- **GREEN Tests:** ~25 tests passing (baseline + import tests)

### After Refactoring (Target State)
- **GREEN Tests:** All ~85 tests passing
- **Baseline Tests:** Will start FAILING (expected - state has changed)

---

## Test Count Summary

| Category | Count | Expected Status (Pre-Refactoring) |
|----------|-------|-----------------------------------|
| AC-8.2.1 Tests | 14 | ~13 RED, 1 GREEN |
| AC-8.2.2 Tests | 8 | ~6 RED, 2 GREEN |
| AC-8.2.3 Tests | 11 | 11 RED |
| AC-8.2.4 Tests | 20 | 20 RED |
| AC-8.2.5 Tests | 12 | 12 GREEN |
| AC-8.2.6 Tests | 20 | ~15 RED, 5 GREEN |
| Baseline Tests | 13 | 13 GREEN |
| **Total** | **98** | **~65 RED, ~33 GREEN** |

---

## Files Created by This ATDD Phase

| File | Purpose | LOC |
|------|---------|-----|
| `tests/unit/story_8_2/__init__.py` | Package marker | ~10 |
| `tests/unit/story_8_2/conftest.py` | Shared fixtures | ~120 |
| `tests/unit/story_8_2/test_ac_8_2_1_production_files.py` | AC-8.2.1 tests | ~220 |
| `tests/unit/story_8_2/test_ac_8_2_2_test_files.py` | AC-8.2.2 tests | ~120 |
| `tests/unit/story_8_2/test_ac_8_2_3_base_class.py` | AC-8.2.3 tests | ~200 |
| `tests/unit/story_8_2/test_ac_8_2_4_storage_isolation.py` | AC-8.2.4 tests | ~280 |
| `tests/unit/story_8_2/test_ac_8_2_5_health_checks.py` | AC-8.2.5 tests | ~180 |
| `tests/unit/story_8_2/test_ac_8_2_6_test_structure.py` | AC-8.2.6 tests | ~220 |
| `tests/unit/story_8_2/test_baseline.py` | Baseline tests | ~150 |
| `docs/stories/atdd-checklist-8-2.md` | This checklist | ~350 |
| **Total** | 9 test files + 1 checklist | ~1,850 |

---

## Definition of Done for ATDD Phase

- [x] Story file analyzed for acceptance criteria
- [x] Test files created with all AC coverage
- [x] Tests structured using BDD-style naming
- [x] Tests are in RED state (failing)
- [x] Baseline tests document current state
- [x] ATDD checklist created
- [x] Test run command documented

---

## Next Steps (Implementation Phase)

1. Run baseline tests to confirm current state
2. Execute Task 1 from story: Baseline Capture
3. Execute Task 2: Create Base Client Class
4. Execute Task 3: Refactor storage.py into package
5. Execute Task 4-6: Refactor client files into packages
6. Execute Task 7: Update imports across codebase
7. Execute Task 8: Refactor test files
8. Execute Task 9-10: File size validation and final validation
9. All acceptance tests should be GREEN
