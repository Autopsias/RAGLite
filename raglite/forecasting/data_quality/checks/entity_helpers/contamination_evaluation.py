"""Result evaluation for entity contamination checks."""

from __future__ import annotations

from raglite.forecasting.data_quality.check_result import CheckResult, CheckStatus
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def evaluate_contamination_result(
    variable: str,
    entity: str,
    fuzzy_count: int,
    exact_count: int,
    contaminated_entities: list[str],
) -> CheckResult:
    """Evaluate contamination check results and return appropriate status.

    Args:
        variable: Variable name
        entity: Entity name
        fuzzy_count: Count from fuzzy ILIKE match
        exact_count: Count from exact match
        contaminated_entities: Sample of contaminated entity names

    Returns:
        CheckResult with contamination status
    """
    # No data found for this entity
    if fuzzy_count == 0 and exact_count == 0:
        return CheckResult(
            check_name="entity_contamination",
            status=CheckStatus.WARN,
            message=f"No data found for entity '{entity}'",
            variable=variable,
            actual_value=0,
            severity=2,
        )

    # Calculate contamination ratio
    ratio = fuzzy_count / max(exact_count, 1)

    # Story 6.28: Use tolerance-based thresholds for contamination detection
    # - ratio <= 1.1 (10% tolerance): PASS - essentially no leakage
    # - ratio <= 1.5 (50% tolerance): WARN - minor leakage
    # - ratio > 1.5: FAIL - significant leakage
    if ratio <= 1.1:
        return CheckResult(
            check_name="entity_contamination",
            status=CheckStatus.PASS,
            message=f"Minimal contamination: fuzzy={fuzzy_count}, exact={exact_count} ({ratio:.1f}x)",
            variable=variable,
            actual_value=exact_count,
        )

    if ratio <= 1.5:
        return CheckResult(
            check_name="entity_contamination",
            status=CheckStatus.WARN,
            message=f"Minor leakage: fuzzy={fuzzy_count}, exact={exact_count} ({ratio:.1f}x)",
            variable=variable,
            actual_value=fuzzy_count,
            threshold=exact_count,
            severity=2,
        )

    # Significant contamination detected
    severity = 5 if ratio > 5 else (4 if ratio > 2 else 3)

    return CheckResult(
        check_name="entity_contamination",
        status=CheckStatus.FAIL,
        message=f"Leakage detected: fuzzy={fuzzy_count}, exact={exact_count} ({ratio:.1f}x)",
        variable=variable,
        severity=severity,
        actual_value=fuzzy_count,
        threshold=exact_count,
        sample_rows=[{"entity": e} for e in contaminated_entities],
    )
