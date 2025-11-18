# Epic Technical Specification: AI Intelligence & Orchestration

Date: 2025-11-05 (Updated: 2025-11-07)
Author: Ricardo
Epic ID: 3
Status: Ready for Implementation (Architecture Complete)

---

## Overview

Epic 3 introduces agentic orchestration capabilities to RAGLite, enabling multi-step reasoning and complex analytical workflows through specialized AI agents. The system will autonomously decompose complex financial queries (e.g., "Calculate YoY revenue growth and explain variance"), orchestrate retrieval and analysis tasks across multiple agents, and synthesize comprehensive answers with full source attribution.

This epic builds upon the high-accuracy retrieval foundation established in Epic 1-2 (70%+ retrieval accuracy validated) and implements a lightweight agentic framework using AWS Strands (v1.15.0) with Mistral model integration. The architecture prioritizes simplicity, transparency, and graceful degradation—workflows that fail revert to Epic 1's basic retrieval without disrupting user experience.

## Architecture Documentation

**Complete architecture documentation created during Story 3.0.8:**

1. **[Architecture Index](./architecture/epic-3-index.md)** - Navigation guide to all Epic 3 architecture docs
2. **[Framework Selection ADR](./architecture/epic-3-framework-selection.md)** - AWS Strands decision (84.5% weighted score)
3. **[Orchestration Design](./architecture/epic-3-orchestration-design.md)** - 3-agent system architecture
4. **[Agent Workflow Patterns](./architecture/epic-3-agent-patterns.md)** - 5 reusable workflow patterns
5. **[Story 3.0.8 Context](./stories/3-0-8-agentic-framework-architecture-spike.context.xml)** - Implementation guidance

**Key Decisions:**
- **Framework:** AWS Strands (Apache 2.0, standalone, no AWS infrastructure required)
- **Model:** Mistral Small for orchestration (tunable to Claude)
- **Architecture:** 3-agent sequential chain (Retrieval → Analysis → Synthesis)
- **LOC:** 350 total (within 600-800 budget)
- **Performance:** <10s p50, <20s p95 target
- **Approved By:** Ricardo (2025-11-07)

**For implementation details, see the Architecture Index above.**

## Objectives and Scope

###  In Scope

**Agentic Framework Integration (Story 3.1):**
- Implement agentic orchestration framework (LangGraph or native function calling per Architecture decision)
- Configure workflow execution engine with state management
- Establish basic 2-step workflow validation (retrieve → synthesize)
- Implement error handling and timeout mechanisms (NFR24, NFR26)

**Specialized Agent Implementation (Stories 3.2-3.4):**
- **Retrieval Agent:** Wrapper around Epic 1-2 retrieval logic, exposing search as agent tool
- **Analysis Agent:** Financial calculations (YoY growth, variance analysis, trend detection, percentage calculations)
- **Synthesis Agent:** Multi-source result aggregation with coherent narrative generation

**Multi-Step Workflow Orchestration (Story 3.5):**
- Query complexity classifier (simple vs multi-step analytical queries)
- Task decomposition engine (break complex queries into sub-tasks)
- Agent routing logic (match sub-tasks to specialized agents)
- Inter-agent communication and state management

**MCP Integration (Story 3.6):**
- New MCP tool: `analyze_financial_question()` exposing agentic workflows
- Backward compatibility with `query_financial_documents()` (Epic 1 tool)
- Transparent reasoning steps in MCP responses
- Performance monitoring and execution time tracking

**Graceful Degradation (Story 3.7):**
- Workflow timeout handling (>30s triggers fallback to Epic 1)
- Agent failure detection and structured logging
- Fallback to Epic 1 basic retrieval when workflows fail
- Partial result return with error explanations

**Test Suite (Story 3.8):**
- 15+ complex analytical test queries
- Automated workflow success rate measurement (target: 80%+)
- Performance validation (<30s p95 execution time per NFR5)
- Failure mode analysis and documentation

### Out of Scope

**NOT Included in Epic 3:**
- Long-term learning or adaptive query rewriting (deferred to Phase 4)
- Multi-document comparison workflows (handled by existing retrieval)
- Real-time streaming of agent reasoning (Claude Desktop displays final results only)
- Agent performance A/B testing infrastructure (deferred to Phase 4)
- Custom LLM fine-tuning for agent prompts (use prompt engineering only)

**Dependencies on Other Epics:**
- Epic 1: Retrieval logic (✅ COMPLETE)
- Epic 2: High-accuracy retrieval foundation (✅ COMPLETE at 70-80%)
- Epic 4: Forecasting capabilities (NOT required for Epic 3)

## System Architecture Alignment

Epic 3 maintains RAGLite's **monolithic architecture** philosophy from Architecture v1.1, adding a lightweight orchestration layer within the existing `raglite/` package. No new services or databases are introduced—agents operate within the same Python process, sharing Qdrant and PostgreSQL connections established in Epic 1-2.

**📚 Reference:** See [epic-3-orchestration-design.md](./architecture/epic-3-orchestration-design.md) for complete system architecture, C4 diagrams, and agent specifications.

**Alignment with Architecture Principles:**
- **Simplicity First:** Agents are simple Python async functions (~50 lines each), not complex frameworks
- **Direct SDK Usage:** AWS Strands used as-is with `@tool` decorator pattern, no custom wrappers
- **Stateless Execution:** Each workflow execution is independent, no persistent agent state
- **Monolithic Deployment:** All agents run in single Docker container (raglite-server)
- **Event-Driven:** Strands' model-driven orchestration with automatic task routing

**Component Integration:**
- `raglite/orchestration/` module (~350 lines total) added to existing monolithic structure
- Agents call existing `retrieval/search.py`, `retrieval/synthesis.py` from Epic 1-2 (no duplication)
- MCP server (`main.py`) exposes new `analyze_financial_question()` tool alongside existing tools
- Shared logging, configuration, and error handling via `raglite/shared/` (no new infrastructure)

**Technology Stack Alignment:**
- **Framework:** AWS Strands v1.15.0 (Apache 2.0, standalone)
  - **Decision:** Per [epic-3-framework-selection.md](./architecture/epic-3-framework-selection.md) - 84.5% weighted score
  - **Approval:** Ricardo (2025-11-07) via Story 3.0.8
  - **Model:** Mistral Small (mistral-small-latest) for orchestration
  - **Integration:** MistralModel with `settings.mistral_api_key` (no AWS Bedrock required)
