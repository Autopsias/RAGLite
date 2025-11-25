# Story Quality Validation Report

**Story:** 3-7-graceful-degradation-for-workflow-failures
**Title:** Graceful Degradation for Workflow Failures
**Date:** 2025-11-18
**Validator:** Bob (Scrum Master - Independent Review)
**Outcome:** ❌ **FAIL** - Critical: 1, Major: 2, Minor: 1

---

## Executive Summary

Story 3.7 demonstrates **excellent technical design** with comprehensive acceptance criteria, detailed architecture guidance, and strong testing strategy. However, **critical continuity gaps** prevent approval.

**The story completely skips Story 3-6** (previous completed story) and jumps back to Story 3-5 for learnings, violating the create-story workflow's continuity tracking requirement. Story 3-6 created 2 new test files and modified 2 core files, none of which are mentioned in Story 3-7's context.

---

## Critical Issues (Blockers)

### ❌ Issue #1: Missing Previous Story Continuity (Story 3-6)

**Severity:** CRITICAL
**Checklist:** Section 2 - Previous Story Continuity Check
**Location:** Lines 190-230 "Learnings from Previous Story"

**Problem:**
Story 3-7 references ONLY Story 3-5 (Multi-Step Workflow Orchestration) in its "Learnings from Previous Story" section, completely skipping Story 3-6 (Analytical Query Tool - MCP).

**Evidence:**
- **Previous story in sprint-status.yaml:** `3-6-analytical-query-tool-mcp: done` (line 102)
- **Current story learnings cite:** `[Source: stories/3-5-multi-step-workflow-orchestration.md#Task-4-Complete]` (line 229)
- **No mention of Story 3-6** anywhere in Story 3-7

**Story 3-6 Context (Missing from Story 3-7):**
- **Status:** done (completed 2025-11-17, production-ready approval)
- **NEW Files Created:**
  - `tests/unit/test_mcp_analytical_tool.py` (91 lines)
  - `tests/integration/test_analytical_query_tool.py` (660 lines)
- **Modified Files:**
  - `raglite/main.py` (+50 lines - MCP tool integration)
  - `raglite/shared/models.py` (+25 lines - AnalyticalQueryRequest/Response models)
- **Key Completion Notes:**
  - MCP analytical query tool fully operational
  - Query complexity routing working (simple→Epic2, analytical→Epic3)
  - Critical bug fixes: agent signature mismatch, stdout pollution, query reformulation
  - Code review: 95/100 quality score, production-ready

