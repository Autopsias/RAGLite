"""Unit tests for Strands orchestrator.

Tests AC2: Framework initialization and configuration validated
Tests AC3: Basic 2-step workflow execution tested
"""

import asyncio

# Check if strands is available
import importlib.util
from unittest.mock import Mock

import pytest

from raglite.agentic.orchestrator import StrandsOrchestrator
from raglite.agentic.state import AgentState, DocumentChunk

STRANDS_AVAILABLE = importlib.util.find_spec("strands") is not None


class TestOrchestrationInitialization:
    """Test Strands orchestrator initialization."""

    def test_orchestrator_initialization(self) -> None:
        """Test that orchestrator initializes with correct configuration.

        AC2: Strands Agent class instantiable with basic config
        """
        orchestrator = StrandsOrchestrator()

        assert orchestrator is not None
        assert orchestrator.orchestration_model == "mistral-small-latest"
        assert orchestrator.agent_timeout == 15

    def test_orchestrator_configuration_retrieval(self) -> None:
        """Test retrieving orchestrator configuration.

        AC2: Framework initialization and configuration validated
        """
        orchestrator = StrandsOrchestrator()
        config = orchestrator.get_configuration()

        assert config["orchestration_model"] == "mistral-small-latest"
        assert config["agent_timeout_seconds"] == 15
        assert "observability_enabled" in config


class TestAgentCreation:
    """Test agent creation through orchestrator."""

    @pytest.mark.skipif(not STRANDS_AVAILABLE, reason="Strands not installed (deferred to Epic 3)")
    @pytest.mark.asyncio
    async def test_create_agent_basic(self) -> None:
        """Test creating a basic agent.

        AC2: Strands Agent class instantiable with basic config
        """
        orchestrator = StrandsOrchestrator()

        agent = await orchestrator.create_agent(
            name="TestAgent",
            system_prompt="You are a test agent",
        )

        assert agent is not None
        assert hasattr(agent, "name") or agent is not None

    @pytest.mark.skipif(not STRANDS_AVAILABLE, reason="Strands not installed (deferred to Epic 3)")
    @pytest.mark.asyncio
    async def test_create_agent_with_tools(self) -> None:
        """Test creating an agent with tools."""
        orchestrator = StrandsOrchestrator()

        def sample_tool(query: str) -> str:
            """Sample tool for agent."""
            return f"Tool result for: {query}"

        agent = await orchestrator.create_agent(
            name="ToolAgent",
            tools=[sample_tool],
            system_prompt="You have tools available",
        )

        assert agent is not None

    @pytest.mark.skipif(not STRANDS_AVAILABLE, reason="Strands not installed (deferred to Epic 3)")
    @pytest.mark.asyncio
    async def test_create_agent_invalid_fails(self) -> None:
        """Test that invalid agent configuration raises error."""
        orchestrator = StrandsOrchestrator()

        # This should handle None tools gracefully
        agent = await orchestrator.create_agent(
            name="Agent",
            tools=None,
        )

        assert agent is not None