- **No New Infrastructure:** Reuses Qdrant, PostgreSQL, Mistral API, FastMCP from Epic 1-2
- **Deployment:** Same Docker Compose setup, no additional containers

**Repository Structure Alignment:**
- Follows CLAUDE.md structure: 15-file monolithic target (~800 lines total across files)
- Epic 3 adds: `orchestration/orchestrator.py`, `orchestration/*_agent.py` (3 agents), `orchestration/fallback.py`
- Total new code: ~350 lines (within 600-800 budget per Architecture section 8)

**📚 Reference:** See [epic-3-agent-patterns.md](./architecture/epic-3-agent-patterns.md) for 5 reusable workflow patterns with production-ready code examples.

## Detailed Design

**📚 Architecture Reference:** For complete agent specifications, C4 diagrams, and workflow patterns, see:
- [epic-3-orchestration-design.md](./architecture/epic-3-orchestration-design.md) - System architecture
- [epic-3-agent-patterns.md](./architecture/epic-3-agent-patterns.md) - Reusable patterns with code

### Services and Modules

**Implementation Overview:**
Epic 3 uses AWS Strands' `@tool` decorator pattern for agent definitions. The orchestrator (Strands Agent with MistralModel) coordinates 3 specialized agents in a sequential chain workflow.

| Module | File | Lines | Responsibilities | Inputs | Outputs | Owner |
|--------|------|-------|-----------------|--------|---------|-------|
| **Workflow Planner** | `raglite/orchestration/planner.py` | ~80 | Query complexity detection, task decomposition, agent routing, state management | User query (str) | Orchestration plan (List[AgentTask]) | Dev |
| **Retrieval Agent** | `raglite/orchestration/retrieval_agent.py` | ~50 | Wrapper around Epic 1-2 search logic, exposes retrieval as agent tool | Search query (str), top_k (int) | List[QueryResult] with chunks + citations | Dev |
| **Analysis Agent** | `raglite/orchestration/analysis_agent.py` | ~50 | Financial calculations (YoY, variance, trends), numerical reasoning with LLM | Financial data points (Dict[str, float]), analysis type (str) | AnalysisResult with calculation + explanation | Dev |
| **Synthesis Agent** | `raglite/orchestration/synthesis_agent.py` | ~50 | Multi-source result aggregation, coherent narrative generation with citations | Sub-task results (List[AgentResult]), original query (str) | Final answer (str) with reasoning steps | Dev |
| **Fallback Handler** | `raglite/orchestration/fallback.py` | ~20 | Graceful degradation, timeout handling, basic retrieval fallback | Workflow failure (Exception), partial results (Optional) | Fallback response with error context | Dev |
| **MCP Tool Integration** | `raglite/main.py` (updated) | +30 | New `analyze_financial_question()` tool, routing logic, MCP response formatting | AnalyticalQueryRequest (Pydantic model) | MCP tool response with reasoning steps | Dev |

**Total New Code:** ~280 lines (within Epic 3 target of ~250-300 lines)

**Module Dependencies:**
- All agents import from `raglite/retrieval/` (Epic 1-2 logic - no code duplication)
- All agents use `raglite/shared/clients.py` for Claude API access (shared connection pool)
- All agents use `raglite/shared/logging.py` for structured logging (consistent format)
- Planner imports agent modules, orchestrates execution flow via LangGraph or function calling

### Data Models and Contracts

**Core Workflow Models:**

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum

class QueryComplexity(str, Enum):
    """Query complexity classification"""
    SIMPLE = "simple"          # Single retrieval, no analysis
    ANALYTICAL = "analytical"  # Multi-step, requires calculation/reasoning

class AgentType(str, Enum):
    """Specialized agent types"""
    RETRIEVAL = "retrieval"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"

class AgentTask(BaseModel):
    """Individual sub-task for an agent"""
    task_id: str
    agent_type: AgentType
    instruction: str
    depends_on: Optional[List[str]] = None  # Task IDs that must complete first

class AgentResult(BaseModel):
    """Result from a single agent execution"""
    task_id: str
    agent_type: AgentType
    success: bool
    result: Any  # QueryResult, AnalysisResult, or str (synthesis)
    execution_time_ms: int
    error: Optional[str] = None

class WorkflowPlan(BaseModel):
    """Complete workflow execution plan"""
    query: str
    complexity: QueryComplexity
    tasks: List[AgentTask]
    estimated_duration_ms: int

class AnalysisResult(BaseModel):
    """Result from Analysis Agent"""
    calculation: str  # e.g., "(12M - 10M) / 10M = 0.20"
    value: float  # 0.20
    formatted_value: str  # "+20%"
    reasoning: str  # LLM-generated explanation
    data_points_used: Dict[str, float]  # {"Q3_2023_revenue": 10.0, "Q3_2024_revenue": 12.0}

class AnalyticalQueryRequest(BaseModel):
    """MCP tool input for analyze_financial_question()"""
    query: str = Field(..., description="Complex analytical financial question")
    enable_reasoning_steps: bool = Field(True, description="Include intermediate reasoning steps in response")
    timeout_seconds: int = Field(30, description="Workflow timeout before fallback")

class AnalyticalQueryResponse(BaseModel):
    """MCP tool output"""
    answer: str = Field(..., description="Final synthesized answer")
    reasoning_steps: List[str] = Field(default_factory=list, description="Transparent workflow steps")
    sources: List[str] = Field(default_factory=list, description="Source citations")
    workflow_status: str = Field(..., description="'success', 'fallback', or 'error'")
    execution_time_ms: int
```

**Entity Relationships:**
- `WorkflowPlan` → contains multiple `AgentTask` objects (task decomposition)
- `AgentTask` → executed by agent, produces `AgentResult` (1:1 mapping)
- Multiple `AgentResult` objects → aggregated by Synthesis Agent → final `AnalyticalQueryResponse`

**Database Schema Changes:**
- **No new tables required** (agents operate stateless, no persistent storage)
- Existing `QueryResult` model from Epic 1 reused by Retrieval Agent (no duplication)
- Workflow execution logs stored via structured logging (JSON to stdout, CloudWatch ingestion)

### APIs and Interfaces

**New MCP Tool: `analyze_financial_question`**

```python
@mcp.tool()
async def analyze_financial_question(request: AnalyticalQueryRequest) -> str:
    """
    Analyze complex financial questions using multi-step agentic workflows.

    Automatically detects query complexity:
    - Simple queries → Fallback to query_financial_documents() (Epic 1)
    - Analytical queries → Orchestrate Retrieval + Analysis + Synthesis agents

    Args:
        request: AnalyticalQueryRequest with query, reasoning flag, timeout

    Returns:
        JSON string with AnalyticalQueryResponse model

    Raises:
        WorkflowTimeoutError: If execution exceeds timeout_seconds
        AgentExecutionError: If agent fails and fallback unsuccessful

    Example:
        >>> await analyze_financial_question(AnalyticalQueryRequest(
        ...     query="Calculate YoY revenue growth and explain variance",
        ...     enable_reasoning_steps=True,
        ...     timeout_seconds=30
        ... ))
        {
          "answer": "Revenue grew 20% YoY (Q3 2023: $10M → Q3 2024: $12M)...",
          "reasoning_steps": ["1. Retrieved Q3 2023 revenue: $10M", ...],
          "sources": ["Q3_2023_Report.pdf (page 12)", ...],
          "workflow_status": "success",
          "execution_time_ms": 2850
        }
    """
