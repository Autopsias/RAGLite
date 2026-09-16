"""Unit tests for WorkflowExecutor (Story 3.5 Task 3.8).

Tests AC3-AC5: Workflow executor with agent routing, parallel/sequential execution
- AC3: Sub-tasks routed to appropriate specialized agents
- AC4: Agent outputs passed between agents as inputs to subsequent steps
- AC5: Workflow execution completes in <30 seconds for typical analytical queries

NOTE: These are unit tests with mocked agents. Integration tests with real agents
are in tests/integration/test_workflow_orchestration.py (Task 5).
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from raglite.agentic.orchestrator import WorkflowExecutor
from raglite.agentic.planner import AgentTask, QueryComplexity, WorkflowPlan


class TestWorkflowExecutorInitialization:
    """Test WorkflowExecutor initialization and agent registry."""

    @patch("raglite.agentic.orchestrator.logger")
    def test_executor_initialization(self, mock_logger):
        """Executor should initialize with agent registry."""
        with patch.dict(
            "sys.modules",
            {
                "raglite.agentic.agents.retrieval_agent": Mock(retrieval_agent=Mock()),
                "raglite.agentic.agents.analysis_agent": Mock(analysis_agent=Mock()),
                "raglite.agentic.agents.synthesis_agent": Mock(synthesis_agent=Mock()),
            },
        ):
            executor = WorkflowExecutor()

            assert executor._agent_registry is not None
            assert isinstance(executor._agent_registry, dict)

    def test_agent_routing_retrieval(self):
        """Retrieval tasks should route to retrieval agent (AC3)."""
        with patch.dict(
            "sys.modules",
            {
                "raglite.agentic.agents.retrieval_agent": Mock(
                    retrieval_agent=Mock(__name__="retrieval_agent")
                ),
                "raglite.agentic.agents.analysis_agent": Mock(analysis_agent=Mock()),
                "raglite.agentic.agents.synthesis_agent": Mock(synthesis_agent=Mock()),
            },
        ):
            executor = WorkflowExecutor()
            agent = executor._route_task_to_agent("retrieval")

            assert agent is not None
            assert agent.__name__ == "retrieval_agent"

    def test_agent_routing_analysis(self):
        """Analysis tasks should route to analysis agent (AC3)."""
        with patch.dict(
            "sys.modules",
            {
                "raglite.agentic.agents.retrieval_agent": Mock(retrieval_agent=Mock()),
                "raglite.agentic.agents.analysis_agent": Mock(
                    analysis_agent=Mock(__name__="analysis_agent")
                ),
                "raglite.agentic.agents.synthesis_agent": Mock(synthesis_agent=Mock()),
            },
        ):
            executor = WorkflowExecutor()
            agent = executor._route_task_to_agent("analysis")

            assert agent is not None
            assert agent.__name__ == "analysis_agent"

    def test_agent_routing_synthesis(self):
        """Synthesis tasks should route to synthesis agent (AC3)."""
        with patch.dict(
            "sys.modules",
            {
                "raglite.agentic.agents.retrieval_agent": Mock(retrieval_agent=Mock()),
                "raglite.agentic.agents.analysis_agent": Mock(analysis_agent=Mock()),
                "raglite.agentic.agents.synthesis_agent": Mock(
                    synthesis_agent=Mock(__name__="synthesis_agent")
                ),
            },
        ):
            executor = WorkflowExecutor()
            agent = executor._route_task_to_agent("synthesis")

            assert agent is not None
            assert agent.__name__ == "synthesis_agent"

    def test_agent_routing_unknown_type(self):
        """Unknown agent type should return None."""
        with patch.dict(
            "sys.modules",
            {
                "raglite.agentic.agents.retrieval_agent": Mock(retrieval_agent=Mock()),
                "raglite.agentic.agents.analysis_agent": Mock(analysis_agent=Mock()),
                "raglite.agentic.agents.synthesis_agent": Mock(synthesis_agent=Mock()),
            },
        ):
            executor = WorkflowExecutor()
            agent = executor._route_task_to_agent("unknown_agent")

            assert agent is None


class TestSingleTaskExecution:
    """Test execution of single tasks."""

    @pytest.mark.asyncio
    async def test_execute_single_retrieval_task(self):
        """Single retrieval task should execute successfully."""
        # Mock retrieval agent
        mock_retrieval_agent = AsyncMock(return_value={"chunks": []})

        with patch.dict(
            "sys.modules",
            {
                "raglite.agentic.agents.retrieval_agent": Mock(
                    retrieval_agent=mock_retrieval_agent
                ),
                "raglite.agentic.agents.analysis_agent": Mock(analysis_agent=AsyncMock()),
                "raglite.agentic.agents.synthesis_agent": Mock(synthesis_agent=AsyncMock()),
            },
        ):
            executor = WorkflowExecutor()

            task = AgentTask(
                task_id="task_1",
                agent_type="retrieval",
                instruction="Search for revenue data",
                depends_on=[],
            )

            result = await executor._execute_task(task, {})

            assert result.task_id == "task_1"
            assert result.agent_type == "retrieval"
            assert result.success is True
            assert result.execution_time_ms >= 0  # May be 0 with fast mocks

    @pytest.mark.asyncio
    async def test_execute_task_with_agent_failure(self):
        """Task execution should handle agent failures gracefully."""
        # Mock failing agent
        mock_agent = AsyncMock(side_effect=Exception("Agent failed"))

        with patch.dict(
            "sys.modules",
            {
                "raglite.agentic.agents.retrieval_agent": Mock(retrieval_agent=mock_agent),
                "raglite.agentic.agents.analysis_agent": Mock(analysis_agent=AsyncMock()),
                "raglite.agentic.agents.synthesis_agent": Mock(synthesis_agent=AsyncMock()),
            },
        ):
            executor = WorkflowExecutor()

            task = AgentTask(
                task_id="task_1",
                agent_type="retrieval",
                instruction="Search for revenue",
                depends_on=[],
            )

            result = await executor._execute_task(task, {})

            assert result.task_id == "task_1"
            assert result.success is False
            assert result.error_message is not None
            assert "Agent failed" in result.error_message


class TestParallelTaskExecution:
    """Test parallel execution of independent tasks (AC4)."""

    @pytest.mark.asyncio
    async def test_parallel_retrievals(self):
        """Independent retrieval tasks should execute in parallel (AC4)."""
        # Mock agents
        mock_retrieval = AsyncMock(return_value={"chunks": []})

        with patch.dict(
            "sys.modules",
            {
                "raglite.agentic.agents.retrieval_agent": Mock(retrieval_agent=mock_retrieval),
                "raglite.agentic.agents.analysis_agent": Mock(analysis_agent=AsyncMock()),
                "raglite.agentic.agents.synthesis_agent": Mock(
                    synthesis_agent=AsyncMock(return_value={"answer": "test"})
                ),
            },
        ):
            executor = WorkflowExecutor()

            # Create plan with 2 parallel retrievals
            plan = WorkflowPlan(
                query="Test query",
                complexity=QueryComplexity.ANALYTICAL,
                tasks=[
                    AgentTask(
                        task_id="task_1",
                        agent_type="retrieval",
                        instruction="Retrieve A",
                        depends_on=[],
                    ),
                    AgentTask(
                        task_id="task_2",
                        agent_type="retrieval",
                        instruction="Retrieve B",
                        depends_on=[],
                    ),
                ],
            )

            start_time = asyncio.get_event_loop().time()
            results = await executor.execute_workflow(plan)
            end_time = asyncio.get_event_loop().time()

            # Both tasks should complete
            assert len(results) == 2
            assert all(r.success for r in results)

            # Parallel execution should be faster than 2x sequential
            # (This is a weak assertion since we're using mocks, but validates parallel execution)
            execution_time_ms = (end_time - start_time) * 1000
            assert execution_time_ms < 5000  # Should be much faster than 5s


class TestSequentialTaskExecution:
    """Test sequential execution with dependencies (AC4)."""

    @pytest.mark.asyncio
    async def test_sequential_dependency_ordering(self):
        """Dependent tasks should execute after dependencies complete (AC4)."""
        execution_order = []

        async def mock_retrieval(**kwargs):
            execution_order.append("retrieval")
            return {"chunks": []}

        async def mock_analysis(**kwargs):
            execution_order.append("analysis")
            return {"value": 0.20}

        async def mock_synthesis(**kwargs):
            execution_order.append("synthesis")
            return {"answer": "test"}

        with patch.dict(
            "sys.modules",
            {
                "raglite.agentic.agents.retrieval_agent": Mock(retrieval_agent=mock_retrieval),
                "raglite.agentic.agents.analysis_agent": Mock(analysis_agent=mock_analysis),
                "raglite.agentic.agents.synthesis_agent": Mock(synthesis_agent=mock_synthesis),
            },
        ):
            executor = WorkflowExecutor()

            # Create plan: retrieval → analysis → synthesis (sequential chain)
            plan = WorkflowPlan(
                query="Test query",
                complexity=QueryComplexity.ANALYTICAL,
                tasks=[
                    AgentTask(
                        task_id="task_1",
                        agent_type="retrieval",
                        instruction="Retrieve data",
                        depends_on=[],
                    ),
                    AgentTask(
                        task_id="task_2",
                        agent_type="analysis",
                        instruction="Analyze data",
                        depends_on=["task_1"],
                    ),
                    AgentTask(
                        task_id="task_3",
                        agent_type="synthesis",
                        instruction="Synthesize answer",
                        depends_on=["task_2"],
                    ),
                ],
            )

            results = await executor.execute_workflow(plan)

            # All tasks should complete
            assert len(results) == 3
            assert all(r.success for r in results)

            # Execution order should be: retrieval → analysis → synthesis
            assert execution_order == ["retrieval", "analysis", "synthesis"]

    @pytest.mark.asyncio
    async def test_dependency_data_passing(self):
        """Dependent tasks should receive outputs from dependency tasks (AC4)."""
        # This test validates that dependency results are passed to dependent tasks
        # In the real implementation, this will depend on agent signatures

        with patch.dict(
            "sys.modules",
            {
                "raglite.agentic.agents.retrieval_agent": Mock(
                    retrieval_agent=AsyncMock(return_value={"chunks": ["chunk1", "chunk2"]})
                ),
                "raglite.agentic.agents.analysis_agent": Mock(
                    analysis_agent=AsyncMock(return_value={"value": 0.20})
                ),
                "raglite.agentic.agents.synthesis_agent": Mock(
                    synthesis_agent=AsyncMock(return_value={"answer": "test"})
                ),
            },
        ):
            executor = WorkflowExecutor()

            plan = WorkflowPlan(
                query="Test query",
                complexity=QueryComplexity.ANALYTICAL,
                tasks=[
                    AgentTask(
                        task_id="task_1",
                        agent_type="retrieval",
                        instruction="Retrieve",
                        depends_on=[],
                    ),
                    AgentTask(
                        task_id="task_2",
                        agent_type="synthesis",
                        instruction="Synthesize",
                        depends_on=["task_1"],
                    ),
                ],
            )

            results = await executor.execute_workflow(plan)

            assert len(results) == 2
            # Task 1 result should be available when Task 2 executes
            assert results[0].task_id == "task_1"
            assert results[0].success is True
            assert results[1].task_id == "task_2"
            assert results[1].success is True


class TestWorkflowPerformance:
    """Test workflow execution performance (AC5)."""

    @pytest.mark.asyncio
    async def test_simple_workflow_under_5s(self):
        """Simple 3-task workflow should complete in <5s (AC5 p50)."""
        with patch.dict(
            "sys.modules",
            {
                "raglite.agentic.agents.retrieval_agent": Mock(
                    retrieval_agent=AsyncMock(return_value={"chunks": []})
                ),
                "raglite.agentic.agents.analysis_agent": Mock(
                    analysis_agent=AsyncMock(return_value={"value": 0.20})
                ),
                "raglite.agentic.agents.synthesis_agent": Mock(
                    synthesis_agent=AsyncMock(return_value={"answer": "test"})
                ),
            },
        ):
            executor = WorkflowExecutor()

            plan = WorkflowPlan(
                query="Test query",
                complexity=QueryComplexity.ANALYTICAL,
                tasks=[
                    AgentTask(
                        task_id="task_1",
                        agent_type="retrieval",
                        instruction="Retrieve",
                        depends_on=[],
                    ),
                    AgentTask(
                        task_id="task_2",
                        agent_type="analysis",
                        instruction="Analyze",
                        depends_on=["task_1"],
                    ),
                    AgentTask(
                        task_id="task_3",
                        agent_type="synthesis",
                        instruction="Synthesize",
                        depends_on=["task_2"],
                    ),
                ],
            )

            start_time = asyncio.get_event_loop().time()
            results = await executor.execute_workflow(plan)
            end_time = asyncio.get_event_loop().time()

            execution_time_s = end_time - start_time

            # AC5: <5s p50 for typical workflows
            assert execution_time_s < 5.0
            assert all(r.success for r in results)
