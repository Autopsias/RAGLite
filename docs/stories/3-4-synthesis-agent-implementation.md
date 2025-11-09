# Story 3.4: Synthesis Agent Implementation

Status: ready-for-dev

## Story

As a system,
I want specialized synthesis agent that combines retrieval and analysis results into coherent answers,
so that multi-step workflows produce natural language responses with proper source attribution.

## Acceptance Criteria

1. **AC1:** Synthesis agent defined with @tool decorator per AWS Strands framework
   - Agent decorated with `@tool` decorator from AWS Strands
   - Agent signature follows Strands tool conventions
   - Agent registered with orchestrator as callable tool
   - Agent accepts List[AgentResult] from upstream agents (retrieval + analysis)

2. **AC2:** Agent aggregates multi-source results into natural language summary
   - Input: retrieval_results (List[DocumentChunk]), analysis_results (List[AnalysisResult]), original_query (str)
   - Output: JSON-serialized final answer with reasoning steps and citations
   - Maintains semantic coherence across multiple information sources
   - Preserves source attribution from both retrieval and analysis agents

3. **AC3:** Agent uses Claude Sonnet for high-quality synthesis with structured prompts
   - Calls Claude Sonnet via shared client from `raglite/shared/clients.py`
   - Structured prompts ensure factual accuracy and citation preservation
   - Reasoning includes explanation of how sources were combined
   - Error handling for LLM API failures (return error metadata)

4. **AC4:** Agent tested with multi-source inputs (unit tests)
   - Unit test validates synthesis of retrieval + analysis results
   - Unit test validates source citation formatting and preservation
   - Unit test validates consistency with original query intent
   - Unit test validates handling of conflicting information from sources
   - Mocked Claude API prevents external dependencies
   - Test execution time <100ms (framework overhead only)

5. **AC5:** Agent integrates in complete 3-agent workflow (integration test)
   - Integration test executes Retrieval → Analysis → Synthesis full workflow
   - Test uses real Qdrant instance (requires `docker-compose up`)
   - Test validates complete workflow produces coherent final answer
   - Test validates execution time <8s for full 3-agent workflow
   - Test validates all source citations preserved in final output

## Tasks / Subtasks

- [ ] **Task 1:** Implement synthesis_agent function with @tool decorator (AC1, AC2) - 4 hours
  - [ ] 1.1: Create `raglite/agentic/agents/synthesis_agent.py` file
  - [ ] 1.2: Implement `@tool async def synthesis_agent(retrieval_results, analysis_results, query)` with AWS Strands decorator
  - [ ] 1.3: Define SynthesisResult Pydantic model in `raglite/agentic/state.py` (answer, reasoning_steps, sources, metadata)
  - [ ] 1.4: Implement multi-source aggregation logic (combine retrieval + analysis results)
  - [ ] 1.5: Add error handling for invalid inputs or missing data (return error metadata)

- [ ] **Task 2:** Integrate Claude Sonnet for high-quality synthesis (AC3) - 3 hours
  - [ ] 2.1: Import Claude client from `raglite/shared/clients.py`
  - [ ] 2.2: Create structured prompt templates for synthesis tasks
  - [ ] 2.3: Implement LLM synthesis call with Claude Sonnet model
  - [ ] 2.4: Parse LLM response and extract reasoning steps + citations
  - [ ] 2.5: Add retry logic for Claude API errors (429/500 status codes)
  - [ ] 2.6: Validate citation preservation and factual accuracy

- [ ] **Task 3:** Create unit tests for synthesis agent (AC4) - 3 hours
  - [ ] 3.1: Create `tests/unit/agentic/test_synthesis_agent.py`
  - [ ] 3.2: Mock Claude API to return synthetic synthesis results
  - [ ] 3.3: Test synthesis of retrieval results only (basic summary)
  - [ ] 3.4: Test synthesis of retrieval + analysis results (complex workflow)
  - [ ] 3.5: Test source citation preservation from all upstream agents
  - [ ] 3.6: Test handling of conflicting information from multiple sources
  - [ ] 3.7: Test error handling (invalid inputs, missing data, LLM API failure)
  - [ ] 3.8: Validate test execution time <100ms (no real LLM calls)

