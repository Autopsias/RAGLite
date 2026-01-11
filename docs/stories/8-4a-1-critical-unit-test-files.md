# Story 8.4a-1: Critical Priority Unit Test File Splitting

> **Note:** This is a micro-story of Story 8.4a (Unit Test File Consolidation). Story 8.4a was broken down due to scope issues (39 files requiring refactoring). This micro-story focuses on the 2 remaining critical priority files (>1000 LOC). test_timeseries_extract.py was already refactored in Story 8.1.

## Story Header

- **Epic:** 8 - Technical Debt Reduction
- **Parent Story:** 8.4a - Unit Test File Consolidation
- **Priority:** P0
- **Effort:** 1 day
- **Dependencies:** Stories 8.1, 8.2, 8.3 (completed)
- **Risk Links:** R-011

## User Story

As a developer,
I want the 2 remaining largest unit test files (>1000 LOC) split into modules under 500 LOC each,
so that AI tools can comprehend the full test context and test maintenance is improved.

## Background

Story 8.4a identified 39 unit test files exceeding 500 LOC. This micro-story addresses the 2 remaining critical priority files that are over 1000 LOC each:

| File | Current LOC | Target | Split Strategy |
|------|-------------|--------|----------------|
| `tests/unit/test_ingestion.py` | 1,817 | <500 each | Split into `tests/unit/ingestion/` directory (4-5 files) |
| `tests/unit/test_model_selection_job.py` | 1,217 | <500 each | Split into `tests/unit/forecasting/model_selection/` (3-4 files) |

**Total:** 2 files, 3,034 LOC to refactor

**Note:** `tests/unit/test_timeseries_extract.py` (1,413 LOC) was already refactored in Story 8.1 into `tests/unit/forecasting/timeseries/`.

## Acceptance Criteria

### AC-8.4a-1.1: Both Files Split to <500 LOC Each

**Given** the 2 remaining critical priority unit test files exceed 1000 LOC
**When** the refactoring is complete
**Then** all resulting files are under 500 LOC each

**Verification:**
- Run `python scripts/check_file_sizes.py --verbose`
- All files in `tests/unit/ingestion/` and `tests/unit/forecasting/model_selection/` pass the 500 LOC check
- Original files deleted or reduced to shim imports only

### AC-8.4a-1.2: Test Count Unchanged or Increased

**Given** the current test count baseline from the 2 files
**When** the refactoring is complete
**Then** the total test count is unchanged or increased (no tests lost)

**Verification:**
- Run `pytest tests/unit/test_ingestion.py tests/unit/test_model_selection_job.py --collect-only -q | tail -1` before refactoring
- Run `pytest tests/unit/ingestion/ tests/unit/forecasting/model_selection/ --collect-only -q | tail -1` after refactoring
- Count must be >= baseline count

### AC-8.4a-1.3: Coverage Maintained at 80%+

**Given** the current coverage baseline for the affected modules
**When** the refactoring is complete
**Then** test coverage remains at or above 80%

**Verification:**
- Run `pytest tests/unit/ --cov=raglite --cov-fail-under=80`
- Coverage >= 80% maintained

### AC-8.4a-1.4: All Unit Tests Pass

**Given** all unit tests currently pass
**When** the refactoring is complete
**Then** all unit tests continue to pass

**Verification:**
- Run `pytest tests/unit/ -x` (stop on first failure)
- All tests pass
- No import errors or fixture issues

### AC-8.4a-1.5: All Resulting Files <500 LOC Verified

**Given** the file size limits are enforced by CI
**When** the refactoring is complete
**Then** all new test files are verified under 500 LOC by check_file_sizes.py

**Verification:**
- Run `python scripts/check_file_sizes.py`
- No new entries added to `.file-size-exceptions` for these files
- CI file size check passes

## Technical Specification

### Splitting Strategy

