# Story 8.4: Test File Consolidation

Status: ready-for-dev

## Story Header

- **Epic:** 8 - Technical Debt Reduction
- **Priority:** P0
- **Effort:** 5-7 days
- **Status:** ready-for-dev
- **Dependencies:** Story 8.1 (completed), Story 8.2 (completed), Story 8.3 (completed)
- **Risk Links:** R-011

## User Story

As a developer,
I want all test files split into modules under 500 LOC each,
so that AI tools can comprehend the full test context, test maintainability is improved, and fixture dependencies remain stable.

## Background

The test suite contains **45 test files exceeding the 500 LOC hard limit**. This story focuses on systematically splitting these files while maintaining test count, coverage, and CI stability.

### Current Test File Inventory (>500 LOC)

| Category | File | LOC | Target | Split Strategy |
|----------|------|-----|--------|----------------|
| **Critical (>1000 LOC)** | tests/unit/test_ingestion.py | 1,817 | <500 | Split by ingestion type (PDF, Excel, base64) |
| **Critical** | tests/unit/test_timeseries_extract.py | 1,413 | <500 | Split by extraction stage |
| **Critical** | tests/integration/test_forecast_query_integration.py | 1,231 | <500 | Split by query type |
| **Critical** | tests/unit/test_model_selection_job.py | 1,217 | <500 | Split by job phase |
| **Critical** | tests/integration/test_model_selection_cache_integration.py | 1,209 | <500 | Split by cache operation |
| **Critical** | tests/integration/test_ingestion_integration.py | ~~1,197~~ ✅ | <500 | Split by document type (COMPLETE) |
| **Severe (750-1000 LOC)** | tests/unit/test_proactive_insights.py | 1,128 | <500 | Split by insight type |
| **Severe** | tests/unit/test_trend_analysis.py | 1,061 | <500 | Split by trend type |
| **Severe** | tests/unit/test_model_selection_cache.py | 1,012 | <500 | Split by cache scenario |
| **Severe** | tests/unit/test_strategic_recommendations.py | 949 | <500 | Split by recommendation type |
| **Severe** | tests/unit/test_table_extraction.py | 921 | <500 | Split by table type |
| **Severe** | tests/unit/test_forecast_query_tool.py | 864 | <500 | Split by tool function |
| **Severe** | tests/unit/test_parallel_ingestion.py | 858 | <500 | Split by parallelism scenario |
| **Severe** | tests/integration/test_model_selection.py | 855 | <500 | Split by selection phase |
| **Moderate (500-750 LOC)** | 31 additional files | 500-750 | <500 | Split by logical grouping |

**Total test files >500 LOC:** 45 files
**Total excess LOC:** ~11,500 LOC above limit

### Impact

1. **AI Comprehension:** Large test files exceed LLM context windows
2. **Test Discovery:** Hard to find specific tests in 1000+ line files
3. **Fixture Isolation:** Large conftest files create hidden dependencies
4. **Maintenance:** Difficult to update tests without side effects

### Pattern from Stories 8.1-8.3

- Split by logical domain (type, phase, scenario)
- Create conftest.py files for shared fixtures
- Maintain test naming conventions
- Verify test discovery with `pytest --collect-only`
- Validate test count unchanged

## Acceptance Criteria

### AC-8.4.1: All Test Files Under 500 LOC

**Given** the 45 test files exceed 500 LOC
**When** the consolidation is complete
**Then** ALL resulting test modules are under 500 LOC each

**Verification:**
- Run `python scripts/check_file_sizes.py --verbose`
- All test files in `tests/` pass the 500 LOC check
- `.file-size-exceptions` has 0 entries for test files

### AC-8.4.2: Test Count Unchanged or Increased

**Given** the baseline test count before consolidation
**When** the consolidation is complete
**Then** test count is equal to or greater than baseline

