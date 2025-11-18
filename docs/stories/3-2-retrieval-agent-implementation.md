# Story 3.2: Retrieval Agent Implementation

Status: review

## Story

As a system,
I want specialized retrieval agent that can search financial knowledge base,
so that agentic workflows can access document information as a tool.

## Acceptance Criteria

1. **AC1:** Retrieval agent defined with tool interface per AWS Strands agentic framework
   - Agent decorated with `@tool` decorator from AWS Strands
   - Agent signature follows Strands tool conventions
   - Agent registered with orchestrator as callable tool

2. **AC2:** Agent accepts query and returns relevant document chunks with citations
   - Input: Natural language query string, optional top_k parameter
   - Output: JSON-serialized list of DocumentChunk objects with metadata
   - Citations include page numbers, document IDs, scores, section types

3. **AC3:** Agent integrates with existing retrieval logic from Epic 1-2
   - Wraps `multi_index_search()` from `raglite.retrieval.multi_index_search`
   - Leverages existing query classification logic (simple/table/analytical)
   - Reuses Epic 2 multi-index architecture (Qdrant + PostgreSQL)
   - No code duplication—direct function calls to existing modules

4. **AC4:** Agent tested in isolation (unit test)
   - Unit test validates agent interface and return format
   - Mocked multi_index_search() prevents external dependencies
   - Test execution time <100ms (framework overhead only)
   - Test validates JSON serialization of results

5. **AC5:** Agent tested within simple workflow (integration test)
   - Integration test executes Retrieval → Synthesis 2-agent workflow
   - Test uses real Qdrant instance (requires `docker-compose up`)
   - Test validates agent coordination via AWS Strands orchestrator
   - Test execution time <5s (includes real search latency)

## Tasks / Subtasks

- [x] **Task 1:** Implement retrieval_agent function with @tool decorator (AC1, AC2) - 3 hours ✅
  - [x] 1.1: Create `raglite/agentic/agents/retrieval_agent.py` file
  - [x] 1.2: Implement `@tool async def retrieval_agent(query, top_k)` with AWS Strands decorator
  - [x] 1.3: Import and call `multi_index_search()` from Epic 2
  - [x] 1.4: Format search results as JSON-serializable DocumentChunk list
  - [x] 1.5: Add error handling for search failures (return empty results with error metadata)

- [x] **Task 2:** Integrate with existing multi-index search (AC3) - 2 hours ✅
  - [x] 2.1: Import `multi_index_search` from `raglite.retrieval.multi_index_search`
  - [x] 2.2: Pass query and top_k parameters to multi_index_search()
  - [x] 2.3: Validate integration preserves Epic 2 query classification (simple/table/analytical)
  - [x] 2.4: Confirm no code duplication—direct function calls only
  - [x] 2.5: Test with sample queries to verify 90%+ retrieval accuracy maintained

- [x] **Task 3:** Create unit tests for retrieval agent (AC4) - 2 hours ✅
  - [x] 3.1: Create `tests/unit/agentic/test_retrieval_agent.py`
  - [x] 3.2: Mock `multi_index_search()` to return synthetic results
  - [x] 3.3: Test agent input validation (query string, top_k integer)
  - [x] 3.4: Test agent output format (JSON-serialized DocumentChunk list)
  - [x] 3.5: Test error handling (search failure returns empty results)
  - [x] 3.6: Validate test execution time <100ms (no real LLM/DB calls)

- [x] **Task 4:** Create integration test for simple workflow (AC5) - 3 hours ✅
  - [x] 4.1: Create `tests/integration/test_retrieval_synthesis_workflow.py`
  - [x] 4.2: Implement 2-agent workflow test: Retrieval → Synthesis
  - [x] 4.3: Use real Qdrant instance (requires `docker-compose up -d`)
  - [x] 4.4: Use MockSynthesisAgent from Story 3.1 (no real synthesis needed yet)
  - [x] 4.5: Test agent coordination via AWS Strands orchestrator
  - [x] 4.6: Validate workflow execution time <5s
  - [x] 4.7: Validate retrieval results passed correctly to synthesis agent

