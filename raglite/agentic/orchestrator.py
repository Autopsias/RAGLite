"""AWS Strands-based orchestrator for agentic workflows.

Provides the orchestration engine for coordinating multi-step workflows
using AWS Strands agents (Story 3.1: AC2, AC3).

Story 3.2: Includes retrieval_agent as registered tool for agent workflows.
"""

import asyncio
from collections.abc import Callable
from typing import Any

from raglite.agentic.state import AgentState
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

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
        """Load default agent tools (Story 3.2-3.3 AC1: agent registration).

        Registers retrieval_agent, analysis_agent, and other core tools available to orchestrator.
        Tools are @tool decorated functions from AWS Strands.
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