```

**Agent Tool Interfaces:**

```python
# Retrieval Agent
async def retrieve_documents(
    query: str,
    top_k: int = 5,
    filters: Optional[Dict[str, Any]] = None
) -> List[QueryResult]:
    """
    Search financial documents (wrapper around Epic 1-2 retrieval).

    Args:
        query: Specific search query (decomposed from complex query)
        top_k: Number of results to return
        filters: Optional metadata filters (company, fiscal_period, etc.)

    Returns:
        List of QueryResult objects with chunks and citations
    """

# Analysis Agent
async def analyze_financial_data(
    data: Dict[str, float],
    analysis_type: str,  # "yoy_growth", "variance", "trend", "percentage"
    context: Optional[str] = None
) -> AnalysisResult:
    """
    Perform financial calculations and reasoning.

    Args:
        data: Financial data points (e.g., {"Q3_2023_revenue": 10.0, "Q3_2024_revenue": 12.0})
        analysis_type: Type of analysis to perform
        context: Optional contextual information for LLM reasoning

    Returns:
        AnalysisResult with calculation, value, and reasoning
    """

# Synthesis Agent
async def synthesize_answer(
    sub_results: List[AgentResult],
    original_query: str
) -> str:
    """
    Aggregate multi-agent results into coherent final answer.

    Args:
        sub_results: Results from retrieval and analysis agents
        original_query: User's original query for context

    Returns:
        Natural language answer with citations and reasoning
    """
```

**Error Codes and HTTP Status (MCP Protocol):**

| Error | Code | Description | Resolution |
|-------|------|-------------|-----------|
| `WORKFLOW_TIMEOUT` | -32000 | Execution exceeded timeout_seconds | Fallback to basic retrieval |
| `AGENT_EXECUTION_ERROR` | -32001 | Agent failed during execution | Log error, fallback to basic retrieval |
| `INVALID_QUERY` | -32602 | Query empty or malformed | Return validation error to user |
| `DECOMPOSITION_FAILED` | -32002 | Planner couldn't decompose query | Fallback to basic retrieval |

### Workflows and Sequencing

**Workflow Example: "Calculate YoY revenue growth and explain variance"**

```
Step 1: Query Analysis (Planner) → QueryComplexity.ANALYTICAL [50ms]
    ↓
Step 2: Task Decomposition (Planner) → WorkflowPlan with 5 tasks [100ms]
    Task A: Retrieval - "Q3 2023 revenue" (no dependencies)
    Task B: Retrieval - "Q3 2024 revenue" (no dependencies)
    Task C: Analysis - "YoY growth calculation" (depends: A, B)
    Task D: Retrieval - "revenue variance drivers" (depends: C)
    Task E: Synthesis - "Aggregate results" (depends: A,B,C,D)
    ↓
Step 3: Parallel Execution (Tasks A & B concurrently) [~850ms]
    Task A: "$10M" (source: Q3_2023_Report.pdf, page 12)
    Task B: "$12M" (source: Q3_2024_Report.pdf, page 12)
    ↓
Step 4: Sequential Execution (Task C) [600ms]
    Analysis: "(12M - 10M) / 10M = 0.20" → +20% YoY growth
    ↓
Step 5: Sequential Execution (Task D) [800ms]
    Retrieval: "30% increase in marketing spend, Product X launch Q2 2024"
    ↓
Step 6: Final Synthesis (Task E) [900ms]
    Output: "Revenue grew 20% YoY (Q3 2023: $10M → Q3 2024: $12M).
             The variance is primarily due to 30% increase in marketing
             spend and launch of Product X in Q2 2024."
    Sources: Q3_2023_Report.pdf (p.12), Q3_2024_Report.pdf (p.12),
             Marketing_Budget_2024.xlsx
    ↓
Step 7: Response Formatting → AnalyticalQueryResponse [total: 3200ms]
    workflow_status: "success"
    reasoning_steps: ["1. Retrieved Q3 2023 revenue: $10M", ...]
```

**Total Execution Time:** ~3.2 seconds (well under 30s NFR5 target)

**Workflow Failure Scenario (Timeout):**

```
Steps 1-4: Normal execution completed [~2.3s]
    ↓
Step 5: Task D (Retrieval Agent) - TIMEOUT [28s]
    (Qdrant search hanging, network issue)
    Total elapsed: 30.3s > timeout_seconds (30s)
    ↓
Step 6: Fallback Handler Triggered
    - Cancel Task D and Task E
    - Call query_financial_documents() from Epic 1
    - Use partial results from Tasks A, B, C
    ↓
Output: AnalyticalQueryResponse
    workflow_status: "fallback"
    answer: "I found revenue data but couldn't complete the full
             analysis. Q3 2024 revenue was $12M (20% increase from
             Q3 2023), but I couldn't retrieve variance context due
             to timeout."
    execution_time_ms: 30100
