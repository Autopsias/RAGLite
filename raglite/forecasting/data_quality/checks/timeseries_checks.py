"""Time series data quality checks.

Checks for frequency patterns, time index integrity, and missing data.
"""

from __future__ import annotations

from collections import Counter

import pandas as pd

from raglite.forecasting.data_quality.check_result import CheckResult, CheckStatus
from raglite.forecasting.data_quality.config import (
    Frequency,
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
    if unique_months == {12}:
        if config.frequency.allow_year_end_only:
            return CheckResult(
                check_name="effective_frequency",
                status=CheckStatus.PASS,
                message=f"Year-end only data (Dec) across {len(years)} years (allowed)",
                variable=variable,
                actual_value={"unique_months": list(unique_months), "years": len(years)},
            )
        else:
            return CheckResult(
                check_name="effective_frequency",
                status=CheckStatus.FAIL,
                message=f"Year-end only data: only December across {len(years)} years",
                variable=variable,
                severity=4,
                actual_value={"unique_months": list(unique_months), "years": len(years)},
            )

    # Check for partial year-end pattern (some years only have December)
    year_month_df = pd.DataFrame({"year": dates.dt.year, "month": dates.dt.month})
    year_months = year_month_df.groupby("year")["month"].apply(set).to_dict()
    year_end_only_years = [y for y, m in year_months.items() if m == {12}]

    if year_end_only_years and not config.frequency.allow_year_end_only:
        return CheckResult(
            check_name="effective_frequency",
            status=CheckStatus.WARN,
            message=f"Year-end only data in years: {year_end_only_years}",
            variable=variable,
            severity=3,
            actual_value={
                "year_end_only_years": year_end_only_years,
                "total_years": len(years),
            },
        )

    # Check expected frequency
    expected_freq = config.frequency.expected
    avg_points_per_year = len(dates) / max(len(years), 1)

    if expected_freq == Frequency.MONTHLY and avg_points_per_year < 6:
        return CheckResult(
            check_name="effective_frequency",
            status=CheckStatus.WARN,
            message=f"Low frequency: {avg_points_per_year:.1f} points/year (expected monthly)",
            variable=variable,
            severity=2,
            actual_value={"avg_points_per_year": avg_points_per_year},
        )

    if expected_freq == Frequency.QUARTERLY and avg_points_per_year < 2:
        return CheckResult(
            check_name="effective_frequency",
            status=CheckStatus.WARN,
            message=f"Low frequency: {avg_points_per_year:.1f} points/year (expected quarterly)",
            variable=variable,
            severity=2,
            actual_value={"avg_points_per_year": avg_points_per_year},
        )

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
    if "value" in data.columns:
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

    # Calculate gaps between consecutive dates
    gaps = dates.diff().dropna()

    # Expected frequency gap
    expected_freq = config.frequency.expected
    if expected_freq == Frequency.DAILY:
        max_allowed_gap = pd.Timedelta(days=7)
    elif expected_freq == Frequency.MONTHLY:
        max_allowed_gap = pd.Timedelta(days=config.frequency.max_gap_months * 31)
    elif expected_freq == Frequency.QUARTERLY:
        max_allowed_gap = pd.Timedelta(days=config.frequency.max_gap_months * 31)
    else:
        max_allowed_gap = pd.Timedelta(days=400)

    # Find large gaps
    large_gaps = gaps[gaps > max_allowed_gap]
    max_gap = gaps.max()
    max_gap_months = max_gap.days / 30

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

    return CheckResult(
        check_name="missing_data_pattern",
        status=CheckStatus.PASS,
        message=f"No large gaps detected (max: {max_gap_months:.1f} months)",
        variable=variable,
        actual_value=max_gap_months,
        threshold=config.frequency.max_gap_months,
    )
