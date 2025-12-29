# ATDD Checklist - Story 8.3: Ingestion Module Refactoring

## Test Files
- **Location:** `tests/atdd/story_8_3/` (package structure)
- **Phase:** TDD RED (tests failing as expected)
- **Status:** Tests created, awaiting implementation

### Test File Structure (Under 500 LOC Each)

| File | LOC | Purpose |
|------|-----|---------|
| `__init__.py` | 12 | Package docstring |
| `conftest.py` | 37 | Shared fixtures and constants |
| `test_ac_8_3_1_production_files.py` | 231 | AC-8.3.1 tests |
| `test_ac_8_3_2_test_files.py` | 78 | AC-8.3.2 tests |
| `test_ac_8_3_3_pipeline.py` | 128 | AC-8.3.3 tests |
| `test_ac_8_3_4_sample_pdfs.py` | 96 | AC-8.3.4 tests |
| `test_ac_8_3_5_test_mirror.py` | 106 | AC-8.3.5 tests |
| `test_backward_compat.py` | 206 | Backward compatibility tests |

## Acceptance Criteria Coverage

### AC-8.3.1: All Production Files Under 500 LOC

| Test ID | Test Name | AC Mapping | Status |
|---------|-----------|------------|--------|
| TEST-AC-8.3.1.1 | `test_ac_8_3_1_1_document_ingestion_package_exists` | AC-8.3.1 | FAILED |
| TEST-AC-8.3.1.2 | `test_ac_8_3_1_2_document_ingestion_modules_under_limit` (6 params) | AC-8.3.1 | FAILED |
| TEST-AC-8.3.1.3 | `test_ac_8_3_1_3_unit_inference_package_exists` | AC-8.3.1 | FAILED |
| TEST-AC-8.3.1.4 | `test_ac_8_3_1_4_unit_inference_modules_under_limit` (4 params) | AC-8.3.1 | FAILED |
| TEST-AC-8.3.1.5 | `test_ac_8_3_1_5_core_package_exists` | AC-8.3.1 | FAILED |
| TEST-AC-8.3.1.6 | `test_ac_8_3_1_6_core_modules_under_limit` (3 params) | AC-8.3.1 | FAILED |
| TEST-AC-8.3.1.7 | `test_ac_8_3_1_7_original_files_are_shims` | AC-8.3.1 | FAILED |
| TEST-AC-8.3.1.8 | `test_ac_8_3_1_8_check_file_sizes_script_passes` | AC-8.3.1 | PASSED |

### AC-8.3.2: All Test Files Under 500 LOC

| Test ID | Test Name | AC Mapping | Status |
|---------|-----------|------------|--------|
| TEST-AC-8.3.2.1 | `test_ac_8_3_2_1_test_directory_structure_exists` | AC-8.3.2 | FAILED |
| TEST-AC-8.3.2.2 | `test_ac_8_3_2_2_all_test_files_under_500_loc` | AC-8.3.2 | SKIPPED |
| TEST-AC-8.3.2.3 | `test_ac_8_3_2_3_conftest_files_exist` | AC-8.3.2 | FAILED |

### AC-8.3.3: Ingestion Pipeline Performance Unchanged

| Test ID | Test Name | AC Mapping | Status |
|---------|-----------|------------|--------|
| TEST-AC-8.3.3.1 | `test_ac_8_3_3_1_ingest_document_importable` | AC-8.3.3 | FAILED |
| TEST-AC-8.3.3.2 | `test_ac_8_3_3_2_ingest_pdf_importable` | AC-8.3.3 | FAILED |
| TEST-AC-8.3.3.3 | `test_ac_8_3_3_3_temp_file_from_url_importable` | AC-8.3.3 | FAILED |
| TEST-AC-8.3.3.4 | `test_ac_8_3_3_4_extract_excel_importable` | AC-8.3.3 | FAILED |
| TEST-AC-8.3.3.5 | `test_ac_8_3_3_5_ingest_documents_parallel_importable` | AC-8.3.3 | FAILED |
| TEST-AC-8.3.3.6 | `test_ac_8_3_3_6_all_existing_tests_pass` | AC-8.3.3 | FAILED |

### AC-8.3.4: Sample PDFs Re-ingestable Successfully

| Test ID | Test Name | AC Mapping | Status |
|---------|-----------|------------|--------|
| TEST-AC-8.3.4.1 | `test_ac_8_3_4_1_adaptive_table_extraction_importable` | AC-8.3.4 | FAILED |
| TEST-AC-8.3.4.2 | `test_ac_8_3_4_2_unit_inference_importable` | AC-8.3.4 | FAILED |
| TEST-AC-8.3.4.3 | `test_ac_8_3_4_3_async_batch_inference_importable` | AC-8.3.4 | FAILED |
| TEST-AC-8.3.4.4 | `test_ac_8_3_4_4_context_helpers_importable` | AC-8.3.4 | FAILED |

### AC-8.3.5: Test File Structure Mirrors Production

| Test ID | Test Name | AC Mapping | Status |
|---------|-----------|------------|--------|
| TEST-AC-8.3.5.1 | `test_ac_8_3_5_1_document_ingestion_test_modules_exist` | AC-8.3.5 | FAILED |
| TEST-AC-8.3.5.2 | `test_ac_8_3_5_2_unit_inference_test_modules_exist` | AC-8.3.5 | FAILED |
| TEST-AC-8.3.5.3 | `test_ac_8_3_5_3_core_test_modules_exist` | AC-8.3.5 | FAILED |

