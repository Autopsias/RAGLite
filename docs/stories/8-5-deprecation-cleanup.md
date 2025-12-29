# Story 8.5: Deprecation Warning Cleanup

## Overview

**Epic:** 8 - Technical Debt Reduction
**Story Key:** 8-5
**Priority:** P2 (Medium)
**Effort:** 2-4 hours
**Status:** In Progress

## Problem Statement

The test suite emits ~40+ deprecation warnings from our own code. While these warnings are intentional (marking deprecated APIs for removal), the tests should be updated to use the new APIs to:
1. Reduce warning noise in test output
2. Validate that new APIs work correctly
3. Prepare for eventual removal of deprecated code

## Scope

### In Scope

1. **`historical_data` parameter deprecation** (~40 warnings)
   - Location: `raglite/forecasting/hybrid/ensemble.py:generate_forecast()` (line 103)
   - New API: Use `metric` parameter instead to fetch from PostgreSQL
   - Affected test files:
     - `tests/unit/test_mcp_edge_cases.py`
     - `tests/unit/test_mcp_cache_exceptions.py`
     - `tests/unit/test_mcp_cache_lookup.py`
     - `tests/unit/test_hybrid_forecasting.py`
     - `tests/unit/test_mcp_response_metadata.py`
     - `tests/unit/test_chronos_integration.py`
     - `tests/unit/forecasting/test_mcp_model_routing_core.py`
     - `tests/integration/test_chronos_ensemble.py`
     - `tests/validation/test_forecast_accuracy.py`

2. **Import path deprecations** (~5 warnings)
   - Old: `raglite.ingestion.document_ingestion` (shim file)
   - New: `raglite.ingestion.document_ingestion` (package with submodules)
   - Note: Package `__init__.py` re-exports all public APIs, so most imports work unchanged
   - Scripts using old patterns:
     - `scripts/validate_forecasting_unified.py`
     - `scripts/ingest-production-batch.py`
     - `scripts/parallel-ingest-all-2025.py`
     - `scripts/benchmark-parallel-ingestion.py`
     - `scripts/ingest-all-2025-docs.py`
     - `scripts/cleanup-and-reingest.py`
     - `scripts/reingest-all-documents.py`
     - `scripts/ingest-for-validation.py`
     - `scripts/fix-qdrant-and-reingest.py`

3. **Fixture marker cleanup** (3 files)
   - Remove `@pytest.mark.priority()` from fixture functions
   - pytest 9.0 will error on marks applied to fixtures
   - Affected files:
     - `tests/integration/test_chunking_slow.py` (line 30-31: `test_pdf_path` fixture)
     - `tests/integration/test_chunking_core.py` (line 25-26: `test_pdf_path` fixture)
     - `tests/integration/test_chunking_extended.py` (line 25-26: `test_pdf_path` fixture)

### Out of Scope

- External library warnings (already filtered in pytest.ini)
- Docling API deprecations (tracked separately, requires library update)

## Acceptance Criteria

### AC1: historical_data Parameter Migration
**ID:** AC-8.5-1

**Given** test files using the deprecated `historical_data` parameter in `generate_forecast()` calls
**When** tests are updated to use the new `metric`-based API with mocked PostgreSQL data fetch
**Then** all 9 affected test files execute without `historical_data parameter is deprecated` warnings
**And** verification command `pytest tests/ -W error::DeprecationWarning 2>&1 | grep -c "historical_data"` returns 0

### AC2: Import Path Updates
**ID:** AC-8.5-2

**Given** the `document_ingestion` module refactored from single file to package structure
**When** package `__init__.py` re-exports are verified for backward compatibility
**Then** all scripts and tests using `from raglite.ingestion.document_ingestion import X` succeed without warnings
**And** verification command `python -W error::DeprecationWarning -c "from raglite.ingestion.document_ingestion import ingest_document"` completes successfully

### AC3: Fixture Marker Cleanup
**ID:** AC-8.5-3