**Impact:**
- Continuity break between stories - Story 3-6 implementation context lost
- Test suite expansion (750+ lines of new tests) not acknowledged
- Potential implementation conflicts (Story 3-7 adds more test files without knowing Story 3-6's test structure)
- Violates create-story workflow requirement: "Learnings from Previous Story should reference: new files created, completion notes, architectural decisions"

**Required Fix:**
Add "Learnings from Story 3-6" subsection BEFORE Story 3-5 section (insert at line 190):

```markdown
### Learnings from Previous Story

**From Story 3-6: Analytical Query Tool (MCP)** (Status: done)

**MCP Tool Integration Complete:**
- ✅ `analytical_query_financial_documents()` MCP tool operational in `raglite/main.py`
- ✅ Query complexity routing: simple→Epic 2, analytical→Epic 3 workflow
- ✅ Full reasoning steps transparency and source attribution
- ✅ Production-ready (95/100 code review score, 2025-11-17)

**Test Suite Expansion:**
- NEW: `tests/unit/test_mcp_analytical_tool.py` (91 lines - MCP registration, model validation)
- NEW: `tests/integration/test_analytical_query_tool.py` (660 lines - 35 tests, 7 test classes)
- Test coverage: YoY queries, variance analysis, trend analysis, comparative queries

**Critical Bug Fixes Applied:**
- Agent signature mismatch resolved (all agents now accept `(instruction: str, context: dict | None)`)
- Stdout pollution fixed (print() → logger.debug() in sql_table_search.py)
- Query reformulation for comparative queries (semantic mismatch resolution)

**Implementation Guidance for Story 3.7:**
- ✅ MCP server structure established - follow existing patterns
- ✅ Error handling via `handle_workflow_failure()` already in place
- ✅ Test suite organization: unit/ and integration/ folders with P0/P1/P2 priority classification
- ⚠️ Watch for test file conflicts - Story 3-6 added 750+ lines of tests

[Source: stories/3-6-analytical-query-tool-mcp.md#Code-Review-2025-11-18]

---

**From Story 3-5: Multi-Step Workflow Orchestration** (Status: done)

[Keep existing Story 3-5 content from lines 192-230]
```

---

## Major Issues (Should Fix)

### ⚠️ Issue #2: Missing NEW Files Reference from Story 3-6

**Severity:** MAJOR
**Checklist:** Section 2 - Subsection "If subsection exists, verify it includes: References to NEW files from previous story"
**Location:** Lines 190-230 "Learnings from Previous Story"

**Problem:**
Story 3-6 created 2 NEW test files (750+ lines combined) not mentioned in Story 3-7's learnings.

**Evidence:**
- **NEW files from Story 3-6:**
  - `tests/unit/test_mcp_analytical_tool.py`
  - `tests/integration/test_analytical_query_tool.py`
- **Story 3-7 Dev Notes** (lines 178-189): Lists files to be CREATED by Story 3-7:
  - `tests/integration/test_graceful_degradation.py` (~400 lines NEW)
  - `tests/unit/test_fallback_response_formatter.py` (~150 lines NEW)
- **No acknowledgment** that Story 3-6 just added 2 test files in same directories

**Impact:**
- Test suite organization not communicated to dev agent
- Potential file naming conflicts (both stories add integration tests)
- Test count tracking inaccurate (~372 tests mentioned in CLAUDE.md, but Story 3-6 added 35+ tests)

**Required Fix:**
Include in Story 3-6 learnings section: "Story 3-6 expanded test suite with 2 new test files (750+ lines, 35 tests). Follow established test organization: priority classification (P0/P1/P2), skipif strategy for CI/CD."

---

### ⚠️ Issue #3: Missing Completion Notes from Story 3-6

**Severity:** MAJOR
**Checklist:** Section 2 - "References to completion notes/warnings"
**Location:** Lines 190-230 "Learnings from Previous Story"

**Problem:**
Story 3-6 completion notes include critical bug fixes and implementation warnings not captured.

**Evidence:**
- **Story 3-6 Completion Notes** (lines 1126-1324 of 3-6 file):
  - Agent signature mismatch bug (CRITICAL) - all agents updated to `(instruction: str, context: dict | None)`
  - Stdout pollution bug (CRITICAL) - print() statements broke MCP JSON parser
  - Query reformulation added to retrieval agent for comparative queries
  - Semantic mismatch resolution (question embeddings vs document embeddings)
- **Story 3-7 does not mention:**
  - Agent signature convention
  - Stdout logging best practices (logger.debug() not print())
  - Query reformulation pattern

**Impact:**
- Implementation warnings not carried forward
- Risk of repeating bugs (e.g., using print() instead of logger.debug())
- Missing context on agent interface conventions

**Required Fix:**
Add to Story 3-6 learnings: "Critical fixes applied: Agent signatures now standardized `(instruction: str, context: dict | None)`. Use logger.debug() not print() to avoid MCP JSON parser errors. Query reformulation pattern available in retrieval_agent.py for comparative queries."

---

## Minor Issues (Nice to Have)

### ➖ Issue #4: Change Log Not Initialized

**Severity:** MINOR
**Checklist:** Section 7 - Story Structure Check
**Location:** Missing from story file

**Problem:**
Story file doesn't have Change Log section after Dev Agent Record.

**Impact:** Low - Story tracking inconsistency

**Required Fix:**
Add after Dev Agent Record (after line 422):

```markdown
## Change Log

- **2025-11-18:** Story drafted by SM (create-story workflow)
```

---

## Successes

1. ✅ **Excellent Acceptance Criteria Quality**
   - All 6 ACs are testable, specific, and atomic
   - Clear success thresholds (≥90% graceful degradation test pass rate)
   - Comprehensive coverage: timeouts, error detection, fallback, user messaging, metrics, testing

2. ✅ **Complete Task-AC Mapping**
   - Every AC has dedicated tasks
   - All tasks reference AC numbers
   - 6 testing subtasks (unit + integration) cover all 6 ACs

3. ✅ **Exceptional Architecture Guidance**
   - **Highly specific 4-tier degradation design** (lines 132-149):
     - Tier 1: Full Orchestration (95% success rate)
     - Tier 2: Partial Analysis (4% success rate)
     - Tier 3: Retrieval Only (0.9% success rate)
     - Tier 4: Epic 1/2 Fallback (0.1% success rate)
   - Timeout strategy clearly defined (15s per-agent, 30s workflow)
   - User-friendly error message examples provided (lines 231-315)

4. ✅ **Strong Testing Strategy**
   - 10 unit tests planned (error formatting, alternative suggestions, metrics)
   - 6 integration tests planned (timeout, API failure, Qdrant failure, partial success)
   - Test scenarios marked `@pytest.mark.slow` for CI/CD
   - Success criteria: ≥90% of failure scenarios handled gracefully

5. ✅ **Comprehensive Source Citations**
   - 6 citations in References section (lines 397-406)
   - All citations include precise section anchors (#story-3.7, #error-handling-strategy)
   - Cites PRD, Architecture (3 docs), previous story, fallback module, NFRs

6. ✅ **Clear Project Structure Notes**
   - Files to be modified clearly listed (lines 164-189)
   - Total new code estimated: ~700 lines (within Epic 3 target)
   - File responsibilities documented

7. ✅ **Proper Story Format**
   - Status: "drafted" ✅
   - Story statement: Correct "As a system / I want / so that" format
   - Dev Agent Record sections initialized correctly

8. ✅ **Dev Notes Quality**
   - Architecture context is VERY specific (not generic)
   - Design decisions explained with rationale
   - Examples provided for all degradation tiers
   - Metrics tracking schema documented

---

## Detailed Validation Results

### 1. Load Story and Extract Metadata ✅

- ✅ Story file loaded: `3-7-graceful-degradation-for-workflow-failures.md`
- ✅ Metadata extracted:
  - Epic: 3
  - Story: 7
  - Story identifier: 3-7-graceful-degradation-for-workflow-failures
  - Title: Graceful Degradation for Workflow Failures
  - Status: drafted

---

### 2. Previous Story Continuity Check

**Previous Story Identified:**
- ✅ Loaded `docs/sprint-status.yaml`
- ✅ Found entry: `3-6-analytical-query-tool-mcp: done` (line 102)
- ✅ Previous story status: done (not backlog/drafted)

**Previous Story Content Loaded:**
- ✅ File: `docs/sprint-artifacts/3-6-analytical-query-tool-mcp.md`
- ✅ Extracted Dev Agent Record:
  - Status: done
  - Code Review: 2025-11-18 (production-ready approval)
  - NEW files: tests/unit/test_mcp_analytical_tool.py, tests/integration/test_analytical_query_tool.py
  - Modified files: raglite/main.py, raglite/shared/models.py
  - Completion notes: 1833 lines (extensive bug fixes documented)

**Senior Developer Review Check:**
- ✅ Review section exists: "Code Review - 2025-11-18 (Amelia - Senior Developer)"
- ✅ Review status: ✅ APPROVED - Production-ready
- ✅ No unchecked [ ] items in review sections
- ✅ No unresolved follow-ups

**Current Story "Learnings from Previous Story" Validation:**
- ✅ Subsection exists (lines 190-230)
- ❌ **CRITICAL FAIL:** Only references Story 3-5, does NOT mention Story 3-6
- ❌ **MAJOR FAIL:** Does NOT reference NEW files from Story 3-6
- ❌ **MAJOR FAIL:** Does NOT mention completion notes from Story 3-6
- ❌ **MAJOR FAIL:** Does NOT call out ANY lessons from Story 3-6
- ✅ Cites source: [Source: stories/3-5-multi-step-workflow-orchestration.md#Task-4-Complete]

**Expected Content (Missing):**
- Story 3-6 NEW files: 2 test files (750+ lines)
- Story 3-6 modified files: raglite/main.py, raglite/shared/models.py
- Story 3-6 key takeaways: MCP tool integration, bug fixes, production approval
- Story 3-6 warnings: Agent signature convention, stdout logging pattern

---

### 3. Source Document Coverage Check

**Available Documents:**
- ✅ Tech spec: `docs/tech-spec-epic-3.md` exists
- ✅ Epics: `docs/epics.md` exists
- ✅ PRD (sharded): `docs/prd/epic-3-ai-intelligence-orchestration.md` exists
- ✅ Architecture (sharded): Multiple files exist:
  - `docs/architecture/epic-3-orchestration-design.md`
  - `docs/architecture/epic-3-agent-patterns.md`
  - `docs/architecture/coding-standards.md`
  - `docs/architecture/testing-strategy.md`

**Citations Extracted from Story:**
1. `docs/prd/epic-3-ai-intelligence-orchestration.md#story-3.7` (line 398)
2. `docs/architecture/epic-3-orchestration-design.md#error-handling-strategy` (line 399)
3. `docs/architecture/epic-3-agent-patterns.md#pattern-4-error-fallback` (line 400)
4. `docs/stories/3-5-multi-step-workflow-orchestration.md#Task-4-Complete` (line 401)
5. `raglite/agentic/fallback.py` (line 402)
6. NFR17, NFR26, NFR32 (line 403)

**Validation Results:**
- ✅ Tech spec exists and cited
- ✅ Epics exist (referenced via PRD citations)
- ✅ PRD exists and cited with section anchor
- ✅ Architecture docs exist and cited (3 architecture files)
- ✅ Testing strategy mentioned in Dev Notes (integration test strategy section)
- ✅ All citations include section names (not vague)
- ✅ Citation quality: Precise section anchors (#story-3.7, #error-handling-strategy, etc.)

---

### 4. Acceptance Criteria Quality Check

**AC Count:** 6 ACs (lines 13-53)

**AC Source:**
- Story cites: `docs/prd/epic-3-ai-intelligence-orchestration.md#story-3.7`

**Individual AC Validation:**

**AC1: Workflow timeout handling (>30 seconds triggers fallback)**
- ✅ Testable: Specific thresholds (30s workflow, 15s per-agent)
- ✅ Specific: Timeout detection method specified (asyncio.wait_for())
- ✅ Atomic: Single concern (timeout handling)

**AC2: Agent failure detection and logging**
- ✅ Testable: Error types enumerated (connection, API, timeout)
- ✅ Specific: Logging requirements detailed (structured metadata, WARNING level)
- ✅ Atomic: Single concern (failure detection)

**AC3: Fallback to basic retrieval when workflow fails**
- ✅ Testable: Trigger conditions listed, fallback path defined
- ✅ Specific: Fallback response format specified
- ✅ Atomic: Single concern (fallback behavior)

**AC4: User receives partial results or error message with suggested alternative query**
- ✅ Testable: Response format specified (answer, limitations, error_summary)
- ✅ Specific: User experience requirements clear ("never 'error 500'")
- ✅ Atomic: Single concern (user messaging)

**AC5: Error rates logged for workflow improvement**
- ✅ Testable: Metrics enumerated (tier_1_success_rate, etc.), target rates specified
- ✅ Specific: Target thresholds provided (Tier 1 ≥95%, Tier 2 <5%, etc.)
- ✅ Atomic: Single concern (metrics tracking)

**AC6: Integration test validates fallback behavior**
- ✅ Testable: Test scenarios listed (timeout, API failure, etc.), success criteria ≥90%
- ✅ Specific: Coverage requirements clear (all 4 degradation tiers)
- ✅ Atomic: Single concern (testing)

**Summary:**
- ✅ All 6 ACs are testable
- ✅ All 6 ACs are specific
- ✅ All 6 ACs are atomic
- ✅ No vague ACs found

---

### 5. Task-AC Mapping Check

**Tasks:** 6 tasks, 33 subtasks (lines 57-106)

**AC Coverage Analysis:**
- Task 1: Enhance timeout handling and failure detection → **AC1, AC2** ✅
- Task 2: Implement user-friendly error messages and alternative query suggestions → **AC4** ✅
- Task 3: Add metrics tracking for workflow degradation → **AC5** ✅
- Task 4: Create integration tests for graceful degradation scenarios → **AC6** ✅
- Task 5: Document graceful degradation behavior and failure handling → **AC1-AC6** ✅
- Task 6: Add monitoring hooks for production observability → **AC5** ✅

**All ACs Covered:**
- AC1: Task 1 ✅
- AC2: Task 1 ✅
- AC3: No explicit task, but covered in Task 1 (fallback implementation exists in Story 3.5)
- AC4: Task 2 ✅
- AC5: Task 3, Task 6 ✅
- AC6: Task 4 ✅

**Task-AC References:**
- ✅ Task 1 references (AC1, AC2) in task description
- ✅ Task 2 references (AC4) in task description
- ✅ Task 3 references (AC5) in task description
- ✅ Task 4 references (AC6) in task description
- ✅ Task 5 references (AC1-AC6) in task description
- ✅ Task 6 references (AC5) in task description

**Testing Subtasks:**
- Task 1.6: Create unit tests for error classification logic ✅
- Task 2.5: Add unit tests for error message formatting ✅
- Task 3.5: Create unit tests for metrics tracking logic ✅
- Task 4.1-4.10: Integration tests (10 subtasks) ✅

**Testing Coverage:**
- ✅ 6 testing subtasks total
- ✅ Testing subtasks ≥ AC count (6 ≥ 6)

**Summary:**
- ✅ Every AC has tasks
- ✅ Every task references ACs
- ✅ Testing subtasks present for all ACs

---

### 6. Dev Notes Quality Check

**Required Subsections Check:**
- ✅ Architecture patterns and constraints (lines 109-161) - "Architecture Context"
- ✅ References (lines 397-406) - "References" section
- ✅ Project Structure Notes (lines 162-189) - "Project Structure Notes"
- ✅ Learnings from Previous Story (lines 190-230) - **BUT WRONG STORY**

**Content Quality Analysis:**

**Architecture Guidance Specificity:**
- ✅ **Highly specific** (not generic):
  - 4-tier degradation strategy with percentages (Tier 1: 95%, Tier 2: 4%, Tier 3: 0.9%, Tier 4: 0.1%)
  - Timeout thresholds: 15s per-agent, 30s workflow
  - User-friendly error message templates provided (lines 231-315)
  - Metrics tracking schema documented (lines 317-343)
  - Testing strategy detailed (lines 346-396)

**Citation Count:**
- ✅ 6 citations in References section (lines 397-406)
- ✅ Additional inline citations in Architecture Context (NFR17, NFR26, NFR32)
- ✅ More than 3 citations threshold met

**Suspicious Specifics Without Citations:**
- ✅ No invented details detected
- ✅ All technical specs referenced to source documents:
  - Timeout values → NFR26 (15s), NFR5 (30s)
  - Degradation tiers → epic-3-agent-patterns.md#pattern-4-error-fallback
  - Metrics targets → Story design decisions (documented rationale)

**Summary:**
- ✅ Architecture guidance is very specific
- ✅ Citation count exceeds minimum (6 > 3)
- ✅ No invented details found
- ⚠️ Learnings section references wrong previous story (Story 3-5 instead of Story 3-6)

---

### 7. Story Structure Check

**Status Field:**
- ✅ Status = "drafted" (line 3)

**Story Statement Format:**
- ✅ Has "As a / I want / so that" format (lines 5-9):
  - "As a system,"
  - "I want to handle agentic workflow failures gracefully,"
  - "so that users receive useful responses even when complex workflows fail."

**Dev Agent Record Sections:**
- ✅ Context Reference (line 409)
- ✅ Agent Model Used (line 413)
- ✅ Debug Log References (line 417)
- ✅ Completion Notes List (line 419)
- ✅ File List (line 421)

**Change Log:**
- ❌ Missing (MINOR ISSUE)

**File Location:**
- ✅ Correct: `docs/sprint-artifacts/3-7-graceful-degradation-for-workflow-failures.md`

**Summary:**
- ✅ Status correct
- ✅ Story format correct
- ✅ Dev Agent Record initialized
- ⚠️ Change Log missing (MINOR ISSUE)
- ✅ File location correct

---

### 8. Unresolved Review Items Alert

**Previous Story (3-6) Review Check:**

**Senior Developer Review:**
- ✅ Review section exists: "Code Review - 2025-11-18 (Amelia - Senior Developer)" (line 1326)
- ✅ Review date: 2025-11-18
- ✅ Overall assessment: ✅ APPROVED - Production-ready implementation
- ✅ Decision: ✅ APPROVED - Production-Ready

**Action Items:**
- ✅ Checked for unchecked [ ] items in "REQUIRED FIXES BEFORE APPROVAL" section
- ✅ Result: No unchecked items (all fixes completed in follow-up sections)

**Review Follow-ups:**
- ✅ Checked for unchecked [ ] items in "Follow-Up Actions" or "Recommendations"
- ✅ Result: No unchecked items (manual testing completed, README optional)

**Current Story (3-7) Check:**
- ❌ **CRITICAL FAIL:** Story 3-7 "Learnings from Previous Story" does NOT mention any review items from Story 3-6
- ❌ **Expected:** If unchecked items existed, should be called out. Even with no unchecked items, should mention production approval status.

**Summary:**
- ✅ No unresolved review items in Story 3-6
- ❌ Story 3-7 does not acknowledge Story 3-6's production approval or review findings

---

## Recommendations

### Must Fix (Critical)

**1. Add Story 3-6 Continuity Section**
- **Priority:** CRITICAL (blocks approval)
- **Action:** Insert Story 3-6 learnings section before Story 3-5 section (line 190)
- **Content:** See Issue #1 for complete section text
- **Estimated Time:** 10 minutes

### Should Fix (Major)

**2. Reference Story 3-6 NEW Files**
- **Priority:** MAJOR
- **Action:** Add to Story 3-6 learnings: "Story 3-6 expanded test suite with 2 new test files (750+ lines, 35 tests). Follow established test organization: priority classification (P0/P1/P2), skipif strategy for CI/CD."
- **Estimated Time:** 5 minutes

**3. Reference Story 3-6 Completion Notes**
- **Priority:** MAJOR
- **Action:** Add to Story 3-6 learnings: "Critical fixes applied: Agent signatures now standardized `(instruction: str, context: dict | None)`. Use logger.debug() not print() to avoid MCP JSON parser errors."
- **Estimated Time:** 5 minutes

### Nice to Have (Minor)

**4. Initialize Change Log**
- **Priority:** MINOR
- **Action:** Add Change Log section after Dev Agent Record
- **Estimated Time:** 2 minutes

---

## Next Steps

### For Story Author (SM/Dev)

**Before marking story as "ready-for-dev":**

1. **Critical Fixes (Required - 20 minutes):**
   - Add Story 3-6 continuity section (10 min)
   - Reference Story 3-6 NEW files (5 min)
   - Reference Story 3-6 completion notes (5 min)

2. **Optional Improvements (5 minutes):**
   - Initialize Change Log section (2 min)
   - Review updated story for accuracy (3 min)

3. **Re-validation:**
   - Re-run create-story validation workflow
   - Confirm all CRITICAL and MAJOR issues resolved
   - Proceed to story-context generation

### For Validator

**If fixes applied:**
- Re-validate Section 2 (Previous Story Continuity)
- Verify all 3 critical/major issues addressed
- Confirm outcome changes from FAIL → PASS with issues or PASS

---

## Validation Metadata

**Checklist Version:** create-story/checklist.md (Story Quality Validation Checklist)
**Validation Date:** 2025-11-18
**Validator:** Bob (Scrum Master - Independent Review Agent)
**Story Status:** drafted
**Sprint Status:** 3-7-graceful-degradation-for-workflow-failures: drafted

**Validation Mode:** Fresh context (independent validator, no workflow instructions loaded)

**Documents Loaded:**
- Story file: `docs/sprint-artifacts/3-7-graceful-degradation-for-workflow-failures.md`
- Checklist: `.bmad/bmm/workflows/4-implementation/create-story/checklist.md`
- Previous story: `docs/sprint-artifacts/3-6-analytical-query-tool-mcp.md`
- Sprint status: `docs/sprint-status.yaml`

---

## Appendix: Checklist Completion Log

✅ **1. Load Story and Extract Metadata** - COMPLETE
❌ **2. Previous Story Continuity Check** - FAIL (Story 3-6 not referenced)
✅ **3. Source Document Coverage Check** - PASS (all docs cited)
✅ **4. Acceptance Criteria Quality Check** - PASS (all ACs testable)
✅ **5. Task-AC Mapping Check** - PASS (all ACs covered)
⚠️ **6. Dev Notes Quality Check** - PASS with issue (Learnings section wrong story)
⚠️ **7. Story Structure Check** - PASS with minor issue (Change Log missing)
✅ **8. Unresolved Review Items Alert** - PASS (no unchecked items in Story 3-6)

**Overall Outcome:** ❌ FAIL (Critical > 0 OR Major > 3)

---

**Validation Complete**
**Report Generated:** 2025-11-18
**Ricardo, this story needs critical fixes before it can proceed to ready-for-dev status.**
