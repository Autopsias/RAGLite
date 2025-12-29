# ATDD Checklist - Story 8.5: Deprecation Warning Cleanup

## Story Information

- **Story ID:** 8-5
- **Epic:** 8 - Technical Debt Reduction
- **Story File:** docs/stories/8-5-deprecation-cleanup.md
- **Test File:** tests/atdd/test_story_8_5_deprecation_cleanup.py
- **Status:** GREEN (All 22 tests passing)
- **Created:** 2025-12-28
- **Completed:** 2025-12-28

## Acceptance Criteria Coverage

### AC-8.5-1: historical_data Parameter Migration

| Test ID | Test Name | AC Link | Status |
|---------|-----------|---------|--------|
| TEST-AC-8.5.1.1 | test_ac_8_5_1_1_no_historical_data_parameter_usage | AC-8.5-1 | GREEN |
| TEST-AC-8.5.1.2 | test_ac_8_5_1_2_no_deprecation_warning_in_output | AC-8.5-1 | GREEN |
| TEST-AC-8.5.1.3 | test_ac_8_5_1_3_generate_forecast_accepts_metric_only | AC-8.5-1 | GREEN |

**Verification Command:**
```bash
pytest tests/ -W error::DeprecationWarning 2>&1 | grep -c "historical_data"
# Expected: 0 (after implementation)
```

### AC-8.5-2: Import Path Updates

| Test ID | Test Name | AC Link | Status |
|---------|-----------|---------|--------|
| TEST-AC-8.5.2.1 | test_ac_8_5_2_1_package_imports_no_warning | AC-8.5-2 | GREEN |
| TEST-AC-8.5.2.2 | test_ac_8_5_2_2_scripts_use_valid_imports | AC-8.5-2 | GREEN |
| TEST-AC-8.5.2.3 | test_ac_8_5_2_3_verify_import_command_succeeds | AC-8.5-2 | GREEN |

**Verification Command:**
```bash
python -W error::DeprecationWarning -c "from raglite.ingestion.document_ingestion import ingest_document"
# Expected: Exit code 0 (after implementation)
```

### AC-8.5-3: Fixture Marker Cleanup

| Test ID | Test Name | AC Link | Status |
|---------|-----------|---------|--------|
| TEST-AC-8.5.3.1 | test_ac_8_5_3_1_no_marker_on_fixtures (parametrized x3) | AC-8.5-3 | GREEN |
| TEST-AC-8.5.3.2 | test_ac_8_5_3_2_no_pytest_removed_in_9_warning | AC-8.5-3 | GREEN |

**Verification Command:**
```bash
pytest tests/integration/test_chunking_*.py -W error 2>&1 | grep -c "PytestRemovedIn9Warning"
# Expected: 0 (after implementation)
```

### AC-8.5-4: Full Test Suite Coverage

| Test ID | Test Name | AC Link | Status |
|---------|-----------|---------|--------|
| TEST-AC-8.5.4.1 | test_ac_8_5_4_1_no_raglite_deprecation_in_unit_tests | AC-8.5-4 | GREEN |
| TEST-AC-8.5.4.2 | test_ac_8_5_4_2_historical_data_warnings_count_zero | AC-8.5-4 | GREEN |
| TEST-AC-8.5.4.3 | test_ac_8_5_4_3_verification_commands_pass | AC-8.5-4 | GREEN |
| TEST-AC-8.5.SUMMARY | test_ac_8_5_summary_all_deprecations_resolved | All ACs | GREEN |

## Test Statistics

- **Total Tests:** 13
- **AC1 Tests:** 3
- **AC2 Tests:** 3
- **AC3 Tests:** 4 (1 parametrized x3 + 1)
- **AC4 Tests:** 4
- **Summary Tests:** 1

## Deprecation Sources Targeted

