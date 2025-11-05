# UAT Script - Epic 2: Financial Document Queries

**Epic:** Epic 2 - Advanced RAG Architecture Enhancement
**UAT Tester:** Ricardo (Project Lead)
**Date:** 2025-11-05
**MCP Tool:** `query_financial_documents`
**Expected Duration:** 30-60 minutes

---

## Prerequisites

Before starting UAT, verify all prerequisites are met:

### System Requirements
- [ ] **Claude Desktop installed** (latest version)
- [ ] **MCP server configuration exists** at `~/.claude/mcp.json`
- [ ] **Qdrant running:** `docker ps` shows `qdrant/qdrant` container
- [ ] **PostgreSQL running:** `docker ps` shows PostgreSQL container (port 5432)
- [ ] **Environment variables set:** `.env` file contains `ANTHROPIC_API_KEY`

### MCP Configuration

Add this configuration to `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "raglite": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "raglite.main"
      ],
      "cwd": "/Users/ricardocarvalho/DeveloperFolder/RAGLite",
      "env": {
        "PYTHONPATH": "/Users/ricardocarvalho/DeveloperFolder/RAGLite"
      }
    }
  }
}
```

### Setup Verification

1. **Restart Claude Desktop** after adding MCP configuration
2. **Verify MCP connection:**
   - Open Claude Desktop
   - Look for "RAGLite" in available tools/MCP servers
   - If not visible, check Claude Desktop > Settings > MCP

3. **Test MCP server manually (optional):**
   ```bash
   cd /Users/ricardocarvalho/DeveloperFolder/RAGLite
   uv run python -m raglite.main
   # Server should start without errors
   # Press Ctrl+C to stop
   ```

---

## Test Scenarios

### Test 1: Simple Metric Query (Story 2.13-2.14)

**Category:** SQL Table Search
**Feature:** Basic metric retrieval with period normalization

**Action:**
Ask Claude: "What is the EBITDA for Portugal Cement in August 2025?"

**Expected Result:**
- Numeric value with EUR currency (e.g., "191.8 million EUR")
- Clear citation to source (page number, section, or table)
- Response generated within 5 seconds (p50 latency target)

**Actual Result:**
```
[Record what Claude responds with]
```

**Pass/Fail:** _____ (Pass if: value correct, citation present, <5s response time)

**Notes:**
```
[Any usability issues, unclear responses, or suggestions]
```

---

### Test 2: Period Normalization (Story 2.15)

**Category:** Period Mapping
**Feature:** Q3 2025 → Aug-25 mapping

**Action:**
Ask Claude: "What are Portugal Cement's variable costs in Q3 2025?"

**Expected Result:**
- Value for Q3 period (should map to Aug-25, Sep-25, or Aug-25 YTD)
- Explicitly mentions period (e.g., "In Q3 2025 (August 2025)...")
- Citation to source

**Actual Result:**
```
[Record what Claude responds with]
```

**Pass/Fail:** _____ (Pass if: Q3 mapped correctly, value accurate, citation present)

**Notes:**
```
[Any issues with period understanding or mapping]
```

---

### Test 3: Multi-Entity Comparison (Story 2.14 AC2)

**Category:** SQL Table Search - Multi-Entity
**Feature:** Compare metrics across entities

**Action:**
Ask Claude: "Compare variable costs for Portugal and Tunisia in August 2025"

**Expected Result:**
- Both Portugal and Tunisia values shown
- Difference calculated (e.g., "Portugal: -23.4 EUR/ton, Tunisia: -18.2 EUR/ton, difference: 5.2 EUR/ton")
- Citations for both values

**Actual Result:**
```
[Record what Claude responds with]
```

**Pass/Fail:** _____ (Pass if: both values shown, comparison clear, citations present)

**Notes:**
```
[Any issues with comparison formatting or clarity]
```

---

### Test 4: Fuzzy Entity Matching (Story 2.14 AC1)

**Category:** SQL Table Search - Entity Variations
**Feature:** Handle entity name variations

**Action:**
Ask Claude: "What is the Group DSO in August 2025?"

**Expected Result:**
- Finds entity despite variation (Group → Currency (1000 EUR) mapping)
- Correct DSO value retrieved
- Citation to source

**Actual Result:**
```
[Record what Claude responds with]
```

**Pass/Fail:** _____ (Pass if: fuzzy matching works, value correct, citation present)

**Notes:**
```
[Any issues with entity matching or variations]
```

---

### Test 5: Hybrid Search (Story 2.11)

**Category:** Hybrid Search (Vector + SQL)
**Feature:** Semantic search + structured data retrieval

**Action:**
Ask Claude: "Explain Portugal's financial performance in August 2025"

**Expected Result:**
- Combines structured data (EBITDA, revenue) with narrative context
- Multiple sources cited (tables + text sections)
- Coherent explanation synthesized from both search methods

