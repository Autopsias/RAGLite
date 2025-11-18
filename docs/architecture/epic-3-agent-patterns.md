# Epic 3 Agent Workflow Patterns

**Document Type:** Design Patterns Guide
**Status:** ✅ COMPLETE
**Date:** 2025-11-07
**Authors:** Winston (Architect) + Amelia (Developer)
**Story:** Story 3.0.8 - AC3 (Workflow Pattern Examples)
**Framework:** AWS Strands (v1.15.0)

---

## Overview

This document provides reusable workflow patterns for multi-agent orchestration in RAGLite Epic 3. Each pattern includes:
- **Description:** What the pattern does
- **When to Use:** Applicability and use cases
- **Code Example:** AWS Strands implementation
- **Performance:** Expected latency characteristics
- **Trade-offs:** Pros and cons

All patterns use AWS Strands' event-driven architecture with the `@tool` decorator pattern.

---

## Pattern 1: Sequential Chain Pattern

### Description

The Sequential Chain Pattern executes agents in a fixed linear order where each agent's output becomes the next agent's input. This is the foundational pattern for RAGLite's analytical queries.

**Flow:**
```
Query → Agent A → Agent B → Agent C → Result
```

### When to Use

**✅ Use when:**
- Agents have clear sequential dependencies (output of A needed by B)
- Order of execution is deterministic and fixed
- Each agent must complete before the next begins
- Workflow is simple and linear (no branching)

**❌ Avoid when:**
- Agents can run independently in parallel
- Complex branching logic is needed
- Need to optimize for lowest latency (parallelization possible)

### RAGLite Use Case

**Primary Epic 3 workflow:** Retrieval → Analysis → Synthesis

1. **Retrieval Agent** searches documents
2. **Analysis Agent** interprets retrieved chunks
3. **Synthesis Agent** generates final answer with citations

### Code Example

```python
"""Sequential Chain Pattern - RAGLite Epic 3 Core Workflow."""

from strands import Agent, tool
from strands.models.mistral import MistralModel
from pydantic import BaseModel, Field
from raglite.shared.config import settings


# ============================================================================
# Agent Definitions
# ============================================================================

@tool
async def retrieval_agent(query: str, top_k: int = 5) -> str:
    """Agent 1: Retrieve relevant document chunks.

    Args:
        query: Natural language query
        top_k: Number of chunks to retrieve

    Returns:
        JSON string with retrieved chunks and metadata
    """
    from raglite.retrieval.multi_index_search import multi_index_search

    # Execute multi-index search (Epic 2 integration)
    results = await multi_index_search(query, top_k=top_k)

    # Format results for next agent
    output = {
        "chunks": [
            {
                "content": chunk.content,
                "score": chunk.score,
                "page": chunk.page,
                "doc_id": chunk.doc_id
            }
            for chunk in results.chunks
        ],
        "query": query,
        "total_retrieved": len(results.chunks)
    }

    return json.dumps(output)


@tool
async def analysis_agent(retrieval_results: str) -> str:
    """Agent 2: Analyze retrieved chunks and extract key facts.

    Args:
        retrieval_results: JSON string from retrieval_agent

    Returns:
        JSON string with analysis results
    """
    import json
    from anthropic import AsyncAnthropic

    results = json.loads(retrieval_results)
    chunks = results["chunks"]
    query = results["query"]

    # LLM analysis call (Claude Sonnet)
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Analyze these document chunks for the query: "{query}"

Chunks:
{json.dumps(chunks, indent=2)}

Extract:
1. Key facts with page references
2. Relevant insights
3. Any contradictions

Return JSON format:
{{
  "facts": [
    {{"statement": "...", "page": 3, "confidence": 0.9}}
  ],
  "insights": ["..."],
  "contradictions": []
}}"""

    response = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        temperature=0.1,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text


@tool
async def synthesis_agent(analysis_results: str, original_query: str) -> str:
    """Agent 3: Synthesize final answer with citations.

    Args:
        analysis_results: JSON string from analysis_agent
        original_query: Original user query (for context)

    Returns:
        Final answer with citations
    """
    import json
    from anthropic import AsyncAnthropic
    from raglite.retrieval.attribution import generate_citations

    analysis = json.loads(analysis_results)

    # LLM synthesis call (Claude Sonnet)
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Synthesize a comprehensive answer to: "{original_query}"

Based on this analysis:
{json.dumps(analysis, indent=2)}

Requirements:
- Direct, clear answer
- Use facts from analysis
- Mention page numbers inline [page X]
- Note any limitations or contradictions

Write a natural, informative response."""

    response = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=3000,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}]
    )

    answer = response.content[0].text

    # Add formatted citations
    answer_with_citations = await generate_citations(
        answer=answer,
        facts=analysis.get("facts", [])
    )

    return answer_with_citations


# ============================================================================
# Orchestrator Setup
# ============================================================================

def create_sequential_orchestrator() -> Agent:
    """Create orchestrator using Sequential Chain Pattern.

    The orchestrator will call agents in fixed order:
    1. retrieval_agent
    2. analysis_agent (with retrieval results)
    3. synthesis_agent (with analysis results)

    Returns:
        Configured Strands Agent
    """
    # Create model (Mistral or Claude)
    model = MistralModel(
        api_key=settings.mistral_api_key,
        model_id=settings.metadata_extraction_model  # "mistral-small-latest"
    )

    orchestrator = Agent(
        model=model,
        tools=[retrieval_agent, analysis_agent, synthesis_agent],
        system_prompt="""You are an orchestrator for financial document analysis.

Execute agents in this EXACT order:
1. Call retrieval_agent with the user's query
2. Call analysis_agent with the retrieval results
3. Call synthesis_agent with the analysis results

Always execute all three agents. Return the final synthesis to the user."""
    )

    return orchestrator


# ============================================================================
# Usage Example
# ============================================================================

async def execute_sequential_query(query: str) -> str:
    """Execute query using Sequential Chain Pattern.

    Args:
        query: User's natural language query

    Returns:
        Final synthesized answer with citations
    """
    orchestrator = create_sequential_orchestrator()
    result = await orchestrator.invoke_async(query)
    return str(result)


# Example:
# answer = await execute_sequential_query("What was Q3 revenue?")
# print(answer)
```

