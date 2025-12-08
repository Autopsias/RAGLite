"""Hybrid forecasting engine combining Prophet statistical + LLM reasoning.

Story 4.2: Forecasting Engine Implementation.
Story 6.3: Multi-variate forecasting with external regressors.

PERFORMANCE FIX (2025-11-29): Prophet import is lazy-loaded to avoid
50-60s cold start penalty during pytest collection. Prophet is only
imported when generate_forecast() is actually called.
"""

from __future__ import annotations

import asyncio
import json
import os
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from prophet import Prophet
    from sklearn.linear_model import LinearRegression
    from xgboost import XGBRegressor

    from raglite.external_data.storage import ExternalDataStorage

# Story 6.4: Module-level executor for sklearn/xgboost (not async-native)
# Limited to 2 workers to manage memory when running models in parallel
_sklearn_executor = ThreadPoolExecutor(max_workers=2)

from raglite.shared.clients import get_mistral_client

# Lazy-load Prophet to avoid import-time penalty during test collection
# Prophet takes 3-5s to import due to Stan backend dependencies
_prophet_class = None


def _get_prophet_class() -> type[Prophet]:
    """Lazy-load Prophet class on first use.

    Returns:
        Prophet class from prophet library
    """
    global _prophet_class
    if _prophet_class is None:
        from prophet import Prophet

        _prophet_class = Prophet
    return cast("type[Prophet]", _prophet_class)


from raglite.shared.logging import get_logger
from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesData

logger = get_logger(__name__)

# Minimum data points required for reliable forecasting
# FIX (2025-12-01): Lowered from 8 to 6 to allow GROUP-level SQL data
# with occasional missing months (e.g., 7 months Feb-Sep missing June)
# Prophet can produce reasonable forecasts with 6+ monthly data points
MIN_DATA_POINTS = 6

# Story 6.3: Constants for multi-variate forecasting
MAX_MISSING_RATIO = 0.10  # Maximum 10% missing data allowed
MAX_INTERPOLATION_GAP = 3  # Maximum periods to interpolate
MIN_CV_DATA_POINTS = 12  # Minimum points for cross-validation


class InsufficientDataError(Exception):
    """Exception raised when insufficient data for forecasting."""

    pass


# =============================================================================
# Story 6.3: Multi-variate forecasting helper functions
# =============================================================================


def transform_yoy_to_index(
    yoy_series: pd.Series,
    base_value: float = 100.0,
) -> pd.Series:
    """Reconstruct absolute index from YoY% changes.

    Story 6.7: Transform Year-over-Year percentage changes to co-integrated
    level series suitable for forecasting regressors.

    The transformation accumulates monthly changes to reconstruct an index:
    Index_t = Index_{t-1} * (1 + YoY%_t / 1200)

    This converts small percentage values (2.0, 3.3, -1.5) to index values
    that co-move with absolute quantities.

    Args:
        yoy_series: Series of YoY% changes (e.g., 2.0, 3.3, -1.5)
        base_value: Starting index value (default: 100)

    Returns:
        Series of reconstructed absolute index values

    Example:
        >>> yoy = pd.Series([2.0, 3.0, -1.0], index=dates)
        >>> index = transform_yoy_to_index(yoy)
        # Returns approximately [100.17, 100.42, 100.34]
    """
    if yoy_series.empty:
        return yoy_series.copy()

    # Sort by date
    sorted_series = yoy_series.sort_index()

    # Initialize result array
    index_values = np.zeros(len(sorted_series))
    index_values[0] = base_value

    # Accumulate changes: Index_t = Index_{t-1} * (1 + YoY% / 1200)
    # Using 1200 because YoY% needs to be converted to monthly growth
    for i in range(1, len(sorted_series)):
        yoy_pct = sorted_series.iloc[i]
        # Convert annual % to monthly factor
        monthly_factor = 1 + (yoy_pct / 1200)
        index_values[i] = index_values[i - 1] * monthly_factor

    result = pd.Series(index_values, index=sorted_series.index)

    logger.debug(
        "Transformed YoY% to index",
        extra={
            "input_range": f"{sorted_series.min():.2f} to {sorted_series.max():.2f}",
            "output_range": f"{result.min():.2f} to {result.max():.2f}",
        },
    )

    return result


def detect_yoy_percentage(series: pd.Series, target_series: pd.Series | None = None) -> bool:
    """Detect if a series contains YoY percentage changes vs absolute values.

    Story 6.7: Identify YoY% data (e.g., INE Construction Output Index)
    that needs transformation before use as regressors.

    Characteristics of YoY% data:
    - Small range (typically ±10%, max ±30%)
    - Mean close to 0 (long-term average growth)
    - Contains negative values (periods of decline)
    - Values typically between -30 and +30

    Args:
        series: Series to analyze
        target_series: Optional target series for scale comparison

    Returns:
        True if series appears to be YoY% data
    """
    if series.empty:
        return False

    series_min = series.min()
    series_max = series.max()
    series_range = series_max - series_min
    series_mean = series.mean()

    # YoY% specific checks:
    # 1. Must contain negative values (decline periods)
    has_negative = series_min < 0

    # 2. Values typically in -30 to +30 range for YoY%
    in_yoy_range = series_min >= -50 and series_max <= 50

    # 3. Mean should be close to 0 (long-term balance)
    mean_near_zero = abs(series_mean) < 10

    # 4. Small range (YoY% typically varies by ±10 points)
    small_range = series_range < 30

    # All conditions must be met for confident YoY% detection
    if has_negative and in_yoy_range and mean_near_zero and small_range:
        return True

    # Additional check: Scale ratio vs target (if large mismatch)
    if target_series is not None and not target_series.empty:
        target_range = target_series.max() - target_series.min()
        if target_range > 0 and series_range > 0:
            scale_ratio = target_range / series_range
            # Only flag as YoY% if target is 50x+ larger AND values look like percentages
            if scale_ratio > 50 and in_yoy_range and has_negative:
                return True

    return False


