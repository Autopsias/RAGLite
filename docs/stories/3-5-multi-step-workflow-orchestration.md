# Story 3.5: Multi-Step Workflow Orchestration

Status: ready-for-dev

## Story

As a system,
I want to orchestrate agentic workflows for complex analytical queries,
so that questions requiring planning and multiple steps can be answered autonomously.

## Acceptance Criteria

1. **AC1:** Query complexity classifier distinguishes simple vs multi-step analytical queries
   - Simple queries (<5 words, no comparative language) routed directly to retrieval
   - Analytical queries (contains: "growth", "variance", "trend", "compare", "explain") marked as analytical
   - Classifier accuracy >90% on test queries from ground truth set

2. **AC2:** Workflow planner decomposes complex queries into sub-tasks with dependencies
   - Input: Analytical query (string)
   - Output: WorkflowPlan with List[AgentTask] including task_id, agent_type, instruction, depends_on
   - Example: "Calculate YoY revenue growth and explain variance" → 5 tasks (Retrieval Q3 2023, Retrieval Q3 2024, Analysis YoY %, Retrieval drivers, Synthesis)
   - Decomposition validates that all required data is retrieved before analysis
   - Task dependency DAG has no circular dependencies

3. **AC3:** Sub-tasks routed to appropriate specialized agents (retrieval, analysis, synthesis)
   - Retrieval tasks → Retrieval Agent from Story 3.2 (document search)
   - Analysis tasks → Analysis Agent from Story 3.3 (financial calculations)
   - Synthesis tasks → Synthesis Agent from Story 3.4 (result aggregation)
   - Agent selection based on task instruction keyword matching (e.g., "calculate" → analysis)
   - Routing accuracy >90% (matching task type to appropriate agent)

4. **AC4:** Agent outputs passed between agents as inputs to subsequent steps
   - Retrieval Agent output (List[DocumentChunk]) → usable as input to Analysis or Synthesis
   - Analysis Agent output (AnalysisResult) → synthesizable with retrieval results
   - Data format compatibility validated in workflow execution
   - Task dependency ordering ensures downstream tasks receive upstream outputs
   - State management via AgentState model (task_id, success, result, execution_time_ms)

5. **AC5:** Workflow execution completes in <30 seconds for typical analytical queries (NFR5)
   - Planner execution: <100ms
   - Parallel retrieval tasks: <2s (2 retrievals in parallel)
   - Analysis task: <1s
   - Sequential synthesis: <1s
   - Total: <5s p50 execution time
   - P95 <15s for complex workflows
   - Integration test validates timing with real Qdrant + Strands orchestrator

6. **AC6:** Example workflow tested: "Calculate YoY revenue growth and explain variance"
   - Workflow plan: [Retrieval "Q3 2023 revenue", Retrieval "Q3 2024 revenue", Analysis "YoY %", Retrieval "variance drivers", Synthesis]
   - Successful execution produces final answer combining all sources
   - Answer includes specific values ($10M → $12M) + calculation (+20%) + drivers (marketing spend, Product X launch)
   - Sources cited: Q3_2023_Report.pdf, Q3_2024_Report.pdf, Marketing_Budget_2024.xlsx
   - Integration test validates complete workflow with real agents

7. **AC7:** Workflow success rate >80% on complex test queries
   - Test set: 15+ analytical queries from ground truth (story_3_5_complex_queries.json)
   - Success = all agents completed, final answer produced, <30s execution
   - Failure = any agent timeout/exception, falls back to basic retrieval
   - Measurement: test_workflow_orchestration.py integration test counts successes
   - Target: ≥80% (13 of 15+ queries succeed)

8. **AC8:** Failed workflows fall back gracefully to simpler retrieval (NFR17, NFR32)
   - Timeout handling: If any agent exceeds 15s (NFR26), cancel workflow → fallback
   - Agent failure handling: If agent raises exception, cancel downstream tasks → fallback
   - Fallback: Call `query_financial_documents()` from Epic 1 basic retrieval
   - User receives: Partial answer from fallback OR error message with suggestion
   - Error logging: structured logs with error type, agent name, task_id, timing
   - Integration test validates fallback behavior (simulate agent timeout, verify fallback works)