### Performance Characteristics

**Latency:**
- **Best Case (p50):** 11-12s
  - Orchestration: 3s
  - Retrieval: 2s
  - Analysis: 4s
  - Synthesis: 3s
- **Worst Case (p95):** 28-31s
  - Orchestration: 5s
  - Retrieval: 5s
  - Analysis: 10s
  - Synthesis: 8s

**Throughput:** Serial execution limits throughput to 1 query per 11-12s

### Trade-offs

**Pros:**
- ✅ Simple to understand and implement
- ✅ Clear data flow (explicit dependencies)
- ✅ Easy to debug (linear execution trace)
- ✅ Predictable behavior (no race conditions)

**Cons:**
- ❌ Cannot parallelize independent operations
- ❌ Slowest latency (sum of all agents)
- ❌ Single point of failure (one agent fails → all fail)
- ❌ Not optimal for simple queries (full overhead)

### Optimization Opportunities

1. **Conditional Short-Circuit (Pattern 3):** Skip analysis for simple queries
2. **Parallel Retrieval (Pattern 2):** Run vector + SQL searches in parallel
3. **Speculative Analysis:** Start analysis before retrieval fully completes
4. **Caching:** Cache retrieval results for repeated queries

---

## Pattern 2: Parallel Execution Pattern

### Description

The Parallel Execution Pattern runs multiple independent agents concurrently and aggregates their results. Used when agents don't depend on each other's outputs.

**Flow:**
```
        ┌──→ Agent A ──┐
Query ──┼──→ Agent B ──┼──→ Aggregator → Result
        └──→ Agent C ──┘
```

### When to Use

**✅ Use when:**
- Agents are independent (no input dependencies)
- Need to minimize latency (critical path optimization)
- Multiple data sources can be queried simultaneously
- Results can be merged/aggregated cleanly

**❌ Avoid when:**
- Agents have sequential dependencies
- Parallel execution complexity outweighs latency savings
- Difficult to aggregate divergent results

### RAGLite Use Case

**Multi-Backend Retrieval:** Query vector database and SQL database in parallel

Instead of:
```
Query → Vector Search → SQL Search → Merge → Analysis
```

Use:
```
Query → [Vector Search || SQL Search] → Merge → Analysis
```

**Latency Savings:** ~2-3s (max of parallel operations vs sum)

### Code Example

