# Story 3.0.1: Refactor Modules to Size Limits

**Status:** ready-for-dev
**Epic:** Epic 3 - AI Intelligence & Orchestration (Prep Sprint)
**Priority:** 🔴 CRITICAL (Blocks Epic 3 feature implementation)
**Effort:** 2-3 days
**Owner:** Charlie (Dev) + Winston (Architect Review)
**Validated:** 2025-11-05 by Bob (Scrum Master) - All validation issues fixed

## Story

As a **developer preparing for Epic 3**,
I want **all Python files refactored to <1000 lines**,
so that **Epic 3 agentic orchestration code is maintainable and debuggable**.

## Context

**From Epic 2 Retrospective (2025-11-05):**

Ricardo (Project Lead) identified code quality debt: "Files exceeding 1000-1500 lines will bite us in the future."

**Root Cause:**
- Epic 2 focused on feature delivery without enforcing module size constraints
- No hard limits in architecture review checklist
- Some files grew beyond maintainable size during implementation

**Impact on Epic 3:**
- Agentic orchestration adds complexity (multi-agent workflows, state management)
- Debugging large modules with agent interactions = maintenance nightmare
- Refactoring now prevents Epic 3 pain

**Strategic Decision:**
- Address technical debt BEFORE Epic 3 implementation
- Clean start for complex agentic features
- Establish module size enforcement for future epics

## Acceptance Criteria

### AC1: Identify Oversized Files (2 hours)

**Goal:** Scan codebase and identify all files >1000 lines

**Technical Approach:**

```bash
# Scan raglite/ directory for oversized files
find raglite -name "*.py" -exec wc -l {} \; | sort -rn | head -20

# Generate report with standardized format
python scripts/identify-oversized-files.py > docs/refactoring/oversized-files-report.txt
```

**Report Format:**
```
File Path | Line Count | Epic 3 Relevance | Priority
raglite/retrieval/query_classifier.py | 1500 | HIGH | 1
raglite/ingestion/pipeline.py | 1200 | MEDIUM | 2
```

**Success Criteria:**
- ✅ Complete list of files >1000 lines identified
- ✅ Files prioritized by Epic 3 impact (e.g., retrieval/ modules critical)
- ✅ Report saved: `docs/refactoring/oversized-files-report.txt`
- ✅ **Validation:** Verify scan completeness with `find raglite -name "*.py" | wc -l` (compare to report total)

### AC2: Define Refactoring Strategy (2 hours)

**Goal:** Plan how to split oversized modules by domain/responsibility

**Technical Approach:**

For each oversized file:
1. Identify logical boundaries (domain separation)
2. Define new module names (maintain single responsibility)
3. Plan import updates

**Example Strategy:**

```
IF: raglite/retrieval/query_classifier.py is 1500 lines
THEN split into:
  - raglite/retrieval/query_classification/entity_matching.py (300 lines)
  - raglite/retrieval/query_classification/period_mapping.py (200 lines)
  - raglite/retrieval/query_classification/sql_generation.py (500 lines)
  - raglite/retrieval/query_classification/classifier.py (400 lines - orchestrator)
```

**Success Criteria:**
- ✅ Refactoring plan documented for each oversized file
- ✅ New module boundaries defined (single responsibility principle)
- ✅ Winston architecture review approves strategy
- ✅ **Validation:** Winston approval documented in `docs/refactoring/winston-approval-3.0.1.md` or as PR comment

**Files Created:**
- `docs/refactoring/refactoring-strategy.md` (refactoring plan)

### AC3: Execute Refactoring (1-2 days)

**Goal:** Split oversized modules and maintain 100% test coverage

**Technical Approach:**

1. **For each file to refactor:**
   - Create new focused modules
   - Move functions/classes to appropriate modules
   - Update imports across codebase
   - Run pytest after each change (verify 100% pass)

2. **Refactoring Checklist (per file):**
   - [ ] Create new module structure
   - [ ] Move code to new modules
   - [ ] Update imports
   - [ ] Run `pytest` (verify all tests pass)
   - [ ] Run `pytest --cov` (verify coverage maintained)
   - [ ] Verify no file >1000 lines remains

