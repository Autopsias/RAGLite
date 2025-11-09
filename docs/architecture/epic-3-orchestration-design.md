# Epic 3 Orchestration Architecture Design

**Document Type:** Architecture Design Document
**Status:** 🚧 DRAFT (In Progress)
**Date:** 2025-11-07
**Architect:** Winston
**Story:** Story 3.0.8 - AC2 (Orchestration Architecture Design)
**Framework:** AWS Strands (v1.15.0)

---

## Executive Summary

This document defines the orchestration architecture for RAGLite's Epic 3 multi-agent analytical query system. The design uses AWS Strands' event-driven agent framework to coordinate three specialized agents: Retrieval, Analysis, and Synthesis.

**Key Design Decisions:**
- Event-driven orchestration using AWS Strands
- Mistral Small for orchestration decisions (tunable to Claude)
- Three-agent pipeline: Retrieval → Analysis → Synthesis
- Graceful degradation to Epic 2 simple search on failures
- OpenTelemetry observability built-in

**Target Performance:**
- Total query latency: <10s p50, <20s p95 (including orchestration + agent execution)
- Orchestration overhead: 3-5s (validated in POC)

---

## Architecture Context

### Problem Statement

Epic 2 provides accurate document retrieval (90% accuracy) but lacks analytical reasoning capabilities. Users need:
- Multi-step reasoning over retrieved documents
- Cross-document analysis and comparison
- Intelligent synthesis with source attribution

### Solution Approach

Implement agentic orchestration where:
1. **Retrieval Agent** - Queries RAGLite's multi-index search (Qdrant + PostgreSQL)
2. **Analysis Agent** - Interprets and analyzes retrieved documents
3. **Synthesis Agent** - Generates final answer with proper citations

The orchestrator (powered by Mistral/Claude) decides agent execution order and handles coordination.

---

## Agent Specifications

### Agent 1: Retrieval Agent

**Purpose:** Query RAGLite's multi-index search system and return relevant document chunks

**Responsibilities:**
- Accept natural language query from orchestrator
- Route query to appropriate search backend (vector, SQL, or hybrid)
- Execute multi-index search via `raglite.retrieval.multi_index_search`
- Return ranked chunks with metadata (scores, page references, document IDs)

**Input:**
```python
class RetrievalInput(BaseModel):
    query: str = Field(description="Natural language query")
    top_k: int = Field(default=5, description="Number of chunks to retrieve")
    search_mode: str = Field(default="auto", description="auto|vector|sql|hybrid")
```

**Output:**
```python
class RetrievalOutput(BaseModel):
    chunks: list[DocumentChunk] = Field(description="Retrieved document chunks")
    search_metadata: SearchMetadata = Field(description="Search execution metadata")

class DocumentChunk(BaseModel):
    content: str
    score: float
    page: int
    doc_id: str
    section_type: str  # "Text" | "Table" | "List"

class SearchMetadata(BaseModel):
    query_classification: str  # "simple" | "table" | "analytical"
    search_backend_used: str  # "vector" | "sql" | "hybrid"
    total_chunks_searched: int
    retrieval_latency_ms: int
```

**Integration Points:**
- Wraps existing `multi_index_search()` from `raglite.retrieval.multi_index_search`
- Uses existing query classification logic
- Leverages Epic 2 Phase 2A multi-index architecture

**Error Handling:**
- If search fails → Return empty result with error metadata
- If timeout (>10s) → Return partial results
- If Qdrant unreachable → Fallback to PostgreSQL SQL search only

**Performance Target:**
- Latency: <3s p50, <8s p95
- Accuracy: 90%+ (inherited from Epic 2)

---

### Agent 2: Analysis Agent

**Purpose:** Interpret retrieved documents and extract key information relevant to the query

**Responsibilities:**
- Accept retrieved chunks and original query
- Analyze chunks for relevant facts, figures, and relationships
- Identify cross-document patterns and contradictions
- Extract structured information (dates, numbers, entities)
- Provide analytical insights beyond simple retrieval