```python
"""Parallel Execution Pattern - Multi-Backend Retrieval."""

import asyncio
from strands import Agent, tool
from pydantic import BaseModel, Field
from typing import List


# ============================================================================
# Parallel Agent Definitions
# ============================================================================

@tool
async def vector_search_agent(query: str, top_k: int = 5) -> str:
    """Agent A: Vector similarity search via Qdrant.

    Runs independently in parallel with SQL search.
    """
    from raglite.retrieval.search import search_qdrant

    results = await search_qdrant(query, top_k=top_k)

    return json.dumps({
        "source": "vector",
        "chunks": [{"content": r.content, "score": r.score} for r in results],
        "latency_ms": results.latency_ms
    })


@tool
async def sql_search_agent(query: str, top_k: int = 5) -> str:
    """Agent B: SQL table search via PostgreSQL.

    Runs independently in parallel with vector search.
    """
    from raglite.retrieval.sql_search import search_sql_tables

    results = await search_sql_tables(query, top_k=top_k)

    return json.dumps({
        "source": "sql",
        "chunks": [{"content": r.content, "score": r.score} for r in results],
        "latency_ms": results.latency_ms
    })


@tool
async def merge_results_agent(vector_results: str, sql_results: str) -> str:
    """Agent C: Merge and re-rank parallel search results.

    Aggregates results from vector_search_agent and sql_search_agent.
    """
    import json

    vector_data = json.loads(vector_results)
    sql_data = json.loads(sql_results)

    # Combine and re-rank (simple score-based merge)
    all_chunks = (
        vector_data["chunks"] +
        sql_data["chunks"]
    )

    # Sort by score descending
    all_chunks.sort(key=lambda x: x["score"], reverse=True)

    # Take top K from merged results
    merged = all_chunks[:10]

    return json.dumps({
        "merged_chunks": merged,
        "total_sources": 2,
        "vector_count": len(vector_data["chunks"]),
        "sql_count": len(sql_data["chunks"])
    })


# ============================================================================
# Orchestrator Setup
# ============================================================================

def create_parallel_orchestrator() -> Agent:
    """Create orchestrator using Parallel Execution Pattern.

    The orchestrator will:
    1. Call vector_search_agent and sql_search_agent IN PARALLEL
    2. Wait for both to complete
    3. Call merge_results_agent with both results

    Returns:
        Configured Strands Agent
    """
    from strands.models.mistral import MistralModel

    model = MistralModel(
        api_key=settings.mistral_api_key,
        model_id="mistral-small-latest"
    )

    orchestrator = Agent(
        model=model,
        tools=[vector_search_agent, sql_search_agent, merge_results_agent],
        system_prompt="""You are an orchestrator for parallel retrieval.

Execute this workflow:
1. Call BOTH vector_search_agent AND sql_search_agent (in parallel)
2. Wait for both to return results
3. Call merge_results_agent with both results
4. Return the merged results

Important: Call vector_search_agent and sql_search_agent simultaneously."""
    )

    return orchestrator


# ============================================================================
# Manual Parallel Execution (Alternative)
# ============================================================================

async def execute_parallel_retrieval_manual(query: str) -> dict:
    """Execute parallel retrieval without orchestrator.

    Direct implementation using asyncio.gather for guaranteed parallelism.

    Args:
        query: User's query

    Returns:
        Merged search results
    """
    # Execute searches in parallel
    vector_task = vector_search_agent(query, top_k=5)
    sql_task = sql_search_agent(query, top_k=5)

    # Wait for both to complete
    vector_results, sql_results = await asyncio.gather(vector_task, sql_task)

    # Merge results
    merged = await merge_results_agent(vector_results, sql_results)

    return json.loads(merged)
```

### Performance Characteristics

**Latency Improvement:**
- **Sequential:** Vector (2s) + SQL (2s) = 4s
- **Parallel:** max(Vector (2s), SQL (2s)) = 2s
- **Savings:** 50% latency reduction

**Orchestrator Overhead:**
- Event-driven orchestrator may not guarantee true parallelism
- Manual `asyncio.gather()` guarantees parallel execution
- Trade-off: Orchestrator (flexible, 3s overhead) vs Manual (optimal, no overhead)

### Trade-offs

**Pros:**
- ✅ Significant latency reduction (50% for 2 parallel agents)
- ✅ Better resource utilization (parallel I/O)
- ✅ Scales with number of independent operations

**Cons:**
- ❌ More complex implementation (aggregation logic needed)
- ❌ Orchestrator may not guarantee true parallelism
- ❌ Error handling more complex (partial failures)
- ❌ Results must be mergeable (conflict resolution)

### Implementation Notes

**Strands Limitation:** Event-driven orchestrators may execute tools sequentially despite "parallel" instructions. For guaranteed parallelism, use manual `asyncio.gather()` pattern.

**When to use manual pattern:**
- Latency is critical (<2s budget)
- Parallel execution MUST be guaranteed
- Simple aggregation logic

**When to use orchestrator pattern:**
- Flexibility in execution order preferred
- Orchestrator can optimize based on query
- Acceptable to have sequential fallback

---

## Pattern 3: Conditional Routing Pattern

### Description

The Conditional Routing Pattern routes queries to different agent workflows based on query characteristics. Optimizes for common cases while handling complex cases appropriately.

**Flow:**
```
Query → Classifier → Simple? → Fast Path (Epic 2)
                  → Complex? → Full Orchestration (Epic 3)
```

### When to Use

**✅ Use when:**
- Queries have distinct complexity levels
- Simple cases can bypass expensive processing
- Want to optimize p50 latency (most queries simple)
- Cost optimization important (LLM API calls)

**❌ Avoid when:**
- All queries require same processing
- Classification overhead exceeds savings
- Query complexity uniform

### RAGLite Use Case

**Query Complexity Routing:**

- **Simple Queries** (70% of traffic): "What was Q3 revenue?"
  - Route to Epic 2 simple search (4.7s latency)
  - Skip orchestration (save 3s + analysis + synthesis)

- **Complex Queries** (30% of traffic): "Compare Q3 to Q4 and explain variance"
  - Route to Epic 3 full orchestration (12s latency)
  - Use analysis + synthesis agents

**Average Latency Improvement:**
- Before: All queries use Epic 3 (12s average)
- After: 70% × 4.7s + 30% × 12s = 6.9s average (42% improvement)

