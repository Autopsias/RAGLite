# Story 3.8: Agentic Workflow Test Suite

Status: drafted

## Story

As a developer,
I want to validate agentic workflows against test scenarios,
so that workflow reliability and accuracy are measured objectively.

## Acceptance Criteria

1. **AC1:** Test set includes 15+ multi-step analytical queries
   - Test queries cover all 4 workflow patterns: YoY growth, variance analysis, trend analysis, generic analytical
   - Test queries represent real user scenarios from ground truth set
   - Test queries include expected answers with source citations
   - Test data stored in `tests/fixtures/agentic_workflow_test_set.json`
   - Test queries range from simple 2-step to complex 5-step workflows

2. **AC2:** Automated test suite executes workflows and validates results
   - Integration test suite in `tests/integration/test_agentic_workflow_suite.py`
   - Each test query executed end-to-end via `analytical_query_financial_documents()` MCP tool
   - Validation checks: answer non-empty, citations present, execution time logged
   - Test suite runs in CI/CD pipeline automatically
   - Test failures logged with detailed error context

3. **AC3:** Success rate measured (target: 80%+ per FR16 interpretation)
   - Success = workflow completes, final answer produced, <30s execution, citations present
   - Success rate calculated: `successes / total_queries`
   - Target: ≥80% (13 of 15+ queries succeed)
   - Success rate logged in test summary report
   - Failures categorized by reason (timeout, agent failure, accuracy issue)

4. **AC4:** Performance measured (workflow execution time)
   - Per-query latency tracked: p50, p95, max
   - Performance budget validated: p50 <12s, p95 <20s (NFR5)
   - Latency breakdown by workflow pattern (YoY vs Variance vs Trend)
   - Performance regression detection: alert if p95 >25s
   - Performance metrics logged in structured format

5. **AC5:** Failure analysis documents reasons for unsuccessful workflows
   - Each failure documented with: query, workflow pattern, failure reason, agent failed, stack trace
   - Failure reasons categorized: timeout, LLM API error, retrieval failure, accuracy issue, other
   - Failure report generated after test run: `test-reports/agentic_workflow_failures.json`
   - Failure trends analyzed over time (enable optimization)
   - Actionable insights provided for each failure

6. **AC6:** Test suite covers edge cases (missing data, ambiguous queries, conflicting information)
   - Edge case: Missing data (query for data not in documents) → graceful failure expected
   - Edge case: Ambiguous query ("revenue" without time period) → agent clarification or best-effort response
   - Edge case: Conflicting information (2 sources with different numbers) → synthesis identifies conflict
   - Edge case: Complex multi-document reasoning (requires 5+ chunks) → full workflow execution
   - Edge case: Out-of-domain query (non-financial question) → graceful degradation or refusal
   - All edge cases validated in integration tests

## Tasks / Subtasks

- [ ] **Task 1:** Create comprehensive test query set (AC1) - 3 hours
  - [ ] 1.1: Analyze ground truth set for analytical queries
  - [ ] 1.2: Select 15+ queries covering all 4 workflow patterns
  - [ ] 1.3: Add expected answers and source citations to test data
  - [ ] 1.4: Create `tests/fixtures/agentic_workflow_test_set.json`
  - [ ] 1.5: Structure test data: {query, expected_pattern, expected_sources, success_criteria}
  - [ ] 1.6: Add edge case queries (5+): missing data, ambiguous, conflicting, complex, out-of-domain

- [ ] **Task 2:** Implement automated test suite (AC2) - 4 hours
  - [ ] 2.1: Create `tests/integration/test_agentic_workflow_suite.py`
  - [ ] 2.2: Load test queries from `agentic_workflow_test_set.json`
  - [ ] 2.3: Implement parameterized test: `@pytest.mark.parametrize` for each query
  - [ ] 2.4: Execute each query via `analytical_query_financial_documents()` MCP tool
  - [ ] 2.5: Validate response: answer non-empty, citations present, workflow_metadata included
  - [ ] 2.6: Log execution time and workflow metadata for each query
  - [ ] 2.7: Mark tests as `@pytest.mark.slow` for CI/CD
  - [ ] 2.8: Add test summary reporting (success rate, failures, performance)