3. **Safety Protocol:**
   - One file at a time (minimize risk)
   - Run full test suite after each refactor
   - Commit after each successful refactor (rollback safety)

**Success Criteria:**
- ✅ All files <1000 lines
- ✅ 100% test pass rate maintained (no regressions)
- ✅ Test coverage maintained: `pytest --cov=raglite` ≥**[BASELINE: Run at story start to establish %]**
- ✅ Integration tests pass: `pytest tests/integration/`
- ✅ Code functionality unchanged (refactor only, no features)
- ✅ **Test Failure Protocol:** If pytest fails → rollback last change, debug, retry
  - Use `pytest --exitfirst` for immediate failure detection
- ✅ **Performance Check (Optional):** Verify test suite runtime unchanged (within ±10% of baseline)

**Files Modified:**
- Oversized files split into focused modules
- Import statements updated across codebase

### AC4: Architecture Review & Approval (1 hour)

**Goal:** Winston verifies module cohesion and Epic 3 readiness

**Technical Approach:**

Winston reviews:
1. Module boundaries (single responsibility maintained)
2. Import dependencies (no circular dependencies)
3. Test coverage (no gaps introduced)
4. Epic 3 readiness (clean codebase for agentic features)

**Success Criteria:**
- ✅ Winston architecture approval documented in `docs/refactoring/winston-approval-3.0.1.md`
- ✅ No files >1000 lines in `raglite/` directory
- ✅ No circular dependencies introduced (verify with `pydeps raglite` if needed)
- ✅ Epic 3 Stories 3.1+ unblocked

## Tasks / Subtasks

### Task 1: Identify Oversized Files (AC1) - 2 hours

- [x] **Subtask 1.0:** Create output directory
  ```bash
  mkdir -p docs/refactoring
  ```

- [x] **Subtask 1.1:** Scan `raglite/` directory for files >1000 lines
  ```bash
  find raglite -name "*.py" -exec wc -l {} \; | sort -rn | head -20
  ```
  **Result:** 2 files identified (adaptive_table_extraction.py: 3109 lines, pipeline.py: 2302 lines)

- [x] **Subtask 1.2:** Create identification script
  - Script: `scripts/identify-oversized-files.py`
  - Output: List of files with line counts
  - Prioritize by Epic 3 impact
  **Completed:** Script created with comprehensive reporting

- [x] **Subtask 1.3:** Generate report
  - Save to: `docs/refactoring/oversized-files-report.txt`
  - Include: file path, line count, Epic 3 relevance
  **Completed:** Report generated, shows 2 critical files (5,411 lines total)

### Task 2: Define Refactoring Strategy (AC2) - 2 hours

- [x] **Subtask 2.1:** Analyze each oversized file
  - Identify logical domain boundaries
  - Plan module split strategy
  **Completed:** Comprehensive analysis done - 9 new focused modules planned

- [x] **Subtask 2.2:** Document refactoring plan
  - Create: `docs/refactoring/refactoring-strategy.md`
  - For each file: old structure → new structure
  - Example module names and responsibilities
  **Completed:** 9,600-word strategy document created with detailed refactoring plan

- [ ] **Subtask 2.3:** ⏸️ **BLOCKED - Winston architecture review**
  - Present refactoring strategy
  - Get approval before execution
  **Status:** Awaiting Winston/Ricardo approval of `docs/refactoring/refactoring-strategy.md`

### Task 3: Execute Refactoring (AC3) - 1-2 days

- [ ] **Subtask 3.1:** Create new module directories (if needed)
  - Example: `raglite/retrieval/query_classification/`

- [ ] **Subtask 3.2:** Refactor File 1 (highest priority)
  - Create new focused modules
  - Move code
  - Update imports
  - Run `pytest` (verify pass)

- [ ] **Subtask 3.3:** Refactor File 2
  - Repeat process
  - Commit after success