**Verification:**
- Capture baseline: `pytest --collect-only -q | tail -1`
- Compare after: test count >= baseline
- No tests accidentally deleted or skipped
- All test files discoverable

### AC-8.4.3: Coverage Maintained at 80%+

**Given** the current test coverage of 80%+
**When** the consolidation is complete
**Then** coverage remains at 80% or higher

**Verification:**
- Run `pytest --cov=raglite --cov-fail-under=80`
- Coverage report shows no regression
- All critical modules maintain coverage

### AC-8.4.4: CI Pipeline Runs Successfully

**Given** the CI pipeline configuration
**When** the consolidation is complete
**Then** all CI jobs pass without errors

**Verification:**
- GitHub Actions workflow passes
- No import errors in any test file
- All fixtures resolve correctly
- No fixture dependency cycles

## Technical Specification

### Splitting Strategy by File Type

#### 1. Unit Test Files (Critical Priority)

**tests/unit/test_ingestion.py (1,817 LOC)**
Split into:
```
tests/unit/ingestion/
  __init__.py
  test_pdf_ingestion.py (~400 LOC)      # PDF processing tests
  test_excel_ingestion.py (~300 LOC)    # Excel processing tests
  test_base64_ingestion.py (~350 LOC)   # Base64/URL handling tests
  test_chunking.py (~400 LOC)           # Chunking strategy tests
  test_storage.py (~350 LOC)            # Storage operation tests
  conftest.py (~100 LOC)                # Shared fixtures
```

**tests/unit/test_timeseries_extract.py (1,413 LOC)**
Split into:
```
tests/unit/timeseries/
  test_extraction_core.py (~350 LOC)
  test_extraction_parsing.py (~350 LOC)
  test_extraction_metadata.py (~350 LOC)
  test_extraction_edge_cases.py (~350 LOC)
  conftest.py (~50 LOC)
```

#### 2. Integration Test Files (Critical Priority)

**tests/integration/test_forecast_query_integration.py (1,231 LOC)**
Split into:
```
tests/integration/forecasting/
  test_query_basic.py (~400 LOC)
  test_query_complex.py (~400 LOC)
  test_query_edge_cases.py (~400 LOC)
  conftest.py (~50 LOC)
```

**tests/integration/test_ingestion_integration.py (1,197 LOC)**
Split into:
```
tests/integration/ingestion/
  test_pdf_integration.py (~400 LOC)
  test_excel_integration.py (~300 LOC)
  test_batch_integration.py (~400 LOC)
  conftest.py (~100 LOC)
```

#### 3. Moderate Priority Files (500-750 LOC)

Use simple 2-way splits:
- Split by test class/function grouping
- Move related tests together
- Create minimal conftest.py if needed

### Fixture Consolidation Strategy

**Current Fixture Issues:**
- Fixtures scattered across multiple conftest.py files
- Hidden dependencies between fixtures
- Duplicate fixture definitions

**Solution:**
1. Audit all fixtures in scope
2. Identify shared vs. local fixtures
3. Create hierarchy:
   - `tests/conftest.py` - Global fixtures (session-scoped)
   - `tests/unit/conftest.py` - Unit test fixtures
   - `tests/integration/conftest.py` - Integration fixtures
   - `tests/unit/<module>/conftest.py` - Module-specific fixtures

### Test Discovery Validation

After each split, verify:
```bash
# Count tests before
pytest --collect-only -q | tail -1

# Run collection after split
pytest --collect-only -q tests/unit/<module>/

# Verify no collection errors
pytest --collect-only tests/unit/<module>/ 2>&1 | grep -i error
```

## Tasks

### Task 1: Baseline Capture [AC-8.4.2, AC-8.4.3, AC-8.4.4]

- [ ] 1.1 Capture test count: `pytest --collect-only -q | tail -1 > test_count_baseline.txt`
- [ ] 1.2 Capture coverage: `pytest --cov=raglite --cov-report=html > coverage_baseline.txt`
- [ ] 1.3 Document fixture dependency graph
- [ ] 1.4 List all test files >500 LOC with line counts
- [ ] 1.5 Run CI pipeline to confirm green baseline