def validate_regressor_scale(
    regressor: pd.Series,
    target: pd.Series,
    max_scale_ratio: float = 100.0,
    min_correlation: float = 0.2,
) -> tuple[bool, str, dict]:
    """Validate that regressor is suitable for forecasting target.

    Story 6.7: Scale validation prevents mismatched data from causing
    poor forecast accuracy.

    Args:
        regressor: Regressor series to validate
        target: Target series for comparison
        max_scale_ratio: Maximum allowed scale ratio (default: 100)
        min_correlation: Minimum correlation threshold (default: 0.2)

    Returns:
        Tuple of (is_valid, message, metadata)
    """
    metadata: dict = {}

    # Align data
    aligned = pd.DataFrame({"target": target, "regressor": regressor}).dropna()

    if len(aligned) < 10:
        return False, f"Insufficient overlap: only {len(aligned)} aligned points", metadata

    # Scale check
    regressor_range = aligned["regressor"].max() - aligned["regressor"].min()
    target_range = aligned["target"].max() - aligned["target"].min()
    scale_ratio = target_range / max(regressor_range, 1e-6)

    metadata["scale_ratio"] = scale_ratio
    metadata["regressor_range"] = regressor_range
    metadata["target_range"] = target_range

    if scale_ratio > max_scale_ratio:
        return (
            False,
            f"Scale mismatch: target range {target_range:.1f} vs regressor range {regressor_range:.1f} (ratio: {scale_ratio:.1f}x)",
            metadata,
        )

    # Correlation check
    corr = aligned["target"].corr(aligned["regressor"])
    metadata["correlation"] = corr

    if abs(corr) < min_correlation:
        return (
            False,
            f"Low correlation: {corr:.3f} < {min_correlation}",
            metadata,
        )

    return True, "OK", metadata


def select_regressors(
    target: pd.Series,
    candidates: dict[str, pd.Series],
    top_n: int = 7,
    min_correlation: float = 0.3,  # Story 6.7: Lowered from 0.5 to accept moderate correlations
    auto_transform_yoy: bool = True,
) -> list[str]:
    """Select top regressors by Pearson correlation with target.

    Story 6.3 AC3: Correlation-based regressor selection.
    Story 6.7: Auto-transform YoY% data before correlation calculation.

    Args:
        target: Target time-series (y values)
        candidates: Dictionary of candidate regressors {name: series}
        top_n: Maximum number of regressors to select (default: 7)
        min_correlation: Minimum absolute correlation threshold (default: 0.5)
        auto_transform_yoy: Auto-transform YoY% data before correlation (default: True)

    Returns:
        List of selected regressor names sorted by abs(correlation) descending
    """
    if not candidates:
        return []

    # Story 6.7: Transform YoY% candidates before correlation calculation
    transformed_candidates: dict[str, pd.Series] = {}
    for name, series in candidates.items():
        working_series = series.copy()

        if auto_transform_yoy and detect_yoy_percentage(working_series, target):
            # Transform YoY% to index scaled to target mean
            base_value = target.mean() if not target.empty else 100.0
            working_series = transform_yoy_to_index(working_series, base_value=base_value)
            logger.debug(
                f"Pre-selection YoY% transform: {name}",
                extra={
                    "original_range": f"{series.min():.2f}-{series.max():.2f}",
                    "transformed_range": f"{working_series.min():.2f}-{working_series.max():.2f}",
                },
            )

        transformed_candidates[name] = working_series

    # Build DataFrame with target and all candidates
    df = pd.DataFrame({"target": target})
    for name, series in transformed_candidates.items():
        # Reindex to match target
        df[name] = series.reindex(target.index)

    # Calculate correlations
    correlations = df.corr()["target"].drop("target")

    # Filter by minimum correlation
    filtered = correlations[correlations.abs() >= min_correlation]

    # Sort by absolute correlation and take top N
    selected: list[str] = list(filtered.abs().sort_values(ascending=False).head(top_n).index)

    logger.info(
        "Regressors selected",
        extra={
            "candidates": len(candidates),
            "selected": len(selected),
            "names": selected,
            "correlations": {name: f"{correlations.get(name, 0):.3f}" for name in selected},
        },
    )

    return selected


def prepare_regressors(
    regressors: dict[str, pd.Series],
    target_index: pd.DatetimeIndex,
    target_series: pd.Series | None = None,
    auto_transform_yoy: bool = True,
) -> dict[str, pd.Series]:
    """Prepare regressors: align, interpolate, transform, validate.

    Story 6.3 AC4: Missing data handling for regressors.
    Story 6.7: Auto-transform YoY% to absolute index for scale compatibility.

    Args:
        regressors: Dictionary of regressor series
        target_index: Target DatetimeIndex to align to
        target_series: Optional target series for YoY% detection
        auto_transform_yoy: Auto-transform detected YoY% data (default: True)

    Returns:
        Dictionary of prepared regressor series

    Raises:
        ValueError: If >10% missing after interpolation
    """
    prepared = {}

    for name, series in regressors.items():
        working_series = series.copy()

        # Story 6.7: Auto-detect and transform YoY% data
        if auto_transform_yoy and detect_yoy_percentage(working_series, target_series):
            logger.info(
                f"Auto-transforming YoY% regressor: {name}",
                extra={
                    "original_range": f"{working_series.min():.2f} to {working_series.max():.2f}",
                },
            )
            # Scale base value to target range for better correlation
            if target_series is not None and not target_series.empty:
                # Use target mean as base to improve correlation
                base_value = target_series.mean()
            else:
                base_value = 100.0

            working_series = transform_yoy_to_index(working_series, base_value=base_value)
            logger.info(
                f"Transformed {name} to index",
                extra={
                    "new_range": f"{working_series.min():.2f} to {working_series.max():.2f}",
                },
            )

        # Reindex to target index
        aligned = working_series.reindex(target_index)

        # Check missing ratio
        missing_count = aligned.isna().sum()
        missing_ratio = missing_count / len(aligned)

        if missing_ratio > MAX_MISSING_RATIO:
            raise ValueError(
                f"Regressor '{name}' has {missing_ratio:.1%} missing values "
                f"(max allowed: {MAX_MISSING_RATIO:.0%})"
            )

        # Linear interpolation for gaps <= MAX_INTERPOLATION_GAP
        if missing_count > 0:
            # Interpolate with limit
            aligned = aligned.interpolate(method="linear", limit=MAX_INTERPOLATION_GAP)

            # Forward-fill remaining edge cases (max 3 periods)
            aligned = aligned.ffill(limit=MAX_INTERPOLATION_GAP)
            aligned = aligned.bfill(limit=MAX_INTERPOLATION_GAP)

        # Final validation
        if aligned.isna().any():
            raise ValueError(f"Regressor '{name}' still has missing values after interpolation")

        prepared[name] = aligned

    return prepared


