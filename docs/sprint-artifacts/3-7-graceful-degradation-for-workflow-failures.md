# Story 3.7: Graceful Degradation for Workflow Failures

Status: drafted

## Story

As a system,
I want to handle agentic workflow failures gracefully,
so that users receive useful responses even when complex workflows fail.

## Acceptance Criteria

1. **AC1:** Workflow timeout handling (>30 seconds triggers fallback)
   - Per-workflow timeout: 30s max (NFR5)
   - Per-agent timeout: 15s max (NFR26)
   - Timeout detected via asyncio.wait_for() in workflow executor
   - Timeout triggers fallback to basic retrieval (Epic 1/2)
   - Timeout logged with structured metadata (query, tier, timeout_ms)

2. **AC2:** Agent failure detection and logging
   - Agent execution errors caught: connection errors, LLM API failures, timeout errors
   - Structured logging for each failure type with error context
   - Failure metadata includes: agent_name, task_id, error_type, error_message, stack_trace (if available)
   - Failures logged at WARNING level (not ERROR - graceful degradation is expected)
   - Log aggregation enables failure trend analysis

3. **AC3:** Fallback to basic retrieval when workflow fails (NFR17, NFR32)
   - Fallback triggered on: any agent timeout, any agent exception, workflow timeout
   - Fallback path: Call `query_financial_documents()` from Epic 1/2
   - Fallback response includes: partial results (if available), error context, suggested alternative query
   - Fallback always returns a response (never complete failure)
   - Fallback tier indicated in response metadata: "epic1_fallback"

4. **AC4:** User receives partial results or error message with suggested alternative query
   - Partial results preserved when available (e.g., retrieval succeeded but analysis failed)
   - Error message explains what happened without technical jargon
   - Suggested alternative query provided when possible (e.g., "Try a simpler query like 'What was Q3 revenue?'")
   - Response format: answer (partial or fallback), limitations (list of what failed), error_summary (user-friendly)
   - User experience: always helpful, never "error 500"

5. **AC5:** Error rates logged for workflow improvement
   - Metrics tracked: tier_1_success_rate, tier_2_fallback_rate, tier_3_fallback_rate, tier_4_epic1_rate
   - Metrics logged to structured logs with query_id for correlation
   - Target rates: Tier 1 ≥95%, Tier 2 <5%, Tier 3 <1%, Tier 4 <0.1%
   - Metrics enable monitoring dashboards (Epic 5)
   - Metrics enable A/B testing and workflow optimization

6. **AC6:** Integration test validates fallback behavior
   - Test scenarios: agent timeout, agent LLM API failure, workflow timeout, Qdrant connection failure
   - Each scenario validates: fallback triggered, partial results preserved, user-friendly error message
   - Test coverage: all 4 degradation tiers (full, partial, retrieval-only, epic1-fallback)
   - Success criteria: ≥90% of failure scenarios handled gracefully
   - Integration tests marked `@pytest.mark.slow` for CI/CD

## Tasks / Subtasks

- [ ] **Task 1:** Enhance timeout handling and failure detection (AC1, AC2) - 3 hours
  - [ ] 1.1: Review existing timeout implementation in `raglite/agentic/fallback.py`
  - [ ] 1.2: Add workflow-level timeout (30s) wrapping entire orchestration
  - [ ] 1.3: Add per-agent timeout (15s) for each agent invocation (already in Story 3.5)
  - [ ] 1.4: Enhance error detection: classify errors by type (timeout, connection, API, unexpected)
  - [ ] 1.5: Add structured logging for each failure type with context
  - [ ] 1.6: Create unit tests for error classification logic

- [ ] **Task 2:** Implement user-friendly error messages and alternative query suggestions (AC4) - 2 hours
  - [ ] 2.1: Create error message templates for each failure type
  - [ ] 2.2: Add alternative query suggestion logic based on failure type
  - [ ] 2.3: Format partial results when available (show what succeeded)
   - [ ] 2.4: Create `FallbackResponseFormatter` class for consistent user messaging
  - [ ] 2.5: Add unit tests for error message formatting
  - [ ] 2.6: Add examples to docstrings (timeout, API failure, partial success)

