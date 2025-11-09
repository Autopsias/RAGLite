# Agentic Workflow Development Guide

**Story:** 3.1 - Agentic Framework Integration
**Status:** AC7 Documentation Complete
**Date:** 2025-11-09

## Overview

This guide demonstrates how to develop, test, and debug workflows using RAGLite's AWS Strands-based agentic orchestration framework.

## Quick Start: Basic 2-Agent Workflow

### Minimal Example

```python
from raglite.agentic.orchestrator import StrandsOrchestrator
from raglite.agentic.agents.mock_retrieval import MockRetrievalAgent
from raglite.agentic.agents.mock_synthesis import MockSynthesisAgent
from raglite.agentic.state import AgentState

async def run_workflow():
    orchestrator = StrandsOrchestrator()
    retrieval = MockRetrievalAgent()
    synthesis = MockSynthesisAgent()

    workflow_steps = [
        {
            "name": "retrieval",
            "agent": None,
            "process_fn": lambda agent, state: retrieval(state),
        },
        {
            "name": "synthesis",
            "agent": None,
            "process_fn": lambda agent, state: synthesis(state),
        },
    ]

    initial_state = AgentState(query="What is your financial outlook?")
    final_state = await orchestrator.execute_workflow(initial_state, workflow_steps)

    return final_state.synthesis_result
```

## Workflow Patterns

### 1. Sequential Chain Pattern

**Use Case:** Simple linear processing (Retrieval → Synthesis)

```python
workflow_steps = [
    {"name": "step1", "agent": None, "process_fn": agent1.process},
    {"name": "step2", "agent": None, "process_fn": agent2.process},
    {"name": "step3", "agent": None, "process_fn": agent3.process},
]

final_state = await orchestrator.execute_workflow(initial_state, workflow_steps)
```

**State Flow:**
- Query → Agent1 transforms state
- Agent1 output → Agent2 input
- Agent2 output → Agent3 input
- Agent3 output = Final result

### 2. Conditional Routing Pattern

**Use Case:** Route to different agents based on query type

```python
async def conditional_router(agent, state: AgentState) -> AgentState:
    """Route to retrieval or synthesis based on query type."""
    if "forecast" in state.query.lower():
        return await forecasting_agent(state)
    else:
        return await retrieval_agent(state)

workflow_steps = [
    {"name": "router", "agent": None, "process_fn": conditional_router},
    {"name": "synthesis", "agent": None, "process_fn": synthesis_agent},
]
```

### 3. Error Handling with Fallback

**Use Case:** Graceful degradation on agent failures (NFR24)

```python
from raglite.agentic.error_handler import WorkflowErrorHandler

handler = WorkflowErrorHandler(fallback_search_func=simple_search)

async def resilient_retrieval(agent, state: AgentState) -> AgentState:
    """Retrieve with fallback."""
    try:
        return await advanced_retrieval(state)
    except Exception as e:
        # Fallback to simpler search
        return await handler.fallback_to_simple_search(
            state, error_reason=str(e)
        )

workflow_steps = [
    {"name": "retrieval", "agent": None, "process_fn": resilient_retrieval},
    {"name": "synthesis", "agent": None, "process_fn": synthesis_agent},
]
```

## Agent Creation Guide

### Creating a Custom Agent

```python
from raglite.agentic.state import AgentState

class MyCustomAgent:
    """Custom agent for specific task."""

    def __init__(self, name: str):
        self.name = name

    async def __call__(self, state: AgentState) -> AgentState:
        """Process state and return updated state.

        Args:
            state: Current workflow state

        Returns:
            Updated state with agent results
        """
        # Perform processing
        result = self.process(state.query)

        # Update state with results
        state.synthesis_result = result
        state.add_metadata("agent", self.name)

        return state

    def process(self, query: str) -> str:
        """Core processing logic."""
        return f"Processed: {query}"
```

### Using a Strands Agent

```python
from raglite.agentic.orchestrator import StrandsOrchestrator

orchestrator = StrandsOrchestrator()

# Create a Strands agent with tools and system prompt
agent = await orchestrator.create_agent(
    name="AnalysisAgent",
    system_prompt="You are a financial analyst. Analyze the provided data.",
    tools=[],  # Add tool functions here
)

async def analysis_step(_, state: AgentState) -> AgentState:
    """Use Strands agent for analysis."""
    # Agent would process state
    return state
```

## State Management Best Practices

### Validating State Between Agents

```python
async def validated_step(agent, state: AgentState) -> AgentState:
    """Validate state integrity before processing."""

    # Check required fields are present
    is_valid, error = state.validate_required_fields([
        "query",
        "retrieval_results",
    ])

    if not is_valid:
        raise ValueError(f"Invalid state: {error}")

    # Process with confidence
    result = process_chunks(state.retrieval_results)
    state.synthesis_result = result

    return state
```

### Adding Metadata for Debugging

