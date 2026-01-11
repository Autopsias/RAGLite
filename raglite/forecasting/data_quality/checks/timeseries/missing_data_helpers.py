"""Helper functions for missing data pattern analysis."""

from __future__ import annotations

import pandas as pd

from raglite.forecasting.data_quality.check_result import CheckResult, CheckStatus
from raglite.forecasting.data_quality.config import (
    Frequency,
    VariableQualityConfig,
)


def check_value_missing_rate(
    data: pd.DataFrame,
    config: VariableQualityConfig,
    variable: str,
) -> CheckResult | None:
    """Check missing rate in value column.

    Args:
        data: DataFrame with value column
        config: Variable quality configuration
        variable: Variable name

    Returns:
        CheckResult if missing rate too high, None otherwise
    """
    if "value" not in data.columns:
        return None

    values = data["value"]
    missing_count = values.isna().sum()
    missing_rate = missing_count / len(values)

    if missing_rate > config.max_missing_rate:
        return CheckResult(
            check_name="missing_data_pattern",
            status=CheckStatus.FAIL,
            message=f"High missing rate: {missing_rate:.1%} (max {config.max_missing_rate:.1%})",
            variable=variable,
            severity=4,
            actual_value=missing_rate,
            threshold=config.max_missing_rate,
        )
    return None


def calculate_max_gap_months(
    dates: pd.Series, config: VariableQualityConfig
) -> tuple[pd.Timedelta, float]:
    """Calculate maximum allowed gap based on expected frequency.

    Args:
        dates: Sorted datetime series
        config: Variable quality configuration

    Returns:
        Tuple of (max_allowed_gap, max_gap_months)
    """
    gaps = dates.diff().dropna()
    max_gap = gaps.max()
    max_gap_months = max_gap.days / 30

    expected_freq = config.frequency.expected
    if expected_freq == Frequency.DAILY:
        max_allowed_gap = pd.Timedelta(days=7)
    elif expected_freq == Frequency.MONTHLY:
        max_allowed_gap = pd.Timedelta(days=config.frequency.max_gap_months * 31)
    elif expected_freq == Frequency.QUARTERLY:
        max_allowed_gap = pd.Timedelta(days=config.frequency.max_gap_months * 31)
    else:
        max_allowed_gap = pd.Timedelta(days=400)

    return max_allowed_gap, max_gap_months


def check_time_gaps(
    dates: pd.Series,
    config: VariableQualityConfig,
    variable: str,
) -> CheckResult | None:
    """Check for large gaps in time series.

    Args:
        dates: Sorted datetime series
        config: Variable quality configuration
        variable: Variable name

    Returns:
        CheckResult if large gaps detected, None otherwise
    """
    max_allowed_gap, max_gap_months = calculate_max_gap_months(dates, config)

    gaps = dates.diff().dropna()
    large_gaps = gaps[gaps > max_allowed_gap]

    if len(large_gaps) > 0:
        severity = 4 if max_gap_months > config.frequency.max_gap_months * 2 else 3
        return CheckResult(
            check_name="missing_data_pattern",
            status=CheckStatus.WARN if severity < 4 else CheckStatus.FAIL,
            message=f"Max gap: {max_gap_months:.1f} months (threshold: {config.frequency.max_gap_months})",
            variable=variable,
            severity=severity,
            actual_value=max_gap_months,
            threshold=config.frequency.max_gap_months,
        )
    return None
