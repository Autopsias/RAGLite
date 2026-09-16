"""Unit tests for mock agents.

Tests AC3: Basic 2-step workflow execution with mock agents
"""

import pytest

from raglite.agentic.agents.mock_retrieval import MockRetrievalAgent
from raglite.agentic.agents.mock_synthesis import MockSynthesisAgent
from raglite.agentic.state import AgentState


class TestMockRetrievalAgent:
    """Test mock retrieval agent."""

    @pytest.mark.asyncio
    async def test_mock_retrieval_agent_execution(self) -> None:
        """Test mock retrieval agent processes query and returns results.

        AC3: Test workflow: Retrieval Agent returns mock chunks
        """
        agent = MockRetrievalAgent()
        state = AgentState(query="What is the revenue forecast?")

        result_state = await agent(state)

        assert result_state.retrieval_results is not None
        assert len(result_state.retrieval_results) == 3
        assert result_state.retrieval_score == 0.95

    @pytest.mark.asyncio
    async def test_mock_retrieval_agent_adds_metadata(self) -> None:
        """Test that retrieval agent adds metadata to state."""
        agent = MockRetrievalAgent()
        state = AgentState(query="Test query")

        result_state = await agent(state)

        assert result_state.metadata.get("retrieval_agent") == "mock"
        assert result_state.metadata.get("retrieval_chunk_count") == 3

    @pytest.mark.asyncio
    async def test_mock_retrieval_agent_chunk_content(self) -> None:
        """Test that mock retrieval returns proper chunk structure."""
        agent = MockRetrievalAgent()
        state = AgentState(query="Test")

        result_state = await agent(state)

        for chunk in result_state.retrieval_results:
            assert chunk.id is not None
            assert chunk.content is not None
            assert chunk.source is not None
            assert chunk.metadata is not None

    @pytest.mark.asyncio
    async def test_mock_retrieval_agent_preserves_query(self) -> None:
        """Test that agent preserves original query in state."""
        agent = MockRetrievalAgent()
        original_query = "Financial analysis needed"
        state = AgentState(query=original_query)

        result_state = await agent(state)

        assert result_state.query == original_query


class TestMockSynthesisAgent:
    """Test mock synthesis agent."""

    @pytest.mark.asyncio
    async def test_mock_synthesis_agent_with_results(self) -> None:
        """Test synthesis agent processes retrieval results.

        AC3: Test workflow: Synthesis Agent returns mock synthesis
        """
        agent = MockSynthesisAgent()

        # Create state with retrieval results
        from raglite.agentic.state import DocumentChunk

        state = AgentState(query="What is the financial outlook?")
        state.retrieval_results = [
            DocumentChunk(
                id="chunk_1",
                content="Sample content",
                source="report.pdf",
                chunk_index=0,
            )
        ]

        result_state = await agent(state)

        assert result_state.synthesis_result is not None
        assert len(result_state.synthesis_result) > 0
        assert "financial" in result_state.synthesis_result.lower()

    @pytest.mark.asyncio
    async def test_mock_synthesis_agent_without_retrieval(self) -> None:
        """Test synthesis agent handles missing retrieval results."""
        agent = MockSynthesisAgent()
        state = AgentState(query="Test query")
        # No retrieval results set

        result_state = await agent(state)

        assert result_state.synthesis_result is not None
        assert "Unable to synthesize" in result_state.synthesis_result

    @pytest.mark.asyncio
    async def test_mock_synthesis_agent_adds_metadata(self) -> None:
        """Test that synthesis agent adds metadata to state."""
        agent = MockSynthesisAgent()

        from raglite.agentic.state import DocumentChunk

        state = AgentState(query="Test")
        state.retrieval_results = [
            DocumentChunk(
                id="chunk_1",
                content="Data",
                source="file.pdf",
                chunk_index=0,
            )
        ]

        result_state = await agent(state)

        assert result_state.metadata.get("synthesis_agent") == "mock"
        assert result_state.metadata.get("synthesis_type") == "mock"

    @pytest.mark.asyncio
    async def test_mock_synthesis_agent_preserves_query(self) -> None:
        """Test that synthesis agent preserves query."""
        agent = MockSynthesisAgent()
        original_query = "Revenue analysis"

        from raglite.agentic.state import DocumentChunk

        state = AgentState(query=original_query)
        state.retrieval_results = [
            DocumentChunk(
                id="chunk_1",
                content="Revenue data",
                source="report.pdf",
                chunk_index=0,
            )
        ]

        result_state = await agent(state)

        assert result_state.query == original_query


class TestMockAgentIntegration:
    """Test mock agents working together."""

    @pytest.mark.asyncio
    async def test_retrieval_then_synthesis(self) -> None:
        """Test retrieval agent followed by synthesis agent.

        AC3: Basic 2-step workflow execution: Retrieval → Synthesis
        """
        retrieval = MockRetrievalAgent()
        synthesis = MockSynthesisAgent()

        # Start with query
        state = AgentState(query="What is the current financial status?")

        # Run retrieval
        state = await retrieval(state)
        assert state.retrieval_results is not None
        assert state.synthesis_result is None

        # Run synthesis on retrieved results
        state = await synthesis(state)
        assert state.retrieval_results is not None
        assert state.synthesis_result is not None

        # Both should be present in final state
        assert state.query == "What is the current financial status?"
        assert len(state.retrieval_results) > 0
        assert len(state.synthesis_result) > 0