```

**Actor Interaction:**
- **User** → Claude Code/Desktop → MCP Client
- **MCP Client** → calls `analyze_financial_question()` MCP tool
- **Planner** → decomposes query → creates `WorkflowPlan`
- **Agents** → execute tasks (Retrieval, Analysis, Synthesis)
- **Synthesis Agent** → aggregates results → returns final answer
- **MCP Tool** → formats response → returns to MCP Client → User

## Non-Functional Requirements

### Performance

**NFR5: Query Response Time**
- **Target:** <30 seconds p95 for analytical workflows
- **Measurement:** End-to-end execution time from MCP tool invocation to response
- **Validation:** Performance tests on 15+ analytical queries (Story 3.8)

**Performance Budget Breakdown:**
- Query analysis + task decomposition: ~150ms
- Parallel retrieval (2 agents): ~800-1000ms (reuses Epic 1-2 optimized search)
- Analysis agent (1 LLM call): ~600-800ms (Claude Haiku for speed)
- Synthesis agent (1 LLM call): ~900-1200ms (Claude Sonnet for quality)
- Total estimated: ~2.5-3.2 seconds typical, ~8-12 seconds p95 (well under 30s)

**Optimization Strategies:**
- Parallel agent execution where no dependencies (e.g., multiple retrievals)
- Use Claude Haiku for Analysis Agent (faster, cheaper, sufficient for calculations)
- Cache intermediate results within workflow execution (avoid redundant LLM calls)
- Timeout enforcement at 25 seconds (5s buffer for fallback response)

**NFR13: Response Time Impact**
- Epic 1 basic retrieval: <5s p50, <15s p95 (baseline - no change)
- Epic 3 analytical workflows: <10s p50, <30s p95 (acceptable for complex queries)
- Simple queries routed to Epic 1 (no performance regression)

### Security

**NFR10: Data Privacy**
- No agent state persisted beyond workflow execution (stateless agents)
- All data passed between agents in-memory (no external storage)
- Source citations maintain document-level attribution (no leakage across documents)

**NFR11: API Key Security**
- Claude API key used for Analysis and Synthesis agents (same as Epic 1)
- No new API keys required (LangGraph is local Python library if selected)
- API key rotation supported via existing `pydantic-settings` configuration

**Agent Prompt Security:**
- System prompts for agents include guardrails against prompt injection
- Agent instructions validated before execution (no user-provided code execution)
- LLM responses parsed and validated against Pydantic schemas (type safety)

**Error Information Disclosure:**
- Internal errors logged with full stack traces (structured logging)
- User-facing errors sanitized (no stack traces exposed via MCP)
- Fallback responses include generic error messages ("workflow timeout") not specifics

### Reliability/Availability

**NFR17: Graceful Degradation**
- **Target:** 100% of workflow failures result in fallback response (no hard errors)
- **Validation:** Integration tests simulate agent failures (network errors, LLM timeouts)
- **Mechanism:** `raglite/orchestration/fallback.py` catches exceptions, calls Epic 1 retrieval

**Failure Scenarios Handled:**
1. **Agent Timeout:** Single agent exceeds 10s → Cancel agent, fallback to partial results
2. **Workflow Timeout:** Total execution exceeds 30s → Cancel remaining tasks, return partial results
3. **LLM API Error:** Claude API 429/500 → Retry once (exponential backoff), then fallback
4. **Decomposition Failure:** Planner can't parse query → Fallback to Epic 1 basic retrieval
5. **Invalid Agent Response:** Agent returns malformed data → Log error, skip agent, continue workflow

**NFR24: Error Handling**
- All agent functions wrapped in try-except blocks
- Exceptions logged with structured context (agent type, task ID, query)
- User receives actionable error messages (e.g., "Try simplifying your query")

**NFR26: Logging**
- Structured logging for all agent executions (JSON format)
- Log fields: `agent_type`, `task_id`, `execution_time_ms`, `success`, `error`
- Workflow execution traced via `workflow_id` (UUID per workflow)
- Performance metrics logged for analysis (identify slow agents)

### Observability

**Logging Requirements:**

```python
# Example structured log entry
{
  "timestamp": "2025-11-05T10:30:45.123Z",
  "level": "INFO",
  "workflow_id": "wf-abc123",
  "agent_type": "retrieval",
  "task_id": "task-A",
  "query": "Q3 2023 revenue",
  "execution_time_ms": 850,
  "success": true,
  "results_count": 5,
  "sources": ["Q3_2023_Report.pdf"]
}
```

**Key Metrics to Track:**
- **Workflow Success Rate:** `(successful_workflows / total_workflows) × 100%` (target: 80%+)
- **Agent Execution Time:** P50, P95, P99 per agent type (identify bottlenecks)
- **Fallback Rate:** `(fallbacks / total_workflows) × 100%` (monitor reliability)
- **Query Complexity Distribution:** `SIMPLE` vs `ANALYTICAL` (routing effectiveness)

**Performance Monitoring:**
- Each agent logs execution time upon completion
- Workflow planner logs total workflow duration
- MCP tool logs end-to-end request duration (includes network overhead)
- Anomaly detection: Alert if p95 execution time exceeds 30s threshold

**Failure Mode Analysis:**
- Log all workflow failures with reason (timeout, agent error, decomposition failure)
- Track failure patterns by query type (identify problematic query patterns)
- Manual review of failed workflows during Story 3.8 validation

## Dependencies and Integrations

**Runtime Dependencies (from pyproject.toml):**

```toml
dependencies = [
    # Existing Epic 1-2 dependencies (unchanged)
    "docling==2.55.1",
    "sentence-transformers==5.1.1",
    "qdrant-client==1.15.1",
    "fastmcp==2.12.4",
    "anthropic>=0.18.0,<1.0.0",  # Claude API (optional for Analysis/Synthesis agents)
    "pydantic>=2.0,<3.0",
    "pydantic-settings>=2.0,<3.0",
    "httpx>=0.28.1,<1.0.0",

    # NEW: Epic 3 agentic orchestration (✅ APPROVED)
    "strands-agents>=1.10.0,<2.0.0",  # AWS Strands agentic framework (v1.15.0)
    # Note: No LangGraph required - AWS Strands selected as primary framework
]
```

**✅ DEPENDENCY DECISION COMPLETE:**
- **AWS Strands:** Agentic orchestration framework (Apache 2.0, standalone)
  - **Version:** v1.15.0 (installed via `strands-agents>=1.10.0,<2.0.0`)
  - **Package size:** ~2MB + 15 dependencies
  - **Decision:** Per [epic-3-framework-selection.md](./architecture/epic-3-framework-selection.md) - 84.5% weighted score
  - **Approval:** ✅ Ricardo (2025-11-07) via Story 3.0.8
  - **POC Validation:** Mistral integration validated in `strands_poc.py`
  - **No AWS Infrastructure Required:** Standalone library, uses `settings.mistral_api_key`
  - **Fallback:** Simple Function Calling pattern (71.5% score, 105 LOC) available if Strands issues arise

**Installation:**
```bash
uv sync  # Installs strands-agents v1.15.0 + dependencies
```

**Integration Points:**

| Component | Integration Method | Data Flow | Error Handling |
|-----------|-------------------|-----------|----------------|
| **Epic 1 Retrieval** | Direct function calls to `raglite/retrieval/search.py` | AgentTask → `search_documents()` → QueryResult | Catch exceptions, fallback to empty results |
| **Epic 2 Multi-Index** | Direct function calls to `raglite/retrieval/hybrid_search.py` | AgentTask → `hybrid_search()` → QueryResult | Catch exceptions, fallback to vector-only search |
| **Claude API** | Shared client from `raglite/shared/clients.py` | Agent prompt → Claude Sonnet/Haiku → LLM response | Retry logic (429/500), exponential backoff |
| **FastMCP** | New MCP tool definition in `raglite/main.py` | MCP request → `analyze_financial_question()` → JSON response | MCP error codes (-32000, -32001) |
| **Qdrant** | Reuse existing connection from `raglite/shared/clients.py` | Retrieval Agent → Qdrant search → Vector results | Connection pooling, retry on transient errors |
| **PostgreSQL** | Reuse existing connection from Epic 2 (Story 2.6) | Retrieval Agent → SQL table search → Structured results | Connection pooling, retry on transient errors |

**External Service Dependencies:**
- **Claude API (Anthropic):** Required for Analysis Agent (calculations + reasoning) and Synthesis Agent
  - **Version:** Existing `anthropic>=0.18.0,<1.0.0` from Epic 1
  - **Rate Limits:** 1000 RPM (requests per minute) for Claude Sonnet
  - **Mitigation:** Use Claude Haiku for Analysis Agent (5x faster rate limit)

- **Qdrant Vector Database:** Required for Retrieval Agent (semantic search)
  - **Version:** Existing `qdrant-client==1.15.1` from Epic 1
  - **Deployment:** Docker container (raglite-qdrant) from Epic 1 docker-compose.yml

- **PostgreSQL Database:** Required for Retrieval Agent (structured table queries)
  - **Version:** Existing `psycopg2-binary>=2.9,<3.0` from Epic 2
  - **Deployment:** Docker container (raglite-postgres) from Epic 2 docker-compose.yml

**No New External Services Required** (maintains monolithic architecture)

## Acceptance Criteria (Authoritative)

**Story 3.1: Agentic Framework Integration**
1. ✅ LangGraph (or function calling) integrated into `raglite/orchestration/planner.py`
2. ✅ Framework configuration validated (state schema, workflow graph defined)
3. ✅ Basic 2-step workflow tested (Retrieve → Synthesize)
4. ✅ State management functional (intermediate results passed between agents)
5. ✅ Error handling implemented for workflow failures (NFR24, NFR26)
6. ✅ Integration test validates framework execution (test_orchestration.py)
7. ✅ Documentation includes workflow development guide (README.md updated)

**Story 3.2: Retrieval Agent Implementation**
1. ✅ Retrieval agent defined as tool interface (LangGraph ToolNode or function)
2. ✅ Agent accepts query and returns relevant document chunks with citations
3. ✅ Agent integrates with existing retrieval logic from Epic 1-2 (calls search.py)
4. ✅ Agent tested in isolation (unit test: test_retrieval_agent.py)
5. ✅ Agent tested within simple workflow (integration test: test_simple_workflow.py)

**Story 3.3: Analysis Agent Implementation**
1. ✅ Analysis agent defined with capabilities: YoY growth, variance, trend detection, percentages
2. ✅ Agent accepts financial data and analysis instruction, returns AnalysisResult
3. ✅ Agent uses Claude Haiku for numerical reasoning (structured prompts for accuracy)
4. ✅ Agent tested with sample analytical tasks (YoY calculation, variance analysis)
5. ✅ Agent integrates with Retrieval Agent for data access

**Story 3.4: Synthesis Agent Implementation**
1. ✅ Synthesis agent defined to aggregate results from multiple sub-tasks
2. ✅ Agent produces natural language summary with source citations
3. ✅ Agent maintains consistency with original query intent
4. ✅ Agent tested with multi-source inputs (unit test: test_synthesis_agent.py)
5. ✅ Agent output format optimized for MCP client display (JSON with reasoning_steps)

**Story 3.5: Multi-Step Workflow Orchestration**
1. ✅ Workflow planner decomposes complex queries into sub-tasks (task decomposition logic)
2. ✅ Sub-tasks routed to appropriate specialized agents (Retrieval, Analysis, Synthesis)
3. ✅ Agent outputs passed between agents as inputs to subsequent steps (state management)
4. ✅ Workflow execution completes in <30 seconds for typical analytical queries (NFR5)
5. ✅ Example workflow tested: "Calculate YoY revenue growth and explain variance"
   - Retrieval Agent: Get Q3 2023 & 2024 revenue
   - Analysis Agent: Calculate % change
   - Retrieval Agent: Get context for variance
   - Synthesis Agent: Explain variance
6. ✅ Workflow success rate >80% on complex test queries (AC from Story 3.8)
7. ✅ Failed workflows fall back gracefully to simpler retrieval (NFR17, NFR32)

**Story 3.6: Analytical Query Tool (MCP)**
1. ✅ MCP tool defined: `analyze_financial_question()` triggering agentic workflow
2. ✅ Tool accepts natural language analytical queries (AnalyticalQueryRequest model)
3. ✅ Tool routes simple queries to basic retrieval, complex queries to agentic workflow
4. ✅ Responses include reasoning steps taken (transparency via reasoning_steps field)
5. ✅ Test queries validated: trend analysis, variance explanation, YoY comparisons
6. ✅ User testing via Claude Desktop confirms usability (manual validation)

**Story 3.7: Graceful Degradation for Workflow Failures**
1. ✅ Workflow timeout handling (>30 seconds triggers fallback)
2. ✅ Agent failure detection and logging (structured logs with error context)
3. ✅ Fallback to basic retrieval when workflow fails (NFR17, NFR32)
4. ✅ User receives partial results or error message with suggested alternative query
5. ✅ Error rates logged for workflow improvement (Observability section metrics)
6. ✅ Integration test validates fallback behavior (test_fallback.py)

**Story 3.8: Agentic Workflow Test Suite**
1. ✅ Test set includes 15+ multi-step analytical queries (ground_truth_analytical.json)
2. ✅ Automated test suite executes workflows and validates results (pytest suite)
3. ✅ Success rate measured (target: 80%+ per FR16 interpretation)
4. ✅ Performance measured (workflow execution time logged per query)
5. ✅ Failure analysis documents reasons for unsuccessful workflows (failure_report.md)
6. ✅ Test suite covers edge cases (missing data, ambiguous queries, conflicting information)

## Traceability Mapping

| Acceptance Criteria | Spec Section | Component/API | Test Reference |
|---------------------|--------------|---------------|----------------|
| AC 3.1.1: LangGraph integrated | Detailed Design → Workflow Planner | `raglite/orchestration/planner.py` | `tests/unit/test_planner.py::test_langgraph_initialization` |
| AC 3.1.2: Configuration validated | Detailed Design → Data Models | `WorkflowPlan`, `AgentTask` models | `tests/unit/test_planner.py::test_workflow_state_schema` |
| AC 3.1.3: Basic 2-step workflow | Workflows and Sequencing | Retrieve → Synthesize flow | `tests/integration/test_simple_workflow.py::test_retrieve_synthesize` |
| AC 3.1.4: State management functional | Detailed Design → Data Models | `AgentResult` model, inter-agent data flow | `tests/integration/test_state_management.py` |
| AC 3.1.5: Error handling implemented | NFR → Reliability/Availability | `raglite/orchestration/fallback.py` | `tests/integration/test_error_handling.py` |
| AC 3.2.1: Retrieval agent tool interface | APIs and Interfaces → `retrieve_documents()` | `raglite/orchestration/retrieval_agent.py` | `tests/unit/test_retrieval_agent.py::test_agent_interface` |
| AC 3.2.2: Agent returns chunks + citations | APIs and Interfaces → `retrieve_documents()` | Epic 1 `QueryResult` model | `tests/unit/test_retrieval_agent.py::test_citation_format` |
| AC 3.2.3: Agent integrates Epic 1-2 logic | Dependencies and Integrations → Epic 1 Retrieval | `raglite/retrieval/search.py` calls | `tests/integration/test_retrieval_agent_integration.py` |
| AC 3.3.1: Analysis agent capabilities | APIs and Interfaces → `analyze_financial_data()` | `raglite/orchestration/analysis_agent.py` | `tests/unit/test_analysis_agent.py::test_yoy_growth` |
| AC 3.3.2: Agent returns AnalysisResult | Detailed Design → Data Models | `AnalysisResult` model | `tests/unit/test_analysis_agent.py::test_result_format` |
| AC 3.3.3: Agent uses Claude Haiku | Dependencies and Integrations → Claude API | `anthropic.messages.create(model="claude-haiku")` | `tests/unit/test_analysis_agent.py::test_llm_reasoning` |
| AC 3.4.1: Synthesis agent aggregates results | APIs and Interfaces → `synthesize_answer()` | `raglite/orchestration/synthesis_agent.py` | `tests/unit/test_synthesis_agent.py::test_multi_source_synthesis` |
| AC 3.4.2: Agent produces NL summary + citations | APIs and Interfaces → `synthesize_answer()` output | `AnalyticalQueryResponse.sources` field | `tests/unit/test_synthesis_agent.py::test_citation_generation` |
| AC 3.5.1: Planner decomposes queries | Workflows and Sequencing → Task Decomposition | `WorkflowPlan.tasks` list | `tests/unit/test_planner.py::test_query_decomposition` |
| AC 3.5.2: Sub-tasks routed to agents | Workflows and Sequencing → Agent Orchestration | `AgentTask.agent_type` routing | `tests/integration/test_agent_routing.py` |
| AC 3.5.4: Workflow <30s execution (NFR5) | NFR → Performance | `AnalyticalQueryResponse.execution_time_ms` | `tests/performance/test_workflow_performance.py` |
| AC 3.5.5: Example workflow tested | Workflows and Sequencing → Workflow Example | Full workflow diagram | `tests/integration/test_yoy_variance_workflow.py` |
| AC 3.5.6: Success rate >80% | Acceptance Criteria → Story 3.8.3 | `success_rate` metric | `tests/integration/test_workflow_success_rate.py` |
| AC 3.5.7: Graceful degradation | NFR → Reliability/Availability → NFR17 | `raglite/orchestration/fallback.py` | `tests/integration/test_fallback_behavior.py` |
| AC 3.6.1: MCP tool defined | APIs and Interfaces → `analyze_financial_question()` | `raglite/main.py` MCP tool | `tests/integration/test_mcp_tool.py::test_tool_definition` |
| AC 3.6.2: Tool accepts NL queries | APIs and Interfaces → `AnalyticalQueryRequest` | Pydantic model validation | `tests/integration/test_mcp_tool.py::test_query_acceptance` |
| AC 3.6.3: Query routing logic | Workflows and Sequencing → Step 1: Query Analysis | `QueryComplexity` enum | `tests/unit/test_query_classifier.py` |
| AC 3.6.4: Reasoning steps included | APIs and Interfaces → `AnalyticalQueryResponse.reasoning_steps` | JSON response field | `tests/integration/test_mcp_tool.py::test_reasoning_transparency` |
| AC 3.7.1: Timeout handling | NFR → Reliability/Availability → Failure Scenarios | `raglite/orchestration/fallback.py::handle_timeout()` | `tests/integration/test_timeout_handling.py` |
| AC 3.7.2: Agent failure detection | NFR → Observability → Logging Requirements | Structured logs with `success=false` | `tests/integration/test_agent_failure_detection.py` |
| AC 3.7.3: Fallback to basic retrieval | NFR → Reliability/Availability → NFR17 | `raglite/orchestration/fallback.py::fallback_to_basic_retrieval()` | `tests/integration/test_fallback_to_epic1.py` |
| AC 3.8.1: Test set 15+ queries | Test Strategy Summary → Analytical Test Queries | `tests/fixtures/ground_truth_analytical.json` | `tests/integration/test_analytical_suite.py` |
| AC 3.8.2: Automated test suite | Test Strategy Summary → Pytest Integration | `tests/integration/test_analytical_suite.py` | CI/CD pipeline `.github/workflows/ci.yml` |
| AC 3.8.3: Success rate measured | NFR → Observability → Key Metrics | `(successful / total) × 100%` | `tests/integration/test_workflow_success_rate.py` |
| AC 3.8.4: Performance measured | NFR → Performance → NFR5 | `execution_time_ms` logged per query | `tests/performance/test_workflow_performance.py` |
| AC 3.8.5: Failure analysis documented | Risks, Assumptions, Questions → Failure Mode Analysis | `docs/epic-3-failure-analysis.md` | Manual review post-Story 3.8 |
| AC 3.8.6: Edge cases covered | Test Strategy Summary → Edge Case Testing | Test cases in `test_analytical_suite.py` | `tests/integration/test_edge_cases.py` |

## Risks, Assumptions, Open Questions

### Risks

**Risk 1: LangGraph Learning Curve (MEDIUM)**
- **Probability:** MEDIUM (team unfamiliar with LangGraph)
- **Impact:** MEDIUM (could delay Story 3.1 by 2-3 days)
- **Mitigation:**
  - Architect performs 2-day POC before Epic 3 starts (validate framework)
  - Use LangGraph tutorials and examples (official documentation)
  - Consider native Claude function calling as fallback (simpler, no framework)
- **Assumption:** LangGraph is necessary for stateful workflows (Alternative: native function calling may suffice)

**Risk 2: Workflow Complexity Overhead (HIGH)**
- **Probability:** HIGH (multi-agent orchestration adds latency)
- **Impact:** HIGH (could breach <30s NFR5 target)
- **Mitigation:**
  - Parallel agent execution where no dependencies (e.g., parallel retrievals)
  - Use Claude Haiku for Analysis Agent (faster, cheaper)
  - Implement timeout at 25s (5s buffer for fallback)
  - Monitor p95 execution time, optimize bottlenecks
- **Assumption:** Typical analytical workflows require 3-5 agent calls (Validated in Workflows section: 3.2s typical)

**Risk 3: Workflow Success Rate <80% (MEDIUM)**
- **Probability:** MEDIUM (complex queries may fail decomposition)
- **Impact:** MEDIUM (blocks Epic 3 completion)
- **Mitigation:**
  - Start with simple 2-3 step workflows, gradually increase complexity
  - Focus on 3-5 common analytical patterns (YoY, variance, trend)
  - Refine task decomposition prompts based on failure analysis
  - Fallback to Epic 1 retrieval ensures user always gets results
- **Assumption:** 80%+ success rate is achievable with prompt tuning (Validated by industry benchmarks for agentic RAG)

**Risk 4: LLM API Cost Increase (LOW)**
- **Probability:** LOW (Epic 3 adds 2-3 extra LLM calls per analytical query)
- **Impact:** LOW (cost increase <$0.05 per query)
- **Mitigation:**
  - Use Claude Haiku for Analysis Agent ($0.25/MTok input vs $3/MTok for Sonnet)
  - Cache Claude API responses where applicable (same query decomposition)
  - Monitor API usage, alert if costs exceed budget
- **Assumption:** Analytical queries represent <30% of total traffic (Simple queries still use Epic 1)

**Risk 5: Framework Lock-In (LOW)**
- **Probability:** LOW (can migrate to native function calling if needed)
- **Impact:** MEDIUM (3-5 day refactor effort)
- **Mitigation:**
  - Abstract agent interfaces (decouple agents from orchestration framework)
  - POC validates LangGraph adequacy before committing
  - Native function calling documented as fallback option
- **Assumption:** LangGraph is production-ready and stable (Version >=0.0.20)

### Assumptions

1. **Epic 2 Completion:** Epic 3 assumes Epic 2 achieved 70-80% retrieval accuracy (✅ VALIDATED: Epic 2 complete)
2. **Analytical Query Volume:** Analytical queries represent 20-30% of total queries (Simple queries routed to Epic 1)
3. **LangGraph Stability:** LangGraph library is production-ready despite being pre-1.0 (Version 0.0.20+ stable)
4. **Claude API Availability:** Claude API maintains 99.9% uptime (Historical Anthropic SLA)
5. **Workflow Pattern Simplicity:** Most analytical queries fit 3-5 common patterns (YoY, variance, trend, comparison)
6. **User Tolerance for Latency:** Users accept 10-30s response time for complex analytical queries (vs 5s for simple)
7. **Graceful Degradation Acceptable:** Users satisfied with partial results + error message when workflows fail

### Open Questions

**Question 1: LangGraph vs Native Function Calling? ✅ RESOLVED**
- **Context:** Architecture decision completed during Story 3.0.8
- **Decision:** AWS Strands selected as primary framework
  - **Score:** 84.5% weighted (vs 71.5% for Simple Functions, 35% for Pydantic AI)
  - **Rationale:** 47% code reduction, native MCP integration, production-validated, built-in observability
  - **Model:** Mistral Small for orchestration (no AWS Bedrock required)
  - **Fallback:** Simple Function Calling pattern available if issues arise
- **Documentation:** See [epic-3-framework-selection.md](./architecture/epic-3-framework-selection.md)
- **Approval:** Ricardo (2025-11-07)
- **Status:** ✅ RESOLVED - Ready for Story 3.1 implementation

**Question 2: Analytical Test Query Set Coverage?**
- **Context:** Story 3.8 requires 15+ test queries
- **Question:** What financial query patterns to include? (YoY, variance, trend, correlation, what-if?)
- **Approach:** Review Epic 1-2 ground truth queries, extract analytical patterns
- **Timeline:** Defined during Story 3.8 test set creation
- **Owner:** QA (Test Architect)

**Question 3: Workflow Logging Detail Level?**
- **Context:** Observability section specifies structured logging
- **Question:** Log all intermediate agent results? (Verbose) vs Summary only? (Concise)
- **Trade-off:** Verbose aids debugging, Concise reduces log volume
- **Recommendation:** Verbose during Epic 3 development, Concise in production (configurable via environment variable)
- **Timeline:** Defined during Story 3.1 framework integration
- **Owner:** Dev

**Question 4: Agent Prompt Templates Reusability?**
- **Context:** Analysis and Synthesis agents use LLM prompts
- **Question:** Should prompts be externalized (e.g., prompt templates in files) or inline in code?
- **Recommendation:** Inline for MVP (simpler), externalize in Phase 4 if A/B testing needed
- **Timeline:** Implemented during Stories 3.3-3.4
- **Owner:** Dev

**Question 5: Fallback Partial Results Presentation?**
- **Context:** Story 3.7 requires fallback to partial results
- **Question:** How to present partial results to users? (Explicit "partial" flag vs transparent fallback)
- **Recommendation:** Explicit `workflow_status: "fallback"` field in response (transparency)
- **Timeline:** Implemented during Story 3.7
- **Owner:** Dev

## Test Strategy Summary

**Test Pyramid for Epic 3:**

```
                  ▲
                 / \
                /   \
               /     \
              / E2E   \  (~5 tests)
             /---------\
            /           \
           / Integration \ (~20 tests)
          /---------------\
         /                 \
        /   Unit Tests      \ (~40 tests)
       /---------------------\
      /_________________________\