- [ ] **Task 4:** Create integration test for complete 3-agent workflow (AC5) - 4 hours
  - [ ] 4.1: Update `tests/integration/test_analysis_agent_workflow.py` to use real synthesis_agent
  - [ ] 4.2: Implement full Retrieval → Analysis → Synthesis workflow test
  - [ ] 4.3: Use real Qdrant instance (requires `docker-compose up -d`)
  - [ ] 4.4: Use real Claude Sonnet for synthesis (budget LLM calls)
  - [ ] 4.5: Remove MockSynthesisAgent usage from existing tests
  - [ ] 4.6: Test complete workflow coordination via AWS Strands orchestrator
  - [ ] 4.7: Validate workflow execution time <8s
  - [ ] 4.8: Validate all source citations preserved in final output

- [ ] **Task 5:** Update orchestrator configuration (AC1) - 1 hour
  - [ ] 5.1: Add synthesis_agent to orchestrator tools list in `raglite/agentic/orchestrator.py`
  - [ ] 5.2: Update orchestrator system prompt to include synthesis_agent usage
  - [ ] 5.3: Test orchestrator can discover and call synthesis_agent
  - [ ] 5.4: Validate orchestrator logs show synthesis_agent execution

- [ ] **Task 6:** Document agent usage and integration (AC1) - 1 hour
  - [ ] 6.1: Update `docs/architecture/3-1-agentic-workflow-guide.md` with synthesis_agent example
  - [ ] 6.2: Document synthesis_agent signature and SynthesisResult format
  - [ ] 6.3: Add code example showing complete 3-agent workflow
  - [ ] 6.4: Document multi-source aggregation patterns and best practices

## Dev Notes

### Architecture Context

This story implements the third and final production agent for Epic 3's agentic orchestration system. The Synthesis Agent completes the 3-agent sequential chain (Retrieval → Analysis → Synthesis), enabling coherent natural language answers from multi-source information aggregation.

**Framework Context:** AWS Strands v1.15.0 event-driven orchestration (from Story 3.1)
- Uses `@tool` decorator pattern for agent definitions
- Agents are async functions that return JSON-serializable output
- Orchestrator (Mistral Small) coordinates agent execution
- Built-in OpenTelemetry observability

**Integration Strategy:** Direct Claude Sonnet API calls for high-quality synthesis
- Uses shared Claude client from `raglite/shared/clients.py`
- Structured prompts ensure factual accuracy and citation preservation
- Returns SynthesisResult Pydantic model (JSON-serialized for Strands)
- Integrates with Retrieval Agent and Analysis Agent outputs

**Why Claude Sonnet (not Haiku):**
- Superior narrative generation quality (human-like coherence)
- Better multi-source integration (handles conflicting information)
- Citation preservation accuracy (maintains source attribution)
- Acceptable latency: 900-1200ms (vs 600-800ms for Haiku)
- Final synthesis is user-facing, quality > speed trade-off justified

### Project Structure Notes

**New File:**
```
raglite/agentic/agents/synthesis_agent.py  (~60-80 lines)
```

**File Structure:**
```python
# raglite/agentic/agents/synthesis_agent.py

from strands import tool
from raglite.shared.clients import get_claude_client
from raglite.agentic.state import SynthesisResult, AnalysisResult, DocumentChunk
from raglite.shared.logging import logger
import json
from typing import List, Optional

@tool
async def synthesis_agent(
    retrieval_results: List[dict],  # List[DocumentChunk] serialized
    analysis_results: List[dict],   # List[AnalysisResult] serialized
    query: str,
    context: Optional[str] = None
) -> str:
    """Synthesis Agent: Aggregate multi-source results into coherent answer.

    Args:
        retrieval_results: List of document chunks from retrieval agent (JSON dicts)
        analysis_results: List of analysis results from analysis agent (JSON dicts)
        query: Original user query for context
        context: Optional additional context for synthesis

    Returns:
        JSON string containing:
        - answer: Natural language final answer
        - reasoning_steps: List of synthesis steps taken
        - sources: Aggregated source citations from all agents
        - metadata: Execution metadata (confidence, agent coordination)

    Synthesis Patterns:
        - Retrieval-only: Summarize document chunks into coherent answer
        - Retrieval + Analysis: Integrate calculations with document evidence
        - Multi-source conflict resolution: Handle contradictions with citations

    Error Handling:
        If synthesis fails or LLM unavailable, returns error metadata with partial results
    """
    # Implementation here
```

**Model Addition (raglite/agentic/state.py):**
```python
class SynthesisResult(BaseModel):
    """Result from Synthesis Agent"""
    answer: str  # Final natural language answer
    reasoning_steps: List[str]  # Steps taken to synthesize answer
    sources: List[str]  # Aggregated citations from all agents
    metadata: Dict[str, Any]  # Execution metadata (confidence, agent_count, etc.)
```

