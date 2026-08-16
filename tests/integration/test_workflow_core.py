"""Integration tests for multi-step workflow orchestration (Story 3.5 Task 5) - Core tests.

Tests AC6: End-to-end workflow orchestration validation.
These tests validate the complete workflow pipeline:
1. Query classification (classify_query_complexity)
2. Query decomposition (decompose_query)
3. Workflow execution (WorkflowExecutor.execute_workflow)
4. Result validation

NOTE: These are integration tests that require actual agent implementations
to be available. Mock agents are used to simulate real agent behavior.
"""

import asyncio
import time

import pytest

from raglite.agentic.orchestrator import WorkflowExecutor
from raglite.agentic.planner import (
    AgentTask,
    QueryComplexity,
    WorkflowPlan,
    classify_query_complexity,
    decompose_query,
)

# Mark all tests in this module as integration tests that preserve collection state
# Mark as slow due to PDF ingestion taking 60+ seconds per test
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


class TestEndToEndWorkflowOrchestration:
    """End-to-end workflow orchestration tests (AC6: Task 5.2)."""

    @pytest.mark.asyncio
    async def test_simple_query_workflow_end_to_end(self):
        """Test complete workflow for simple query: classify → decompose → execute.

        AC6: End-to-end workflow validation (simple query path)
        """
        # Step 1: Classify query
        query = "What was Q3 revenue?"
        complexity = await classify_query_complexity(query)

        assert complexity == QueryComplexity.SIMPLE

        # Step 2: Decompose query
        plan = await decompose_query(query, complexity)

        assert plan.complexity == QueryComplexity.SIMPLE
        assert len(plan.tasks) == 1
        assert plan.tasks[0].agent_type == "retrieval"

        # Step 3: Execute workflow with mock agent
        executor = WorkflowExecutor()

        async def mock_retrieval_agent(instruction: str, context: dict) -> str:
            return "Q3 2023 revenue: $150M (Source: Financial Report Q3 2023, Page 5)"

        executor._agent_registry["retrieval"] = mock_retrieval_agent

        results = await executor.execute_workflow(plan)

        # Step 4: Verify results
        assert len(results) == 1
        assert results[0].success is True
        assert "Q3 2023 revenue" in results[0].result
        assert results[0].agent_type == "retrieval"

    @pytest.mark.asyncio
    async def test_analytical_query_workflow_end_to_end(self):
        """Test complete workflow for analytical query with multiple agents.

        AC6: End-to-end workflow validation (analytical query path)
        """
        # Step 1: Classify query
        query = "Calculate YoY revenue growth and explain variance"
        complexity = await classify_query_complexity(query)

        assert complexity == QueryComplexity.ANALYTICAL

        # Step 2: Decompose query
        plan = await decompose_query(query, complexity)

        assert plan.complexity == QueryComplexity.ANALYTICAL
        assert len(plan.tasks) >= 4  # YoY pattern: 2 retrievals + 1 analysis + 1 synthesis

        # Step 3: Execute workflow with mock agents
        executor = WorkflowExecutor()

        async def mock_retrieval_agent(instruction: str, context: dict) -> str:
            if "previous period" in instruction:
                return "Q3 2022 revenue: $140M"
            else:
                return "Q3 2023 revenue: $150M"

        async def mock_analysis_agent(instruction: str, context: dict) -> str:
            return "YoY growth: 7.14% ($10M increase from $140M to $150M)"

        async def mock_synthesis_agent(instruction: str, context: dict) -> str:
            return "Q3 2023 revenue grew 7.14% year-over-year from $140M to $150M, representing a $10M increase."

        executor._agent_registry["retrieval"] = mock_retrieval_agent
        executor._agent_registry["analysis"] = mock_analysis_agent
        executor._agent_registry["synthesis"] = mock_synthesis_agent

        results = await executor.execute_workflow(plan)

        # Step 4: Verify results
        assert len(results) >= 4
        assert all(r.success for r in results), (
            f"Some tasks failed: {[r.error_message for r in results if not r.success]}"
        )

        # Verify final synthesis result
        synthesis_result = next(r for r in reversed(results) if r.agent_type == "synthesis")
        assert "7.14%" in synthesis_result.result
        assert "$150M" in synthesis_result.result