def calculate_accuracy(model: Prophet, df: pd.DataFrame) -> dict[str, float]:
    """Calculate RMSE, MAE, MAPE using Prophet cross-validation.

    Story 6.3 AC5: Accuracy metrics calculation.

    Args:
        model: Fitted Prophet model
        df: Training DataFrame with 'ds' and 'y' columns

    Returns:
        Dictionary with 'rmse', 'mae', 'mape' metrics
    """
    # Only run CV if sufficient data (12+ points)
    if len(df) < MIN_CV_DATA_POINTS:
        logger.warning(
            f"Insufficient data for CV ({len(df)} < {MIN_CV_DATA_POINTS}). Returning zero metrics."
        )
        return {"rmse": 0.0, "mae": 0.0, "mape": 0.0}

    try:
        from prophet.diagnostics import cross_validation, performance_metrics

        # Calculate appropriate CV parameters based on data length
        data_span_days = (df["ds"].max() - df["ds"].min()).days

        # Initial training period: ~60% of data
        initial_days = int(data_span_days * 0.6)
        initial = f"{initial_days} days"

        # Period between cutoffs: ~30 days
        period = "30 days"

        # Horizon: ~90 days (3 months)
        horizon = "90 days"

        cv = cross_validation(model, initial=initial, period=period, horizon=horizon)
        metrics = performance_metrics(cv)

        return {
            "rmse": float(metrics["rmse"].mean()),
            "mae": float(metrics["mae"].mean()),
            "mape": float(metrics["mape"].mean()),
        }

    except Exception as e:
        logger.warning(f"Cross-validation failed: {e}. Returning zero metrics.")
        return {"rmse": 0.0, "mae": 0.0, "mape": 0.0}


