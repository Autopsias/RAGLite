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

NOTE: This is a facade module that re-exports all functionality from specialized modules.
"""

# Error handling and classification
from raglite.agentic.fallback_error_handling import (
    ErrorType,
    FallbackTier,
    classify_error,
    create_user_friendly_error_message,
    suggest_alternative_query,
)

# Timeout execution wrappers
from raglite.agentic.fallback_execution import (
    execute_with_timeout,
    execute_workflow_with_timeout,
)

# Metrics tracking
from raglite.agentic.fallback_metrics import (
    calculate_tier_rates,
    log_workflow_metrics,
)

# Recovery strategies and response formatting
from raglite.agentic.fallback_recovery import (
    FallbackResponse,
    fallback_to_basic_retrieval,
    format_fallback_response,
    handle_workflow_failure,
)

__all__ = [
    # Error types and classification
    "ErrorType",
    "FallbackTier",
    "classify_error",
    "suggest_alternative_query",
    "create_user_friendly_error_message",
    # Response model
    "FallbackResponse",
    # Execution wrappers
    "execute_with_timeout",
    "execute_workflow_with_timeout",
    # Recovery functions
    "fallback_to_basic_retrieval",
    "format_fallback_response",
    "handle_workflow_failure",
    # Metrics
    "log_workflow_metrics",
    "calculate_tier_rates",
]