- [ ] **Task 3:** Add success rate measurement and reporting (AC3) - 2 hours
  - [ ] 3.1: Calculate success rate: `successes / total_queries`
  - [ ] 3.2: Define success criteria: workflow completes, answer produced, <30s, citations present
  - [ ] 3.3: Log success rate in test summary
  - [ ] 3.4: Assert success rate ≥80% (13 of 15+)
  - [ ] 3.5: Categorize failures by reason (timeout, agent failure, accuracy)
  - [ ] 3.6: Add structured logging for success/failure events

- [ ] **Task 4:** Add performance measurement and validation (AC4) - 2 hours
  - [ ] 4.1: Track per-query latency (start → end timestamp)
  - [ ] 4.2: Calculate p50, p95, max latency across all queries
  - [ ] 4.3: Validate performance budget: p50 <12s, p95 <20s
  - [ ] 4.4: Breakdown latency by workflow pattern (YoY, Variance, Trend, Generic)
  - [ ] 4.5: Log performance metrics in structured format
  - [ ] 4.6: Add performance regression detection (alert if p95 >25s)

- [ ] **Task 5:** Implement failure analysis and reporting (AC5) - 3 hours
  - [ ] 5.1: Create failure report structure: {query, pattern, reason, agent_failed, stack_trace}
  - [ ] 5.2: Capture detailed error context for each failure
  - [ ] 5.3: Categorize failures: timeout, LLM API error, retrieval failure, accuracy issue
  - [ ] 5.4: Generate failure report JSON: `test-reports/agentic_workflow_failures.json`
  - [ ] 5.5: Add actionable insights for each failure type
  - [ ] 5.6: Create failure trend analysis helper function

- [ ] **Task 6:** Add edge case testing (AC6) - 3 hours
  - [ ] 6.1: Test edge case: Missing data query → validate graceful failure
  - [ ] 6.2: Test edge case: Ambiguous query → validate best-effort response
  - [ ] 6.3: Test edge case: Conflicting information → validate conflict identification
  - [ ] 6.4: Test edge case: Complex multi-document reasoning → validate full workflow
  - [ ] 6.5: Test edge case: Out-of-domain query → validate graceful refusal
  - [ ] 6.6: Document expected behavior for each edge case

- [ ] **Task 7:** Documentation and CI/CD integration (AC1-AC6) - 2 hours
  - [ ] 7.1: Document test suite in README: how to run, what it validates
  - [ ] 7.2: Add test data schema documentation
  - [ ] 7.3: Update CI/CD workflow to run agentic test suite
  - [ ] 7.4: Configure test summary reporting in CI
  - [ ] 7.5: Add failure report artifact upload to CI
  - [ ] 7.6: Document how to analyze failure trends

## Dev Notes

### Architecture Context

This story creates a comprehensive test suite to validate the end-to-end agentic workflow system built in Stories 3.1-3.7. It ensures:
- Workflow reliability (80%+ success rate)
- Performance compliance (p50 <12s, p95 <20s)
- Edge case handling (missing data, ambiguous queries, conflicts)
- Failure analysis for continuous improvement

**Testing Philosophy:**
- **Integration Tests**: Test real workflows end-to-end (no mocking of workflow components)
- **Fixtures**: Real test queries from ground truth analytical subset
- **Validation**: Automated success/failure categorization
- **Reporting**: Structured failure analysis for optimization

**Key Integration Points:**
- Uses `analytical_query_financial_documents()` MCP tool (Story 3.6)
- Uses all workflow patterns from Story 3.5 (YoY, Variance, Trend, Generic)
- Validates graceful degradation from Story 3.7
- Tests all 3 agents (Retrieval, Analysis, Synthesis from Stories 3.2-3.4)

**Design Decisions:**

1. **15+ Test Query Minimum:**
   - Why: Statistical significance (80% = 13/15 minimum sample size)
   - Coverage: All 4 workflow patterns + 5 edge cases
   - Real-world queries from ground truth set (representative)

2. **Success Criteria:**
   - Workflow completes (no exceptions)
   - Answer produced (non-empty string)
   - <30s execution time (NFR5 compliance)
   - Citations present (source attribution)
   - Why: Captures both functional correctness and performance

3. **Performance Measurement:**
   - p50 (median): Typical query experience
   - p95: Worst-case acceptable performance
   - Why: p50 <12s ensures good UX, p95 <20s ensures no timeouts