def get_baseline_rmse(metric: str) -> float | None:
    """Get Epic 4 baseline RMSE from stored results.

    Story 6.3 AC5: Baseline RMSE lookup for improvement calculation.

    Args:
        metric: Metric name to look up

    Returns:
        Baseline RMSE if available, None otherwise
    """
    # Check environment variable first
    env_key = f"BASELINE_RMSE_{metric.upper()}"
    env_value = os.getenv(env_key)
    if env_value:
        try:
            return float(env_value)
        except ValueError:
            pass

    # Check accuracy tracking log file
    log_path = Path("docs/accuracy-tracking-log.jsonl")
    if log_path.exists():
        try:
            with open(log_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if (
                        entry.get("metric") == metric
                        and entry.get("type") == "baseline"
                        and "rmse" in entry
                    ):
                        return float(entry["rmse"])
        except (json.JSONDecodeError, OSError):
            pass

    return None


def _generate_future_regressors(
    regressors: dict[str, pd.Series],
    future_dates: pd.DatetimeIndex,
    strategy: str = "constant",
) -> dict[str, pd.Series]:
    """Generate future regressor values based on strategy.

    Story 6.3 AC7: Future regressor value strategies.

    Args:
        regressors: Historical regressor series
        future_dates: Future dates to generate values for
        strategy: Strategy - 'constant', 'extrapolate', or 'provided'

    Returns:
        Dictionary of regressor series extended to future dates

    Raises:
        ValueError: If strategy='provided' but future values missing
    """
    extended = {}

    for name, series in regressors.items():
        historical = series.dropna()

        if strategy == "constant":
            # Use last known value for all future dates
            last_value = historical.iloc[-1]
            future_values = pd.Series(last_value, index=future_dates)

        elif strategy == "extrapolate":
            # Linear extrapolation from last 3 values
            if len(historical) >= 3:
                last_n = historical.tail(3)
                x = np.arange(len(last_n))
                y = last_n.values
                slope, intercept = np.polyfit(x, y, 1)

                future_x = np.arange(len(last_n), len(last_n) + len(future_dates))
                future_y = slope * future_x + intercept
                future_values = pd.Series(future_y, index=future_dates)
            else:
                # Fall back to constant if not enough data
                last_value = historical.iloc[-1]
                future_values = pd.Series(last_value, index=future_dates)

        elif strategy == "provided":
            # Check if future values already in series
            future_available = series.reindex(future_dates)
            if future_available.isna().any():
                raise ValueError(
                    f"Strategy 'provided' requires future values for '{name}' "
                    f"to be included in external_regressors"
                )
            # For provided strategy, series already contains both historical + future
            # Just keep the original series (no concat needed)
            extended[name] = series.dropna()
            continue

        else:
            raise ValueError(f"Unknown future regressor strategy: {strategy}")

        # Combine historical and future (for constant/extrapolate strategies only)
        extended[name] = pd.concat([historical, future_values])

    return extended


async def fetch_historical_metric(
    metric: str,
    storage: ExternalDataStorage | None = None,
) -> pd.Series:
    """Fetch historical time-series from PostgreSQL external data.

    Story 6.3 AC6: Data fetching from PostgreSQL.

    Args:
        metric: Metric name to fetch
        storage: Optional ExternalDataStorage instance

    Returns:
        pandas Series with DatetimeIndex

    Raises:
        ValueError: If metric not found or no data available
    """
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.shared.database import get_session

    if storage is None:
        session = get_session()
        storage = ExternalDataStorage(session)

    # Try to find a source containing this metric
    sources = storage.list_sources()
    for source in sources:
        source_name = str(source.source_name)  # Cast for mypy
        metrics = storage.get_metrics_for_source(source_name)
        if metric in metrics:
            # Query all data for this metric
            from datetime import date, timedelta

            end_date = date.today()
            start_date = end_date - timedelta(days=5 * 365)  # 5 years

            points = storage.query_data_range(
                source_name,
                start_date,
                end_date,
                metric_name=metric,
            )

            if points:
                # Convert to Series with DatetimeIndex
                dates = pd.to_datetime([p.date for p in points])
                values = [float(p.value) for p in points]
                return pd.Series(values, index=dates, name=metric)

    raise ValueError(f"Metric '{metric}' not found in external data sources")


async def generate_forecast(
    metric: str,
    historical_data: TimeSeriesData | None = None,
    periods_ahead: int = 4,
    external_regressors: dict[str, pd.Series] | None = None,
    frequency: str = "M",
    future_regressor_strategy: str = "constant",
) -> ForecastResult:
    """Generate forecast for financial metric using Prophet + LLM.

    Story 4.2 AC1-AC4: Hybrid forecasting with Prophet statistical model
    and Mistral Large for confidence reasoning.

    Story 6.3: Extended with multi-variate forecasting support.

    Args:
        metric: Metric name (e.g., "revenue", "cash_flow", "expenses")
        historical_data: Time-series data from Story 4.1 extraction.
            DEPRECATED in Story 6.3 - use fetch_historical_metric() instead.
        periods_ahead: Number of periods to forecast (default 4 quarters)
        external_regressors: Optional dict of external regressor series for
            multi-variate forecasting (Story 6.3)
        frequency: Data frequency - 'M' (monthly), 'Q' (quarterly), 'D' (daily)
        future_regressor_strategy: Strategy for future regressor values:
            - 'constant': Use last known value (default)
            - 'extrapolate': Linear extrapolation from last 3 values
            - 'provided': Use values already in external_regressors

    Returns:
        ForecastResult with predictions, confidence intervals, and reasoning.
        When external_regressors provided, includes:
        - model_type: 'prophet_multivariate'
        - accuracy_metrics: {'rmse': X, 'mae': Y, 'mape': Z}
        - regressors_used: list of regressor names
        - improvement_vs_baseline: percentage improvement vs Epic 4 baseline

    Raises:
        InsufficientDataError: If <6 data points available
    """
    # Story 6.3 AC8: Deprecation warning for historical_data
    if historical_data is not None:
        warnings.warn(
            "historical_data parameter is deprecated, will be removed in Epic 7. "
            "Use metric parameter to fetch from PostgreSQL.",
            DeprecationWarning,
            stacklevel=2,
        )

    # Determine if multi-variate mode
    is_multivariate = external_regressors is not None and len(external_regressors) > 0

    logger.info(
        "Generating forecast",
        extra={
            "metric": metric,
            "data_points": len(historical_data.points) if historical_data else 0,
            "periods": periods_ahead,
            "multivariate": is_multivariate,
            "regressors": list(external_regressors.keys()) if external_regressors else [],
        },
    )

    # Validate minimum data requirement (AC4: 6+ data points for reliability)
    if historical_data is None:
        raise InsufficientDataError(
            "No historical data provided. Either pass historical_data "
            "or use fetch_historical_metric() to load from PostgreSQL."
        )

    if len(historical_data.points) < MIN_DATA_POINTS:
        raise InsufficientDataError(
            f"Insufficient data for forecast. Minimum {MIN_DATA_POINTS} data points required "
            f"for reliable predictions. Got {len(historical_data.points)}."
        )

    # Step 1: Prepare DataFrame for Prophet (requires 'ds' and 'y' columns)
    df = pd.DataFrame(
        {
            "ds": [p.date for p in historical_data.points],
            "y": [p.value for p in historical_data.points],
        }
    )

    # Step 2: Configure Prophet based on data availability
    # CRITICAL: Only enable yearly seasonality if we have 12+ months of data.
    # With less data, Prophet hallucinates seasonal patterns causing negative forecasts.
    data_span_days = (df["ds"].max() - df["ds"].min()).days
    has_full_year_data = data_span_days >= 335  # ~11 months minimum for yearly seasonality

    # For short data spans, use simpler model (trend only)
    Prophet = _get_prophet_class()  # Lazy-load Prophet on first use
    model = Prophet(
        yearly_seasonality=has_full_year_data,  # Only if we have 12+ months
        weekly_seasonality=False,  # Financial data is quarterly/monthly, not weekly
        daily_seasonality=False,
        changepoint_prior_scale=0.05
        if not has_full_year_data
        else 0.2,  # More conservative for short data
        interval_width=0.95,
        uncertainty_samples=1000,
    )

    # Story 6.3: Add external regressors for multi-variate forecasting
    regressors_used: list[str] = []
    if is_multivariate and external_regressors:
        # Select regressors by correlation
        target_series = pd.Series(
            [p.value for p in historical_data.points],
            index=pd.to_datetime([p.date for p in historical_data.points]),
        )
        selected = select_regressors(target_series, external_regressors)

        if selected:
            # Prepare regressors (align, interpolate, auto-transform YoY%)
            target_index = pd.DatetimeIndex(df["ds"])
            prepared = prepare_regressors(
                {k: v for k, v in external_regressors.items() if k in selected},
                target_index,
                target_series=target_series,  # Story 6.7: Enable YoY% auto-detection
            )

            # Add each regressor to Prophet and DataFrame
            for name, series in prepared.items():
                model.add_regressor(name, mode="additive")
                df[name] = series.values
                regressors_used.append(name)

            logger.info(
                "Multi-variate regressors added",
                extra={"regressors": regressors_used},
            )

    logger.info(
        "Prophet configured",
        extra={
            "data_points": len(df),
            "data_span_days": data_span_days,
            "yearly_seasonality": has_full_year_data,
            "changepoint_prior_scale": 0.05 if not has_full_year_data else 0.2,
            "regressors": regressors_used,
        },
    )

    # Step 3: Fit model and generate forecast
    # CRITICAL FIX: Prophet must forecast at the same frequency as input data.
    # If input is monthly, forecast monthly then aggregate to quarterly.
    model.fit(df)

    # Determine input data frequency
    if len(df) >= 2:
        date_diff = (df["ds"].iloc[1] - df["ds"].iloc[0]).days
        is_monthly_data = 25 <= date_diff <= 35
    else:
        is_monthly_data = False

    if is_monthly_data:
        # Story 6.7: Respect frequency parameter - return monthly if requested
        output_monthly = frequency.upper() in ("M", "ME", "MS")

        if output_monthly:
            # Monthly input, monthly output (Story 6.7)
            future = model.make_future_dataframe(periods=periods_ahead, freq="ME")

            # Story 6.3: Add regressor values to future dataframe
            if regressors_used and external_regressors:
                future_dates = pd.DatetimeIndex(future["ds"].tail(periods_ahead))
                extended = _generate_future_regressors(
                    {k: v for k, v in external_regressors.items() if k in regressors_used},
                    future_dates,
                    strategy=future_regressor_strategy,
                )
                for name in regressors_used:
                    if name in extended:
                        future[name] = extended[name].reindex(future["ds"]).values

            prophet_forecast = model.predict(future)
            forecast_months = prophet_forecast.tail(periods_ahead)

            # Return monthly forecasts directly (no aggregation)
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

            logger.debug(
                "Monthly forecast generated",
                extra={"periods": periods_ahead, "output_frequency": "monthly"},
            )
        else:
            # Monthly input, quarterly output (aggregate 3 months)
            monthly_periods = periods_ahead * 3  # 3 months per quarter
            future = model.make_future_dataframe(periods=monthly_periods, freq="ME")

            # Story 6.3: Add regressor values to future dataframe
            if regressors_used and external_regressors:
                future_dates = pd.DatetimeIndex(future["ds"].tail(monthly_periods))
                extended = _generate_future_regressors(
                    {k: v for k, v in external_regressors.items() if k in regressors_used},
                    future_dates,
                    strategy=future_regressor_strategy,
                )
                for name in regressors_used:
                    if name in extended:
                        future[name] = extended[name].reindex(future["ds"]).values

            prophet_forecast = model.predict(future)

            # Get only the future monthly predictions (not historical)
            forecast_months = prophet_forecast.tail(monthly_periods)

            # Aggregate monthly forecasts into quarterly
            forecast_points = []
            for q_idx in range(periods_ahead):
                # Get 3 months for this quarter
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
                    f"Quarterly aggregation: {label} = sum of 3 monthly forecasts",
                    extra={
                        "quarter": label,
                        "monthly_values": quarter_months["yhat"].tolist(),
                        "quarterly_total": quarterly_value,
                    },
                )
    else:
        # Non-monthly input: use original quarterly forecast
        future = model.make_future_dataframe(periods=periods_ahead, freq="QE")

        # Story 6.3: Add regressor values to future dataframe
        if regressors_used and external_regressors:
            future_dates = pd.DatetimeIndex(future["ds"].tail(periods_ahead))
            extended = _generate_future_regressors(
                {k: v for k, v in external_regressors.items() if k in regressors_used},
                future_dates,
                strategy=future_regressor_strategy,
            )
            for name in regressors_used:
                if name in extended:
                    future[name] = extended[name].reindex(future["ds"]).values

        prophet_forecast = model.predict(future)

        # Step 4: Extract forecast points (only the predicted periods, not historical)
        forecast_points = []
        forecast_rows = prophet_forecast.tail(periods_ahead)

        for _, row in forecast_rows.iterrows():
            # Generate quarter label
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

    # Step 5: Calculate accuracy metrics if multi-variate
    accuracy_metrics: dict[str, float] = {}
    improvement_vs_baseline: float | None = None

    if is_multivariate:
        # Calculate accuracy using cross-validation
        accuracy_metrics = calculate_accuracy(model, df)

        # Calculate improvement vs baseline
        baseline_rmse = get_baseline_rmse(metric)
        if baseline_rmse and accuracy_metrics.get("rmse", 0) > 0:
            improvement_vs_baseline = (
                (baseline_rmse - accuracy_metrics["rmse"]) / baseline_rmse
            ) * 100

            logger.info(
                "Accuracy improvement calculated",
                extra={
                    "baseline_rmse": baseline_rmse,
                    "new_rmse": accuracy_metrics["rmse"],
                    "improvement_pct": improvement_vs_baseline,
                },
            )

    # Step 6: Build ForecastResult with multi-variate fields
    model_type = "prophet_multivariate" if regressors_used else "prophet_univariate"
    basis_text = f"Prophet model trained on {len(historical_data.points)} data points"
    if regressors_used:
        basis_text += f" with {len(regressors_used)} external regressors"

    result = ForecastResult(
        metric_name=metric,
        historical_data=historical_data.points,
        forecast=forecast_points,
        basis=basis_text,
        accuracy_estimate="±15% (NFR10 target)",
        periods_ahead=periods_ahead,
        # Story 6.3: Multi-variate fields
        model_type=model_type,
        accuracy_metrics=accuracy_metrics,
        regressors_used=regressors_used,
        improvement_vs_baseline=improvement_vs_baseline,
    )

    # Step 7: Generate LLM explanation for confidence reasoning
    context = f"Historical {metric} data from {len(historical_data.source_documents)} documents"
    if regressors_used:
        context += f". Multi-variate forecast using: {', '.join(regressors_used)}"
    explanation = await explain_forecast(result, context)
    result.confidence_reasoning = explanation

    logger.info(
        "Forecast generated",
        extra={
            "metric": metric,
            "forecast_points": len(forecast_points),
            "model_type": model_type,
            "regressors": regressors_used,
            "accuracy_metrics": accuracy_metrics,
        },
    )

    return result


