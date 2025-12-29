# Story 8.4 Breakdown Recommendation

**Original Story:** 8-4-test-file-consolidation
**Status:** Deferred for breakdown into manageable sub-stories
**Decision Date:** 2025-12-27
**Reason:** Story requires refactoring ~96 test files (5-7 day effort), too large for autonomous workflow execution

---

## Recommended Sub-Story Breakdown

### Story 8.4a: Unit Test File Consolidation

**Goal:** Reduce all unit test files to <500 LOC

**Scope:**
- Target: ~60 unit test files exceeding 500 LOC
- Key files: `tests/unit/test_ingestion.py` (1,817 LOC), `tests/unit/test_timeseries_extract.py` (1,413 LOC)
- Estimated effort: 2-3 days

**Acceptance Criteria:**
- AC1: All unit test files under 500 LOC
- AC2: Test count unchanged or increased
- AC3: Coverage maintained at 80%+
- AC4: All unit tests pass

**Dependencies:** Stories 8.1, 8.2, 8.3 (completed)

---

### Story 8.4b: Integration Test File Consolidation

**Goal:** Reduce all integration test files to <500 LOC

**Scope:**
- Target: ~25 integration test files exceeding 500 LOC
- Key file: `tests/integration/conftest.py` (1,411 LOC)
- Estimated effort: 1-2 days

**Acceptance Criteria:**
- AC1: All integration test files under 500 LOC
- AC2: Test count unchanged or increased
- AC3: Coverage maintained at 80%+
- AC4: All integration tests pass
- AC5: Fixture dependencies preserved

**Dependencies:** Story 8.4a (recommended, not required)

---

### Story 8.4c: ATDD/E2E Test File Consolidation

**Goal:** Reduce all ATDD and E2E test files to <500 LOC

**Scope:**
- Target: ~11 ATDD/E2E test files exceeding 500 LOC
- Estimated effort: 1-2 days

**Acceptance Criteria:**
- AC1: All ATDD/E2E test files under 500 LOC
- AC2: Test count unchanged or increased
- AC3: All ATDD/E2E tests pass
- AC4: CI pipeline runs successfully

**Dependencies:** Stories 8.4a, 8.4b (recommended for consistency)

---

## Original Story 8.4 Analysis

**Files Requiring Refactoring:** ~96 test files total
- **Unit tests:** ~60 files
- **Integration tests:** ~25 files
- **ATDD/E2E tests:** ~11 files

**Original Epic 8 Goal:** Zero files over 500 LOC in test code
**Breakdown Preserves Goal:** Yes - all sub-stories combined achieve original objective

---

## Implementation Strategy

### Phased Approach (Recommended)
1. **Phase 1:** Story 8.4a (unit tests) - establishes patterns
2. **Phase 2:** Story 8.4b (integration tests) - applies patterns
3. **Phase 3:** Story 8.4c (ATDD/E2E tests) - completes consolidation

### Parallel Approach (Alternative)
- Stories 8.4a, 8.4b, 8.4c can be executed in parallel if resources allow
- Each operates on different test directories
- Minimal risk of conflicts

---

## ATDD Tests Status

The ATDD tests generated for original Story 8.4 remain valid:
- **Location:** `tests/atdd/story_8_4/`
- **Checklist:** `docs/qa/atdd-checklist-story-8-4.md`
- **Tests:** 18 acceptance tests
- **Current Status:** 5/18 passing, 11/16 failing

**Recommendation:** Update ATDD tests to align with sub-story breakdown (or create separate ATDD tests for each sub-story).

---

## Next Steps

1. **Create Story 8.4a:** Use `/bmad:bmm:workflows:create-story` for unit test consolidation
2. **Create Story 8.4b:** Use `/bmad:bmm:workflows:create-story` for integration test consolidation
3. **Create Story 8.4c:** Use `/bmad:bmm:workflows:create-story` for ATDD/E2E test consolidation
4. **Execute Stories:** Run `/epic-dev-full 8` to process sub-stories through full workflow

---

## References

- Original Story: `docs/stories/8-4-test-file-consolidation.md`
- Epic 8 PRD: `docs/prd/epic-8-technical-debt-reduction.md`
- File Size Standards: `.claude/rules/file-size-limits.md`
- Sprint Status: `docs/implementation-artifacts/sprint-status.yaml`
