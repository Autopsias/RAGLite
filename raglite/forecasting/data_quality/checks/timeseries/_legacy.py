"""Time series data quality checks.

Checks for frequency patterns, time index integrity, and missing data.
"""

from __future__ import annotations

from collections import Counter

import pandas as pd

from raglite.forecasting.data_quality.check_result import CheckResult, CheckStatus
from raglite.forecasting.data_quality.checks.timeseries.frequency_helpers import (
    check_expected_frequency,
    check_partial_year_end_pattern,
    check_year_end_only_pattern,
)
from raglite.forecasting.data_quality.checks.timeseries.missing_data_helpers import (
    calculate_max_gap_months,
    check_time_gaps,
    check_value_missing_rate,
)
from raglite.forecasting.data_quality.config import (
    VariableQualityConfig,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def check_effective_frequency(
    variable: str,
    config: VariableQualityConfig,
    data: pd.DataFrame,
) -> CheckResult:
    """Check effective data frequency and detect year-end only patterns.

    Detects cases where monthly data only has December values (year-end reporting).

    Args:
        variable: Variable name
        config: Variable quality configuration
        data: DataFrame with 'date' or 'period' column

    Returns:
        CheckResult with frequency analysis
    """
    if data is None or data.empty:
        return CheckResult(
            check_name="effective_frequency",
            status=CheckStatus.SKIP,
            message="No data to check",
            variable=variable,
        )

    # Get date column
    date_col = None
    if "date" in data.columns:
        date_col = "date"
    elif "period" in data.columns:
        date_col = "period"
    else:
        return CheckResult(
            check_name="effective_frequency",
            status=CheckStatus.SKIP,
            message="No date/period column found",
            variable=variable,
        )

    # Convert to datetime if needed
    dates = pd.to_datetime(data[date_col], errors="coerce")
    dates = dates.dropna()

    if len(dates) < 2:
        return CheckResult(
            check_name="effective_frequency",
            status=CheckStatus.SKIP,
            message=f"Insufficient date points ({len(dates)} < 2)",
            variable=variable,
        )

    # Analyze month distribution
    months = dates.dt.month
    month_counts = Counter(months)
    unique_months = set(months)
    years = dates.dt.year.unique()

    # Check for year-end only pattern (December only)
    year_end_result = check_year_end_only_pattern(months, years, config, variable)
    if year_end_result is not None:
        return year_end_result

    # Check for partial year-end pattern (some years only have December)
    partial_year_end_result = check_partial_year_end_pattern(dates, years, config, variable)
    if partial_year_end_result is not None:
        return partial_year_end_result

    # Check expected frequency
    freq_result = check_expected_frequency(dates, unique_months, config, variable)
    if freq_result is not None:
        return freq_result

    # All checks passed
    avg_points_per_year = len(dates) / max(len(years), 1)
    return CheckResult(
        check_name="effective_frequency",
        status=CheckStatus.PASS,
        message=f"Frequency OK: {avg_points_per_year:.1f} points/year, {len(unique_months)} unique months",
        variable=variable,
        actual_value={
            "avg_points_per_year": avg_points_per_year,
            "unique_months": len(unique_months),
            "month_distribution": dict(month_counts),
        },
    )


async def check_time_index_integrity(
    variable: str,
    config: VariableQualityConfig,
    data: pd.DataFrame,
) -> CheckResult:
    """Check time index for duplicates and monotonic ordering.

    Args:
        variable: Variable name
        config: Variable quality configuration
        data: DataFrame with date column

    Returns:
        CheckResult with time index integrity status
    """
    if data is None or data.empty:
        return CheckResult(
            check_name="time_index_integrity",
            status=CheckStatus.SKIP,
            message="No data to check",
            variable=variable,
        )

    # Get date column
    date_col = None
    if "date" in data.columns:
        date_col = "date"
    elif "period" in data.columns:
        date_col = "period"
    else:
        return CheckResult(
            check_name="time_index_integrity",
            status=CheckStatus.SKIP,
            message="No date/period column found",
            variable=variable,
        )

    dates = pd.to_datetime(data[date_col], errors="coerce")
    valid_dates = dates.dropna()

    if len(valid_dates) == 0:
        return CheckResult(
            check_name="time_index_integrity",
            status=CheckStatus.FAIL,
            message="No valid dates found",
            variable=variable,
            severity=4,
        )

    issues = []

    # Check for duplicates
    duplicates = valid_dates[valid_dates.duplicated(keep=False)]
    if len(duplicates) > 0:
        dup_count = len(duplicates.unique())
        issues.append(f"{dup_count} duplicate dates")

    # Check for non-monotonic order
    sorted_dates = valid_dates.sort_values()
    if not valid_dates.equals(sorted_dates):
        # Check if at least mostly sorted
        out_of_order = (valid_dates.values[1:] < valid_dates.values[:-1]).sum()
        if out_of_order > 0:
            issues.append(f"{out_of_order} out-of-order transitions")

    # Check for null conversion rate
    null_count = len(dates) - len(valid_dates)
    if null_count > 0:
        null_rate = null_count / len(dates)
        if null_rate > 0.1:
            issues.append(f"{null_count} unparseable dates ({null_rate:.1%})")

    if not issues:
        return CheckResult(
            check_name="time_index_integrity",
            status=CheckStatus.PASS,
            message=f"Time index OK: {len(valid_dates)} valid dates, no duplicates",
            variable=variable,
            actual_value={
                "valid_dates": len(valid_dates),
                "date_range": f"{valid_dates.min()} to {valid_dates.max()}",
            },
        )

    severity = 4 if len(duplicates) > len(valid_dates) * 0.1 else 3

    return CheckResult(
        check_name="time_index_integrity",
        status=CheckStatus.WARN if severity < 4 else CheckStatus.FAIL,
        message="; ".join(issues),
        variable=variable,
        severity=severity,
        actual_value={
            "valid_dates": len(valid_dates),
            "duplicate_dates": len(duplicates.unique()) if len(duplicates) > 0 else 0,
        },
    )


async def check_missing_data_pattern(
    variable: str,
    config: VariableQualityConfig,
    data: pd.DataFrame,
) -> CheckResult:
    """Check missing data rate and patterns.

    Identifies gaps in time series and overall missing rate.

    Args:
        variable: Variable name
        config: Variable quality configuration
        data: DataFrame with date and value columns

    Returns:
        CheckResult with missing data analysis
    """
    if data is None or data.empty:
        return CheckResult(
            check_name="missing_data_pattern",
            status=CheckStatus.SKIP,
            message="No data to check",
            variable=variable,
        )

    # Check value column missing rate
    missing_rate_result = check_value_missing_rate(data, config, variable)
    if missing_rate_result is not None:
        return missing_rate_result

    # Check for gaps in time series
    date_col = "date" if "date" in data.columns else "period" if "period" in data.columns else None

    if date_col is None:
        return CheckResult(
            check_name="missing_data_pattern",
            status=CheckStatus.SKIP,
            message="No date column for gap analysis",
            variable=variable,
        )

    dates = pd.to_datetime(data[date_col], errors="coerce").dropna().sort_values()

    if len(dates) < 2:
        return CheckResult(
            check_name="missing_data_pattern",
            status=CheckStatus.SKIP,
            message="Insufficient dates for gap analysis",
            variable=variable,
        )

    # Check for large gaps
    gap_result = check_time_gaps(dates, config, variable)
    if gap_result is not None:
        return gap_result

    # No gaps detected
    _, max_gap_months = calculate_max_gap_months(dates, config)
    return CheckResult(
        check_name="missing_data_pattern",
        status=CheckStatus.PASS,
        message=f"No large gaps detected (max: {max_gap_months:.1f} months)",
        variable=variable,
        actual_value=max_gap_months,
        threshold=config.frequency.max_gap_months,
    )
