# Technical Specification: Epic 3 - AI Intelligence & Orchestration

**Epic:** Epic 3 - AI Intelligence & Orchestration
**Phase:** Phase 3 (Weeks 9-12, or 5-8 if Phase 2 skipped)
**Goal:** Multi-step reasoning and complex analytical workflows via agentic orchestration
**Status:** NOT STARTED - **⚠️ CRITICAL ARCHITECTURE GAP**
**Version:** 1.0
**Date:** 2025-10-12
**Author:** Sarah (Product Owner)

---

## ⚠️ CRITICAL ARCHITECTURE GAP - MUST RESOLVE BEFORE IMPLEMENTATION

**BLOCKER:** Framework selection not yet completed. Cannot create stories for Epic 3 until architecture design phase complete.

**Decision Required:** Architect must select and design agentic orchestration approach:
- **Option 1:** LangGraph (stateful agent workflows, Python-native)
- **Option 2:** AWS Bedrock Agents (managed service, requires AWS)
- **Option 3:** Native function calling (Claude 3.7 Sonnet tool use, no framework)

**Estimated Architecture Design Effort:** 5-7 days
- 2 days: Research spike (evaluate frameworks against NFRs)
- 2 days: Proof-of-concept (implement simple 2-step workflow in each approach)
- 1 day: Architecture design document (selected approach + patterns)
- 1-2 days: Story refinement (update Epic 3 stories with framework specifics)

**Dependencies:**
- Phase 1 completion (Week 5) before architecture spike
- Decision gate outcome (GO/NO-GO for Phase 2)
- User approval of framework selection

**This tech spec provides HIGH-LEVEL guidance only. Detailed component specs CANNOT be created until framework selected.**

---

## 1. Executive Summary

Epic 3 enables multi-step analytical reasoning via agentic orchestration. The system autonomously plans, executes, and synthesizes complex analytical workflows (e.g., "Calculate YoY revenue growth and explain variance").

**Target:** ~250-300 additional lines of Python code
**Timeline:** 4 weeks (contingent on architecture design completion)
**Current Blocker:** Framework selection

**Capabilities Enabled:**
- Multi-step workflow planning and execution
- Specialized agents: Retrieval, Analysis, Synthesis
- Complex analytical queries (trend analysis, variance explanation, YoY comparisons)
- Graceful degradation to basic retrieval on workflow failures

---

## 2. Architecture Overview (High-Level)

### 2.1 Conceptual Architecture

```
┌──────────────────────────────────────────────────────────┐
│  MCP Clients (Claude Code, Claude Desktop)             │
└────────────────────┬─────────────────────────────────────┘
                     │ Model Context Protocol
┌────────────────────▼─────────────────────────────────────┐
│  RAGLite Monolithic Server (main.py)                    │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │  MCP Tools Layer                                    ││
│  │  • query_financial_documents() (Epic 1 ✅)         ││
│  │  • analyze_financial_question() (Epic 3 - NEW)     ││
│  └─────────────────────────────────────────────────────┘│
│                                                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Agentic Orchestration Layer (NEW ~250 lines)      ││
│  │                                                     ││
│  │  ┌──────────────────────────────────────────────┐  ││
│  │  │  Workflow Planner                            │  ││
│  │  │  • Decomposes complex queries into sub-tasks│  ││
│  │  │  • Routes tasks to specialized agents        │  ││
│  │  │  • Manages state and execution flow          │  ││
│  │  └──────────────────────────────────────────────┘  ││
│  │                                                     ││
│  │  ┌──────────────────────────────────────────────┐  ││
│  │  │  Specialized Agents                          │  ││
│  │  │  • Retrieval Agent (search documents)        │  ││
│  │  │  • Analysis Agent (calculate, reason)        │  ││
│  │  │  • Synthesis Agent (aggregate, summarize)    │  ││
│  │  └──────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────┘│
│                                                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Business Logic (Epic 1-2 ✅)                      ││
│  │  ├─ ingestion/ (pipeline, entity extraction)       ││
│  │  ├─ retrieval/ (search, hybrid, attribution)       ││
│  │  └─ shared/ (config, logging, models, clients)     ││
│  └─────────────────────────────────────────────────────┘│
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│  Data Layer                                              │
│  ├─ Qdrant (Vector DB) ✅                               │
│  └─ Neo4j (Knowledge Graph) - CONDITIONAL Epic 2        │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Workflow Execution Flow (Framework-Agnostic)

**Example Query:** "Calculate YoY revenue growth and explain variance"

```
1. Query Analysis
   └─> Workflow Planner detects complex analytical query

2. Task Decomposition
   └─> Sub-tasks:
       a. Retrieve Q3 2023 revenue
       b. Retrieve Q3 2024 revenue
       c. Calculate % change
       d. Retrieve context for variance explanation
       e. Synthesize explanation