**Given** pytest fixtures in 3 chunking test files using deprecated `@pytest.mark.priority()` decorator
**When** the decorator is removed from all `test_pdf_path` fixtures
**Then** no `PytestRemovedIn9Warning` appears in test output
**And** verification command `pytest tests/integration/test_chunking_*.py -W error 2>&1 | grep -c "PytestRemovedIn9Warning"` returns 0

### AC4: Full Test Suite Coverage
**ID:** AC-8.5-4

**Given** all deprecation cleanup tasks completed (AC1-AC3)
**When** the full test suite executes with deprecation warnings escalated to errors
**Then** all 3300+ tests pass without raglite code deprecation warnings
**And** test coverage remains at or above 80%
**And** no test behavior changes (same assertions pass/fail as before migration)

## Tasks

### Task 1: Fixture Marker Cleanup
**Links to:** AC-8.5-3
**Effort:** 15 minutes
**Files:**
- `tests/integration/test_chunking_slow.py`
- `tests/integration/test_chunking_core.py`
- `tests/integration/test_chunking_extended.py`

**Actions:**
1. Remove `@pytest.mark.priority("P2")` line from `test_pdf_path` fixture in each file
2. Run verification: `pytest tests/integration/test_chunking_*.py -W error 2>&1 | grep "PytestRemovedIn9Warning"`

**Deliverables:**
- 3 updated test files with fixtures conforming to pytest 9.0 requirements
- Verification output showing 0 PytestRemovedIn9Warning instances

### Task 2: historical_data Parameter Migration
**Links to:** AC-8.5-1
**Effort:** 1-2 hours
**Files to update:**
- `tests/unit/test_mcp_edge_cases.py`
- `tests/unit/test_mcp_cache_exceptions.py`
- `tests/unit/test_mcp_cache_lookup.py`
- `tests/unit/test_hybrid_forecasting.py`
- `tests/unit/test_mcp_response_metadata.py`
- `tests/unit/test_chronos_integration.py`
- `tests/unit/forecasting/test_mcp_model_routing_core.py`
- `tests/integration/test_chronos_ensemble.py`
- `tests/validation/test_forecast_accuracy.py`

**Pattern:**
```python
# Before (deprecated):
result = await generate_forecast(metric="ebitda", historical_data=data, horizon=6)

# After (new API with mock):
with patch("raglite.forecasting.hybrid.ensemble.fetch_historical_data") as mock_fetch:
    mock_fetch.return_value = data
    result = await generate_forecast(metric="ebitda", horizon=6)
```

**Actions:**
1. Update each test file to use mocked data fetch pattern
2. Run incremental verification after each file: `pytest <file> -W error::DeprecationWarning`
3. Final verification: `pytest tests/ -W error::DeprecationWarning 2>&1 | grep "historical_data"`

**Deliverables:**
- 9 updated test files using new API without deprecated parameter
- Test run output showing 0 historical_data deprecation warnings

### Task 3: Import Path Verification
**Links to:** AC-8.5-2
**Effort:** 30 minutes

**Actions:**
1. Verify package `__init__.py` re-exports: `cat raglite/ingestion/document_ingestion/__init__.py`
2. Test import compatibility: `python -W error::DeprecationWarning -c "from raglite.ingestion.document_ingestion import ingest_document, ingest_pdf, extract_excel"`
3. Scan scripts for direct submodule imports: `grep -r "from raglite.ingestion.document_ingestion\." scripts/`
4. Update any scripts with explicit submodule paths if needed

**Deliverables:**
- Verification report showing backward-compatible imports work
- Updated scripts (if any require changes)

### Task 4: Final Verification
**Links to:** AC-8.5-4
**Effort:** 30 minutes