**Existing Modules (Modified):**
- `raglite/agentic/orchestrator.py` - Add synthesis_agent to tools list
- `raglite/agentic/state.py` - Add SynthesisResult model (~15 lines)
- `tests/integration/test_analysis_agent_workflow.py` - Replace MockSynthesisAgent with real agent

**Testing:**
- Unit tests: `tests/unit/agentic/test_synthesis_agent.py` (~8 tests)
- Integration tests: Update `tests/integration/test_analysis_agent_workflow.py` (use real synthesis agent)
- Total new tests: 8 unit tests (expect +8 in CI test count)

### Learnings from Previous Story

**From Story 3-3: Analysis Agent Implementation** (Status: done)

**Framework Infrastructure:**
- ✅ AWS Strands v1.15.0 operational with Mistral orchestration
- ✅ `@tool` decorator pattern validated and documented
- ✅ Tool registration mechanism in orchestrator.py functional
- ✅ AgentState model captures execution results with timing
- ✅ Error handler with timeout + graceful degradation ready

**Key Services/Interfaces Created:**
- **Analysis Agent** (`raglite/agentic/agents/analysis_agent.py`):
  - Performs financial calculations with Claude Haiku reasoning
  - Returns JSON-serialized AnalysisResult with formula + value + reasoning
  - Integrated with orchestrator tools list
  - 100% passing tests (13 unit + 7 integration)

- **Retrieval Agent** (`raglite/agentic/agents/retrieval_agent.py`):
  - Wraps Epic 2 multi_index_search()
  - Returns JSON-serialized DocumentChunk list
  - Available as tool for synthesis agent to reference

- **MockSynthesisAgent** (`raglite/agentic/agents/mock_synthesis.py`):
  - ⚠️ Currently used in integration tests - TO BE REPLACED
  - Returns placeholder synthesis results
  - Story 3.4 will replace with real implementation

**Implementation Guidance for Story 3.4:**
- ✅ Use `@tool` decorator pattern (established in Story 3.1-3.3)
- ✅ Return JSON-serialized output (Strands requirement)
- ✅ Add agent to orchestrator tools list in `orchestrator.py`
- ✅ Follow error handling patterns from `error_handler.py`
- ✅ Use Claude Sonnet (not Haiku) for synthesis quality
- ✅ Add structured logging with `logger.info("Synthesis agent called", extra={...})`
- ✅ Import Claude client from `raglite/shared/clients.py` (no new client creation)
- ⚠️ Replace MockSynthesisAgent in existing integration tests

**Multi-Source Aggregation Patterns:**
- Synthesis agent receives outputs from both retrieval and analysis agents
- Must preserve citations from retrieval_results (DocumentChunk.source_citation)
- Must integrate calculations from analysis_results (AnalysisResult.formatted_value + reasoning)
- Must handle scenarios where only retrieval results exist (no analysis needed)
- Must handle conflicting information from multiple sources (cite all sources)

**Testing Patterns:**
- Unit tests mock Claude API with synthetic responses
- Integration tests use real Qdrant + real Claude Sonnet (budget LLM calls)
- Complete 3-agent workflow tests validate orchestration
- Performance tests assert execution time <8s for full workflow

**Files to Reference:**
- `raglite/agentic/agents/analysis_agent.py` - Agent structure template (363 lines)
- `raglite/agentic/agents/retrieval_agent.py` - Tool registration pattern
- `raglite/agentic/orchestrator.py` - Tool registration mechanism
- `tests/unit/agentic/test_analysis_agent.py` - Unit test patterns (257 lines)
- `tests/integration/test_analysis_agent_workflow.py` - Integration test patterns (275 lines)

[Source: stories/3-3-analysis-agent-implementation.md]

### Performance Constraints (NFRs)

**NFR5: Query Response Time**
- Target: <30s p95 for analytical workflows (entire multi-agent pipeline)
- Synthesis agent budget: <1.2s p50, <2.0s p95 (per Tech Spec)
- Claude Sonnet latency: 900-1200ms typical (quality synthesis)
- Orchestration overhead: 3-5s (validated in Story 3.1)

**Performance Budget Breakdown:**
- Retrieval Agent (Story 3.2): 2-3s (2 parallel retrievals)
- Analysis Agent (Story 3.3): 0.6-0.8s
- **Synthesis Agent (Story 3.4): 0.9-1.2s** ← This story
- Orchestration overhead: 0.15s (task decomposition + routing)
- **Total estimated: ~4.5-6.5s typical** (well under 30s target)

