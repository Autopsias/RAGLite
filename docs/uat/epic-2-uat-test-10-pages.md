# UAT Script - Epic 2: Financial Document Queries (10-Page Test Document)

**Epic:** Epic 2 - Advanced RAG Architecture Enhancement
**UAT Tester:** Ricardo (Project Lead)
**Date:** 2025-11-07
**Test Document:** test-10-pages.pdf (Secil Group Financial Data - Aug 2025)
**MCP Tool:** `query_financial_documents`
**Expected Duration:** 30-60 minutes

---

## Prerequisites

✅ **Already Verified:**
- [x] Claude Desktop installed and running
- [x] MCP server configured at `~/.claude/mcp.json`
- [x] Qdrant running (docker ps shows qdrant container)
- [x] PostgreSQL running (docker ps shows postgres container)
- [x] test-10-pages.pdf ingested into RAGLite
- [x] RAGLite MCP server connected (visible in Claude Desktop)

---

## Test Scenarios

### Test 1: Simple Metric Query (SQL Table Search)

**Category:** Basic retrieval from structured data
**Feature Tested:** SQL table search, metric extraction

**Action:**
Ask Claude: "What are the indicators for Secil Portugal in August 2025?"

**Expected Result:**
- Lists performance indicators (operational, financial)
- Values shown with proper units
- Clear citation to page/table
- Response within 5 seconds

**Actual Result:**
```
[Record Claude's response here]
```

**Pass/Fail:** _____ (Pass if: indicators listed, values present, citation included, <5s)

**Notes:**
```
[Any usability issues or observations]
```

---

### Test 2: Period Comparison (Budget vs Actual)

**Category:** Multi-period analysis
**Feature Tested:** Budget comparison detection, period understanding

**Action:**
Ask Claude: "How does August 2025 performance compare to budget for Secil Portugal?"

**Expected Result:**
- Shows both Aug-25 and Budget Aug-25 values
- Variance or comparison mentioned
- Clear labeling of actual vs budget
- Citation to source table

**Actual Result:**
```
[Record Claude's response here]
```

**Pass/Fail:** _____ (Pass if: both values shown, comparison clear, properly labeled)

**Notes:**
```
[Note clarity of budget vs actual distinction]
```

---

### Test 3: Year-over-Year Comparison

**Category:** Historical comparison
**Feature Tested:** Multi-entity or multi-period retrieval

**Action:**
Ask Claude: "Compare August 2025 performance to August 2024 for Secil operations"

**Expected Result:**
- Shows both Aug-25 and Aug-24 values
- Percentage change or variance mentioned (% LY column)
- Clear comparison narrative
- Citations for both periods

**Actual Result:**
```
[Record Claude's response here]
```

**Pass/Fail:** _____ (Pass if: both periods shown, variance/% change included, comparison clear)

**Notes:**
```
[Evaluate comparison quality]
```

---

### Test 4: Entity/Geography Identification

**Category:** Multi-entity query
**Feature Tested:** Entity recognition and differentiation

**Action:**
Ask Claude: "What operational data is available for Secil Lebanon?"

**Expected Result:**
- Correctly identifies Lebanon operations (separate from Portugal)
- Shows relevant metrics for Lebanon entity
- Clear geographic/entity labeling
- Citation to page/section

**Actual Result:**
```
[Record Claude's response here]
```

**Pass/Fail:** _____ (Pass if: Lebanon data found, separated from Portugal, correctly labeled)

**Notes:**
```
[Note entity disambiguation quality]
```

---

### Test 5: Table-Aware Chunking

**Category:** Table retrieval
**Feature Tested:** Large table handling (4096-token threshold)

**Action:**
Ask Claude: "Show me the complete operational performance table for Secil Portugal"

**Expected Result:**
- Multiple metrics from same table retrieved together
- Table structure preserved (columns: Aug-25, Budget Aug-25, Aug-24, % B, % LY)
- All values from same entity/period
- Citation indicates table source

**Actual Result:**
```
[Record Claude's response here]
```

**Pass/Fail:** _____ (Pass if: multiple metrics retrieved, table context clear, structure preserved)

**Notes:**
```
[Evaluate table retrieval quality]
```

---

### Test 6: Currency Context Understanding

**Category:** Currency handling
**Feature Tested:** Currency awareness, exchange rate context

**Action:**
Ask Claude: "What currency are the financial values reported in, and are there any exchange rate impacts mentioned?"

**Expected Result:**
- Identifies currency (likely EUR/Euros)
- Mentions currency exchange impacts if present
- Clear explanation of currency context
- Citation to relevant section

**Actual Result:**
```
[Record Claude's response here]
```

**Pass/Fail:** _____ (Pass if: currency identified, exchange rate context found if applicable)

