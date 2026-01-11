"""Fallback recovery strategies and response formatting.

This module implements graceful degradation with tiered fallback
strategies (Story 3.5 AC8, Story 3.7 AC2, AC4).
"""

from pydantic import BaseModel, Field

from raglite.agentic.fallback_error_handling import (
    ErrorType,
    FallbackTier,
    classify_error,
    create_user_friendly_error_message,
    suggest_alternative_query,
)
from raglite.agentic.planner import AgentResult, QueryComplexity
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class FallbackResponse(BaseModel):
    """Response from fallback handler with tier metadata.

    Story 3.7 AC4: Enhanced with user-friendly error messaging and alternative query suggestions.
    """

    answer: str = Field(..., description="Final answer (may be partial or fallback)")
    tier: FallbackTier = Field(..., description="Quality tier of response")
    confidence: str = Field(..., description="Confidence level: high|medium|low|none")
    limitations: list[str] = Field(
        default_factory=list, description="Limitations or caveats about the answer"
    )
    partial_results: list[AgentResult] = Field(
        default_factory=list, description="Partial results from successful agents"
    )
    error_details: str | None = Field(
        default=None, description="Technical error details (internal)"
    )
    error_summary: str | None = Field(
        default=None, description="User-friendly error explanation (AC4)"
    )
    alternative_query: str | None = Field(
        default=None, description="Suggested alternative query (AC4)"
    )
    execution_time_ms: int = Field(..., description="Total execution time")


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


def _build_partial_fallback(
    query: str,
    partial_results: list[AgentResult],
    error_message: str,
    error_type: ErrorType,
    total_time_ms: int,
) -> FallbackResponse:
    """Create fallback response using partial workflow results."""
    fallback = format_fallback_response(
        query=query,
        tier=FallbackTier.PARTIAL_WORKFLOW,
        partial_results=partial_results,
        error_message=f"Workflow incomplete: {error_message}",
        total_time_ms=total_time_ms,
    )
    fallback.error_summary = create_user_friendly_error_message(
        error_type, FallbackTier.PARTIAL_WORKFLOW
    )
    fallback.alternative_query = suggest_alternative_query(query, error_type)
    return fallback


async def _build_epic1_fallback(
    query: str, error_message: str, error_type: ErrorType, total_time_ms: int
) -> FallbackResponse:
    """Create fallback response using Epic 1 basic retrieval."""
    basic_answer = await fallback_to_basic_retrieval(query)
    fallback = format_fallback_response(
        query=query,
        tier=FallbackTier.EPIC1_FALLBACK,
        partial_results=[],
        error_message=f"All agents failed: {error_message}",
        total_time_ms=total_time_ms,
    )
    fallback.answer = basic_answer
    fallback.error_summary = create_user_friendly_error_message(
        error_type, FallbackTier.EPIC1_FALLBACK
    )
    fallback.alternative_query = suggest_alternative_query(query, error_type)
    return fallback


def _build_complete_failure_response(
    error_message: str, fallback_error: Exception, total_time_ms: int
) -> FallbackResponse:
    """Create response for complete system failure."""
    return FallbackResponse(
        answer="I apologize, but I'm experiencing technical difficulties and cannot process your query at this time.",
        tier=FallbackTier.EPIC1_FALLBACK,
        confidence="none",
        limitations=["Complete system failure"],
        partial_results=[],
        error_details=f"Workflow failed ({error_message}), fallback also failed ({fallback_error})",
        error_summary="Our system is currently unavailable. Please try again in a few minutes.",
        alternative_query="Please try again later or contact support if the issue persists.",
        execution_time_ms=total_time_ms,
    )


async def handle_workflow_failure(
    query: str,
    complexity: QueryComplexity,
    partial_results: list[AgentResult],
    error: Exception,
    total_time_ms: int,
) -> FallbackResponse:
    """Handle workflow failure with graceful degradation (AC8).

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
    error_type = classify_error(error)

    logger.warning(
        "Workflow failure - initiating graceful degradation",
        extra={
            "query": query,
            "error_type": error_type.value,
            "partial_result_count": len(partial_results),
        },
    )

    successful_results = [r for r in partial_results if r.success]

    if successful_results:
        logger.info(
            "Using partial workflow results", extra={"successful_agents": len(successful_results)}
        )
        return _build_partial_fallback(
            query, partial_results, error_message, error_type, total_time_ms
        )

    logger.warning("All agents failed - falling back to Epic 1 basic retrieval")
    try:
        return await _build_epic1_fallback(query, error_message, error_type, total_time_ms)
    except Exception as fallback_error:
        logger.critical("Epic 1 fallback also failed", extra={"error": str(fallback_error)})
        return _build_complete_failure_response(error_message, fallback_error, total_time_ms)