### Task 2: Split Critical Unit Test Files (>1000 LOC) [AC-8.4.1]

- [ ] 2.1 Split `tests/unit/test_ingestion.py` (1,817 LOC)
  - [ ] 2.1.1 Create `tests/unit/ingestion/` directory
  - [ ] 2.1.2 Extract PDF tests to `test_pdf_ingestion.py`
  - [ ] 2.1.3 Extract Excel tests to `test_excel_ingestion.py`
  - [ ] 2.1.4 Extract base64 tests to `test_base64_ingestion.py`
  - [ ] 2.1.5 Extract chunking tests to `test_chunking.py`
  - [ ] 2.1.6 Extract storage tests to `test_storage.py`
  - [ ] 2.1.7 Create `conftest.py` for shared fixtures
  - [ ] 2.1.8 Verify all tests pass
  - [ ] 2.1.9 All files <500 LOC

- [ ] 2.2 Split `tests/unit/test_timeseries_extract.py` (1,413 LOC)
  - [ ] 2.2.1 Create `tests/unit/timeseries/` directory
  - [ ] 2.2.2 Split by extraction phase
  - [ ] 2.2.3 Create conftest.py for shared fixtures
  - [ ] 2.2.4 Verify all tests pass
  - [ ] 2.2.5 All files <500 LOC

- [ ] 2.3 Split `tests/unit/test_model_selection_job.py` (1,217 LOC)
  - [ ] 2.3.1 Split by job phase
  - [ ] 2.3.2 Verify all tests pass
  - [ ] 2.3.3 All files <500 LOC

- [ ] 2.4 Split `tests/unit/test_proactive_insights.py` (1,128 LOC)
  - [ ] 2.4.1 Split by insight type
  - [ ] 2.4.2 Verify all tests pass
  - [ ] 2.4.3 All files <500 LOC

- [ ] 2.5 Split `tests/unit/test_trend_analysis.py` (1,061 LOC)
  - [ ] 2.5.1 Split by trend type
  - [ ] 2.5.2 Verify all tests pass
  - [ ] 2.5.3 All files <500 LOC

- [ ] 2.6 Split `tests/unit/test_model_selection_cache.py` (1,012 LOC)
  - [ ] 2.6.1 Split by cache scenario
  - [ ] 2.6.2 Verify all tests pass
  - [ ] 2.6.3 All files <500 LOC

### Task 3: Split Critical Integration Test Files (>1000 LOC) [AC-8.4.1]

- [ ] 3.1 Split `tests/integration/test_forecast_query_integration.py` (1,231 LOC)
  - [ ] 3.1.1 Create `tests/integration/forecasting/` directory
  - [ ] 3.1.2 Split by query complexity
  - [ ] 3.1.3 Create conftest.py for shared fixtures
  - [ ] 3.1.4 Verify all tests pass
  - [ ] 3.1.5 All files <500 LOC

- [ ] 3.2 Split `tests/integration/test_model_selection_cache_integration.py` (1,209 LOC)
  - [ ] 3.2.1 Split by cache operation type
  - [ ] 3.2.2 Verify all tests pass
  - [ ] 3.2.3 All files <500 LOC

- [ ] 3.3 Split `tests/integration/test_ingestion_integration.py` (1,197 LOC)
  - [ ] 3.3.1 Create `tests/integration/ingestion/` directory
  - [ ] 3.3.2 Split by document type
  - [ ] 3.3.3 Verify all tests pass
  - [ ] 3.3.4 All files <500 LOC

### Task 4: Split Severe Priority Files (750-1000 LOC) [AC-8.4.1]