### Code Example

```python
"""Conditional Routing Pattern - Query Complexity Classifier."""

from strands import Agent, tool
from enum import Enum


class QueryComplexity(str, Enum):
    SIMPLE = "simple"       # Direct fact retrieval
    ANALYTICAL = "analytical"  # Multi-step reasoning
    COMPARATIVE = "comparative"  # Cross-document comparison


# ============================================================================
# Classification Agent
# ============================================================================

@tool
async def classify_query_complexity(query: str) -> str:
    """Classifier: Determine query complexity level.

    Args:
        query: User's natural language query

    Returns:
        JSON with classification: {"complexity": "simple|analytical|comparative", "confidence": 0.9}
    """
    from anthropic import AsyncAnthropic
    import json

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Classify this financial query's complexity:

Query: "{query}"

Complexity Levels:
- SIMPLE: Direct fact retrieval (e.g., "What was Q3 revenue?")
- ANALYTICAL: Requires interpretation (e.g., "Why did revenue increase?")
- COMPARATIVE: Cross-document comparison (e.g., "Compare Q3 vs Q4 revenue")

Return JSON:
{{
  "complexity": "simple|analytical|comparative",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}"""

    response = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=200,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text


@tool
async def simple_search_path(query: str) -> str:
    """Fast Path: Epic 2 simple search (no orchestration).

    For simple queries that don't need analysis or synthesis.
    """
    from raglite.retrieval.multi_index_search import multi_index_search
    from raglite.retrieval.attribution import generate_citations

    # Direct search
    results = await multi_index_search(query, top_k=5)

    # Basic citation generation
    answer = f"Based on the documents:\n\n"
    for i, chunk in enumerate(results.chunks, 1):
        answer += f"[{i}] {chunk.content} (Page {chunk.page})\n\n"

    return answer


@tool
async def complex_orchestration_path(query: str) -> str:
    """Complex Path: Epic 3 full orchestration.

    For analytical/comparative queries needing multi-agent reasoning.
    """
    # Use Sequential Chain Pattern (Pattern 1)
    orchestrator = create_sequential_orchestrator()
    result = await orchestrator.invoke_async(query)
    return str(result)


# ============================================================================
# Routing Orchestrator
# ============================================================================

def create_routing_orchestrator() -> Agent:
    """Create orchestrator using Conditional Routing Pattern.

    Workflow:
    1. Classify query complexity
    2. IF simple → simple_search_path
    3. IF analytical/comparative → complex_orchestration_path

    Returns:
        Configured Strands Agent
    """
    from strands.models.mistral import MistralModel

    model = MistralModel(
        api_key=settings.mistral_api_key,
        model_id="mistral-small-latest"
    )

    orchestrator = Agent(
        model=model,
        tools=[
            classify_query_complexity,
            simple_search_path,
            complex_orchestration_path
        ],
        system_prompt="""You are a routing orchestrator.

Workflow:
1. Call classify_query_complexity with the user's query
2. IF complexity is "simple":
   - Call simple_search_path (fast, no analysis needed)
3. IF complexity is "analytical" or "comparative":
   - Call complex_orchestration_path (full multi-agent reasoning)

Return the result from whichever path was chosen."""
    )

    return orchestrator


# ============================================================================
# Usage Example
# ============================================================================

async def execute_routed_query(query: str) -> str:
    """Execute query with automatic complexity routing.

    Args:
        query: User's natural language query

    Returns:
        Answer (via simple path or complex path)
    """
    orchestrator = create_routing_orchestrator()
    result = await orchestrator.invoke_async(query)
    return str(result)


# Examples:
# Simple query (uses fast path):
# answer = await execute_routed_query("What was Q3 revenue?")
#
# Complex query (uses full orchestration):
# answer = await execute_routed_query("Compare Q3 and Q4 revenue trends")
```

### Performance Characteristics

**Latency by Query Type:**

| Query Type | Percentage | Latency | Path |
|------------|-----------|---------|------|
| Simple | 70% | 4.7s | Epic 2 direct |
| Analytical | 20% | 12s | Epic 3 orchestration |
| Comparative | 10% | 12s | Epic 3 orchestration |

**Average Latency:**
- Without routing: 12s (all use Epic 3)
- With routing: 6.9s (70% use Epic 2)
- **Improvement: 42%**

**Classification Overhead:** +500ms (acceptable for 5s+ savings on simple queries)

### Trade-offs

**Pros:**
- ✅ 42% average latency improvement
- ✅ Cost savings (fewer LLM API calls for simple queries)
- ✅ Better user experience (simple queries feel instant)
- ✅ Scalable (most queries are simple)

**Cons:**
- ❌ Classification overhead (500ms)
- ❌ Misclassification risk (simple query routed to complex path or vice versa)
- ❌ More complex codebase (2 paths to maintain)
- ❌ Requires query complexity tuning

### Implementation Notes

**Classification Accuracy:** Target 90%+ to avoid user frustration from misrouting

