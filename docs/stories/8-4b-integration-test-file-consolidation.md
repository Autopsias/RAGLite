# Story 8.4b: Integration Test File Consolidation

> **Note:** This is a sub-story of Story 8.4 (Test File Consolidation). Story 8.4 was broken down into sub-stories per `docs/stories/8-4-story-breakdown-recommendation.md`. This sub-story focuses on integration test files exceeding 500 LOC.

## Story Header

- **Epic:** 8 - Technical Debt Reduction
- **Parent Story:** 8.4 - Test File Consolidation
- **Priority:** P0
- **Effort:** 1-2 days
- **Dependencies:** Stories 8.4a-1, 8.4a-2, 8.4a-3 (completed - patterns established)
- **Risk Links:** R-011
- **Next Story:** 8.4c - ATDD/E2E Test File Consolidation

## User Story

As a developer,
I want all integration test files reduced to under 500 LOC each,
so that AI tools can comprehend the full test context and integration test maintenance is improved.

## Background

Story 8.4 identified multiple test files exceeding 500 LOC. This sub-story addresses the 17 integration test files that exceed the limit:

| Priority | File | Current LOC | Target | Split Strategy |
|----------|------|-------------|--------|----------------|
| Critical | `tests/integration/test_forecast_query_integration.py` | 1,075 | <500 each | 3-way split (query types, workflows, edge cases) |
| Critical | `tests/integration/test_ingestion_integration.py` | 989 | <500 each | 3-way split (pdf, excel, pipeline) |
| Critical | `tests/integration/test_model_selection_cache_integration.py` | 969 | <500 each | 3-way split (cache, invalidation, integration) |
| Severe | `tests/integration/test_story_6_23_final_validation.py` | 674 | <500 each | 2-way split (validation, edge cases) |
| Severe | `tests/integration/test_model_selection.py` | 667 | <500 each | 2-way split (selection, performance) |
| Severe | `tests/integration/test_epic3_p0_scenarios.py` | 620 | <500 each | 2-way split (scenarios, validation) |
| Severe | `tests/integration/test_catboost_adaptive_weights.py` | 588 | <500 each | Fixture extraction or 2-way split |
| Severe | `tests/integration/test_fixed_chunking.py` | 566 | <500 each | Fixture extraction or 2-way split |
| Severe | `tests/integration/test_ecb_macroeconomic_integration.py` | 562 | <500 each | Fixture extraction or 2-way split |
| Moderate | `tests/integration/test_eurostat_api.py` | 543 | <500 each | Fixture extraction |
| Moderate | `tests/integration/test_proactive_insights_integration.py` | 532 | <500 each | Fixture extraction |
| Moderate | `tests/integration/test_metadata_injection.py` | 520 | <500 each | Fixture extraction |
| Moderate | `tests/integration/test_external_data_integration.py` | 509 | <500 each | Fixture extraction |
| Moderate | `tests/integration/test_analytical_query_tool.py` | 506 | <500 each | Fixture extraction |
| Moderate | `tests/integration/test_epic6_accuracy_regression.py` | 504 | <500 each | Fixture extraction |
| Moderate | `tests/integration/fixtures/session_fixtures.py` | 410 | Keep | Already under limit |
| Moderate | `tests/integration/test_workflow_orchestration.py` | 409 | Keep | Already under limit |

**Total Files to Refactor:** 15 files exceeding 500 LOC (~9,600 LOC to refactor)

**Note:** After file size analysis, the actual count is 15 files requiring refactoring (2 files are already under limit).

## Acceptance Criteria

### AC-8.4b.1: All Integration Test Files Under 500 LOC

**Given** 15 integration test files exceed the 500 LOC limit
**When** the refactoring is complete
**Then** all integration test files are under 500 LOC each

**Verification:**
- Run `python scripts/check_file_sizes.py --verbose`
- All files in `tests/integration/` pass the 500 LOC check
- Original files deleted or reduced to shim imports only

### AC-8.4b.2: Test Count Unchanged or Increased

**Given** the current test count baseline: `pytest tests/integration/ --collect-only -q | tail -1`
**When** the refactoring is complete
**Then** the total test count is unchanged or increased (no tests lost)