4. **Failure Categorization:**
   - Timeout: Agent or workflow exceeded time budget
   - LLM API Error: Claude/Mistral API failure
   - Retrieval Failure: Qdrant/PostgreSQL issue
   - Accuracy Issue: Workflow completed but answer incorrect
   - Other: Unexpected errors
   - Why: Enables targeted optimization (e.g., if most failures are timeouts → optimize agent latency)

5. **Edge Case Testing:**
   - Missing data: Validates graceful handling when documents don't contain requested info
   - Ambiguous queries: Tests agent clarification or best-effort reasoning
   - Conflicting information: Tests synthesis agent's conflict resolution
   - Complex reasoning: Tests multi-document, multi-step workflows
   - Out-of-domain: Tests scope boundaries (should decline gracefully)

### Project Structure Notes

**New Files:**
```
tests/fixtures/agentic_workflow_test_set.json  (~200 lines NEW)
  - 15+ test queries with expected patterns, sources, success criteria
  - Edge cases with expected behaviors

tests/integration/test_agentic_workflow_suite.py  (~400 lines NEW)
  - Parameterized integration tests for all queries
  - Success rate measurement
  - Performance validation
  - Failure analysis

test-reports/agentic_workflow_failures.json  (generated at runtime)
  - Failure analysis report
  - Structured failure categorization
```

**Total New Code:** ~600 lines (within Epic 3 target)

### Learnings from Previous Stories

**From Story 3-5: Multi-Step Workflow Orchestration** (Status: done)

**Workflow Patterns Implemented:**
- ✅ YoY Growth Workflow (5 tasks: 2 retrievals, 1 analysis, 1 retrieval, 1 synthesis)
- ✅ Variance Analysis Workflow (5 tasks)
- ✅ Trend Analysis Workflow (6 tasks: 4 retrievals, 1 analysis, 1 synthesis)
- ✅ Generic Analytical Workflow (fallback pattern)

**From Story 3-6: Analytical Query Tool MCP** (Status: drafted)

**MCP Tool Integration:**
- ✅ `analytical_query_financial_documents()` tool available
- ✅ Routing logic (simple vs analytical queries)
- ✅ Reasoning steps transparency
- ✅ Workflow metadata in response

**From Story 3-7: Graceful Degradation** (Status: drafted)

**Error Handling Validated:**
- ✅ 4-tier graceful degradation system
- ✅ Timeout handling (per-agent 15s, workflow 30s)
- ✅ Fallback to Epic 1/2 on failures
- ✅ User-friendly error messages

**Implementation Guidance for Story 3.8:**
- ✅ Use `analytical_query_financial_documents()` for all tests (end-to-end validation)
- ✅ Test data from `tests/ground_truth.json` analytical query subset
- ✅ Parameterized tests with `@pytest.mark.parametrize(test_queries)`
- ✅ Success criteria: answer, citations, <30s, workflow metadata
- ✅ Performance assertions: p50 <12s, p95 <20s
- ✅ Failure categorization: match against known error types from Story 3.7

**Files to Reference:**
- `raglite/main.py` - `analytical_query_financial_documents()` MCP tool
- `raglite/agentic/planner.py` - Workflow patterns (478 lines)
- `raglite/agentic/orchestrator.py` - WorkflowExecutor (~350 lines)
- `tests/integration/test_workflow_orchestration.py` - Integration test patterns (450 lines, 12 tests)
- `tests/fixtures/story_3_5_complex_queries.json` - Test query structure reference

[Source: stories/3-5-multi-step-workflow-orchestration.md, stories/3-6-analytical-query-tool-mcp.md, stories/3-7-graceful-degradation-for-workflow-failures.md]

### Test Query Set Structure

**Test Data Schema (`agentic_workflow_test_set.json`):**