**Input:**
```python
class AnalysisInput(BaseModel):
    query: str = Field(description="Original user query")
    chunks: list[DocumentChunk] = Field(description="Retrieved chunks from Retrieval Agent")
    analysis_depth: str = Field(default="standard", description="standard|deep")
```

**Output:**
```python
class AnalysisOutput(BaseModel):
    key_facts: list[Fact] = Field(description="Extracted facts with source attribution")
    insights: list[Insight] = Field(description="Analytical insights")
    contradictions: list[str] = Field(description="Identified contradictions if any")
    confidence: float = Field(description="Confidence in analysis (0-1)")

class Fact(BaseModel):
    statement: str
    source_chunk_id: str
    page_reference: int
    confidence: float

class Insight(BaseModel):
    insight: str
    supporting_chunks: list[str]
    reasoning: str
```

**LLM Configuration:**
- Model: Claude 3.7 Sonnet (primary) or Mistral Large (cost optimization)
- Temperature: 0.1 (factual analysis)
- Max tokens: 2000
- System prompt: "You are a financial document analyst..."

**Error Handling:**
- If LLM API fails → Return raw chunks without analysis
- If analysis incomplete → Mark as partial with confidence <0.5
- If contradictions found → Escalate to synthesis with warning

**Performance Target:**
- Latency: <5s p50, <12s p95
- Accuracy: Qualitative (will establish baseline in Story 3.3)

---

### Agent 3: Synthesis Agent

**Purpose:** Generate final answer with proper citations and source attribution

**Responsibilities:**
- Accept analysis results and original query
- Synthesize coherent answer addressing the user's question
- Generate proper citations using RAGLite's citation format
- Handle contradictions and confidence scores
- Format response for MCP client display

**Input:**
```python
class SynthesisInput(BaseModel):
    query: str = Field(description="Original user query")
    analysis: AnalysisOutput = Field(description="Analysis from Analysis Agent")
    citation_style: str = Field(default="inline", description="inline|footnote")
```

**Output:**
```python
class SynthesisOutput(BaseModel):
    answer: str = Field(description="Final synthesized answer with citations")
    confidence: float = Field(description="Overall confidence (0-1)")
    sources_used: list[str] = Field(description="List of source documents")
    limitations: list[str] = Field(description="Limitations or caveats")
```

**LLM Configuration:**
- Model: Claude 3.7 Sonnet (high-quality synthesis)
- Temperature: 0.2 (balanced creativity and accuracy)
- Max tokens: 3000
- System prompt: "You are a financial analysis assistant..."

**Integration Points:**
- Uses `generate_citations()` from `raglite.retrieval.attribution`
- Formats response according to MCP response spec (from `docs/front-end-spec/`)

**Error Handling:**
- If synthesis fails → Return raw analysis facts with basic formatting
- If citations fail → Return answer without attribution (log warning)
- If confidence <0.3 → Prepend disclaimer to answer

**Performance Target:**
- Latency: <4s p50, <10s p95
- User satisfaction: >80% (qualitative, post-Epic 3)

---

## Orchestration Architecture

### Event-Driven Coordination with AWS Strands

**Orchestrator Agent Specification:**

```python
from strands import Agent
from strands.models.mistral import MistralModel
from raglite.shared.config import settings

# Create orchestrator model (Mistral or Claude)
orchestrator_model = MistralModel(
    api_key=settings.mistral_api_key,
    model_id="mistral-small-latest"  # Tunable to Claude
)

# Define orchestrator agent
orchestrator = Agent(
    model=orchestrator_model,
    tools=[retrieval_agent, analysis_agent, synthesis_agent],
    system_prompt="""You are an intelligent orchestrator for financial document analysis.

Your role:
1. Understand the user's query
2. Call retrieval_agent to search for relevant documents
3. Call analysis_agent to interpret the retrieved documents
4. Call synthesis_agent to generate the final answer with citations

Always execute all three agents in sequence. Handle any errors gracefully.

Return the final synthesis result to the user."""
)
```

**Orchestration Flow:**

