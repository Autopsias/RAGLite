"""Graceful degradation and fallback handling for agentic workflows.

This module implements timeout handling and fallback mechanisms for Story 3.5
to ensure workflows always return useful results even when agents fail (AC8).

Story 3.7 enhancements:
- Enhanced error classification (AC2)
- User-friendly error messages (AC4)
- Alternative query suggestions (AC4)
- Metrics tracking (AC5)
- Workflow-level timeout handling (AC1)

Pattern: Error Fallback Pattern from epic-3-agent-patterns.md
"""

import asyncio
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from raglite.agentic.planner import AgentResult, QueryComplexity
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


# Story 3.7: AC2 - Enhanced error classification
class ErrorType(str, Enum):
    """Classification of workflow failure types (AC2)."""

    TIMEOUT = "timeout"  # Agent or workflow exceeded time limit
    CONNECTION_ERROR = "connection"  # Qdrant/DB connection failed
    API_FAILURE = "api_failure"  # LLM API (Claude/Mistral) error
    UNEXPECTED = "unexpected"  # Unknown/unexpected error


def classify_error(error: Exception) -> ErrorType:
    """Classify error by type for structured logging (AC2).

    Args:
        error: Exception that occurred during workflow

    Returns:
        ErrorType classification

    Example:
        >>> classify_error(TimeoutError())
        ErrorType.TIMEOUT
        >>> classify_error(ConnectionError())
        ErrorType.CONNECTION_ERROR
    """
    error_name = type(error).__name__
    error_str = str(error).lower()

    # Timeout errors
    if isinstance(error, (TimeoutError, asyncio.TimeoutError)):
        return ErrorType.TIMEOUT

    # Connection errors (Qdrant, PostgreSQL, network)
    if isinstance(error, ConnectionError) or "connection" in error_str or "qdrant" in error_str:
        return ErrorType.CONNECTION_ERROR

    # LLM API failures (Anthropic, Mistral)
    if (
        "api" in error_str
        or "http" in error_str
        or "anthropic" in error_str
        or "mistral" in error_str
        or error_name in ("HTTPError", "APIError", "RateLimitError")
    ):
        return ErrorType.API_FAILURE

    # Unknown/unexpected
    return ErrorType.UNEXPECTED


def suggest_alternative_query(query: str, error_type: ErrorType) -> str | None:
    """Suggest alternative query based on failure type (AC4).

    Args:
        query: Original user query
        error_type: Type of error that occurred

    Returns:
        Alternative query suggestion, or None if no suggestion available

    Example:
        >>> suggest_alternative_query("Calculate YoY growth...", ErrorType.TIMEOUT)
        "Try a simpler query like 'What was Q3 2024 revenue?'"
    """
    if error_type == ErrorType.TIMEOUT:
        # Timeout: suggest simpler query
        return "Try a simpler query like 'What was Q3 revenue?' or break into smaller questions"

    if error_type in (ErrorType.API_FAILURE, ErrorType.CONNECTION_ERROR):
        # API/connection issues: suggest retry
        return "Please wait a moment and try again, or rephrase your question"

    # No specific suggestion
    return None


class FallbackTier(str, Enum):
    """Quality tier of fallback response (AC8)."""

    FULL_WORKFLOW = "full"  # All agents succeeded
    PARTIAL_WORKFLOW = "partial"  # Some agents succeeded
    EPIC1_FALLBACK = "epic1_fallback"  # Fell back to basic retrieval


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


