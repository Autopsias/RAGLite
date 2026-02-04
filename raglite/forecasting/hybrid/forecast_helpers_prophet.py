"""Prophet model configuration and fitting helpers.

Story 8: Refactoring helpers - Prophet-specific functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from raglite.forecasting.hybrid.lazy_imports import _get_prophet_class
from raglite.forecasting.hybrid.preprocessing import (
    prepare_regressors,
    select_regressors,
)
from raglite.forecasting.hybrid.preprocessing_regressors import PROFIT_METRICS

if TYPE_CHECKING:
    from logging import Logger

    from prophet import Prophet

    from raglite.shared.models import TimeSeriesData


# Module-level constants
# EBITDA forecast fix (2026-02-03): Removed profit and net_income from flat growth.
# Profit metrics should use linear growth to capture business expansion trends.
# Only truly bounded or ratio metrics should use flat growth.
FLAT_GROWTH_METRICS = [
    "capacity_utilization",  # 0-100% bounded
    "frequency ratio",  # Ratio metric
    "utilization",  # 0-100% bounded
]

# Metrics that should use multiplicative seasonality (growth patterns)
MULTIPLICATIVE_SEASONALITY_METRICS = {
    "ebitda",
    "ebitda ifrs",
    "revenue",
    "turnover",
    "turnover+vat",
    "profit",
    "net_income",
    "operating_profit",
    "gross_profit",
}


def filter_regressors_for_cache(
    selected_model: str | None,
    selected_regressors: list[str] | None,
    external_regressors: dict[str, pd.Series] | None,
) -> dict[str, pd.Series] | None:
    """Filter external_regressors based on cached model selection.

    Story 7b-6 AC-7b.6.3: Only pass regressors that are in cached selection AND available.

    Args:
        selected_model: Model from cache (or None)
        selected_regressors: Regressor list from cache (or None)
        external_regressors: Available external regressors

    Returns:
        Filtered regressors dict or None
    """
    if selected_model is None:
        return external_regressors

    if selected_regressors is not None and external_regressors is not None:
        # Only pass regressors that are in the cached selection AND available
        filtered = {
            name: series
            for name, series in external_regressors.items()
            if name in selected_regressors
        }
        return filtered if filtered else None
    elif selected_regressors is None:
        # use_regressors=False in cache - don't pass any regressors
        return None

    return external_regressors


def prepare_prophet_dataframe(
    historical_data: TimeSeriesData,
    metric: str,
    logger: Logger,
) -> pd.DataFrame:
    """Prepare DataFrame for Prophet model.

    Creates 'ds' and 'y' columns, handles duplicate dates.

    Args:
        historical_data: Time-series data
        metric: Metric name (for logging)
        logger: Logger instance

    Returns:
        Prepared DataFrame with 'ds' and 'y' columns
    """
    df = pd.DataFrame(
        {
            "ds": [p.date for p in historical_data.points],
            "y": [p.value for p in historical_data.points],
        }
    )

    # BUG FIX (P0): Handle duplicate dates before creating Prophet model
    # Duplicates cause "cannot reindex on an axis with duplicate labels" error
    if df.duplicated(subset=["ds"]).any():
        dup_count = df.duplicated(subset=["ds"]).sum()
        logger.warning(
            "Duplicate dates detected in historical data - aggregating by taking mean",
            extra={
                "metric": metric,
                "duplicates": dup_count,
                "total_points": len(df),
            },
        )
        # Group by date and take mean of values
        df = df.groupby("ds", as_index=False).agg({"y": "mean"})

    return df


def detect_data_characteristics(
    df: pd.DataFrame,
    metric: str,
    logger: Logger,
) -> tuple[bool, bool, bool]:
    """Detect data characteristics for Prophet configuration.

    Args:
        df: DataFrame with 'ds' and 'y' columns
        metric: Metric name
        logger: Logger instance

    Returns:
        Tuple of (has_full_year_data, use_flat_growth, has_data_gaps)
    """
    # Check data span for yearly seasonality
    data_span_days = (df["ds"].max() - df["ds"].min()).days
    has_full_year_data = data_span_days >= 335  # ~11 months minimum

    # Story 6.23: Detect metrics that need flat growth
    metric_lower = metric.lower().strip()
    use_flat_growth = any(metric_kw in metric_lower for metric_kw in FLAT_GROWTH_METRICS)

    # FIX (2025-12-14): Detect significant gaps in data
    has_data_gaps = False
    if len(df) >= 2:
        for i in range(len(df) - 1):
            gap_days = (df["ds"].iloc[i + 1] - df["ds"].iloc[i]).days
            if gap_days > 60:  # More than 2 months gap
                has_data_gaps = True
                logger.info(
                    f"Data gap detected: {gap_days} days",
                    extra={"metric": metric, "gap_days": gap_days},
                )
                break

    # Story 6.24: Special case for Thermal Energy - override gap detection
    if metric.lower() in ("thermal_cost", "thermal energy", "thermal"):
        if has_data_gaps:
            logger.info(
                "Thermal Energy: Overriding gap detection (quarterly reporting pattern)",
                extra={"metric": metric, "override": "quarterly_pattern"},
            )
        has_data_gaps = False

    return has_full_year_data, use_flat_growth, has_data_gaps


def configure_prophet(
    has_full_year_data: bool,
    use_flat_growth: bool,
    has_data_gaps: bool,
    metric: str,
    logger: Logger,
) -> Prophet:
    """Configure Prophet model based on data characteristics.

    EBITDA forecast fix (2026-02-03): Use multiplicative seasonality for profit
    metrics to better capture percentage-based seasonal patterns.

    Args:
        has_full_year_data: Whether data spans ~1 year
        use_flat_growth: Whether to use flat growth mode
        has_data_gaps: Whether data has significant gaps
        metric: Metric name (for logging)
        logger: Logger instance

    Returns:
        Configured Prophet model instance
    """
    Prophet = _get_prophet_class()  # Lazy-load Prophet
    metric_lower = metric.lower().strip()

    # EBITDA fix: Determine if metric should use multiplicative seasonality
    # Profit/revenue metrics have percentage-based seasonal patterns
    use_multiplicative = metric_lower in MULTIPLICATIVE_SEASONALITY_METRICS
    seasonality_mode = "multiplicative" if use_multiplicative else "additive"

    # Determine changepoint prior scale
    if use_flat_growth:
        changepoint_prior = 0.001  # Minimal flexibility for flat cost metrics
        logger.info(
            f"Using flat growth for {metric} (sparse data pattern)",
            extra={"metric": metric, "growth": "flat", "changepoint_prior": changepoint_prior},
        )
    elif not has_full_year_data or has_data_gaps:
        changepoint_prior = 0.05  # Conservative for short data OR data with gaps
        if has_data_gaps:
            logger.info(
                f"Using conservative changepoint prior for {metric} due to data gaps",
                extra={"metric": metric, "changepoint_prior": changepoint_prior},
            )
    else:
        changepoint_prior = 0.2  # Standard for full year data

    model = Prophet(
        growth="flat" if use_flat_growth else "linear",
        yearly_seasonality=has_full_year_data and not use_flat_growth,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=changepoint_prior,
        seasonality_mode=seasonality_mode,  # EBITDA fix: multiplicative for profit metrics
        interval_width=0.95,
        uncertainty_samples=1000,
    )

    if use_multiplicative:
        logger.info(
            f"Using multiplicative seasonality for {metric}",
            extra={
                "metric": metric,
                "seasonality_mode": seasonality_mode,
                "reason": "profit/revenue metric with percentage-based seasonal patterns",
            },
        )

    return model


def add_regressors_to_prophet(
    model: Prophet,
    df: pd.DataFrame,
    historical_data: TimeSeriesData,
    external_regressors: dict[str, pd.Series] | None,
    logger: Logger,
    metric: str | None = None,
) -> tuple[list[str], dict[str, int]]:
    """Add external regressors to Prophet model and DataFrame.

    Story 6.3: Multi-variate forecasting support.
    Forecast reliability fix (2026-02-02): Pass metric name for appropriate
    correlation threshold selection (lower for profit metrics like EBITDA).
    EBITDA forecast fix (2026-02-03): Apply optimal lags to maximize correlation.

    Args:
        model: Prophet model instance
        df: DataFrame with 'ds' and 'y' columns
        historical_data: Original time-series data
        external_regressors: Dict of external regressor series
        logger: Logger instance
        metric: Metric name (used to determine correlation threshold)

    Returns:
        Tuple of (list of regressor names added, dict of {name: lag} for lags applied)
    """
    regressors_used: list[str] = []
    lags_applied: dict[str, int] = {}

    if not external_regressors:
        return regressors_used, lags_applied

    # Select regressors by correlation
    target_series = pd.Series(
        [p.value for p in historical_data.points],
        index=pd.to_datetime([p.date for p in historical_data.points]),
    )

    # EBITDA fix (2026-02-03): Get lag info along with selection
    # Macro indicators often have 1-3 month lag effect on financial metrics
    metric_lower = (metric or "").lower()
    is_profit_metric = metric_lower in PROFIT_METRICS

    # Get selection with lag info for profit metrics (where lagged correlations matter)
    lag_info = select_regressors(
        target_series, external_regressors, metric_name=metric, return_lag_info=True
    )

    if lag_info:
        selected = list(lag_info.keys())

        # Prepare regressors (align, interpolate, auto-transform YoY%)
        target_index = pd.DatetimeIndex(df["ds"])
        prepared = prepare_regressors(
            {k: v for k, v in external_regressors.items() if k in selected},
            target_index,
            target_series=target_series,  # Story 6.7: Enable YoY% auto-detection
        )

        # EBITDA fix: Determine regressor prior scale based on metric type
        # Profit metrics need higher prior scale to allow regressor influence
        regressor_prior_scale = 0.05 if is_profit_metric else 0.01

        # Add each regressor to Prophet and DataFrame with optimal lag applied
        for name, series in prepared.items():
            corr, lag = lag_info.get(name, (0.0, 0))

            # Apply optimal lag if detected
            if lag > 0:
                lagged_series = series.shift(lag)
                # Fill leading NaN values with first valid value (forward-fill alternative)
                lagged_series = lagged_series.bfill()
                df[name] = lagged_series.values
                lags_applied[name] = lag
                logger.info(
                    f"Applied {lag}-period lag to regressor {name}",
                    extra={
                        "regressor": name,
                        "lag_periods": lag,
                        "correlation": f"{abs(corr):.3f}",
                        "metric": metric,
                    },
                )
            else:
                df[name] = series.values

            # Match regressor mode to model's seasonality mode to prevent sign flips
            regressor_mode = getattr(model, "seasonality_mode", "additive")
            model.add_regressor(name, mode=regressor_mode, prior_scale=regressor_prior_scale)
            regressors_used.append(name)

        logger.info(
            "Multi-variate regressors added",
            extra={
                "regressors": regressors_used,
                "lags_applied": lags_applied if lags_applied else "none",
                "prior_scale": regressor_prior_scale,
                "metric_type": "profit" if is_profit_metric else "other",
            },
        )

    return regressors_used, lags_applied


def prepare_and_fit_prophet_model(
    historical_data: TimeSeriesData,
    metric: str,
    external_regressors: dict[str, pd.Series] | None,
    logger: Logger,
) -> tuple[Prophet, pd.DataFrame, list[str], dict[str, int]]:
    """Prepare data, configure Prophet model, add regressors, and fit.

    Story 8.1: Extracted from generate_forecast to reduce function length.
    Combines Steps 6-7 of original generate_forecast.
    EBITDA fix (2026-02-03): Returns lag info for future regressor generation.

    Args:
        historical_data: Time-series data
        metric: Metric name
        external_regressors: External regressors dict
        logger: Logger instance

    Returns:
        Tuple of (fitted_model, dataframe, regressors_used, lags_applied)
    """
    # Prepare DataFrame
    df = prepare_prophet_dataframe(historical_data, metric, logger)

    # Detect characteristics and configure model
    has_full_year, use_flat_growth, has_gaps = detect_data_characteristics(df, metric, logger)
    model = configure_prophet(has_full_year, use_flat_growth, has_gaps, metric, logger)

    # Add regressors and fit (pass metric for appropriate threshold selection)
    # EBITDA fix: Now returns lag info for applying same lags to future values
    regressors_used, lags_applied = add_regressors_to_prophet(
        model, df, historical_data, external_regressors, logger, metric=metric
    )
    model.fit(df)

    return model, df, regressors_used, lags_applied