```
User Query (via MCP)
        ↓
┌───────────────────────────┐
│  MCP Tool Entry Point     │
│  analytical_query()       │
└───────────────────────────┘
        ↓
┌───────────────────────────┐
│  Orchestrator Agent       │
│  (Mistral/Claude decides) │
└───────────────────────────┘
        ↓
   ┌────┴────┐
   ↓         ↓
   Decision: Call retrieval_agent
        ↓
┌───────────────────────────┐
│  Retrieval Agent          │
│  @tool async def          │
│  - Multi-index search     │
│  - Returns chunks         │
└───────────────────────────┘
        ↓
   ┌────┴────┐
   ↓         ↓
   Decision: Call analysis_agent with chunks
        ↓
┌───────────────────────────┐
│  Analysis Agent           │
│  @tool async def          │
│  - Interpret chunks       │
│  - Extract facts          │
└───────────────────────────┘
        ↓
   ┌────┴────┐
   ↓         ↓
   Decision: Call synthesis_agent with analysis
        ↓
┌───────────────────────────┐
│  Synthesis Agent          │
│  @tool async def          │
│  - Generate answer        │
│  - Add citations          │
└───────────────────────────┘
        ↓
┌───────────────────────────┐
│  Orchestrator Returns     │
│  Final Answer to MCP      │
└───────────────────────────┘
        ↓
   MCP Client (Claude Desktop)
```

### State Management

**Approach:** Implicit state via tool arguments (Strands pattern)

Each agent receives necessary context as function arguments:
- Retrieval Agent: query only
- Analysis Agent: query + chunks
- Synthesis Agent: query + analysis

**No shared state or memory needed** - orchestrator passes context between agents via tool calls.

**Advantages:**
- Stateless agents (easier testing)
- Clear data flow (explicit arguments)
- No state synchronization issues

**Disadvantages:**
- Orchestrator must manage context passing
- Cannot parallelize agents (sequential dependency)

---

## Communication Patterns

### Pattern 1: Sequential Agent Chain (Primary)

```
Query → Retrieval → Analysis → Synthesis → Answer
```

**When to use:** Standard analytical queries (80% of use cases)

**Latency:** Sum of agent latencies (~12s total)

---

### Pattern 2: Parallel Retrieval with Sequential Analysis (Future)

```
Query → [Vector Search || SQL Search] → Merge → Analysis → Synthesis → Answer
```

**When to use:** Complex queries requiring multiple search backends

**Latency:** Parallelization saves ~2-3s

**Implementation:** Epic 3.5 or Epic 4

---

### Pattern 3: Conditional Routing (Future)

```
Query → Classifier → Simple Query? → Direct Answer (Epic 2)
                  → Complex Query? → Orchestrator (Epic 3)
```

**When to use:** Optimize for simple queries that don't need orchestration

**Latency:** Saves 3-5s for simple queries

**Implementation:** Story 3.6

---

## Error Handling Strategy

### Error Classification

**Level 1: Agent Execution Errors**
- Retrieval Agent fails (Qdrant timeout, connection error)
- Analysis Agent fails (LLM API error)
- Synthesis Agent fails (citation generation error)

**Level 2: Orchestrator Errors**
- Orchestrator LLM fails to decide next agent
- Orchestrator exceeds token limit
- Orchestrator times out (>30s)

**Level 3: System Errors**
- MCP server crash
- Database connection failures
- Memory exhaustion

### Graceful Degradation Strategy

**Tier 1: Full Orchestration (Best)**
- All 3 agents execute successfully
- Return synthesized answer with citations
- Confidence: HIGH

**Tier 2: Partial Orchestration (Good)**
- Retrieval + Analysis succeed, Synthesis fails
- Return analysis facts with basic formatting
- Confidence: MEDIUM

**Tier 3: Retrieval Only (Acceptable)**
- Only Retrieval succeeds
- Return raw chunks (Epic 2 behavior)
- Confidence: LOW

**Tier 4: Complete Failure (Fallback)**
- All agents fail
- Return error message with fallback to Epic 2 simple search
- Confidence: NONE

### Error Handling Code Pattern

