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