**Misclassification Handling:**
- Simple → Complex: Acceptable (slower but correct)
- Complex → Simple: Bad (incomplete answer)
- Mitigation: Bias classifier toward complex when uncertain

**Future Enhancement (Epic 4):** Learn from user feedback to improve classification

---

## Pattern 4: Error Fallback Pattern

### Description

The Error Fallback Pattern implements graceful degradation when agents fail, ensuring the system always returns *something* useful to the user rather than complete failure.

**Flow:**
```
Try Full Orchestration → Fail? → Try Partial → Fail? → Fallback to Baseline
```

### When to Use

**✅ Use when:**
- System reliability is critical (production systems)
- Partial results are better than no results
- Multiple tiers of functionality exist
- User experience must never completely break

**❌ Avoid when:**
- Partial results are misleading or dangerous
- All-or-nothing requirement (e.g., financial transactions)
- Debugging is more important than uptime (development)

### RAGLite Use Case

**4-Tier Graceful Degradation:**

1. **Tier 1 (Best):** Full orchestration succeeds (Retrieval + Analysis + Synthesis)
2. **Tier 2 (Good):** Retrieval + Analysis succeed, Synthesis fails (return analyzed facts)
3. **Tier 3 (Acceptable):** Retrieval succeeds, Analysis + Synthesis fail (return raw chunks)
4. **Tier 4 (Fallback):** Everything fails → Epic 2 simple search

**Availability Target:** 99.9% (even if Epic 3 agents fail, Epic 2 fallback works)

### Code Example