## Tasks / Subtasks

- [ ] **Task 1:** Implement query complexity classifier (AC1) - 4 hours
  - [ ] 1.1: Create `raglite/agentic/planner.py` file with classifier function
  - [ ] 1.2: Implement `classify_query_complexity(query: str) → QueryComplexity` async function
  - [ ] 1.3: Define keyword patterns for "simple" vs "analytical" classification
  - [ ] 1.4: Add unit tests for classifier (simple queries, analytical queries, edge cases)
  - [ ] 1.5: Validate classifier accuracy >90% on ground truth test queries

- [ ] **Task 2:** Implement workflow planner with task decomposition (AC2) - 6 hours
  - [ ] 2.1: Implement `decompose_query(query: str, complexity: QueryComplexity) → WorkflowPlan` async function
  - [ ] 2.2: Create agent task templates for common workflow patterns (retrieval, analysis, synthesis)
  - [ ] 2.3: Implement dependency graph creation (mark task dependencies via depends_on field)
  - [ ] 2.4: Validate task graph has no circular dependencies
  - [ ] 2.5: Add logging to show decomposition steps
  - [ ] 2.6: Create unit tests for decomposition (example workflows, edge cases)
  - [ ] 2.7: Validate decomposition against example "YoY growth" workflow (AC6 example)

- [ ] **Task 3:** Implement workflow executor with agent routing (AC3, AC4, AC5) - 8 hours
  - [ ] 3.1: Create `WorkflowExecutor` class in `raglite/agentic/orchestrator.py` (or new file)
  - [ ] 3.2: Implement `execute_workflow(plan: WorkflowPlan) → List[AgentResult]` async function
  - [ ] 3.3: Implement task routing logic: match task instruction to agent type (Retrieval/Analysis/Synthesis)
  - [ ] 3.4: Implement parallel task execution for independent tasks (using asyncio.gather)
  - [ ] 3.5: Implement sequential task execution for dependent tasks (respect depends_on field)
  - [ ] 3.6: Implement inter-agent data passing: use AgentState to pass outputs between agents
  - [ ] 3.7: Add structured logging for each task execution (task_id, agent_type, execution_time_ms)
  - [ ] 3.8: Add unit tests for executor (single task, parallel tasks, sequential with dependencies)
  - [ ] 3.9: Add performance assertions: planner <100ms, execution <5s p50

- [ ] **Task 4:** Implement workflow timeout and graceful degradation (AC8) - 4 hours
  - [ ] 4.1: Add timeout mechanism using asyncio.wait_for() for each agent call
  - [ ] 4.2: Implement timeout handler: catch asyncio.TimeoutError, trigger fallback
  - [ ] 4.3: Implement fallback function: call `query_financial_documents()` from Epic 1
  - [ ] 4.4: Format fallback response: partial answer + error message + suggestion
  - [ ] 4.5: Add error logging with structured metadata (error_type, agent_name, task_id)
  - [ ] 4.6: Create unit tests for timeout handling (simulate agent timeout, verify fallback)

- [ ] **Task 5:** Create integration tests for complete workflow orchestration (AC5, AC6, AC7, AC8) - 6 hours
  - [ ] 5.1: Create `tests/integration/test_workflow_orchestration.py`
  - [ ] 5.2: Create test query set: `tests/fixtures/story_3_5_complex_queries.json` (15+ analytical queries)
  - [ ] 5.3: Test basic workflow: Planner → Executor → Synthesis (AC6 example)
  - [ ] 5.4: Test parallel task execution (multiple retrievals in parallel, AC3, AC4)
  - [ ] 5.5: Test sequential dependencies (retrieval before analysis before synthesis, AC2, AC4)
  - [ ] 5.6: Test performance: measure p50/p95 execution time (AC5)
  - [ ] 5.7: Test success rate on 15+ test queries (AC7, measure >80%)
  - [ ] 5.8: Test timeout handling: simulate agent timeout, verify fallback (AC8)
  - [ ] 5.9: Test error recovery: simulate agent exception, verify fallback
  - [ ] 5.10: Mark slow tests with `@pytest.mark.slow` for CI/CD