- [x] **Task 5:** Update orchestrator configuration (AC1) - 1 hour ✅
  - [x] 5.1: Add retrieval_agent to orchestrator tools list in `raglite/agentic/orchestrator.py`
  - [x] 5.2: Update orchestrator system prompt to include retrieval_agent usage
  - [x] 5.3: Test orchestrator can discover and call retrieval_agent
  - [x] 5.4: Validate orchestrator logs show retrieval_agent execution

- [x] **Task 6:** Document agent usage and integration (AC1) - 1 hour ✅
  - [x] 6.1: Update `docs/architecture/3-1-agentic-workflow-guide.md` with retrieval_agent example
  - [x] 6.2: Document retrieval_agent signature and return format
  - [x] 6.3: Add code example showing orchestrator calling retrieval_agent
  - [x] 6.4: Document integration with Epic 2 multi-index search

## Dev Notes

### Architecture Context

This story implements the first production agent for Epic 3's agentic orchestration system. The Retrieval Agent exposes Epic 1-2's high-accuracy retrieval capabilities (90%+ accuracy from Epic 2 validation) as a tool callable by the AWS Strands orchestrator.

**Framework Context:** AWS Strands v1.15.0 event-driven orchestration (from Story 3.1)
- Uses `@tool` decorator pattern for agent definitions
- Agents are async functions that return JSON-serializable output
- Orchestrator (Mistral Small) coordinates agent execution
- Built-in OpenTelemetry observability

**Integration Strategy:** Wrapper pattern (no code duplication)
- Directly calls `multi_index_search()` from `raglite.retrieval.multi_index_search`
- Preserves Epic 2 query classification logic (simple/table/analytical routing)
- Reuses Qdrant + PostgreSQL connections from shared clients
- Returns existing DocumentChunk Pydantic models (JSON-serialized for Strands)

**Why Wrapper Pattern:**
- Epic 2 multi-index search is battle-tested (90% accuracy validated)
- Avoid code duplication and maintenance burden
- Preserve existing performance characteristics (<3s p50, <8s p95)
- Enable future enhancements in one place (multi_index_search module)

### Project Structure Notes

**New File:**
```
raglite/agentic/agents/retrieval_agent.py  (~50 lines)
```

**File Structure:**
```python
# raglite/agentic/agents/retrieval_agent.py

from strands import tool
from raglite.retrieval.multi_index_search import multi_index_search
from raglite.shared.logging import logger
import json

@tool
async def retrieval_agent(query: str, top_k: int = 5) -> str:
    """Retrieval Agent: Search financial document knowledge base.

    Args:
        query: Natural language search query
        top_k: Number of document chunks to retrieve (default: 5)

    Returns:
        JSON string containing:
        - chunks: List of DocumentChunk dicts (content, score, page, doc_id)
        - query: Original query for context
        - total_retrieved: Number of chunks returned
        - search_metadata: Query classification and backend used

    Error Handling:
        If search fails, returns empty results with error metadata
    """
    # Implementation here
```

**Existing Modules (No Changes):**
- `raglite/retrieval/multi_index_search.py` - Called directly (no wrapper modifications)
- `raglite/agentic/orchestrator.py` - Updated to include retrieval_agent in tools list
- `raglite/agentic/state.py` - AgentState model already supports agent results

**Testing:**
- Unit tests: `tests/unit/agentic/test_retrieval_agent.py` (~5 tests)
- Integration tests: `tests/integration/test_retrieval_synthesis_workflow.py` (~3 tests)
- Total new tests: 8 tests (expect +8 in CI test count)

### Learnings from Previous Story

**From Story 3-1: Agentic Framework Integration** (Status: done)

**Framework Infrastructure:**
- ✅ AWS Strands v1.15.0 installed and configured
- ✅ Orchestrator with event-driven pattern functional (`raglite/agentic/orchestrator.py`)
- ✅ AgentState model with validation ready (`raglite/agentic/state.py`)
- ✅ Error handler with timeout + graceful degradation operational (`raglite/agentic/error_handler.py`)
- ✅ Mock agents available as templates (MockRetrievalAgent, MockSynthesisAgent)

**Key Services/Interfaces Created:**
- **Orchestrator** (`raglite/agentic/orchestrator.py`):
  - Uses Mistral Small for agent coordination
  - Accepts tools list for agent registration
  - System prompt directs agent execution order
  - Logs all agent executions with structured metadata

- **AgentState Model** (`raglite/agentic/state.py`):
  - Captures agent execution results
  - Validates required fields (query, agent_type, success, result)
  - Supports state propagation between agents

