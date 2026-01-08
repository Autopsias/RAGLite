"""Value-related data quality checks.

Checks for value ranges, unit consistency, and outliers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from raglite.forecasting.data_quality.check_result import CheckResult, CheckStatus
from raglite.forecasting.data_quality.config import (
    ExpectedSign,
    VariableQualityConfig,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def _validate_data_for_range_check(
    variable: str,
    data: pd.DataFrame,
) -> CheckResult | None:
    """Validate input data for range checking.

    Args:
        variable: Variable name
        data: DataFrame with 'value' column

    Returns:
        CheckResult if validation fails, None if data is valid
    """
    if data is None or data.empty:
        return CheckResult(
            check_name="value_range",
            status=CheckStatus.SKIP,
            message="No data to check",
            variable=variable,
        )

    if "value" not in data.columns:
        return CheckResult(
            check_name="value_range",
            status=CheckStatus.FAIL,
            message="Missing 'value' column in data",
            variable=variable,
            severity=3,
        )

    return None


def _check_min_bound(
    values: pd.Series,
    min_value: float,
    total_count: int,
) -> tuple[list[str], list[dict]]:
    """Check if values violate minimum bound.

    Args:
        values: Series of values to check
        min_value: Minimum acceptable value
        total_count: Total number of values (for percentage calculation)

    Returns:
        Tuple of (issue messages, sample violations)
    """
    below_min = values[values < min_value]
    if len(below_min) == 0:
        return [], []

    pct = len(below_min) / total_count * 100
    issues = [f"{len(below_min)} values ({pct:.1f}%) below min {min_value}"]
    sample_violations = [{"value": v, "issue": "below_min"} for v in below_min.head(3).tolist()]
    return issues, sample_violations


def _check_max_bound(
    values: pd.Series,
    max_value: float,
    total_count: int,
) -> tuple[list[str], list[dict]]:
    """Check if values violate maximum bound.

    Args:
        values: Series of values to check
        max_value: Maximum acceptable value
        total_count: Total number of values (for percentage calculation)

    Returns:
        Tuple of (issue messages, sample violations)
    """
    above_max = values[values > max_value]
    if len(above_max) == 0:
        return [], []

    pct = len(above_max) / total_count * 100
    issues = [f"{len(above_max)} values ({pct:.1f}%) above max {max_value}"]
    sample_violations = [{"value": v, "issue": "above_max"} for v in above_max.head(3).tolist()]
    return issues, sample_violations


def _check_sign_constraint(
    values: pd.Series,
    expected_sign: ExpectedSign,
    total_count: int,
) -> tuple[list[str], list[dict]]:
    """Check if values violate sign constraint.

    Args:
        values: Series of values to check
        expected_sign: Expected sign constraint
        total_count: Total number of values (for percentage calculation)

    Returns:
        Tuple of (issue messages, sample violations)
    """
    if expected_sign == ExpectedSign.POSITIVE:
        non_positive = values[values <= 0]
        if len(non_positive) == 0:
            return [], []
        pct = len(non_positive) / total_count * 100
        issues = [f"{len(non_positive)} values ({pct:.1f}%) non-positive"]
        sample_violations = [
            {"value": v, "issue": "non_positive"} for v in non_positive.head(3).tolist()
        ]
    elif expected_sign == ExpectedSign.NEGATIVE:
        non_negative = values[values >= 0]
        if len(non_negative) == 0:
            return [], []
        pct = len(non_negative) / total_count * 100
        issues = [f"{len(non_negative)} values ({pct:.1f}%) non-negative"]
        sample_violations = [
            {"value": v, "issue": "non_negative"} for v in non_negative.head(3).tolist()
        ]
    else:
        return [], []

    return issues, sample_violations


def _build_range_check_result(
    variable: str,
    values: pd.Series,
    issues: list[str],
    sample_violations: list[dict],
) -> CheckResult:
    """Build CheckResult from range validation findings.

    Args:
        variable: Variable name
        values: Series of validated values
        issues: List of issue messages
        sample_violations: List of sample violation details

    Returns:
        CheckResult with appropriate status and severity
    """
    if not issues:
        return CheckResult(
            check_name="value_range",
            status=CheckStatus.PASS,
            message=f"All {len(values)} values within expected range",
            variable=variable,
            actual_value={"min": float(values.min()), "max": float(values.max())},
        )

    # Determine severity based on violation rate
    violation_rate = len(sample_violations) / len(values)
    severity = 5 if violation_rate > 0.2 else (4 if violation_rate > 0.1 else 3)

    return CheckResult(
        check_name="value_range",
        status=CheckStatus.FAIL,
        message="; ".join(issues),
        variable=variable,
        severity=severity,
        actual_value={"min": float(values.min()), "max": float(values.max())},
        sample_rows=sample_violations[:5],
    )


async def check_value_range(
    variable: str,
    config: VariableQualityConfig,
    data: pd.DataFrame,
) -> CheckResult:
    """Check if values fall within expected range.

    Validates values against configured min/max bounds and sign constraints.

    Args:
        variable: Variable name
        config: Variable quality configuration
        data: DataFrame with 'value' column

    Returns:
        CheckResult with range validation status
    """
    # Validate input data
    validation_result = _validate_data_for_range_check(variable, data)
    if validation_result is not None:
        return validation_result

    values = data["value"].dropna()
    if len(values) == 0:
        return CheckResult(
            check_name="value_range",
            status=CheckStatus.WARN,
            message="All values are null",
            variable=variable,
            severity=2,
        )

    range_config = config.value_range
    issues = []
    sample_violations = []

    # Check minimum bound
    if range_config.min_value is not None:
        min_issues, min_samples = _check_min_bound(values, range_config.min_value, len(values))
        issues.extend(min_issues)
        sample_violations.extend(min_samples)

    # Check maximum bound
    if range_config.max_value is not None:
        max_issues, max_samples = _check_max_bound(values, range_config.max_value, len(values))
        issues.extend(max_issues)
        sample_violations.extend(max_samples)

    # Check sign constraint
    sign_issues, sign_samples = _check_sign_constraint(
        values, range_config.expected_sign, len(values)
    )
    issues.extend(sign_issues)
    sample_violations.extend(sign_samples)

    return _build_range_check_result(variable, values, issues, sample_violations)


async def check_unit_consistency(
    variable: str,
    config: VariableQualityConfig,
    data: pd.DataFrame,
) -> CheckResult:
    """Check for unit/scale consistency issues.

    Detects 1000x scale mismatches by comparing median to expected reference.

    Args:
        variable: Variable name
        config: Variable quality configuration
        data: DataFrame with 'value' column

    Returns:
        CheckResult with unit consistency status
    """
    if not config.value_range.detect_scale_mismatch:
        return CheckResult(
            check_name="unit_consistency",
            status=CheckStatus.SKIP,
            message="Scale mismatch detection not configured",
            variable=variable,
        )

    if config.value_range.scale_reference_median is None:
        return CheckResult(
            check_name="unit_consistency",
            status=CheckStatus.SKIP,
            message="No reference median configured",
            variable=variable,
        )

    if data is None or data.empty or "value" not in data.columns:
        return CheckResult(
            check_name="unit_consistency",
            status=CheckStatus.SKIP,
            message="No data to check",
            variable=variable,
        )

    values = data["value"].dropna()
    if len(values) == 0:
        return CheckResult(
            check_name="unit_consistency",
            status=CheckStatus.SKIP,
            message="All values are null",
            variable=variable,
        )

    actual_median = float(values.median())
    expected_median = config.value_range.scale_reference_median

    # Handle zero/near-zero expected median
    if abs(expected_median) < 0.001:
        return CheckResult(
            check_name="unit_consistency",
            status=CheckStatus.PASS,
            message="Reference median near zero, skipping ratio check",
            variable=variable,
            actual_value=actual_median,
        )

    ratio = abs(actual_median / expected_median)

    # Check for scale mismatch (roughly 1000x off)
    if ratio > 500 or ratio < 0.002:
        # Severe mismatch - likely wrong units
        return CheckResult(
            check_name="unit_consistency",
            status=CheckStatus.FAIL,
            message=f"Scale mismatch: median={actual_median:.2f}, expected~{expected_median:.2f} ({ratio:.0f}x off)",
            variable=variable,
            severity=5,
            actual_value=actual_median,
            threshold=expected_median,
        )

    if ratio > 50 or ratio < 0.02:
        # Moderate mismatch - worth investigating
        return CheckResult(
            check_name="unit_consistency",
            status=CheckStatus.WARN,
            message=f"Possible scale issue: median={actual_median:.2f}, expected~{expected_median:.2f} ({ratio:.1f}x)",
            variable=variable,
            severity=3,
            actual_value=actual_median,
            threshold=expected_median,
        )

    return CheckResult(
        check_name="unit_consistency",
        status=CheckStatus.PASS,
        message=f"Scale consistent: median={actual_median:.2f} (expected~{expected_median:.2f})",
        variable=variable,
        actual_value=actual_median,
        threshold=expected_median,
    )


async def check_robust_outliers(
    variable: str,
    config: VariableQualityConfig,
    data: pd.DataFrame,
    mad_threshold: float = 3.5,
) -> CheckResult:
    """Detect outliers using MAD-based robust z-scores.

    Uses Median Absolute Deviation (MAD) which is robust to outliers,
    unlike standard deviation.

    Args:
        variable: Variable name
        config: Variable quality configuration
        data: DataFrame with 'value' column
        mad_threshold: Number of MAD units to consider outlier (default 3.5)

    Returns:
        CheckResult with outlier detection status
    """
    if data is None or data.empty or "value" not in data.columns:
        return CheckResult(
            check_name="robust_outliers",
            status=CheckStatus.SKIP,
            message="No data to check",
            variable=variable,
        )

    # Keep only non-null rows for proper index alignment
    data_clean = data[data["value"].notna()].copy()
    if len(data_clean) < 3:
        return CheckResult(
            check_name="robust_outliers",
            status=CheckStatus.SKIP,
            message=f"Insufficient data points ({len(data_clean)} < 3)",
            variable=variable,
        )

    # Convert to float array to handle Decimal types from PostgreSQL
    values_float = data_clean["value"].astype(float).values

    # Calculate MAD-based z-scores
    median = float(np.median(values_float))
    mad = float(np.median(np.abs(values_float - median)))

    # Avoid division by zero
    if mad == 0:
        return CheckResult(
            check_name="robust_outliers",
            status=CheckStatus.PASS,
            message="No variance in data (MAD=0)",
            variable=variable,
            actual_value={"median": median, "mad": mad},
        )

    # Modified Z-score using MAD (0.6745 is the consistency constant for normal distribution)
    modified_z = 0.6745 * (values_float - median) / mad
    outlier_mask = np.abs(modified_z) > mad_threshold
    outlier_count = outlier_mask.sum()
    outlier_rate = outlier_count / len(values_float)

    if outlier_count == 0:
        return CheckResult(
            check_name="robust_outliers",
            status=CheckStatus.PASS,
            message=f"No outliers detected (MAD threshold={mad_threshold})",
            variable=variable,
            actual_value={"median": median, "mad": mad, "outliers": 0},
        )

    # Build sample outliers with their z-scores
    outlier_indices = np.where(outlier_mask)[0][:5]
    sample_outliers = []
    for idx in outlier_indices:
        val = values_float[idx]
        z = 0.6745 * (val - median) / mad
        sample_outliers.append({"value": float(val), "z_score": round(float(z), 2)})

    severity = 4 if outlier_rate > 0.1 else (3 if outlier_rate > 0.05 else 2)
    status = CheckStatus.WARN if outlier_rate < 0.1 else CheckStatus.FAIL

    return CheckResult(
        check_name="robust_outliers",
        status=status,
        message=f"{outlier_count} outliers ({outlier_rate:.1%}) detected",
        variable=variable,
        severity=severity,
        actual_value={"median": median, "mad": mad, "outliers": outlier_count},
        threshold=mad_threshold,
        sample_rows=sample_outliers,
    )