```python
@mcp.tool()
async def analytical_query_financial_documents(query: str) -> QueryResponse:
    """Analytical query with graceful degradation."""

    try:
        # Tier 1: Full orchestration
        result = await orchestrator.invoke_async(query)
        return QueryResponse(
            answer=str(result),
            confidence="high",
            tier="full_orchestration"
        )

    except RetrievalError as e:
        # Tier 4: Fallback to Epic 2
        logger.warning("Retrieval failed, falling back to Epic 2", extra={"error": str(e)})
        return await simple_query_financial_documents(query)

    except AnalysisError as e:
        # Tier 3: Return raw chunks
        logger.warning("Analysis failed, returning raw chunks", extra={"error": str(e)})
        chunks = await multi_index_search(query)
        return format_chunks_as_response(chunks, confidence="low")

    except SynthesisError as e:
        # Tier 2: Return analysis without synthesis
        logger.warning("Synthesis failed, returning analysis", extra={"error": str(e)})
        analysis = e.partial_analysis
        return format_analysis_as_response(analysis, confidence="medium")

    except Exception as e:
        # Tier 4: Unexpected failure
        logger.error("Orchestration failed", extra={"error": str(e)})
        return await simple_query_financial_documents(query)
```

---

## Observability & Monitoring

### Built-In Observability (OpenTelemetry)

AWS Strands includes automatic OpenTelemetry tracing:

**Automatic Metrics:**
- Agent invocation count
- Agent execution latency
- Tool call duration
- Token usage per agent
- Error rates by agent type

**Trace Structure:**
```
Span: analytical_query (root)
  ├─ Span: orchestrator.invoke_async
  │   ├─ Span: retrieval_agent.execute
  │   │   └─ Span: multi_index_search
  │   ├─ Span: analysis_agent.execute
  │   │   └─ Span: claude_api_call
  │   └─ Span: synthesis_agent.execute
  │       ├─ Span: claude_api_call
  │       └─ Span: generate_citations
```

### Custom Logging Strategy

**Structured Logging (raglite.shared.logging):**

```python
# Agent entry
logger.info("Agent invoked", extra={
    "agent": "retrieval",
    "query": query,
    "top_k": top_k
})

# Agent success
logger.info("Agent completed", extra={
    "agent": "retrieval",
    "chunks_found": len(chunks),
    "latency_ms": latency
})

# Agent failure
logger.error("Agent failed", extra={
    "agent": "retrieval",
    "error": str(e),
    "tier": "degraded"
})
```

### Performance Monitoring

**Key Metrics to Track:**

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Total query latency (p50) | <10s | >15s |
| Total query latency (p95) | <20s | >30s |
| Orchestration overhead | 3-5s | >8s |
| Retrieval latency | <3s | >8s |
| Analysis latency | <5s | >12s |
| Synthesis latency | <4s | >10s |
| Agent error rate | <5% | >10% |
| Graceful degradation rate | <10% | >25% |

---

## Integration with RAGLite Components

### MCP Server Entry Point

**New MCP Tool:**

```python
@mcp.tool()
async def analytical_query_financial_documents(
    query: str,
    orchestration: bool = True
) -> QueryResponse:
    """Query financial documents with multi-agent analytical reasoning.

    This is the Epic 3 analytical query tool that uses orchestrated agents
    for complex queries requiring multi-step reasoning.

    Args:
        query: Natural language query
        orchestration: Enable orchestration (True) or use Epic 2 simple search (False)

    Returns:
        QueryResponse with synthesized answer, citations, and confidence

    Example:
        >>> response = await analytical_query_financial_documents(
        ...     "Compare Q3 revenue to Q4 and explain the variance"
        ... )
        >>> print(response.answer)
    """
    if not orchestration:
        # Direct Epic 2 simple search (bypass orchestration)
        return await query_financial_documents(query)

    # Epic 3 orchestration
    return await orchestrate_analytical_query(query)
```

### Existing Component Reuse

**FROM Epic 2 (reused as-is):**
- `raglite.retrieval.multi_index_search` - Retrieval Agent backend
- `raglite.retrieval.attribution.generate_citations` - Synthesis Agent citations
- `raglite.shared.models.QueryResponse` - Response format
- `raglite.shared.logging` - Structured logging

