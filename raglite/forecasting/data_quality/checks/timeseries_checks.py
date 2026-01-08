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


def _get_date_column(data: pd.DataFrame) -> str | None:
    """Get the date column name from DataFrame.

    Args:
        data: DataFrame to check

    Returns:
        Column name ('date' or 'period') or None if not found
    """
    if "date" in data.columns:
        return "date"
    elif "period" in data.columns:
        return "period"
    return None


def _check_year_end_pattern(
    unique_months: set[int],
    years: int,
    variable: str,
    allow_year_end_only: bool,
) -> CheckResult | None:
    """Check if data only has December values (year-end pattern).

    Args:
        unique_months: Set of unique month numbers
        years: Number of years in data
        variable: Variable name
        allow_year_end_only: Whether year-end only is allowed

    Returns:
        CheckResult if year-end pattern detected, None otherwise
    """
    if unique_months == {12}:
        if allow_year_end_only:
            return CheckResult(
                check_name="effective_frequency",
                status=CheckStatus.PASS,
                message=f"Year-end only data (Dec) across {years} years (allowed)",
                variable=variable,
                actual_value={"unique_months": list(unique_months), "years": years},
            )
        else:
            return CheckResult(
                check_name="effective_frequency",
                status=CheckStatus.FAIL,
                message=f"Year-end only data: only December across {years} years",
                variable=variable,
                severity=4,
                actual_value={"unique_months": list(unique_months), "years": years},
            )
    return None


def _check_partial_year_end_pattern(
    dates: pd.Series,
    years: int,
    variable: str,
    allow_year_end_only: bool,
) -> CheckResult | None:
    """Check if some years only have December values.

    Args:
        dates: Datetime series
        years: Number of years
        variable: Variable name
        allow_year_end_only: Whether year-end only is allowed

    Returns:
        CheckResult if partial pattern detected, None otherwise
    """
    year_month_df = pd.DataFrame({"year": dates.dt.year, "month": dates.dt.month})
    year_months = year_month_df.groupby("year")["month"].apply(set).to_dict()
    year_end_only_years = [y for y, m in year_months.items() if m == {12}]

    if year_end_only_years and not allow_year_end_only:
        return CheckResult(
            check_name="effective_frequency",
            status=CheckStatus.WARN,
            message=f"Year-end only data in years: {year_end_only_years}",
            variable=variable,
            severity=3,
            actual_value={
                "year_end_only_years": year_end_only_years,
                "total_years": years,
            },
        )
    return None


def _validate_frequency_against_expected(
    avg_points_per_year: float,
    expected_freq: Frequency,
    variable: str,
) -> CheckResult | None:
    """Check if actual frequency matches expected frequency.

    Args:
        avg_points_per_year: Average data points per year
        expected_freq: Expected frequency
        variable: Variable name

    Returns:
        CheckResult if frequency too low, None otherwise
    """
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
    return None


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
    date_col = _get_date_column(data)
    if date_col is None:
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
    year_end_result = _check_year_end_pattern(
        unique_months,
        len(years),
        variable,
        config.frequency.allow_year_end_only,
    )
    if year_end_result is not None:
        return year_end_result

    # Check for partial year-end pattern (some years only have December)
    partial_result = _check_partial_year_end_pattern(
        dates,
        len(years),
        variable,
        config.frequency.allow_year_end_only,
    )
    if partial_result is not None:
        return partial_result

    # Check expected frequency
    expected_freq = config.frequency.expected
    avg_points_per_year = len(dates) / max(len(years), 1)

    freq_result = _validate_frequency_against_expected(
        avg_points_per_year,
        expected_freq,
        variable,
    )
    if freq_result is not None:
        return freq_result

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
    date_col = _get_date_column(data)
    if date_col is None:
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


def _calculate_max_gap_threshold(
    expected_freq: Frequency,
    max_gap_months: int,
) -> pd.Timedelta:
    """Calculate maximum allowed gap based on expected frequency.

    Args:
        expected_freq: Expected data frequency
        max_gap_months: Maximum gap in months

    Returns:
        Timedelta representing maximum allowed gap
    """
    if expected_freq == Frequency.DAILY:
        return pd.Timedelta(days=7)
    elif expected_freq == Frequency.MONTHLY:
        return pd.Timedelta(days=max_gap_months * 31)
    elif expected_freq == Frequency.QUARTERLY:
        return pd.Timedelta(days=max_gap_months * 31)
    else:
        return pd.Timedelta(days=400)


def _check_value_column_missing_rate(
    data: pd.DataFrame,
    max_missing_rate: float,
    variable: str,
) -> CheckResult | None:
    """Check missing rate in value column.

    Args:
        data: DataFrame with value column
        max_missing_rate: Maximum allowed missing rate
        variable: Variable name

    Returns:
        CheckResult if missing rate too high, None otherwise
    """
    if "value" not in data.columns:
        return None

    values = data["value"]
    missing_count = values.isna().sum()
    missing_rate = missing_count / len(values)

    if missing_rate > max_missing_rate:
        return CheckResult(
            check_name="missing_data_pattern",
            status=CheckStatus.FAIL,
            message=f"High missing rate: {missing_rate:.1%} (max {max_missing_rate:.1%})",
            variable=variable,
            severity=4,
            actual_value=missing_rate,
            threshold=max_missing_rate,
        )
    return None


def _analyze_time_series_gaps(
    dates: pd.Series,
    expected_freq: Frequency,
    max_gap_months: int,
    variable: str,
) -> CheckResult:
    """Analyze gaps in time series.

    Args:
        dates: Sorted datetime series
        expected_freq: Expected data frequency
        max_gap_months: Maximum gap in months
        variable: Variable name

    Returns:
        CheckResult with gap analysis
    """
    # Calculate gaps between consecutive dates
    gaps = dates.diff().dropna()
    max_allowed_gap = _calculate_max_gap_threshold(expected_freq, max_gap_months)

    # Find large gaps
    large_gaps = gaps[gaps > max_allowed_gap]
    max_gap = gaps.max()
    max_gap_months_actual = max_gap.days / 30

    if len(large_gaps) > 0:
        severity = 4 if max_gap_months_actual > max_gap_months * 2 else 3

        return CheckResult(
            check_name="missing_data_pattern",
            status=CheckStatus.WARN if severity < 4 else CheckStatus.FAIL,
            message=f"Max gap: {max_gap_months_actual:.1f} months (threshold: {max_gap_months})",
            variable=variable,
            severity=severity,
            actual_value=max_gap_months_actual,
            threshold=max_gap_months,
        )

    return CheckResult(
        check_name="missing_data_pattern",
        status=CheckStatus.PASS,
        message=f"No large gaps detected (max: {max_gap_months_actual:.1f} months)",
        variable=variable,
        actual_value=max_gap_months_actual,
        threshold=max_gap_months,
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
    value_result = _check_value_column_missing_rate(
        data,
        config.max_missing_rate,
        variable,
    )
    if value_result is not None:
        return value_result

    # Check for gaps in time series
    date_col = _get_date_column(data)

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

    return _analyze_time_series_gaps(
        dates,
        config.frequency.expected,
        config.frequency.max_gap_months,
        variable,
    )
