"""Unit tests for AgentState and state management.

Tests AC4: State management functional for multi-step workflows
Tests AC4: State validation confirms data integrity across agent boundaries
"""

from raglite.agentic.state import AgentState, AnalysisOutput, DocumentChunk


class TestAgentStateBasics:
    """Test basic AgentState functionality."""

    def test_agent_state_creation_with_query(self) -> None:
        """Test creating AgentState with query input.

        AC4: Agent execution state captured and propagated
        """
        query = "What is the revenue forecast for 2025?"
        state = AgentState(query=query)

        assert state.query == query
        assert state.retrieval_results is None
        assert state.analysis_results is None
        assert state.synthesis_result is None
        assert state.metadata == {}

    def test_document_chunk_creation(self) -> None:
        """Test creating DocumentChunk objects."""
        chunk = DocumentChunk(
            id="chunk_1",
            content="Sample financial data",
            source="report.pdf",
            page_number=10,
            chunk_index=0,
        )

        assert chunk.id == "chunk_1"
        assert chunk.content == "Sample financial data"
        assert chunk.source == "report.pdf"
        assert chunk.page_number == 10
        assert chunk.chunk_index == 0

    def test_analysis_output_creation(self) -> None:
        """Test creating AnalysisOutput objects."""
        analysis = AnalysisOutput(
            insights=["Revenue growing", "Costs stable"],
            entities=["Company A", "Q4 2024"],
            confidence_score=0.92,
        )

        assert len(analysis.insights) == 2
        assert "Revenue growing" in analysis.insights
        assert analysis.confidence_score == 0.92


class TestStateProgression:
    """Test state progression through agent pipeline."""

    def test_state_progression_through_agents(self) -> None:
        """Test state passing between agents.

        AC4: Context passes between sequential agents
        """
        # Initial state
        state = AgentState(query="Financial analysis needed")
        assert state.retrieval_results is None

        # After retrieval agent
        retrieval_chunk = DocumentChunk(
            id="chunk_1",
            content="Revenue: $5.2B",
            source="report.pdf",
            page_number=15,
            chunk_index=0,
        )
        state.retrieval_results = [retrieval_chunk]
        state.retrieval_score = 0.95

        assert len(state.retrieval_results) == 1
        assert state.retrieval_score == 0.95
        assert state.synthesis_result is None

        # After synthesis agent
        state.synthesis_result = "Based on the retrieved data..."
        assert state.synthesis_result is not None
        assert len(state.retrieval_results) == 1  # Still present


class TestStateMetadata:
    """Test state metadata management."""

    def test_add_metadata(self) -> None:
        """Test adding metadata to state.

        AC4: Agent execution state captured and propagated
        """
        state = AgentState(query="Test query")
        state.add_metadata("step_1", "completed")
        state.add_metadata("duration_ms", 125)

        assert state.metadata["step_1"] == "completed"
        assert state.metadata["duration_ms"] == 125

    def test_metadata_persistence(self) -> None:
        """Test that metadata persists through state updates."""
        state = AgentState(query="Test query")
        state.add_metadata("agent_1", "retrieval")

        # Add retrieval results and more metadata
        chunk = DocumentChunk(
            id="chunk_1",
            content="Data",
            source="file.pdf",
            chunk_index=0,
        )
        state.retrieval_results = [chunk]
        state.add_metadata("agent_2", "synthesis")

        assert state.metadata["agent_1"] == "retrieval"
        assert state.metadata["agent_2"] == "synthesis"


class TestStateValidation:
    """Test state validation."""

    def test_validate_required_fields_success(self) -> None:
        """Test successful field validation.

        AC4: State validation confirms data integrity across agent boundaries
        """
        state = AgentState(query="Test query")
        chunk = DocumentChunk(
            id="chunk_1",
            content="Data",
            source="file.pdf",
            chunk_index=0,
        )
        state.retrieval_results = [chunk]

        is_valid, error = state.validate_required_fields(["query", "retrieval_results"])
        assert is_valid is True
        assert error is None

    def test_validate_required_fields_missing_fields(self) -> None:
        """Test validation with missing required fields."""
        state = AgentState(query="Test query")
        # retrieval_results is None (not set)

        is_valid, error = state.validate_required_fields(
            ["query", "retrieval_results", "synthesis_result"]
        )
        assert is_valid is False
        assert error is not None
        assert "Missing required fields" in error

    def test_validate_empty_requirements(self) -> None:
        """Test validation with no required fields."""
        state = AgentState(query="Test query")

        is_valid, error = state.validate_required_fields([])
        assert is_valid is True
        assert error is None

    def test_validate_single_missing_field(self) -> None:
        """Test validation with single missing field."""
        state = AgentState(query="Test query")

        is_valid, error = state.validate_required_fields(["synthesis_result"])
        assert is_valid is False
        assert "synthesis_result" in error


class TestStateDataIntegrity:
    """Test state data integrity across boundaries."""

    def test_state_data_isolation(self) -> None:
        """Test that state modifications don't affect other instances."""
        state1 = AgentState(query="Query 1")
        state2 = AgentState(query="Query 2")

        chunk = DocumentChunk(
            id="chunk_1",
            content="Data",
            source="file.pdf",
            chunk_index=0,
        )

        state1.retrieval_results = [chunk]

        assert state1.retrieval_results is not None
        assert state2.retrieval_results is None

    def test_state_metadata_isolation(self) -> None:
        """Test that metadata doesn't leak between states."""
        state1 = AgentState(query="Query 1")
        state2 = AgentState(query="Query 2")

        state1.add_metadata("key", "value1")
        state2.add_metadata("key", "value2")

        assert state1.metadata["key"] == "value1"
        assert state2.metadata["key"] == "value2"