**NEW for Epic 3:**
- `raglite.orchestration.orchestrator` - Strands orchestrator setup
- `raglite.orchestration.agents.retrieval` - Retrieval Agent implementation
- `raglite.orchestration.agents.analysis` - Analysis Agent implementation
- `raglite.orchestration.agents.synthesis` - Synthesis Agent implementation

**Repository Structure:**
```
raglite/
├── orchestration/              # NEW - Epic 3
│   ├── __init__.py
│   ├── orchestrator.py         # Main orchestrator setup
│   └── agents/
│       ├── __init__.py
│       ├── retrieval.py        # Retrieval Agent
│       ├── analysis.py         # Analysis Agent
│       └── synthesis.py        # Synthesis Agent
```

**LOC Estimate:**
- orchestrator.py: ~50 lines
- retrieval.py: ~80 lines (wraps multi_index_search)
- analysis.py: ~120 lines (LLM prompts + parsing)
- synthesis.py: ~100 lines (synthesis + citations)
- **Total: ~350 lines** (within 600-800 LOC budget)

---

## Architecture Diagrams

### C4 Context Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         RAGLite                              │
│                   (Financial RAG System)                     │
│                                                              │
│  ┌─────────────────────┐       ┌──────────────────────┐   │
│  │  Epic 2: Simple     │       │  Epic 3: Analytical  │   │
│  │  Query Tool         │       │  Query Tool          │   │
│  │  (query_financial_  │       │  (analytical_query_  │   │
│  │   documents)        │       │   financial_docs)    │   │
│  └─────────────────────┘       └──────────────────────┘   │
│            │                              │                 │
│            ↓                              ↓                 │
│  ┌─────────────────────┐       ┌──────────────────────┐   │
│  │  Multi-Index Search │       │  Agent Orchestrator  │   │
│  │  (Qdrant + Postgres)│       │  (AWS Strands)       │   │
│  └─────────────────────┘       └──────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                    ↑
                    │ MCP Protocol
                    ↓
         ┌──────────────────────┐
         │   Claude Desktop     │
         │   (MCP Client)       │
         └──────────────────────┘
                    ↑
                    │
         ┌──────────────────────┐
         │    End User          │
         └──────────────────────┘