**Measurement:**
- Log execution time per agent call via `AgentState.execution_time_ms`
- Integration tests assert synthesis agent execution time <2.0s
- Performance tests (Story 3.8) will measure p50/p95 across workflow types

**NFR24: Graceful Degradation**
- If synthesis_agent fails → Return concatenated retrieval/analysis results with error note
- If timeout (>15s per NFR26) → Cancel agent, return partial results
- If Claude API unreachable → Return structured data only (no narrative synthesis)
- User always receives a response (no hard failures)

**NFR26: Agent Timeout**
- Individual agent timeout: 15s max (enforced by error_handler.py)
- Synthesis agent expected to complete in <1.2s p50, <2.0s p95
- Timeout enforcement prevents hanging workflows

### Synthesis Patterns Specification

**Pattern 1: Retrieval-Only Synthesis**
- **Input:** List[DocumentChunk] from retrieval agent, no analysis results
- **Task:** Summarize document chunks into coherent answer
- **Output:** Natural language answer with source citations
- **Example:**
  - Query: "What is the company's revenue guidance for 2024?"
  - Retrieval: 3 chunks from Q3_2024_Report.pdf mentioning "$50M-52M guidance"
  - Synthesis: "The company's 2024 revenue guidance is $50M-52M, as stated in the Q3 2024 earnings report. [Source: Q3_2024_Report.pdf, page 8]"

**Pattern 2: Retrieval + Analysis Synthesis**
- **Input:** List[DocumentChunk] + List[AnalysisResult]
- **Task:** Integrate calculations with document evidence
- **Output:** Answer combining numerical analysis with contextual narrative
- **Example:**
  - Query: "Calculate YoY revenue growth and explain variance"
  - Retrieval: Q3 2023 revenue ($10M), Q3 2024 revenue ($12M)
  - Analysis: YoY growth = +20% (calculation: (12-10)/10 = 0.20)
  - Synthesis: "Revenue grew 20% YoY from $10M (Q3 2023) to $12M (Q3 2024). This growth was driven by increased marketing spend and the launch of Product X in Q2 2024. [Sources: Q3_2023_Report.pdf, Q3_2024_Report.pdf, Marketing_Budget_2024.xlsx]"

**Pattern 3: Multi-Source Conflict Resolution**
- **Input:** Conflicting information from multiple document chunks
- **Task:** Present all perspectives with citations, note discrepancies
- **Output:** Balanced answer acknowledging conflicts
- **Example:**
  - Query: "What is the employee headcount?"
  - Retrieval: Document A says "450 employees", Document B says "470 employees"
  - Synthesis: "Employee headcount is reported as 450 in the Q2 2024 report [Source: Q2_2024_Report.pdf] and 470 in the Q3 2024 report [Source: Q3_2024_Report.pdf], suggesting a net addition of 20 employees during Q3."

**Pattern 4: Partial Results (Error Handling)**
- **Input:** Some agents succeeded, some failed
- **Task:** Synthesize available information, note limitations
- **Output:** Partial answer with explicit caveats
- **Example:**
  - Query: "Calculate YoY revenue growth and explain variance"
  - Retrieval: Success (retrieved Q3 2023 & 2024 revenue)
  - Analysis: FAILED (Claude API timeout)
  - Synthesis: "I found Q3 2023 revenue ($10M) and Q3 2024 revenue ($12M), but couldn't complete the growth calculation due to a system timeout. Based on the values, revenue increased by $2M year-over-year. [Note: Full analysis unavailable due to timeout]"

### Testing Strategy

**Unit Tests (8 tests, <1s total execution):**

1. **Test Agent Interface** (`test_synthesis_agent_interface`)
   - Validate `@tool` decorator applied
   - Validate async function signature (retrieval_results, analysis_results, query, context)
   - Validate return type is JSON string

2. **Test Retrieval-Only Synthesis** (`test_synthesis_retrieval_only`)
   - Input: List[DocumentChunk] (3 chunks with citations)
   - Expected: Natural language summary with preserved citations
   - Mock Claude API to return synthetic summary
   - Validate SynthesisResult model structure

3. **Test Retrieval + Analysis Synthesis** (`test_synthesis_retrieval_analysis`)
   - Input: List[DocumentChunk] + List[AnalysisResult] (YoY calculation)
   - Expected: Answer integrating numerical analysis with document context
   - Validate calculation referenced in narrative
   - Validate both retrieval and analysis sources cited