**Notes:**
```
[Note currency handling clarity]
```

---

### Test 7: YTD (Year-to-Date) Queries

**Category:** Period aggregation understanding
**Feature Tested:** YTD vs monthly period distinction

**Action:**
Ask Claude: "What is the YTD performance for Secil operations in August 2025?"

**Expected Result:**
- Correctly identifies YTD vs monthly metrics
- Shows Year-to-Date cumulative values
- Clear labeling of YTD period
- Citation to YTD section/table

**Actual Result:**
```
[Record Claude's response here]
```

**Pass/Fail:** _____ (Pass if: YTD values found, distinguished from monthly, clearly labeled)

**Notes:**
```
[Evaluate YTD vs monthly distinction clarity]
```

---

### Test 8: Hybrid Search (Semantic + Structured)

**Category:** Hybrid retrieval
**Feature Tested:** Vector search + SQL table search combination

**Action:**
Ask Claude: "Explain Secil Portugal's operational performance context and key metrics for August 2025"

**Expected Result:**
- Combines narrative context (vector search) with structured metrics (SQL search)
- Natural language explanation PLUS specific numbers
- Multiple sources cited (text sections + tables)
- Coherent synthesis

**Actual Result:**
```
[Record Claude's response here]
```

**Pass/Fail:** _____ (Pass if: both narrative and metrics present, multiple sources, coherent)

**Notes:**
```
[Evaluate hybrid search quality and synthesis]
```

---

### Test 9: Source Attribution Accuracy (NFR7)

**Category:** Citation quality
**Feature Tested:** 95%+ source attribution accuracy

**Action:**
Ask Claude: "What page contains the Treasury Preview for Secil Lebanon?"

**Verification Steps:**
1. Note the page number Claude provides
2. Manually verify by checking test-10-pages.pdf
3. Confirm citation accuracy (correct page + section)

**Expected Result:**
- Specific page number cited (page 3, 9, or other)
- Citation accurate when manually verified
- Section or table name included if available

**Actual Result:**
```
Citation provided: Page _____
Manual verification: _____ (✅ Correct / ❌ Incorrect / ⚠️ Partial)
Actual location in PDF: _____
```

**Pass/Fail:** _____ (Pass if: citation specific AND manually verified as correct)

**Notes:**
```
[Evaluate citation specificity and accuracy]
```

---

### Test 10: Response Time Performance (NFR13)

**Category:** Performance
**Feature Tested:** <5s p50 latency, <15s p95 latency

**Action:**
Execute 3 queries and measure response time:

1. "What are the indicators for Secil Portugal?"
2. "Compare August 2025 to budget"
3. "Show YTD performance metrics"

**Expected Result:**
- Median (p50) response time: <5 seconds
- Maximum response time: <15 seconds
- No timeout errors or failures

**Actual Results:**
```
Query 1 response time: _____ seconds
Query 2 response time: _____ seconds
Query 3 response time: _____ seconds

Median (p50): _____ seconds
Max: _____ seconds
```

**Pass/Fail:** _____ (Pass if: median <5s AND max <15s)

**Notes:**
```
[Note any performance issues or slow responses]
```

---

## Results Summary

**Tests Completed:** _____/10

**Tests Passed:** _____/10

**Tests Failed:** _____/10

**Overall Pass Rate:** _____%

**Overall Result:**
- ✅ **PASS** (≥80% pass rate = 8+ tests) → Epic 2 approved for completion
- ⚠️ **PARTIAL** (60-79% pass rate = 6-7 tests) → Create UX improvement stories
- ❌ **FAIL** (<60% pass rate = <6 tests) → Epic 2 NOT complete - fix blocking issues

---

## Usability Feedback

**What worked well:**
```
[Positive observations about the MCP tool experience]
```

**What needs improvement:**
```
[Issues, confusions, or suggestions for better UX]
```

**Specific recommendations:**
```
[Concrete suggestions for improving the query experience]
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
**Epic 2 Status:** _____ (Approved for Completion / Needs Improvement / Not Complete)

**Signature:** _____

---

## Next Steps

**If PASS (≥80%):**
1. Update sprint-status.yaml: `epic-2: done`
2. Document lessons learned
3. Begin Epic 3 feature implementation (agentic orchestration)

**If PARTIAL (60-79%):**
1. Create UX improvement stories for failed tests
2. Schedule follow-up UAT after fixes
3. Consider 1-week delay for Epic 3 if needed

**If FAIL (<60%):**
1. Team meeting to review critical issues
2. Fix blocking usability/accuracy issues
3. Re-run UAT after fixes (must achieve ≥60% to proceed)

---

**Document Version:** 2.0 (Redesigned for test-10-pages.pdf)
**Last Updated:** 2025-11-07