### 1. historical_data Parameter (~40 warnings)
- **Location:** `raglite/forecasting/hybrid/ensemble.py:103`
- **Message:** "historical_data parameter is deprecated, will be removed in Epic 7"
- **Affected Files:**
  - tests/unit/test_mcp_edge_cases.py
  - tests/unit/test_mcp_cache_exceptions.py
  - tests/unit/test_mcp_cache_lookup.py
  - tests/unit/test_hybrid_forecasting.py
  - tests/unit/test_mcp_response_metadata.py
  - tests/unit/test_chronos_integration.py
  - tests/unit/forecasting/test_mcp_model_routing_core.py
  - tests/integration/test_chronos_ensemble.py
  - tests/validation/test_forecast_accuracy.py

### 2. Import Path Deprecations (~5 warnings)
- **Location:** `raglite/ingestion/document_ingestion.py` (shim file)
- **Message:** "Please update imports to: from raglite.ingestion.document_ingestion import <function>"
- **Affected Scripts:**
  - scripts/validate_forecasting_unified.py
  - scripts/ingest-production-batch.py
  - scripts/parallel-ingest-all-2025.py
  - scripts/benchmark-parallel-ingestion.py
  - scripts/ingest-all-2025-docs.py
  - scripts/cleanup-and-reingest.py
  - scripts/reingest-all-documents.py
  - scripts/ingest-for-validation.py
  - scripts/fix-qdrant-and-reingest.py

### 3. Fixture Marker Cleanup (3 fixtures)
- **Warning:** PytestRemovedIn9Warning
- **Issue:** @pytest.mark.priority() applied to @pytest.fixture functions
- **Affected Files:**
  - tests/integration/test_chunking_slow.py (test_pdf_path fixture, line 30-31)
  - tests/integration/test_chunking_core.py (test_pdf_path fixture, line 25-26)
  - tests/integration/test_chunking_extended.py (test_pdf_path fixture, line 25-26)

## Running the Tests

### Run All ATDD Tests (expect failures in RED phase)
```bash
pytest tests/atdd/test_story_8_5_deprecation_cleanup.py -v
```

### Run Specific AC Tests
```bash
# AC1: historical_data migration
pytest tests/atdd/test_story_8_5_deprecation_cleanup.py::TestAC851HistoricalDataDeprecation -v

# AC2: Import path updates
pytest tests/atdd/test_story_8_5_deprecation_cleanup.py::TestAC852ImportPathDeprecation -v

# AC3: Fixture marker cleanup
pytest tests/atdd/test_story_8_5_deprecation_cleanup.py::TestAC853FixtureMarkerCleanup -v

# AC4: Full suite coverage
pytest tests/atdd/test_story_8_5_deprecation_cleanup.py::TestAC854FullSuiteCoverage -v
```

## Expected State Transitions

| Phase | Status | Description |
|-------|--------|-------------|
| RED | Current | All tests fail - deprecated code exists |
| GREEN | Pending | All tests pass - deprecations resolved |
| REFACTOR | N/A | Code cleanup complete |

## Implementation Notes

### Pattern for historical_data Migration

**Before (deprecated):**
```python
result = await generate_forecast(
    metric="ebitda",
    historical_data=pd.Series([100, 110, 120]),
    horizon=6
)
```

**After (new API with mock):**
```python
with patch("raglite.forecasting.hybrid.ensemble.fetch_historical_data") as mock_fetch:
    mock_fetch.return_value = pd.Series([100, 110, 120])
    result = await generate_forecast(metric="ebitda", horizon=6)
```

### Fixture Marker Fix

**Before:**
```python
@pytest.fixture
@pytest.mark.priority("P2")
def test_pdf_path():
    ...
```

**After:**
```python
@pytest.fixture
def test_pdf_path():
    ...
```

## Definition of Done

- [x] All TEST-AC-8.5.1.x tests pass (historical_data migration)
- [x] All TEST-AC-8.5.2.x tests pass (import path updates)
- [x] All TEST-AC-8.5.3.x tests pass (fixture marker cleanup)
- [x] All TEST-AC-8.5.4.x tests pass (full suite coverage)
- [x] TEST-AC-8.5.SUMMARY passes (all deprecations resolved)
- [x] Verification commands return 0 counts
- [x] No regression in test coverage (>= 80%)
