"""Graceful degradation and fallback handling for agentic workflows.

This module implements timeout handling and fallback mechanisms for Story 3.5
to ensure workflows always return useful results even when agents fail (AC8).

Pattern: Error Fallback Pattern from epic-3-agent-patterns.md
"""

import asyncio
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from raglite.agentic.planner import AgentResult, QueryComplexity
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class FallbackTier(str, Enum):
    """Quality tier of fallback response (AC8)."""

    FULL_WORKFLOW = "full"  # All agents succeeded
    PARTIAL_WORKFLOW = "partial"  # Some agents succeeded
    EPIC1_FALLBACK = "epic1_fallback"  # Fell back to basic retrieval


class FallbackResponse(BaseModel):
    """Response from fallback handler with tier metadata."""

    answer: str = Field(..., description="Final answer (may be partial or fallback)")
    tier: FallbackTier = Field(..., description="Quality tier of response")
    confidence: str = Field(..., description="Confidence level: high|medium|low")
    limitations: list[str] = Field(
        default_factory=list, description="Limitations or caveats about the answer"
    )
    partial_results: list[AgentResult] = Field(
        default_factory=list, description="Partial results from successful agents"
    )
    error_details: str | None = Field(default=None, description="Error details if workflow failed")
    execution_time_ms: int = Field(..., description="Total execution time")


