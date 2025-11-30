"""Integration tests for agentic framework.

Tests AC6: Integration test validates framework execution
- End-to-end test with mock agents (no real LLM calls)
- Test validates agent coordination and state flow
- Test execution time <1s (framework overhead only)
"""

import time

import pytest

from raglite.agentic.agents.mock_retrieval import MockRetrievalAgent
from raglite.agentic.agents.mock_synthesis import MockSynthesisAgent
from raglite.agentic.orchestrator import StrandsOrchestrator
from raglite.agentic.state import AgentState

# Mark all tests in this module as integration tests that preserve collection state
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection]


@pytest.mark.asyncio
class TestAgenticFrameworkIntegration:
    """Integration tests for the agentic framework."""

    async def test_end_to_end_mock_workflow(self) -> None:
        """Test end-to-end workflow with mock agents.

        AC6: End-to-end test with mock agents (no real LLM calls)
        AC6: Test validates agent coordination and state flow
        """
        orchestrator = StrandsOrchestrator()
        retrieval_agent = MockRetrievalAgent()
        synthesis_agent = MockSynthesisAgent()

        # Create workflow steps using mock agents
        workflow_steps = [
            {
                "name": "retrieval",
                "agent": None,
                "process_fn": lambda agent, state: retrieval_agent(state),
            },
            {
                "name": "synthesis",
                "agent": None,
                "process_fn": lambda agent, state: synthesis_agent(state),
            },
        ]

        # Execute workflow
        initial_state = AgentState(query="What is the financial performance for 2024?")

        final_state = await orchestrator.execute_workflow(initial_state, workflow_steps)

        # Validate workflow executed successfully
        assert final_state.query == initial_state.query
        assert final_state.retrieval_results is not None
        assert len(final_state.retrieval_results) > 0
        assert final_state.synthesis_result is not None
        assert len(final_state.synthesis_result) > 0

    async def test_state_propagation_through_agents(self) -> None:
        """Test state propagates correctly between agents.

        AC6: Test validates agent coordination and state flow
        """
        orchestrator = StrandsOrchestrator()
        retrieval_agent = MockRetrievalAgent()
        synthesis_agent = MockSynthesisAgent()

        execution_trace = []

        async def step1(agent, state: AgentState) -> AgentState:
            """Retrieval with execution tracing."""
            execution_trace.append("retrieval_start")
            state = await retrieval_agent(state)
            execution_trace.append("retrieval_end")
            return state

        async def step2(agent, state: AgentState) -> AgentState:
            """Synthesis with execution tracing."""
            execution_trace.append("synthesis_start")
            state = await synthesis_agent(state)
            execution_trace.append("synthesis_end")
            return state

        workflow_steps = [
            {
                "name": "retrieval",
                "agent": None,
                "process_fn": step1,
            },
            {
                "name": "synthesis",
                "agent": None,
                "process_fn": step2,
            },
        ]

        initial_state = AgentState(query="Test query")
        final_state = await orchestrator.execute_workflow(initial_state, workflow_steps)

        # Validate execution order
        assert execution_trace == [
            "retrieval_start",
            "retrieval_end",
            "synthesis_start",
            "synthesis_end",
        ]

        # Validate state progression
        assert final_state.retrieval_results is not None
        assert final_state.synthesis_result is not None

    async def test_framework_overhead_performance(self) -> None:
        """Test framework overhead is minimal (<1s).

        AC6: Test execution time <1s (framework overhead only, no LLM latency)
        """
        orchestrator = StrandsOrchestrator()
        retrieval_agent = MockRetrievalAgent()
        synthesis_agent = MockSynthesisAgent()

        async def fast_retrieval(agent, state: AgentState) -> AgentState:
            """Fast retrieval (mock data, no I/O)."""
            return await retrieval_agent(state)

        async def fast_synthesis(agent, state: AgentState) -> AgentState:
            """Fast synthesis (mock generation, no LLM)."""
            return await synthesis_agent(state)

        workflow_steps = [
            {
                "name": "retrieval",
                "agent": None,
                "process_fn": fast_retrieval,
            },
            {
                "name": "synthesis",
                "agent": None,
                "process_fn": fast_synthesis,
            },
        ]

        # Measure execution time
        start_time = time.time()

        initial_state = AgentState(query="Performance test query")
        final_state = await orchestrator.execute_workflow(initial_state, workflow_steps)

        elapsed_time = time.time() - start_time

        # Verify execution completed
        assert final_state.retrieval_results is not None
        assert final_state.synthesis_result is not None

        # Framework overhead should be <1s (mock agents have no latency)
        assert elapsed_time < 1.0, f"Framework overhead {elapsed_time}s exceeds 1s limit"

    async def test_multiple_retrieval_results(self) -> None:
        """Test handling of multiple retrieval results in synthesis.

        AC6: Test validates agent coordination and state flow
        """
        orchestrator = StrandsOrchestrator()
        retrieval_agent = MockRetrievalAgent()
        synthesis_agent = MockSynthesisAgent()

        async def multi_result_retrieval(agent, state: AgentState) -> AgentState:
            """Retrieval returning multiple chunks."""
            return await retrieval_agent(state)

        async def multi_aware_synthesis(agent, state: AgentState) -> AgentState:
            """Synthesis processing multiple chunks."""
            return await synthesis_agent(state)

        workflow_steps = [
            {
                "name": "retrieval",
                "agent": None,
                "process_fn": multi_result_retrieval,
            },
            {
                "name": "synthesis",
                "agent": None,
                "process_fn": multi_aware_synthesis,
            },
        ]

        initial_state = AgentState(query="Comprehensive financial analysis")
        final_state = await orchestrator.execute_workflow(initial_state, workflow_steps)

        # Validate multiple results handled correctly
        assert final_state.retrieval_results is not None
        assert len(final_state.retrieval_results) > 1
        assert final_state.synthesis_result is not None
        assert "retrieved data" in final_state.synthesis_result.lower()

    async def test_workflow_metadata_accumulation(self) -> None:
        """Test that metadata accumulates through workflow.

        AC6: Test validates agent coordination and state flow
        """
        orchestrator = StrandsOrchestrator()
        retrieval_agent = MockRetrievalAgent()
        synthesis_agent = MockSynthesisAgent()

        async def metadata_retrieval(agent, state: AgentState) -> AgentState:
            """Retrieval that adds metadata."""
            state = await retrieval_agent(state)
            state.add_metadata("retrieval_model", "mock_v1")
            return state

        async def metadata_synthesis(agent, state: AgentState) -> AgentState:
            """Synthesis that adds metadata."""
            state = await synthesis_agent(state)
            state.add_metadata("synthesis_model", "mock_v1")
            return state

        workflow_steps = [
            {
                "name": "retrieval",
                "agent": None,
                "process_fn": metadata_retrieval,
            },
            {
                "name": "synthesis",
                "agent": None,
                "process_fn": metadata_synthesis,
            },
        ]

        initial_state = AgentState(query="Test")
        final_state = await orchestrator.execute_workflow(initial_state, workflow_steps)

        # Validate metadata accumulated
        assert final_state.metadata.get("retrieval_agent") == "mock"
        assert final_state.metadata.get("synthesis_agent") == "mock"
        assert final_state.metadata.get("retrieval_model") == "mock_v1"
        assert final_state.metadata.get("synthesis_model") == "mock_v1"
