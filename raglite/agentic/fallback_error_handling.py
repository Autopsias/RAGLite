"""Error classification and user-friendly messaging for fallback handling.

This module handles error classification, user-friendly error messages,
and alternative query suggestions (Story 3.7 AC2, AC4).
"""

from enum import Enum


class ErrorType(str, Enum):
    """Classification of workflow failure types (AC2)."""

    TIMEOUT = "timeout"  # Agent or workflow exceeded time limit
    CONNECTION_ERROR = "connection"  # Qdrant/DB connection failed
    API_FAILURE = "api_failure"  # LLM API (Claude/Mistral) error
    UNEXPECTED = "unexpected"  # Unknown/unexpected error


class FallbackTier(str, Enum):
    """Quality tier of fallback response (AC8)."""

    FULL_WORKFLOW = "full"  # All agents succeeded
    PARTIAL_WORKFLOW = "partial"  # Some agents succeeded
    EPIC1_FALLBACK = "epic1_fallback"  # Fell back to basic retrieval


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
    import asyncio

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
