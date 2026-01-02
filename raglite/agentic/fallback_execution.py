"""Timeout execution wrappers for agentic workflows.

This module provides timeout handling for individual agents and
complete workflow orchestration (Story 3.5 AC8, Story 3.7 AC1).
"""

import asyncio
from typing import Any

from raglite.agentic.fallback_error_handling import ErrorType, classify_error
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def execute_with_timeout(
    agent_fn: Any,
    instruction: str,
    context: dict[str, Any],
    timeout_seconds: float = 15.0,
) -> Any:
    """Execute agent with timeout handling (AC8, NFR26: 15s per-agent timeout).

    Story 3.7 AC2: Enhanced error classification and structured logging.

    Args:
        agent_fn: Agent callable function
        instruction: Task instruction for the agent
        context: Context data from previous agents
        timeout_seconds: Timeout in seconds (default 15s per NFR26)

    Returns:
        Agent result

    Raises:
        asyncio.TimeoutError: If agent exceeds timeout
        Exception: If agent execution fails
    """
    try:
        # Execute with timeout (AC8: 4.1)
        result = await asyncio.wait_for(
            agent_fn(instruction=instruction, context=context),
            timeout=timeout_seconds,
        )
        return result

    except TimeoutError as e:
        # Story 3.7 AC2: Enhanced timeout logging with error classification
        error_type = classify_error(e)
        logger.warning(  # AC2: WARNING level (graceful degradation expected)
            "Agent execution timeout",
            extra={
                "agent": getattr(agent_fn, "__name__", "unknown"),
                "instruction": instruction[:100],
                "timeout_seconds": timeout_seconds,
                "error_type": error_type.value,
            },
        )
        raise

    except Exception as e:
        # Story 3.7 AC2: Classify and log all error types
        error_type = classify_error(e)
        logger.warning(  # AC2: WARNING level for agent failures (graceful degradation)
            "Agent execution failed",
            extra={
                "agent": getattr(agent_fn, "__name__", "unknown"),
                "instruction": instruction[:100],
                "error_type": error_type.value,
                "error_message": str(e)[:200],
            },
        )
        raise


async def execute_workflow_with_timeout(
    workflow_fn: Any,
    *args: Any,
    timeout_seconds: float = 30.0,
    **kwargs: Any,
) -> Any:
    """Execute entire workflow with timeout handling (AC1: NFR5 30s workflow timeout).

    This wraps the complete workflow orchestration with a 30-second timeout to ensure
    total query response time stays within NFR5 requirements (p95 <15s, max 30s).

    Args:
        workflow_fn: Workflow execution function to wrap
        *args: Positional arguments to pass to workflow_fn
        timeout_seconds: Workflow timeout in seconds (default 30s per NFR5)
        **kwargs: Keyword arguments to pass to workflow_fn

    Returns:
        Workflow execution result

    Raises:
        asyncio.TimeoutError: If workflow exceeds 30s timeout

    Example:
        >>> result = await execute_workflow_with_timeout(
        ...     executor.execute_workflow, plan, timeout_seconds=30.0
        ... )
    """
    try:
        logger.info(
            "Starting workflow with timeout",
            extra={"timeout_seconds": timeout_seconds},
        )

        result = await asyncio.wait_for(
            workflow_fn(*args, **kwargs),
            timeout=timeout_seconds,
        )

        logger.info(
            "Workflow completed within timeout",
            extra={"timeout_seconds": timeout_seconds},
        )

        return result

    except TimeoutError:
        # AC1: Workflow timeout triggers immediate fallback to Epic 1/2
        logger.warning(
            "Workflow execution timeout - triggering Tier 4 fallback",
            extra={
                "timeout_seconds": timeout_seconds,
                "error_type": ErrorType.TIMEOUT.value,
            },
        )
        raise