### Additional Coverage: Backward Compatibility

| Test ID | Test Name | Purpose | Status |
|---------|-----------|---------|--------|
| TEST-SHIM-1 | `test_shim_document_ingestion_imports_with_deprecation_warning` | Shim deprecation | SKIPPED |
| TEST-SHIM-2 | `test_shim_unit_inference_exports_all_public_functions` | Shim exports | SKIPPED |

### Additional Coverage: Import Graph Validation

| Test ID | Test Name | Purpose | Status |
|---------|-----------|---------|--------|
| TEST-IMPORT-1 | `test_document_ingestion_no_circular_imports` | No circular deps | SKIPPED |
| TEST-IMPORT-2 | `test_unit_inference_no_circular_imports` | No circular deps | SKIPPED |
| TEST-IMPORT-3 | `test_core_no_circular_imports` | No circular deps | SKIPPED |

### Additional Coverage: Main Entry Point

| Test ID | Test Name | Purpose | Status |
|---------|-----------|---------|--------|
| TEST-ENTRY-1 | `test_raglite_ingestion_module_importable` | Main module import | PASSED |
| TEST-ENTRY-2 | `test_ingest_pdf_available_from_main_module` | Public API | PASSED |

## Test Summary

| Category | Total | Passed | Failed | Skipped |
|----------|-------|--------|--------|---------|
| AC-8.3.1 (Production Files) | 18 | 1 | 17 | 0 |
| AC-8.3.2 (Test Files) | 3 | 0 | 2 | 1 |
| AC-8.3.3 (Pipeline) | 6 | 0 | 6 | 0 |
| AC-8.3.4 (Sample PDFs) | 4 | 0 | 4 | 0 |
| AC-8.3.5 (Test Mirror) | 3 | 0 | 3 | 0 |
| Backward Compat | 2 | 0 | 0 | 2 |
| Import Graph | 3 | 0 | 0 | 3 |
| Entry Point | 2 | 2 | 0 | 0 |
| **TOTAL** | **41** | **3** | **32** | **6** |

## Expected Test Behavior (RED Phase)

Tests are correctly in **RED** state:
- **32 FAILED** - Expected failures because refactoring not done yet
- **6 SKIPPED** - Smart skips that detect pre-refactoring state
- **3 PASSED** - Entry point tests that work with current structure

### Why Tests Fail

1. **Package directories don't exist yet:**
   - `raglite/ingestion/document_ingestion/` (needs to be created)
   - `raglite/ingestion/adaptive_table/unit_inference/` (needs to be created)
   - `raglite/ingestion/adaptive_table/core/` (needs to be created)

2. **Modules not yet split:**
   - `document_ingestion.py` is 1,343 LOC (needs refactoring)
   - `unit_inference.py` is 1,205 LOC (needs refactoring)
   - `core.py` is 903 LOC (needs refactoring)

3. **Test structure not yet created:**
   - `tests/unit/ingestion/document_ingestion/` (needs to be created)
   - `tests/unit/ingestion/adaptive_table/` (needs to be created)

## Run Tests

```bash
# Run all ATDD tests for Story 8.3
uv run pytest tests/atdd/story_8_3/ -v

# Run specific AC tests
uv run pytest tests/atdd/story_8_3/test_ac_8_3_1_production_files.py -v
uv run pytest tests/atdd/story_8_3/test_ac_8_3_2_test_files.py -v
uv run pytest tests/atdd/story_8_3/test_ac_8_3_3_pipeline.py -v
uv run pytest tests/atdd/story_8_3/test_ac_8_3_4_sample_pdfs.py -v
uv run pytest tests/atdd/story_8_3/test_ac_8_3_5_test_mirror.py -v
uv run pytest tests/atdd/story_8_3/test_backward_compat.py -v
```

## Transition to GREEN Phase

After implementing Story 8.3, all tests should pass:

1. Create package directories with `__init__.py`
2. Split each large file into modules under 500 LOC
3. Create backward compatibility shims with deprecation warnings
4. Update imports across codebase
5. Create test directory structure mirroring production
6. Split test files into modules under 500 LOC

## Files to Monitor

### Production Files (Before -> After Refactoring)

| Original File | LOC | Target Structure |
|---------------|-----|------------------|
| `raglite/ingestion/document_ingestion.py` | 1,343 | `raglite/ingestion/document_ingestion/` package (6 modules) |
| `raglite/ingestion/adaptive_table/unit_inference.py` | 1,205 | `raglite/ingestion/adaptive_table/unit_inference/` package (4 modules) |
| `raglite/ingestion/adaptive_table/core.py` | 903 | `raglite/ingestion/adaptive_table/core/` package (3 modules) |

### Test Files (Before -> After Refactoring)

| Original File | Target Structure |
|---------------|------------------|
| `tests/unit/test_ingestion.py` | `tests/unit/ingestion/document_ingestion/` (6 test modules) |
| Tests in adaptive_table | `tests/unit/ingestion/adaptive_table/` (2 subdirs) |
