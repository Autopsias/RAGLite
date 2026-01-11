# Story 8.4a: Unit Test File Consolidation

> **Note:** This is a sub-story of Story 8.4 (Test File Consolidation) per the breakdown recommendation in `docs/stories/8-4-story-breakdown-recommendation.md`. Story 8.4 was split due to large scope (~96 test files) into sub-stories 8.4a (unit tests), 8.4b (integration tests), and 8.4c (e2e tests).

## Story Header

- **Epic:** 8 - Technical Debt Reduction
- **Priority:** P0
- **Effort:** 2-3 days
- **Dependencies:** Stories 8.1, 8.2, 8.3 (completed)
- **Risk Links:** R-011

## User Story

As a developer,
I want all unit test files reduced to under 500 LOC each,
so that AI tools can comprehend the full test context and maintainability is improved.

## Background

Story 8.4 (Test File Consolidation) was broken down into sub-stories due to its large scope (~96 test files requiring refactoring). This sub-story focuses specifically on unit test files.

**Current State:**
From `.file-size-exceptions`, the following unit test files exceed 500 LOC:

| File | Current LOC | Target | Priority |
|------|-------------|--------|----------|
| `tests/unit/test_ingestion.py` | 1,817 | <500 | Critical |
| `tests/unit/test_timeseries_extract.py` | 1,413 | <500 | Critical |
| `tests/unit/test_model_selection_job.py` | 1,217 | <500 | Critical |
| `tests/unit/test_proactive_insights.py` | 1,128 | <500 | Severe |
| `tests/unit/test_trend_analysis.py` | 1,061 | <500 | Severe |
| `tests/unit/test_model_selection_cache.py` | 1,012 | <500 | Severe |
| `tests/unit/test_strategic_recommendations.py` | 949 | <500 | Severe |
| `tests/unit/test_table_extraction.py` | 921 | <500 | Severe |
| `tests/unit/test_forecast_query_tool.py` | 864 | <500 | Moderate |
| `tests/unit/test_parallel_ingestion.py` | 858 | <500 | Moderate |
| `tests/unit/test_eurostat_indicators_edge_cases.py` | 815 | <500 | Moderate |
| `tests/unit/test_anomaly_detection.py` | 811 | <500 | Moderate |
| `tests/unit/test_housing_transactions.py` | 767 | <500 | Moderate |
| `tests/unit/test_multi_metric_validation.py` | 760 | <500 | Moderate |
| `tests/unit/test_model_selection_utils.py` | 750 | <500 | Moderate |
| `tests/unit/test_arima_model.py` | 745 | <500 | Moderate |
| `tests/unit/test_eurostat_indicators.py` | 718 | <500 | Moderate |
| `tests/unit/test_story_7_4_expanded_coverage.py` | 661 | <500 | Moderate |
| `tests/unit/test_retrieval.py` | 653 | <500 | Moderate |
| `tests/unit/test_safety_guard.py` | 624 | <500 | Moderate |
| `tests/unit/test_arima_ets_models_expanded.py` | 611 | <500 | Moderate |
| `tests/unit/test_mcp_model_routing.py` | 595 | <500 | Moderate |
| `tests/unit/test_auto_update.py` | 568 | <500 | Moderate |
| `tests/unit/test_standard_layouts.py` | 560 | <500 | Moderate |
| `tests/unit/test_catboost_integration.py` | 555 | <500 | Moderate |
| `tests/unit/test_phase2_centralized_validation.py` | 554 | <500 | Moderate |
| `tests/unit/test_hybrid_search.py` | 553 | <500 | Moderate |
| `tests/unit/test_proactive_insights_mcp.py` | 551 | <500 | Moderate |
| `tests/unit/test_unit_inference.py` | 550 | <500 | Moderate |
| `tests/unit/test_story_6_23_validation_unit.py` | 542 | <500 | Moderate |
| `tests/unit/test_ets_model.py` | 541 | <500 | Moderate |
| `tests/unit/test_ecb_macroeconomic.py` | 539 | <500 | Moderate |
| `tests/unit/test_scripts_accuracy_utils.py` | 533 | <500 | Moderate |
| `tests/unit/test_synthesis_agent.py` | 523 | <500 | Moderate |
| `tests/unit/test_ensemble_forecasting.py` | 520 | <500 | Moderate |
| `tests/unit/test_regressor_config_story_6_16.py` | 512 | <500 | Moderate |
| `tests/unit/test_base64_ingestion.py` | 512 | <500 | Moderate |
| `tests/unit/external_data/test_refactoring_acceptance.py` | 507 | <500 | Moderate |
| `tests/unit/test_scheduler.py` | 503 | <500 | Moderate |

**Total:** 39 unit test files exceeding 500 LOC

**Impact:**
- Large test files exceed LLM context windows, causing incomplete understanding
- Test maintenance becomes difficult with monolithic files
- Related tests are harder to locate and understand

## Acceptance Criteria