async def execute_with_timeout(
    agent_fn: Any,
    instruction: str,
    context: dict[str, Any],
    timeout_seconds: float = 15.0,
) -> Any:
    """Execute agent with timeout handling (AC8, NFR26: 15s per-agent timeout).

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

    except TimeoutError:
        # Log timeout event (AC8: 4.2, 4.5)
        logger.error(
            "Agent execution timeout",
            extra={
                "agent": getattr(agent_fn, "__name__", "unknown"),
                "instruction": instruction[:100],
                "timeout_seconds": timeout_seconds,
                "error_type": "timeout",
            },
        )
        raise


async def fallback_to_basic_retrieval(query: str) -> str:
    """Fallback to Epic 1 basic retrieval when workflow fails (AC8: 4.3).

    This function calls the existing search_documents() from Epic 1
    as a last-resort fallback when agentic workflows fail.

    Args:
        query: Original user query

    Returns:
        Answer from basic retrieval

    Raises:
        Exception: If basic retrieval also fails
    """
    try:
        logger.warning(
            "Falling back to Epic 1 basic retrieval",
            extra={"query": query, "reason": "workflow_failure"},
        )

        # Import Epic 1 retrieval tool
        from raglite.retrieval.search import search_documents

        # Execute basic search (Epic 1 logic)
        # search_documents returns list[QueryResult]
        search_results = await search_documents(query, top_k=5)

        # Format basic answer
        if not search_results:
            return "I couldn't find relevant information to answer your query."

        # Simple formatting with QueryResult content
        answer = "Based on the available documents:\n\n"
        for i, result in enumerate(search_results[:3], 1):
            answer += f"[{i}] {result.text[:200]}...\n\n"

        return answer

    except Exception as e:
        logger.error(
            "Epic 1 fallback also failed",
            extra={"query": query, "error": str(e), "error_type": "fallback_failure"},
        )
        # Absolute last resort
        return "I apologize, but I'm experiencing technical difficulties and cannot process your query at this time. Please try again later or rephrase your question."


def format_fallback_response(
    query: str,
    tier: FallbackTier,
    partial_results: list[AgentResult],
    error_message: str,
    total_time_ms: int,
) -> FallbackResponse:
    """Format fallback response with partial results and error context (AC8: 4.4).

    Args:
        query: Original user query
        tier: Fallback tier that was triggered
        partial_results: Partial results from successful agents
        error_message: Error message explaining what failed
        total_time_ms: Total workflow execution time

    Returns:
        FallbackResponse with formatted answer and metadata
    """
    logger.info(
        "Formatting fallback response",
        extra={
            "tier": tier,
            "partial_result_count": len(partial_results),
            "error_summary": error_message[:100],
        },
    )

    if tier == FallbackTier.PARTIAL_WORKFLOW:
        # Format partial results
        answer = "⚠️ **Partial Analysis** (some agents unavailable)\n\n"

        # Include any successful results
        for result in partial_results:
            if result.success and result.result:
                answer += f"**{result.agent_type.title()} Agent:**\n{result.result}\n\n"

        answer += f"\n*Note: {error_message}*"

        return FallbackResponse(
            answer=answer,
            tier=tier,
            confidence="medium",
            limitations=[
                "Some agents failed to complete",
                "Answer may be incomplete",
                "Consider rephrasing your query",
            ],
            partial_results=partial_results,
            error_details=error_message,
            execution_time_ms=total_time_ms,
        )

    elif tier == FallbackTier.EPIC1_FALLBACK:
        # Epic 1 fallback response
        return FallbackResponse(
            answer="",  # Will be filled by fallback_to_basic_retrieval()
            tier=tier,
            confidence="low",
            limitations=[
                "Advanced analysis unavailable",
                "Showing basic search results only",
                "No multi-step reasoning performed",
            ],
            partial_results=partial_results,
            error_details=error_message,
            execution_time_ms=total_time_ms,
        )

    else:
        # Full workflow succeeded (no fallback needed)
        final_result = next(
            (r for r in reversed(partial_results) if r.success and r.agent_type == "synthesis"),
            None,
        )

        if final_result:
            return FallbackResponse(
                answer=str(final_result.result),
                tier=FallbackTier.FULL_WORKFLOW,
                confidence="high",
                limitations=[],
                partial_results=partial_results,
                execution_time_ms=total_time_ms,
            )
        else:
            # No synthesis result, but workflow "succeeded"
            return FallbackResponse(
                answer="Workflow completed but no final synthesis available.",
                tier=FallbackTier.PARTIAL_WORKFLOW,
                confidence="low",
                limitations=["No synthesis agent result"],
                partial_results=partial_results,
                execution_time_ms=total_time_ms,
            )


async def handle_workflow_failure(
    query: str,
    complexity: QueryComplexity,
    partial_results: list[AgentResult],
    error: Exception,
    total_time_ms: int,
) -> FallbackResponse:
    """Handle workflow failure with graceful degradation (AC8: 4.2, 4.3, 4.4).

    Implements tiered fallback strategy:
    1. Try to use partial results if any agents succeeded
    2. Fall back to Epic 1 basic retrieval if all agents failed

    Args:
        query: Original user query
        complexity: Query complexity classification
        partial_results: Partial results from agents that succeeded
        error: Exception that caused workflow failure
        total_time_ms: Total workflow execution time

    Returns:
        FallbackResponse with best available answer
    """
    error_message = str(error)
    error_type = type(error).__name__

    logger.warning(
        "Workflow failure - initiating graceful degradation",
        extra={
            "query": query,
            "complexity": complexity,
            "error_type": error_type,
            "error_message": error_message[:200],
            "partial_result_count": len(partial_results),
        },
    )

    # Check if any agents succeeded
    successful_results = [r for r in partial_results if r.success]

    if successful_results:
        # Tier 2: Partial workflow results available
        logger.info(
            "Using partial workflow results",
            extra={"successful_agents": len(successful_results)},
        )

        fallback = format_fallback_response(
            query=query,
            tier=FallbackTier.PARTIAL_WORKFLOW,
            partial_results=partial_results,
            error_message=f"Workflow incomplete: {error_message}",
            total_time_ms=total_time_ms,
        )

        return fallback

    else:
        # Tier 3: All agents failed - fall back to Epic 1
        logger.warning(
            "All agents failed - falling back to Epic 1 basic retrieval",
            extra={"error_type": error_type},
        )

        try:
            basic_answer = await fallback_to_basic_retrieval(query)

            fallback = format_fallback_response(
                query=query,
                tier=FallbackTier.EPIC1_FALLBACK,
                partial_results=[],
                error_message=f"All agents failed: {error_message}",
                total_time_ms=total_time_ms,
            )
            fallback.answer = basic_answer

            return fallback

        except Exception as fallback_error:
            # Absolute failure - return error message
            logger.critical(
                "Epic 1 fallback also failed",
                extra={"error": str(fallback_error)},
            )

            return FallbackResponse(
                answer="I apologize, but I'm experiencing technical difficulties and cannot process your query at this time.",
                tier=FallbackTier.EPIC1_FALLBACK,
                confidence="low",
                limitations=["Complete system failure"],
                partial_results=[],
                error_details=f"Workflow failed ({error_message}), fallback also failed ({fallback_error})",
                execution_time_ms=total_time_ms,
            )