- [ ] **Subtask 3.4:** Refactor File N (all remaining files)
  - Continue until all files <1000 lines

- [ ] **Subtask 3.5:** Final validation
  - Run full test suite: `pytest`
  - Check coverage: `pytest --cov=raglite`
  - Verify no file >1000 lines

### Task 4: Architecture Review (AC4) - 1 hour

- [ ] **Subtask 4.1:** Winston reviews refactored codebase
  - Module cohesion check
  - Import dependency check
  - Test coverage verification

- [ ] **Subtask 4.2:** Document approval
  - Winston signs off
  - Epic 3 Stories 3.1+ unblocked

## Dev Notes

### Refactoring Principles

**KISS Principle:**
- Split by domain/responsibility, not by arbitrary line counts
- Maintain single responsibility per module
- No over-engineering (no new abstractions)

**Safety First:**
- One file at a time
- Full test suite after each refactor
- Commit after each success (rollback safety)

**Epic 3 Focus:**
- Prioritize `raglite/retrieval/` modules (agentic workflows will use these)
- Clean module boundaries enable multi-agent coordination

### Module Size Guidelines

**Hard Limits (enforced going forward):**
- ⚠️ Warning at 800 lines
- ❌ Error at 1000 lines
- 🎯 Target: Most files 200-400 lines

**When to Split:**
- File approaches 800 lines → Plan refactor
- File exceeds 1000 lines → Immediate refactor required

### Testing Standards

**Test Coverage Maintenance:**
- Run `pytest` after every module split
- Verify 100% test pass rate
- Check coverage: `pytest --cov=raglite`

