"""Multi-step workflow orchestration for agentic coordination.

Story 3.5: Multi-Step Workflow Orchestration
Executes multi-step workflow plans with parallel and sequential task coordination.
"""

import asyncio
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from raglite.agentic.orchestrator_tools import load_workflow_agents
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from raglite.agentic.planner import AgentResult, AgentTask, WorkflowPlan

logger = get_logger(__name__)


class WorkflowExecutor:
    """Executes multi-step workflow plans with parallel and sequential task coordination.

    This executor takes a WorkflowPlan (from decompose_query) and orchestrates execution
    across specialized agents (Retrieval, Analysis, Synthesis) with proper dependency
    management and inter-agent data passing.

    AC3: Sub-tasks routed to appropriate specialized agents
    AC4: Agent outputs passed between agents as inputs to subsequent steps
    AC5: Workflow execution completes in <30 seconds for typical analytical queries

    Supported Workflow Patterns:
        1. **YoY Growth Pattern** (yoy_growth):
           - Parallel retrieval: Previous period + Current period
           - Analysis: Calculate year-over-year percentage growth
           - Optional: Retrieve variance drivers if query asks to "explain"
           - Synthesis: Aggregate all results into final answer
           - Example: "Calculate YoY revenue growth from 2022 to 2023"

        2. **Variance Analysis Pattern** (variance_analysis):
           - Retrieval: Current period financial data
           - Optional: Comparison period data (if comparative query)
           - Analysis: Calculate variance magnitude and change
           - Retrieval: Variance drivers and contributing factors
           - Synthesis: Explain variance with context
           - Example: "Explain the variance in Q3 operating expenses"

        3. **Trend Analysis Pattern** (trend_analysis):
           - Parallel retrieval: Multiple periods (default 4 quarters)
           - Analysis: Identify trend pattern (growth, decline, cyclical, stable)
           - Synthesis: Describe trend with supporting data
           - Example: "Show revenue trend over the last 4 quarters"

        4. **Generic Analytical Pattern** (generic_analytical):
           - Fallback pattern when no specific pattern matches
           - Retrieval: Relevant financial data for query
           - Optional analysis: If calculation/analysis keywords present
           - Synthesis: Aggregate results into answer
           - Example: "Analyze the financial performance metrics"

    Example usage:
        >>> plan = await decompose_query("Calculate YoY growth", QueryComplexity.ANALYTICAL)
        >>> executor = WorkflowExecutor()
        >>> results = await executor.execute_workflow(plan)
        >>> len(results)  # 4 results: 2 retrievals + 1 analysis + 1 synthesis
        4
    """

    def __init__(self) -> None:
        """Initialize workflow executor with agent registry."""
        # Agent registry: maps agent_type to callable agent function
        self._agent_registry: dict[str, Callable] = load_workflow_agents()

        logger.info(
            "WorkflowExecutor initialized",
            extra={"registered_agents": list(self._agent_registry.keys())},
        )

    def _route_task_to_agent(self, agent_type: str) -> Callable | None:
        """Route task to appropriate agent based on agent_type (AC3).

        Args:
            agent_type: Type of agent ("retrieval", "analysis", or "synthesis")

        Returns:
            Agent callable function, or None if agent not found
        """
        agent = self._agent_registry.get(agent_type.lower())
        if not agent:
            logger.warning(
                "Agent type not found in registry",
                extra={
                    "agent_type": agent_type,
                    "available": list(self._agent_registry.keys()),
                },
            )
        return agent

    def _create_error_result(
        self, task: "AgentTask", error_msg: str, execution_time_ms: int = 0
    ) -> "AgentResult":
        """Create an error AgentResult."""
        from raglite.agentic.planner import AgentResult

        return AgentResult(
            task_id=task.task_id,
            agent_type=task.agent_type,
            success=False,
            result=None,
            execution_time_ms=execution_time_ms,
            error_message=error_msg,
        )

    def _create_success_result(
        self, task: "AgentTask", result: Any, execution_time_ms: int
    ) -> "AgentResult":
        """Create a success AgentResult."""
        from raglite.agentic.planner import AgentResult

        return AgentResult(
            task_id=task.task_id,
            agent_type=task.agent_type,
            success=True,
            result=result,
            execution_time_ms=execution_time_ms,
        )

    async def _execute_task(
        self,
        task: "AgentTask",
        task_results: dict[str, Any],
        timeout_seconds: float = 15.0,
    ) -> "AgentResult":
        """Execute a single agent task with timeout handling (AC3, AC4, AC8).

        Args:
            task: AgentTask to execute
            task_results: Dictionary of completed task results (for dependency resolution)
            timeout_seconds: Per-agent timeout in seconds (default 15s per NFR26)

        Returns:
            AgentResult with execution outcome
        """
        from raglite.agentic.fallback import execute_with_timeout

        start_time_ms = int(time.time() * 1000)
        logger.info(
            "Executing task",
            extra={
                "task_id": task.task_id,
                "agent_type": task.agent_type,
                "timeout_seconds": timeout_seconds,
            },
        )

        # Route to appropriate agent (AC3)
        agent_fn = self._route_task_to_agent(task.agent_type)
        if not agent_fn:
            error_msg = f"Agent type '{task.agent_type}' not registered"
            logger.error(error_msg, extra={"task_id": task.task_id})
            return self._create_error_result(task, error_msg)

        try:
            # Gather dependency outputs (AC4: inter-agent data passing)
            dependency_data = {
                dep_id: task_results[dep_id].result
                for dep_id in task.depends_on
                if dep_id in task_results
            }

            # Execute agent with timeout (AC8)
            result = await execute_with_timeout(
                agent_fn=agent_fn,
                instruction=task.instruction,
                context=dependency_data,
                timeout_seconds=timeout_seconds,
            )

            execution_time_ms = int(time.time() * 1000) - start_time_ms
            logger.info(
                "Task execution completed",
                extra={"task_id": task.task_id, "execution_time_ms": execution_time_ms},
            )
            return self._create_success_result(task, result, execution_time_ms)

        except TimeoutError:
            execution_time_ms = int(time.time() * 1000) - start_time_ms
            logger.error(
                "Agent execution timeout",
                extra={"task_id": task.task_id, "timeout_seconds": timeout_seconds},
            )
            return self._create_error_result(
                task, f"Agent execution timeout after {timeout_seconds}s", execution_time_ms
            )

        except Exception as e:
            execution_time_ms = int(time.time() * 1000) - start_time_ms
            logger.error("Task execution failed", extra={"task_id": task.task_id, "error": str(e)})
            return self._create_error_result(task, f"Task execution failed: {e}", execution_time_ms)

    def _find_ready_tasks(
        self, pending_tasks: dict[str, "AgentTask"], task_results: dict[str, "AgentResult"]
    ) -> list["AgentTask"]:
        """Find tasks that have all dependencies completed."""
        return [
            task
            for task in pending_tasks.values()
            if all(dep_id in task_results for dep_id in task.depends_on)
        ]

    async def execute_workflow(self, plan: "WorkflowPlan") -> list["AgentResult"]:
        """Execute complete workflow plan with parallel and sequential coordination (AC3, AC4, AC5).

        Args:
            plan: WorkflowPlan with task DAG

        Returns:
            List of AgentResult for all executed tasks
        """
        from raglite.agentic.planner import AgentResult

        workflow_start_ms = int(time.time() * 1000)
        logger.info(
            "Workflow execution started", extra={"query": plan.query, "task_count": len(plan.tasks)}
        )

        task_results: dict[str, AgentResult] = {}
        pending_tasks = {task.task_id: task for task in plan.tasks}
        results: list[AgentResult] = []

        while pending_tasks:
            ready_tasks = self._find_ready_tasks(pending_tasks, task_results)

            if not ready_tasks:
                error_msg = "Workflow deadlock: no tasks ready to execute but tasks remain"
                logger.error(error_msg, extra={"pending_tasks": list(pending_tasks.keys())})
                for task in pending_tasks.values():
                    results.append(self._create_error_result(task, error_msg))
                break

            logger.info("Executing parallel task batch", extra={"task_count": len(ready_tasks)})

            task_futures = [
                self._execute_task(
                    task, task_results, timeout_seconds=settings.strands_agent_timeout_seconds
                )
                for task in ready_tasks
            ]
            batch_results = await asyncio.gather(*task_futures, return_exceptions=False)

            for i, task in enumerate(ready_tasks):
                result = batch_results[i]
                task_results[task.task_id] = result
                results.append(result)
                del pending_tasks[task.task_id]

        total_time_ms = int(time.time() * 1000) - workflow_start_ms
        success_count = sum(1 for r in results if r.success)
        logger.info(
            "Workflow execution completed",
            extra={
                "total_tasks": len(results),
                "successful_tasks": success_count,
                "total_time_ms": total_time_ms,
            },
        )

        return results