### AC-8.4a.1: All Unit Test Files Under 500 LOC

**Given** the unit test files in `tests/unit/` exceed 500 LOC
**When** the refactoring is complete
**Then** ALL unit test files are under 500 LOC each

**Verification:**
- Run `python scripts/check_file_sizes.py --verbose`
- All `tests/unit/` files pass the 500 LOC check
- No new entries added to `.file-size-exceptions` for unit tests

### AC-8.4a.2: Test Count Unchanged or Increased

**Given** the current test count baseline
**When** the refactoring is complete
**Then** the total test count is unchanged or increased (no tests lost)

**Verification:**
- Run `pytest tests/unit/ --collect-only -q | tail -1` before and after
- Count must be >= baseline count
- No test functions removed (only reorganized)

### AC-8.4a.3: Coverage Maintained at 80%+

**Given** the current coverage baseline for unit tests
**When** the refactoring is complete
**Then** test coverage remains at or above 80%

**Verification:**
- Run `pytest tests/unit/ --cov=raglite --cov-fail-under=80`
- Coverage >= 80% maintained
- No untested code paths introduced during refactoring

### AC-8.4a.4: All Unit Tests Pass

**Given** all unit tests currently pass
**When** the refactoring is complete
**Then** all unit tests continue to pass

**Verification:**
- Run `pytest tests/unit/ -x` (stop on first failure)
- All tests pass
- No import errors or fixture issues

## Technical Specification

### Splitting Strategy

**Priority 1 - Critical Files (>1000 LOC):**
```
tests/unit/
  ingestion/
    test_document_ingestion.py      # Core ingestion tests
    test_pdf_processing.py          # PDF-specific tests
    test_excel_processing.py        # Excel-specific tests
    test_chunking.py                # Chunking tests
    conftest.py                     # Shared fixtures
  forecasting/
    timeseries/                     # Already split in Story 8.1
    model_selection/
      test_job.py                   # From test_model_selection_job.py
      test_cache.py                 # From test_model_selection_cache.py
      test_utils.py                 # From test_model_selection_utils.py
      conftest.py                   # Shared fixtures
```

**Priority 2 - Severe Files (750-1000 LOC):**
- Split by test class or feature area
- Extract shared fixtures to conftest.py files
- Group related tests into subdirectories

**Priority 3 - Moderate Files (500-750 LOC):**
- Minor splits or fixture extraction
- May require only removing duplication

### Split Patterns

| Original File | Split Strategy | New Structure |
|---------------|----------------|---------------|
| `test_ingestion.py` (1,817) | By ingestion type | `ingestion/test_*.py` (4-5 files) |
| `test_model_selection_job.py` (1,217) | By functionality | `model_selection/test_job*.py` (2-3 files) |
| `test_proactive_insights.py` (1,128) | By insight type | `insights/test_*.py` (3 files) |
| `test_trend_analysis.py` (1,061) | By analysis type | `trend/test_*.py` (2-3 files) |

### Fixture Management

1. **Root fixtures** remain in `tests/unit/conftest.py`
2. **Subdirectory fixtures** go to `tests/unit/<module>/conftest.py`
3. **Shared test utilities** go to `tests/unit/<module>/helpers.py`

## Tasks

- [ ] Task 1: Baseline Capture [AC-8.4a.2, AC-8.4a.3, AC-8.4a.4]
  - [ ] 1.1 Run `pytest tests/unit/ --collect-only -q | tail -1` - record test count
  - [ ] 1.2 Run `pytest tests/unit/ --cov=raglite` - record coverage baseline
  - [ ] 1.3 Document all unit test files exceeding 500 LOC
  - [ ] 1.4 Create backup of files being refactored

- [ ] Task 2: Priority 1 - Critical Files [AC-8.4a.1]
  - [ ] 2.1 Split `test_ingestion.py` (1,817 LOC) into ingestion/ subdirectory
  - [ ] 2.2 Split `test_model_selection_job.py` (1,217 LOC) into model_selection/ subdirectory
  - [ ] 2.3 Verify tests pass after each split
  - [ ] 2.4 Update imports and fixtures as needed

- [ ] Task 3: Priority 2 - Severe Files [AC-8.4a.1]
  - [ ] 3.1 Split `test_proactive_insights.py` (1,128 LOC)
  - [ ] 3.2 Split `test_trend_analysis.py` (1,061 LOC)
  - [ ] 3.3 Split `test_model_selection_cache.py` (1,012 LOC)
  - [ ] 3.4 Split `test_strategic_recommendations.py` (949 LOC)
  - [ ] 3.5 Split `test_table_extraction.py` (921 LOC)
  - [ ] 3.6 Verify tests pass after each split

- [ ] Task 4: Priority 3 - Moderate Files [AC-8.4a.1]
  - [ ] 4.1 Refactor files 800-900 LOC (4 files)
  - [ ] 4.2 Refactor files 700-800 LOC (5 files)
  - [ ] 4.3 Refactor files 600-700 LOC (5 files)
  - [ ] 4.4 Refactor files 500-600 LOC (15 files)
  - [ ] 4.5 Verify tests pass after each batch

