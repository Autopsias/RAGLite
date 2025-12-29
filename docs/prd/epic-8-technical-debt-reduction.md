# Epic 8: Technical Debt Reduction

**Status:** IN PROGRESS
**Sprint Change Proposal:** SCP-2025-12-25-001 APPROVED
**Test Design:** docs/test-design-epic-8.md

---

## Overview

### Goal
Reduce ALL files to <500 LOC for optimal AI comprehension and maintainability. This is a refactoring epic focused on file size reduction without changing functionality.

### Problem Statement
The RAGLite codebase has accumulated significant technical debt in file sizes, with **84 files exceeding the 500 LOC hard limit**:

| Category | Files | LOC Range | Total Excess LOC |
|----------|-------|-----------|------------------|
| **Production - Critical** | 7 | 1,000-3,178 | ~8,500 |
| **Production - Severe** | 6 | 750-1,000 | ~1,500 |
| **Production - Moderate** | 26 | 500-750 | ~4,000 |
| **Tests - Critical** | 6 | 1,000-1,817 | ~4,500 |
| **Tests - Severe** | 8 | 750-1,000 | ~2,000 |
| **Tests - Moderate** | 31 | 500-750 | ~4,500 |
| **TOTAL** | **84** | - | **~25,000** |

### Impact
1. **AI Comprehension:** Large files exceed LLM context windows, causing incomplete understanding and inconsistent edits
2. **Maintainability:** Files over 1000 LOC are difficult to navigate and understand
3. **Code Quality:** Violates project coding standards documented in `.claude/rules/file-size-limits.md`

---

## Success Criteria

1. **Zero files over 500 LOC** in production code
2. **Zero files over 500 LOC** in test code
3. **Test structure mirrors production** - each production module has corresponding test module
4. **80%+ test coverage** maintained
5. **All CI checks passing**
6. **`.file-size-exceptions` reduced to 0 entries**
7. **No orphaned tests** - all tests updated to import from new module locations

---

## Stories

### Story 8.1: Critical Forecasting Module Refactoring

**Goal:** Reduce worst 7 production files below 500 LOC

**Files to refactor:**
- `raglite/forecasting/timeseries_extract.py` (3,178 LOC -> 6-7 modules)
- `raglite/forecasting/hybrid.py` (2,780 LOC -> 5-6 modules)
- `tests/unit/test_timeseries_extract.py` (1,413 LOC)

**Acceptance Criteria:**
- AC1: All production files under 500 LOC
- AC2: All test files under 500 LOC
- AC3: 100% test coverage maintained
- AC4: All imports updated across codebase
- AC5: No circular dependencies
- AC6: Performance benchmarks unchanged
- AC7: Test file structure mirrors production module structure

**Risk Links:** R-002, R-003

---

### Story 8.2: External Data Client Refactoring

**Goal:** Reduce external data client files below 500 LOC

**Files to refactor:**
- `raglite/external_data/clients/basegov.py` (1,066 LOC)
- `raglite/external_data/clients/ecb.py` (1,033 LOC)
- `raglite/external_data/clients/eurostat.py` (957 LOC)
- `raglite/external_data/storage.py` (1,633 LOC)

**Acceptance Criteria:**
- AC1: All production files under 500 LOC
- AC2: All test files under 500 LOC
- AC3: Shared base class for common patterns
- AC4: Storage operations isolated and testable
- AC5: All health checks pass
- AC6: Test file structure mirrors production module structure

**Risk Links:** R-004, R-006

---

### Story 8.3: Ingestion Module Refactoring

**Goal:** Reduce ingestion module files below 500 LOC

**Files to refactor:**
- `raglite/ingestion/document_ingestion.py` (1,343 LOC -> 3-4 modules)
- `raglite/ingestion/adaptive_table/unit_inference.py` (1,205 LOC -> 3 modules)
- `raglite/ingestion/adaptive_table/core.py` (903 LOC -> 2 modules)

**Acceptance Criteria:**
- AC1: All production files under 500 LOC
- AC2: All test files under 500 LOC
- AC3: Ingestion pipeline performance unchanged
- AC4: Sample PDFs (3) re-ingestable successfully
- AC5: Test file structure mirrors production module structure

**Risk Links:** R-007

---

### Story 8.4: Test File Consolidation (UMBRELLA STORY)

**Note:** Story 8.4 has been broken down into sub-stories per `docs/stories/8-4-story-breakdown-recommendation.md`

**Sub-Stories:**
- **Story 8.4a:** Unit Test File Consolidation (~60 files, 2-3 days)
- **Story 8.4b:** Integration Test File Consolidation (~25 files, 1-2 days)
- **Story 8.4c:** ATDD/E2E Test File Consolidation (~11 files, 1-2 days)

---

#### Story 8.4a: Unit Test File Consolidation (UMBRELLA - BROKEN DOWN)

**Note:** Story 8.4a broken down into micro-stories due to scope (39 files, ~16,000 LOC)