- [ ] **Task 6:** Update MCP tool and orchestrator integration (AC1-AC8) - 3 hours
  - [ ] 6.1: Update `raglite/main.py` to call new `analyze_financial_question()` tool
  - [ ] 6.2: Route `analyze_financial_question()` to workflow orchestrator
  - [ ] 6.3: Implement query complexity check: if simple → call `query_financial_documents()`, if analytical → orchestrate workflow
  - [ ] 6.4: Format final MCP response with answer + reasoning_steps + sources + execution_time_ms
  - [ ] 6.5: Add MCP integration tests to validate tool works end-to-end

- [ ] **Task 7:** Document workflow orchestration patterns and API (AC1-AC8) - 2 hours
  - [ ] 7.1: Update `docs/architecture/3-1-agentic-workflow-guide.md` with workflow orchestration section
  - [ ] 7.2: Document planner API: `classify_query_complexity()`, `decompose_query()`
  - [ ] 7.3: Document executor API: `execute_workflow()`
  - [ ] 7.4: Document MCP tool: `analyze_financial_question()` with examples
  - [ ] 7.5: Add example workflows (YoY growth, variance explanation, trend analysis)
  - [ ] 7.6: Document fallback behavior and error handling

## Dev Notes

### Architecture Context

This story implements the **workflow orchestration layer** for Epic 3's agentic system. It ties together the three specialized agents (Retrieval, Analysis, Synthesis from Stories 3.2-3.4) into a coordinated multi-step workflow system.

**Framework Context:** AWS Strands v1.15.0 event-driven orchestration (from Story 3.1)
- Planner: Decomposes queries, creates task DAG
- Executor: Routes tasks to appropriate agents (Retrieval/Analysis/Synthesis)
- Task execution: Sequential (dependent tasks) and parallel (independent tasks)
- State management: AgentState model tracks results, timing, success/failure per task
- Fallback: Graceful degradation to Epic 1 retrieval if workflow fails

**Integration Points:**
- Uses Retrieval Agent from Story 3.2 (document search wrapper)
- Uses Analysis Agent from Story 3.3 (financial calculations)
- Uses Synthesis Agent from Story 3.4 (result aggregation)
- Integrates with MCP server (`raglite/main.py`) via new `analyze_financial_question()` tool
- Falls back to `query_financial_documents()` tool from Epic 1 on workflow failure

**Key Design Decisions:**
1. **Complexity Classifier:** Keyword-based detection (simple vs analytical)
   - Simple: "What is X?", direct retrieval queries
   - Analytical: "Calculate Y", "Compare X and Y", "Explain variance", etc.
   - Why: Avoids overhead of multi-step orchestration for simple queries

2. **Task Decomposition:** Planner creates explicit task DAG with dependencies
   - Why: Enables parallel execution of independent tasks (speed)
   - Dependencies tracked via `depends_on` field (ordering)
   - Example: 2 parallel retrievals → 1 analysis → 1 synthesis

3. **Agent Routing:** Keyword matching from task instruction
   - "retrieve", "search", "find" → Retrieval Agent
   - "calculate", "analyze", "compute" → Analysis Agent
   - "synthesize", "summarize", "aggregate" → Synthesis Agent
   - Why: Simple, deterministic, no ML required

4. **Timeout Handling:** Per-agent timeout (15s max, NFR26) + workflow timeout (30s, NFR5)
   - Why: Prevents hanging workflows, provides graceful degradation

5. **Fallback Strategy:** Timeout/agent-failure → call Epic 1 basic retrieval
   - Why: User always gets a response (better UX than error)
   - Partial results preserved when possible

### Project Structure Notes