```python
"""Error Fallback Pattern - Graceful Degradation Implementation."""

from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ResponseTier(str, Enum):
    """Quality tier of the response."""
    FULL_ORCHESTRATION = "full"      # All 3 agents succeeded
    PARTIAL_ANALYSIS = "partial"     # Retrieval + Analysis only
    RETRIEVAL_ONLY = "retrieval"     # Retrieval only (raw chunks)
    FALLBACK_EPIC2 = "fallback"      # Epic 2 simple search


class DegradedResponse(BaseModel):
    """Response with degradation metadata."""
    answer: str
    tier: ResponseTier
    confidence: str  # "high" | "medium" | "low" | "none"
    limitations: List[str]
    error_details: Optional[str] = None


# ============================================================================
# Tiered Execution with Fallbacks
# ============================================================================

async def execute_with_fallback(query: str) -> DegradedResponse:
    """Execute query with 4-tier graceful degradation.

    Tries each tier in order, falling back on failures:
    Tier 1 → Tier 2 → Tier 3 → Tier 4

    Args:
        query: User's query

    Returns:
        DegradedResponse with answer and tier metadata
    """

    # ========================================================================
    # TIER 1: Full Orchestration (Best)
    # ========================================================================
    try:
        logger.info("Attempting Tier 1: Full orchestration", extra={"query": query})

        # Execute all 3 agents
        retrieval_results = await retrieval_agent(query)
        analysis_results = await analysis_agent(retrieval_results)
        synthesis_result = await synthesis_agent(analysis_results, query)

        logger.info("Tier 1 success", extra={"query": query})

        return DegradedResponse(
            answer=synthesis_result,
            tier=ResponseTier.FULL_ORCHESTRATION,
            confidence="high",
            limitations=[]
        )

    except SynthesisError as e:
        logger.warning("Tier 1 failed: Synthesis error", extra={"error": str(e)})
        # Fall through to Tier 2

    except Exception as e:
        logger.error("Tier 1 failed: Unexpected error", extra={"error": str(e)})
        # Fall through to Tier 2

    # ========================================================================
    # TIER 2: Partial Analysis (Good)
    # ========================================================================
    try:
        logger.info("Attempting Tier 2: Retrieval + Analysis", extra={"query": query})

        # Try retrieval + analysis (synthesis already failed above)
        if 'retrieval_results' not in locals():
            retrieval_results = await retrieval_agent(query)

        if 'analysis_results' not in locals():
            analysis_results = await analysis_agent(retrieval_results)

        # Format analysis as readable answer
        analysis = json.loads(analysis_results)
        answer = f"Based on the analysis (synthesis unavailable):\n\n"

        for fact in analysis.get("facts", []):
            answer += f"• {fact['statement']} (Page {fact['page']}, confidence: {fact['confidence']})\n"

        if analysis.get("insights"):
            answer += "\nInsights:\n"
            for insight in analysis["insights"]:
                answer += f"• {insight}\n"

        logger.info("Tier 2 success", extra={"query": query})

        return DegradedResponse(
            answer=answer,
            tier=ResponseTier.PARTIAL_ANALYSIS,
            confidence="medium",
            limitations=["Synthesis agent unavailable - showing analyzed facts instead"],
            error_details="Synthesis failed"
        )

    except AnalysisError as e:
        logger.warning("Tier 2 failed: Analysis error", extra={"error": str(e)})
        # Fall through to Tier 3

    except Exception as e:
        logger.error("Tier 2 failed: Unexpected error", extra={"error": str(e)})
        # Fall through to Tier 3

    # ========================================================================
    # TIER 3: Retrieval Only (Acceptable)
    # ========================================================================
    try:
        logger.info("Attempting Tier 3: Retrieval only", extra={"query": query})

        # Try retrieval only (analysis already failed above)
        if 'retrieval_results' not in locals():
            retrieval_results = await retrieval_agent(query)

        # Format chunks as basic answer
        chunks_data = json.loads(retrieval_results)
        answer = f"Found {len(chunks_data['chunks'])} relevant documents (analysis unavailable):\n\n"

        for i, chunk in enumerate(chunks_data["chunks"], 1):
            answer += f"[{i}] {chunk['content'][:200]}... (Page {chunk['page']})\n\n"

        logger.info("Tier 3 success", extra={"query": query})

        return DegradedResponse(
            answer=answer,
            tier=ResponseTier.RETRIEVAL_ONLY,
            confidence="low",
            limitations=[
                "Analysis and synthesis unavailable",
                "Showing raw document chunks without interpretation"
            ],
            error_details="Analysis and synthesis failed"
        )

    except RetrievalError as e:
        logger.warning("Tier 3 failed: Retrieval error", extra={"error": str(e)})
        # Fall through to Tier 4

    except Exception as e:
        logger.error("Tier 3 failed: Unexpected error", extra={"error": str(e)})
        # Fall through to Tier 4

    # ========================================================================
    # TIER 4: Epic 2 Fallback (Last Resort)
    # ========================================================================
    try:
        logger.warning("All Epic 3 agents failed, falling back to Epic 2", extra={"query": query})

        # Fall back to Epic 2 simple search
        from raglite.main import query_financial_documents

        epic2_result = await query_financial_documents(query)

        return DegradedResponse(
            answer=f"⚠️ Advanced analysis unavailable. Basic search results:\n\n{epic2_result.answer}",
            tier=ResponseTier.FALLBACK_EPIC2,
            confidence="none",
            limitations=[
                "All Epic 3 agents unavailable",
                "Showing Epic 2 baseline search results",
                "No analysis or synthesis performed"
            ],
            error_details="Complete Epic 3 failure"
        )

    except Exception as e:
        logger.critical("TIER 4 FAILED: Complete system failure", extra={"error": str(e)})

        # Absolute last resort: return error message
        return DegradedResponse(
            answer="Sorry, the system is experiencing issues and cannot process your query at this time. Please try again later.",
            tier=ResponseTier.FALLBACK_EPIC2,
            confidence="none",
            limitations=["Complete system failure"],
            error_details=f"All tiers failed: {str(e)}"
        )


# ============================================================================
# MCP Tool Integration
# ============================================================================

@mcp.tool()
async def analytical_query_financial_documents(query: str) -> QueryResponse:
    """Analytical query with graceful degradation.

    Implements 4-tier fallback:
    1. Full orchestration (best)
    2. Partial analysis (good)
    3. Retrieval only (acceptable)
    4. Epic 2 fallback (last resort)

    Args:
        query: Natural language query

    Returns:
        QueryResponse with answer and metadata
    """
    result = await execute_with_fallback(query)

    # Log degradation events for monitoring
    if result.tier != ResponseTier.FULL_ORCHESTRATION:
        logger.warning(
            "Degraded response returned",
            extra={
                "query": query,
                "tier": result.tier,
                "confidence": result.confidence,
                "limitations": result.limitations
            }
        )

    return QueryResponse(
        answer=result.answer,
        confidence=result.confidence,
        metadata={
            "tier": result.tier,
            "limitations": result.limitations,
            "error_details": result.error_details
        }
    )
```

### Performance Characteristics

**Latency by Tier:**

| Tier | Success Rate | Latency | User Experience |
|------|-------------|---------|-----------------|
| Tier 1 | 95% | 12s | Excellent |
| Tier 2 | 4% | 9s | Good |
| Tier 3 | 0.9% | 5s | Acceptable |
| Tier 4 | 0.1% | 5s | Poor but functional |

**Availability:** 99.9%+ (even if Epic 3 completely fails, Epic 2 works)

### Trade-offs

**Pros:**
- ✅ 99.9%+ availability (high reliability)
- ✅ Always returns something useful
- ✅ User experience degrades gracefully (not abruptly)
- ✅ Explicit error visibility (tier metadata)

**Cons:**
- ❌ Complex error handling code (~200 LOC)
- ❌ Difficult to test all failure scenarios
- ❌ May hide underlying issues (mask failures)
- ❌ User confusion about partial results

### Monitoring Recommendations

**Key Metrics:**
- Tier 1 success rate (target: 95%+)
- Tier 2 fallback rate (target: <5%)
- Tier 3 fallback rate (target: <1%)
- Tier 4 fallback rate (alert: >0.1%)

**Alerting:**
- Alert if Tier 1 success rate <90% (agent health issue)
- Alert if Tier 4 rate >1% (systemic failure)
- Track degradation trends over time

