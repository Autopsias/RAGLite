# Story 3.6 Manual Testing Guide

## Overview

This document provides instructions for manually testing Story 3.6: Analytical Query Tool (MCP) via Claude Desktop.

**Story:** `docs/sprint-artifacts/3-6-analytical-query-tool-mcp.md`

**Features to validate:**
- AC1: MCP tool defined (analytical_query_financial_documents)
- AC2: AnalyticalQueryRequest/Response models
- AC3: Conditional routing (simple → Epic 2, analytical → Epic 3)
- AC4: Reasoning steps transparency
- AC5: Test query validation (trend analysis, variance, YoY)
- AC6: Source citations

---

## Prerequisites

### 1. Start RAGLite MCP Server

```bash
cd /Users/ricardocarvalho/DeveloperFolder/RAGLite

# Start Qdrant and PostgreSQL
docker-compose up -d

# Start MCP server
uv run python -m raglite.main
```

### 2. Configure Claude Desktop

Ensure Claude Desktop has RAGLite configured in MCP settings (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "raglite": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/ricardocarvalho/DeveloperFolder/RAGLite",
        "python",
        "-m",
        "raglite.main"
      ]
    }
  }
}
```

### 3. Ingest Test Documents

Ensure at least one financial document is ingested:

```bash
# Example: Ingest a sample financial report
uv run python -c "
import asyncio
from raglite.ingestion.pipeline import ingest_document
asyncio.run(ingest_document('/path/to/financial_report.pdf'))
"
```

---

## Test Cases

### AC1 & AC2: Tool Discovery and Model Validation

**Test:** Verify the `analytical_query_financial_documents` tool is available in Claude Desktop.

**Steps:**
1. Open Claude Desktop
2. Start a new conversation
3. Check available MCP tools (Claude should show RAGLite tools)
4. Look for `analytical_query_financial_documents` in the tools list

**Expected Result:** Tool is visible and callable from Claude Desktop.

---

### AC3: Conditional Routing - Simple Query

**Test:** Verify simple queries route to Epic 2 basic retrieval.

**Test Query:**
```
Using the analytical_query_financial_documents tool:
What is the total revenue for Q3 2023?
```

**Expected Response Fields:**
- `complexity`: "simple"
- `workflow_metadata.workflow_pattern`: "simple_retrieval"
- `workflow_metadata.fallback_tier`: "epic2_routing"
- `workflow_metadata.task_count`: 1
- `confidence`: "high"
- `reasoning_steps`: Should include steps like:
  1. Classified query as simple (direct retrieval)
  2. Retrieved N relevant documents via vector search
  3. Ranked results by similarity score
- `sources`: List of source documents with page numbers

**Validation:**
- ✅ Simple query routed to Epic 2 (not full workflow)
- ✅ Reasoning steps explain routing decision
- ✅ Sources provided with page references

---

### AC3: Conditional Routing - Analytical Query

**Test:** Verify analytical queries route to Epic 3 workflow orchestration.

**Test Query:**
```
Using the analytical_query_financial_documents tool:
Calculate the year-over-year revenue growth from Q3 2022 to Q3 2023 and explain the main drivers of variance.
```

**Expected Response Fields:**
- `complexity`: "analytical"
- `workflow_metadata.workflow_pattern`: "yoy_growth" or "variance_analysis"
- `workflow_metadata.task_count`: >= 4 (retrieval + analysis + synthesis tasks)
- `confidence`: "high", "medium", or "low"
- `reasoning_steps`: Should include workflow steps like:
  1. Classified query as analytical (yoy_growth pattern)
  2. Retrieved previous period data
  3. Retrieved current period data
  4. Performed analysis: Calculate year-over-year revenue growth percentage
  5. Synthesized final answer from N workflow tasks
- `sources`: List of source documents from retrieval tasks

**Validation:**
- ✅ Analytical query routed to Epic 3 workflow
- ✅ Multiple workflow tasks executed
- ✅ Reasoning steps show workflow execution transparently
- ✅ Sources include documents from all retrieval steps

---

### AC4: Reasoning Steps Transparency

**Test:** Verify reasoning steps are transparent and informative across query types.

**Test Queries:**

1. **Simple Query:**
   ```
   What is the company's total debt?
   ```

   **Expected `reasoning_steps`:**
   - Step 1: Classification decision
   - Step 2: Retrieval action with result count
   - Step 3: Ranking method

2. **Analytical Query:**
   ```
   Analyze the trend in operating expenses over the past 4 quarters.
   ```

   **Expected `reasoning_steps`:**
   - Step 1: Classification as analytical (trend_analysis pattern)
   - Steps 2-5: Retrieval tasks for each quarter
   - Step 6: Analysis task (trend identification)
   - Step 7: Synthesis task

**Validation:**
- ✅ Reasoning steps present in all responses
- ✅ Steps are numbered sequentially
- ✅ Steps describe what the system did (not just what it will do)
- ✅ Steps reference specific tasks and results

---

### AC5: Test Query Validation

**Test:** Verify diverse query types are handled correctly.

#### 5.1 YoY Comparison Query

**Test Query:**
```
Compare Q3 2023 revenue to Q3 2022 and calculate year-over-year growth.
```

**Expected:**
- Complexity: "analytical"
- Pattern: "yoy_growth"
- Task count: >= 4
- Reasoning includes retrieval for both periods + analysis + synthesis

#### 5.2 Variance Analysis Query

**Test Query:**
```
Explain why operating expenses increased in Q3 compared to budget.
```

**Expected:**
- Complexity: "analytical"
- Pattern: "variance_analysis"
- Reasoning includes variance drivers retrieval
- Answer includes explanation of variance causes

#### 5.3 Trend Analysis Query

**Test Query:**
```
Analyze revenue trends over the past 4 quarters.
```

**Expected:**
- Complexity: "analytical"
- Pattern: "trend_analysis"
- Task count: >= 6 (4 retrievals + 1 analysis + 1 synthesis)
- Reasoning shows retrieval for each period

#### 5.4 Simple Factual Query

**Test Query:**
```
What is the company's total debt?
```

**Expected:**
- Complexity: "simple"
- Pattern: "simple_retrieval"
- Task count: 1
- Fast response time

**Validation:**
- ✅ All query types handled appropriately
- ✅ Complexity classification accurate
- ✅ Workflow patterns match query intent

---

### AC6: Source Citations

**Test:** Verify source citations are present and properly formatted.

**Test Query (any analytical query):**
```
Calculate YoY revenue growth and identify the main drivers.
```

**Expected `sources` field:**
```json
[
  "Q3_2022_Financial_Report.pdf (page 5)",
  "Q3_2023_Financial_Report.pdf (page 5)",
  "Q3_2023_Variance_Analysis.pdf (page 12)"
]
```

**Validation:**
- ✅ `sources` field is a list of strings
- ✅ Each source includes document name
- ✅ Page numbers included when available
- ✅ Sources deduplicated (no duplicates)
- ✅ Sources match documents mentioned in reasoning steps

---

## Graceful Degradation Testing

**Test:** Verify fallback behavior when workflows fail.

**Test Query (edge case that might trigger fallback):**
```
Calculate YoY revenue growth, analyze variance drivers, identify trends, and forecast next quarter's performance.
```

**Expected Response (if fallback triggered):**
- `workflow_metadata.fallback_tier`: "partial", "epic1_fallback", or "full"
- `reasoning_steps`: Includes fallback explanation
  - Example: "Workflow failed: [error message]"
  - Example: "Gracefully degraded to [tier] tier"
- `limitations`: List of caveats about answer quality
- `sources`: Still present (from fallback retrieval)

**Validation:**
- ✅ System provides answer even when workflow fails
- ✅ Reasoning explains what went wrong
- ✅ Fallback tier tracked in metadata
- ✅ Limitations communicated to user

---

## Automated Integration Tests

### Run MCP Compliance Tests (No Data Required)

```bash
# Run tests that validate tool structure and models
uv run pytest tests/integration/test_analytical_query_tool.py::TestMCPToolCompliance -v
```

**Expected:** 3 tests pass
- test_analytical_query_tool_registered
- test_analytical_query_request_model_valid
- test_analytical_query_response_model_has_required_fields

### Run Full Integration Tests (Requires Ingested Data)

```bash
# Run all integration tests (requires Qdrant with data)
uv run pytest tests/integration/test_analytical_query_tool.py --no-skip -v
```

**Note:** These tests are skipped by default in CI. Run manually after ingesting test documents.

**Expected:** 15 tests covering:
- Conditional routing (2 tests)
- Reasoning transparency (3 tests)
- Source citations (3 tests)
- Query types (4 tests)
- Graceful degradation (2 tests)
- Response consistency (1 test)

---

## Success Criteria

### Story 3.6 is COMPLETE when:

- ✅ **AC1**: MCP tool `analytical_query_financial_documents` discoverable in Claude Desktop
- ✅ **AC2**: `AnalyticalQueryRequest` and `AnalyticalQueryResponse` models working
- ✅ **AC3**: Simple queries route to Epic 2, analytical queries route to Epic 3 workflow
- ✅ **AC4**: All responses include transparent `reasoning_steps` explaining what happened
- ✅ **AC5**: Test queries validated:
  - YoY comparison queries work
  - Variance analysis queries work
  - Trend analysis queries work
  - Simple factual queries work
- ✅ **AC6**: All responses include `sources` with document names and page references

### Additional Validation

- MCP compliance tests pass (3/3)
- Integration tests pass with ingested data (15/15)
- Claude Desktop manual testing confirms usability
- Reasoning steps are clear and helpful to users
- Source citations enable answer verification

---

## Troubleshooting

### Issue: Tool not appearing in Claude Desktop

**Solution:**
1. Restart Claude Desktop after MCP config changes
2. Verify server path in `claude_desktop_config.json`
3. Check server logs for startup errors

### Issue: "Collection doesn't exist" error

**Solution:**
1. Ensure Qdrant is running: `docker-compose ps`
2. Initialize collection: `python scripts/init-qdrant.py`
3. Ingest at least one document

### Issue: Reasoning steps empty or unclear

**Solution:**
- Check implementation in `raglite/main.py` lines 390-395 (simple path)
- Check implementation in `raglite/main.py` lines 470-491 (analytical path)
- Verify workflow execution in logs

### Issue: Sources missing or incorrectly formatted

**Solution:**
- Check source extraction in `raglite/main.py` lines 397-403 (simple path)
- Check source extraction in `raglite/main.py` lines 493-511 (analytical path)
- Verify retrieval results have proper metadata

---

## Notes

- **Performance:** Simple queries ~2-5s, analytical queries ~10-30s depending on complexity
- **Fallback:** System gracefully degrades to Epic 1 retrieval if workflows fail
- **Transparency:** Reasoning steps intentionally verbose for debugging and user trust
- **Sources:** Page numbers may be `None` for chunked content without page info

---

## Related Files

- **Implementation:** `raglite/main.py` (lines 278-616)
- **Models:** `raglite/shared/models.py` (lines 216-258)
- **Tests:** `tests/integration/test_analytical_query_tool.py`
- **Story:** `docs/sprint-artifacts/3-6-analytical-query-tool-mcp.md`
