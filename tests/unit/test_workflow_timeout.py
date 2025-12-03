"""Unit tests for workflow timeout and graceful degradation (Story 3.5 Task 4.6).

Tests AC8: Workflow timeout and graceful degradation mechanisms.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from raglite.agentic.fallback import (
    FallbackTier,
    execute_with_timeout,
    fallback_to_basic_retrieval,
    format_fallback_response,
    handle_workflow_failure,
)
from raglite.agentic.orchestrator import WorkflowExecutor
from raglite.agentic.planner import AgentResult, AgentTask, QueryComplexity


class TestExecuteWithTimeout:
    """Tests for execute_with_timeout() function (AC8: Task 4.1)."""

    @pytest.mark.asyncio
    async def test_execute_with_timeout_success(self):
        """Test successful agent execution within timeout."""

        # Arrange
        async def mock_agent(instruction: str, context: dict) -> str:
            await asyncio.sleep(0.1)  # Simulate work
            return "Agent completed successfully"

        # Act
        result = await execute_with_timeout(
            agent_fn=mock_agent,
            instruction="Test instruction",
            context={},
            timeout_seconds=5.0,
        )

        # Assert
        assert result == "Agent completed successfully"

    @pytest.mark.asyncio
    async def test_execute_with_timeout_triggers_timeout(self):
        """Test timeout is triggered when agent exceeds timeout limit (AC8: Task 4.1)."""

        # Arrange
        async def slow_agent(instruction: str, context: dict) -> str:
            await asyncio.sleep(10.0)  # Longer than timeout
            return "Should not reach here"

        # Act & Assert
        with pytest.raises(asyncio.TimeoutError):
            await execute_with_timeout(
                agent_fn=slow_agent,
                instruction="Test instruction",
                context={},
                timeout_seconds=0.1,  # Short timeout
            )

    @pytest.mark.asyncio
    async def test_execute_with_timeout_propagates_exceptions(self):
        """Test that non-timeout exceptions are propagated."""

        # Arrange
        async def failing_agent(instruction: str, context: dict) -> str:
            raise ValueError("Agent logic error")

        # Act & Assert
        with pytest.raises(ValueError, match="Agent logic error"):
            await execute_with_timeout(
                agent_fn=failing_agent,
                instruction="Test instruction",
                context={},
                timeout_seconds=5.0,
            )


class TestFallbackToBasicRetrieval:
    """Tests for fallback_to_basic_retrieval() function (AC8: Task 4.3)."""

    @pytest.mark.asyncio
    @patch("raglite.retrieval.search.search_documents")
    async def test_fallback_returns_basic_search_results(self, mock_search):
        """Test fallback calls Epic 1 search and formats results."""
        # Arrange
        # search_documents returns list[QueryResult]
        mock_result_1 = MagicMock(text="Q3 revenue was $150M", score=0.9)
        mock_result_2 = MagicMock(text="Operating expenses increased 15%", score=0.8)
        mock_search.return_value = [mock_result_1, mock_result_2]

        # Act
        result = await fallback_to_basic_retrieval("What was Q3 revenue?")

        # Assert
        assert "Based on the available documents" in result
        assert "Q3 revenue was $150M" in result
        mock_search.assert_called_once()

    @pytest.mark.asyncio
    @patch("raglite.retrieval.search.search_documents")
    async def test_fallback_handles_no_results(self, mock_search):
        """Test fallback handles case with no search results."""
        # Arrange
        mock_search.return_value = []  # Empty list

        # Act
        result = await fallback_to_basic_retrieval("Nonexistent topic")

        # Assert
        assert "couldn't find relevant information" in result

    @pytest.mark.asyncio
    @patch("raglite.retrieval.search.search_documents")
    async def test_fallback_handles_search_failure(self, mock_search):
        """Test fallback handles Epic 1 search failure gracefully."""
        # Arrange
        mock_search.side_effect = Exception("Database connection failed")

        # Act
        result = await fallback_to_basic_retrieval("Test query")

        # Assert
        assert "experiencing technical difficulties" in result


class TestFormatFallbackResponse:
    """Tests for format_fallback_response() function (AC8: Task 4.4)."""

    def test_format_partial_workflow_response(self):
        """Test formatting of partial workflow response."""
        # Arrange
        partial_results = [
            AgentResult(
                task_id="task_1",
                agent_type="retrieval",
                success=True,
                result="Retrieved document chunks",
                execution_time_ms=500,
            ),
            AgentResult(
                task_id="task_2",
                agent_type="analysis",
                success=False,
                result=None,
                execution_time_ms=100,
                error_message="Timeout",
            ),
        ]

        # Act
        response = format_fallback_response(
            query="Test query",
            tier=FallbackTier.PARTIAL_WORKFLOW,
            partial_results=partial_results,
            error_message="Analysis agent timed out",
            total_time_ms=600,
        )

        # Assert
        assert response.tier == FallbackTier.PARTIAL_WORKFLOW
        assert response.confidence == "medium"
        assert "Partial Analysis" in response.answer
        assert "Retrieved document chunks" in response.answer
        assert len(response.limitations) > 0
        assert response.error_details == "Analysis agent timed out"

    def test_format_epic1_fallback_response(self):
        """Test formatting of Epic 1 fallback response."""
        # Act
        response = format_fallback_response(
            query="Test query",
            tier=FallbackTier.EPIC1_FALLBACK,
            partial_results=[],
            error_message="All agents failed",
            total_time_ms=1000,
        )

        # Assert
        assert response.tier == FallbackTier.EPIC1_FALLBACK
        assert response.confidence == "low"
        assert "Advanced analysis unavailable" in response.limitations
        assert any("search results" in lim for lim in response.limitations)

    def test_format_full_workflow_response(self):
        """Test formatting of successful full workflow response."""
        # Arrange
        partial_results = [
            AgentResult(
                task_id="task_1",
                agent_type="retrieval",
                success=True,
                result="Retrieved docs",
                execution_time_ms=200,
            ),
            AgentResult(
                task_id="task_2",
                agent_type="analysis",
                success=True,
                result="Analyzed data",
                execution_time_ms=300,
            ),
            AgentResult(
                task_id="task_3",
                agent_type="synthesis",
                success=True,
                result="Final answer with citations",
                execution_time_ms=250,
            ),
        ]

        # Act
        response = format_fallback_response(
            query="Test query",
            tier=FallbackTier.FULL_WORKFLOW,
            partial_results=partial_results,
            error_message="",
            total_time_ms=750,
        )

        # Assert
        assert response.tier == FallbackTier.FULL_WORKFLOW
        assert response.confidence == "high"
        assert response.answer == "Final answer with citations"
        assert len(response.limitations) == 0


class TestHandleWorkflowFailure:
    """Tests for handle_workflow_failure() function (AC8: Task 4.2, 4.3, 4.4)."""

    @pytest.mark.asyncio
    async def test_handle_failure_with_partial_results(self):
        """Test fallback uses partial results when some agents succeeded."""
        # Arrange
        partial_results = [
            AgentResult(
                task_id="task_1",
                agent_type="retrieval",
                success=True,
                result="Retrieved docs",
                execution_time_ms=200,
            ),
            AgentResult(
                task_id="task_2",
                agent_type="analysis",
                success=False,
                result=None,
                execution_time_ms=100,
                error_message="Timeout",
            ),
        ]

        # Act
        response = await handle_workflow_failure(
            query="Test query",
            complexity=QueryComplexity.ANALYTICAL,
            partial_results=partial_results,
            error=TimeoutError("Analysis timed out"),
            total_time_ms=300,
        )

        # Assert
        assert response.tier == FallbackTier.PARTIAL_WORKFLOW
        assert "Retrieved docs" in response.answer
        assert len(response.partial_results) == 2

    @pytest.mark.asyncio
    @patch("raglite.agentic.fallback.fallback_to_basic_retrieval")
    async def test_handle_failure_falls_back_to_epic1(self, mock_fallback):
        """Test fallback to Epic 1 when all agents failed."""
        # Arrange
        mock_fallback.return_value = "Basic search result"
        partial_results = [
            AgentResult(
                task_id="task_1",
                agent_type="retrieval",
                success=False,
                result=None,
                execution_time_ms=100,
                error_message="Timeout",
            ),
        ]

        # Act
        response = await handle_workflow_failure(
            query="Test query",
            complexity=QueryComplexity.ANALYTICAL,
            partial_results=partial_results,
            error=RuntimeError("All agents failed"),
            total_time_ms=100,
        )

        # Assert
        assert response.tier == FallbackTier.EPIC1_FALLBACK
        assert response.answer == "Basic search result"
        mock_fallback.assert_called_once_with("Test query")

    @pytest.mark.asyncio
    @patch("raglite.agentic.fallback.fallback_to_basic_retrieval")
    async def test_handle_failure_handles_complete_failure(self, mock_fallback):
        """Test complete failure when even Epic 1 fallback fails."""
        # Arrange
        mock_fallback.side_effect = Exception("Database unavailable")

        # Act
        response = await handle_workflow_failure(
            query="Test query",
            complexity=QueryComplexity.ANALYTICAL,
            partial_results=[],
            error=RuntimeError("Workflow failed"),
            total_time_ms=50,
        )

        # Assert
        assert response.tier == FallbackTier.EPIC1_FALLBACK
        assert "technical difficulties" in response.answer
        assert "Complete system failure" in response.limitations


class TestWorkflowExecutorTimeoutIntegration:
    """Integration tests for WorkflowExecutor timeout handling (AC8)."""

    @pytest.mark.asyncio
    async def test_executor_handles_task_timeout(self):
        """Test WorkflowExecutor properly handles task timeout."""
        # Arrange
        executor = WorkflowExecutor()

        # Create a mock slow agent
        async def slow_agent(instruction: str, context: dict) -> str:
            await asyncio.sleep(20.0)  # Exceeds timeout
            return "Should not complete"

        # Mock the agent registry
        executor._agent_registry["retrieval"] = slow_agent

        task = AgentTask(
            task_id="task_1",
            agent_type="retrieval",
            instruction="Test instruction",
            depends_on=[],
        )

        # Act
        result = await executor._execute_task(task, {}, timeout_seconds=0.1)

        # Assert
        assert result.success is False
        assert "timeout" in result.error_message.lower()
        assert result.execution_time_ms >= 100  # At least timeout duration

    @pytest.mark.asyncio
    @patch("raglite.agentic.orchestrator.settings")
    async def test_executor_continues_after_timeout(self, mock_settings):
        """Test WorkflowExecutor continues with other tasks after a timeout."""
        # Arrange
        mock_settings.strands_agent_timeout_seconds = 0.1  # Very short timeout for test
        executor = WorkflowExecutor()

        # Create mock agents: one slow, one fast
        async def slow_agent(instruction: str, context: dict) -> str:
            await asyncio.sleep(10.0)  # Much longer than timeout
            return "Slow result"

        async def fast_agent(instruction: str, context: dict) -> str:
            await asyncio.sleep(0.01)
            return "Fast result"

        executor._agent_registry["retrieval"] = slow_agent
        executor._agent_registry["analysis"] = fast_agent

        # Create two independent tasks
        task1 = AgentTask(
            task_id="task_1",
            agent_type="retrieval",
            instruction="Slow task",
            depends_on=[],
        )
        task2 = AgentTask(
            task_id="task_2",
            agent_type="analysis",
            instruction="Fast task",
            depends_on=[],
        )

        from raglite.agentic.planner import WorkflowPlan

        plan = WorkflowPlan(
            query="Test query",
            complexity=QueryComplexity.ANALYTICAL,
            tasks=[task1, task2],
        )

        # Act
        results = await executor.execute_workflow(plan)

        # Assert
        assert len(results) == 2
        # Task 1 should fail (timeout)
        assert results[0].success is False
        assert "timeout" in results[0].error_message.lower()
        # Task 2 should succeed (fast)
        assert results[1].success is True
        assert results[1].result == "Fast result"
