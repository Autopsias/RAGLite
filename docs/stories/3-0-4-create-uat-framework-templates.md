# Story 3.0.4: Create UAT Framework Templates

**Status:** drafted
**Epic:** Epic 3 - AI Intelligence & Orchestration (Prep Sprint)
**Priority:** 🔴 CRITICAL (Establishes UAT for all epics)
**Effort:** 2 hours
**Owner:** Bob (Scrum Master) + Murat (Test Architect)

## Story

As a **project team**,
I want **standardized UAT templates and workflow documentation**,
so that **user acceptance testing is repeatable across all epics and usability issues are caught early**.

## Context

**From Epic 2 Retrospective (2025-11-05):**

Ricardo (Project Lead): "We should execute user tests iteratively to know what works and what doesn't."

**Root Cause:**
- No UAT framework defined
- Automated tests passing but usability unknown
- Project Lead couldn't use MCP tool (documentation gap missed by pytest)

**Impact:**
- Usability gaps invisible to automated testing
- Features built but not validated with real users
- Epic completion based on code tests, not user acceptance

**Strategic Decision:**
- Define UAT workflow for all epics
- Create templates for repeatable testing
- Ricardo as UAT tester going forward

## Acceptance Criteria

### AC1: UAT Workflow Documentation (1 hour)

**Goal:** Define standard UAT process for all epics

**Technical Approach:**

Create workflow doc: `docs/process/uat-framework.md`

**Content:**

```markdown
# User Acceptance Testing (UAT) Framework

**Purpose:** Validate user-facing features before marking epics complete

**Tester:** Ricardo (Project Lead)

---

## When to Use UAT

**Required:**
- After every epic, before marking "complete"
- For any user-facing feature (MCP tools, UI, APIs)
- Before production deployment

**Optional:**
- After individual stories (for high-risk features)
- Mid-epic validation (if major UX concerns)

---

## UAT Workflow

### Phase 1: UAT Readiness

**Who:** Story developer + Bob (SM)
**When:** Story marked "done" or epic nearing completion
**Output:** List of UAT-ready features

**Checklist:**
- [ ] Feature implemented and passing automated tests
- [ ] Setup documentation exists (e.g., MCP config guide)
- [ ] Prerequisites documented (dependencies, services)
- [ ] Test environment ready (databases, APIs running)

---

### Phase 2: UAT Script Creation

**Who:** Bob (SM) + Murat (Test Architect)
**When:** After UAT readiness confirmed
**Effort:** 1-2 hours per epic
**Output:** UAT script (markdown file)

**Script Structure:**
1. Prerequisites and setup verification
2. 8-10 test scenarios (step-by-step)
3. Expected vs actual results format
4. Pass/fail criteria for each scenario
5. Results summary section

**Use Template:** `docs/templates/uat-script-template.md`

---

### Phase 3: UAT Execution

**Who:** Ricardo (Project Lead)
**When:** After UAT script finalized
**Effort:** 30-60 min per epic
**Output:** Completed UAT script with results

**Process:**
1. Follow setup steps (verify prerequisites)
2. Execute each test scenario
3. Record actual results
4. Mark pass/fail for each test
5. Note usability issues or suggestions
6. Complete results summary

---

### Phase 4: UAT Results Review

**Who:** Entire team
**When:** After UAT execution complete
**Effort:** 30 min
**Output:** Epic status decision

**Decision Criteria:**

| Pass Rate | Decision | Action |
|-----------|----------|--------|
| ≥80% | ✅ PASS | Epic approved for completion |
| 60-79% | ⚠️ PARTIAL | Create UX improvement stories, schedule follow-up UAT |
| <60% | ❌ FAIL | Epic NOT complete - fix blocking issues, re-run UAT |

**If PASS:**
- Mark epic as complete
- Move to next epic

**If PARTIAL:**
- Create follow-up stories for failed tests
- Schedule follow-up UAT after fixes
- Consider delaying next epic by 1 week

**If FAIL:**
- Team meeting to review critical issues
- Fix blocking issues before next epic
- Re-run UAT after fixes (must achieve ≥60% to proceed)

---

## Testing Standards

**Test Scenario Requirements:**
- Clear action (what to do)
- Clear expectation (what should happen)
- Measurable pass/fail criteria
- Real user workflow (not contrived edge cases)

**Good Test Scenario:**
```markdown
### Test 1: Simple Metric Query

**Action:** Ask "What is the EBITDA for Portugal Cement in August 2025?"
**Expected:** Numeric value with EUR currency, citation to page/section, <5s response
**Actual:** _____
**Pass/Fail:** _____ (Pass if: value correct, citation present, <5s)
```

**Bad Test Scenario:**
```markdown
### Test 1: Query