**1. test_ingestion.py (1,817 LOC) -> tests/unit/ingestion/**

```
tests/unit/ingestion/
  __init__.py
  conftest.py                    # Shared fixtures (mock Docling, embeddings, etc.)
  test_pdf_ingestion.py          # TestIngestPDF class tests
  test_excel_processing.py       # Excel extraction tests
  test_base64_ingestion.py       # Base64 content tests (if not already separate)
  test_chunking.py               # Chunking strategy tests
  test_vector_storage.py         # Qdrant storage tests
```

**2. test_model_selection_job.py (1,217 LOC) -> tests/unit/forecasting/model_selection/**

```
tests/unit/forecasting/model_selection/
  __init__.py
  conftest.py                    # Shared fixtures (mock historical data, models)
  test_job_core.py               # Core job execution tests
  test_job_batch.py              # Batch processing tests
  test_job_parallel.py           # Parallel execution tests (workers)
  test_job_cache.py              # Cache integration tests
  test_job_reports.py            # Report generation tests
```

### Fixture Management

1. **Root fixtures** remain in `tests/unit/conftest.py`
2. **Module fixtures** go to `tests/unit/<module>/conftest.py`
3. **Shared test utilities** go to `tests/unit/<module>/helpers.py` if needed

## Tasks

- [ ] Task 1: Baseline Capture [AC-8.4a-1.2, AC-8.4a-1.3, AC-8.4a-1.4]
  - [ ] 1.1 Record test count for 2 files: `pytest tests/unit/test_ingestion.py tests/unit/test_model_selection_job.py --collect-only -q | tail -1`
  - [ ] 1.2 Record coverage baseline: `pytest tests/unit/ --cov=raglite`
  - [ ] 1.3 Document current LOC for each file

- [ ] Task 2: Split test_ingestion.py (1,817 LOC) [AC-8.4a-1.1]
  - [ ] 2.1 Create `tests/unit/ingestion/` directory structure
  - [ ] 2.2 Create `tests/unit/ingestion/conftest.py` with shared fixtures
  - [ ] 2.3 Split by test class/feature: PDF, Excel, chunking, storage
  - [ ] 2.4 Update imports in all new files
  - [ ] 2.5 Verify tests pass: `pytest tests/unit/ingestion/ -v`
  - [ ] 2.6 Delete or convert original file to shim

- [ ] Task 3: Split test_model_selection_job.py (1,217 LOC) [AC-8.4a-1.1]
  - [ ] 3.1 Create `tests/unit/forecasting/model_selection/` directory structure
  - [ ] 3.2 Create `tests/unit/forecasting/model_selection/conftest.py` with shared fixtures
  - [ ] 3.3 Split by functionality: core, batch, parallel, cache, reports
  - [ ] 3.4 Update imports in all new files
  - [ ] 3.5 Verify tests pass: `pytest tests/unit/forecasting/model_selection/ -v`
  - [ ] 3.6 Delete or convert original file to shim

- [ ] Task 4: File Size Validation [AC-8.4a-1.5]
  - [ ] 4.1 Run `python scripts/check_file_sizes.py --verbose`
  - [ ] 4.2 Verify all new files under 500 LOC
  - [ ] 4.3 Update `.file-size-exceptions` if needed (remove old entries)
  - [ ] 4.4 Document any exceptions with justification

- [ ] Task 5: Final Validation (MANDATORY) [All ACs]
  - [ ] 5.1 Verify test count >= baseline
  - [ ] 5.2 Run `pytest tests/unit/ -x` - all tests pass
  - [ ] 5.3 Run `pytest tests/unit/ --cov=raglite --cov-fail-under=80` - coverage maintained
  - [ ] 5.4 Run `python scripts/check_file_sizes.py` - all files pass
  - [ ] 5.5 Update sprint-status.yaml

## Dev Notes

### Risk Mitigation Strategies

**R-011: Fixture Dependency Issues (Score: 6)**
- Test fixtures before modifying files
- Use `pytest --fixtures` to map fixture dependencies
- Keep conftest.py files in appropriate scope
- Incremental refactoring with tests after each step

### Existing Patterns to Follow

**From Story 8.1 - Timeseries Test Structure:**
```
tests/unit/forecasting/timeseries/
  __init__.py
  conftest.py              # Shared fixtures for timeseries tests
  test_parsing.py          # Tests for parsing module
  test_core.py             # Tests for core module
  test_sql_extraction.py   # Tests for SQL extraction
```

**Fixture Pattern:**
```python
# tests/unit/<module>/conftest.py
import pytest

@pytest.fixture
def sample_data():
    """Shared fixture for module tests."""
    return {...}
```

### Architecture References

- [Epic 8 PRD](docs/prd/epic-8-technical-debt-reduction.md)
- [Story 8.4a](docs/stories/8-4a-unit-test-file-consolidation.md) - Parent story
- [Story 8.4 Breakdown Recommendation](docs/stories/8-4-story-breakdown-recommendation.md)
- [File Size Limits Standards](.claude/rules/file-size-limits.md)
- [Story 8.1 Reference](docs/stories/8-1-critical-forecasting-module-refactoring.md) - Proven patterns

### NFRs

- **File Size:** All resulting files <500 LOC (enforced)
- **Test Count:** >= baseline count (no tests lost)
- **Coverage:** >=80% for unit tests
- **Performance:** Test suite execution time unchanged (+/- 10%)

## Testing Requirements

### Validation Checklist

```bash
# Pre-refactoring baseline
pytest tests/unit/test_ingestion.py tests/unit/test_model_selection_job.py --collect-only -q | tail -1 > test_count_baseline.txt
pytest tests/unit/ --cov=raglite > coverage_baseline.txt
python scripts/check_file_sizes.py --verbose > sizes_baseline.txt

# After each major split
pytest tests/unit/ -x  # Stop on first failure

# Final validation
pytest tests/unit/ --collect-only -q | tail -1  # AC-8.4a-1.2: Verify count >= baseline
pytest tests/unit/ --cov=raglite --cov-fail-under=80  # AC-8.4a-1.3: Verify coverage >=80%
python scripts/check_file_sizes.py  # AC-8.4a-1.5: Verify all files <500 LOC
pytest tests/unit/ -x  # AC-8.4a-1.4: Verify all tests pass
```

## Definition of Done

- [ ] All 5 acceptance criteria verified with passing tests
- [ ] Both original files split into modules <500 LOC each
- [ ] Test count >= baseline (no tests lost)
- [ ] Coverage >=80% maintained
- [ ] All unit tests pass
- [ ] Fixtures properly organized in conftest.py files
- [ ] `.file-size-exceptions` updated (entries removed for refactored files)
- [ ] All CI checks passing

## Dev Agent Record

### Context Reference

N/A (micro-story creation)

### Agent Model Used

- **Story Creation:** Claude Opus 4.5
- **Validation:** Claude Sonnet 4.5 (2 iterations)
- **ATDD Generation:** Claude Opus 4.5
- **Implementation:** Claude Sonnet 4.5
- **Code Review:** Claude Opus 4.5 (2 iterations)
- **Test Expansion:** Claude Sonnet 4.5
- **Test Quality Review:** Claude Haiku 4
- **Quality Gate:** Claude Opus 4.5

### Debug Log References

- Session: 2025-12-27 (epic-dev-full orchestrator)
- ATDD Checklist: docs/qa/atdd-checklist-story-8-4a-1.md
- ATDD Tests: tests/atdd/story_8_4a_1/

### Completion Notes List

**Phase 8 PASS - 2025-12-27**

- Scope correction: Reduced from 3 files to 2 files (test_timeseries_extract.py already refactored in Story 8.1)
- Files split: test_ingestion.py (1,817 LOC) → 13 files, test_model_selection_job.py (1,217 LOC) → 8 files
- Test count increased: 97 baseline → 224 tests (130% increase)
- Coverage maintained: 84% (exceeds 80% target)
- Quality gate: PASS (P0=100%, P1=100%)
- Quality score: 78/100 (B - Acceptable)

**Key Achievements:**
- All resulting files <500 LOC (max: 439 LOC)
- 22 ATDD tests generated (all passing acceptance criteria)
- 47 additional edge case tests added
- Shared fixtures consolidated in conftest.py files
- File size exceptions updated (.file-size-exceptions)

**Issues Fixed:**
- psycopg2 import errors resolved
- 16 placeholder tests removed
- pytestmark added to 17 test files
- Duplicate imports cleaned up
- Test failure in test_rules_edge_cases.py fixed

### File List

**Created (21 files):**

*Ingestion Tests (13 files):*
- tests/unit/ingestion/__init__.py
- tests/unit/ingestion/conftest.py (110 LOC - shared fixtures)
- tests/unit/ingestion/test_pdf_ingestion.py (439 LOC)
- tests/unit/ingestion/test_excel_processing.py
- tests/unit/ingestion/test_document_routing.py
- tests/unit/ingestion/test_chunking.py
- tests/unit/ingestion/test_embeddings.py (398 LOC)
- tests/unit/ingestion/test_vector_storage.py
- tests/unit/ingestion/test_module_integration.py
- tests/unit/ingestion/document_ingestion/test_temp_files_edge_cases.py (438 LOC)
- tests/unit/ingestion/document_ingestion/test_excel_edge_cases.py
- tests/unit/ingestion/document_ingestion/test_pdf_processing_edge_cases.py
- tests/unit/ingestion/adaptive_table/[various edge case test files]

*Model Selection Tests (8 files):*
- tests/unit/forecasting/model_selection/__init__.py
- tests/unit/forecasting/model_selection/conftest.py (100 LOC - shared fixtures)
- tests/unit/forecasting/model_selection/test_slash_command_subagent.py
- tests/unit/forecasting/model_selection/test_batch_functions.py (152 LOC)
- tests/unit/forecasting/model_selection/test_caching_reports.py (240 LOC)
- tests/unit/forecasting/model_selection/test_single_variable_core.py
- tests/unit/forecasting/model_selection/test_performance_errors.py
- tests/unit/forecasting/model_selection/test_edge_cases.py

**Deleted (2 files):**
- tests/unit/test_ingestion.py (1,817 LOC)
- tests/unit/test_model_selection_job.py (1,217 LOC)

**Modified:**
- .file-size-exceptions (removed entries for split files)

### Change Log

- 2025-12-27: Micro-story created (subset of Story 8.4a for critical priority files)
- 2025-12-27: Story scope corrected (3 files → 2 files, test_timeseries_extract.py already done)
- 2025-12-27: Phase 1-8 completed via epic-dev-full workflow
- 2025-12-27: Quality Gate PASS - Story marked done in sprint-status.yaml