def create_user_friendly_error_message(error_type: ErrorType, tier: FallbackTier) -> str:
    """Create user-friendly error message without technical jargon (AC4).

    Args:
        error_type: Classification of error that occurred
        tier: Fallback tier that was triggered

    Returns:
        User-friendly error explanation

    Example:
        >>> create_user_friendly_error_message(ErrorType.TIMEOUT, FallbackTier.PARTIAL_WORKFLOW)
        "Our analysis system is experiencing delays, but we found some results."
    """
    # Story 3.7 AC4: No technical jargon - user-friendly explanations
    if error_type == ErrorType.TIMEOUT:
        if tier == FallbackTier.PARTIAL_WORKFLOW:
            return "Our analysis system is experiencing delays, but we found some results."
        elif tier == FallbackTier.EPIC1_FALLBACK:
            return "Our advanced analysis system is taking longer than usual. Here are basic search results."
        else:
            return "The analysis took longer than expected."

    elif error_type == ErrorType.API_FAILURE:
        if tier == FallbackTier.PARTIAL_WORKFLOW:
            return "Our AI service is temporarily unavailable, but we have partial results."
        elif tier == FallbackTier.EPIC1_FALLBACK:
            return "Our AI analysis service is temporarily unavailable. Here are the documents we found."
        else:
            return "Our AI service is experiencing issues."

    elif error_type == ErrorType.CONNECTION_ERROR:
        if tier == FallbackTier.PARTIAL_WORKFLOW:
            return "We're experiencing database connectivity issues, but found some results."
        elif tier == FallbackTier.EPIC1_FALLBACK:
            return "We're experiencing database issues. Here are results from our backup search."
        else:
            return "Database connectivity issues detected."

    else:  # UNEXPECTED
        if tier == FallbackTier.PARTIAL_WORKFLOW:
            return "We encountered an issue processing your query, but have partial results."
        elif tier == FallbackTier.EPIC1_FALLBACK:
            return "We encountered an issue with advanced analysis. Here are basic search results."
        else:
            return "An unexpected issue occurred while processing your query."


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

    Story 3.7 AC2, AC4: Enhanced with error classification and user-friendly messaging.

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
    error_type_enum = classify_error(error)  # AC2: Enhanced error classification

    logger.warning(  # AC2: WARNING level (graceful degradation expected)
        "Workflow failure - initiating graceful degradation",
        extra={
            "query": query,
            "complexity": complexity,
            "error_type": error_type_enum.value,  # AC2: Structured error_type field
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

        # Story 3.7 AC4: Add user-friendly error summary and alternative query
        fallback.error_summary = create_user_friendly_error_message(
            error_type_enum, FallbackTier.PARTIAL_WORKFLOW
        )
        fallback.alternative_query = suggest_alternative_query(query, error_type_enum)

        return fallback

    else:
        # Tier 3: All agents failed - fall back to Epic 1
        logger.warning(
            "All agents failed - falling back to Epic 1 basic retrieval",
            extra={"error_type": error_type_enum.value},  # AC2: Structured error_type
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

            # Story 3.7 AC4: Add user-friendly error summary and alternative query
            fallback.error_summary = create_user_friendly_error_message(
                error_type_enum, FallbackTier.EPIC1_FALLBACK
            )
            fallback.alternative_query = suggest_alternative_query(query, error_type_enum)

            return fallback

        except Exception as fallback_error:
            # Absolute failure - return error message
            logger.critical(
                "Epic 1 fallback also failed",
                extra={
                    "error": str(fallback_error),
                    "error_type": classify_error(fallback_error).value,  # AC2
                },
            )

            # Story 3.7 AC4: User-friendly complete failure message
            return FallbackResponse(
                answer="I apologize, but I'm experiencing technical difficulties and cannot process your query at this time.",
                tier=FallbackTier.EPIC1_FALLBACK,
                confidence="none",  # AC4: Added "none" confidence level
                limitations=["Complete system failure"],
                partial_results=[],
                error_details=f"Workflow failed ({error_message}), fallback also failed ({fallback_error})",
                error_summary="Our system is currently unavailable. Please try again in a few minutes.",
                alternative_query="Please try again later or contact support if the issue persists.",
                execution_time_ms=total_time_ms,
            )


# Story 3.7: AC1 - Workflow-level timeout handling
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


# Story 3.7: AC5 - Metrics tracking for workflow degradation
def log_workflow_metrics(
    query_id: str,
    query: str,
    tier: FallbackTier,
    confidence: str,
    execution_time_ms: int,
    agents_invoked: list[str],
    agents_failed: list[str],
    error_type: ErrorType | None = None,
) -> None:
    """Log workflow metrics for degradation tier tracking (AC5).

    Logs structured metrics that enable:
    - Monitoring dashboards (Epic 5 CloudWatch)
    - A/B testing and workflow optimization
    - Alert triggering (Tier 1 <90% or Tier 4 >1%)

    Args:
        query_id: Unique query identifier for correlation
        query: Original user query (for debugging)
        tier: Fallback tier that was used
        confidence: Answer confidence level
        execution_time_ms: Total workflow execution time
        agents_invoked: List of agents that were invoked
        agents_failed: List of agents that failed
        error_type: Error type if workflow failed (optional)

    Example:
        >>> log_workflow_metrics(
        ...     query_id="abc123",
        ...     query="Calculate YoY growth",
        ...     tier=FallbackTier.FULL_WORKFLOW,
        ...     confidence="high",
        ...     execution_time_ms=11500,
        ...     agents_invoked=["retrieval", "analysis", "synthesis"],
        ...     agents_failed=[],
        ...     error_type=None
        ... )
    """
    import datetime

    from raglite.shared.models import WorkflowMetrics

    # Create metrics object
    metrics = WorkflowMetrics(
        query_id=query_id,
        query=query[:200],  # Truncate long queries for logging
        tier=tier.value,
        confidence=confidence,
        execution_time_ms=execution_time_ms,
        agents_invoked=agents_invoked,
        agents_failed=agents_failed,
        error_type=error_type.value if error_type else None,
        timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
    )

    # AC5: Log metrics with structured metadata for aggregation
    logger.info(
        "Workflow metrics",
        extra={
            "query_id": metrics.query_id,
            "tier": metrics.tier,
            "confidence": metrics.confidence,
            "execution_time_ms": metrics.execution_time_ms,
            "agents_invoked": metrics.agents_invoked,
            "agents_failed": metrics.agents_failed,
            "error_type": metrics.error_type,
            "timestamp": metrics.timestamp,
            # For CloudWatch Insights / DataDog aggregation:
            "metric_type": "workflow_degradation",
            "tier_1_success": 1 if tier == FallbackTier.FULL_WORKFLOW else 0,
            "tier_2_fallback": 1 if tier == FallbackTier.PARTIAL_WORKFLOW else 0,
            "tier_4_epic1": 1 if tier == FallbackTier.EPIC1_FALLBACK else 0,
        },
    )


def calculate_tier_rates(workflow_logs: list[dict[str, Any]]) -> dict[str, float]:
    """Calculate tier success rates from workflow logs (AC5 metrics aggregation).

    This helper function aggregates metrics for monitoring dashboards.
    Target rates: Tier 1 ≥95%, Tier 2 <5%, Tier 3 <1%, Tier 4 <0.1%

    Args:
        workflow_logs: List of workflow log entries with 'tier' field

    Returns:
        Dictionary with tier rates:
        - tier_1_success_rate: Percentage of full orchestration workflows (target ≥95%)
        - tier_2_fallback_rate: Percentage of partial workflows (target <5%)
        - tier_4_epic1_rate: Percentage of Epic 1 fallbacks (target <0.1%)

    Example:
        >>> logs = [
        ...     {"tier": "full"},
        ...     {"tier": "full"},
        ...     {"tier": "partial"},
        ... ]
        >>> rates = calculate_tier_rates(logs)
        >>> rates["tier_1_success_rate"]
        66.67  # 2 out of 3 workflows succeeded
    """
    if not workflow_logs:
        return {
            "tier_1_success_rate": 0.0,
            "tier_2_fallback_rate": 0.0,
            "tier_4_epic1_rate": 0.0,
        }

    total = len(workflow_logs)
    tier_1_count = sum(1 for log in workflow_logs if log.get("tier") == "full")
    tier_2_count = sum(1 for log in workflow_logs if log.get("tier") == "partial")
    tier_4_count = sum(1 for log in workflow_logs if log.get("tier") == "epic1_fallback")

    return {
        "tier_1_success_rate": round((tier_1_count / total) * 100, 2),
        "tier_2_fallback_rate": round((tier_2_count / total) * 100, 2),
        "tier_4_epic1_rate": round((tier_4_count / total) * 100, 2),
    }