3. Agent Orchestration
   └─> Retrieval Agent: Fetch Q3 2023 revenue → $10M
   └─> Retrieval Agent: Fetch Q3 2024 revenue → $12M
   └─> Analysis Agent: Calculate (12M - 10M) / 10M = +20%
   └─> Retrieval Agent: Fetch "marketing spend", "new product launches"
   └─> Synthesis Agent: "Revenue grew 20% YoY due to 30% increase
                         in marketing spend and launch of Product X
                         in Q2 2024."

4. Response Formatting
   └─> MCP tool returns synthesized answer with citations
```

---

## 3. Component Specifications (HIGH-LEVEL ONLY)

**⚠️ NOTE:** Detailed specs CANNOT be written until framework selected. The following provides conceptual guidance only.

### 3.1 Workflow Planner (~80 lines - framework-dependent)

**Purpose:** Decompose complex queries into sub-tasks and orchestrate agent execution.

**Key Responsibilities:**
- Query complexity detection (simple vs multi-step)
- Task decomposition (break query into atomic sub-tasks)
- Agent routing (match sub-task to specialized agent)
- State management (track intermediate results)
- Error handling (detect failures, trigger fallback)

**Framework-Specific Implementations:**

**Option 1: LangGraph**
```python
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

# Define state schema
class WorkflowState(TypedDict):
    query: str
    sub_tasks: List[str]
    results: Dict[str, Any]
    final_answer: str

# Build graph (nodes = agents, edges = execution flow)
workflow = StateGraph(WorkflowState)
workflow.add_node("planner", plan_tasks)
workflow.add_node("retrieval", retrieval_agent)
workflow.add_node("analysis", analysis_agent)
workflow.add_node("synthesis", synthesis_agent)
workflow.set_entry_point("planner")
```

**Option 2: AWS Bedrock Agents**
```python
import boto3
bedrock_agent = boto3.client('bedrock-agent-runtime')

# Define agents in AWS Console
# Invoke via API
response = bedrock_agent.invoke_agent(
    agentId='agent-123',
    sessionId='session-456',
    inputText=query
)
```

**Option 3: Native Function Calling**
```python
from anthropic import Anthropic

tools = [
    {
        "name": "retrieve_documents",
        "description": "Search financial documents",
        "input_schema": {...}
    },
    {
        "name": "analyze_data",
        "description": "Perform calculations",
        "input_schema": {...}
    }
]

# Claude orchestrates via tool calls
response = anthropic.messages.create(
    model="claude-3-7-sonnet-20250219",
    tools=tools,
    messages=[{"role": "user", "content": query}]
)
```

**NFRs:**
- NFR5: <30s workflow execution for typical analytical queries
- NFR17: Graceful degradation on workflow failures
- NFR24: Comprehensive error logging

---

### 3.2 Specialized Agents (~150 lines total)

#### Retrieval Agent (~50 lines)
**Purpose:** Search financial knowledge base (wrapper around Epic 1 retrieval).

**Tool Interface:**
```python
async def retrieval_agent(query: str, top_k: int = 5) -> List[QueryResult]:
    """Wrapper around Epic 1 search.py for agent use.

    Args:
        query: Specific retrieval query (decomposed from complex query)
        top_k: Number of results

    Returns:
        List of QueryResult objects
    """
```

#### Analysis Agent (~50 lines)
**Purpose:** Perform calculations and reasoning over retrieved data.

**Capabilities:**
- YoY/QoQ growth calculations
- Variance analysis (budget vs actual)
- Percentage changes
- Trend detection (increasing, decreasing, stable)
- Correlation identification (basic statistical reasoning)

**Tool Interface:**
```python
async def analysis_agent(data: Dict[str, float], analysis_type: str) -> AnalysisResult:
    """Perform analytical calculations.

    Args:
        data: Financial data points (e.g., {"Q3_2023": 10.0, "Q3_2024": 12.0})
        analysis_type: Type of analysis ("yoy_growth", "variance", "trend")

    Returns:
        AnalysisResult with calculation and reasoning
    """
```

#### Synthesis Agent (~50 lines)
**Purpose:** Aggregate results from multiple agents into coherent answer.

**Tool Interface:**
```python
async def synthesis_agent(sub_results: List[AgentResult], original_query: str) -> str:
    """Synthesize final answer from sub-task results.

    Args:
        sub_results: Results from retrieval/analysis agents
        original_query: User's original query

    Returns:
        Natural language answer with citations
    """
