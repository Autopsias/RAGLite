"""AWS Strands-based orchestrator for agentic workflows.

Provides the orchestration engine for coordinating multi-step workflows
using AWS Strands agents (Story 3.1: AC2, AC3).

Story 3.2: Includes retrieval_agent as registered tool for agent workflows.
"""

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from raglite.agentic.state import AgentState
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from raglite.agentic.planner import AgentResult, AgentTask, WorkflowPlan

logger = get_logger(__name__)


class StrandsOrchestrator:
    """Orchestrates multi-agent workflows using AWS Strands.

    AC2: Framework initialization and configuration validated
    AC3: Basic 2-step workflow execution tested

    NOTE: Strands initialization is deferred until Epic 3 (Story 3.1+).
    """

    def __init__(self) -> None:
        """Initialize the Strands orchestrator with configuration."""
        self.orchestration_model = settings.strands_orchestration_model
        self.agent_timeout = settings.strands_agent_timeout_seconds
        self.enable_observability = settings.strands_enable_opentelemetry

        # Initialize registered tools list (Story 3.2 AC1: retrieval_agent registration)
        self._registered_tools: list[Callable] = []
        self._load_default_tools()

        # Import Strands on initialization (AC1)
        # NOTE: Strands deferred until Epic 3 - store Agent class if available
        try:
            from strands import Agent

            self.Agent = Agent
        except ImportError:
            # Strands not installed - deferred until Epic 3 (Story 3.1+)
            logger.warning(
                "AWS Strands not installed - agentic workflows deferred to Epic 3",
                extra={"required_version": "1.15.0+"},
            )
            self.Agent = None

        logger.info(
            "Strands orchestrator initialized",
            extra={
                "model": self.orchestration_model,
                "timeout_seconds": self.agent_timeout,
                "observability_enabled": self.enable_observability,
                "registered_tools": len(self._registered_tools),
            },
        )

    def _load_default_tools(self) -> None:
        """Load default agent tools (Story 3.2-3.4 AC1: agent registration).

        Registers retrieval_agent, analysis_agent, synthesis_agent, and other core tools
        available to orchestrator. Tools are @tool decorated functions from AWS Strands.
        """
        try:
            # Import retrieval_agent (Story 3.2)
            from raglite.agentic.agents.retrieval_agent import retrieval_agent

            self._registered_tools.append(retrieval_agent)
            logger.info(
                "Registered retrieval_agent tool",
                extra={"tool_name": "retrieval_agent"},
            )

        except ImportError as e:
            logger.warning(
                "Failed to load retrieval_agent tool",
                extra={"error": str(e)},
            )

        try:
            # Import analysis_agent (Story 3.3 AC1)
            from raglite.agentic.agents.analysis_agent import analysis_agent

            self._registered_tools.append(analysis_agent)
            logger.info(
                "Registered analysis_agent tool",
                extra={"tool_name": "analysis_agent"},
            )

        except ImportError as e:
            logger.warning(
                "Failed to load analysis_agent tool",
                extra={"error": str(e)},
            )

        try:
            # Import synthesis_agent (Story 3.4 AC1)
            from raglite.agentic.agents.synthesis_agent import synthesis_agent

            self._registered_tools.append(synthesis_agent)
            logger.info(
                "Registered synthesis_agent tool",
                extra={"tool_name": "synthesis_agent"},
            )

        except ImportError as e:
            logger.warning(
                "Failed to load synthesis_agent tool",
                extra={"error": str(e)},
            )

        try:
            # Import forecasting_agent (Story 4.2 AC5)
            from raglite.agentic.agents.forecasting_agent import forecasting_agent

            self._registered_tools.append(forecasting_agent)
            logger.info(
                "Registered forecasting_agent tool",
                extra={"tool_name": "forecasting_agent"},
            )

        except ImportError as e:
            logger.warning(
                "Failed to load forecasting_agent tool",
                extra={"error": str(e)},
            )

    def get_available_tools(self) -> list[Callable]:
        """Get list of all registered tools available to agents.

        Story 3.2 AC1: Returns available tools for agent creation
        Includes retrieval_agent and other @tool decorated functions.

        Returns:
            List of callable tools registered with the orchestrator
        """
        return self._registered_tools.copy()

    def register_tools(self, tools: list[Callable]) -> None:
        """Register additional tools with the orchestrator.

        Story 3.2 AC1: Allows dynamic tool registration
        Tools should be @tool decorated functions from AWS Strands.

        Args:
            tools: List of callable tools to register
        """
        for tool in tools:
            if callable(tool):
                self._registered_tools.append(tool)
                logger.info(
                    "Tool registered with orchestrator",
                    extra={"tool_name": getattr(tool, "__name__", str(tool))},
                )
            else:
                logger.warning(
                    "Attempted to register non-callable tool",
                    extra={"tool": str(tool)},
                )

    async def create_agent(
        self,
        name: str,
        tools: list[Callable] | None = None,
        system_prompt: str | None = None,
        use_registered_tools: bool = True,
    ) -> Any:
        """Create a Strands Agent for a specific orchestration task.

        AC2: Strands Agent class instantiable with basic config
        Story 3.2 AC1: Agent can use registered tools (retrieval_agent, etc.)

        Args:
            name: Agent name/identifier
            tools: Optional list of tool functions available to agent
                If None and use_registered_tools=True, uses orchestrator's registered tools
            system_prompt: Optional system prompt for agent behavior
            use_registered_tools: If True and tools=None, includes registered tools

        Returns:
            Configured Strands Agent instance

        Raises:
            ValueError: If agent creation fails
        """
        try:
            if tools is None:
                # Use registered tools if available and requested (Story 3.2 AC1)
                if use_registered_tools:
                    tools = self.get_available_tools()
                else:
                    tools = []

            if system_prompt is None:
                system_prompt = f"You are {name}, an agent in the RAGLite orchestration system."

            # Create agent with Mistral Small as the orchestration LLM
            # Using Strands Agent API with correct parameters
            agent = self.Agent(
                system_prompt=system_prompt,
                tools=tools,
                agent_id=name,
                name=name,
            )

            logger.info(
                "Agent created",
                extra={"agent_name": name, "tools_count": len(tools)},
            )

            return agent

        except Exception as e:
            logger.error(
                "Failed to create agent",
                extra={
                    "agent_name": name,
                    "error": str(e),
                },
            )
            raise ValueError(f"Agent creation failed for '{name}': {e}") from e

    async def execute_workflow(
        self,
        initial_state: AgentState,
        workflow_steps: list[dict[str, Any]],
    ) -> AgentState:
        """Execute a multi-step workflow with sequential agents.

        AC3: Basic 2-step workflow execution tested
        AC4: State passes correctly between agents

        Args:
            initial_state: Initial AgentState with query input
            workflow_steps: List of workflow step definitions,
                each with 'agent' and 'process_fn' keys

        Returns:
            Updated AgentState with all agent results

        Raises:
            TimeoutError: If any agent execution exceeds timeout
            RuntimeError: If workflow execution fails
        """
        current_state = initial_state
        logger.info(
            "Workflow execution started",
            extra={
                "query": current_state.query,
                "steps": len(workflow_steps),
            },
        )

        for i, step in enumerate(workflow_steps):
            try:
                agent = step.get("agent")
                process_fn = step.get("process_fn")
                step_name = step.get("name", f"step_{i}")

                if not process_fn:
                    raise ValueError(f"Step {i} missing required 'process_fn'")

                logger.info(
                    "Executing workflow step",
                    extra={
                        "step_name": step_name,
                        "step_number": i + 1,
                        "total_steps": len(workflow_steps),
                    },
                )

                # Execute step with timeout (NFR26)
                current_state = await asyncio.wait_for(
                    process_fn(agent, current_state),
                    timeout=self.agent_timeout,
                )

                logger.info(
                    "Workflow step completed",
                    extra={
                        "step_name": step_name,
                        "state_fields": [
                            k for k, v in current_state.model_dump().items() if v is not None
                        ],
                    },
                )

            except TimeoutError as e:
                logger.error(
                    "Agent execution timeout",
                    extra={
                        "step_name": step_name,
                        "timeout_seconds": self.agent_timeout,
                        "step_number": i + 1,
                    },
                )
                raise TimeoutError(
                    f"Agent '{step_name}' exceeded {self.agent_timeout}s timeout"
                ) from e

            except Exception as e:
                logger.error(
                    "Workflow step failed",
                    extra={
                        "step_name": step_name,
                        "step_number": i + 1,
                        "error": str(e),
                    },
                )
                raise RuntimeError(f"Workflow failed at step '{step_name}': {e}") from e

        logger.info(
            "Workflow execution completed successfully",
            extra={
                "total_steps": len(workflow_steps),
                "final_state_fields": [
                    k for k, v in current_state.model_dump().items() if v is not None
                ],
            },
        )

        return current_state

    def get_configuration(self) -> dict[str, Any]:
        """Get the current orchestrator configuration.

        Returns:
            Dictionary with current settings
        """
        return {
            "orchestration_model": self.orchestration_model,
            "agent_timeout_seconds": self.agent_timeout,
            "observability_enabled": self.enable_observability,
        }


