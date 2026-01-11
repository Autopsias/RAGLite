"""Helper functions for frequency analysis."""

from __future__ import annotations

import pandas as pd

from raglite.forecasting.data_quality.check_result import CheckResult, CheckStatus
from raglite.forecasting.data_quality.config import (
    Frequency,
    VariableQualityConfig,
)


def check_year_end_only_pattern(
    months: pd.Series,
    years: pd.Series,
    config: VariableQualityConfig,
    variable: str,
) -> CheckResult | None:
    """Check if data is year-end only (December only).

    Args:
        months: Series of month values
        years: Series of unique years
        config: Variable quality configuration
        variable: Variable name

    Returns:
        CheckResult if year-end only pattern detected, None otherwise
    """
    unique_months = set(months)

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
    return None


def check_partial_year_end_pattern(
    dates: pd.Series,
    years: pd.Series,
    config: VariableQualityConfig,
    variable: str,
) -> CheckResult | None:
    """Check if some years only have December data.

    Args:
        dates: Series of datetime values
        years: Series of unique years
        config: Variable quality configuration
        variable: Variable name

    Returns:
        CheckResult if partial year-end pattern detected, None otherwise
    """
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
    return None


def check_expected_frequency(
    dates: pd.Series,
    unique_months: set,
    config: VariableQualityConfig,
    variable: str,
) -> CheckResult | None:
    """Check if data meets expected frequency requirements.

    Args:
        dates: Series of datetime values
        unique_months: Set of unique months present
        config: Variable quality configuration
        variable: Variable name

    Returns:
        CheckResult if frequency doesn't match expectation, None otherwise
    """
    expected_freq = config.frequency.expected
    years = dates.dt.year.unique()
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

    return None