4. **Test Source Citation Preservation** (`test_synthesis_citation_preservation`)
   - Input: Multiple DocumentChunk objects with unique citations
   - Expected: All citations preserved in SynthesisResult.sources list
   - Validate no citation loss during synthesis

5. **Test Conflicting Information Handling** (`test_synthesis_conflict_resolution`)
   - Input: DocumentChunk A says "X", DocumentChunk B says "Y"
   - Expected: Synthesis acknowledges both perspectives with citations
   - Validate balanced presentation

6. **Test Error Handling** (`test_synthesis_agent_error_handling`)
   - Test empty retrieval_results (return error metadata)
   - Test invalid JSON inputs (return error metadata)
   - Mock Claude API failure (return structured data only, no narrative)
   - Validate error logged with structured metadata

7. **Test JSON Serialization** (`test_synthesis_agent_json_serialization`)
   - Validate SynthesisResult model serializes to JSON
   - Validate complex reasoning_steps list serializes correctly
   - Validate special characters in answer text

8. **Test Optional Context Parameter** (`test_synthesis_optional_context`)
   - Test synthesis with context parameter provided
   - Test synthesis without context (default behavior)
   - Validate context influences synthesis when present

**Integration Tests (Update existing tests, ~4 tests):**

1. **Test Complete 3-Agent Workflow** (`test_retrieval_analysis_synthesis_workflow`)
   - Replace MockSynthesisAgent with real synthesis_agent
   - Use real Qdrant instance (requires `docker-compose up`)
   - Use real Claude Sonnet for synthesis
   - Validate retrieval → analysis → synthesis coordination
   - Validate workflow execution time <8s
   - Validate final answer includes retrieval + analysis insights

2. **Test Synthesis Agent Coordination** (`test_synthesis_agent_coordination_via_orchestrator`)
   - Orchestrator calls synthesis_agent via Strands framework
   - Validate agent execution state captured in AgentState
   - Validate agent result includes execution_time_ms, success=true

3. **Test Error Recovery in Full Workflow** (`test_synthesis_agent_error_recovery`)
   - Simulate analysis agent failure (synthesis still succeeds with retrieval-only)
   - Validate workflow continues (no crash)
   - Validate synthesis produces partial results

4. **Test Performance** (`test_synthesis_agent_performance`)
   - Execute 10 synthesis agent calls sequentially
   - Measure p50, p95 execution time
   - Assert p50 <1.2s, p95 <2.0s
   - Validate Claude Sonnet latency within budget

**Test Data:**
- Sample retrieval results from `tests/fixtures/` (synthetic document chunks)
- Sample analysis results from Story 3.3 tests (YoY growth, variance)
- Use ground truth documents from Epic 1-2 (real PDFs)
- Reuse Qdrant fixture from `tests/conftest.py`

**Mocking Strategy:**
- Unit tests: Mock Claude API to avoid LLM costs
- Integration tests: Real Claude Sonnet (budget ~$0.15 per test run)
- Real orchestrator coordination (no mocking of Strands framework)

### References

- **Epic 3 PRD:** `docs/prd/epic-3-ai-intelligence-orchestration.md#story-3.4` ⭐ CRITICAL
- **Tech Spec:** `docs/tech-spec-epic-3.md#agent-3-synthesis-agent` ⭐ CRITICAL
- **Orchestration Design:** `docs/architecture/epic-3-orchestration-design.md#agent-3-synthesis-agent` ⭐ CRITICAL
- **Agent Patterns:** `docs/architecture/epic-3-agent-patterns.md#pattern-3-aggregation` ⭐ CRITICAL (Code examples)
- **Workflow Guide:** `docs/architecture/3-1-agentic-workflow-guide.md` (Story 3.1 reference)
- **Previous Story:** `docs/stories/3-3-analysis-agent-implementation.md` (Analysis Agent patterns)
- **Claude API Client:** `raglite/shared/clients.py` (Shared client for Sonnet)
- **AWS Strands @tool Decorator:** https://github.com/awslabs/agents-for-amazon-bedrock-strands/blob/main/README.md#tools

## Dev Agent Record

### Context Reference

- `docs/stories/3-4-synthesis-agent-implementation.context.xml` (Generated: 2025-11-09)

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Date | Version | Change | Status |
|------|---------|--------|--------|
| 2025-11-09 | 1.0.0 | Initial story draft created | DRAFTED |