- [ ] **Task 3:** Add metrics tracking for workflow degradation (AC5) - 2 hours
  - [ ] 3.1: Create `WorkflowMetrics` model with tier success rates
  - [ ] 3.2: Add metrics logging after each workflow execution
  - [ ] 3.3: Log degradation events with structured metadata (tier, query_id, error_type)
  - [ ] 3.4: Add metrics aggregation helper function for analysis
  - [ ] 3.5: Create unit tests for metrics tracking logic

- [ ] **Task 4:** Create integration tests for graceful degradation scenarios (AC6) - 4 hours
  - [ ] 4.1: Create `tests/integration/test_graceful_degradation.py`
  - [ ] 4.2: Test scenario: Agent timeout (simulate with mock delay)
  - [ ] 4.3: Test scenario: LLM API failure (simulate with mock exception)
  - [ ] 4.4: Test scenario: Workflow timeout (30s)
  - [ ] 4.5: Test scenario: Qdrant connection failure
  - [ ] 4.6: Test scenario: Partial success (retrieval + analysis succeed, synthesis fails)
  - [ ] 4.7: Validate fallback response format for each scenario
  - [ ] 4.8: Validate partial results preserved when available
  - [ ] 4.9: Validate user-friendly error messages included
  - [ ] 4.10: Mark tests as `@pytest.mark.slow` for CI/CD

- [ ] **Task 5:** Document graceful degradation behavior and failure handling (AC1-AC6) - 2 hours
  - [ ] 5.1: Add "Error Handling" section to `docs/architecture/epic-3-orchestration-design.md`
  - [ ] 5.2: Document 4-tier degradation strategy with examples
  - [ ] 5.3: Document failure types and corresponding fallback behaviors
  - [ ] 5.4: Document metrics tracked and alerting thresholds
  - [ ] 5.5: Add user-facing documentation on what happens when workflows fail
  - [ ] 5.6: Update MCP tool docstring with failure handling examples

- [ ] **Task 6:** Add monitoring hooks for production observability (AC5) - 2 hours
  - [ ] 6.1: Add OpenTelemetry span attributes for degradation tier
  - [ ] 6.2: Add custom metrics for Tier 1/2/3/4 rates (CloudWatch-ready format)
  - [ ] 6.3: Add log aggregation tags for error trend analysis
  - [ ] 6.4: Document metrics export format for Epic 5 monitoring setup
  - [ ] 6.5: Create example CloudWatch dashboard JSON (for future Epic 5 deployment)

## Dev Notes

### Architecture Context

This story enhances and validates the graceful degradation system already implemented in Story 3.5. Story 3.5 built the core fallback mechanism (`raglite/agentic/fallback.py`), and this story focuses on:
1. Production-grade error handling and messaging
2. Metrics tracking for observability
3. Comprehensive integration testing of failure scenarios

**Core Graceful Degradation System (from Story 3.5):**
- ✅ `execute_with_timeout()`: Per-agent timeout handling (15s)
- ✅ `fallback_to_basic_retrieval()`: Fallback to Epic 1/2 search
- ✅ `handle_workflow_failure()`: Orchestrates graceful degradation logic
- ✅ `FallbackResponse`: 3-tier quality hierarchy (full → partial → epic1_fallback)
- ✅ 14 unit tests for timeout and fallback scenarios

**What Story 3.7 Adds:**
- ✅ Workflow-level timeout (30s) wrapping entire orchestration
- ✅ User-friendly error messages and alternative query suggestions
- ✅ Metrics tracking for degradation tier rates
- ✅ Integration tests for real-world failure scenarios
- ✅ Production observability hooks (OpenTelemetry, CloudWatch-ready)

**Design Decisions:**

1. **4-Tier Graceful Degradation (Pattern 4 from agent-patterns.md):**
   - **Tier 1 (Full Orchestration):** All 3 agents succeed → confidence: HIGH
   - **Tier 2 (Partial Analysis):** Retrieval + Analysis succeed, Synthesis fails → confidence: MEDIUM
   - **Tier 3 (Retrieval Only):** Only Retrieval succeeds → confidence: LOW
   - **Tier 4 (Epic 1/2 Fallback):** All agents fail → confidence: NONE (fallback to simple search)