---

## Pattern 5: Hierarchical Orchestration Pattern

### Description

The Hierarchical Orchestration Pattern uses a master orchestrator that delegates to specialized sub-orchestrators, each managing their own set of agents. Enables complex workflows with logical groupings.

**Flow:**
```
                  Master Orchestrator
                         │
        ┌────────────────┼────────────────┐
        ↓                ↓                 ↓
   Financial        Forecasting        Risk
   Sub-Orchestrator  Sub-Orchestrator   Sub-Orchestrator
   │                 │                   │
   ├─ Retrieval      ├─ Trend            ├─ Anomaly
   ├─ Analysis       ├─ Prophet          ├─ Threshold
   └─ Synthesis      └─ Forecast         └─ Alert
```

### When to Use

**✅ Use when:**
- Workflow has logical domain groupings (financial, forecasting, risk)
- Sub-workflows are reusable across different queries
- Need to scale agent count beyond simple linear chains
- Want to parallelize independent sub-workflows

**❌ Avoid when:**
- Simple linear workflow sufficient (use Pattern 1)
- Limited agent count (<5 total agents)
- Adds unnecessary complexity for current needs

### RAGLite Use Case

**Epic 4 Multi-Domain Analysis:**

- **Master Orchestrator:** Coordinates 3 sub-domains
- **Financial Sub-Orchestrator:** Handles document retrieval and analysis (Epic 3)
- **Forecasting Sub-Orchestrator:** Handles time-series prediction (Epic 4)
- **Risk Sub-Orchestrator:** Handles anomaly detection (Epic 4)

**Example Query:** "What was Q3 revenue, what's the Q4 forecast, and are there any anomalies?"

**Execution:**
1. Master delegates to all 3 sub-orchestrators (parallel)
2. Each sub-orchestrator runs its workflow
3. Master aggregates results into comprehensive answer

### Code Example

```python
"""Hierarchical Orchestration Pattern - Multi-Domain Master Orchestrator."""

from strands import Agent, tool


# ============================================================================
# Sub-Orchestrator 1: Financial Analysis (Epic 3)
# ============================================================================

@tool
async def financial_analysis_orchestrator(query: str) -> str:
    """Sub-Orchestrator: Financial document analysis.

    Manages: Retrieval → Analysis → Synthesis (Pattern 1)
    """
    # Reuse Sequential Chain Pattern from Epic 3
    orchestrator = create_sequential_orchestrator()
    result = await orchestrator.invoke_async(query)

    return json.dumps({
        "domain": "financial_analysis",
        "result": str(result)
    })


# ============================================================================
# Sub-Orchestrator 2: Forecasting (Epic 4)
# ============================================================================

@tool
async def forecasting_orchestrator(query: str, time_horizon: str = "1_quarter") -> str:
    """Sub-Orchestrator: Time-series forecasting.

    Manages: Trend Analysis → Prophet Model → Forecast Generation
    """
    # Placeholder for Epic 4 implementation
    return json.dumps({
        "domain": "forecasting",
        "forecast": "Q4 2023 projected revenue: $160M (+6.7%)",
        "confidence_interval": "[155M, 165M]",
        "model": "prophet"
    })


# ============================================================================
# Sub-Orchestrator 3: Risk Analysis (Epic 4)
# ============================================================================

@tool
async def risk_analysis_orchestrator(query: str) -> str:
    """Sub-Orchestrator: Anomaly detection and risk assessment.

    Manages: Anomaly Detection → Threshold Analysis → Risk Scoring
    """
    # Placeholder for Epic 4 implementation
    return json.dumps({
        "domain": "risk_analysis",
        "anomalies": ["Q2 operating expenses +45% (outlier)"],
        "risk_score": 0.35,
        "risk_level": "moderate"
    })


# ============================================================================
# Master Orchestrator
# ============================================================================

def create_master_orchestrator() -> Agent:
    """Create master orchestrator managing 3 sub-orchestrators.

    The master delegates to specialized sub-orchestrators:
    - Financial Analysis (Epic 3 agents)
    - Forecasting (Epic 4 agents)
    - Risk Analysis (Epic 4 agents)

    Returns:
        Configured master Strands Agent
    """
    from strands.models.mistral import MistralModel

    model = MistralModel(
        api_key=settings.mistral_api_key,
        model_id="mistral-small-latest"
    )

    orchestrator = Agent(
        model=model,
        tools=[
            financial_analysis_orchestrator,
            forecasting_orchestrator,
            risk_analysis_orchestrator
        ],
        system_prompt="""You are a master orchestrator for comprehensive financial analysis.

You manage 3 sub-orchestrators:
1. financial_analysis_orchestrator - Historical document analysis
2. forecasting_orchestrator - Future predictions
3. risk_analysis_orchestrator - Anomaly detection

Analyze the user's query and determine which sub-orchestrators to invoke:
- Queries about historical data → financial_analysis_orchestrator
- Queries about future predictions → forecasting_orchestrator
- Queries about risks/anomalies → risk_analysis_orchestrator
- Complex queries → Multiple sub-orchestrators (can run in parallel)

Aggregate results from all sub-orchestrators into a comprehensive answer."""
    )

    return orchestrator


# ============================================================================
# Usage Example
# ============================================================================

async def execute_hierarchical_query(query: str) -> str:
    """Execute query using Hierarchical Orchestration Pattern.

    Args:
        query: User's comprehensive query (may span multiple domains)

    Returns:
        Aggregated answer from relevant sub-orchestrators
    """
    master = create_master_orchestrator()
    result = await master.invoke_async(query)
    return str(result)


# Example:
# Comprehensive query (triggers all 3 sub-orchestrators):
# answer = await execute_hierarchical_query(
#     "What was Q3 revenue, what's the Q4 forecast, and are there any financial risks?"
# )
#
# Output:
# """
# **Q3 Revenue Analysis:**
# Q3 2023 revenue was $150M, up 10% from Q2... [from financial_analysis_orchestrator]
#
# **Q4 Forecast:**
# Q4 2023 projected revenue: $160M (+6.7% growth), confidence interval [155M, 165M]
# [from forecasting_orchestrator]
#
# **Risk Assessment:**
# Moderate risk detected: Q2 operating expenses increased 45% (outlier). Risk score: 0.35/1.0
# [from risk_analysis_orchestrator]
# """
```