- **Error Handler** (`raglite/agentic/error_handler.py`):
  - 15s max timeout per agent (NFR26)
  - Graceful degradation to Epic 2 simple search on failures (NFR24)
  - Structured error logging with agent metadata

**Architectural Decisions from Story 3-1:**
- Event-driven agents-as-tools pattern (not imperative orchestration)
- Mistral Small for orchestration (tunable to Claude 3.7 Sonnet)
- OpenTelemetry observability deferred to Story 3.5 (optional for MVP)

**Testing Infrastructure:**
- 53 tests passing (97.1% pass rate)
- Mock agents prevent LLM API costs in tests
- Integration tests validate agent coordination
- Orchestrator tested with 2-agent workflows

**Implementation Guidance for Story 3.2:**
- ✅ Use `@tool` decorator pattern (established in Story 3.1)
- ✅ Return JSON-serialized output (Strands requirement)
- ✅ Add agent to orchestrator tools list in `orchestrator.py`
- ✅ Follow error handling patterns from `error_handler.py`
- ✅ Use MockSynthesisAgent for integration tests (no real synthesis needed yet)
- ✅ Add structured logging with `logger.info("Retrieval agent called", extra={...})`

**Files to Reference:**
- `raglite/agentic/agents/mock_retrieval.py` - Template for retrieval_agent structure
- `raglite/agentic/orchestrator.py` - How to register agents with orchestrator
- `tests/unit/agentic/test_mock_agents.py` - Testing patterns for agent validation
- `tests/integration/test_agentic_framework.py` - Orchestrator coordination test examples

[Source: stories/3-1-agentic-framework-integration.md]

### Performance Constraints (NFRs)

**NFR5: Query Response Time**
- Target: <30s p95 for analytical workflows (entire multi-agent pipeline)
- Retrieval agent budget: <3s p50, <8s p95 (from Tech Spec)
- Orchestration overhead: 3-5s (validated in Story 3.1 POC)

**Measurement:**
- Log execution time per agent call via `AgentState.execution_time_ms`
- Integration tests assert workflow execution time <5s
- Performance tests (Story 3.8) will measure p50/p95 across query types

**NFR24: Graceful Degradation**
- If retrieval_agent fails → Return empty results with error metadata
- If timeout (>15s per NFR26) → Cancel agent, return partial results
- If Qdrant unreachable → Fallback to PostgreSQL SQL search only
- User always receives a response (no hard failures)

**NFR26: Agent Timeout**
- Individual agent timeout: 15s max (enforced by error_handler.py)
- Retrieval agent expected to complete in <3s p50, <8s p95
- Timeout enforcement prevents hanging workflows

**NFR7: Source Attribution Accuracy**
- Retrieval agent must preserve page numbers, document IDs, section types
- 95%+ attribution accuracy target (inherited from Epic 1)
- Citations validated in integration tests

### Testing Strategy

**Unit Tests (5 tests, <2s total execution):**

1. **Test Agent Interface** (`test_retrieval_agent_interface`)
   - Validate `@tool` decorator applied
   - Validate async function signature (query, top_k)
   - Validate return type is JSON string

2. **Test Return Format** (`test_retrieval_agent_return_format`)
   - Mock `multi_index_search()` to return synthetic chunks
   - Validate JSON-serialized output contains: chunks, query, total_retrieved, search_metadata
   - Validate DocumentChunk dict structure (content, score, page, doc_id, section_type)

3. **Test Multi-Index Integration** (`test_retrieval_agent_multi_index_integration`)
   - Mock `multi_index_search()` and assert called with correct parameters
   - Validate query classification preserved (simple/table/analytical)
   - Validate top_k parameter passed through

4. **Test Error Handling** (`test_retrieval_agent_error_handling`)
   - Mock `multi_index_search()` to raise exception
   - Validate agent returns empty results with error metadata
   - Validate error logged with structured metadata

5. **Test JSON Serialization** (`test_retrieval_agent_json_serialization`)
   - Validate Pydantic DocumentChunk models serialize to JSON
   - Validate special characters (quotes, newlines) handled correctly
   - Validate large chunks (>2000 chars) serialize without truncation

**Integration Tests (3 tests, ~5s total execution):**