async def explain_forecast(forecast: ForecastResult, context: str) -> str:
    """Use Mistral Large to explain forecast with context.

    Story 4.2 AC1: LLM reasoning layer for confidence rationale.

    Args:
        forecast: Prophet forecast result
        context: Retrieved document context (trends, events)

    Returns:
        Natural language explanation with confidence rationale
    """
    logger.info("Generating forecast explanation with Mistral Large")

    client = get_mistral_client()

    # Build forecast summary for prompt
    forecast_summary = {
        "metric": forecast.metric_name,
        "periods_ahead": forecast.periods_ahead,
        "historical_points": len(forecast.historical_data),
        "predictions": [
            {
                "period": p.label,
                "value": round(p.value, 2),
                "range": f"{round(p.lower, 2)} - {round(p.upper, 2)}",
            }
            for p in forecast.forecast
        ],
    }

    prompt = f"""You are a financial analyst explaining a forecast to stakeholders.

Forecast Data:
{json.dumps(forecast_summary, indent=2)}

Context:
{context}

Please provide a clear, concise explanation that:
1. Summarizes the forecast values and confidence intervals
2. Explains why confidence intervals are what they are (data quality, trends)
3. Identifies 2-3 key risks
4. Identifies 1-2 opportunities

Format your response as JSON:
{{
    "summary": "2-3 sentence natural language explanation of the forecast",
    "confidence_rationale": "Why confidence intervals are narrow/wide",
    "risks": ["Risk 1", "Risk 2"],
    "opportunities": ["Opportunity 1"]
}}"""

    try:
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
        )
        llm_response = response.choices[0].message.content if response.choices else ""

        # Parse JSON response and format as explanation text
        if llm_response:
            # Try to parse as JSON, fall back to raw text
            try:
                parsed = json.loads(llm_response)
                explanation = parsed.get("summary", "")
                if parsed.get("confidence_rationale"):
                    explanation += f" {parsed['confidence_rationale']}"
                return str(explanation)
            except json.JSONDecodeError:
                return llm_response

    except Exception as e:
        logger.warning(f"LLM explanation failed, using fallback: {e}")

    # Fallback explanation if LLM fails
    return (
        f"Forecast based on {len(forecast.historical_data)} historical data points. "
        f"Confidence intervals reflect model uncertainty over {forecast.periods_ahead} periods."
    )


# =============================================================================
# Story 6.4: Ensemble Forecasting (scikit-learn + XGBoost)
# =============================================================================

# Lazy-load sklearn/xgboost to avoid import overhead (similar to Prophet)
_sklearn_loaded = False
_xgboost_loaded = False


def _get_linear_regression() -> Any:
    """Lazy-load LinearRegression from sklearn."""
    global _sklearn_loaded
    if not _sklearn_loaded:
        from sklearn.linear_model import LinearRegression

        _sklearn_loaded = True
        return LinearRegression
    from sklearn.linear_model import LinearRegression

    return LinearRegression


def _get_time_series_split() -> Any:
    """Lazy-load TimeSeriesSplit from sklearn."""
    from sklearn.model_selection import TimeSeriesSplit

    return TimeSeriesSplit


def _get_xgboost_regressor() -> Any:
    """Lazy-load XGBRegressor from xgboost."""
    global _xgboost_loaded
    if not _xgboost_loaded:
        from xgboost import XGBRegressor

        _xgboost_loaded = True
        return XGBRegressor
    from xgboost import XGBRegressor

    return XGBRegressor


def _get_grid_search_cv() -> Any:
    """Lazy-load GridSearchCV from sklearn."""
    from sklearn.model_selection import GridSearchCV

    return GridSearchCV