**Verification:**
- Record test count before refactoring
- Run `pytest tests/integration/ --collect-only -q | tail -1` after refactoring
- Count must be >= baseline count

### AC-8.4b.3: Coverage Maintained at 80%+

**Given** the current coverage baseline for integration tests
**When** the refactoring is complete
**Then** test coverage remains at or above 80%

**Verification:**
- Run `pytest tests/integration/ --cov=raglite --cov-fail-under=80`
- Coverage >= 80% maintained

### AC-8.4b.4: All Integration Tests Pass

**Given** all integration tests currently pass
**When** the refactoring is complete
**Then** all integration tests continue to pass

**Verification:**
- Run `pytest tests/integration/ -x` (stop on first failure)
- All tests pass
- No import errors or fixture issues

### AC-8.4b.5: Fixture Dependencies Preserved

**Given** integration tests have complex fixture dependencies in conftest.py
**When** the refactoring is complete
**Then** all fixture dependencies are preserved and working

**Verification:**
- Run `pytest tests/integration/ --fixtures` to verify fixture availability
- All shared fixtures remain accessible from all test files
- No fixture duplication or circular dependencies

## Technical Specification

### Splitting Strategy

**Critical Priority Files (>900 LOC) - 3-way splits:**

**1. test_forecast_query_integration.py (1,075 LOC) -> tests/integration/forecasting/**

```
tests/integration/forecasting/
  __init__.py
  conftest.py                           # Shared fixtures (mock forecasts, time series)
  test_forecast_query_types.py          # Query type-specific tests (~350 LOC)
  test_forecast_workflows.py            # Workflow and pipeline tests (~350 LOC)
  test_forecast_edge_cases.py           # Edge cases and error handling (~350 LOC)
```

**2. test_ingestion_integration.py (989 LOC) -> tests/integration/ingestion/**

```
tests/integration/ingestion/
  __init__.py
  conftest.py                           # Shared fixtures (sample PDFs, test data)
  test_pdf_pipeline.py                  # PDF ingestion pipeline tests (~350 LOC)
  test_excel_pipeline.py                # Excel processing tests (~300 LOC)
  test_ingestion_workflow.py            # End-to-end ingestion workflow (~300 LOC)
```

**3. test_model_selection_cache_integration.py (969 LOC) -> tests/integration/model_selection/**

```
tests/integration/model_selection/
  __init__.py
  conftest.py                           # Shared fixtures (mock cache, models)
  test_cache_operations.py              # Cache read/write tests (~350 LOC)
  test_cache_invalidation.py            # Cache invalidation tests (~300 LOC)
  test_selection_integration.py         # Model selection integration (~300 LOC)
```

**Severe Priority Files (550-700 LOC) - 2-way splits:**

**4. test_story_6_23_final_validation.py (674 LOC)**
- Split into `test_story_6_23_validation.py` and `test_story_6_23_edge_cases.py`

**5. test_model_selection.py (667 LOC)**
- Split into `test_model_selection_core.py` and `test_model_selection_perf.py`

**6. test_epic3_p0_scenarios.py (620 LOC)**
- Split into `test_epic3_core_scenarios.py` and `test_epic3_validation.py`

**7. test_catboost_adaptive_weights.py (588 LOC)**
- Extract fixtures to conftest.py, reduce to <500 LOC

**8. test_fixed_chunking.py (566 LOC)**
- Extract fixtures to conftest.py, reduce to <500 LOC

**9. test_ecb_macroeconomic_integration.py (562 LOC)**
- Extract fixtures to conftest.py, reduce to <500 LOC

**Moderate Priority Files (500-550 LOC) - Fixture extraction only:**

Files 10-15: Extract common fixtures to conftest.py or tests/integration/fixtures/:
- `test_eurostat_api.py` (543 LOC)
- `test_proactive_insights_integration.py` (532 LOC)
- `test_metadata_injection.py` (520 LOC)
- `test_external_data_integration.py` (509 LOC)
- `test_analytical_query_tool.py` (506 LOC)
- `test_epic6_accuracy_regression.py` (504 LOC)

### Fixture Management

1. **Root integration fixtures** remain in `tests/integration/conftest.py`
2. **Module-specific fixtures** go to `tests/integration/<module>/conftest.py`
3. **Shared fixtures** go to `tests/integration/fixtures/` (already exists)
4. **Session-scoped fixtures** preserve existing patterns in `fixtures/session_fixtures.py`

### Directory Structure After Refactoring

```
tests/integration/
  __init__.py
  conftest.py                           # Root fixtures (<100 LOC)
  fixtures/
    __init__.py
    container_lifecycle.py              # Docker container fixtures
    helper_fixtures.py                  # Helper functions
    module_fixtures.py                  # Module-level fixtures
    session_fixtures.py                 # Session-scoped fixtures
    session_state.py                    # Session state management
    service_checking.py                 # Service availability checks
  forecasting/
    __init__.py
    conftest.py                         # Forecasting-specific fixtures
    test_forecast_query_types.py
    test_forecast_workflows.py
    test_forecast_edge_cases.py
  ingestion/
    __init__.py
    conftest.py                         # Ingestion-specific fixtures
    test_pdf_pipeline.py
    test_excel_pipeline.py
    test_ingestion_workflow.py
  model_selection/
    __init__.py
    conftest.py                         # Model selection fixtures
    test_cache_operations.py
    test_cache_invalidation.py
    test_selection_integration.py
  # ... remaining test files (all <500 LOC)
```

## Tasks

- [ ] Task 1: Baseline Capture [AC-8.4b.2, AC-8.4b.3, AC-8.4b.4]
  - [ ] 1.1 Record test count: `pytest tests/integration/ --collect-only -q | tail -1`
  - [ ] 1.2 Record coverage baseline: `pytest tests/integration/ --cov=raglite`
  - [ ] 1.3 Document current LOC for each file: `python scripts/check_file_sizes.py --verbose`
  - [ ] 1.4 Map fixture dependencies: `pytest tests/integration/ --fixtures`

- [ ] Task 2: Split test_forecast_query_integration.py (1,075 LOC) [AC-8.4b.1]
  - [ ] 2.1 Create `tests/integration/forecasting/` directory structure
  - [ ] 2.2 Create `tests/integration/forecasting/conftest.py` with shared fixtures
  - [ ] 2.3 Split into 3 files: query_types, workflows, edge_cases
  - [ ] 2.4 Update imports in all new files
  - [ ] 2.5 Verify tests pass: `pytest tests/integration/forecasting/ -v`
  - [ ] 2.6 Delete original file

- [ ] Task 3: Split test_ingestion_integration.py (989 LOC) [AC-8.4b.1]
  - [ ] 3.1 Create `tests/integration/ingestion/` directory structure
  - [ ] 3.2 Create `tests/integration/ingestion/conftest.py` with shared fixtures
  - [ ] 3.3 Split into 3 files: pdf_pipeline, excel_pipeline, ingestion_workflow
  - [ ] 3.4 Update imports in all new files
  - [ ] 3.5 Verify tests pass: `pytest tests/integration/ingestion/ -v`
  - [ ] 3.6 Delete original file

- [ ] Task 4: Split test_model_selection_cache_integration.py (969 LOC) [AC-8.4b.1]
  - [ ] 4.1 Create `tests/integration/model_selection/` directory structure
  - [ ] 4.2 Create `tests/integration/model_selection/conftest.py` with shared fixtures
  - [ ] 4.3 Split into 3 files: cache_operations, cache_invalidation, selection_integration
  - [ ] 4.4 Update imports in all new files
  - [ ] 4.5 Verify tests pass: `pytest tests/integration/model_selection/ -v`
  - [ ] 4.6 Delete original file

- [ ] Task 5: Split Severe Priority Files (6 files) [AC-8.4b.1]
  - [ ] 5.1 Split test_story_6_23_final_validation.py (674 LOC) into 2 files
  - [ ] 5.2 Split test_model_selection.py (667 LOC) into 2 files
  - [ ] 5.3 Split test_epic3_p0_scenarios.py (620 LOC) into 2 files
  - [ ] 5.4 Refactor test_catboost_adaptive_weights.py (588 LOC) - extract fixtures
  - [ ] 5.5 Refactor test_fixed_chunking.py (566 LOC) - extract fixtures
  - [ ] 5.6 Refactor test_ecb_macroeconomic_integration.py (562 LOC) - extract fixtures
  - [ ] 5.7 Verify all tests pass after each split

- [ ] Task 6: Refactor Moderate Priority Files (6 files) [AC-8.4b.1]
  - [ ] 6.1 Extract fixtures from test_eurostat_api.py (543 LOC)
  - [ ] 6.2 Extract fixtures from test_proactive_insights_integration.py (532 LOC)
  - [ ] 6.3 Extract fixtures from test_metadata_injection.py (520 LOC)
  - [ ] 6.4 Extract fixtures from test_external_data_integration.py (509 LOC)
  - [ ] 6.5 Extract fixtures from test_analytical_query_tool.py (506 LOC)
  - [ ] 6.6 Extract fixtures from test_epic6_accuracy_regression.py (504 LOC)
  - [ ] 6.7 Verify all tests pass after fixture extraction

- [ ] Task 7: Fixture Validation [AC-8.4b.5]
  - [ ] 7.1 Run `pytest tests/integration/ --fixtures` to verify fixture availability
  - [ ] 7.2 Verify no fixture duplication
  - [ ] 7.3 Verify no circular dependencies
  - [ ] 7.4 Update `tests/integration/fixtures/` if needed

- [ ] Task 8: File Size Validation [AC-8.4b.1]
  - [ ] 8.1 Run `python scripts/check_file_sizes.py --verbose`
  - [ ] 8.2 Verify all new files under 500 LOC
  - [ ] 8.3 Update `.file-size-exceptions` (remove old entries)
  - [ ] 8.4 Document any exceptions with justification

- [ ] Task 9: Final Validation (MANDATORY) [All ACs]
  - [ ] 9.1 Verify test count >= baseline [AC-8.4b.2]
  - [ ] 9.2 Run `pytest tests/integration/ -x` - all tests pass [AC-8.4b.4]
  - [ ] 9.3 Run `pytest tests/integration/ --cov=raglite --cov-fail-under=80` [AC-8.4b.3]
  - [ ] 9.4 Run `python scripts/check_file_sizes.py` [AC-8.4b.1]
  - [ ] 9.5 Update sprint-status.yaml

## Dev Notes

### Risk Mitigation Strategies

**R-011: Fixture Dependency Issues (Score: 6)**
- Integration tests have complex fixture dependencies (Docker containers, databases)
- Test fixtures before modifying files
- Use `pytest --fixtures` to map fixture dependencies
- Keep conftest.py files in appropriate scope
- Incremental refactoring with tests after each step
- Preserve session-scoped fixtures for container lifecycle

### Patterns Established in Story 8.4a

**From Stories 8.4a-1, 8.4a-2, 8.4a-3 (COMPLETED):**

1. **Directory Structure Pattern:**
```
tests/<type>/<module>/
  __init__.py
  conftest.py              # Shared fixtures for module tests
  test_<feature>.py        # Feature-specific tests (<500 LOC)
  test_<feature>_edge_cases.py  # Edge cases if needed
```

2. **Fixture Pattern:**
```python
# tests/<type>/<module>/conftest.py
import pytest

@pytest.fixture
def sample_data():
    """Shared fixture for module tests."""
    return {...}
```

3. **Splitting Criteria:**
- Files >800 LOC: 3-way split by functionality
- Files 600-800 LOC: 2-way split by feature or test class
- Files 500-600 LOC: Fixture extraction to conftest.py

4. **Test Count Preservation:**
- All original tests must be preserved
- Test count should increase (more granular organization)
- Use `pytest --collect-only` to verify counts

### Integration Test Specific Considerations

1. **Container Dependencies:** Many integration tests require Docker containers (Qdrant, PostgreSQL)
2. **Session Fixtures:** Preserve session-scoped fixtures in `fixtures/session_fixtures.py`
3. **Service Checks:** Keep service availability checks in `fixtures/service_checking.py`
4. **Module Order:** Some tests may depend on execution order - preserve with markers if needed

### Architecture References

- [Epic 8 PRD](docs/prd/epic-8-technical-debt-reduction.md)
- [Story 8.4 Parent](docs/stories/8-4-test-file-consolidation.md)
- [Story 8.4a-1 Reference](docs/stories/8-4a-1-critical-unit-test-files.md) - Critical file patterns
- [Story 8.4a-2 Reference](docs/stories/8-4a-2-severe-unit-test-files.md) - Severe file patterns
- [Story 8.4a-3 Reference](docs/stories/8-4a-3-moderate-unit-test-files.md) - Moderate file patterns
- [File Size Limits Standards](.claude/rules/file-size-limits.md)

### NFRs

- **File Size:** All resulting files <500 LOC (enforced)
- **Test Count:** >= baseline count (no tests lost)
- **Coverage:** >=80% for integration tests
- **Performance:** Test suite execution time unchanged (+/- 10%)
- **Fixture Isolation:** No fixture leakage between test modules

## Testing Requirements

### Validation Checklist

```bash
# Pre-refactoring baseline
pytest tests/integration/ --collect-only -q | tail -1 > test_count_baseline.txt
pytest tests/integration/ --cov=raglite > coverage_baseline.txt
python scripts/check_file_sizes.py --verbose > sizes_baseline.txt
pytest tests/integration/ --fixtures > fixtures_baseline.txt

# After each major split
pytest tests/integration/ -x  # Stop on first failure

# Final validation
pytest tests/integration/ --collect-only -q | tail -1  # AC-8.4b.2: Verify count >= baseline
pytest tests/integration/ --cov=raglite --cov-fail-under=80  # AC-8.4b.3: Verify coverage >=80%
python scripts/check_file_sizes.py  # AC-8.4b.1: Verify all files <500 LOC
pytest tests/integration/ -x  # AC-8.4b.4: Verify all tests pass
pytest tests/integration/ --fixtures  # AC-8.4b.5: Verify fixtures available
```

## Definition of Done

- [ ] All 5 acceptance criteria verified with passing tests
- [ ] All 15 integration test files refactored to <500 LOC each
- [ ] Test count >= baseline (no tests lost)
- [ ] Coverage >=80% maintained
- [ ] All integration tests pass
- [ ] Fixtures properly organized in conftest.py files
- [ ] `.file-size-exceptions` updated (entries removed for refactored files)
- [ ] All CI checks passing

## Dev Agent Record

### Context Reference

N/A (story creation)

### Agent Model Used

- **Story Creation:** Claude Opus 4.5

### Debug Log References

N/A

### Completion Notes List

N/A (pending implementation)

### File List

**To Be Created:**
- tests/integration/forecasting/__init__.py
- tests/integration/forecasting/conftest.py
- tests/integration/forecasting/test_forecast_query_types.py
- tests/integration/forecasting/test_forecast_workflows.py
- tests/integration/forecasting/test_forecast_edge_cases.py
- tests/integration/ingestion/__init__.py
- tests/integration/ingestion/conftest.py
- tests/integration/ingestion/test_pdf_pipeline.py
- tests/integration/ingestion/test_excel_pipeline.py
- tests/integration/ingestion/test_ingestion_workflow.py
- tests/integration/model_selection/__init__.py
- tests/integration/model_selection/conftest.py
- tests/integration/model_selection/test_cache_operations.py
- tests/integration/model_selection/test_cache_invalidation.py
- tests/integration/model_selection/test_selection_integration.py

**To Be Deleted:**
- tests/integration/test_forecast_query_integration.py (1,075 LOC)
- tests/integration/test_ingestion_integration.py (989 LOC)
- tests/integration/test_model_selection_cache_integration.py (969 LOC)

**To Be Modified (split or fixture extraction):**
- tests/integration/test_story_6_23_final_validation.py (674 LOC)
- tests/integration/test_model_selection.py (667 LOC)
- tests/integration/test_epic3_p0_scenarios.py (620 LOC)
- tests/integration/test_catboost_adaptive_weights.py (588 LOC)
- tests/integration/test_fixed_chunking.py (566 LOC)
- tests/integration/test_ecb_macroeconomic_integration.py (562 LOC)
- tests/integration/test_eurostat_api.py (543 LOC)
- tests/integration/test_proactive_insights_integration.py (532 LOC)
- tests/integration/test_metadata_injection.py (520 LOC)
- tests/integration/test_external_data_integration.py (509 LOC)
- tests/integration/test_analytical_query_tool.py (506 LOC)
- tests/integration/test_epic6_accuracy_regression.py (504 LOC)

### Change Log

- 2025-12-28: Story created (sub-story of Story 8.4 for integration test files)