1. **Test Simple Workflow: Retrieval → Synthesis** (`test_retrieval_synthesis_workflow`)
   - Use real Qdrant instance (requires `docker-compose up`)
   - Use MockSynthesisAgent from Story 3.1 (no real synthesis)
   - Validate retrieval results passed correctly to synthesis agent
   - Validate workflow execution time <5s
   - Validate orchestrator logs show agent coordination

2. **Test Retrieval Agent Coordination** (`test_retrieval_agent_coordination_via_orchestrator`)
   - Orchestrator calls retrieval_agent via Strands framework
   - Validate agent execution state captured in AgentState
   - Validate agent result includes execution_time_ms, success=true

3. **Test Error Recovery** (`test_retrieval_agent_error_recovery`)
   - Simulate Qdrant connection failure
   - Validate orchestrator receives error metadata
   - Validate workflow continues (no crash)
   - Validate error logged with agent_type, task_id, error reason

**Test Data:**
- Use Epic 1-2 ground truth documents (real PDFs in `tests/fixtures/`)
- Reuse Qdrant fixture from `tests/conftest.py` (initialized with sample docs)
- Use sample queries from `tests/fixtures/ground_truth.json`

**Mocking Strategy:**
- Unit tests: Mock `multi_index_search()` to avoid Qdrant dependency
- Integration tests: Real Qdrant, real multi_index_search, MockSynthesisAgent
- No real LLM API calls in Story 3.2 tests (synthesis mocked)

### References

- **Epic 3 PRD:** `docs/prd/epic-3-ai-intelligence-orchestration.md#story-3.2` ⭐ CRITICAL
- **Tech Spec:** `docs/tech-spec-epic-3.md#agent-1-retrieval-agent` ⭐ CRITICAL
- **Orchestration Design:** `docs/architecture/epic-3-orchestration-design.md#agent-1-retrieval-agent` ⭐ CRITICAL
- **Agent Patterns:** `docs/architecture/epic-3-agent-patterns.md#pattern-1-sequential-chain` ⭐ CRITICAL (Code examples)
- **Workflow Guide:** `docs/architecture/3-1-agentic-workflow-guide.md` (Story 3.1 reference)
- **Previous Story:** `docs/stories/3-1-agentic-framework-integration.md` (Framework setup)
- **Multi-Index Search:** `raglite/retrieval/multi_index_search.py` (Integration point)
- **AWS Strands @tool Decorator:** https://github.com/awslabs/agents-for-amazon-bedrock-strands/blob/main/README.md#tools

## Dev Agent Record

### Context Reference

- `docs/stories/3-2-retrieval-agent-implementation.context.xml` (Generated: 2025-11-09)

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- **2025-11-09 15:30:** All 6 tasks completed successfully
  - Retrieval_agent implemented with @tool decorator wrapping Epic 2 multi_index_search
  - 16 comprehensive unit tests (100% passing: AC1 interface, AC2 return format, AC3 integration, AC4 error handling)
  - 11 integration test scenarios for AC5 validation (2-agent workflow with real Qdrant)
  - Orchestrator updated with tool registration mechanism (_load_default_tools, get_available_tools, register_tools)
  - Documentation updated in agentic workflow guide with retrieval_agent examples
  - Total test coverage: 59 unit tests + 11 integration tests
  - Performance: Unit tests <100ms ✅, framework overhead validated

### File List

**Created:**
- `raglite/agentic/agents/retrieval_agent.py` (159 lines) - @tool decorated agent wrapping multi_index_search
- `tests/unit/agentic/test_retrieval_agent.py` (502 lines) - 16 unit tests covering AC1-AC4
- `tests/integration/test_retrieval_synthesis_workflow.py` (341 lines) - 11 integration tests for AC5

**Modified:**
- `raglite/agentic/orchestrator.py` - Added tool registration (lines 27-35, 59-112, 119)
- `docs/architecture/3-1-agentic-workflow-guide.md` - Added retrieval_agent documentation and examples (lines 146-193, 399-427)
- `docs/sprint-status.yaml` - Updated story status: ready-for-dev → in-progress → review

**Test Results:**
- Unit tests: 16/16 passing (100%)
- Agentic framework tests: 59/59 passing (100%, including existing Story 3.1 tests)
- Total new tests: 27 (16 unit + 11 integration)