- [ ] 4.1 Split `tests/unit/test_strategic_recommendations.py` (949 LOC)
- [ ] 4.2 Split `tests/unit/test_table_extraction.py` (921 LOC)
- [ ] 4.3 Split `tests/unit/test_forecast_query_tool.py` (864 LOC)
- [ ] 4.4 Split `tests/unit/test_parallel_ingestion.py` (858 LOC)
- [ ] 4.5 Split `tests/integration/test_model_selection.py` (855 LOC)
- [ ] 4.6 Split `tests/integration/test_story_6_23_final_validation.py` (837 LOC)
- [ ] 4.7 Split `tests/validation/test_recommendation_alignment.py` (825 LOC)
- [ ] 4.8 Split `tests/unit/test_eurostat_indicators_edge_cases.py` (815 LOC)

### Task 5: Split Moderate Priority Files (500-750 LOC) [AC-8.4.1]

- [ ] 5.1 Process remaining 31 files systematically
- [ ] 5.2 Use 2-way splits for files 500-600 LOC
- [ ] 5.3 Use 3-way splits for files 600-750 LOC
- [ ] 5.4 Verify all tests pass after each batch
- [ ] 5.5 All files <500 LOC

### Task 6: Fixture Consolidation [AC-8.4.4]

- [ ] 6.1 Audit all fixtures in test files
- [ ] 6.2 Identify shared vs local fixtures
- [ ] 6.3 Consolidate shared fixtures to appropriate conftest.py
- [ ] 6.4 Remove duplicate fixture definitions
- [ ] 6.5 Verify fixture resolution with `pytest --collect-only`

### Task 7: Update `.file-size-exceptions` [AC-8.4.1]

- [ ] 7.1 Remove all test file entries from exceptions
- [ ] 7.2 Verify no test file exceptions remain
- [ ] 7.3 Run `python scripts/check_file_sizes.py --verbose`

### Task 8: Final Validation (MANDATORY) [All ACs]

- [ ] 8.1 Run `python scripts/check_file_sizes.py --verbose` - all tests <500 LOC
- [ ] 8.2 Verify test count: `pytest --collect-only -q | tail -1` >= baseline
- [ ] 8.3 Run `pytest --cov=raglite --cov-fail-under=80` - coverage maintained
- [ ] 8.4 Run full test suite: `pytest tests/` - all pass
- [ ] 8.5 Verify CI pipeline passes
- [ ] 8.6 No fixture resolution errors
- [ ] 8.7 `.file-size-exceptions` has 0 test entries

## Dev Notes

### Learnings from Stories 8.1-8.3

1. **Split by logical domain** - Tests for same feature stay together
2. **Shared fixtures in conftest.py** - Avoid duplication
3. **Validate after each split** - Catch issues early
4. **Test discovery verification** - Use `pytest --collect-only`
5. **Maintain test naming conventions** - `test_<module>_<scenario>.py`

### Risk Mitigation Strategies

**R-011: Fixture Dependency Issues (Score: 6)**
- Document fixture dependencies before refactoring
- Phased extraction: one fixture group at a time
- Validate fixture resolution after each extraction
- Test with `pytest --collect-only` to verify all tests discover

### Architecture References