# Story 6.4 AC4: Default XGBoost hyperparameter grid
XGBOOST_PARAM_GRID = {
    "n_estimators": [50, 100, 200],
    "max_depth": [3, 6, 9],
    "learning_rate": [0.01, 0.1, 0.2],
    "subsample": [0.7, 0.8, 0.9],
}

# Fast mode for testing (reduced grid)
XGBOOST_PARAM_GRID_FAST = {
    "n_estimators": [100],
    "max_depth": [6],
    "learning_rate": [0.1],
    "subsample": [0.8],
}


def fit_linear_regression(
    X: pd.DataFrame,
    y: pd.Series,
    feature_names: list[str],
) -> tuple[LinearRegression, dict[str, float]]:
    """Fit Linear Regression with external regressors.

    Story 6.4 AC3: Linear Regression for ensemble.

    Args:
        X: Feature DataFrame (regressors)
        y: Target series (metric values)
        feature_names: Names of features for logging

    Returns:
        Tuple of (fitted LinearRegression model, accuracy metrics dict with rmse/mae/mape)
    """
    LinearRegression = _get_linear_regression()
    TimeSeriesSplit = _get_time_series_split()

    model = LinearRegression()

    # Time-series cross-validation (5-fold)
    tscv = TimeSeriesSplit(n_splits=min(5, len(X) - 1))
    cv_rmse_scores: list[float] = []
    cv_mae_scores: list[float] = []
    cv_mape_scores: list[float] = []

    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model.fit(X_train, y_train)
        predictions = model.predict(X_val)

        # RMSE: Root Mean Squared Error
        rmse = float(np.sqrt(np.mean((y_val.values - predictions) ** 2)))
        cv_rmse_scores.append(rmse)

        # MAE: Mean Absolute Error
        mae = float(np.mean(np.abs(y_val.values - predictions)))
        cv_mae_scores.append(mae)

        # MAPE: Mean Absolute Percentage Error (avoid division by zero)
        y_vals = y_val.values
        non_zero_mask = y_vals != 0
        if non_zero_mask.any():
            mape = float(
                np.mean(
                    np.abs(
                        (y_vals[non_zero_mask] - predictions[non_zero_mask]) / y_vals[non_zero_mask]
                    )
                )
                * 100
            )
        else:
            mape = 0.0
        cv_mape_scores.append(mape)

    # Final fit on all data
    model.fit(X, y)

    metrics = {
        "rmse": float(np.mean(cv_rmse_scores)) if cv_rmse_scores else 0.0,
        "mae": float(np.mean(cv_mae_scores)) if cv_mae_scores else 0.0,
        "mape": float(np.mean(cv_mape_scores)) if cv_mape_scores else 0.0,
    }

    logger.info(
        "Linear Regression fitted",
        extra={"features": feature_names, "cv_rmse": metrics["rmse"], "cv_mae": metrics["mae"]},
    )

    return model, metrics


def fit_xgboost(
    X: pd.DataFrame,
    y: pd.Series,
    fast_mode: bool = False,
) -> tuple[XGBRegressor, dict[str, object]]:
    """Fit XGBoost regressor with hyperparameter tuning.

    Story 6.4 AC4: XGBoost with GridSearchCV (5-fold time-series split).

    Args:
        X: Feature DataFrame (regressors)
        y: Target series (metric values)
        fast_mode: Use reduced param grid for testing (default: False)

    Returns:
        Tuple of (best fitted XGBRegressor model, accuracy metrics dict with rmse/mae/mape/best_params)
    """
    XGBRegressor = _get_xgboost_regressor()
    GridSearchCV = _get_grid_search_cv()
    TimeSeriesSplit = _get_time_series_split()

    param_grid = XGBOOST_PARAM_GRID_FAST if fast_mode else XGBOOST_PARAM_GRID

    # Use fewer splits for small datasets
    n_splits = min(5, len(X) - 1)
    tscv = TimeSeriesSplit(n_splits=n_splits)

    # Use multiple scoring to get RMSE, MAE, and MAPE
    scoring = {
        "rmse": "neg_root_mean_squared_error",
        "mae": "neg_mean_absolute_error",
    }

    grid_search = GridSearchCV(
        XGBRegressor(random_state=42, verbosity=0),
        param_grid,
        cv=tscv,
        scoring=scoring,
        refit="rmse",  # Refit using best RMSE model
        n_jobs=-1,  # Parallel execution
    )

    grid_search.fit(X, y)

    best_model = grid_search.best_estimator_
    best_rmse = -grid_search.cv_results_["mean_test_rmse"][grid_search.best_index_]
    best_mae = -grid_search.cv_results_["mean_test_mae"][grid_search.best_index_]

    # Calculate MAPE manually using time-series cross-validation
    # (cross_val_predict doesn't work with TimeSeriesSplit as it's not a partition)
    mape_scores: list[float] = []
    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        # Refit best model on training fold
        best_model.fit(X_train, y_train)
        fold_predictions = best_model.predict(X_val)

        y_vals = y_val.values
        non_zero_mask = y_vals != 0
        if non_zero_mask.any():
            fold_mape = float(
                np.mean(
                    np.abs(
                        (y_vals[non_zero_mask] - fold_predictions[non_zero_mask])
                        / y_vals[non_zero_mask]
                    )
                )
                * 100
            )
            mape_scores.append(fold_mape)

    # Final refit on all data (GridSearchCV already did this, but ensure consistency)
    best_model.fit(X, y)
    mape = float(np.mean(mape_scores)) if mape_scores else 0.0

    metrics: dict[str, object] = {
        "rmse": float(best_rmse),
        "mae": float(best_mae),
        "mape": mape,
        "best_params": grid_search.best_params_,
    }

    logger.info(
        "XGBoost fitted",
        extra={
            "best_params": grid_search.best_params_,
            "cv_rmse": best_rmse,
            "cv_mae": best_mae,
            "fast_mode": fast_mode,
        },
    )

    return best_model, metrics


def _calculate_weighted_average(
    predictions: dict[str, list[float]],
    weights: dict[str, float],
    models: list[str],
) -> list[float]:
    """Calculate weighted average of model predictions.

    Story 6.4 AC5: Ensemble voting with configurable weights.

    Args:
        predictions: Dict of model name -> list of predictions
        weights: Dict of model name -> weight
        models: List of successfully fitted model names

    Returns:
        List of weighted average predictions
    """
    # Normalize weights for available models only
    total_weight = sum(weights.get(m, 0.0) for m in models)
    if total_weight == 0:
        # Equal weights if no valid weights
        normalized = {m: 1.0 / len(models) for m in models}
    else:
        normalized = {m: weights.get(m, 0.0) / total_weight for m in models}

    # Weighted sum
    n_periods = len(next(iter(predictions.values())))
    result = [0.0] * n_periods

    for model in models:
        for i, val in enumerate(predictions[model]):
            result[i] += val * normalized[model]

    return result