```

### C4 Container Diagram (Epic 3 Orchestration)

```
┌────────────────────────────────────────────────────────────────┐
│                Epic 3: Analytical Query System                  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  MCP Server (FastMCP)                                     │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  analytical_query_financial_documents()            │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Orchestrator (AWS Strands Agent)                        │ │
│  │  - Model: Mistral Small / Claude Sonnet                 │ │
│  │  - Tools: [retrieval_agent, analysis_agent,             │ │
│  │            synthesis_agent]                              │ │
│  └──────────────────────────────────────────────────────────┘ │
│         │                    │                    │            │
│         ↓                    ↓                    ↓            │
│  ┌────────────┐      ┌────────────┐      ┌────────────┐      │
│  │ Retrieval  │      │ Analysis   │      │ Synthesis  │      │
│  │ Agent      │      │ Agent      │      │ Agent      │      │
│  │            │      │            │      │            │      │
│  │ @tool      │      │ @tool      │      │ @tool      │      │
│  │ async def  │      │ async def  │      │ async def  │      │
│  └────────────┘      └────────────┘      └────────────┘      │
│         │                    │                    │            │
│         ↓                    ↓                    ↓            │
│  ┌────────────┐      ┌────────────┐      ┌────────────┐      │
│  │ Multi-Index│      │ Claude API │      │ Citation   │      │
│  │ Search     │      │ (Analysis) │      │ Generator  │      │
│  │ (Epic 2)   │      │            │      │ (Epic 2)   │      │
│  └────────────┘      └────────────┘      └────────────┘      │
│         │                                        │             │
│         ↓                                        ↓             │
│  ┌────────────┐                          ┌────────────┐       │
│  │ Qdrant +   │                          │ OpenTelemetry│      │
│  │ PostgreSQL │                          │ (Auto Trace) │      │
│  └────────────┘                          └────────────┘       │
└────────────────────────────────────────────────────────────────┘
```

### Sequence Diagram (Successful Flow)

```
User → MCP: analytical_query("Q3 revenue vs Q4?")
MCP → Orchestrator: invoke_async(query)
Orchestrator → Mistral: "Which tool should I call first?"
Mistral → Orchestrator: "Call retrieval_agent"
Orchestrator → Retrieval Agent: retrieval_agent(query)
Retrieval Agent → Multi-Index: multi_index_search(query)
Multi-Index → Qdrant: vector_search()
Multi-Index → PostgreSQL: sql_search()
Multi-Index → Retrieval Agent: chunks=[...]
Retrieval Agent → Orchestrator: RetrievalOutput(chunks)
Orchestrator → Mistral: "Next action?"
Mistral → Orchestrator: "Call analysis_agent"
Orchestrator → Analysis Agent: analysis_agent(query, chunks)
Analysis Agent → Claude: analyze(chunks)
Claude → Analysis Agent: facts=[...]
Analysis Agent → Orchestrator: AnalysisOutput(facts)
Orchestrator → Mistral: "Next action?"
Mistral → Orchestrator: "Call synthesis_agent"
Orchestrator → Synthesis Agent: synthesis_agent(query, analysis)
Synthesis Agent → Claude: synthesize(facts)
Claude → Synthesis Agent: answer="..."
Synthesis Agent → Citation Gen: generate_citations(answer, facts)
Citation Gen → Synthesis Agent: answer_with_citations
Synthesis Agent → Orchestrator: SynthesisOutput(answer)
Orchestrator → MCP: AgentResult(message=answer)
MCP → User: QueryResponse(answer, citations, confidence)
```

---

## Performance Budget

### Latency Breakdown (Target vs POC)

| Component | Target (p50) | POC Actual | Target (p95) | Notes |
|-----------|-------------|------------|-------------|-------|
| **Orchestration Overhead** | 2-3s | 3.4s | 5-8s | Tunable via model choice |
| Retrieval Agent | 2s | 0.1s (mock) | 5s | Wraps Epic 2 search |
| Analysis Agent | 4s | 0.2s (mock) | 10s | LLM analysis call |
| Synthesis Agent | 3s | 0.25s (mock) | 8s | LLM synthesis + citations |
| **Total End-to-End** | **11-12s** | **~4s (mock)** | **28-31s** | Sum of components |

**Performance Optimization Strategies:**

1. **Orchestrator Model Choice (Story 3.1):**
   - Test Claude Sonnet for orchestration (expect ~2s vs 3.4s)
   - Benchmark Mistral Large vs Small

2. **Agent Parallelization (Story 3.5):**
   - Parallel vector + SQL search in Retrieval Agent (-2s)
   - Speculative analysis during retrieval (-1s)

3. **Caching (Epic 4):**
   - Cache retrieval results for common queries
   - Cache analysis for repeated document sets

4. **Streaming (Epic 4):**
   - Stream synthesis incrementally to user
   - Improves perceived latency

---

## Security Considerations

### API Key Management

**Current (Epic 3):**
- Mistral API key: `settings.mistral_api_key` (from .env)
- Claude API key: `settings.anthropic_api_key` (from .env)

**Future (Epic 5 - Production):**
- Move to AWS Secrets Manager
- Rotate keys automatically
- Audit API key usage

### Input Validation

**Query Validation:**
- Max query length: 500 characters
- No SQL injection attempts (parameterized queries)
- Rate limiting: 10 queries/minute per user (Epic 5)

### Output Sanitization

**Response Sanitization:**
- No raw database schema exposure
- Sanitize file paths in citations
- Redact sensitive PII if detected (Epic 5)

---

## Testing Strategy

### Unit Tests

**Per-Agent Testing:**
```python
# tests/unit/orchestration/test_retrieval_agent.py
@pytest.mark.asyncio
async def test_retrieval_agent_success(mock_multi_index_search):
    """Test retrieval agent with successful search."""
    mock_multi_index_search.return_value = mock_chunks

    result = await retrieval_agent("test query")

    assert result.chunks
    assert len(result.chunks) > 0
    assert result.search_metadata.retrieval_latency_ms < 5000
