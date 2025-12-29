# Story 8.4a-2: Severe Priority Unit Test File Splitting

> **Note:** This is a micro-story of Story 8.4a (Unit Test File Consolidation). Story 8.4a was broken down due to scope issues (39 files requiring refactoring). This micro-story focuses on the 5 severe priority files (750-1000 LOC).

## Story Header

- **Epic:** 8 - Technical Debt Reduction
- **Parent Story:** 8.4a - Unit Test File Consolidation
- **Priority:** P0
- **Effort:** 1 day
- **Dependencies:** Story 8.4a-1 (recommended for consistency, not required)
- **Risk Links:** R-011

## User Story

As a developer,
I want the 5 severe priority unit test files (750-1000 LOC) split into modules under 500 LOC each,
so that AI tools can comprehend the full test context and test maintenance is improved.

## Background

Story 8.4a identified 39 unit test files exceeding 500 LOC. This micro-story addresses the 5 severe priority files that are between 750-1000 LOC:

| File | Current LOC | Target | Split Strategy |
|------|-------------|--------|----------------|
| `tests/unit/test_proactive_insights.py` | 1,128 | <500 each | Split into `tests/unit/insights/` directory (3 files) |
| `tests/unit/test_trend_analysis.py` | 1,061 | <500 each | Split into `tests/unit/insights/` or `tests/unit/forecasting/` (3 files) |
| `tests/unit/test_model_selection_cache.py` | 1,012 | <500 each | Split into `tests/unit/forecasting/model_selection/` (3 files) |
| `tests/unit/test_strategic_recommendations.py` | 949 | <500 each | Split into `tests/unit/insights/` directory (2 files) |
| `tests/unit/test_table_extraction.py` | 921 | <500 each | Split into `tests/unit/ingestion/` directory (2 files) |

**Total:** 5 files, 5,071 LOC to refactor

## Acceptance Criteria

### AC-8.4a-2.1: All 5 Files Split to <500 LOC Each

**Given** the 5 severe priority unit test files are between 750-1000 LOC
**When** the refactoring is complete
**Then** all resulting files are under 500 LOC each

**Verification:**
- Run `python scripts/check_file_sizes.py --verbose`
- All new test files pass the 500 LOC check
- Original files deleted or reduced to shim imports only

### AC-8.4a-2.2: Test Count Unchanged or Increased

**Given** `pytest tests/unit/test_proactive_insights.py tests/unit/test_trend_analysis.py tests/unit/test_model_selection_cache.py tests/unit/test_strategic_recommendations.py tests/unit/test_table_extraction.py --collect-only -q | tail -1` shows the current test count baseline from the 5 files
**When** the refactoring is complete
**Then** the total test count is unchanged or increased (no tests lost)

**Verification:**
- Run `pytest tests/unit/test_proactive_insights.py tests/unit/test_trend_analysis.py tests/unit/test_model_selection_cache.py tests/unit/test_strategic_recommendations.py tests/unit/test_table_extraction.py --collect-only -q | tail -1` before refactoring
- Run equivalent pytest on new locations after refactoring
- Count must be >= baseline count

### AC-8.4a-2.3: Coverage Maintained at 80%+

**Given** `pytest tests/unit/ --cov=raglite` shows the current coverage baseline for insights, forecasting, and ingestion modules
**When** the refactoring is complete
**Then** test coverage remains at or above 80%

**Verification:**
- Run `pytest tests/unit/ --cov=raglite --cov-fail-under=80`
- Coverage >= 80% maintained

### AC-8.4a-2.4: All Unit Tests Pass

**Given** all unit tests currently pass
**When** the refactoring is complete
**Then** all unit tests continue to pass

**Verification:**
- Run `pytest tests/unit/ -x` (stop on first failure)
- All tests pass
- No import errors or fixture issues

### AC-8.4a-2.5: All Resulting Files <500 LOC Verified

**Given** the file size limits are enforced by CI
**When** the refactoring is complete
**Then** all new test files are verified under 500 LOC by check_file_sizes.py

**Verification:**
- Run `python scripts/check_file_sizes.py`
- No new entries added to `.file-size-exceptions` for these files
- CI file size check passes

## Technical Specification

### Splitting Strategy