```json
{
  "test_queries": [
    {
      "id": "yoy_growth_1",
      "query": "Calculate year-over-year revenue growth from Q3 2023 to Q3 2024",
      "expected_pattern": "yoy_growth",
      "expected_workflow": {
        "task_count": 5,
        "agents": ["retrieval", "retrieval", "analysis", "retrieval", "synthesis"]
      },
      "expected_sources": ["Q3_2023_Report.pdf", "Q3_2024_Report.pdf"],
      "success_criteria": {
        "answer_contains": ["growth", "20%", "Q3 2023", "Q3 2024"],
        "citations_present": true,
        "execution_time_max_ms": 30000
      },
      "edge_case": false
    },
    {
      "id": "edge_missing_data",
      "query": "What was Q5 2025 revenue?",
      "expected_pattern": "retrieval_only",
      "expected_workflow": {
        "task_count": 1,
        "agents": ["retrieval"]
      },
      "expected_sources": [],
      "success_criteria": {
        "answer_contains": ["not found", "unavailable", "no data"],
        "graceful_failure": true
      },
      "edge_case": true,
      "edge_case_type": "missing_data"
    }
    // ... 13+ more queries
  ]
}
```

### Test Categories (15+ queries)

**YoY Growth Queries (3):**
1. "Calculate year-over-year revenue growth from Q3 2023 to Q3 2024"
2. "What is the YoY percentage change in operating expenses?"
3. "Compare annual revenue 2022 vs 2023 and calculate growth rate"

**Variance Analysis Queries (3):**
4. "Why did operating expenses increase in Q3 2024?"
5. "Explain the variance between projected and actual revenue for Q4"
6. "What caused the revenue decline from Q2 to Q3?"

**Trend Analysis Queries (3):**
7. "What is the revenue trend over the last 4 quarters?"
8. "Analyze the quarterly expense trend for 2023"
9. "Identify patterns in profit margins across 2023-2024"

**Generic Analytical Queries (2):**
10. "How do 2023 operating margins compare to 2022?"
11. "What factors contributed to profitability improvement in Q4?"

**Edge Cases (5+):**
12. **Missing Data:** "What was Q5 2025 revenue?" (future data not in documents)
13. **Ambiguous Query:** "What is revenue?" (no time period specified)
14. **Conflicting Information:** "What was Q3 2023 revenue?" (if 2 sources disagree)
15. **Complex Multi-Document:** "Compare Q1, Q2, Q3, Q4 2023 revenue and identify trends"
16. **Out-of-Domain:** "What is the weather forecast for tomorrow?" (non-financial)

### Success Rate Calculation

**Success Criteria:**
```python
def is_successful(response: AnalyticalQueryResponse) -> bool:
    """Determine if workflow execution was successful."""
    return (
        response.answer and len(response.answer) > 50 and  # Non-trivial answer
        response.sources and len(response.sources) > 0 and  # Citations present
        response.workflow_metadata.get("execution_time_ms", 999999) < 30000 and  # <30s
        response.workflow_metadata.get("tier") in ["full_orchestration", "partial_analysis"]  # Not fallback
    )
```

**Success Rate Calculation:**
```python
success_count = sum(1 for response in responses if is_successful(response))
success_rate = success_count / len(responses)

assert success_rate >= 0.80, f"Success rate {success_rate:.1%} below 80% threshold"
```

**Expected Distribution:**
- Tier 1 (Full): 80-90% (12-14 of 15+)
- Tier 2 (Partial): 5-10% (1-2 of 15+)
- Tier 3 (Retrieval): 0-5% (0-1 of 15+)
- Tier 4 (Fallback): 0-5% (0-1 of 15+)

### Performance Budget Validation

**Latency Targets (NFR5):**
- p50: <12s (median query)
- p95: <20s (95th percentile)
- Max: <30s (hard timeout)

**Performance Test:**
```python
def test_performance_budget():
    """Validate workflow performance against NFR5 targets."""
    latencies = [r.workflow_metadata["execution_time_ms"] for r in responses]

    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    max_latency = max(latencies)

    assert p50 < 12000, f"p50 latency {p50}ms exceeds 12s budget"
    assert p95 < 20000, f"p95 latency {p95}ms exceeds 20s budget"
    assert max_latency < 30000, f"Max latency {max_latency}ms exceeds 30s timeout"
```

**Latency Breakdown by Pattern:**
```python
# Expected latencies by workflow pattern
pattern_latencies = {
    "yoy_growth": {"p50": 11000, "p95": 18000},      # 5 tasks
    "variance": {"p50": 12000, "p95": 19000},        # 5 tasks
    "trend": {"p50": 13000, "p95": 20000},           # 6 tasks (more retrievals)
    "generic": {"p50": 10000, "p95": 16000}          # Variable
}
```

### Failure Analysis Report Schema

**Failure Report Structure:**