**No Functionality Changes:**
- Refactor only (move code, don't modify behavior)
- If tests fail, refactor introduced bug → rollback and retry

### References

**Source Documents:**
- [Epic 2 Retrospective](docs/retrospectives/epic-2-retro-2025-11-05.md) - Code quality debt identified
- [Epic 3 Prep Tech Spec](docs/tech-spec-epic-3-prep.md) - Refactoring strategy
- [Action Item 2](docs/retrospectives/epic-2-retro-2025-11-05.md#action-item-2-code-quality-module-size-enforcement) - Module size enforcement

## Definition of Done

**This story is considered DONE when ALL of the following are complete:**

### 1. Code Quality
- [ ] All files in `raglite/` are <1000 lines (verified via script: `find raglite -name "*.py" -exec wc -l {} \; | sort -rn | head -1`)
- [ ] No circular dependencies introduced (verify with `pydeps raglite` if needed)
- [ ] Module boundaries follow single responsibility principle (Winston-approved)
- [ ] No files >1000 lines remain in any directory

### 2. Testing
- [ ] 100% test pass rate: `uv run pytest` (all tests green)
- [ ] Test coverage maintained: `uv run pytest --cov=raglite` (≥baseline % established at story start)
- [ ] Integration tests pass: `uv run pytest tests/integration/`
- [ ] No test runtime regression (within ±10% of baseline, optional check)

### 3. Documentation
- [ ] Refactoring strategy documented: `docs/refactoring/refactoring-strategy.md` exists and complete
- [ ] Oversized files report generated: `docs/refactoring/oversized-files-report.txt` exists
- [ ] Winston architecture approval documented: `docs/refactoring/winston-approval-3.0.1.md` or PR comment

### 4. Version Control
- [ ] All changes committed with meaningful messages (e.g., "refactor: split query_classifier into focused modules")
- [ ] Each refactor committed separately (rollback safety maintained)
- [ ] No uncommitted changes in working directory: `git status` shows clean
- [ ] All commits follow conventional commit format

### 5. Epic 3 Readiness
- [ ] Winston signs off on module cohesion and Epic 3 readiness
- [ ] Epic 3 Stories 3.1+ unblocked (no technical debt blocking start)
- [ ] Story marked "done" in `sprint-status.yaml` (or equivalent tracking system)

### 6. Quality Gates Passed
- [ ] All acceptance criteria (AC1-AC4) completed and validated
- [ ] All subtasks (Task 1-4) checked off and verified
- [ ] No known bugs or regressions introduced by refactoring
- [ ] Code review completed (if required by team process)

**Story cannot be marked "done" until ALL checkboxes above are complete.**

## Dev Agent Record

### Context Reference

- [Story Context XML](3-0-1-refactor-modules-to-size-limits.context.xml) - Generated 2025-11-05

### Agent Model Used

Claude 3.7 Sonnet (claude-sonnet-4-5-20250929)

### Debug Log References

**Session 2025-11-05:**
- Established pre-refactoring baseline (test results, dependencies, coverage - in progress)
- Created identification script: `scripts/identify-oversized-files.py`
- Generated oversized files report: 2 files identified (5,411 lines total)
- Analyzed module boundaries and dependencies
- Created comprehensive refactoring strategy (9,600 words)
- **BLOCKED:** Awaiting Winston/Ricardo approval before proceeding to AC3 refactoring execution

### Completion Notes List

**2025-11-05 - AC1 Complete:**
✅ Identified 2 oversized files:
- `adaptive_table_extraction.py`: 3109 lines (3x over 1000-line limit)
- `pipeline.py`: 2302 lines (2.3x over limit)

✅ Created comprehensive identification script with Epic 3 relevance prioritization

**2025-11-05 - AC2 Complete (Pending Approval):**
✅ Analyzed both files - identified 9 focused modules total:
- **adaptive_table_extraction.py → 5 modules**: classification.py, multi_header.py, standard_layouts.py, unit_inference.py, core.py
- **pipeline.py → 4 modules**: document_ingestion.py, chunking_strategy.py, embedding_generation.py, storage_operations.py

✅ Created refactoring strategy document with:
- Detailed module responsibilities and line count targets
- Import dependency analysis (no circular dependencies)
- Test impact assessment (34 imports from pipeline.py, 1 from adaptive_table_extraction.py)
- Compatibility shim pattern to maintain test stability
- Per-module refactoring protocol with validation gates

**Baseline Establishment:**
- Test results: Recording baseline (69% complete at checkpoint)
- Test dependencies: Mapped 34 imports from pipeline.py, 1 from adaptive_table_extraction.py
- Coverage baseline: Will be captured once tests complete
- Git checkpoint: Refactoring docs and scripts staged

**Next Step:**
✅ APPROVED - Strategy approved by Ricardo. AC3 execution ready for next session (2-3 hours estimated).

**Session Plan:**
- Priority 1: Refactor pipeline.py into 4 focused modules (1.5-2 hours)
- Priority 2: Refactor adaptive_table_extraction.py into 5 modules (1-1.5 hours)
- Final validation: All files <1000 lines, 349 tests passing (15 minutes)

**Handoff Document:** `docs/refactoring/next-session-handoff.md` - Complete execution plan for next session

### File List

**Created:**
- `docs/refactoring/oversized-files-report.txt` - File identification report
- `docs/refactoring/refactoring-strategy.md` - Comprehensive refactoring strategy (9,600 words)
- `docs/refactoring/baseline-summary.md` - Pre-refactoring baseline summary
- `docs/refactoring/next-session-handoff.md` - Complete handoff for AC3 execution
- `docs/refactoring/test_dependencies_pipeline.txt` - Pipeline test import mapping (34 imports)
- `docs/refactoring/test_dependencies_table.txt` - Table extraction test mapping (1 import)
- `docs/refactoring/baseline_test_results.txt` - Pre-refactoring test baseline (349 passed)
- `docs/refactoring/baseline_coverage.txt` - Pre-refactoring coverage baseline
- `scripts/identify-oversized-files.py` - Automated file identification script

**Modified:**
- `docs/sprint-status.yaml` - Story status: ready-for-dev → in-progress
- `docs/stories/3-0-1-refactor-modules-to-size-limits.md` - Task progress updates (this file)

---

**Story Created:** 2025-11-05
**Created By:** Bob (Scrum Master) - Batch create from Epic 3 Prep tech spec
**Next Step:** Review story, then run `story-ready` or `story-context` to mark ready for dev