**Action:** Test the query tool
**Expected:** It works
**Actual:** _____
**Pass/Fail:** _____
```

---

## Reporting

**UAT Results Location:**
- `docs/uat/epic-{N}-{feature-name}-uat.md` (completed script)

**Results Summary:**
- Tests passed: X/Y
- Overall: PASS / PARTIAL / FAIL
- Epic status: Approved / Needs Improvement / Not Complete

---

## Epic-Specific UAT Examples

**Epic 2: Financial Queries**
- Test MCP `query_financial_documents` tool
- 10 scenarios covering SQL search, hybrid search, period normalization
- [Script: docs/uat/epic-2-financial-queries-uat.md]

**Epic 3: Agentic Workflows (Future)**
- Test MCP `analyze_financial_question` tool
- 10 scenarios covering multi-step reasoning, agent transparency
- Focus on workflow clarity, not just accuracy

---

## Integration with Workflow

**Sprint Status Integration:**
- Epic marked "done" only after UAT PASS
- If UAT FAIL, epic status remains "in-progress"

**Story Context Integration:**
- UAT findings inform next epic's story creation
- UX issues documented as lessons learned

---

**Last Updated:** 2025-11-05
**Version:** 1.0
```

**Success Criteria:**
- ✅ UAT workflow documented: `docs/process/uat-framework.md`
- ✅ 4 phases clearly defined (Readiness, Script Creation, Execution, Review)
- ✅ Decision criteria table (≥80% PASS, 60-79% PARTIAL, <60% FAIL)
- ✅ Integration with sprint workflow

**Files Created:**
- `docs/process/uat-framework.md` (~400 lines)

### AC2: Create UAT Script Template (30 minutes)

**Goal:** Reusable template for all future UAT scripts

**Technical Approach:**

Create template: `docs/templates/uat-script-template.md`

**Content:**

```markdown
# UAT Script - Epic {{N}}: {{Epic Name}}

**Epic:** Epic {{N}} - {{Epic Name}}
**UAT Tester:** Ricardo (Project Lead)
**Date:** {{date}}
**Feature:** {{feature_name}}
**Expected Duration:** 30-60 minutes

---

## Prerequisites

Before starting UAT, verify all prerequisites are met:

### System Requirements
- [ ] **{{Prerequisite 1}}** (e.g., Claude Desktop installed)
- [ ] **{{Prerequisite 2}}** (e.g., MCP server configured)
- [ ] **{{Prerequisite 3}}** (e.g., Services running)

### {{Feature}} Configuration

[Include feature-specific setup instructions]

### Setup Verification

1. **Step 1:** {{Verification step}}
2. **Step 2:** {{Verification step}}

---

## Test Scenarios

### Test 1: {{Test Name}}

**Category:** {{category}}
**Feature:** {{specific feature being tested}}

**Action:**
{{Clear instruction of what to do}}

**Expected Result:**
- {{Expected outcome 1}}
- {{Expected outcome 2}}
- {{Expected outcome 3}}

**Actual Result:**
```
[Record what actually happened]
```

**Pass/Fail:** _____ (Pass if: {{specific criteria}})

**Notes:**
```
[Any usability issues, suggestions, or observations]
```

---

[Repeat for Tests 2-10]

---

## Results Summary

**Tests Completed:** _____/10

**Tests Passed:** _____/10

**Tests Failed:** _____/10

**Overall Pass Rate:** _____%

**Overall Result:**
- ✅ **PASS** (≥80% pass rate) → Epic approved for completion
- ⚠️ **PARTIAL** (60-79% pass rate) → Create UX improvement stories
- ❌ **FAIL** (<60% pass rate) → Epic NOT complete - fix blocking issues

---

## Usability Feedback

**What worked well:**
```
[Positive observations]
```

**What needs improvement:**
```
[Issues, confusions, or suggestions]
```

**Specific recommendations:**
```
[Concrete suggestions]
```

---

## Critical Issues (Blockers)

If any critical issues prevent testing, document here:

**Issue:**
```
[Describe the blocking issue]
```

**Impact:**
```
[How does this prevent UAT completion?]
```

**Recommended Action:**
```
[What should the team do to resolve this?]
```

---

## UAT Sign-Off

**Tester:** Ricardo (Project Lead)
**Date Completed:** _____
**Overall Result:** _____ (PASS / PARTIAL / FAIL)
**Epic Status:** _____ (Approved / Needs Improvement / Not Complete)

**Signature:** _____

---

**Next Steps (if PASS):**
- Mark Epic {{N}} as complete
- Begin Epic {{N+1}} Prep Sprint
- Address non-blocking UX improvements in future epics

**Next Steps (if PARTIAL):**
- Create UX improvement stories
- Schedule follow-up UAT
- Consider 1-week delay for next epic

**Next Steps (if FAIL):**
- Team meeting to review issues
- Fix blocking issues
- Re-run UAT
```