# ==============================================================================
# Story 3.5: Multi-Step Workflow Orchestration
# ==============================================================================


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
        self._agent_registry: dict[str, Callable] = {}
        self._load_agents()

        logger.info(
            "WorkflowExecutor initialized",
            extra={"registered_agents": list(self._agent_registry.keys())},
        )

    def _load_agents(self) -> None:
        """Load and register available agents (AC3: agent routing)."""
        try:
            from raglite.agentic.agents.retrieval_agent import retrieval_agent

            self._agent_registry["retrieval"] = retrieval_agent
            logger.info("Registered retrieval agent", extra={"agent_type": "retrieval"})
        except ImportError as e:
            logger.warning("Failed to load retrieval_agent", extra={"error": str(e)})

        try:
            from raglite.agentic.agents.analysis_agent import analysis_agent

            self._agent_registry["analysis"] = analysis_agent
            logger.info("Registered analysis agent", extra={"agent_type": "analysis"})
        except ImportError as e:
            logger.warning("Failed to load analysis_agent", extra={"error": str(e)})

        try:
            from raglite.agentic.agents.synthesis_agent import synthesis_agent

            self._agent_registry["synthesis"] = synthesis_agent
            logger.info("Registered synthesis agent", extra={"agent_type": "synthesis"})
        except ImportError as e:
            logger.warning("Failed to load synthesis_agent", extra={"error": str(e)})

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
                extra={"agent_type": agent_type, "available": list(self._agent_registry.keys())},
            )
        return agent

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

        AC4: Agent outputs passed between agents as inputs
        AC8: Timeout handling with graceful degradation (Task 4.1, 4.2)
        """
        import time

        from raglite.agentic.fallback import execute_with_timeout
        from raglite.agentic.planner import AgentResult

        start_time_ms = int(time.time() * 1000)

        logger.info(
            "Executing task",
            extra={
                "task_id": task.task_id,
                "agent_type": task.agent_type,
                "instruction": task.instruction[:100],
                "timeout_seconds": timeout_seconds,
            },
        )

        # Route to appropriate agent (AC3)
        agent_fn = self._route_task_to_agent(task.agent_type)
        if not agent_fn:
            error_msg = f"Agent type '{task.agent_type}' not registered"
            logger.error(error_msg, extra={"task_id": task.task_id})
            return AgentResult(
                task_id=task.task_id,
                agent_type=task.agent_type,
                success=False,
                result=None,
                execution_time_ms=0,
                error_message=error_msg,
            )

        try:
            # Gather dependency outputs for this task (AC4: inter-agent data passing)
            dependency_data = {}
            for dep_id in task.depends_on:
                if dep_id in task_results:
                    dependency_data[dep_id] = task_results[dep_id].result

            # Execute agent with timeout (AC8: Task 4.1)
            result = await execute_with_timeout(
                agent_fn=agent_fn,
                instruction=task.instruction,
                context=dependency_data,
                timeout_seconds=timeout_seconds,
            )

            execution_time_ms = int(time.time() * 1000) - start_time_ms

            logger.info(
                "Task execution completed",
                extra={
                    "task_id": task.task_id,
                    "agent_type": task.agent_type,
                    "execution_time_ms": execution_time_ms,
                    "success": True,
                },
            )

            return AgentResult(
                task_id=task.task_id,
                agent_type=task.agent_type,
                success=True,
                result=result,
                execution_time_ms=execution_time_ms,
            )

        except TimeoutError:
            # AC8: Task 4.2 - Timeout handler
            execution_time_ms = int(time.time() * 1000) - start_time_ms
            error_msg = f"Agent execution timeout after {timeout_seconds}s"
            logger.error(
                "Agent execution timeout",
                extra={
                    "task_id": task.task_id,
                    "agent_type": task.agent_type,
                    "timeout_seconds": timeout_seconds,
                    "error_type": "timeout",
                    "execution_time_ms": execution_time_ms,
                },
            )

            return AgentResult(
                task_id=task.task_id,
                agent_type=task.agent_type,
                success=False,
                result=None,
                execution_time_ms=execution_time_ms,
                error_message=error_msg,
            )

        except Exception as e:
            execution_time_ms = int(time.time() * 1000) - start_time_ms
            error_msg = f"Task execution failed: {e}"
            logger.error(
                "Task execution failed",
                extra={
                    "task_id": task.task_id,
                    "agent_type": task.agent_type,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "execution_time_ms": execution_time_ms,
                },
            )

            return AgentResult(
                task_id=task.task_id,
                agent_type=task.agent_type,
                success=False,
                result=None,
                execution_time_ms=execution_time_ms,
                error_message=error_msg,
            )

    async def execute_workflow(self, plan: "WorkflowPlan") -> list["AgentResult"]:
        """Execute complete workflow plan with parallel and sequential coordination (AC3, AC4, AC5).

        This method:
        1. Identifies independent tasks (no dependencies) for parallel execution
        2. Executes dependent tasks sequentially after dependencies complete
        3. Passes results between agents via task_results dictionary

        Args:
            plan: WorkflowPlan with task DAG

        Returns:
            List of AgentResult for all executed tasks

        AC3: Sub-tasks routed to appropriate specialized agents
        AC4: Agent outputs passed between agents as inputs to subsequent steps
        AC5: Workflow execution completes in <30 seconds for typical analytical queries

        Example:
            >>> plan = await decompose_query("Calculate YoY growth", QueryComplexity.ANALYTICAL)
            >>> results = await executor.execute_workflow(plan)
            >>> all(r.success for r in results)
            True
        """
        import time

        from raglite.agentic.planner import AgentResult

        workflow_start_ms = int(time.time() * 1000)

        logger.info(
            "Workflow execution started",
            extra={
                "query": plan.query,
                "task_count": len(plan.tasks),
                "complexity": plan.complexity,
            },
        )

        task_results: dict[str, AgentResult] = {}
        pending_tasks = {task.task_id: task for task in plan.tasks}
        results: list[AgentResult] = []

        while pending_tasks:
            # Find tasks ready to execute (all dependencies completed)
            ready_tasks = [
                task
                for task in pending_tasks.values()
                if all(dep_id in task_results for dep_id in task.depends_on)
            ]

            if not ready_tasks:
                # No tasks ready - dependency deadlock (should not happen with validated DAG)
                error_msg = "Workflow deadlock: no tasks ready to execute but tasks remain"
                logger.error(
                    error_msg,
                    extra={"pending_tasks": list(pending_tasks.keys())},
                )
                # Create error results for remaining tasks
                for task_id, task in pending_tasks.items():
                    results.append(
                        AgentResult(
                            task_id=task_id,
                            agent_type=task.agent_type,
                            success=False,
                            result=None,
                            execution_time_ms=0,
                            error_message=error_msg,
                        )
                    )
                break

            # Execute ready tasks in parallel (AC3, AC4)
            logger.info(
                "Executing parallel task batch",
                extra={
                    "task_count": len(ready_tasks),
                    "task_ids": [t.task_id for t in ready_tasks],
                },
            )

            # AC8: Pass timeout parameter to _execute_task (Task 4.1)
            task_futures = [
                self._execute_task(
                    task, task_results, timeout_seconds=settings.strands_agent_timeout_seconds
                )
                for task in ready_tasks
            ]
            batch_results = await asyncio.gather(*task_futures, return_exceptions=False)

            # Store results and remove from pending
            for i, task in enumerate(ready_tasks):
                result = batch_results[i]
                task_results[task.task_id] = result
                results.append(result)
                del pending_tasks[task.task_id]

                logger.info(
                    "Task completed and removed from pending",
                    extra={"task_id": task.task_id, "success": result.success},
                )

        workflow_end_ms = int(time.time() * 1000)
        total_time_ms = workflow_end_ms - workflow_start_ms

        success_count = sum(1 for r in results if r.success)
        logger.info(
            "Workflow execution completed",
            extra={
                "total_tasks": len(results),
                "successful_tasks": success_count,
                "failed_tasks": len(results) - success_count,
                "total_time_ms": total_time_ms,
            },
        )

        return results