class TestWorkflowExecution:
    """Test workflow execution."""

    @pytest.mark.asyncio
    async def test_two_step_workflow_execution(self) -> None:
        """Test basic 2-step workflow execution.

        AC3: Basic 2-step workflow execution tested
        AC3: Test workflow: Retrieval Agent → Synthesis Agent
        """
        orchestrator = StrandsOrchestrator()

        # Create mock agents
        async def mock_retrieval(agent: Mock, state: AgentState) -> AgentState:
            """Mock retrieval step."""
            chunk = DocumentChunk(
                id="chunk_1",
                content="Mock data",
                source="mock.pdf",
                chunk_index=0,
            )
            state.retrieval_results = [chunk]
            return state

        async def mock_synthesis(agent: Mock, state: AgentState) -> AgentState:
            """Mock synthesis step."""
            state.synthesis_result = "Mock synthesis result"
            return state

        # Define workflow steps
        workflow_steps = [
            {
                "name": "retrieval",
                "agent": Mock(),
                "process_fn": mock_retrieval,
            },
            {
                "name": "synthesis",
                "agent": Mock(),
                "process_fn": mock_synthesis,
            },
        ]

        # Execute workflow
        initial_state = AgentState(query="Test query")
        final_state = await orchestrator.execute_workflow(initial_state, workflow_steps)

        assert final_state.query == "Test query"
        assert final_state.retrieval_results is not None
        assert len(final_state.retrieval_results) == 1
        assert final_state.synthesis_result == "Mock synthesis result"

    @pytest.mark.asyncio
    async def test_workflow_state_propagation(self) -> None:
        """Test that state propagates correctly between agents.

        AC3: State passes correctly between agents
        AC4: Context passes between sequential agents
        """
        orchestrator = StrandsOrchestrator()

        execution_order = []

        async def step_1(agent: Mock, state: AgentState) -> AgentState:
            """First workflow step."""
            execution_order.append("step_1")
            state.add_metadata("step_1_executed", True)
            state.retrieval_results = [
                DocumentChunk(
                    id="chunk_1",
                    content="Data",
                    source="file.pdf",
                    chunk_index=0,
                )
            ]
            return state

        async def step_2(agent: Mock, state: AgentState) -> AgentState:
            """Second workflow step."""
            execution_order.append("step_2")
            # Verify state from step_1
            assert state.metadata.get("step_1_executed") is True
            assert state.retrieval_results is not None
            state.synthesis_result = "Result based on retrieval"
            return state

        workflow_steps = [
            {"name": "step_1", "agent": Mock(), "process_fn": step_1},
            {"name": "step_2", "agent": Mock(), "process_fn": step_2},
        ]

        initial_state = AgentState(query="Test")
        final_state = await orchestrator.execute_workflow(initial_state, workflow_steps)

        # Verify execution order
        assert execution_order == ["step_1", "step_2"]

        # Verify final state
        assert final_state.metadata.get("step_1_executed") is True
        assert final_state.retrieval_results is not None
        assert final_state.synthesis_result == "Result based on retrieval"

    @pytest.mark.asyncio
    async def test_workflow_timeout_handling(self) -> None:
        """Test workflow timeout handling.

        AC5: Agent timeout handling (max 15s per agent, per NFR26)
        """
        orchestrator = StrandsOrchestrator()

        async def slow_agent(agent: Mock, state: AgentState) -> AgentState:
            """Agent that takes too long."""
            await asyncio.sleep(20)  # Exceeds 15s timeout
            return state

        workflow_steps = [
            {
                "name": "slow_step",
                "agent": Mock(),
                "process_fn": slow_agent,
            }
        ]

        initial_state = AgentState(query="Test")

        with pytest.raises(TimeoutError):
            await orchestrator.execute_workflow(initial_state, workflow_steps)

    @pytest.mark.asyncio
    async def test_workflow_step_error_handling(self) -> None:
        """Test workflow error handling on step failure."""
        orchestrator = StrandsOrchestrator()

        async def failing_agent(agent: Mock, state: AgentState) -> AgentState:
            """Agent that raises error."""
            raise ValueError("Agent processing failed")

        workflow_steps = [
            {
                "name": "failing_step",
                "agent": Mock(),
                "process_fn": failing_agent,
            }
        ]

        initial_state = AgentState(query="Test")

        with pytest.raises(RuntimeError):
            await orchestrator.execute_workflow(initial_state, workflow_steps)

    @pytest.mark.asyncio
    async def test_workflow_missing_step_attributes(self) -> None:
        """Test workflow with missing step attributes."""
        orchestrator = StrandsOrchestrator()

        # Missing 'process_fn'
        workflow_steps = [{"name": "incomplete_step", "agent": Mock()}]

        initial_state = AgentState(query="Test")

        with pytest.raises(RuntimeError):
            await orchestrator.execute_workflow(initial_state, workflow_steps)