**Success Criteria:**
- ✅ UAT script template created: `docs/templates/uat-script-template.md`
- ✅ Reusable for all future epics
- ✅ Includes all required sections (Prerequisites, Test Scenarios, Results, Sign-Off)

**Files Created:**
- `docs/templates/uat-script-template.md` (~200 lines)

### AC3: Create Supporting Templates (30 minutes)

**Goal:** Additional templates for data dictionary and module size guidelines

**Technical Approach:**

**Template 1: Data Dictionary Template**

Create: `docs/templates/data-dictionary-template.md`

```markdown
# Data Dictionary - Epic {{N}}

**Generated:** {{date}}
**Source:** {{database/source}}
**Purpose:** Validate test queries align with actual data

---

## Available {{Category 1}}

| Item | Description | Sample Value | Unit |
|------|-------------|--------------|------|
| {{item1}} | {{description}} | {{sample}} | {{unit}} |

**Total:** {{count}}

---

## Data Limitations

### Missing {{Category}}
- ❌ {{missing_item}} (reason)

---

## Test Query Validation Rules

**BEFORE creating ANY test query:**

1. **{{Check 1}}:** {{rule}}
2. **{{Check 2}}:** {{rule}}

---

**Last Updated:** {{date}}
```

**Template 2: Module Size Guidelines**

Create: `docs/coding-standards/module-size.md`

```markdown
# Module Size Guidelines

**Purpose:** Maintain code quality and prevent maintenance nightmares

---

## Hard Limits

- ⚠️ **Warning at 800 lines**
- ❌ **Error at 1000 lines**
- 🎯 **Target: 200-400 lines per file**

---

## When to Split

**File approaches 800 lines:**
- Plan refactor
- Identify logical boundaries
- Schedule refactoring story

**File exceeds 1000 lines:**
- Immediate refactor required
- Block new features until refactored

---

## Refactoring Strategy

1. Identify domain boundaries
2. Split by responsibility (single responsibility principle)
3. Create focused submodules
4. Update imports
5. Maintain 100% test coverage

---

**Example:**

```
IF: module.py is 1500 lines
THEN split into:
  - module/component1.py (300 lines)
  - module/component2.py (400 lines)
  - module/orchestrator.py (200 lines)
```

---

**Enforcement:** Winston includes module size check in architecture review

**Last Updated:** {{date}}
```

**Success Criteria:**
- ✅ Data dictionary template created
- ✅ Module size guidelines created
- ✅ Both templates ready for reuse

**Files Created:**
- `docs/templates/data-dictionary-template.md`
- `docs/coding-standards/module-size.md`

## Tasks / Subtasks

### Task 1: UAT Workflow Documentation (AC1) - 1 hour

- [ ] **Subtask 1.1:** Define 4 phases
  - Readiness, Script Creation, Execution, Review

- [ ] **Subtask 1.2:** Define decision criteria
  - ≥80% PASS, 60-79% PARTIAL, <60% FAIL

- [ ] **Subtask 1.3:** Document integration
  - Sprint status, story context

- [ ] **Subtask 1.4:** Add examples
  - Epic 2, Epic 3 UAT scenarios

### Task 2: UAT Script Template (AC2) - 30 minutes

- [ ] **Subtask 2.1:** Create template structure
  - Prerequisites, Test Scenarios, Results, Sign-Off

- [ ] **Subtask 2.2:** Add placeholders
  - {{Epic N}}, {{test scenarios}}, {{criteria}}

- [ ] **Subtask 2.3:** Include examples
  - Good vs bad test scenario

### Task 3: Supporting Templates (AC3) - 30 minutes

- [ ] **Subtask 3.1:** Create data dictionary template
- [ ] **Subtask 3.2:** Create module size guidelines
- [ ] **Subtask 3.3:** Review all templates

## Dev Notes

### Template Design Principles

**Reusability:**
- Use placeholders: {{variable}}
- Generic structure (works for any epic)
- Examples included for clarity

**Completeness:**
- All required sections
- Pass/fail criteria explicit
- Results format standardized

### References

**Source Documents:**
- [Epic 2 Retrospective](docs/retrospectives/epic-2-retro-2025-11-05.md) - UAT framework gap
- [Epic 3 Prep Tech Spec](docs/tech-spec-epic-3-prep.md#story-304) - UAT templates spec
- [Action Item 3](docs/retrospectives/epic-2-retro-2025-11-05.md#action-item-3-user-acceptance-testing-uat-framework) - UAT framework mandate

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