```

### Integration Tests

**Full Orchestration Flow:**
```python
# tests/integration/test_orchestration_flow.py
@pytest.mark.asyncio
async def test_full_orchestration_flow():
    """Test complete orchestration from query to synthesis."""
    query = "What was Q3 revenue?"

    response = await analytical_query_financial_documents(query)

    assert response.answer
    assert response.confidence in ["high", "medium", "low"]
    assert len(response.sources_used) > 0
```

### Performance Tests

**Latency Validation:**
```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_orchestration_latency():
    """Validate orchestration meets performance budget."""
    query = "Compare Q3 and Q4 revenue"

    start = time.time()
    result = await analytical_query_financial_documents(query)
    latency = (time.time() - start) * 1000

    assert latency < 15000  # 15s p50 acceptable
    assert result.answer
```

---

## Deployment Considerations

### Epic 3 Deployment (Local/Dev)

**No infrastructure changes:**
- Strands runs in-process (no new services)
- Uses existing Qdrant + PostgreSQL
- OpenTelemetry traces to stdout (dev mode)

**Configuration:**
```bash
# .env additions
ORCHESTRATOR_MODEL=mistral-small-latest  # or claude-3-5-sonnet
ORCHESTRATION_ENABLED=true
ORCHESTRATION_TIMEOUT_MS=30000
```

### Epic 5 Deployment (Production - AWS)

**Infrastructure Additions:**
- CloudWatch: Store OpenTelemetry traces
- X-Ray: Distributed tracing visualization
- Lambda: Async job queue for long-running queries (>30s)

**Monitoring Dashboards:**
- Agent execution latency trends
- Error rate by agent type
- Graceful degradation frequency
- Token usage and costs

---

## Open Questions & Future Work

### Open Questions (To Resolve in Story 3.1)

1. **Orchestrator Model Choice:**
   - Should we use Mistral (free, 3.4s overhead) or Claude (paid, ~2s expected)?
   - Cost vs latency tradeoff analysis needed

2. **Analysis Agent Depth:**
   - Standard vs deep analysis mode?
   - When to use each?

3. **Parallel Agent Execution:**
   - Can we parallelize retrieval backends (vector || SQL)?
   - Complexity vs 2s latency savings

### Future Enhancements (Epic 4+)

1. **Agent Memory:**
   - Multi-turn conversations with context retention
   - Strands session management

2. **Human-in-the-Loop:**
   - Interrupt orchestration for clarification
   - User feedback on agent decisions

3. **Agent Self-Improvement:**
   - Learn from successful/failed queries
   - Adaptive routing based on query complexity

---

## Document Status

**Current Status:** 🚧 DRAFT (AC2 in progress)

**Completed Sections:**
- ✅ Agent Specifications (Retrieval, Analysis, Synthesis)
- ✅ Orchestration Architecture
- ✅ Communication Patterns
- ✅ Error Handling Strategy
- ✅ Observability & Monitoring
- ✅ Integration Points
- ✅ Architecture Diagrams (C4 Context, Container, Sequence)
- ✅ Performance Budget
- ✅ Security Considerations
- ✅ Testing Strategy
- ✅ Deployment Considerations

**Pending:**
- [ ] Team review and feedback
- [ ] Winston's final sign-off
- [ ] Ricardo (Project Lead) approval

---

## References

- **Story 3.0.8:** `docs/stories/3-0-8-agentic-framework-architecture-spike.md`
- **Framework Selection:** `docs/architecture/epic-3-framework-selection.md`
- **Epic 3 PRD:** `docs/prd/epic-3-ai-intelligence-orchestration.md`
- **AWS Strands Docs:** https://github.com/awslabs/agents-for-amazon-bedrock-strands
- **RAGLite Epic 2 Architecture:** `docs/architecture/` (multi-index search baseline)

---

**Created By:** Winston (Architect)
**Date:** 2025-11-07
**Next Step:** Team review and Story 3.1 implementation planning
