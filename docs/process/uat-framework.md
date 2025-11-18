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