```python
async def instrumented_agent(agent, state: AgentState) -> AgentState:
    """Agent with comprehensive metadata."""
    import time

    start = time.time()

    # Add context metadata
    state.add_metadata("agent_start_time", start)
    state.add_metadata("query_length", len(state.query))

    # Do processing
    state.synthesis_result = "Result"

    # Add timing metadata
    duration = time.time() - start
    state.add_metadata("agent_duration_ms", duration * 1000)

    return state
```

## Debugging Guide

### 1. Logging with Structured Metadata

All agentic workflow components use structured logging:

```python
# Error logging automatically includes:
# - agent_id: Which agent failed
# - error_type: Type of failure (timeout, exception, etc.)
# - failure_reason: Detailed error message
# - timestamp: When error occurred

# Enable debug logging:
import logging
logging.getLogger("raglite.agentic").setLevel(logging.DEBUG)
```

### 2. Accessing Error Logs

```python
from raglite.agentic.error_handler import WorkflowErrorHandler

handler = WorkflowErrorHandler()

# ... run workflow ...

# Inspect errors
error_log = handler.get_error_log()
for error in error_log:
    print(f"Agent: {error['agent_id']}, Type: {error['error_type']}")
    print(f"Details: {error}")
```

### 3. Performance Monitoring

```python
import time
from raglite.agentic.state import AgentState

async def timed_workflow(orchestrator, initial_state):
    """Execute workflow with performance tracking."""
    start = time.time()

    workflow_steps = [
        # ... workflow steps ...
    ]

    final_state = await orchestrator.execute_workflow(
        initial_state, workflow_steps
    )

    duration = time.time() - start
    print(f"Total workflow time: {duration:.2f}s")
    print(f"Per-step breakdown:")

    for key, value in final_state.metadata.items():
        if "duration" in key:
            print(f"  {key}: {value}ms")

    return final_state
```

### 4. Testing Workflows

```python
@pytest.mark.asyncio
async def test_workflow_with_mocks():
    """Test workflow using mock agents."""
    from raglite.agentic.agents.mock_retrieval import MockRetrievalAgent
    from raglite.agentic.agents.mock_synthesis import MockSynthesisAgent

    orchestrator = StrandsOrchestrator()

    workflow_steps = [
        {
            "name": "retrieval",
            "agent": None,
            "process_fn": lambda agent, state: MockRetrievalAgent()(state),
        },
        {
            "name": "synthesis",
            "agent": None,
            "process_fn": lambda agent, state: MockSynthesisAgent()(state),
        },
    ]

    initial_state = AgentState(query="Test query")
    final_state = await orchestrator.execute_workflow(initial_state, workflow_steps)

    assert final_state.retrieval_results is not None
    assert final_state.synthesis_result is not None
```

## Timeout Handling (NFR26)

Per NFR26, individual agents have a 15-second timeout:

```python
# Timeout is automatically enforced
orchestrator = StrandsOrchestrator()
# Agent timeout: 15 seconds (per settings)
```

If an agent exceeds the timeout:
- TimeoutError is raised
- Error is logged with agent ID and timeout duration
- Fallback mechanism (if configured) can handle gracefully

## Graceful Degradation (NFR24)

Configure fallback search for resilience:

```python
from raglite.agentic.error_handler import WorkflowErrorHandler
from raglite.retrieval.multi_index_search import multi_index_search

handler = WorkflowErrorHandler(fallback_search_func=multi_index_search)

async def resilient_workflow():
    """Workflow that falls back to Epic 2 search on failure."""
    try:
        # Execute agentic workflow...
        pass
    except Exception as e:
        # Fall back to simple search
        final_state = await handler.fallback_to_simple_search(
            state, error_reason=str(e)
        )
        return final_state
```

When fallback is triggered:
- State is updated with `used_fallback: true` metadata
- Retrieval results populated from simple search
- Error reason logged for debugging

## Common Issues & Solutions

### Issue: Agent timeout at 15s
**Solution:** Break workflow into smaller, faster steps. Offload heavy processing to earlier pipeline stages.

### Issue: State fields missing between agents
**Solution:** Use `state.validate_required_fields()` to detect missing fields early.

### Issue: Test execution slow (>1s framework overhead)
**Solution:** Use mock agents for testing. Framework overhead should be <100ms. If slower, profile with debug logging.

## References

- **Configuration:** `raglite/shared/config.py` - Strands configuration settings
- **Orchestrator:** `raglite/agentic/orchestrator.py` - Core orchestration engine
- **State Management:** `raglite/agentic/state.py` - AgentState definition
- **Error Handler:** `raglite/agentic/error_handler.py` - Error handling and fallback
- **Mock Agents:** `raglite/agentic/agents/` - Mock agent implementations for testing
- **Tests:** `tests/unit/agentic/` & `tests/integration/test_agentic_framework.py` - Comprehensive test examples

## Next Steps

After this story (3.1), the following stories implement actual agents:

- **Story 3.2:** Retrieval Agent - Integrates with `multi_index_search` for document retrieval
- **Story 3.3:** Analysis Agent - Processes retrieved data for insights
- **Story 3.4:** Synthesis Agent - Generates final answers from analysis

These agents will be plugged into the orchestration framework created in this story using the patterns documented above.
