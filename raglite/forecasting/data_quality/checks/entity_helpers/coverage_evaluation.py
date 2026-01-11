"""Result evaluation for entity coverage checks."""

from __future__ import annotations

from raglite.forecasting.data_quality.check_result import CheckResult, CheckStatus
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def evaluate_coverage_result(
    variable: str,
    entity: str,
    period_count: int,
    min_required: int,
) -> CheckResult:
    """Evaluate coverage check results and return appropriate status.

    Args:
        variable: Variable name
        entity: Entity name
        period_count: Number of periods found
        min_required: Minimum required periods

    Returns:
        CheckResult with coverage status
    """
    if period_count >= min_required:
        return CheckResult(
            check_name="entity_coverage",
            status=CheckStatus.PASS,
            message=f"Entity '{entity}' has {period_count} periods (>= {min_required})",
            variable=variable,
            actual_value=period_count,
            threshold=min_required,
        )

    if period_count > 0:
        return CheckResult(
            check_name="entity_coverage",
            status=CheckStatus.WARN,
            message=f"Low coverage: {period_count} periods (need {min_required})",
            variable=variable,
            actual_value=period_count,
            threshold=min_required,
            severity=2,
        )

    return CheckResult(
        check_name="entity_coverage",
        status=CheckStatus.FAIL,
        message=f"No data for entity '{entity}'",
        variable=variable,
        actual_value=0,
        threshold=min_required,
        severity=4,
    )