```

---

### 3.3 Files to Create (Framework-Dependent)

**Estimated Repository Structure:**

```
raglite/
├── orchestration/             # NEW module (~250 lines)
│   ├── planner.py            (~80 lines - workflow planning)
│   ├── retrieval_agent.py    (~50 lines - search wrapper)
│   ├── analysis_agent.py     (~50 lines - calculations)
│   ├── synthesis_agent.py    (~50 lines - aggregation)
│   └── fallback.py           (~20 lines - graceful degradation)
├── main.py                    # Update with analyze_financial_question() tool
└── tests/
    └── test_orchestration.py  (~100 lines - workflow tests)
```

---

## 4. API Contracts

### 4.1 New MCP Tool: analyze_financial_question

**Input:**
```json
{
  "query": "Calculate YoY revenue growth and explain variance",
  "enable_orchestration": true
}
```

**Output:**
```json
{
  "answer": "Revenue grew 20% YoY (Q3 2023: $10M → Q3 2024: $12M). The variance is primarily due to 30% increase in marketing spend and launch of Product X in Q2 2024.",
  "reasoning_steps": [
    "1. Retrieved Q3 2023 revenue: $10M",
    "2. Retrieved Q3 2024 revenue: $12M",
    "3. Calculated YoY growth: +20%",
    "4. Retrieved marketing spend data: +30%",
    "5. Synthesized variance explanation"
  ],
  "sources": [
    "Q3_2023_Report.pdf (page 12)",
    "Q3_2024_Report.pdf (page 12)",
    "Marketing_Budget_2024.xlsx (sheet 'Q2-Q3')"
  ],
  "workflow_status": "success",
  "execution_time_ms": 2850
}
```

**Fallback Response (on workflow failure):**
```json
{
  "answer": "I found revenue data but couldn't complete the full analysis. Q3 2024 revenue was $12M (source: Q3_2024_Report.pdf, p.12).",
  "reasoning_steps": ["1. Workflow timeout after 30s", "2. Fallback to basic retrieval"],
  "workflow_status": "fallback",
  "execution_time_ms": 30100
}
```

---

## 5. NFR Validation Criteria

### Performance (NFR5)
**Target:** <30s workflow execution (p95)

**Validation Method:**
- Performance tests on 15+ analytical queries
- Measure end-to-end workflow latency
- Identify bottlenecks (agent LLM calls, retrieval)

### Workflow Success Rate (FR16 interpretation)
**Target:** 80%+ success rate on complex analytical queries

**Validation Method:**
- Test set: 15+ multi-step queries (Story 3.8)
- Measure: (Successful workflows / Total workflows) × 100%
- Track failure modes: timeouts, agent errors, incorrect decomposition

### Graceful Degradation (NFR17, NFR32)
**Target:** 100% of workflow failures result in fallback response (not hard error)

**Validation Method:**
- Integration tests simulate agent failures
- Validate fallback to basic retrieval
- Ensure user receives useful partial results

---

## 6. Implementation Timeline

### Pre-Phase 3: Architecture Design (5-7 days)

**MANDATORY before Story 3.1 can begin.**

**Activities:**
- Research spike: Evaluate LangGraph, Bedrock, function calling
- Proof-of-concept: Simple 2-step workflow in each approach
- Architecture design document: Selected approach + patterns
- Story refinement: Update Epic 3 stories with framework specifics

**Deliverables:**
- Architecture design document (Epic 3 approach)
- Updated Epic 3 stories with framework-specific acceptance criteria

---

### Week 9 (or 5): Framework Integration + Retrieval Agent
**Stories:**
- Story 3.1: Agentic Framework Integration
- Story 3.2: Retrieval Agent Implementation

**Deliverables:**
- Framework deployed and configured
- Simple 2-step workflow functional
- Retrieval agent wrapper complete

---

### Week 10 (or 6): Analysis + Synthesis Agents
**Stories:**
- Story 3.3: Analysis Agent Implementation
- Story 3.4: Synthesis Agent Implementation

**Deliverables:**
- Analysis agent (YoY, variance, trend calculations)
- Synthesis agent (aggregation, summarization)
- Unit tests for both agents

---

### Week 11 (or 7): Multi-Step Workflow Orchestration
**Stories:**
- Story 3.5: Multi-Step Workflow Orchestration
- Story 3.6: Analytical Query Tool (MCP)

**Deliverables:**
- Workflow planner (task decomposition)
- MCP tool: analyze_financial_question()
- End-to-end integration tests

---

### Week 12 (or 8): Testing + Graceful Degradation
**Stories:**
- Story 3.7: Graceful Degradation for Workflow Failures
- Story 3.8: Agentic Workflow Test Suite

**Deliverables:**
- Fallback logic implemented
- Test suite (15+ analytical queries)
- Phase 3 validation report

**Success Criteria:**
- 80%+ workflow success rate
- <30s execution time (p95)
- 100% graceful degradation on failures

---

## 7. Dependencies & Blockers

### CRITICAL BLOCKER: Architecture Design Not Complete

**Impact:** CANNOT start Epic 3 stories until framework selected.

**Resolution Required:**
1. Architect performs 5-7 day design sprint
2. User approves framework selection
3. Tech spec updated with framework-specific details
4. Stories updated with framework-specific acceptance criteria

**Estimated Delay:** 1-2 weeks before Epic 3 can begin

---

### External Dependencies

**Framework-Specific:**
- **LangGraph:** pip install langgraph (add to pyproject.toml)
- **AWS Bedrock Agents:** AWS account, IAM roles, Bedrock service access
- **Function Calling:** No new dependencies (Claude 3.7 Sonnet built-in)

**Existing Dependencies (Epic 1):**
- Claude API ✅
- Qdrant ✅
- Docling ✅

---

## 8. Success Criteria

### Phase 3 Completion Criteria (End of Week 12 or 8)

**Must Meet (GO Criteria):**
1. ✅ 80%+ workflow success rate on analytical queries (15+ test queries)
2. ✅ <30s workflow execution time (p95)
3. ✅ All workflow failures result in fallback (no hard errors)
4. ✅ MCP tool (analyze_financial_question) functional via Claude Desktop
5. ✅ Reasoning steps transparent (users understand workflow)

**Decision Gate:**
- **IF** all criteria met → **PROCEED to Epic 4** (Forecasting & Insights)
- **IF** success rate <70% → **REASSESS** (simplify workflows or improve agents)

---

## 9. Risks & Mitigation

### Risk 1: Framework Selection Delay (HIGH)

**Probability:** HIGH (architecture design not started yet)
**Impact:** VERY HIGH (blocks entire Epic 3)

**Mitigation:**
1. **IMMEDIATE ACTION:** Schedule architecture design sprint (5-7 days)
2. Architect performs research + POC in parallel with Phase 1-2
3. User reviews framework options weekly (async decision-making)
4. Timebox design: If no decision by Phase 2 end, default to function calling (simplest)

**Status:** UNRESOLVED (must address before Epic 3)

---

### Risk 2: Workflow Complexity (MEDIUM)

**Probability:** MEDIUM (multi-step orchestration non-trivial)
**Impact:** MEDIUM (could reduce success rate below 80%)

**Mitigation:**
1. Start with simple 2-step workflows (Week 9)
2. Iterative complexity: Add 3-step, 4-step workflows gradually
3. Focus on 3-5 common analytical patterns (YoY, variance, trend)
4. If success rate <70% by Week 11, simplify workflows

---

### Risk 3: Performance Overhead (MEDIUM)

**Probability:** MEDIUM (multiple LLM calls = latency)
**Impact:** MEDIUM (could breach <30s target)

**Mitigation:**
1. Parallel agent execution where possible (retrieval + retrieval concurrent)
2. Cache intermediate results (avoid redundant LLM calls)
3. Use Claude Haiku for simple sub-tasks (faster, cheaper)
4. Fallback timeout: 25s (leave 5s buffer for user response)

---

### Risk 4: Framework Lock-In (LOW)

**Probability:** LOW (can migrate if needed)
**Impact:** MEDIUM (refactor effort if framework inadequate)

**Mitigation:**
1. Abstract agent interfaces (decouple agents from orchestration)
2. POC validates framework before committing
3. Function calling fallback: Always viable (no vendor lock-in)

---

## 10. References

### Architecture Documents
- `docs/architecture/8-phased-implementation-strategy-v11-simplified.md` - Phase 3 timeline
- **MISSING:** Epic 3 architecture design document (MUST CREATE)

### PRD Documents
- `docs/prd/epic-3-ai-intelligence-orchestration.md` - Epic 3 stories

### Research
- LangGraph Documentation: https://github.com/langchain-ai/langgraph
- AWS Bedrock Agents: https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
- Claude Function Calling: https://docs.anthropic.com/claude/docs/tool-use

---

## 11. Next Steps (IMMEDIATE ACTION REQUIRED)

**Priority 1: Resolve Architecture Blocker**
1. ✅ User acknowledges architecture gap (this tech spec)
2. ⏰ Schedule architecture design sprint (5-7 days)
3. 📋 Architect performs framework evaluation
4. ✅ User approves framework selection
5. 📝 Update this tech spec with framework-specific details

**Priority 2: Refine Stories**
Once framework selected:
1. Update Story 3.1-3.8 acceptance criteria (framework-specific)
2. Create detailed component specs (planner, agents)
3. Update repository structure (files to create)
4. Finalize NFR validation approach (framework-dependent)

**Status:** Epic 3 BLOCKED until Priority 1 complete.

---

**Document Version:** 1.0
**Created:** 2025-10-12
**Author:** Sarah (Product Owner)
**Next Update:** After architecture design sprint complete (framework selected)
