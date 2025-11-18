# Story 3.0.5: Execute Epic 2 UAT

**Status:** done
**Epic:** Epic 3 - AI Intelligence & Orchestration (Prep Sprint)
**Priority:** 🔴 CRITICAL (Validates Epic 2 foundation)
**Effort:** 30-60 minutes
**Owner:** Ricardo (Project Lead) - UAT Tester
**Depends On:** Story 3.0.3 (MCP Setup Guide - needed for configuration)

## Story

As a **project lead**,
I want **to execute user acceptance testing on Epic 2's MCP query tool**,
so that **Epic 2 is officially validated complete before building Epic 3 on top of it**.

## Context

**From Epic 2 Retrospective (2025-11-05):**

Ricardo (Project Lead): "We should execute user tests where we have a real user executing functionality iteratively."

**Current State:**
- Epic 2 marked "complete" based on automated tests (77.6% accuracy)
- MCP server exists since Epic 1 (`raglite/main.py`)
- No real user has tested the query tool yet
- Ricardo hasn't connected to MCP server

**Risk:**
- Epic 3 builds on Epic 2 foundation
- If Epic 2 has usability issues, Epic 3 inherits them
- UAT now prevents cascading UX debt

**Strategic Decision:**
- Validate Epic 2 with real user testing BEFORE Epic 3
- Establish UAT baseline for all future epics
- Ricardo's feedback informs Epic 3 UX design

## Acceptance Criteria

### AC1: MCP Server Setup (10 minutes)

**Goal:** Connect Claude Desktop to RAGLite MCP server

**Technical Approach:**

1. **Use Story 3.0.3's setup guide:**
   - Location: `docs/setup/mcp-configuration.md`
   - Follow step-by-step instructions

2. **Add MCP configuration:**
   - Edit: `~/.claude/mcp.json`
   - Add RAGLite server configuration
   - Use absolute path to RAGLite project

3. **Restart Claude Desktop:**
   - Quit completely (not just close window)
   - Reopen and wait 5-10 seconds

4. **Verify connection:**
   - Check Settings > MCP for "RAGLite"
   - If not visible, troubleshoot using guide

**Success Criteria:**
- ✅ MCP server configured (using Story 3.0.3 guide)
- ✅ Claude Desktop shows "RAGLite" in connected servers
- ✅ No connection errors in logs

**Validation:**
- Ricardo successfully connects (validates Story 3.0.3 guide clarity)
- If connection fails, Story 3.0.3 guide needs improvement

### AC2: Execute UAT Script (30-60 minutes)

**Goal:** Test all 10 Epic 2 scenarios and record results

**Technical Approach:**

1. **Open UAT script:**
   - Location: `docs/uat/epic-2-financial-queries-uat.md`
   - Created during Epic 2 retrospective

2. **Verify prerequisites:**
   - Qdrant running: `docker ps`
   - PostgreSQL running: `docker ps`
   - MCP server connected (from AC1)

3. **Execute 10 test scenarios:**
   - Test 1: Simple Metric Query
   - Test 2: Period Normalization
   - Test 3: Multi-Entity Comparison
   - Test 4: Fuzzy Entity Matching
   - Test 5: Hybrid Search
   - Test 6: Table-Aware Chunking
   - Test 7: Currency Limitation Handling
   - Test 8: Budget vs Actual Detection
   - Test 9: Source Attribution Accuracy
   - Test 10: Response Time

4. **For each test:**
   - Execute action (ask query in Claude Desktop)
   - Record actual result
   - Compare to expected result
   - Mark pass/fail
   - Note any usability issues

5. **Complete results summary:**
   - Count tests passed/failed
   - Calculate pass rate
   - Overall result: PASS (≥80%) / PARTIAL (60-79%) / FAIL (<60%)

**Success Criteria:**
- ✅ All 10 test scenarios executed
- ✅ Actual results recorded for each test
- ✅ Pass/fail marked for each test
- ✅ Results summary completed
- ✅ Usability feedback documented

**Files Modified:**
- `docs/uat/epic-2-financial-queries-uat.md` (filled in with results)

### AC3: UAT Results Review (30 minutes)

**Goal:** Team reviews results and decides Epic 2 status

**Technical Approach:**

1. **Present results to team:**
   - Share completed UAT script
   - Discuss pass rate
   - Highlight usability issues

2. **Team decision:**

| Pass Rate | Decision | Action |
|-----------|----------|--------|
| ≥80% | ✅ EPIC 2 COMPLETE | Officially mark Epic 2 done, proceed to Epic 3 |
| 60-79% | ⚠️ PARTIAL | Create UX improvement stories, schedule follow-up UAT |
| <60% | ❌ FAIL | Epic 2 NOT complete - fix issues, re-run UAT |

3. **If PASS (≥80%):**
   - Update sprint-status.yaml: Epic 2 officially complete
   - Document lessons learned
   - Begin Epic 3 feature implementation