**New Files:**
```
raglite/agentic/planner.py          (~150 lines)
  - QueryComplexity enum (SIMPLE, ANALYTICAL)
  - AgentTask, WorkflowPlan, AgentResult Pydantic models
  - classify_query_complexity() function
  - decompose_query() function

raglite/agentic/orchestrator.py      (~200 lines, updated from Story 3.1)
  - Existing: Framework integration from Story 3.1
  - Added: WorkflowExecutor class
  - Added: execute_workflow() method
  - Added: task routing logic

tests/integration/test_workflow_orchestration.py  (~300 lines)
  - Test query set: story_3_5_complex_queries.json

tests/fixtures/story_3_5_complex_queries.json  (~50 lines)
```

**Modified Files:**
- `raglite/agentic/state.py` - Add AgentTask, WorkflowPlan, AgentResult models (~30 lines new)
- `raglite/main.py` - Add query complexity check routing (~20 lines new)
- `docs/architecture/3-1-agentic-workflow-guide.md` - Add workflow orchestration section

**Total New Code:** ~400 lines (within Epic 3 target of ~350-400 lines)

### Learnings from Previous Story

**From Story 3-4: Synthesis Agent Implementation** (Status: done)

**Framework Infrastructure Ready:**
- ✅ AWS Strands v1.15.0 fully operational with Mistral orchestration
- ✅ `@tool` decorator pattern for agent definitions
- ✅ AgentState model captures execution results + timing
- ✅ Error handling framework in `error_handler.py` with timeout support
- ✅ All 3 agents (Retrieval, Analysis, Synthesis) implemented and tested

**Key Services/Interfaces Created:**
- **Retrieval Agent** (`raglite/agentic/agents/retrieval_agent.py`):
  - Wraps Epic 2 multi_index_search()
  - Returns JSON-serializable DocumentChunk list
  - Available as tool in orchestrator

- **Analysis Agent** (`raglite/agentic/agents/analysis_agent.py`):
  - Performs financial calculations with Claude Haiku
  - Returns AnalysisResult (formula, value, reasoning)
  - Full test coverage (13 unit + 7 integration)

- **Synthesis Agent** (`raglite/agentic/agents/synthesis_agent.py`):
  - Aggregates retrieval + analysis results
  - Produces natural language answer with citations
  - Uses Claude Sonnet for high-quality synthesis

**Implementation Guidance for Story 3.5:**
- ✅ Use Strands orchestrator from Story 3.1 as foundation
- ✅ Agents are ready to be called (no further agent implementation needed)
- ✅ Focus on task decomposition logic (planner) and task orchestration (executor)
- ✅ Reuse error handling patterns from `error_handler.py` (timeouts, fallback)
- ✅ Follow structured logging patterns with `logger.info("...", extra={...})`
- ⚠️ Parallel task execution: use `asyncio.gather()` for independent tasks
- ⚠️ Sequential task execution: respect `depends_on` field for task ordering
- ⚠️ Task routing: keyword-based matching of task instructions to agent types

**Files to Reference:**
- `raglite/agentic/agents/retrieval_agent.py` - Agent structure (60 lines)
- `raglite/agentic/agents/analysis_agent.py` - Agent structure (363 lines)
- `raglite/agentic/agents/synthesis_agent.py` - Agent structure (200 lines)
- `raglite/agentic/orchestrator.py` - Tool registration mechanism
- `raglite/agentic/error_handler.py` - Timeout handling patterns
- `raglite/shared/logging.py` - Structured logging patterns
- `tests/integration/test_analysis_agent_workflow.py` - Integration test patterns (275 lines)