- [ ] Task 5: Fixture Consolidation [AC-8.4a.4]
  - [ ] 5.1 Extract common fixtures to subdirectory conftest.py files
  - [ ] 5.2 Remove duplicate fixture definitions
  - [ ] 5.3 Verify fixture availability across test modules
  - [ ] 5.4 Update imports to use shared fixtures

- [ ] Task 6: File Size Validation [AC-8.4a.1]
  - [ ] 6.1 Run `python scripts/check_file_sizes.py --verbose`
  - [ ] 6.2 Verify all unit test files under 500 LOC
  - [ ] 6.3 Remove unit test entries from `.file-size-exceptions`
  - [ ] 6.4 Document any exceptions with justification

- [ ] Task 7: Final Validation (MANDATORY) [All ACs]
  - [ ] 7.1 Run `pytest tests/unit/ --collect-only -q | tail -1` - verify test count >= baseline
  - [ ] 7.2 Run `pytest tests/unit/ -x` - all tests pass
  - [ ] 7.3 Run `pytest tests/unit/ --cov=raglite --cov-fail-under=80` - coverage maintained
  - [ ] 7.4 Run `python scripts/check_file_sizes.py` - all files pass
  - [ ] 7.5 Update sprint-status.yaml

## Dev Notes

### Risk Mitigation Strategies

**R-011: Fixture Dependency Issues (Score: 6)**
- Test fixtures before modifying files
- Use `pytest --fixtures` to map fixture dependencies
- Keep conftest.py files in appropriate scope
- Incremental refactoring with tests after each step

### Extraction Order

1. **Extract largest files first** - biggest impact on AI comprehension
2. **Group by module** - tests for same production module together
3. **Extract fixtures after splitting** - avoid duplicate fixtures
4. **Run tests frequently** - catch issues early

### Parallelization Opportunities

Files can be split in parallel by priority group:
- Priority 1 files can be split concurrently
- Priority 2 files can be split concurrently
- Priority 3 files can be split concurrently

### Architecture References

- [Epic 8 PRD - Story 8.4](docs/prd/epic-8-technical-debt-reduction.md#Story-8.4)
- [Story 8.4 Breakdown Recommendation](docs/stories/8-4-story-breakdown-recommendation.md) - Validates sub-story split from Epic 8.4
- [File Size Limits Standards](.claude/rules/file-size-limits.md) - Research-backed thresholds and enforcement
- [Test Organization Patterns](docs/architecture/6-complete-reference-implementation.md#testing) - Standard test structure
- [Story 8.1 Reference](docs/stories/8-1-critical-forecasting-module-refactoring.md) - Proven patterns for test splitting (module -> subdirectories with conftest.py)

### Existing Patterns to Follow

**Test Structure Pattern (from Story 8.1):**
```
tests/unit/forecasting/
  timeseries/
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

### NFRs

- **File Size:** All unit test files <500 LOC (enforced)
- **Test Count:** >= baseline count (no tests lost)
- **Coverage:** >=80% for unit tests
- **Performance:** Test suite execution time unchanged (+/- 10%)
- **Fixture Scope:** Appropriate conftest.py placement

## Testing Requirements

### Validation Checklist

```bash
# Pre-refactoring baseline (AC-8.4a.2, AC-8.4a.3)
pytest tests/unit/ --collect-only -q | tail -1 > test_count_baseline.txt
pytest tests/unit/ --cov=raglite > coverage_baseline.txt
python scripts/check_file_sizes.py --verbose > sizes_baseline.txt

# After each major split (AC-8.4a.4)
pytest tests/unit/ -x  # Stop on first failure

# Final validation
pytest tests/unit/ --collect-only -q | tail -1  # AC-8.4a.2: Verify count >= baseline
pytest tests/unit/ --cov=raglite --cov-fail-under=80  # AC-8.4a.3: Verify coverage >=80%
python scripts/check_file_sizes.py  # AC-8.4a.1: Verify all files <500 LOC
pytest tests/unit/ -x  # AC-8.4a.4: Verify all tests pass
```

## Definition of Done

- [ ] All 4 acceptance criteria verified with passing tests
- [ ] All unit test files <500 LOC (verified by check_file_sizes.py)
- [ ] Test count >= baseline (no tests lost)
- [ ] Coverage >=80% maintained
- [ ] All unit tests pass
- [ ] Fixtures properly organized in conftest.py files
- [ ] `.file-size-exceptions` updated (unit test entries removed)
- [ ] All CI checks passing

## Dev Agent Record

### Context Reference

N/A (epic-dev-full workflow - direct implementation)

### Agent Model Used

- **Story Creation:** Claude Opus 4.5

### Debug Log References

N/A

### Completion Notes List

N/A

### File List

N/A

### Change Log

- 2025-12-27: Story created via create-story workflow (sub-story of 8.4)