**1. test_proactive_insights.py (1,128 LOC) -> tests/unit/insights/**

```
tests/unit/insights/
  __init__.py
  conftest.py                      # Shared fixtures (mock metrics, insights data)
  test_insight_generation.py       # Core insight generation tests
  test_insight_types.py            # Tests by insight type (trend, anomaly, pattern)
  test_insight_formatting.py       # Output formatting and serialization tests
```

**2. test_trend_analysis.py (1,061 LOC) -> tests/unit/insights/ or tests/unit/forecasting/**

```
tests/unit/insights/  # or tests/unit/forecasting/ depending on where production code lives
  test_trend_detection.py          # Trend detection algorithm tests
  test_trend_classification.py     # Trend type classification tests
  test_trend_metrics.py            # Trend metrics calculation tests
```

**3. test_model_selection_cache.py (1,012 LOC) -> tests/unit/forecasting/model_selection/**

```
tests/unit/forecasting/model_selection/
  # (extends from Story 8.4a-1 if model_selection/ already exists)
  test_cache_storage.py            # Cache storage and retrieval tests
  test_cache_invalidation.py       # Cache invalidation and refresh tests
  test_cache_integration.py        # Integration with model selection tests
```

**4. test_strategic_recommendations.py (949 LOC) -> tests/unit/insights/**

```
tests/unit/insights/
  test_recommendation_engine.py    # Recommendation generation tests
  test_recommendation_ranking.py   # Ranking and prioritization tests
```

**5. test_table_extraction.py (921 LOC) -> tests/unit/ingestion/**

```
tests/unit/ingestion/
  # (extends from Story 8.4a-1 if ingestion/ already exists)
  test_table_detection.py          # Table detection tests
  test_table_parsing.py            # Table parsing and structure tests
```

### Fixture Management

1. **Root fixtures** remain in `tests/unit/conftest.py`
2. **Module fixtures** go to `tests/unit/<module>/conftest.py`
3. **Shared test utilities** go to `tests/unit/<module>/helpers.py` if needed
4. **Cross-module fixtures** should be promoted to root conftest.py

## Tasks

- [ ] Task 1: Baseline Capture [AC-8.4a-2.2, AC-8.4a-2.3, AC-8.4a-2.4]
  - [ ] 1.1 Record test count for 5 files
  - [ ] 1.2 Record coverage baseline: `pytest tests/unit/ --cov=raglite`
  - [ ] 1.3 Document current LOC for each file
  - [ ] 1.4 Check if any target directories already exist from Story 8.4a-1

- [ ] Task 2: Split test_proactive_insights.py (1,128 LOC) [AC-8.4a-2.1]
  - [ ] 2.1 Create `tests/unit/insights/` directory structure (if not exists)
  - [ ] 2.2 Create `tests/unit/insights/conftest.py` with shared fixtures
  - [ ] 2.3 Split by test class/feature: generation, types, formatting
  - [ ] 2.4 Update imports in all new files
  - [ ] 2.5 Verify tests pass: `pytest tests/unit/insights/ -v`
  - [ ] 2.6 Delete or convert original file to shim

- [ ] Task 3: Split test_trend_analysis.py (1,061 LOC) [AC-8.4a-2.1]
  - [ ] 3.1 Determine target directory (insights/ or forecasting/)
  - [ ] 3.2 Split by functionality: detection, classification, metrics
  - [ ] 3.3 Update imports in all new files
  - [ ] 3.4 Verify tests pass
  - [ ] 3.5 Delete or convert original file to shim

- [ ] Task 4: Split test_model_selection_cache.py (1,012 LOC) [AC-8.4a-2.1]
  - [ ] 4.1 Extend `tests/unit/forecasting/model_selection/` (if exists from 8.4a-1)
  - [ ] 4.2 Split by functionality: storage, invalidation, integration
  - [ ] 4.3 Update imports in all new files
  - [ ] 4.4 Verify tests pass
  - [ ] 4.5 Delete or convert original file to shim

- [ ] Task 5: Split test_strategic_recommendations.py (949 LOC) [AC-8.4a-2.1]
  - [ ] 5.1 Add to `tests/unit/insights/` directory
  - [ ] 5.2 Split by functionality: engine, ranking
  - [ ] 5.3 Update imports in all new files
  - [ ] 5.4 Verify tests pass
  - [ ] 5.5 Delete or convert original file to shim

- [ ] Task 6: Split test_table_extraction.py (921 LOC) [AC-8.4a-2.1]
  - [ ] 6.1 Add to `tests/unit/ingestion/` directory (if exists from 8.4a-1)
  - [ ] 6.2 Split by functionality: detection, parsing
  - [ ] 6.3 Update imports in all new files
  - [ ] 6.4 Verify tests pass
  - [ ] 6.5 Delete or convert original file to shim

- [ ] Task 7: File Size Validation [AC-8.4a-2.5]
  - [ ] 7.1 Run `python scripts/check_file_sizes.py --verbose`
  - [ ] 7.2 Verify all new files under 500 LOC
  - [ ] 7.3 Update `.file-size-exceptions` if needed (remove old entries)
  - [ ] 7.4 Document any exceptions with justification

- [ ] Task 8: Final Validation (MANDATORY) [All ACs]
  - [ ] 8.1 Verify test count >= baseline
  - [ ] 8.2 Run `pytest tests/unit/ -x` - all tests pass
  - [ ] 8.3 Run `pytest tests/unit/ --cov=raglite --cov-fail-under=80` - coverage maintained
  - [ ] 8.4 Run `python scripts/check_file_sizes.py` - all files pass
  - [ ] 8.5 Update sprint-status.yaml

## Dev Notes

### Risk Mitigation Strategies

**R-011: Fixture Dependency Issues (Score: 6)**
- Test fixtures before modifying files
- Use `pytest --fixtures` to map fixture dependencies
- Keep conftest.py files in appropriate scope
- Incremental refactoring with tests after each step

### Parallelization Opportunities

Files can be split in parallel if different developers work on different modules:
- insights/ tests (proactive_insights, trend_analysis, strategic_recommendations)
- model_selection/ tests (cache)
- ingestion/ tests (table_extraction)

### Existing Patterns to Follow

**From Story 8.1/8.4a-1 - Test Structure:**
```
tests/unit/<module>/
  __init__.py
  conftest.py              # Shared fixtures for module tests
  test_<feature>.py        # Feature-specific tests
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
- [Story 8.4a-1](docs/stories/8-4a-1-critical-unit-test-files.md) - Sibling micro-story (critical files)
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
pytest tests/unit/test_proactive_insights.py tests/unit/test_trend_analysis.py tests/unit/test_model_selection_cache.py tests/unit/test_strategic_recommendations.py tests/unit/test_table_extraction.py --collect-only -q | tail -1 > test_count_baseline.txt
pytest tests/unit/ --cov=raglite > coverage_baseline.txt
python scripts/check_file_sizes.py --verbose > sizes_baseline.txt

# After each major split
pytest tests/unit/ -x  # Stop on first failure

# Final validation
pytest tests/unit/ --collect-only -q | tail -1  # AC-8.4a-2.2: Verify count >= baseline
pytest tests/unit/ --cov=raglite --cov-fail-under=80  # AC-8.4a-2.3: Verify coverage >=80%
python scripts/check_file_sizes.py  # AC-8.4a-2.5: Verify all files <500 LOC
pytest tests/unit/ -x  # AC-8.4a-2.4: Verify all tests pass
```

## Definition of Done

- [ ] All 5 acceptance criteria verified with passing tests
- [ ] All 5 original files split into modules <500 LOC each
- [ ] Test count >= baseline (no tests lost)
- [ ] Coverage >=80% maintained
- [ ] All unit tests pass
- [ ] Fixtures properly organized in conftest.py files
- [ ] `.file-size-exceptions` updated (entries removed for refactored files)
- [ ] All CI checks passing

## Dev Agent Record

### Context Reference

Code review feedback for Story 8-4a-2 implementation requiring HIGH and MEDIUM priority fixes.

### Agent Model Used

- **Story Creation:** Claude Opus 4.5
- **Code Review Fixes:** Claude Sonnet 4.5

### Debug Log References

N/A

### Completion Notes List

**Code Review Fixes Applied (2025-12-27):**
- H1: Created missing `tests/unit/insights/__init__.py`
- H2: Created `tests/unit/insights/conftest.py` with shared fixtures (sample_anomalies, sample_trends, sample_forecasts, sample_risk_insight, sample_opportunity_insight, sample_anomaly_insight, sample_trend_insight)
- H3: Updated Dev Agent Record with implementation details
- M1: Extracted TestEdgeCases and TestStructuredLogging from test_insight_workflow.py (499 LOC) to test_insight_edge_cases.py (brings workflow file under 500 LOC)
- M2: Added pytestmark = [pytest.mark.unit] to 8 test files (test_insight_models.py, test_insight_helpers.py, test_insight_synthesis.py, test_insight_workflow.py, test_insight_edge_cases.py, test_recommendation_generation.py, test_recommendation_helpers.py, test_recommendation_edge_cases.py)
- M3: Removed duplicate fixtures from test_recommendation_models.py (now use conftest.py fixtures)
- M3: Updated test_insight_workflow.py to use conftest.py fixtures instead of local duplicates

### File List

**Created:**
- tests/unit/insights/__init__.py
- tests/unit/insights/conftest.py
- tests/unit/insights/test_insight_edge_cases.py

**Modified:**
- tests/unit/insights/test_insight_workflow.py (reduced from 499 LOC by extracting edge cases)
- tests/unit/insights/test_insight_models.py (added pytestmark)
- tests/unit/insights/test_insight_helpers.py (added pytestmark)
- tests/unit/insights/test_insight_synthesis.py (added pytestmark)
- tests/unit/insights/test_recommendation_generation.py (added pytestmark)
- tests/unit/insights/test_recommendation_helpers.py (added pytestmark)
- tests/unit/insights/test_recommendation_models.py (added pytestmark, removed duplicate fixtures)
- tests/unit/insights/test_recommendation_edge_cases.py (added pytestmark)
- docs/stories/8-4a-2-severe-unit-test-files.md (this file - Dev Agent Record)

### Change Log

- 2025-12-27: Micro-story created (subset of Story 8.4a for severe priority files)
- 2025-12-27: Code review fixes applied (H1-H3, M1-M3) for insights test module organization
