"""Metrics tracking and aggregation for workflow degradation.

This module implements metrics logging for workflow degradation tier tracking
(Story 3.7 AC5).
"""

import datetime
from typing import Any

from raglite.agentic.fallback_error_handling import ErrorType, FallbackTier
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


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
