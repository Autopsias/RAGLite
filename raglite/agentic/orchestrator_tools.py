"""Tool registration and management for agentic orchestration.

Provides functionality for loading and registering agent tools
(retrieval_agent, analysis_agent, synthesis_agent, forecasting_agent).
"""

from collections.abc import Callable

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def load_default_tools() -> list[Callable]:
    """Load default agent tools (Story 3.2-3.4 AC1: agent registration).

    Registers retrieval_agent, analysis_agent, synthesis_agent, and other core tools
    available to orchestrator. Tools are @tool decorated functions from AWS Strands.

    Returns:
        List of successfully loaded agent tool functions
    """
    registered_tools: list[Callable] = []

    try:
        # Import retrieval_agent (Story 3.2)
        from raglite.agentic.agents.retrieval_agent import retrieval_agent

        registered_tools.append(retrieval_agent)
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

        registered_tools.append(analysis_agent)
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

        registered_tools.append(synthesis_agent)
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

        registered_tools.append(forecasting_agent)
        logger.info(
            "Registered forecasting_agent tool",
            extra={"tool_name": "forecasting_agent"},
        )

    except ImportError as e:
        logger.warning(
            "Failed to load forecasting_agent tool",
            extra={"error": str(e)},
        )

    return registered_tools


def register_tools(
    registered_tools: list[Callable],
    tools: list[Callable],
) -> None:
    """Register additional tools with the orchestrator.

    Story 3.2 AC1: Allows dynamic tool registration
    Tools should be @tool decorated functions from AWS Strands.

    Args:
        registered_tools: Current list of registered tools (modified in place)
        tools: List of callable tools to register
    """
    for tool in tools:
        if callable(tool):
            registered_tools.append(tool)
            logger.info(
                "Tool registered with orchestrator",
                extra={"tool_name": getattr(tool, "__name__", str(tool))},
            )
        else:
            logger.warning(
                "Attempted to register non-callable tool",
                extra={"tool": str(tool)},
            )


def load_workflow_agents() -> dict[str, Callable]:
    """Load and register available agents for WorkflowExecutor (AC3: agent routing).

    Returns:
        Dictionary mapping agent_type to callable agent function
    """
    agent_registry: dict[str, Callable] = {}

    try:
        from raglite.agentic.agents.retrieval_agent import retrieval_agent

        agent_registry["retrieval"] = retrieval_agent
        logger.info("Registered retrieval agent", extra={"agent_type": "retrieval"})
    except ImportError as e:
        logger.warning("Failed to load retrieval_agent", extra={"error": str(e)})

    try:
        from raglite.agentic.agents.analysis_agent import analysis_agent

        agent_registry["analysis"] = analysis_agent
        logger.info("Registered analysis agent", extra={"agent_type": "analysis"})
    except ImportError as e:
        logger.warning("Failed to load analysis_agent", extra={"error": str(e)})

    try:
        from raglite.agentic.agents.synthesis_agent import synthesis_agent

        agent_registry["synthesis"] = synthesis_agent
        logger.info("Registered synthesis agent", extra={"agent_type": "synthesis"})
    except ImportError as e:
        logger.warning("Failed to load synthesis_agent", extra={"error": str(e)})

    return agent_registry
