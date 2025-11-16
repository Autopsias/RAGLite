"""Workflow planning and query decomposition for multi-step agentic workflows.

This module implements the query complexity classifier and task decomposition
engine for Story 3.5: Multi-Step Workflow Orchestration.
"""

import logging
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QueryComplexity(str, Enum):
    """Classification of query complexity (AC1)."""

    SIMPLE = "simple"  # Direct retrieval queries
    ANALYTICAL = "analytical"  # Multi-step analytical queries requiring orchestration


class AgentTask(BaseModel):
    """A single task in a workflow plan (AC2)."""

    task_id: str = Field(..., description="Unique task identifier (e.g., 'task_1')")
    agent_type: str = Field(..., description="Agent type: 'retrieval', 'analysis', or 'synthesis'")
    instruction: str = Field(..., description="Task instruction for the agent")
    depends_on: list[str] = Field(
        default_factory=list, description="Task IDs that must complete before this task"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional task metadata")


class WorkflowPlan(BaseModel):
    """Complete workflow plan with task DAG (AC2)."""

    query: str = Field(..., description="Original user query")
    complexity: QueryComplexity = Field(..., description="Query complexity classification")
    tasks: list[AgentTask] = Field(..., description="List of tasks in execution order")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Workflow metadata (e.g., estimated_time_ms)"
    )


class AgentResult(BaseModel):
    """Result from a single agent task execution (AC4)."""

    task_id: str = Field(..., description="Task identifier that was executed")
    agent_type: str = Field(..., description="Agent type that executed the task")
    success: bool = Field(..., description="Whether task completed successfully")
    result: Any = Field(default=None, description="Task result data")
    execution_time_ms: int = Field(..., description="Task execution time in milliseconds")
    error_message: str | None = Field(default=None, description="Error message if task failed")


async def classify_query_complexity(query: str) -> QueryComplexity:
    """Classify query as simple or analytical based on keyword matching (AC1).

    This classifier distinguishes between:
    - **Simple queries:** Direct retrieval (e.g., "What is revenue?")
    - **Analytical queries:** Multi-step reasoning (e.g., "Calculate YoY growth")

    Args:
        query: Natural language user query

    Returns:
        QueryComplexity.SIMPLE or QueryComplexity.ANALYTICAL

    Examples:
        >>> await classify_query_complexity("What is Q3 revenue?")
        QueryComplexity.SIMPLE

        >>> await classify_query_complexity("Calculate YoY revenue growth")
        QueryComplexity.ANALYTICAL

    AC1: Classifier accuracy >90% on test queries from ground truth set
    """
    # Keywords that indicate analytical/multi-step queries
    analytical_keywords = {
        # Calculation keywords
        "calculate",
        "compute",
        "determine",
        # Growth/change keywords
        "growth",
        "change",
        "increase",
        "decrease",
        "yoy",
        "year-over-year",
        "quarter-over-quarter",
        "qoq",
        # Variance/analysis keywords
        "variance",
        "difference",
        "delta",
        "deviation",
        # Trend keywords
        "trend",
        "pattern",
        "forecast",
        "predict",
        "projection",
        # Comparison keywords
        "compare",
        "comparison",
        "versus",
        "vs",
        "vs.",
        "between",
        # Explanation/reasoning keywords
        "explain",
        "why",
        "reason",
        "cause",
        "driver",
        "impact",
        # Analysis keywords
        "analyze",
        "analysis",
        "assess",
        "evaluate",
        # Percentage/ratio keywords
        "percentage",
        "percent",
        "%",
        "ratio",
        "margin",
        "rate",
    }

    query_lower = query.lower()

    # Check if any analytical keyword is present in the query
    if any(keyword in query_lower for keyword in analytical_keywords):
        return QueryComplexity.ANALYTICAL

    return QueryComplexity.SIMPLE


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

    Examples:
        >>> plan = await decompose_query(
        ...     "Calculate YoY revenue growth and explain variance",
        ...     QueryComplexity.ANALYTICAL
        ... )
        >>> len(plan.tasks)
        5  # 2 retrievals + 1 analysis + 1 retrieval + 1 synthesis

    AC2: Workflow planner decomposes complex queries into sub-tasks with dependencies
    """
    logger.info("Decomposing query", extra={"query": query, "complexity": complexity})

    # Simple queries don't need decomposition
    if complexity == QueryComplexity.SIMPLE:
        tasks = [
            AgentTask(
                task_id="task_1",
                agent_type="retrieval",
                instruction=f"Search documents for: {query}",
                depends_on=[],
            )
        ]
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
    tasks = []  # Initialize tasks list for analytical queries

    # Pattern 1: YoY Growth Workflow
    # Keywords: "yoy", "year-over-year", "growth", "calculate"
    if re.search(r"\byoy\b|year.over.year|growth.*calculate|calculate.*growth", query_lower):
        logger.info("Detected YoY growth pattern", extra={"pattern": "yoy_growth"})

        # Extract time periods if mentioned (e.g., "Q3 2023", "2024")
        current_period = "current period"
        previous_period = "previous period"

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

    # Pattern 2: Variance Analysis Workflow
    # Keywords: "variance", "explain", "why", "difference"
    elif re.search(
        r"variance|why.*\b(increase|decrease|change)\b|explain.*difference", query_lower
    ):
        logger.info("Detected variance analysis pattern", extra={"pattern": "variance_analysis"})

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

    # Pattern 3: Trend Analysis Workflow
    # Keywords: "trend", "pattern", "over time"
    elif re.search(r"trend|pattern|over.*time|historical", query_lower):
        logger.info("Detected trend analysis pattern", extra={"pattern": "trend_analysis"})

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

    # Pattern 4: Generic Analytical Workflow (fallback)
    else:
        logger.info("Using generic analytical pattern", extra={"pattern": "generic_analytical"})

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
            "estimated_time_ms": len(tasks) * 1500,  # Rough estimate: 1.5s per task
        },
    )

    logger.info(
        "Query decomposition complete",
        extra={"task_count": len(tasks), "pattern": plan.metadata.get("pattern", "unknown")},
    )

    return plan