class TestParallelTaskExecution:
    """Tests for parallel task execution (AC6: Task 5.3)."""

    @pytest.mark.asyncio
    async def test_independent_tasks_execute_in_parallel(self):
        """Verify independent tasks execute concurrently, not sequentially.

        AC6: Parallel execution validation
        """
        executor = WorkflowExecutor()

        # Track execution timestamps
        execution_times = {}

        async def slow_agent_1(instruction: str, context: dict) -> str:
            start = time.time()
            await asyncio.sleep(0.2)  # 200ms
            execution_times["task_1"] = (start, time.time())
            return "Result 1"

        async def slow_agent_2(instruction: str, context: dict) -> str:
            start = time.time()
            await asyncio.sleep(0.2)  # 200ms
            execution_times["task_2"] = (start, time.time())
            return "Result 2"

        executor._agent_registry["retrieval"] = slow_agent_1
        executor._agent_registry["analysis"] = slow_agent_2

        # Create two independent tasks (no dependencies)
        plan = WorkflowPlan(
            query="Test parallel execution",
            complexity=QueryComplexity.ANALYTICAL,
            tasks=[
                AgentTask(
                    task_id="task_1",
                    agent_type="retrieval",
                    instruction="Parallel task 1",
                    depends_on=[],
                ),
                AgentTask(
                    task_id="task_2",
                    agent_type="analysis",
                    instruction="Parallel task 2",
                    depends_on=[],
                ),
            ],
        )

        workflow_start = time.time()
        results = await executor.execute_workflow(plan)
        workflow_duration = time.time() - workflow_start

        # Verify results
        assert len(results) == 2
        assert all(r.success for r in results)

        # Verify parallel execution: total time should be ~200ms, not ~400ms
        # Allow some overhead, but should be significantly less than sequential (400ms)
        assert workflow_duration < 0.35, (
            f"Workflow took {workflow_duration}s, expected <350ms for parallel execution"
        )

        # Verify tasks overlapped in time
        task_1_start, task_1_end = execution_times["task_1"]
        task_2_start, task_2_end = execution_times["task_2"]

        # Check for temporal overlap (parallel execution)
        overlap = min(task_1_end, task_2_end) - max(task_1_start, task_2_start)
        assert overlap > 0.1, f"Tasks did not overlap sufficiently (overlap: {overlap}s)"

    @pytest.mark.asyncio
    async def test_yoy_pattern_parallel_retrieval(self):
        """Test YoY growth pattern executes two retrievals in parallel.

        AC6: Pattern-specific parallel execution validation
        """
        query = "Calculate YoY revenue growth"
        complexity = await classify_query_complexity(query)
        plan = await decompose_query(query, complexity)

        # Verify YoY pattern was detected
        assert plan.complexity == QueryComplexity.ANALYTICAL

        # Find the two retrieval tasks (should be independent)
        retrieval_tasks = [t for t in plan.tasks if t.agent_type == "retrieval"]
        assert len(retrieval_tasks) >= 2

        # Verify both retrievals have no dependencies (can run in parallel)
        assert retrieval_tasks[0].depends_on == []
        assert retrieval_tasks[1].depends_on == []


class TestSequentialDependencyExecution:
    """Tests for sequential dependency execution (AC6: Task 5.4)."""

    @pytest.mark.asyncio
    async def test_dependent_tasks_execute_in_order(self):
        """Verify dependent tasks execute sequentially after dependencies complete.

        AC6: Sequential dependency validation
        """
        executor = WorkflowExecutor()

        # Track execution order
        execution_order = []

        async def agent_1(instruction: str, context: dict) -> str:
            execution_order.append("task_1")
            await asyncio.sleep(0.05)
            return "Result 1"

        async def agent_2(instruction: str, context: dict) -> str:
            execution_order.append("task_2")
            # Verify dependency result is available in context
            assert "task_1" in context
            assert context["task_1"] == "Result 1"
            await asyncio.sleep(0.05)
            return "Result 2"

        async def agent_3(instruction: str, context: dict) -> str:
            execution_order.append("task_3")
            # Verify both dependencies available
            assert "task_1" in context
            assert "task_2" in context
            return "Result 3"

        executor._agent_registry["retrieval"] = agent_1
        executor._agent_registry["analysis"] = agent_2
        executor._agent_registry["synthesis"] = agent_3

        # Create sequential dependency chain: task_1 → task_2 → task_3
        plan = WorkflowPlan(
            query="Test sequential execution",
            complexity=QueryComplexity.ANALYTICAL,
            tasks=[
                AgentTask(
                    task_id="task_1",
                    agent_type="retrieval",
                    instruction="First task",
                    depends_on=[],
                ),
                AgentTask(
                    task_id="task_2",
                    agent_type="analysis",
                    instruction="Second task",
                    depends_on=["task_1"],
                ),
                AgentTask(
                    task_id="task_3",
                    agent_type="synthesis",
                    instruction="Third task",
                    depends_on=["task_1", "task_2"],
                ),
            ],
        )

        results = await executor.execute_workflow(plan)

        # Verify results
        assert len(results) == 3
        assert all(r.success for r in results)

        # Verify execution order
        assert execution_order == ["task_1", "task_2", "task_3"]