def _fit_and_forecast_linear(
    X: pd.DataFrame,
    y: pd.Series,
    X_future: pd.DataFrame,
    feature_names: list[str],
    periods_ahead: int,
) -> dict[str, Any]:
    """Fit Linear Regression and generate forecast (for ThreadPoolExecutor).

    Story 6.4 AC5: Combined fit+forecast for parallel execution.

    Args:
        X: Training feature DataFrame
        y: Target series
        X_future: Future feature values for prediction
        feature_names: Names of features
        periods_ahead: Number of periods to forecast

    Returns:
        Dict with 'values' list and 'metrics' dict
    """
    model, metrics = fit_linear_regression(X, y, feature_names)
    predictions = model.predict(X_future)
    return {
        "values": predictions.tolist()[:periods_ahead],
        "metrics": metrics,
    }


def _fit_and_forecast_xgboost(
    X: pd.DataFrame,
    y: pd.Series,
    X_future: pd.DataFrame,
    periods_ahead: int,
    fast_mode: bool = False,
) -> dict[str, Any]:
    """Fit XGBoost and generate forecast (for ThreadPoolExecutor).

    Story 6.4 AC5: Combined fit+forecast for parallel execution.

    Args:
        X: Training feature DataFrame
        y: Target series
        X_future: Future feature values for prediction
        periods_ahead: Number of periods to forecast
        fast_mode: Use reduced hyperparameter grid

    Returns:
        Dict with 'values' list and 'metrics' dict
    """
    model, metrics = fit_xgboost(X, y, fast_mode=fast_mode)
    predictions = model.predict(X_future)
    return {
        "values": predictions.tolist()[:periods_ahead],
        "metrics": metrics,
    }


def _run_linear_forecast(
    model: LinearRegression,
    X_future: pd.DataFrame,
    periods_ahead: int,
) -> dict[str, object]:
    """Run Linear Regression forecast prediction.

    This is a synchronous function designed to be called via ThreadPoolExecutor
    for parallel ensemble execution alongside async Prophet.

    Args:
        model: Fitted LinearRegression model from sklearn
        X_future: Future feature values (regressors extrapolated forward)
        periods_ahead: Number of periods to forecast

    Returns:
        Dict with 'values' list of predictions and 'metrics' dict
    """
    try:
        predictions = model.predict(X_future)
        return {
            "values": predictions.tolist()[:periods_ahead],
            "metrics": {"model": "linear"},
        }
    except Exception as e:
        logger.warning(f"Linear forecast failed: {e}")
        raise


def _run_xgboost_forecast(
    model: XGBRegressor,
    X_future: pd.DataFrame,
    periods_ahead: int,
) -> dict[str, object]:
    """Run XGBoost forecast prediction.

    This is a synchronous function designed to be called via ThreadPoolExecutor
    for parallel ensemble execution alongside async Prophet.

    Args:
        model: Fitted XGBRegressor model from xgboost
        X_future: Future feature values (regressors extrapolated forward)
        periods_ahead: Number of periods to forecast

    Returns:
        Dict with 'values' list of predictions and 'metrics' dict
    """
    try:
        predictions = model.predict(X_future)
        return {
            "values": predictions.tolist()[:periods_ahead],
            "metrics": {"model": "xgboost"},
        }
    except Exception as e:
        logger.warning(f"XGBoost forecast failed: {e}")
        raise