- [Epic 8 PRD - Story 8.4](/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/prd/epic-8-technical-debt-reduction.md#story-84-test-file-consolidation)
- [Epic 8 Test Design - Story 8.4](/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/test-design-epic-8.md#story-84-test-file-consolidation)
- [File Size Limits Standards](/Users/ricardocarvalho/DeveloperFolder/RAGLite/.claude/rules/file-size-limits.md)
- [Story 8.3 Completed](/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/stories/8-3-ingestion-module-refactoring.md) - Pattern reference

**Epic 8 File Size Standards (from PRD):**
- **Hard Limit:** 500 LOC for ALL files (production and test)
- **Strategic Goal:** Zero files over 500 LOC across entire codebase
- **Quality Gate:** Enforced by `.file-size-exceptions` ratchet mechanism
- **Research-Based Thresholds:** Optimal AI comprehension at 100-250 LOC; must refactor at 400+ LOC
- **Enforcement:** Pre-commit hooks + CI validation block new violations
- **Test Mirror Principle:** Test file structure must mirror production module structure (Story 8.3, Dev Notes - "Existing Patterns to Follow" section, lines 347-362)

### Existing Patterns to Follow

**Test Directory Structure:**
```
tests/
  unit/
    <module>/
      __init__.py
      conftest.py        # Module-specific fixtures
      test_<feature1>.py
      test_<feature2>.py
  integration/
    <module>/
      __init__.py
      conftest.py
      test_<scenario1>.py
      test_<scenario2>.py
```

**Fixture Hierarchy:**
```
tests/conftest.py          # Global fixtures (session-scoped)
tests/unit/conftest.py     # Unit test fixtures
tests/integration/conftest.py  # Integration fixtures
tests/unit/<module>/conftest.py  # Module-specific fixtures
```

### Files to Split (Full List)

| Priority | File | LOC | Target Split |
|----------|------|-----|--------------|
| Critical | tests/unit/test_ingestion.py | 1,817 | 6 files |
| Critical | tests/unit/test_timeseries_extract.py | 1,413 | 4 files |
| Critical | tests/integration/test_forecast_query_integration.py | 1,231 | 3 files |
| Critical | tests/unit/test_model_selection_job.py | 1,217 | 3 files |
| Critical | tests/integration/test_model_selection_cache_integration.py | 1,209 | 3 files |
| Critical | tests/integration/test_ingestion_integration.py | 1,197 | 3 files |
| Severe | tests/unit/test_proactive_insights.py | 1,128 | 3 files |
| Severe | tests/unit/test_trend_analysis.py | 1,061 | 3 files |
| Severe | tests/unit/test_model_selection_cache.py | 1,012 | 3 files |
| Severe | tests/unit/test_strategic_recommendations.py | 949 | 2 files |
| Severe | tests/unit/test_table_extraction.py | 921 | 2 files |
| Severe | tests/unit/test_forecast_query_tool.py | 864 | 2 files |
| Severe | tests/unit/test_parallel_ingestion.py | 858 | 2 files |
| Severe | tests/integration/test_model_selection.py | 855 | 2 files |
| Moderate | 31 additional files | 500-750 | 2 files each |

### NFRs

- **File Size:** All test files <500 LOC (enforced)
- **Test Count:** >= baseline (no tests deleted)
- **Coverage:** Maintain 80%+ coverage
- **Fixture Stability:** No fixture resolution errors
- **CI Stability:** All CI jobs pass

## Testing Requirements

### Unit Tests

- All existing tests continue to pass
- Tests organized by module/feature
- Each test file <500 LOC
- Shared fixtures in conftest.py files

### Integration Tests

- All integration tests continue to pass
- Test organization mirrors unit test structure
- Fixture dependencies clearly documented

### Validation Checklist

```bash
# Pre-refactoring baseline
pytest --collect-only -q | tail -1 > test_count_baseline.txt
pytest --cov=raglite --cov-report=html > coverage_baseline.txt

# After each split batch
pytest -x  # Stop on first failure
python scripts/check_file_sizes.py --verbose

# Final validation
pytest --collect-only -q | tail -1  # Compare to baseline
pytest --cov=raglite --cov-fail-under=80  # Coverage check
pytest tests/  # Full test suite
python scripts/check_file_sizes.py  # File size check
```

## Definition of Done

- [ ] All 4 acceptance criteria verified with passing tests
- [ ] All 45 test files <500 LOC (0 exceptions for tests)
- [ ] Test count >= baseline (no tests lost)
- [ ] Coverage >= 80% maintained
- [ ] CI pipeline passes
- [ ] No fixture resolution errors
- [ ] `.file-size-exceptions` has 0 test file entries

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
