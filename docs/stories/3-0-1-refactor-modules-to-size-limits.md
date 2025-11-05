# Story 3.0.1: Refactor Modules to Size Limits

**Status:** drafted
**Epic:** Epic 3 - AI Intelligence & Orchestration (Prep Sprint)
**Priority:** 🔴 CRITICAL (Blocks Epic 3 feature implementation)
**Effort:** 2-3 days
**Owner:** Charlie (Dev) + Winston (Architect Review)

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

# Generate report
python scripts/identify-oversized-files.py > docs/refactoring/oversized-files-report.txt
```

**Success Criteria:**
- ✅ Complete list of files >1000 lines identified
- ✅ Files prioritized by Epic 3 impact (e.g., retrieval/ modules critical)
- ✅ Report saved: `docs/refactoring/oversized-files-report.txt`

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
- ✅ Test coverage maintained or improved
- ✅ Code functionality unchanged (refactor only, no features)

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
- ✅ Winston architecture approval documented
- ✅ No files >1000 lines in `raglite/` directory
- ✅ Epic 3 Stories 3.1+ unblocked

## Tasks / Subtasks

### Task 1: Identify Oversized Files (AC1) - 2 hours

- [ ] **Subtask 1.1:** Scan `raglite/` directory for files >1000 lines
  ```bash
  find raglite -name "*.py" -exec wc -l {} \; | sort -rn | head -20
  ```

- [ ] **Subtask 1.2:** Create identification script
  - Script: `scripts/identify-oversized-files.py`
  - Output: List of files with line counts
  - Prioritize by Epic 3 impact

- [ ] **Subtask 1.3:** Generate report
  - Save to: `docs/refactoring/oversized-files-report.txt`
  - Include: file path, line count, Epic 3 relevance

### Task 2: Define Refactoring Strategy (AC2) - 2 hours

- [ ] **Subtask 2.1:** Analyze each oversized file
  - Identify logical domain boundaries
  - Plan module split strategy

- [ ] **Subtask 2.2:** Document refactoring plan
  - Create: `docs/refactoring/refactoring-strategy.md`
  - For each file: old structure → new structure
  - Example module names and responsibilities

- [ ] **Subtask 2.3:** Winston architecture review
  - Present refactoring strategy
  - Get approval before execution

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

## Dev Agent Record

### Context Reference

<!-- Story Context XML path will be added here if generated -->

### Agent Model Used

Claude 3.7 Sonnet (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

---

**Story Created:** 2025-11-05
**Created By:** Bob (Scrum Master) - Batch create from Epic 3 Prep tech spec
**Next Step:** Review story, then run `story-ready` or `story-context` to mark ready for dev