4. **If PARTIAL (60-79%):**
   - Create follow-up stories for failed tests
   - Schedule follow-up UAT after fixes
   - Consider delaying Epic 3 by 1 week

5. **If FAIL (<60%):**
   - Team meeting to review critical issues
   - Fix blocking usability issues
   - Re-run UAT (must achieve ≥60% to proceed)

**Success Criteria:**
- ✅ Team reviews UAT results
- ✅ Decision made: PASS / PARTIAL / FAIL
- ✅ Epic 2 status updated accordingly
- ✅ Action items created (if needed)

## Tasks / Subtasks

### Task 1: MCP Server Setup (AC1) - 10 minutes

- [ ] **Subtask 1.1:** Follow Story 3.0.3 setup guide
  - Edit `~/.claude/mcp.json`
  - Add RAGLite configuration
  - Use absolute path

- [ ] **Subtask 1.2:** Restart Claude Desktop
  - Quit completely
  - Reopen and wait

- [ ] **Subtask 1.3:** Verify connection
  - Check Settings > MCP
  - Confirm "RAGLite" appears

- [ ] **Subtask 1.4:** Troubleshoot if needed
  - Use troubleshooting section from Story 3.0.3
  - Fix any connection issues

### Task 2: Execute UAT Script (AC2) - 30-60 minutes

- [ ] **Subtask 2.1:** Open UAT script
  - File: `docs/uat/epic-2-financial-queries-uat.md`

- [ ] **Subtask 2.2:** Verify prerequisites
  - Qdrant running
  - PostgreSQL running
  - MCP connected

- [ ] **Subtask 2.3:** Execute Test 1 (Simple Metric Query)
  - Ask query in Claude Desktop
  - Record actual result
  - Mark pass/fail

- [ ] **Subtask 2.4:** Execute Tests 2-10
  - Repeat for each test scenario
  - Note usability issues

- [ ] **Subtask 2.5:** Complete results summary
  - Count passes/fails
  - Calculate pass rate
  - Overall result

### Task 3: UAT Results Review (AC3) - 30 minutes

- [ ] **Subtask 3.1:** Present results to team
  - Share completed UAT script
  - Discuss findings

- [ ] **Subtask 3.2:** Team decision
  - Evaluate pass rate
  - Decide: PASS / PARTIAL / FAIL

- [ ] **Subtask 3.3:** Update Epic 2 status
  - If PASS: Mark Epic 2 officially complete
  - If PARTIAL/FAIL: Create action items

## Dev Notes

### Learnings from Previous Story

**From Story 3.0.4 (Create UAT Framework Templates) - Status: done**

Story 3.0.4 created the complete UAT framework that enables this story's execution:

**Files Created (Ready for Use):**
- `docs/process/uat-framework.md` (173 lines) - UAT workflow with 4 phases (Readiness, Script Creation, Execution, Review)
- `docs/templates/uat-script-template.md` (145 lines) - Reusable UAT script template
- `docs/templates/data-dictionary-template.md` (160 lines) - Data dictionary template
- `docs/coding-standards/module-size.md` (409 lines) - Module size guidelines

**Key Achievements:**
- ✅ UAT framework documented with decision criteria: ≥80% PASS, 60-79% PARTIAL, <60% FAIL
- ✅ UAT script template ready to apply to Epic 2 testing
- ✅ Senior Developer Review: APPROVED (after addressing review findings)
- ✅ Templates validated through self-review and code review process

**Architectural Decisions:**
- KISS principle maintained (no custom frameworks or tooling)
- Standard markdown documentation approach
- Manual UAT execution appropriate for user-facing features
- Cross-platform documentation with user-centric language

**Relevance to Story 3.0.5:**
- **UAT Framework** provides the 4-phase structure for Epic 2 UAT execution
- **Decision Criteria** clearly define pass/fail thresholds (≥80% to mark Epic 2 complete)
- **UAT Script Template** serves as the base for Epic 2 test scenarios
- **Process Documentation** guides Ricardo through UAT execution
- **MCP Setup Guide** (Story 3.0.3) combined with UAT framework enables end-to-end testing

**Advisory Notes from Review:**
- Templates will be validated in practice during this story's execution
- If usability issues found with templates, document for future improvement
- UAT script should be at `docs/uat/epic-2-financial-queries-uat.md` (may already exist from Epic 2 retrospective)

**Reference:** [Story 3.0.4](docs/stories/3-0-4-create-uat-framework-templates.md)

---

### UAT Execution Tips

**For Ricardo:**

1. **Take your time:**
   - Don't rush through scenarios
   - Note every usability issue (even small ones)
   - Your feedback shapes Epic 3 UX

2. **Be honest:**
   - If something is confusing, mark it FAIL
   - We want real user perspective
   - Better to find issues now than in production

3. **Document thoroughly:**
   - Write actual results verbatim
   - Include screenshots if helpful
   - Usability notes are as important as pass/fail

### Expected Pass Rate

**Realistic Target:**
- 70-90% pass rate (7-9 out of 10 tests)
- Some edge cases may fail (acceptable)
- Major features should work (Tests 1-5 critical)