### Performance Characteristics

**Latency:**
- **Sequential sub-orchestrators:** Sum of all sub-workflows (~30s)
- **Parallel sub-orchestrators:** Max of all sub-workflows (~12s)
- **Master overhead:** +2s (delegation decisions)

**Scalability:**
- Can add new sub-orchestrators without modifying existing ones
- Each sub-orchestrator independently scalable
- Master orchestrator becomes bottleneck beyond ~10 sub-orchestrators

### Trade-offs

**Pros:**
- ✅ Clean separation of concerns (domain-specific logic isolated)
- ✅ Reusable sub-orchestrators (financial analysis used in multiple queries)
- ✅ Parallel execution possible (independent sub-workflows)
- ✅ Scales to complex multi-domain workflows

**Cons:**
- ❌ High complexity (orchestrators managing orchestrators)
- ❌ Difficult to debug (nested execution traces)
- ❌ Master orchestrator overhead (~2s)
- ❌ Over-engineering for simple use cases

### Implementation Notes

**When to implement:**
- Epic 4+ (when forecasting and risk analysis are added)
- NOT for Epic 3 (simple sequential chain sufficient)

**Sub-Orchestrator Design:**
- Each sub-orchestrator should be independently testable
- Use Pattern 1 (Sequential Chain) within sub-orchestrators
- Master should NOT know internals of sub-orchestrators (encapsulation)

**Testing Strategy:**
- Test each sub-orchestrator in isolation
- Mock sub-orchestrators when testing master
- End-to-end tests validate full hierarchy

---

## Pattern Selection Guide

### Decision Matrix

| Pattern | Latency | Complexity | Use Case | RAGLite Phase |
|---------|---------|-----------|----------|---------------|
| **1. Sequential Chain** | Slowest (11-12s) | Low | Standard workflows, clear dependencies | Epic 3 (Primary) |
| **2. Parallel Execution** | Fast (saves 50%) | Medium | Independent operations, latency-critical | Epic 3.5 (Optimization) |
| **3. Conditional Routing** | Variable (4-12s) | Medium | Mixed complexity queries | Story 3.6 (Enhancement) |
| **4. Error Fallback** | N/A | High | Production reliability | Epic 3 (Core) |
| **5. Hierarchical** | Variable (12-30s) | Very High | Multi-domain workflows | Epic 4 (Future) |

### RAGLite Implementation Roadmap

**Epic 3 Sprint 1-2 (Weeks 1-2):**
- ✅ Pattern 1 (Sequential Chain) - Primary workflow
- ✅ Pattern 4 (Error Fallback) - Production reliability

**Epic 3 Sprint 3 (Week 3):**
- ⚠️ Pattern 3 (Conditional Routing) - If latency issues

**Epic 3.5 (Performance Sprint):**
- ⚠️ Pattern 2 (Parallel Execution) - If p95 latency >20s

**Epic 4 (Forecasting & Insights):**
- ⚠️ Pattern 5 (Hierarchical) - When adding forecasting domain

---

## References

- **Architecture Design:** `docs/architecture/epic-3-orchestration-design.md`
- **Framework Selection:** `docs/architecture/epic-3-framework-selection.md`
- **AWS Strands Docs:** https://github.com/awslabs/agents-for-amazon-bedrock-strands
- **Story 3.0.8:** `docs/stories/3-0-8-agentic-framework-architecture-spike.md`

---

**Created By:** Winston (Architect) + Amelia (Developer)
**Date:** 2025-11-07
**Status:** ✅ COMPLETE
**Next Step:** Story 3.1 implementation (Orchestrator setup using Pattern 1 + Pattern 4)
