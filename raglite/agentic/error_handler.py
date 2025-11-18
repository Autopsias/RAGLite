"""Error handling and graceful degradation for agentic workflows.

Implements AC5: Error handling with timeout, graceful degradation,
and structured error logging (NFR24, NFR26).
"""

import asyncio
from collections.abc import Callable
from typing import Any

from raglite.agentic.state import AgentState
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class AgentExecutionError(Exception):
    """Base exception for agent execution failures."""

    def __init__(
        self,
        message: str,
        agent_name: str,
        error_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize agent execution error.

        Args:
            message: Error description
            agent_name: Name of the agent that failed
            error_type: Type of error (timeout, failure, etc.)
            metadata: Additional error context
        """
        self.message = message
        self.agent_name = agent_name
        self.error_type = error_type
        self.metadata = metadata or {}

        super().__init__(self.message)


class WorkflowErrorHandler:
    """Handles errors in agentic workflows with graceful degradation.

    AC5: Error handling implemented for workflow failures (NFR24, NFR26)
    AC5: Graceful degradation on agent failures
    AC5: Error logging with structured metadata
    """

    def __init__(self, fallback_search_func: Callable[..., Any] | None = None) -> None:
        """Initialize error handler.

        Args:
            fallback_search_func: Optional fallback function for simple search
                (from Epic 2: raglite.retrieval.multi_index_search)
        """
        self.fallback_search_func = fallback_search_func
        self.error_log: list[dict[str, Any]] = []

    async def execute_with_fallback(
        self,
        agent_task: Any,
        timeout_seconds: int,
        agent_name: str,
        state: AgentState,
    ) -> tuple[bool, AgentState, str | None]:
        """Execute agent task with timeout and fallback handling.

        AC5: Agent timeout handling (max 15s per agent)
        AC5: Graceful degradation on agent failures

        Args:
            agent_task: Async function to execute
            timeout_seconds: Timeout in seconds (15s per NFR26)
            agent_name: Name of agent for logging
            state: Current workflow state

        Returns:
            Tuple of (success, updated_state, error_message)
        """
        try:
            # Execute with timeout
            result_state = await asyncio.wait_for(agent_task, timeout=timeout_seconds)
            return True, result_state, None

        except TimeoutError:
            error_msg = f"Agent '{agent_name}' exceeded {timeout_seconds}s timeout"
            self._log_error(
                error_msg,
                agent_name,
                "timeout",
                {"timeout_seconds": timeout_seconds, "query": state.query},
            )
            return False, state, error_msg

        except Exception as e:
            error_msg = f"Agent '{agent_name}' failed: {str(e)}"
            self._log_error(
                error_msg,
                agent_name,
                "failure",
                {
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                    "query": state.query,
                },
            )
            return False, state, error_msg

    async def fallback_to_simple_search(self, state: AgentState, error_reason: str) -> AgentState:
        """Fallback to Epic 2 simple search on workflow failure.

        AC5: Graceful degradation on agent failures (fallback to Epic 2)
        NFR24: Graceful degradation on component failures

        Args:
            state: Current workflow state
            error_reason: Reason for fallback

        Returns:
            State with retrieval results from simple search (if available)
        """
        logger.warning(
            "Workflow failed, falling back to simple search",
            extra={
                "query": state.query,
                "fallback_reason": error_reason,
                "has_fallback": self.fallback_search_func is not None,
            },
        )

        if not self.fallback_search_func:
            logger.error(
                "Fallback search function not configured",
                extra={"query": state.query},
            )
            return state

        try:
            # Call fallback simple search function
            retrieval_results = await self.fallback_search_func(state.query, top_k=5)

            if retrieval_results:
                # Convert results to DocumentChunk format
                from raglite.agentic.state import DocumentChunk

                chunks = [
                    DocumentChunk(
                        id=f"fallback_{i}",
                        content=getattr(result, "content", str(result)),
                        source=getattr(result, "source", "fallback_search"),
                        page_number=getattr(result, "page_number", None),
                        chunk_index=i,
                    )
                    for i, result in enumerate(retrieval_results)
                ]

                state.retrieval_results = chunks
                state.add_metadata("used_fallback", True)
                state.add_metadata("fallback_reason", error_reason)

                logger.info(
                    "Fallback search succeeded",
                    extra={
                        "query": state.query,
                        "chunks_retrieved": len(chunks),
                    },
                )

        except Exception as e:
            error_msg = f"Fallback search also failed: {str(e)}"
            self._log_error(
                error_msg,
                "fallback_search",
                "fallback_failure",
                {
                    "query": state.query,
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
            )

        return state

    def _log_error(
        self,
        message: str,
        agent_name: str,
        error_type: str,
        metadata: dict[str, Any],
    ) -> None:
        """Log error with structured metadata.

        AC5: Error logging with structured metadata
        (agent ID, failure reason, timestamp)

        Args:
            message: Error message
            agent_name: Name of agent
            error_type: Type of error
            metadata: Additional context
        """
        # Filter out error_type from metadata to avoid overwriting parameter
        metadata_safe = {
            k: v
            for k, v in metadata.items()
            if k not in ("error_type", "error_message", "agent_id")
        }

        error_context = {
            "agent_id": agent_name,
            "error_type": error_type,
            "error_message": message,  # Use 'error_message' to avoid conflict
            **metadata_safe,
        }

        logger.error(
            message,
            extra={
                "agent_id": agent_name,
                "error_type": error_type,
                **metadata_safe,
            },
        )

        # Store in error log for debugging
        self.error_log.append(error_context)

    def get_error_log(self) -> list:
        """Get accumulated error log.

        Returns:
            List of error records with metadata
        """
        return self.error_log

    def clear_error_log(self) -> None:
        """Clear the error log."""
        self.error_log = []