```json
{
  "test_run_id": "2025-11-16T10:30:00Z",
  "total_queries": 17,
  "successes": 14,
  "failures": 3,
  "success_rate": 0.82,
  "failed_queries": [
    {
      "query_id": "trend_3",
      "query": "Identify patterns in profit margins across 2023-2024",
      "expected_pattern": "trend_analysis",
      "failure_reason": "timeout",
      "agent_failed": "retrieval",
      "error_message": "Retrieval Agent exceeded 15s timeout",
      "stack_trace": "...",
      "workflow_metadata": {
        "tier": "epic1_fallback",
        "execution_time_ms": 30100,
        "task_count": 2  # Only 2 tasks completed before timeout
      },
      "actionable_insight": "Optimize Qdrant query for multi-quarter searches"
    },
    // ... 2 more failures
  ]
}
```

**Failure Categorization:**
- **Timeout** (40% of failures): Agent or workflow exceeded time budget
- **LLM API Error** (30%): Claude/Mistral API 429/500 errors
- **Retrieval Failure** (20%): Qdrant/PostgreSQL connection issues
- **Accuracy Issue** (10%): Workflow completed but answer incorrect/incomplete

### Testing Strategy

**Integration Tests (17 tests, ~300s total, marked `@pytest.mark.slow`):**

1. **Parameterized Query Tests** (15+ tests):
   - Each test query from `agentic_workflow_test_set.json` runs as individual test
   - Validates: answer, citations, execution time, workflow metadata
   - Success criteria checked per query

2. **Success Rate Test** (1 test):
   - Aggregate test validates ≥80% success rate
   - Fails if <13 of 15+ queries succeed

3. **Performance Budget Test** (1 test):
   - Validates p50 <12s, p95 <20s, max <30s
   - Fails if any performance target exceeded

**Test Execution:**
```bash
# Run agentic workflow test suite (slow, ~5 minutes)
uv run pytest tests/integration/test_agentic_workflow_suite.py -v

# Run with failure report generation
uv run pytest tests/integration/test_agentic_workflow_suite.py --json-report --json-report-file=test-reports/agentic_workflow_failures.json
```

**CI/CD Integration:**
- Runs automatically on every PR
- Generates failure report artifact
- Alerts if success rate <80% or p95 >25s
- Tracks success rate trend over time

### Edge Case Testing Details

**Edge Case 1: Missing Data**
- Query: "What was Q5 2025 revenue?" (future quarter not in documents)
- Expected: Graceful failure, Tier 3 or 4 response
- Validation: Answer contains "not found", "unavailable", or "no data for Q5 2025"

**Edge Case 2: Ambiguous Query**
- Query: "What is revenue?" (no time period specified)
- Expected: Best-effort response (e.g., most recent revenue) or clarification request
- Validation: Answer provides context ("Most recent revenue is Q3 2024: $12M")

**Edge Case 3: Conflicting Information**
- Query: "What was Q3 2023 revenue?" (mock 2 sources with different values)
- Expected: Synthesis agent identifies conflict, reports both values
- Validation: Answer mentions "conflicting sources" or shows both values with sources

**Edge Case 4: Complex Multi-Document**
- Query: "Compare Q1, Q2, Q3, Q4 2023 revenue and identify trends"
- Expected: Full workflow with 4 retrievals + analysis + synthesis
- Validation: Answer includes all 4 quarters, trend identified, <30s execution

**Edge Case 5: Out-of-Domain**
- Query: "What is the weather forecast for tomorrow?"
- Expected: Graceful refusal or "not applicable to financial documents"
- Validation: Answer explains scope limitation, suggests financial query

### References

- **Epic 3 PRD:** `docs/prd/epic-3-ai-intelligence-orchestration.md#story-3.8` ⭐ CRITICAL
- **Story 3.5:** `docs/stories/3-5-multi-step-workflow-orchestration.md` (workflow patterns, integration test patterns)
- **Story 3.6:** `docs/stories/3-6-analytical-query-tool-mcp.md` (MCP tool integration)
- **Story 3.7:** `docs/stories/3-7-graceful-degradation-for-workflow-failures.md` (failure handling)
- **Ground Truth Set:** `tests/ground_truth.json` (source of analytical queries)
- **NFR5:** Performance budget (<30s p95)
- **FR16:** Workflow success rate (80%+ target)

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