**Micro-Stories:**
- **Story 8.4a-1:** Critical Unit Test Files (3 files, 4,447 LOC, 1-2 days)
- **Story 8.4a-2:** Severe Unit Test Files (5 files, 5,071 LOC, 1 day)
- **Story 8.4a-3:** Moderate Unit Test Files (31 files, ~10,000 LOC, 2-3 days)

---

##### Story 8.4a-1: Critical Unit Test Files

**Goal:** Split 3 critical priority unit test files (>1000 LOC) to <500 LOC each

**Files to refactor:**
- `tests/unit/test_ingestion.py` (1,817 LOC -> 4-5 files)
- `tests/unit/test_timeseries_extract.py` (1,413 LOC -> 3-4 files)
- `tests/unit/test_model_selection_job.py` (1,217 LOC -> 3-4 files)

**Acceptance Criteria:**
- AC1: All 3 files split into modules <500 LOC each
- AC2: Test count unchanged or increased
- AC3: Coverage maintained at 80%+
- AC4: All unit tests pass
- AC5: All resulting files <500 LOC verified

**Risk Links:** R-011

---

##### Story 8.4a-2: Severe Unit Test Files

**Goal:** Split 5 severe priority unit test files (750-1000 LOC) to <500 LOC each

**Files to refactor:**
- `tests/unit/test_proactive_insights.py` (1,128 LOC -> 3 files)
- `tests/unit/test_trend_analysis.py` (1,061 LOC -> 3 files)
- `tests/unit/test_model_selection_cache.py` (1,012 LOC -> 3 files)
- `tests/unit/test_strategic_recommendations.py` (949 LOC -> 2 files)
- `tests/unit/test_table_extraction.py` (921 LOC -> 2 files)

**Acceptance Criteria:**
- AC1: All 5 files split into modules <500 LOC each
- AC2: Test count unchanged or increased
- AC3: Coverage maintained at 80%+
- AC4: All unit tests pass
- AC5: All resulting files <500 LOC verified

**Risk Links:** R-011

---

##### Story 8.4a-3: Moderate Unit Test Files

**Goal:** Split 31 moderate priority unit test files (500-750 LOC) to <500 LOC each

**Files to refactor:** 31 unit test files (503-815 LOC each)

**Acceptance Criteria:**
- AC1: All 31 files split or refactored to <500 LOC each
- AC2: Test count unchanged or increased
- AC3: Coverage maintained at 80%+
- AC4: All unit tests pass
- AC5: All resulting files <500 LOC verified

**Risk Links:** R-011

---

#### Story 8.4b: Integration Test File Consolidation

**Goal:** Reduce all integration test files to <500 LOC

**Files to refactor:** ~25 integration test files
- `tests/integration/conftest.py` (1,411 LOC)
- Critical and severe priority integration test files

**Acceptance Criteria:**
- AC1: All integration test files under 500 LOC
- AC2: Test count unchanged or increased
- AC3: Coverage maintained at 80%+
- AC4: All integration tests pass
- AC5: Fixture dependencies preserved

**Risk Links:** R-011

---

#### Story 8.4c: ATDD/E2E Test File Consolidation

**Goal:** Reduce all ATDD and E2E test files to <500 LOC

**Files to refactor:** ~11 ATDD/E2E test files

**Acceptance Criteria:**
- AC1: All ATDD/E2E test files under 500 LOC
- AC2: Test count unchanged or increased
- AC3: All ATDD/E2E tests pass
- AC4: CI pipeline runs successfully

**Risk Links:** R-011

---

## Timeline Estimate

| Phase | Duration | Strategy |
|-------|----------|----------|
| Phase 1 (Story 8.1 - Critical) | 1-2 weeks | Sequential |
| Phase 2 (Story 8.2 - Severe) | 1 week | Partial parallelization |
| Phase 3 (Story 8.3 - Moderate) | 1-2 weeks | By module |
| Phase 4 (Story 8.4 - Tests) | 1-2 weeks | Independent |
| **Total** | **4-7 weeks** | - |

---

## Risk Summary

**High-Priority Risks (Score >=6):**
- R-002: Import breakage across hybrid.py dependencies
- R-003: Test coverage regression during forecasting module split
- R-007: PDF processing regression during document_ingestion.py split
- R-011: Fixture dependency issues during conftest.py refactoring
- R-013: Backward compatibility breaks across refactored modules
- R-015: **CRITICAL** - Production database corruption during testing

**Full risk details:** See `docs/test-design-epic-8.md`

---

## Dependencies

- **Epic 1-4:** DONE (no impact)
- **Epic 5:** BACKLOG (can incorporate refactoring)
- **Epic 6-7:** DONE (main source of debt)

---

## References

- Sprint Change Proposal: `docs/implementation-artifacts/sprint-change-proposal-2025-12-25.md`
- Test Design: `docs/test-design-epic-8.md`
- File Size Briefing: `docs/analysis/file-size-refactoring-briefing.md`
- Coding Standards: `.claude/rules/file-size-limits.md`
