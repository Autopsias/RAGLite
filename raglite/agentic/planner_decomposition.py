"""Query decomposition and workflow pattern detection."""

import logging
import re

from raglite.agentic.planner_models import AgentTask, QueryComplexity, WorkflowPlan

logger = logging.getLogger(__name__)


def _build_simple_workflow(query: str) -> list[AgentTask]:
    """Build simple single-task workflow."""
    return [
        AgentTask(
            task_id="task_1",
            agent_type="retrieval",
            instruction=f"Search documents for: {query}",
            depends_on=[],
        )
    ]


def _build_yoy_growth_workflow(query: str, query_lower: str) -> list[AgentTask]:
    """Build YoY growth analysis workflow pattern."""
    logger.info("Detected YoY growth pattern", extra={"pattern": "yoy_growth"})

    current_period = "current period"
    previous_period = "previous period"
    tasks: list[AgentTask] = []

    # Task 1: Retrieve previous period data
    tasks.append(
        AgentTask(
            task_id="task_1",
            agent_type="retrieval",
            instruction=f"Retrieve revenue data for {previous_period}",
            depends_on=[],
            metadata={"period": previous_period},
        )
    )

    # Task 2: Retrieve current period data (parallel with task 1)
    tasks.append(
        AgentTask(
            task_id="task_2",
            agent_type="retrieval",
            instruction=f"Retrieve revenue data for {current_period}",
            depends_on=[],
            metadata={"period": current_period},
        )
    )

    # Task 3: Calculate YoY growth percentage
    tasks.append(
        AgentTask(
            task_id="task_3",
            agent_type="analysis",
            instruction="Calculate year-over-year revenue growth percentage",
            depends_on=["task_1", "task_2"],
            metadata={"calculation_type": "yoy_percentage"},
        )
    )

    # Task 4: Retrieve variance drivers if "explain" keyword present
    if "explain" in query_lower or "driver" in query_lower or "variance" in query_lower:
        tasks.append(
            AgentTask(
                task_id="task_4",
                agent_type="retrieval",
                instruction="Retrieve revenue variance drivers and contributing factors",
                depends_on=["task_3"],
                metadata={"type": "variance_drivers"},
            )
        )
        # Task 5: Synthesize final answer with all sources
        tasks.append(
            AgentTask(
                task_id="task_5",
                agent_type="synthesis",
                instruction=f"Synthesize final answer for: {query}",
                depends_on=["task_1", "task_2", "task_3", "task_4"],
            )
        )
    else:
        # Task 4: Synthesize without variance drivers
        tasks.append(
            AgentTask(
                task_id="task_4",
                agent_type="synthesis",
                instruction=f"Synthesize final answer for: {query}",
                depends_on=["task_1", "task_2", "task_3"],
            )
        )

    return tasks


def _build_variance_analysis_workflow(query: str, query_lower: str) -> list[AgentTask]:
    """Build variance analysis workflow pattern."""
    logger.info("Detected variance analysis pattern", extra={"pattern": "variance_analysis"})
    tasks: list[AgentTask] = []

    # Task 1: Retrieve current data
    tasks.append(
        AgentTask(
            task_id="task_1",
            agent_type="retrieval",
            instruction="Retrieve current period financial data",
            depends_on=[],
        )
    )

    # Task 2: Retrieve comparison period data (if comparative query)
    if re.search(r"compare|versus|vs\b|between", query_lower):
        tasks.append(
            AgentTask(
                task_id="task_2",
                agent_type="retrieval",
                instruction="Retrieve comparison period financial data",
                depends_on=[],
            )
        )
        analysis_deps = ["task_1", "task_2"]
        task_id_offset = 2
    else:
        analysis_deps = ["task_1"]
        task_id_offset = 1

    # Task N+1: Analyze variance
    tasks.append(
        AgentTask(
            task_id=f"task_{task_id_offset + 1}",
            agent_type="analysis",
            instruction="Calculate variance and identify magnitude of change",
            depends_on=analysis_deps,
            metadata={"calculation_type": "variance"},
        )
    )

    # Task N+2: Retrieve drivers
    tasks.append(
        AgentTask(
            task_id=f"task_{task_id_offset + 2}",
            agent_type="retrieval",
            instruction="Retrieve variance drivers, budget changes, and contributing factors",
            depends_on=[f"task_{task_id_offset + 1}"],
        )
    )

    # Task N+3: Synthesize
    all_task_ids = [task.task_id for task in tasks]
    tasks.append(
        AgentTask(
            task_id=f"task_{task_id_offset + 3}",
            agent_type="synthesis",
            instruction=f"Synthesize final answer for: {query}",
            depends_on=all_task_ids,
        )
    )

    return tasks


def _build_trend_analysis_workflow(query: str, query_lower: str) -> list[AgentTask]:
    """Build trend analysis workflow pattern."""
    logger.info("Detected trend analysis pattern", extra={"pattern": "trend_analysis"})
    tasks: list[AgentTask] = []

    # Detect number of periods (default 4 quarters if not specified)
    num_periods = 4
    period_match = re.search(r"(\d+)\s*(quarter|month|year)", query_lower)
    if period_match:
        num_periods = int(period_match.group(1))

    # Tasks 1-N: Parallel retrieval for each period
    for i in range(num_periods):
        tasks.append(
            AgentTask(
                task_id=f"task_{i + 1}",
                agent_type="retrieval",
                instruction=f"Retrieve data for period {i + 1}",
                depends_on=[],
                metadata={"period_index": i + 1},
            )
        )

    # Task N+1: Analyze trend
    retrieval_task_ids = [f"task_{i + 1}" for i in range(num_periods)]
    tasks.append(
        AgentTask(
            task_id=f"task_{num_periods + 1}",
            agent_type="analysis",
            instruction="Identify trend pattern (growth, decline, cyclical, stable)",
            depends_on=retrieval_task_ids,
            metadata={"calculation_type": "trend_analysis"},
        )
    )

    # Task N+2: Synthesize
    all_task_ids = [task.task_id for task in tasks]
    tasks.append(
        AgentTask(
            task_id=f"task_{num_periods + 2}",
            agent_type="synthesis",
            instruction=f"Synthesize final answer for: {query}",
            depends_on=all_task_ids,
        )
    )

    return tasks


