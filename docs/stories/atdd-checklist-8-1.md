# ATDD Checklist - Story 8.1: Critical Forecasting Module Refactoring

## Story Summary
Split large forecasting production files into modules under 500 LOC each for improved AI comprehension and maintainability.

## Test Status: RED (Pre-Refactoring)

All acceptance tests are designed to FAIL initially. They will PASS after refactoring is complete.

---

## Acceptance Criteria Test Mapping

### AC-8.1.1: Production Files Under 500 LOC

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-AC-8.1.1-A | `test_ac_8_1_1_original_files_converted_to_shims` | RED | Verifies shim conversion (< 100 LOC) |
| TEST-AC-8.1.1-B | `test_ac_8_1_1_timeseries_submodules_exist` | RED | Checks for 7 timeseries submodules |
| TEST-AC-8.1.1-C | `test_ac_8_1_1_hybrid_submodules_exist` | RED | Checks for 6 hybrid submodules |
| TEST-AC-8.1.1-D | `test_ac_8_1_1_all_new_modules_under_500_loc` | RED | Validates LOC limits on new modules |

**Current State:**
- `timeseries_extract.py`: 3,178 LOC (target: < 100 as shim)
- `hybrid.py`: 2,780 LOC (target: < 100 as shim)

---

### AC-8.1.2: Test Files Under 500 LOC

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-AC-8.1.2-A | `test_ac_8_1_2_original_test_file_split` | RED | Verifies test file split |
| TEST-AC-8.1.2-B | `test_ac_8_1_2_timeseries_test_submodules_exist` | RED | Checks for 6 test submodules |
| TEST-AC-8.1.2-C | `test_ac_8_1_2_hybrid_test_submodules_exist` | RED | Checks for 5 test submodules |
| TEST-AC-8.1.2-D | `test_ac_8_1_2_all_new_test_modules_under_500_loc` | RED | Validates LOC limits on test modules |

**Current State:**
- `test_timeseries_extract.py`: 1,413 LOC (target: split into < 500 LOC each)
- `test_hybrid_forecasting.py`: 489 LOC (already under limit)

---

### AC-8.1.3: Test Coverage >= 80% Maintained

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-AC-8.1.3-A | `test_ac_8_1_3_forecasting_module_importable` | GREEN | Basic import check |
| TEST-AC-8.1.3-B | `test_ac_8_1_3_timeseries_module_importable` | RED | New package import |
| TEST-AC-8.1.3-C | `test_ac_8.1.3_hybrid_submodule_importable` | RED | New package import |

**Verification Command:**
```bash
pytest --cov=raglite.forecasting --cov-fail-under=80
```

---

### AC-8.1.4: All Imports Updated Across Codebase

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-AC-8.1.4-A | `test_ac_8_1_4_old_import_paths_work` | GREEN | Old paths via shims |
| TEST-AC-8.1.4-B | `test_ac_8_1_4_new_import_paths_work_timeseries` | RED | New timeseries imports |
| TEST-AC-8.1.4-C | `test_ac_8_1_4_new_import_paths_work_hybrid` | RED | New hybrid imports |
| TEST-AC-8.1.4-D | `test_ac_8_1_4_deprecation_warning_from_old_imports` | RED | Deprecation warnings |

---

### AC-8.1.5: No Circular Dependencies

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-AC-8.1.5-A | `test_ac_8_1_5_import_raglite_succeeds` | GREEN | Top-level import |
| TEST-AC-8.1.5-B | `test_ac_8_1_5_import_forecasting_succeeds` | GREEN | Forecasting import |
| TEST-AC-8.1.5-C | `test_ac_8_1_5_each_submodule_imports_independently` | RED | Individual imports |

**Verification Commands:**
```bash
python -c "import raglite"
python -c "import raglite.forecasting"
```

---

### AC-8.1.6: Performance Benchmarks Unchanged

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-AC-8.1.6-A | `test_ac_8_1_6_module_import_time_acceptable` | GREEN | Import time < 5s |
| TEST-AC-8.1.6-B | `test_ac_8_1_6_forecasting_functions_accessible` | GREEN | Function access |

**Performance Tolerance:** +/- 10% from baseline

---

### AC-8.1.7: Test Structure Mirrors Production

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-AC-8.1.7-A | `test_ac_8_1_7_timeseries_test_structure_matches_production` | RED | 1:1 mapping |
| TEST-AC-8.1.7-B | `test_ac_8_1_7_hybrid_test_structure_matches_production` | RED | 1:1 mapping |
| TEST-AC-8.1.7-C | `test_ac_8_1_7_conftest_files_exist` | RED | Shared fixtures |

---

## Baseline Tests (Should PASS Before Refactoring)

| Test Name | Status | Purpose |
|-----------|--------|---------|
| `test_baseline_timeseries_extract_exceeds_limit` | GREEN | Documents current state |
| `test_baseline_hybrid_exceeds_limit` | GREEN | Documents current state |
| `test_baseline_test_timeseries_extract_exceeds_limit` | GREEN | Documents current state |
| `test_baseline_timeseries_package_does_not_exist` | GREEN | Confirms package not created |
| `test_baseline_hybrid_package_does_not_exist` | GREEN | Confirms package not created |

