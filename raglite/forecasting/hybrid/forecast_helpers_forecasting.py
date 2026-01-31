"""Forecast generation helpers for monthly and quarterly forecasts.

Story 8: Refactoring helpers - forecast point generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from raglite.forecasting.hybrid.preprocessing import _generate_future_regressors
from raglite.shared.models import ForecastPoint

if TYPE_CHECKING:
    from logging import Logger

    from prophet import Prophet


# Module-level constants
# Phase 3 Quality Fix (2026-01-29): Added cost metrics to prevent negative forecasts
# Variable Cost, Electricity Cost, Thermal Cost are always positive values
POSITIVE_ONLY_METRICS = {
    "ebitda",
    "revenue",
    "capacity_utilization",
    "sales_volume",
    # Cost metrics (Phase 3 fix)
    "variable_cost",
    "variable cost",
    "electricity_cost",
    "electrical energy",
    "thermal_cost",
    "thermal energy",
}


def detect_input_frequency(df: pd.DataFrame) -> bool:
    """Detect if input data is monthly frequency.

    Uses median of RECENT date differences to handle sparse historical data.

    Args:
        df: DataFrame with 'ds' column

    Returns:
        True if data appears to be monthly, False otherwise
    """
    if len(df) < 2:
        return False

    # Use last 5 date differences (or all if fewer than 5)
    num_recent = min(5, len(df) - 1)
    start_idx = len(df) - 1 - num_recent
    date_diffs: list[int] = [
        (df["ds"].iloc[i + 1] - df["ds"].iloc[i]).days for i in range(start_idx, len(df) - 1)
    ]
    median_diff: int = sorted(date_diffs)[len(date_diffs) // 2]
    return bool(25 <= median_diff <= 35)


def generate_monthly_forecast_points(
    model: Prophet,
    df: pd.DataFrame,
    periods_ahead: int,
    regressors_used: list[str],
    external_regressors: dict[str, pd.Series] | None,
    future_regressor_strategy: str,
    metric: str,
    logger: Logger,
) -> list[ForecastPoint]:
    """Generate monthly forecast points.

    Args:
        model: Fitted Prophet model
        df: DataFrame with 'ds', 'y' columns
        periods_ahead: Number of periods to forecast
        regressors_used: List of regressor names in model
        external_regressors: External regressor series
        future_regressor_strategy: Strategy for future values
        metric: Metric name
        logger: Logger instance

    Returns:
        List of ForecastPoint for monthly forecasts
    """
    future = model.make_future_dataframe(periods=periods_ahead, freq="MS")

    # Add regressor values to future dataframe
    if regressors_used and external_regressors:
        future_dates = pd.DatetimeIndex(future["ds"].tail(periods_ahead))
        extended = _generate_future_regressors(
            {k: v for k, v in external_regressors.items() if k in regressors_used},
            future_dates,
            strategy=future_regressor_strategy,
        )
        for name in regressors_used:
            if name in extended:
                reindexed = extended[name].reindex(future["ds"])
                reindexed = reindexed.ffill().bfill()
                future[name] = reindexed.values

    prophet_forecast = model.predict(future)
    forecast_months = prophet_forecast.tail(periods_ahead)

    # Build forecast points
    forecast_points = []
    for _, row in forecast_months.iterrows():
        month_name = row["ds"].strftime("%b %Y")
        forecast_points.append(
            ForecastPoint(
                date=row["ds"].to_pydatetime(),
                value=row["yhat"],
                lower=row["yhat_lower"],
                upper=row["yhat_upper"],
                label=month_name,
            )
        )

    # Clamp negative values for positive-only metrics
    if metric.lower() in POSITIVE_ONLY_METRICS:
        clamped_count = 0
        for i, point in enumerate(forecast_points):
            if point.value < 0:
                clamped_count += 1
                forecast_points[i] = ForecastPoint(
                    date=point.date,
                    value=0.0,
                    lower=max(0.0, point.lower),
                    upper=point.upper,
                    label=point.label,
                )
        if clamped_count > 0:
            logger.warning(
                f"Clamped {clamped_count} negative forecast values to 0",
                extra={"metric": metric, "clamped_count": clamped_count},
            )

    logger.debug(
        "Monthly forecast generated",
        extra={"periods": periods_ahead, "output_frequency": "monthly"},
    )

    return forecast_points


def generate_quarterly_from_monthly(
    model: Prophet,
    df: pd.DataFrame,
    periods_ahead: int,
    regressors_used: list[str],
    external_regressors: dict[str, pd.Series] | None,
    future_regressor_strategy: str,
    logger: Logger,
) -> list[ForecastPoint]:
    """Generate quarterly forecasts by aggregating monthly predictions.

    Args:
        model: Fitted Prophet model
        df: DataFrame with 'ds', 'y' columns
        periods_ahead: Number of quarters to forecast
        regressors_used: List of regressor names in model
        external_regressors: External regressor series
        future_regressor_strategy: Strategy for future values
        logger: Logger instance

    Returns:
        List of ForecastPoint for quarterly forecasts
    """
    monthly_periods = periods_ahead * 3  # 3 months per quarter
    future = model.make_future_dataframe(periods=monthly_periods, freq="MS")

    # Add regressor values to future dataframe
    if regressors_used and external_regressors:
        future_dates = pd.DatetimeIndex(future["ds"].tail(monthly_periods))
        extended = _generate_future_regressors(
            {k: v for k, v in external_regressors.items() if k in regressors_used},
            future_dates,
            strategy=future_regressor_strategy,
        )
        for name in regressors_used:
            if name in extended:
                reindexed = extended[name].reindex(future["ds"])
                reindexed = reindexed.ffill().bfill()
                future[name] = reindexed.values

    prophet_forecast = model.predict(future)
    forecast_months = prophet_forecast.tail(monthly_periods)

    # Aggregate monthly forecasts into quarterly
    forecast_points = []
    for q_idx in range(periods_ahead):
        start_idx = q_idx * 3
        end_idx = start_idx + 3
        quarter_months = forecast_months.iloc[start_idx:end_idx]

        # Sum monthly values to get quarterly total
        quarterly_value = quarter_months["yhat"].sum()
        quarterly_lower = quarter_months["yhat_lower"].sum()
        quarterly_upper = quarter_months["yhat_upper"].sum()

        # Use the last month's date as the quarter-end date
        quarter_end_date = quarter_months.iloc[-1]["ds"]
        quarter = (quarter_end_date.month - 1) // 3 + 1
        label = f"Q{quarter} {quarter_end_date.year}"

        forecast_points.append(
            ForecastPoint(
                date=quarter_end_date.to_pydatetime(),
                value=quarterly_value,
                lower=quarterly_lower,
                upper=quarterly_upper,
                label=label,
            )
        )

        logger.debug(
            f"Quarterly aggregation: {label}",
            extra={
                "quarter": label,
                "monthly_values": quarter_months["yhat"].tolist(),
                "quarterly_total": quarterly_value,
            },
        )

    return forecast_points


def generate_quarterly_direct(
    model: Prophet,
    df: pd.DataFrame,
    periods_ahead: int,
    regressors_used: list[str],
    external_regressors: dict[str, pd.Series] | None,
    future_regressor_strategy: str,
    logger: Logger,
) -> list[ForecastPoint]:
    """Generate quarterly forecasts directly (non-monthly input data).

    Args:
        model: Fitted Prophet model
        df: DataFrame with 'ds', 'y' columns
        periods_ahead: Number of quarters to forecast
        regressors_used: List of regressor names in model
        external_regressors: External regressor series
        future_regressor_strategy: Strategy for future values
        logger: Logger instance

    Returns:
        List of ForecastPoint for quarterly forecasts
    """
    future = model.make_future_dataframe(periods=periods_ahead, freq="QE")

    # Add regressor values to future dataframe
    if regressors_used and external_regressors:
        future_dates = pd.DatetimeIndex(future["ds"].tail(periods_ahead))
        extended = _generate_future_regressors(
            {k: v for k, v in external_regressors.items() if k in regressors_used},
            future_dates,
            strategy=future_regressor_strategy,
        )
        for name in regressors_used:
            if name in extended:
                reindexed = extended[name].reindex(future["ds"])
                reindexed = reindexed.ffill().bfill()
                future[name] = reindexed.values

    prophet_forecast = model.predict(future)
    forecast_rows = prophet_forecast.tail(periods_ahead)

    # Build forecast points
    forecast_points = []
    for _, row in forecast_rows.iterrows():
        quarter = (row["ds"].month - 1) // 3 + 1
        label = f"Q{quarter} {row['ds'].year}"

        forecast_points.append(
            ForecastPoint(
                date=row["ds"].to_pydatetime(),
                value=row["yhat"],
                lower=row["yhat_lower"],
                upper=row["yhat_upper"],
                label=label,
            )
        )

    return forecast_points


def generate_forecast_points_by_frequency(
    model: Prophet,
    df: pd.DataFrame,
    periods_ahead: int,
    regressors_used: list[str],
    external_regressors: dict[str, pd.Series] | None,
    future_regressor_strategy: str,
    frequency: str,
    metric: str,
    logger: Logger,
) -> list[ForecastPoint]:
    """Generate forecast points based on input/output frequency.

    Story 8.1: Extracted from generate_forecast to reduce function length.

    Args:
        model: Fitted Prophet model
        df: Training DataFrame
        periods_ahead: Number of periods to forecast
        regressors_used: List of regressor names
        external_regressors: External regressors dict
        future_regressor_strategy: Strategy for future values
        frequency: Output frequency
        metric: Metric name
        logger: Logger instance

    Returns:
        List of ForecastPoint objects
    """
    is_monthly = detect_input_frequency(df)
    output_monthly = frequency.upper() in ("M", "ME", "MS")

    if is_monthly and output_monthly:
        return generate_monthly_forecast_points(
            model,
            df,
            periods_ahead,
            regressors_used,
            external_regressors,
            future_regressor_strategy,
            metric,
            logger,
        )
    elif is_monthly:
        return generate_quarterly_from_monthly(
            model,
            df,
            periods_ahead,
            regressors_used,
            external_regressors,
            future_regressor_strategy,
            logger,
        )
    else:
        return generate_quarterly_direct(
            model,
            df,
            periods_ahead,
            regressors_used,
            external_regressors,
            future_regressor_strategy,
            logger,
        )