**If <70%:**
- Indicates significant usability issues
- Team needs to address before Epic 3

### Epic 2 Foundation for Epic 3

**Why UAT matters:**
- Epic 3 builds agentic workflows on Epic 2 retrieval
- If basic queries don't work, multi-step reasoning won't either
- UAT validates foundation before adding complexity

### References

**Source Documents:**
- [Epic 2 Retrospective](docs/retrospectives/epic-2-retro-2025-11-05.md) - UAT requirement identified
- [Epic 3 Prep Tech Spec](docs/tech-spec-epic-3-prep.md#story-305) - UAT execution spec
- [Epic 2 UAT Script](docs/uat/epic-2-financial-queries-uat.md) - Test scenarios
- [Story 3.0.3 MCP Setup Guide](docs/setup/mcp-configuration.md) - Connection instructions

## Dev Agent Record

### Context Reference

- **Story Context XML**: `docs/stories/3-0-5-execute-epic-2-uat.context.xml` (Generated: 2025-11-07)

### Agent Model Used

Claude 3.7 Sonnet (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

## Change Log

**2025-11-05:** Story created by Bob (Scrum Master) - Batch create from Epic 3 Prep tech spec

**2025-11-07:** Story updated by Bob (Scrum Master) - Added "Learnings from Previous Story" section:
- ✅ Added comprehensive learnings from Story 3.0.4 (UAT Framework Templates)
- ✅ Documented files created in 3.0.4 (UAT framework, templates) ready for use in this story
- ✅ Highlighted architectural decisions (KISS principle, markdown documentation)
- ✅ Cross-referenced UAT framework and decision criteria (≥80% PASS threshold)
- ✅ Noted template validation will occur during execution of this story
- **Status:** Story remains "drafted" - awaiting execution by Ricardo

**2025-11-07:** Story context generated by Bob (Scrum Master) - Story ready for execution:
- ✅ Generated comprehensive Story Context XML (3-0-5-execute-epic-2-uat.context.xml)
- ✅ Included documentation artifacts (UAT framework, templates, MCP setup guide, tech spec)
- ✅ Identified relevant code artifacts (MCP server, retrieval services, ground truth data)
- ✅ Documented constraints (manual execution, prerequisites, decision gates)
- ✅ Defined testing approach (manual UAT with 10 test scenarios)
- ✅ Updated story status: drafted → ready-for-dev
- ✅ Updated sprint-status.yaml: 3-0-5-execute-epic-2-uat → ready-for-dev
- **Status:** Story ready for Ricardo to execute UAT

**2025-11-07:** UAT script redesigned by Bob (Scrum Master) - Aligned with actual ingested document:
- ⚠️ **Issue Found:** Original UAT script (epic-2-financial-queries-uat.md) referenced full 160-page PDF with data not in ingested test-10-pages.pdf
- ✅ **Investigation:** Verified actual ingested document is test-10-pages.pdf (10-page Secil Group financial subset)
- ✅ **Solution:** Created new UAT script aligned with actual content: epic-2-uat-test-10-pages.md
- ✅ **New Test Queries:** Redesigned 10 test scenarios based on actual Secil Group data (Aug-25, Budget, YTD, Portugal/Lebanon entities)
- ✅ **Validation:** All queries tested against actual Qdrant content to ensure executability
- **UAT Script:** Use `docs/uat/epic-2-uat-test-10-pages.md` (NOT the old epic-2-financial-queries-uat.md)

**2025-11-07:** UAT executed by Ricardo - PASSED with 90% (Story DONE):
- ✅ **Tests Passed:** 9/10 (Simple query, Budget comparison, YoY comparison, Entity ID, Currency, YTD, Hybrid search, Citations, Performance)
- ⚠️ **Tests Partial:** 1/10 (Table-specific requests need improvement, but tables retrieve correctly via metric queries)
- ❌ **Tests Failed:** 0/10
- ✅ **Pass Rate:** 90% → **EXCEEDS 80% THRESHOLD** → Epic 2 officially complete
- ✅ **Key Achievements:** 100% citation accuracy, p50 4.7s (target <5s), p95 9.1s (target <15s), entity disambiguation working, multi-period comparisons working
- 📋 **Recommendations:** 7 UX improvements documented for Epic 3 (query suggestion system, template library, progressive enhancement)
- ✅ **Epic 2 Status:** Updated to "done" in sprint-status.yaml
- ✅ **Results:** Full report at `docs/uat/epic-2-uat-results-completed.md`
- **Status:** Story marked "done" - Epic 2 foundation validated for Epic 3 development

---

**Story Created:** 2025-11-05
**Created By:** Bob (Scrum Master) - Batch create from Epic 3 Prep tech spec
**Last Updated:** 2025-11-07 (Added learnings from Story 3.0.4)
**Next Step:** Review story, then run `story-ready` or `story-context` to mark ready for dev
**Dependency:** Story 3.0.3 (MCP Setup Guide) must be complete before execution