---

## Test File Location

```
tests/unit/story_8_1/
  __init__.py                        # Package marker (~5 LOC)
  conftest.py                        # Shared fixtures and utilities (~56 LOC)
  test_ac_8_1_1_production_files.py  # AC-8.1.1 tests (~108 LOC)
  test_ac_8_1_2_test_files.py        # AC-8.1.2 tests (~89 LOC)
  test_ac_8_1_3_coverage.py          # AC-8.1.3 tests (~53 LOC)
  test_ac_8_1_4_imports.py           # AC-8.1.4 tests (~113 LOC)
  test_ac_8_1_5_circular_deps.py     # AC-8.1.5 tests (~82 LOC)
  test_ac_8_1_6_performance.py       # AC-8.1.6 tests (~54 LOC)
  test_ac_8_1_7_structure.py         # AC-8.1.7 tests (~110 LOC)
  test_baseline.py                   # Baseline tests (~71 LOC)
```

## How to Run Tests

```bash
# Run all Story 8.1 acceptance tests
pytest tests/unit/story_8_1/ -v

# Run specific AC tests
pytest tests/unit/story_8_1/test_ac_8_1_1_production_files.py -v
pytest tests/unit/story_8_1/test_ac_8_1_2_test_files.py -v
pytest tests/unit/story_8_1/test_ac_8_1_3_coverage.py -v
pytest tests/unit/story_8_1/test_ac_8_1_4_imports.py -v
pytest tests/unit/story_8_1/test_ac_8_1_5_circular_deps.py -v
pytest tests/unit/story_8_1/test_ac_8_1_6_performance.py -v
pytest tests/unit/story_8_1/test_ac_8_1_7_structure.py -v

# Run baseline tests only
pytest tests/unit/story_8_1/test_baseline.py -v
```

---

## Expected Test Results

### Before Refactoring (Current State)
- **RED Tests:** 20+ tests failing (acceptance criteria not met)
- **GREEN Tests:** 5 baseline tests passing (documenting current state)
- **GREEN Tests:** 4-5 import/performance tests passing (basic functionality)

### After Refactoring (Target State)
- **GREEN Tests:** All 25+ tests passing
- **Baseline Tests:** Will start FAILING (expected - state has changed)

---

## Files Created by This ATDD Phase

| File | Purpose | LOC |
|------|---------|-----|
| `tests/unit/story_8_1/__init__.py` | Package marker | ~5 |
| `tests/unit/story_8_1/conftest.py` | Shared fixtures | ~56 |
| `tests/unit/story_8_1/test_ac_8_1_1_production_files.py` | AC-8.1.1 tests | ~108 |
| `tests/unit/story_8_1/test_ac_8_1_2_test_files.py` | AC-8.1.2 tests | ~89 |
| `tests/unit/story_8_1/test_ac_8_1_3_coverage.py` | AC-8.1.3 tests | ~53 |
| `tests/unit/story_8_1/test_ac_8_1_4_imports.py` | AC-8.1.4 tests | ~113 |
| `tests/unit/story_8_1/test_ac_8_1_5_circular_deps.py` | AC-8.1.5 tests | ~82 |
| `tests/unit/story_8_1/test_ac_8_1_6_performance.py` | AC-8.1.6 tests | ~54 |
| `tests/unit/story_8_1/test_ac_8_1_7_structure.py` | AC-8.1.7 tests | ~110 |
| `tests/unit/story_8_1/test_baseline.py` | Baseline tests | ~71 |
| `docs/stories/atdd-checklist-8-1.md` | This checklist | ~230 |
| **Total** | 10 test files + 1 checklist | ~741 |

---

## Definition of Done for ATDD Phase

- [x] Story file analyzed for acceptance criteria
- [x] Test file created with all AC coverage
- [x] Tests structured using BDD-style naming
- [x] Tests are in RED state (failing)
- [x] Baseline tests document current state
- [x] ATDD checklist created
- [x] Test run command documented

---

## Next Steps (Implementation Phase)

1. Run baseline tests to confirm current state
2. Execute Task 1 from story: Baseline Capture
3. Execute Task 2-4: Analyze and extract timeseries modules
4. Run acceptance tests after each extraction to track progress
5. Execute Task 5-7: Analyze and extract hybrid modules
6. Execute Task 8-9: Create shims and update imports
7. Execute Task 10-11: Refactor test files
8. Execute Task 12-13: Final validation
9. All acceptance tests should be GREEN

---

## Test Count Summary

| Category | Count | Status |
|----------|-------|--------|
| AC-8.1.1 Tests | 4 | RED |
| AC-8.1.2 Tests | 4 | RED |
| AC-8.1.3 Tests | 3 | 1 GREEN, 2 RED |
| AC-8.1.4 Tests | 4 | 1 GREEN, 3 RED |
| AC-8.1.5 Tests | 3 | 2 GREEN, 1 RED |
| AC-8.1.6 Tests | 2 | 2 GREEN |
| AC-8.1.7 Tests | 3 | RED |
| Baseline Tests | 5 | GREEN |
| **Total** | **28** | **~11 GREEN, ~17 RED** |
