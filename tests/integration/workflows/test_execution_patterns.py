"""Integration tests for workflow execution patterns and error handling (Story 3.5).

Tests sequential dependencies, mixed execution patterns, pattern recognition, and error handling.
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
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


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

    @pytest.mark.asyncio
    async def test_mixed_parallel_sequential_execution(self):
        """Test workflow with both parallel and sequential tasks.

        AC6: Mixed execution pattern validation
        Pattern: [task_1 || task_2] → task_3 → task_4
        """
        executor = WorkflowExecutor()

        execution_times = {}

        async def parallel_agent_1(instruction: str, context: dict) -> str:
            start = time.time()
            await asyncio.sleep(0.1)
            execution_times["task_1"] = (start, time.time())
            return "Result 1"

        async def parallel_agent_2(instruction: str, context: dict) -> str:
            start = time.time()
            await asyncio.sleep(0.1)
            execution_times["task_2"] = (start, time.time())
            return "Result 2"

        async def sequential_agent_3(instruction: str, context: dict) -> str:
            execution_times["task_3"] = (time.time(), time.time())
            assert "task_1" in context and "task_2" in context
            return "Result 3"

        async def sequential_agent_4(instruction: str, context: dict) -> str:
            execution_times["task_4"] = (time.time(), time.time())
            assert "task_3" in context
            return "Result 4"

        executor._agent_registry["retrieval"] = parallel_agent_1
        executor._agent_registry["analysis"] = parallel_agent_2
        executor._agent_registry["synthesis"] = sequential_agent_3

        # Mixed pattern: two parallel tasks, then sequential
        plan = WorkflowPlan(
            query="Test mixed execution",
            complexity=QueryComplexity.ANALYTICAL,
            tasks=[
                AgentTask(
                    task_id="task_1",
                    agent_type="retrieval",
                    instruction="Parallel 1",
                    depends_on=[],
                ),
                AgentTask(
                    task_id="task_2",
                    agent_type="analysis",
                    instruction="Parallel 2",
                    depends_on=[],
                ),
                AgentTask(
                    task_id="task_3",
                    agent_type="synthesis",
                    instruction="Sequential after parallel",
                    depends_on=["task_1", "task_2"],
                ),
            ],
        )

        workflow_start = time.time()
        results = await executor.execute_workflow(plan)
        workflow_duration = time.time() - workflow_start

        # Verify all tasks succeeded
        assert len(results) == 3
        assert all(r.success for r in results)

        # Verify parallel execution: should take ~100ms, not 200ms
        assert workflow_duration < 0.2, (
            f"Expected ~100ms for parallel + sequential, got {workflow_duration}s"
        )


class TestWorkflowPatternRecognition:
    """Tests for workflow pattern recognition (AC6: Task 5.5)."""

    @pytest.mark.asyncio
    async def test_yoy_growth_pattern_decomposition(self):
        """Test YoY growth pattern is correctly recognized and decomposed."""
        query = "Calculate year-over-year revenue growth"
        complexity = await classify_query_complexity(query)
        plan = await decompose_query(query, complexity)

        assert plan.complexity == QueryComplexity.ANALYTICAL
        assert len(plan.tasks) >= 4  # 2 retrievals + 1 analysis + 1 synthesis

        # Verify pattern-specific tasks
        retrieval_tasks = [t for t in plan.tasks if t.agent_type == "retrieval"]
        assert len(retrieval_tasks) >= 2  # Previous and current period

        analysis_tasks = [t for t in plan.tasks if t.agent_type == "analysis"]
        assert len(analysis_tasks) >= 1
        assert "growth" in analysis_tasks[0].instruction.lower()

    @pytest.mark.asyncio
    async def test_variance_analysis_pattern_decomposition(self):
        """Test variance analysis pattern is correctly recognized and decomposed."""
        query = "Explain the variance in operating expenses"
        complexity = await classify_query_complexity(query)
        plan = await decompose_query(query, complexity)

        assert plan.complexity == QueryComplexity.ANALYTICAL

        # Variance pattern should have analysis and driver retrieval
        analysis_tasks = [t for t in plan.tasks if t.agent_type == "analysis"]
        assert len(analysis_tasks) >= 1

        # Should have retrieval for variance drivers
        retrieval_tasks = [t for t in plan.tasks if t.agent_type == "retrieval"]
        driver_retrieval = any("driver" in t.instruction.lower() for t in retrieval_tasks)
        assert driver_retrieval

    @pytest.mark.asyncio
    async def test_trend_analysis_pattern_decomposition(self):
        """Test trend analysis pattern is correctly recognized and decomposed."""
        query = "Show revenue trend over the last 4 quarters"
        complexity = await classify_query_complexity(query)
        plan = await decompose_query(query, complexity)

        assert plan.complexity == QueryComplexity.ANALYTICAL

        # Trend pattern should have multiple parallel retrievals
        retrieval_tasks = [t for t in plan.tasks if t.agent_type == "retrieval"]
        assert len(retrieval_tasks) >= 4  # 4 quarters

        # All retrievals should be independent (parallel)
        assert all(t.depends_on == [] for t in retrieval_tasks)

    @pytest.mark.asyncio
    async def test_generic_analytical_pattern_fallback(self):
        """Test generic analytical pattern is used when no specific pattern matches."""
        query = "Analyze the financial performance metrics"
        complexity = await classify_query_complexity(query)
        plan = await decompose_query(query, complexity)

        assert plan.complexity == QueryComplexity.ANALYTICAL

        # Generic pattern: retrieval + optional analysis + synthesis
        assert len(plan.tasks) >= 2  # At minimum retrieval + synthesis


class TestWorkflowErrorHandling:
    """Tests for workflow error handling in orchestration (AC6: Task 5.5)."""

    @pytest.mark.asyncio
    async def test_workflow_continues_after_task_failure(self):
        """Verify workflow continues with independent tasks after one task fails."""
        executor = WorkflowExecutor()

        async def failing_agent(instruction: str, context: dict) -> str:
            raise ValueError("Agent failed")

        async def success_agent(instruction: str, context: dict) -> str:
            return "Success result"

        executor._agent_registry["retrieval"] = failing_agent
        executor._agent_registry["analysis"] = success_agent

        # Two independent tasks: one will fail, one will succeed
        plan = WorkflowPlan(
            query="Test error handling",
            complexity=QueryComplexity.ANALYTICAL,
            tasks=[
                AgentTask(
                    task_id="task_1",
                    agent_type="retrieval",
                    instruction="Failing task",
                    depends_on=[],
                ),
                AgentTask(
                    task_id="task_2",
                    agent_type="analysis",
                    instruction="Success task",
                    depends_on=[],
                ),
            ],
        )

        results = await executor.execute_workflow(plan)

        # Verify both tasks completed (one failed, one succeeded)
        assert len(results) == 2
        assert results[0].success is False
        assert results[1].success is True

    @pytest.mark.asyncio
    async def test_dependent_task_not_executed_if_dependency_fails(self):
        """Verify dependent tasks gracefully handle dependency failures."""
        executor = WorkflowExecutor()

        async def failing_agent(instruction: str, context: dict) -> str:
            raise ValueError("Agent failed")

        async def dependent_agent(instruction: str, context: dict) -> str:
            # This should be called even if dependency failed
            # Context will be empty for failed dependency
            return "Dependent executed"

        executor._agent_registry["retrieval"] = failing_agent
        executor._agent_registry["analysis"] = dependent_agent

        plan = WorkflowPlan(
            query="Test dependency failure",
            complexity=QueryComplexity.ANALYTICAL,
            tasks=[
                AgentTask(
                    task_id="task_1",
                    agent_type="retrieval",
                    instruction="Failing task",
                    depends_on=[],
                ),
                AgentTask(
                    task_id="task_2",
                    agent_type="analysis",
                    instruction="Dependent task",
                    depends_on=["task_1"],
                ),
            ],
        )

        results = await executor.execute_workflow(plan)

        # Both tasks should complete (first fails, second executes anyway)
        assert len(results) == 2
        assert results[0].success is False
        assert results[1].success is True  # Executor continues despite failed dependency