**Actions:**
1. Run full test suite: `pytest tests/ -v`
2. Check for raglite deprecation warnings: `pytest tests/ 2>&1 | grep -i "deprecat" | grep raglite`
3. Verify coverage: `pytest tests/ --cov=raglite --cov-report=term-missing | grep "TOTAL"`
4. Confirm test count: `pytest tests/ --co -q | wc -l`

**Deliverables:**
- Test suite execution report (all 3300+ tests passing)
- Coverage report showing ≥80% coverage maintained
- Deprecation warning audit showing 0 raglite code warnings

## Testing Requirements

### Test Execution Strategy
1. **Incremental validation:** Run tests after each task to catch regressions early
2. **Warning escalation:** Use `-W error::DeprecationWarning` to ensure zero deprecation warnings
3. **Behavior preservation:** Verify same assertions pass/fail before and after changes
4. **Coverage maintenance:** Ensure ≥80% coverage maintained across all modified modules

### Test Scope by Task
- **Task 1 (Fixture cleanup):** 3 integration test files in `tests/integration/test_chunking_*.py`
- **Task 2 (historical_data migration):** 9 test files across unit/integration/validation
- **Task 3 (Import verification):** All scripts in `scripts/` directory + test suite
- **Task 4 (Final verification):** Full test suite (3300+ tests)

### Expected Test Behavior
- **Before migration:** ~40 deprecation warnings from `historical_data` parameter
- **After migration:** 0 deprecation warnings from raglite code
- **Test count:** 3300+ tests (unchanged)
- **Pass rate:** 100% (unchanged)
- **Coverage:** ≥80% (unchanged)

### Validation Commands
```bash
# Fixture marker warnings
pytest tests/integration/test_chunking_*.py -W error 2>&1 | grep "PytestRemovedIn9Warning"

# historical_data deprecation warnings
pytest tests/ -W error::DeprecationWarning 2>&1 | grep "historical_data"

# Import path warnings
python -W error::DeprecationWarning -c "from raglite.ingestion.document_ingestion import ingest_document"

# Full suite verification
pytest tests/ -v --cov=raglite --cov-report=term-missing
```

## Technical Notes

### historical_data Migration Pattern

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

### Import Path Backward Compatibility

The `document_ingestion` package `__init__.py` (from Story 8.3) maintains backward compatibility:
```python
# All these imports work without warnings:
from raglite.ingestion.document_ingestion import ingest_pdf
from raglite.ingestion.document_ingestion import ingest_document
from raglite.ingestion.document_ingestion import extract_excel
```

Package structure:
```
raglite/ingestion/document_ingestion/
├── __init__.py          # Re-exports all public APIs
├── core.py              # ingest_document
├── pdf_processing.py    # ingest_pdf
├── excel_processing.py  # extract_excel
└── ...
```

### Fixture Marker Fix (pytest 9.0 compatibility)

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

## Dev Notes

### Architecture References
- **Forecasting module:** `docs/architecture/6-complete-reference-implementation.md` Section 4.2 (Hybrid Forecasting)
- **Document ingestion package:** `docs/architecture/7-ingestion-module-structure.md` (Story 8.3 refactoring)
- **Deprecation implementation:** `raglite/forecasting/hybrid/ensemble.py:103` (`generate_forecast` function)
- **Test infrastructure:** `docs/architecture/12-test-infrastructure.md`

### Migration Dependencies
- **Story 8.3 completion:** Package structure must be in place for import verification
- **PostgreSQL mocks:** Tests need access to `fetch_historical_data` mock pattern
- **pytest version:** Fixture marker cleanup targets pytest 9.0 compatibility

## Definition of Done

- [x] Story file created with complete acceptance criteria
- [ ] All deprecation warnings from raglite code eliminated
- [ ] Test suite passes (3300+ tests)
- [ ] No regression in test coverage
- [ ] PR approved and merged

## References

- pytest.ini filterwarnings configuration (updated 2025-12-28)
- Epic 7 planned removal of `historical_data` parameter
- Story 8.3: Ingestion module refactoring (document_ingestion package)