async def generate_ensemble_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    external_regressors: dict[str, pd.Series] | None = None,
    periods_ahead: int = 4,
    models: list[str] | None = None,
    weights: dict[str, float] | None = None,
    fast_mode: bool = False,
) -> ForecastResult:
    """Generate ensemble forecast using multiple models.

    Story 6.4 AC5: Ensemble voting with configurable weights.
    Story 6.4 AC6: Graceful degradation with fallback.

    Args:
        metric: Metric name (e.g., "cement_demand")
        historical_data: Time-series data from extraction
        external_regressors: Dict of regressor series from PostgreSQL
        periods_ahead: Number of periods to forecast (default: 4)
        models: Models to use (default: ["prophet", "linear", "xgboost"])
        weights: Model weights (default from settings)
        fast_mode: Use fast hyperparameter grid for XGBoost (default: False)

    Returns:
        ForecastResult with ensemble predictions and per-model details

    Raises:
        InsufficientDataError: If <6 data points available
    """
    from raglite.shared.config import settings

    # Default models and weights from settings
    if models is None:
        models = settings.forecasting_models.split(",")
    if weights is None:
        weights = {
            "prophet": settings.ensemble_weight_prophet,
            "linear": settings.ensemble_weight_linear,
            "xgboost": settings.ensemble_weight_xgboost,
        }
    if fast_mode is False:
        fast_mode = settings.ensemble_fast_mode

    logger.info(
        "Generating ensemble forecast",
        extra={"metric": metric, "models": models, "weights": weights},
    )

    # Validate minimum data requirement
    if len(historical_data.points) < MIN_DATA_POINTS:
        raise InsufficientDataError(
            f"Insufficient data for forecast. Minimum {MIN_DATA_POINTS} data points required. "
            f"Got {len(historical_data.points)}."
        )

    # Prepare data
    df = pd.DataFrame(
        {
            "ds": [p.date for p in historical_data.points],
            "y": [p.value for p in historical_data.points],
        }
    )

    # Select and prepare regressors
    target_series = pd.Series(df["y"].values, index=pd.DatetimeIndex(df["ds"]))
    selected: list[str] = []
    prepared: dict[str, pd.Series] = {}

    if external_regressors:
        selected = select_regressors(target_series, external_regressors)
        if selected:
            prepared = prepare_regressors(
                {k: v for k, v in external_regressors.items() if k in selected},
                pd.DatetimeIndex(df["ds"]),
                target_series=target_series,  # Story 6.7: Enable YoY% auto-detection
            )

    # Build feature matrix for sklearn models
    X = pd.DataFrame(prepared) if prepared else pd.DataFrame()
    y = target_series

    # Track results
    predictions: dict[str, list[float]] = {}
    metrics_results: dict[str, dict[str, Any]] = {}
    successful_models: list[str] = []
    prophet_result: ForecastResult | None = None

    # Story 6.4 AC5: Parallel execution using asyncio.gather + ThreadPoolExecutor
    # Prophet is async-native, sklearn models run in ThreadPoolExecutor
    loop = asyncio.get_event_loop()

    # Prepare future feature values for sklearn models (constant extrapolation)
    # WARNING: Future regressors are extrapolated using last observed value.
    # This assumes regressors stay constant, which may lead to forecast error
    # for metrics with trending external factors.
    X_future: pd.DataFrame | None = None
    if len(X.columns) > 0:
        last_row = X.iloc[-1:].values
        X_future = pd.DataFrame(
            np.tile(last_row, (periods_ahead, 1)),
            columns=X.columns,
        )

    # Build parallel task list
    tasks: list[Any] = []
    task_names: list[str] = []

    # Prophet task (async native)
    if "prophet" in models:
        tasks.append(
            generate_forecast(
                metric=metric,
                historical_data=historical_data,
                external_regressors=external_regressors,
                periods_ahead=periods_ahead,
            )
        )
        task_names.append("prophet")

    # Linear Regression task (sync, via ThreadPoolExecutor)
    if "linear" in models and len(X.columns) > 0 and X_future is not None:
        # Create explicit copies for thread safety
        X_copy = X.copy()
        y_copy = y.copy()
        X_future_copy = X_future.copy()
        feature_names = list(X.columns)

        def run_linear() -> dict[str, Any]:
            return _fit_and_forecast_linear(
                X_copy, y_copy, X_future_copy, feature_names, periods_ahead
            )

        tasks.append(loop.run_in_executor(_sklearn_executor, run_linear))
        task_names.append("linear")

    # XGBoost task (sync, via ThreadPoolExecutor)
    if "xgboost" in models and len(X.columns) > 0 and X_future is not None:
        # Create explicit copies for thread safety
        X_copy_xgb = X.copy()
        y_copy_xgb = y.copy()
        X_future_copy_xgb = X_future.copy()
        fast_mode_copy = fast_mode

        def run_xgboost() -> dict[str, Any]:
            return _fit_and_forecast_xgboost(
                X_copy_xgb, y_copy_xgb, X_future_copy_xgb, periods_ahead, fast_mode_copy
            )

        tasks.append(loop.run_in_executor(_sklearn_executor, run_xgboost))
        task_names.append("xgboost")

    # Execute all models in parallel
    if tasks:
        logger.info(
            "Running ensemble models in parallel",
            extra={"models": task_names, "parallel_count": len(tasks)},
        )
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for name, result in zip(task_names, results, strict=False):
            if isinstance(result, Exception):
                logger.warning(f"{name.capitalize()} model failed: {result}")
                continue

            if name == "prophet":
                prophet_result = cast(ForecastResult, result)
                predictions["prophet"] = [p.value for p in prophet_result.forecast]
                metrics_results["prophet"] = prophet_result.accuracy_metrics
                successful_models.append("prophet")
                logger.info("Prophet model succeeded (parallel)")
            else:
                # Linear or XGBoost result is a dict with values and metrics
                result_dict = cast("dict[str, Any]", result)
                predictions[name] = result_dict["values"]
                metrics_value = result_dict.get("metrics")
                if metrics_value is not None:
                    metrics_results[name] = cast("dict[str, Any]", metrics_value)
                successful_models.append(name)
                logger.info(f"{name.capitalize()} model succeeded (parallel)")
    else:
        logger.info("No models configured to run")

    # Story 6.4 AC6: Fallback strategy
    if not successful_models:
        logger.warning("All ensemble models failed, falling back to Prophet-multivariate")
        # Try Prophet-multivariate as final fallback
        try:
            fallback_result = await generate_forecast(
                metric=metric,
                historical_data=historical_data,
                external_regressors=external_regressors,
                periods_ahead=periods_ahead,
            )
            return fallback_result
        except Exception:
            # Ultimate fallback: Prophet-univariate
            logger.warning("Prophet-multivariate failed, falling back to Prophet-univariate")
            return await generate_forecast(
                metric=metric,
                historical_data=historical_data,
                external_regressors=None,  # Force univariate
                periods_ahead=periods_ahead,
            )

    # Calculate weighted ensemble if multiple models succeeded
    if len(successful_models) == 1:
        # Only one model, use its predictions directly
        ensemble_values = predictions[successful_models[0]]
    else:
        ensemble_values = _calculate_weighted_average(predictions, weights, successful_models)

    # Build forecast points (use Prophet structure if available)
    if prophet_result:
        forecast_points = [
            ForecastPoint(
                date=p.date,
                value=ensemble_values[i] if i < len(ensemble_values) else p.value,
                lower=p.lower,  # Use Prophet CI
                upper=p.upper,  # Use Prophet CI
                label=p.label,
            )
            for i, p in enumerate(prophet_result.forecast)
        ]
    else:
        # Build from scratch (no Prophet available)
        last_date = df["ds"].max()
        forecast_points = []
        for i in range(periods_ahead):
            # Estimate next quarter date
            next_date = last_date + pd.DateOffset(months=3 * (i + 1))
            quarter = (next_date.month - 1) // 3 + 1
            label = f"Q{quarter} {next_date.year}"

            # Simple CI estimate: ±20% of value
            value = ensemble_values[i] if i < len(ensemble_values) else 0.0
            forecast_points.append(
                ForecastPoint(
                    date=next_date.to_pydatetime(),
                    value=value,
                    lower=value * 0.8,
                    upper=value * 1.2,
                    label=label,
                )
            )

    # Aggregate accuracy metrics
    combined_metrics: dict[str, float] = {}
    if metrics_results:
        rmse_values = [
            float(m.get("rmse", 0))
            for m in metrics_results.values()
            if isinstance(m.get("rmse"), (int, float))
        ]
        if rmse_values:
            combined_metrics["rmse"] = float(np.mean(rmse_values))
            combined_metrics["mae"] = 0.0
            combined_metrics["mape"] = 0.0

    # Build ForecastResult
    basis_text = f"Ensemble of {len(successful_models)} models"
    if selected:
        basis_text += f" with {len(selected)} regressors"

    result = ForecastResult(
        metric_name=metric,
        historical_data=historical_data.points,
        forecast=forecast_points,
        model_type="ensemble",
        ensemble_models=successful_models,
        individual_predictions=predictions,
        ensemble_weights={k: weights.get(k, 0.0) for k in successful_models},
        accuracy_metrics=combined_metrics,
        regressors_used=selected,
        basis=basis_text,
        accuracy_estimate="±15% (NFR10 target)",
        periods_ahead=periods_ahead,
    )

    # Generate LLM explanation
    context = f"Ensemble forecast for {metric} using {', '.join(successful_models)}"
    if selected:
        context += f" with external regressors: {', '.join(selected)}"
    result.confidence_reasoning = await explain_forecast(result, context)

    logger.info(
        "Ensemble forecast generated",
        extra={
            "metric": metric,
            "successful_models": successful_models,
            "forecast_points": len(forecast_points),
            "regressors": selected,
        },
    )

    return result