2. **User-Friendly Error Messages:**
   - NO technical jargon (no "asyncio.TimeoutError", no stack traces)
   - YES helpful context (what failed, what partial results are available)
   - YES alternative suggestions ("Try a simpler query like...")
   - Example: "Our analysis system is experiencing delays. Here are the raw documents we found: [chunks]. For faster results, try asking 'What was Q3 revenue?'"

3. **Metrics Tracking:**
   - Tier rates logged after EVERY workflow execution
   - Metrics in structured logs for aggregation (CloudWatch Insights, DataDog, etc.)
   - Target thresholds: Tier 1 ≥95%, Tier 2 <5%, Tier 3 <1%, Tier 4 <0.1%
   - Alert if Tier 1 <90% or Tier 4 >1% (indicates systemic failure)

4. **Timeout Strategy:**
   - Per-agent timeout: 15s (NFR26) - prevents single agent from hanging
   - Workflow timeout: 30s (NFR5) - ensures total query <30s p95
   - Timeouts cascading: Agent timeout → try next tier, Workflow timeout → fallback immediately

5. **Integration Testing Philosophy:**
   - Mock external dependencies (Qdrant, LLM APIs) to simulate failures
   - Test REAL fallback code paths (not mocked)
   - Validate user experience (error messages, partial results)
   - Cover all 4 degradation tiers

### Project Structure Notes

**Files Modified:**
```
raglite/agentic/fallback.py               (~100 lines added)
  - Add workflow-level timeout wrapper
  - Add FallbackResponseFormatter class
  - Add alternative query suggestion logic
  - Add metrics tracking integration

raglite/agentic/orchestrator.py           (~30 lines added)
  - Add workflow timeout wrapper around execute_workflow()
  - Add metrics logging after execution

raglite/shared/models.py                  (~20 lines added)
  - Add WorkflowMetrics model
  - Add error_summary, alternative_query fields to responses

tests/integration/test_graceful_degradation.py  (~400 lines NEW)
  - Integration tests for all degradation tiers
  - Real failure scenario testing

tests/unit/test_fallback_response_formatter.py  (~150 lines NEW)
  - Unit tests for error message formatting
  - Unit tests for alternative query suggestions
```

**Total New Code:** ~700 lines (within Epic 3 target)

### Learnings from Previous Story

**From Story 3-5: Multi-Step Workflow Orchestration** (Status: done)

**Graceful Degradation Infrastructure Already Built:**
- ✅ `raglite/agentic/fallback.py` (280 lines) - Core fallback logic
- ✅ `execute_with_timeout()` - Per-agent timeout via asyncio.wait_for()
- ✅ `fallback_to_basic_retrieval()` - Epic 1/2 fallback path
- ✅ `handle_workflow_failure()` - Orchestrates degradation tiers
- ✅ `FallbackResponse` model - 3-tier quality hierarchy
- ✅ 14 unit tests in `test_workflow_timeout.py` (401 lines)

**What's Already Working:**
- Per-agent timeout (15s) catches hung agents
- Fallback to Epic 1/2 search on complete failure
- 3-tier degradation system (full → partial → epic1_fallback)
- Basic error logging with structured metadata

**What Story 3.7 Needs to Add:**
- Workflow-level 30s timeout (not just per-agent)
- User-friendly error messages (current: technical error strings)
- Alternative query suggestions (current: none)
- Metrics tracking for tier rates (current: logs only, no aggregation)
- Integration tests for real failure scenarios (current: unit tests with mocks)
- Production observability hooks (current: logs only)

**Implementation Guidance:**
- ✅ Build on existing `raglite/agentic/fallback.py` - don't rewrite
- ✅ Enhance `handle_workflow_failure()` with user-friendly messaging
- ✅ Add `FallbackResponseFormatter` class for consistent error messages
- ✅ Add `WorkflowMetrics` tracking to `WorkflowExecutor`
- ✅ Test real failure paths using mocked external dependencies (Qdrant, LLM APIs)

**Files to Reference:**
- `raglite/agentic/fallback.py` - Core fallback logic (280 lines)
- `raglite/agentic/orchestrator.py` - WorkflowExecutor class (~350 lines)
- `tests/unit/test_workflow_timeout.py` - Timeout testing patterns (401 lines, 14 tests)
- `raglite/shared/models.py` - Response models

