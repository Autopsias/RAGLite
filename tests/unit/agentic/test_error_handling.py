"""Unit tests for error handling and graceful degradation.

Tests AC5: Error handling implemented for workflow failures (NFR24, NFR26)
Tests AC5: Graceful degradation on agent failures
Tests AC5: Error logging with structured metadata
"""

import asyncio

import pytest

from raglite.agentic.error_handler import AgentExecutionError, WorkflowErrorHandler
from raglite.agentic.state import AgentState


class TestAgentExecutionError:
    """Test AgentExecutionError exception."""

    def test_agent_execution_error_creation(self) -> None:
        """Test creating AgentExecutionError."""
        error = AgentExecutionError(
            message="Agent failed",
            agent_name="TestAgent",
            error_type="failure",
            metadata={"details": "test error"},
        )

        assert error.message == "Agent failed"
        assert error.agent_name == "TestAgent"
        assert error.error_type == "failure"
        assert error.metadata["details"] == "test error"


class TestTimeoutHandling:
    """Test timeout handling for agents."""

    @pytest.mark.asyncio
    async def test_agent_timeout_detection(self) -> None:
        """Test detection of agent timeout.

        AC5: Agent timeout handling (max 15s per agent, per NFR26)
        """
        handler = WorkflowErrorHandler()

        async def slow_agent():
            """Agent that times out."""
            await asyncio.sleep(2)
            return AgentState(query="test")

        state = AgentState(query="test")
        success, result_state, error = await handler.execute_with_fallback(
            slow_agent(), timeout_seconds=1, agent_name="SlowAgent", state=state
        )

        assert success is False
        assert error is not None
        assert "timeout" in error.lower()

    @pytest.mark.asyncio
    async def test_agent_success_within_timeout(self) -> None:
        """Test agent success within timeout."""
        handler = WorkflowErrorHandler()

        async def fast_agent():
            """Agent that completes quickly."""
            state = AgentState(query="test")
            state.synthesis_result = "Done"
            return state

        state = AgentState(query="test")
        success, result_state, error = await handler.execute_with_fallback(
            fast_agent(), timeout_seconds=5, agent_name="FastAgent", state=state
        )

        assert success is True
        assert error is None
        assert result_state.synthesis_result == "Done"


class TestErrorLogging:
    """Test error logging with structured metadata."""

    def test_error_logging_captures_metadata(self) -> None:
        """Test that error logging captures structured metadata.

        AC5: Error logging with structured metadata
        (agent ID, failure reason, timestamp)
        """
        handler = WorkflowErrorHandler()

        handler._log_error(
            message="Test error",
            agent_name="TestAgent",
            error_type="failure",
            metadata={
                "query": "test query",
                "reason": "processing failed",
            },
        )

        error_log = handler.get_error_log()
        assert len(error_log) == 1
        assert error_log[0]["agent_id"] == "TestAgent"
        assert error_log[0]["error_type"] == "failure"
        assert error_log[0]["query"] == "test query"

    def test_error_log_accumulation(self) -> None:
        """Test that errors accumulate in error log."""
        handler = WorkflowErrorHandler()

        handler._log_error(
            message="Error 1",
            agent_name="Agent1",
            error_type="timeout",
            metadata={},
        )
        handler._log_error(
            message="Error 2",
            agent_name="Agent2",
            error_type="failure",
            metadata={},
        )

        error_log = handler.get_error_log()
        assert len(error_log) == 2
        assert error_log[0]["agent_id"] == "Agent1"
        assert error_log[1]["agent_id"] == "Agent2"

    def test_error_log_clearing(self) -> None:
        """Test that error log can be cleared."""
        handler = WorkflowErrorHandler()

        handler._log_error(
            message="Error",
            agent_name="Agent",
            error_type="failure",
            metadata={},
        )

        assert len(handler.get_error_log()) == 1

        handler.clear_error_log()

        assert len(handler.get_error_log()) == 0