**Actual Result:**
```
[Record what Claude responds with]
```

**Pass/Fail:** _____ (Pass if: hybrid results evident, synthesis coherent, multiple citations)

**Notes:**
```
[Any issues with hybrid search quality or coherence]
```

---

### Test 6: Table-Aware Chunking (Story 2.8)

**Category:** Table Retrieval
**Feature:** Large tables kept intact (4096-token threshold)

**Action:**
Ask Claude: "What are all the metrics for Portugal Cement in August 2025?"

**Expected Result:**
- Multiple metrics retrieved from same table (EBITDA, Variable Cost, Revenue, etc.)
- Table structure preserved in response
- All values from same period

**Actual Result:**
```
[Record what Claude responds with]
```

**Pass/Fail:** _____ (Pass if: multiple metrics retrieved, table context clear)

**Notes:**
```
[Any issues with table retrieval or structure]
```

---

### Test 7: Currency Limitation Handling (Story 2.14 AC5)

**Category:** Error Handling
**Feature:** Explicit messaging for unavailable currencies

**Action:**
Ask Claude: "What is Angola's EBITDA in million AOA?"

**Expected Result:**
- Explicit message: "Data available in EUR only. Conversion to AOA not supported."
- OR: Value provided in EUR with note that AOA conversion unavailable
- Clear, user-friendly explanation

**Actual Result:**
```
[Record what Claude responds with]
```

**Pass/Fail:** _____ (Pass if: limitation clearly communicated, not confusing or silent failure)

**Notes:**
```
[Evaluate clarity of error messaging]
```

---

### Test 8: Budget vs Actual Detection (Story 2.14 AC4)

**Category:** Period Variants
**Feature:** Distinguish budget from actual periods

**Action:**
Ask Claude: "How did Portugal's variable costs compare to budget in August 2025?"

**Expected Result:**
- Actual and budget values shown (if budget data exists)
- Labels clearly distinguish "Actual" vs "Budget"
- Variance calculated

**Actual Result:**
```
[Record what Claude responds with]
```

**Pass/Fail:** _____ (Pass if: budget/actual labeled, variance shown OR clear message if budget unavailable)

**Notes:**
```
[Any issues with budget data handling]
```

---

### Test 9: Source Attribution Accuracy (NFR7)

**Category:** Citation Quality
**Feature:** 95%+ source attribution accuracy

**Action:**
Ask Claude: "What is Tunisia's EBITDA in August 2025?"

**Verification:**
- Note the citation provided (page, section, table)
- Manually verify citation matches actual source in PDF
- Check if citation is specific (page + section) or vague (page only)

**Expected Result:**
- Citation to specific location (page + section or table)
- Citation accuracy: 95%+ (value actually appears at cited location)

**Actual Result:**
```
Citation provided: _____
Manual verification: _____ (correct / incorrect / partial)
```

**Pass/Fail:** _____ (Pass if: citation specific and accurate)

**Notes:**
```
[Evaluate citation quality and specificity]
```

---

### Test 10: Response Time (NFR13)

**Category:** Performance
**Feature:** <5s p50 latency, <15s p95 latency

**Action:**
Ask Claude 3 queries and measure response time:
1. "What is Brazil's revenue in August 2025?"
2. "Compare EBITDA for all entities in August 2025"
3. "Explain Portugal's margin trends"

**Expected Result:**
- Median response time (p50): <5 seconds
- Maximum response time (p95): <15 seconds
- No timeout errors

**Actual Results:**
```
Query 1 response time: _____ seconds
Query 2 response time: _____ seconds
Query 3 response time: _____ seconds

Median (p50): _____ seconds
Max: _____ seconds
```

**Pass/Fail:** _____ (Pass if: median <5s, max <15s)

**Notes:**
```
[Any performance issues or slow responses]
```

---

## Results Summary

**Tests Completed:** _____/10

**Tests Passed:** _____/10

**Tests Failed:** _____/10

**Overall Pass Rate:** _____%

**Overall Result:**
- ✅ **PASS** (≥80% pass rate) → Epic 2 approved for completion
- ⚠️ **PARTIAL** (60-79% pass rate) → Create UX improvement stories
- ❌ **FAIL** (<60% pass rate) → Epic 2 NOT complete - fix blocking issues

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

**Next Steps (if PASS):**
- Mark Epic 2 as complete
- Begin Epic 3 Preparation Sprint
- Address any non-blocking UX improvements in Epic 3+

**Next Steps (if PARTIAL):**
- Create UX improvement stories for failed tests
- Schedule follow-up UAT after fixes
- Delay Epic 3 by 1 week if needed

**Next Steps (if FAIL):**
- Team meeting to review critical issues
- Fix blocking issues before Epic 2 completion
- Re-run UAT after fixes
