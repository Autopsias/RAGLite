"""Unit tests for workflow decomposition (Story 3.5 Task 2.6-2.7).

Tests AC2: Workflow planner decomposes complex queries into sub-tasks with dependencies
- Input: Analytical query (string)
- Output: WorkflowPlan with List[AgentTask] including task_id, agent_type, instruction, depends_on
- Example: "Calculate YoY revenue growth and explain variance" → 5 tasks
- Decomposition validates that all required data is retrieved before analysis
- Task dependency DAG has no circular dependencies
"""

import pytest

from raglite.agentic.planner import (
    AgentTask,
    QueryComplexity,
    WorkflowPlan,
    _has_circular_dependencies,
    decompose_query,
)


class TestCircularDependencyDetection:
    """Test circular dependency validation (AC2)."""

    def test_no_circular_dependencies_linear(self):
        """Linear task chain should have no circular dependencies."""
        tasks = [
            AgentTask(
                task_id="task_1",
                agent_type="retrieval",
                instruction="Get data",
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
        ]
        assert not _has_circular_dependencies(tasks)

    def test_no_circular_dependencies_parallel(self):
        """Parallel tasks with common downstream dependency should be valid."""
        tasks = [
            AgentTask(
                task_id="task_1",
                agent_type="retrieval",
                instruction="Get A",
                depends_on=[],
            ),
            AgentTask(
                task_id="task_2",
                agent_type="retrieval",
                instruction="Get B",
                depends_on=[],
            ),
            AgentTask(
                task_id="task_3",
                agent_type="analysis",
                instruction="Analyze",
                depends_on=["task_1", "task_2"],
            ),
        ]
        assert not _has_circular_dependencies(tasks)

    def test_circular_dependency_detected_simple(self):
        """Simple circular dependency (A→B→A) should be detected."""
        tasks = [
            AgentTask(
                task_id="task_1",
                agent_type="retrieval",
                instruction="Get A",
                depends_on=["task_2"],
            ),
            AgentTask(
                task_id="task_2",
                agent_type="analysis",
                instruction="Analyze",
                depends_on=["task_1"],
            ),
        ]
        assert _has_circular_dependencies(tasks)

    def test_circular_dependency_detected_complex(self):
        """Complex circular dependency (A→B→C→A) should be detected."""
        tasks = [
            AgentTask(
                task_id="task_1",
                agent_type="retrieval",
                instruction="Get A",
                depends_on=["task_3"],
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
        ]
        assert _has_circular_dependencies(tasks)

    def test_self_referencing_dependency_detected(self):
        """Self-referencing task (A→A) should be detected as circular."""
        tasks = [
            AgentTask(
                task_id="task_1",
                agent_type="retrieval",
                instruction="Get A",
                depends_on=["task_1"],
            ),
        ]
        assert _has_circular_dependencies(tasks)


class TestSimpleQueryDecomposition:
    """Test decomposition of simple queries."""

    @pytest.mark.asyncio
    async def test_simple_query_single_retrieval(self):
        """Simple query should decompose to single retrieval task."""
        query = "What is Q3 revenue?"
        plan = await decompose_query(query, QueryComplexity.SIMPLE)

        assert isinstance(plan, WorkflowPlan)
        assert plan.query == query
        assert plan.complexity == QueryComplexity.SIMPLE
        assert len(plan.tasks) == 1
        assert plan.tasks[0].agent_type == "retrieval"
        assert plan.tasks[0].depends_on == []

    @pytest.mark.asyncio
    async def test_simple_query_metadata(self):
        """Simple query plan should have correct metadata."""
        query = "List expenses"
        plan = await decompose_query(query, QueryComplexity.SIMPLE)

        assert "pattern" in plan.metadata
        assert plan.metadata["pattern"] == "simple"
        assert plan.metadata["task_count"] == 1


class TestYoYGrowthWorkflow:
    """Test YoY growth workflow pattern (AC6 example)."""

    @pytest.mark.asyncio
    async def test_yoy_growth_basic(self):
        """YoY growth query should decompose to retrieval + analysis + synthesis."""
        query = "Calculate YoY revenue growth"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        assert len(plan.tasks) == 4  # 2 retrievals + 1 analysis + 1 synthesis
        assert plan.tasks[0].agent_type == "retrieval"  # Previous period
        assert plan.tasks[1].agent_type == "retrieval"  # Current period
        assert plan.tasks[2].agent_type == "analysis"  # YoY calculation
        assert plan.tasks[3].agent_type == "synthesis"  # Final answer

    @pytest.mark.asyncio
    async def test_yoy_growth_with_variance_explanation(self):
        """YoY growth + variance explanation should add driver retrieval (AC6)."""
        query = "Calculate YoY revenue growth and explain variance"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        # AC6 example: 5 tasks expected
        assert len(plan.tasks) == 5
        assert plan.tasks[0].agent_type == "retrieval"  # Previous period
        assert plan.tasks[1].agent_type == "retrieval"  # Current period
        assert plan.tasks[2].agent_type == "analysis"  # YoY %
        assert plan.tasks[3].agent_type == "retrieval"  # Variance drivers
        assert plan.tasks[4].agent_type == "synthesis"  # Final answer

    @pytest.mark.asyncio
    async def test_yoy_parallel_retrievals(self):
        """YoY retrievals should be parallel (no dependencies on each other)."""
        query = "Calculate YoY revenue growth"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        # Task 1 and Task 2 should both have no dependencies (parallel)
        assert plan.tasks[0].depends_on == []
        assert plan.tasks[1].depends_on == []

    @pytest.mark.asyncio
    async def test_yoy_analysis_depends_on_retrievals(self):
        """YoY analysis task should depend on both retrieval tasks."""
        query = "Calculate YoY revenue growth"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        analysis_task = plan.tasks[2]  # Third task is analysis
        assert "task_1" in analysis_task.depends_on
        assert "task_2" in analysis_task.depends_on

    @pytest.mark.asyncio
    async def test_yoy_synthesis_depends_on_all(self):
        """YoY synthesis should depend on all previous tasks."""
        query = "Calculate YoY revenue growth and explain variance"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        synthesis_task = plan.tasks[4]  # Fifth task is synthesis
        assert "task_1" in synthesis_task.depends_on
        assert "task_2" in synthesis_task.depends_on
        assert "task_3" in synthesis_task.depends_on
        assert "task_4" in synthesis_task.depends_on


class TestVarianceAnalysisWorkflow:
    """Test variance analysis workflow pattern."""

    @pytest.mark.asyncio
    async def test_variance_analysis_basic(self):
        """Variance analysis should retrieve data, analyze, retrieve drivers, synthesize."""
        query = "Explain the variance in expenses"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        assert len(plan.tasks) >= 4  # At least: retrieval + analysis + drivers + synthesis
        assert any(task.agent_type == "retrieval" for task in plan.tasks)
        assert any(task.agent_type == "analysis" for task in plan.tasks)
        assert any(task.agent_type == "synthesis" for task in plan.tasks)

    @pytest.mark.asyncio
    async def test_variance_analysis_with_comparison(self):
        """Variance with comparison should have 2 parallel retrievals."""
        query = "Compare Q3 2023 and Q3 2024 expenses and explain variance"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        # Should have 2 retrieval tasks (current + comparison period)
        retrieval_tasks = [
            t for t in plan.tasks if t.agent_type == "retrieval" and not t.depends_on
        ]
        assert len(retrieval_tasks) == 2  # Both parallel


class TestTrendAnalysisWorkflow:
    """Test trend analysis workflow pattern."""

    @pytest.mark.asyncio
    async def test_trend_analysis_default_periods(self):
        """Trend analysis should default to 4 periods if not specified."""
        query = "What is the trend in revenue over time?"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        # Should have 4 retrieval tasks (default quarters) + 1 analysis + 1 synthesis
        retrieval_tasks = [t for t in plan.tasks if t.agent_type == "retrieval"]
        assert len(retrieval_tasks) == 4

    @pytest.mark.asyncio
    async def test_trend_analysis_specified_periods(self):
        """Trend analysis should extract number of periods from query."""
        query = "What is the revenue trend over 6 quarters?"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        # Should have 6 retrieval tasks
        retrieval_tasks = [t for t in plan.tasks if t.agent_type == "retrieval"]
        assert len(retrieval_tasks) == 6

    @pytest.mark.asyncio
    async def test_trend_parallel_retrievals(self):
        """Trend retrieval tasks should be parallel."""
        query = "Show me the trend over 3 months"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        # All retrieval tasks should have no dependencies
        retrieval_tasks = [t for t in plan.tasks if t.agent_type == "retrieval"]
        for task in retrieval_tasks:
            assert task.depends_on == []


class TestGenericAnalyticalWorkflow:
    """Test generic analytical fallback pattern."""

    @pytest.mark.asyncio
    async def test_generic_analytical_with_calculation(self):
        """Generic analytical query with calculation keyword."""
        query = "Calculate the profit margin"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        # Should have retrieval + analysis + synthesis
        assert len(plan.tasks) == 3
        assert plan.tasks[0].agent_type == "retrieval"
        assert plan.tasks[1].agent_type == "analysis"
        assert plan.tasks[2].agent_type == "synthesis"

    @pytest.mark.asyncio
    async def test_generic_analytical_without_calculation(self):
        """Generic analytical query without calculation (e.g., impact assessment)."""
        query = "What is the impact of marketing spend?"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        # Should have retrieval + synthesis (no analysis)
        assert len(plan.tasks) == 2
        assert plan.tasks[0].agent_type == "retrieval"
        assert plan.tasks[1].agent_type == "synthesis"


class TestWorkflowPlanValidation:
    """Test workflow plan validation and metadata."""

    @pytest.mark.asyncio
    async def test_task_ids_unique(self):
        """All task IDs in plan should be unique."""
        query = "Calculate YoY revenue growth and explain variance"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        task_ids = [task.task_id for task in plan.tasks]
        assert len(task_ids) == len(set(task_ids))  # All unique

    @pytest.mark.asyncio
    async def test_dependency_references_valid(self):
        """Task dependencies should reference valid task IDs."""
        query = "Calculate YoY revenue growth"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        task_ids = {task.task_id for task in plan.tasks}
        for task in plan.tasks:
            for dep_id in task.depends_on:
                assert dep_id in task_ids, f"Invalid dependency: {dep_id} not in task list"

    @pytest.mark.asyncio
    async def test_no_circular_dependencies_in_plan(self):
        """Generated workflow plan should never have circular dependencies."""
        queries = [
            "Calculate YoY revenue growth",
            "Explain the variance in expenses",
            "What is the trend over 4 quarters?",
            "Calculate profit margin",
        ]

        for query in queries:
            plan = await decompose_query(query, QueryComplexity.ANALYTICAL)
            assert not _has_circular_dependencies(plan.tasks)

    @pytest.mark.asyncio
    async def test_plan_metadata_populated(self):
        """Workflow plan should have metadata (task count, estimated time)."""
        query = "Calculate YoY revenue growth"
        plan = await decompose_query(query, QueryComplexity.ANALYTICAL)

        assert "task_count" in plan.metadata
        assert plan.metadata["task_count"] == len(plan.tasks)
        assert "estimated_time_ms" in plan.metadata
        assert plan.metadata["estimated_time_ms"] > 0