def _build_generic_analytical_workflow(query: str, query_lower: str) -> list[AgentTask]:
    """Build generic analytical workflow pattern (fallback)."""
    logger.info("Using generic analytical pattern", extra={"pattern": "generic_analytical"})
    tasks: list[AgentTask] = []

    # Task 1: Retrieve relevant data
    tasks.append(
        AgentTask(
            task_id="task_1",
            agent_type="retrieval",
            instruction=f"Retrieve relevant financial data for: {query}",
            depends_on=[],
        )
    )

    # Task 2: Analyze if calculation/analysis keywords present
    if re.search(r"calculate|analyze|assess|evaluate", query_lower):
        tasks.append(
            AgentTask(
                task_id="task_2",
                agent_type="analysis",
                instruction=f"Perform financial analysis for: {query}",
                depends_on=["task_1"],
            )
        )
        synthesis_deps = ["task_1", "task_2"]
    else:
        synthesis_deps = ["task_1"]

    # Task N: Synthesize
    tasks.append(
        AgentTask(
            task_id=f"task_{len(tasks) + 1}",
            agent_type="synthesis",
            instruction=f"Synthesize final answer for: {query}",
            depends_on=synthesis_deps,
        )
    )

    return tasks


def _has_circular_dependencies(tasks: list[AgentTask]) -> bool:
    """Check if task dependency graph has circular dependencies (AC2).

    Args:
        tasks: List of agent tasks with dependencies

    Returns:
        True if circular dependencies detected, False otherwise
    """
    # Build adjacency list
    task_ids = {task.task_id for task in tasks}
    adjacency = {task.task_id: task.depends_on for task in tasks}

    # DFS-based cycle detection
    visited = set()
    recursion_stack = set()

    def has_cycle(task_id: str) -> bool:
        """Recursive DFS to detect cycles."""
        if task_id in recursion_stack:
            return True
        if task_id in visited:
            return False

        visited.add(task_id)
        recursion_stack.add(task_id)

        for dependency in adjacency.get(task_id, []):
            if dependency in task_ids and has_cycle(dependency):
                return True

        recursion_stack.remove(task_id)
        return False

    # Check each task for cycles
    for task_id in task_ids:
        if task_id not in visited:
            if has_cycle(task_id):
                return True

    return False


async def decompose_query(query: str, complexity: QueryComplexity) -> WorkflowPlan:
    """Decompose complex query into multi-step workflow plan (AC2).

    This function analyzes analytical queries and creates a task DAG with:
    - Retrieval tasks for document search
    - Analysis tasks for financial calculations
    - Synthesis task for final answer aggregation

    Args:
        query: Natural language user query
        complexity: Query complexity classification

    Returns:
        WorkflowPlan with task DAG and execution metadata

    Raises:
        ValueError: If task graph has circular dependencies

    AC2: Workflow planner decomposes complex queries into sub-tasks with dependencies
    """
    logger.info("Decomposing query", extra={"query": query, "complexity": complexity})

    # Simple queries don't need decomposition
    if complexity == QueryComplexity.SIMPLE:
        tasks = _build_simple_workflow(query)
        plan = WorkflowPlan(
            query=query,
            complexity=complexity,
            tasks=tasks,
            metadata={"pattern": "simple", "task_count": 1, "estimated_time_ms": 1500},
        )
        logger.info("Simple query decomposition complete", extra={"task_count": 1})
        return plan

    # Analytical queries - pattern detection
    query_lower = query.lower()
    pattern = "generic_analytical"

    # Pattern 1: YoY Growth Workflow
    if re.search(r"\byoy\b|year.over.year|growth.*calculate|calculate.*growth", query_lower):
        tasks = _build_yoy_growth_workflow(query, query_lower)
        pattern = "yoy_growth"

    # Pattern 2: Variance Analysis Workflow
    elif re.search(
        r"variance|why.*\b(increase|decrease|change)\b|explain.*difference", query_lower
    ):
        tasks = _build_variance_analysis_workflow(query, query_lower)
        pattern = "variance_analysis"

    # Pattern 3: Trend Analysis Workflow
    elif re.search(r"trend|pattern|over.*time|historical", query_lower):
        tasks = _build_trend_analysis_workflow(query, query_lower)
        pattern = "trend_analysis"

    # Pattern 4: Generic Analytical Workflow (fallback)
    else:
        tasks = _build_generic_analytical_workflow(query, query_lower)

    # Validate task graph has no circular dependencies (AC2)
    if _has_circular_dependencies(tasks):
        error_msg = "Task decomposition failed: circular dependencies detected"
        logger.error(error_msg, extra={"query": query})
        raise ValueError(error_msg)

    # Build workflow plan
    plan = WorkflowPlan(
        query=query,
        complexity=complexity,
        tasks=tasks,
        metadata={
            "task_count": len(tasks),
            "estimated_time_ms": len(tasks) * 1500,
            "pattern": pattern,
        },
    )

    logger.info(
        "Query decomposition complete",
        extra={"task_count": len(tasks), "pattern": pattern},
    )

    return plan