[Source: stories/3-5-multi-step-workflow-orchestration.md#Task-4-Complete]

### Graceful Degradation Tier Examples

**Tier 1: Full Orchestration (95% success rate)**
```
User Query: "Calculate YoY revenue growth from Q3 2023 to Q3 2024"

Response:
{
  "answer": "Revenue grew 20% year-over-year from Q3 2023 ($10M) to Q3 2024 ($12M). This growth was driven by increased Product X sales (+35%) and new market expansion in APAC region. [Source: Q3_2023_Report.pdf, page 5; Q3_2024_Report.pdf, page 7]",
  "tier": "full_orchestration",
  "confidence": "high",
  "reasoning_steps": [
    "1. Retrieval Agent: Retrieved Q3 2023 and Q3 2024 financial reports",
    "2. Analysis Agent: Calculated 20% YoY growth rate",
    "3. Synthesis Agent: Generated final answer with citations"
  ],
  "limitations": []
}
```

**Tier 2: Partial Analysis (4% success rate)**
```
User Query: "Calculate YoY revenue growth from Q3 2023 to Q3 2024"

Response:
{
  "answer": "Based on the analysis (synthesis unavailable):\n• Q3 2023 revenue: $10M (Page 5, confidence: 0.95)\n• Q3 2024 revenue: $12M (Page 7, confidence: 0.95)\n• YoY growth: 20% (calculated)\n\nNote: Our synthesis system is temporarily unavailable, so this is raw analysis without full context.",
  "tier": "partial_analysis",
  "confidence": "medium",
  "reasoning_steps": [
    "1. Retrieval Agent: Retrieved documents",
    "2. Analysis Agent: Extracted facts and calculated growth",
    "3. Synthesis Agent: FAILED (timeout)"
  ],
  "limitations": ["Synthesis agent unavailable - showing analyzed facts without full synthesis"],
  "error_summary": "Analysis complete, but final synthesis timed out"
}
```

**Tier 3: Retrieval Only (0.9% success rate)**
```
User Query: "Calculate YoY revenue growth from Q3 2023 to Q3 2024"

Response:
{
  "answer": "Found 5 relevant documents (analysis unavailable):\n\n[1] Q3 2023 revenue: $10M, up 15% from Q2... (Page 5)\n[2] Q3 2024 revenue: $12M, driven by Product X growth... (Page 7)\n[3] APAC market expansion contributed $1.5M... (Page 12)\n\nNote: Our analysis system is unavailable. You may need to manually calculate growth from the above numbers.",
  "tier": "retrieval_only",
  "confidence": "low",
  "reasoning_steps": [
    "1. Retrieval Agent: Retrieved 5 documents",
    "2. Analysis Agent: FAILED (LLM API error)",
    "3. Synthesis Agent: SKIPPED"
  ],
  "limitations": [
    "Analysis and synthesis unavailable",
    "Showing raw document chunks without interpretation"
  ],
  "error_summary": "Unable to analyze data - LLM service temporarily unavailable",
  "alternative_query": "Try a simpler query like 'What was Q3 2024 revenue?'"
}
```

**Tier 4: Epic 1/2 Fallback (0.1% success rate)**
```
User Query: "Calculate YoY revenue growth from Q3 2023 to Q3 2024"

Response:
{
  "answer": "⚠️ Our advanced analysis system is experiencing issues. Here's what we found using basic search:\n\nRelevant documents:\n• Q3 2023 Financial Report (Page 5): Revenue section\n• Q3 2024 Financial Report (Page 7): Revenue section\n• Marketing Analysis 2024 (Page 12): Growth drivers\n\nFor fastest results, try asking: 'What was Q3 2024 revenue?'",
  "tier": "epic1_fallback",
  "confidence": "none",
  "reasoning_steps": [
    "1. Retrieval Agent: FAILED (Qdrant connection error)",
    "2. Fallback: Used Epic 1/2 basic search"
  ],
  "limitations": [
    "All Epic 3 agents unavailable",
    "Showing Epic 2 baseline search results",
    "No analysis or calculation performed"
  ],
  "error_summary": "System temporarily unavailable - showing basic search results",
  "alternative_query": "Try simpler queries like 'What was Q3 revenue?' or wait a few minutes and retry"
}
```

### Metrics Tracking Schema

**Logged After Every Workflow Execution:**

```python
workflow_metrics = {
    "query_id": "uuid-1234-5678",
    "query": "Calculate YoY revenue growth...",
    "tier": "full_orchestration",  # or partial_analysis, retrieval_only, epic1_fallback
    "confidence": "high",  # or medium, low, none
    "execution_time_ms": 11500,
    "agents_invoked": ["retrieval", "analysis", "synthesis"],
    "agents_failed": [],  # or ["synthesis"] if Tier 2
    "error_type": None,  # or "timeout", "api_failure", "connection_error"
    "timestamp": "2025-11-16T10:30:00Z"
}
```

**Aggregated Metrics (for monitoring dashboards):**
- `tier_1_success_rate = count(tier="full_orchestration") / count(total_workflows)`
- `tier_2_fallback_rate = count(tier="partial_analysis") / count(total_workflows)`
- `tier_3_fallback_rate = count(tier="retrieval_only") / count(total_workflows)`
- `tier_4_epic1_rate = count(tier="epic1_fallback") / count(total_workflows)`

**Alert Thresholds:**
- Alert: `tier_1_success_rate < 0.90` (90%) → Degraded service
- Alert: `tier_4_epic1_rate > 0.01` (1%) → Systemic failure

### Testing Strategy

**Unit Tests (10 tests, <1s total):**
1. **Error Message Formatting** (4 tests):
   - Timeout error → user-friendly message
   - API failure error → user-friendly message
   - Connection error → user-friendly message
   - Partial success → includes partial results

2. **Alternative Query Suggestions** (3 tests):
   - Complex analytical query failure → suggest simpler query
   - Timeout → suggest retry or simpler query
   - No suggestion available → None returned

3. **Metrics Tracking** (3 tests):
   - Metrics logged for Tier 1 success
   - Metrics logged for Tier 2/3/4 failures
   - Metrics aggregation helper function

**Integration Tests (6 tests, ~60s total, marked `@pytest.mark.slow`):**

1. **Agent Timeout Scenario** (`test_agent_timeout_fallback`)
   - Mock agent with 20s delay (exceeds 15s timeout)
   - Verify fallback triggered
   - Verify user-friendly error message
   - Verify partial results preserved

2. **LLM API Failure Scenario** (`test_llm_api_failure_fallback`)
   - Mock LLM API raising HTTPError
   - Verify fallback to next tier
   - Verify error message explains issue

3. **Workflow Timeout Scenario** (`test_workflow_timeout_30s`)
   - Mock slow workflow exceeding 30s
   - Verify workflow timeout triggers immediate fallback
   - Verify Tier 4 epic1_fallback used

4. **Qdrant Connection Failure** (`test_qdrant_connection_failure`)
   - Mock Qdrant client raising ConnectionError
   - Verify fallback to Epic 1/2 search
   - Verify Tier 4 response

5. **Partial Success Scenario** (`test_partial_success_tier2`)
   - Mock synthesis agent failure (timeout)
   - Verify retrieval + analysis results preserved
   - Verify Tier 2 response format

6. **All Tiers Coverage** (`test_all_degradation_tiers`)
   - Validate all 4 tiers can be reached
   - Validate tier transitions logical
   - Validate metrics tracked for each tier

### References

- **Epic 3 PRD:** `docs/prd/epic-3-ai-intelligence-orchestration.md#story-3.7` ⭐ CRITICAL
- **Orchestration Design:** `docs/architecture/epic-3-orchestration-design.md#error-handling-strategy` ⭐ CRITICAL
- **Agent Patterns:** `docs/architecture/epic-3-agent-patterns.md#pattern-4-error-fallback` ⭐ CRITICAL
- **Story 3.5:** `docs/stories/3-5-multi-step-workflow-orchestration.md#Task-4-Complete` (fallback implementation)
- **Fallback Module:** `raglite/agentic/fallback.py` (280 lines, Story 3.5 baseline)
- **NFR17:** Graceful degradation requirement
- **NFR26:** Per-agent timeout (15s)
- **NFR32:** Fallback to simple search requirement

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