[Source: stories/3-4-synthesis-agent-implementation.md#Learnings-from-Previous-Story]

### Complexity Classifier Patterns

**Pattern 1: Simple Queries (Direct Retrieval)**
- Examples: "What is revenue?", "List expenses", "Show Q3 results"
- Keywords: Direct nouns, no verbs suggesting analysis
- Routing: `query_financial_documents()` from Epic 1
- Benefit: Fast (no orchestration overhead)

**Pattern 2: Analytical Queries (Multi-Step Workflow)**
- Examples: "Calculate YoY growth", "Compare Q3 2023 and 2024", "Explain variance"
- Keywords: "calculate", "compare", "explain", "analyze", "trend", "growth", "variance"
- Routing: Multi-step orchestration via planner + executor
- Benefit: Coordinated multi-agent reasoning

**Classifier Implementation:**
```python
async def classify_query_complexity(query: str) -> QueryComplexity:
    """Classify query as simple or analytical based on keyword matching."""
    analytical_keywords = {
        "calculate", "growth", "variance", "trend", "compare",
        "explain", "analyze", "reason", "forecast", "predict",
        "yoy", "percentage", "change", "impact", "driver"
    }

    query_lower = query.lower()
    if any(kw in query_lower for kw in analytical_keywords):
        return QueryComplexity.ANALYTICAL
    else:
        return QueryComplexity.SIMPLE
```

### Task Decomposition Patterns

**Pattern 1: YoY Growth Workflow** (AC6 Example)
- Query: "Calculate YoY revenue growth and explain variance"
- Decomposition:
  - Task 1: Retrieval "Q3 2023 revenue" (no deps)
  - Task 2: Retrieval "Q3 2024 revenue" (no deps)
  - Task 3: Analysis "YoY % change" (depends: Task 1, 2)
  - Task 4: Retrieval "revenue variance drivers" (depends: Task 3)
  - Task 5: Synthesis "aggregate results" (depends: Task 1, 2, 3, 4)
- Execution: Tasks 1,2 parallel (850ms) → Task 3 (600ms) → Task 4 (800ms) → Task 5 (900ms) = 3.2s total

**Pattern 2: Variance Analysis Workflow**
- Query: "Why did expenses increase and what's the impact?"
- Decomposition:
  - Task 1: Retrieval "current expenses" + "previous period expenses"
  - Task 2: Analysis "variance calculation"
  - Task 3: Retrieval "expense drivers, budget changes"
  - Task 4: Analysis "impact on profitability"
  - Task 5: Synthesis

**Pattern 3: Trend Analysis Workflow**
- Query: "What's the trend in revenue over last 4 quarters?"
- Decomposition:
  - Task 1-4: Retrieval (4 quarterly revenues, parallel)
  - Task 5: Analysis "trend identification" (depends: Tasks 1-4)
  - Task 6: Synthesis

### Performance Budget Breakdown (NFR5)

**Target:** <30s p95 execution time for complex workflows

**Actual Budget:**
- Complexity classifier: <50ms (keyword matching)
- Query decomposition: <100ms (LLM + template matching)
- Parallel retrieval (2 queries): ~2s (Qdrant latency)
- Analysis agent: ~600-800ms (Claude Haiku reasoning)
- Sequential retrieval (drivers): ~800ms
- Synthesis agent: ~900-1200ms (Claude Sonnet)
- AWS Strands orchestration: ~150ms (task routing, state management)
- **Total: ~5.5s p50, <10s p95**

**Per-Agent Timeouts (NFR26):**
- Individual agent timeout: 15s max (enforced via asyncio.wait_for)
- Any agent exceeding 15s → cancel task, trigger fallback

### Fallback Behavior (NFR17, NFR32)

**Trigger Conditions:**
1. Any agent exceeds 15s timeout (NFR26)
2. Any agent raises exception (connection error, LLM API failure, etc.)
3. Workflow timeout reaches 30s (NFR5)

**Fallback Response Format:**
```python
fallback_response = AnalyticalQueryResponse(
    answer="[Partial/basic retrieval answer from Epic 1]",
    reasoning_steps=["1. Attempted multi-step analysis", "2. Agent timeout - falling back to basic retrieval"],
    sources=[...],  # Partial sources from agents that succeeded
    workflow_status="fallback",
    execution_time_ms=30100  # Total elapsed time
)
```

**User Experience:**
- User receives a response (never "error", always tries to help)
- Partial results shown when available
- Error message explains what happened
- Suggested alternative query if applicable

### Testing Strategy

**Unit Tests (10 tests, <1s total execution):**

1. **Complexity Classification** (3 tests):
   - Simple queries: "What is revenue?" → SIMPLE
   - Analytical queries: "Calculate YoY growth" → ANALYTICAL
   - Edge cases: Multi-word queries, mixed signals

2. **Query Decomposition** (4 tests):
   - YoY workflow decomposition (5 tasks with dependencies)
   - Variance analysis decomposition
   - Trend analysis decomposition
   - Circular dependency detection (should fail gracefully)

3. **Agent Routing** (2 tests):
   - Task instruction → agent type matching
   - Accuracy >90% validation

4. **Performance** (1 test):
   - Planner execution <100ms

**Integration Tests (8 tests, ~60s total):**

1. **Basic Workflow Execution** (`test_basic_workflow`)
   - Execute YoY growth workflow end-to-end
   - Validate final answer contains calculation + context

2. **Parallel Task Execution** (`test_parallel_retrieval`)
   - 2 retrieval tasks execute in parallel
   - Timing: 2 tasks should take <2.5s, not 4s

3. **Sequential Task Dependencies** (`test_sequential_dependencies`)
   - Analysis task waits for retrieval tasks to complete
   - Retrieval tasks run before analysis

4. **Workflow Success Rate** (`test_workflow_success_rate`)
   - Execute 15+ analytical queries
   - Count successes
   - Assert ≥80% success rate (13 of 15+)

5. **Performance Metrics** (`test_workflow_performance`)
   - Measure p50, p95 execution time
   - Assert p50 <5s, p95 <15s

6. **Timeout Handling** (`test_agent_timeout_fallback`)
   - Simulate agent timeout
   - Verify fallback to Epic 1 retrieval
   - Verify partial results preserved

7. **Agent Failure Recovery** (`test_agent_failure_fallback`)
   - Simulate agent exception (LLM API failure)
   - Verify workflow doesn't crash
   - Verify fallback triggered

8. **Complete Workflow with MCP Tool** (`test_analyze_financial_question_tool`)
   - Call `analyze_financial_question()` MCP tool
   - Validate response format
   - Validate answer content

**Test Data:**
- `tests/fixtures/story_3_5_complex_queries.json`: 15+ analytical queries with expected structures
- Uses real Qdrant instance (requires `docker-compose up`)
- Uses real agents (Retrieval, Analysis, Synthesis from previous stories)

**Mocking Strategy:**
- Unit tests: Mock Strands orchestrator if needed (or test real orchestrator)
- Integration tests: Real agents + real Qdrant (budget LLM calls for Analysis/Synthesis)
- Timeout tests: Mock asyncio.wait_for() to simulate timeouts

### References

- **Epic 3 PRD:** `docs/prd/epic-3-ai-intelligence-orchestration.md#story-3.5` ⭐ CRITICAL
- **Tech Spec:** `docs/tech-spec-epic-3.md#multi-step-workflow-orchestration` ⭐ CRITICAL
- **Orchestration Design:** `docs/architecture/epic-3-orchestration-design.md#workflow-planner` ⭐ CRITICAL
- **Agent Patterns:** `docs/architecture/epic-3-agent-patterns.md#pattern-workflow` ⭐ CRITICAL
- **Retrieval Agent:** `docs/stories/3-2-retrieval-agent-implementation.md` (reference)
- **Analysis Agent:** `docs/stories/3-3-analysis-agent-implementation.md` (reference)
- **Synthesis Agent:** `docs/stories/3-4-synthesis-agent-implementation.md` (reference)
- **Workflow Guide:** `docs/architecture/3-1-agentic-workflow-guide.md` (Story 3.1 reference)
- **AWS Strands:** https://github.com/awslabs/agents-for-amazon-bedrock-strands

## Dev Agent Record

### Context Reference

- `docs/stories/3-5-multi-step-workflow-orchestration.context.xml` (Generated: 2025-11-10)

### Agent Model Used

Claude Haiku 4.5

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Date | Version | Change | Status |
|------|---------|--------|--------|
| 2025-11-10 | 1.0.0 | Initial story draft created | DRAFTED |