class TestFallbackHandling:
    """Test graceful degradation with fallback."""

    @pytest.mark.asyncio
    async def test_fallback_without_fallback_function(self) -> None:
        """Test fallback handling when no fallback function is configured.

        AC5: Graceful degradation on agent failures
        """
        handler = WorkflowErrorHandler(fallback_search_func=None)

        state = AgentState(query="test query")
        result_state = await handler.fallback_to_simple_search(state, error_reason="agent timeout")

        # State should be unchanged if no fallback function
        assert result_state.query == "test query"

    @pytest.mark.asyncio
    async def test_fallback_with_search_function(self) -> None:
        """Test fallback to simple search function.

        AC5: Graceful degradation (fallback to Epic 2 simple search)
        """

        async def mock_search(query: str, top_k: int):
            """Mock search function."""

            # Return mock results
            class MockResult:
                def __init__(self, content, source):
                    self.content = content
                    self.source = source
                    self.page_number = 1

            return [
                MockResult("Financial data 1", "report.pdf"),
                MockResult("Financial data 2", "report.pdf"),
            ]

        handler = WorkflowErrorHandler(fallback_search_func=mock_search)

        state = AgentState(query="financial analysis")
        result_state = await handler.fallback_to_simple_search(
            state, error_reason="agentic workflow failed"
        )

        assert result_state.retrieval_results is not None
        assert len(result_state.retrieval_results) == 2
        assert result_state.metadata.get("used_fallback") is True

    @pytest.mark.asyncio
    async def test_fallback_search_failure(self) -> None:
        """Test fallback when simple search also fails.

        AC5: Graceful degradation with logging
        """

        async def failing_search(query: str, top_k: int):
            """Mock search that fails."""
            raise RuntimeError("Search failed")

        handler = WorkflowErrorHandler(fallback_search_func=failing_search)

        state = AgentState(query="test query")
        result_state = await handler.fallback_to_simple_search(state, error_reason="agent failed")

        # Should return state with error metadata
        assert result_state.query == "test query"
        # Check error log
        errors = handler.get_error_log()
        assert any("fallback" in str(e) for e in errors)


class TestGracefulDegradation:
    """Test graceful degradation workflow."""

    @pytest.mark.asyncio
    async def test_workflow_failure_triggers_fallback(self) -> None:
        """Test that workflow failure triggers fallback.

        AC5: Graceful degradation on agent failures (NFR24)
        """

        async def failing_agent():
            """Agent that fails."""
            raise ValueError("Agent processing failed")

        async def mock_fallback(query: str, top_k: int):
            """Mock fallback search."""

            class MockResult:
                def __init__(self):
                    self.content = "Fallback result"
                    self.source = "fallback"
                    self.page_number = None

            return [MockResult()]

        handler = WorkflowErrorHandler(fallback_search_func=mock_fallback)

        state = AgentState(query="test query")

        # Try to execute agent (will fail)
        success, result_state, error = await handler.execute_with_fallback(
            failing_agent(), timeout_seconds=5, agent_name="FailingAgent", state=state
        )

        assert success is False

        # Fall back to simple search
        final_state = await handler.fallback_to_simple_search(result_state, error_reason=error)

        assert final_state.retrieval_results is not None
        assert final_state.metadata.get("used_fallback") is True


class TestErrorMetadata:
    """Test error metadata collection."""

    def test_timeout_error_metadata(self) -> None:
        """Test that timeout errors include proper metadata."""
        handler = WorkflowErrorHandler()

        handler._log_error(
            message="Timeout",
            agent_name="TimeoutAgent",
            error_type="timeout",
            metadata={
                "timeout_seconds": 15,
                "query": "complex query",
            },
        )

        error_log = handler.get_error_log()
        assert error_log[0]["timeout_seconds"] == 15
        assert error_log[0]["agent_id"] == "TimeoutAgent"

    def test_failure_error_metadata(self) -> None:
        """Test that failure errors include proper metadata."""
        handler = WorkflowErrorHandler()

        handler._log_error(
            message="Agent failed",
            agent_name="FailureAgent",
            error_type="failure",
            metadata={
                "error_type": "ValueError",
                "error_details": "Invalid input",
                "query": "test",
            },
        )

        error_log = handler.get_error_log()
        assert error_log[0]["error_details"] == "Invalid input"
        assert error_log[0]["error_type"] == "failure"