```

### Unit Tests (~40 tests, <2 min execution)

**Target:** 80%+ code coverage for `raglite/orchestration/` module

**Test Files:**
- `tests/unit/test_planner.py` (~10 tests)
  - Test query complexity classification (SIMPLE vs ANALYTICAL)
  - Test task decomposition logic (query → WorkflowPlan)
  - Test agent routing (AgentTask → correct agent type)
  - Test state schema validation (WorkflowPlan, AgentTask models)

- `tests/unit/test_retrieval_agent.py` (~5 tests)
  - Test agent interface (input validation, output format)
  - Test integration with Epic 1-2 retrieval (mocked)
  - Test citation format consistency

- `tests/unit/test_analysis_agent.py` (~10 tests)
  - Test YoY growth calculation (financial formulas)
  - Test variance analysis (budget vs actual)
  - Test trend detection (increasing, stable, decreasing)
  - Test percentage calculations
  - Test LLM reasoning integration (mocked Claude API)

- `tests/unit/test_synthesis_agent.py` (~5 tests)
  - Test multi-source result aggregation
  - Test natural language summary generation (mocked Claude API)
  - Test citation inclusion and formatting

- `tests/unit/test_fallback.py` (~10 tests)
  - Test timeout detection and handling
  - Test agent failure detection
  - Test fallback to Epic 1 retrieval (mocked)
  - Test partial result formatting

**Mocking Strategy:**
- Mock Claude API calls (unit tests should be fast, no external dependencies)
- Mock Qdrant/PostgreSQL connections (use in-memory fixtures)
- Mock Epic 1-2 retrieval functions (return synthetic QueryResult objects)

### Integration Tests (~20 tests, 5-10 min execution with Qdrant)

**Target:** Validate end-to-end workflow execution with real dependencies

**Test Files:**
- `tests/integration/test_simple_workflow.py` (~3 tests)
  - Test 2-step workflow (Retrieve → Synthesize)
  - Test parallel retrieval (2 Retrieval Agents concurrently)

- `tests/integration/test_yoy_variance_workflow.py` (~5 tests)
  - Test full YoY variance workflow (5-step example from Workflows section)
  - Test execution time <30s
  - Test reasoning steps transparency

- `tests/integration/test_agent_routing.py` (~3 tests)
  - Test SIMPLE query routed to Epic 1
  - Test ANALYTICAL query routed to Epic 3 workflow
  - Test query classification accuracy

- `tests/integration/test_fallback_behavior.py` (~5 tests)
  - Test workflow timeout triggers fallback
  - Test agent failure triggers fallback
  - Test partial results returned correctly
  - Test user receives error message

- `tests/integration/test_mcp_tool.py` (~4 tests)
  - Test `analyze_financial_question()` MCP tool definition
  - Test tool accepts AnalyticalQueryRequest
  - Test tool returns AnalyticalQueryResponse
  - Test reasoning steps included in response

**Test Data:**
- Use Epic 1-2 ground truth documents (real PDFs/Excel files)
- Create `tests/fixtures/ground_truth_analytical.json` with 15+ analytical queries
- Reuse Qdrant/PostgreSQL fixtures from Epic 1-2

### E2E Tests (~5 tests, 10-15 min execution)

**Target:** Validate full system with MCP client simulation

**Test Files:**
- `tests/e2e/test_analytical_query_e2e.py` (~5 tests)
  - Test analytical query via MCP client (Claude Desktop simulation)
  - Test response format compliance with MCP protocol
  - Test source attribution accuracy (NFR7)
  - Test workflow success rate on diverse query types

### Performance Tests (Story 3.8)

**Test File:** `tests/performance/test_workflow_performance.py`

**Metrics to Measure:**
- p50, p95, p99 execution time for analytical workflows
- Per-agent execution time breakdown (identify bottlenecks)
- Success rate on 15+ analytical test queries (target: 80%+)
- Fallback rate (target: <20%)

**Load Testing (Phase 4 Deferred):**
- Concurrent workflow execution (10+ users)
- Rate limiting validation (Claude API 1000 RPM)

### Accuracy Validation (Story 3.8)

**Test Set:** `tests/fixtures/ground_truth_analytical.json`

**Query Types to Cover:**
- YoY growth calculation (e.g., "What was YoY revenue growth in Q3?")
- Variance explanation (e.g., "Why did Q3 expenses increase?")
- Trend analysis (e.g., "What is the hiring trend over last 3 quarters?")
- Percentage calculations (e.g., "What percentage of budget was spent on marketing?")
- Comparative analysis (e.g., "How does Q3 2024 compare to Q3 2023?")

**Validation Method:**
- Manual review of workflow results vs expected answers
- Success criteria: 80%+ queries return correct + relevant answers
- Failure analysis: Document reasons for unsuccessful workflows (report in `docs/epic-3-failure-analysis.md`)

### Test Frameworks and Tools

```toml
[dependency-groups]
test = [
    "pytest==8.4.2",
    "pytest-asyncio==1.2.0",
    "pytest-cov==5.0.0",
    "pytest-mock>=3.12,<4.0",
    "pytest-timeout>=2.0,<3.0",  # Enforce test timeouts
]
```

**CI/CD Integration:**
- Unit tests run on every commit (GitHub Actions)
- Integration tests run on PR merge to main
- E2E tests run nightly (long execution time)
- Performance tests run weekly (monitor regressions)

**Coverage Target:**
- Unit test coverage: 80%+ for `raglite/orchestration/` module
- Integration test coverage: All critical workflows (YoY, variance, trend)
- E2E test coverage: Full MCP protocol compliance

---

**Epic 3 Tech Spec Complete**
**Total Lines:** ~350 lines of new code
**Timeline:** 4 weeks (Stories 3.1-3.8)
**Dependencies:** Epic 1-2 complete (✅), AWS Strands approved (✅)
**Status:** ✅ Ready for implementation - Story 3.1 can begin

**📚 Complete Architecture Documentation:**
- **[Architecture Index](./architecture/epic-3-index.md)** - Start here for Epic 3 architecture
- **[Framework Selection](./architecture/epic-3-framework-selection.md)** - AWS Strands decision (ADR)
- **[Orchestration Design](./architecture/epic-3-orchestration-design.md)** - 3-agent system architecture
- **[Agent Patterns](./architecture/epic-3-agent-patterns.md)** - 5 reusable workflow patterns
- **[Story 3.0.8 Context](./stories/3-0-8-agentic-framework-architecture-spike.context.xml)** - Implementation guidance
- **[POC Code](../strands_poc.py)** - Working validation code
