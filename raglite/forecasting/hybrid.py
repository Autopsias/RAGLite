"""Hybrid forecasting engine combining Prophet statistical + LLM reasoning.

Story 4.2: Forecasting Engine Implementation.
Story 6.3: Multi-variate forecasting with external regressors.
Story 6.8: Added LightGBM to ensemble (AC4), Ridge/Lasso regression (AC5),
           and regime change detection (AC6).

PERFORMANCE FIX (2025-11-29): Prophet import is lazy-loaded to avoid
50-60s cold start penalty during pytest collection. Prophet is only
imported when generate_forecast() is actually called.
"""

from __future__ import annotations

import json
import os
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from catboost import CatBoostRegressor
    from prophet import Prophet
    from sklearn.linear_model import LinearRegression

    from raglite.external_data.storage import ExternalDataStorage

# Story 6.4: Module-level executor for sklearn/xgboost (not async-native)
# Limited to 2 workers to manage memory when running models in parallel
_sklearn_executor = ThreadPoolExecutor(max_workers=2)

from raglite.forecasting.models.arima_model import fit_arima
from raglite.forecasting.models.chronos_model import (
    generate_chronos_cold_start_forecast,
)
from raglite.forecasting.models.ets_model import fit_ets
from raglite.shared.clients import get_mistral_client

# Story 7b-6: Model selection cache integration
try:
    from raglite.external_data.storage import get_cached_model_selection
except ImportError:
    # Storage module may not be available in some test scenarios
    get_cached_model_selection = None  # type: ignore

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


from raglite.forecasting.models.base import MIN_DATA_POINTS, InsufficientDataError
from raglite.shared.logging import get_logger
from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesData, TimeSeriesPoint

logger = get_logger(__name__)


# =============================================================================
# Story 6.8 AC6: Regime Change Detection Data Types
# =============================================================================

# Story 6.3: Constants for multi-variate forecasting
# Story 6.10.4: Increased from 10% to 30% to tolerate date range mismatches
# between external data (2020-2025) and SECIL data (2021-2025)
MAX_MISSING_RATIO = 0.30  # Maximum 30% missing data allowed
MAX_INTERPOLATION_GAP = 3  # Maximum periods to interpolate
MIN_CV_DATA_POINTS = 12  # Minimum points for cross-validation


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
) -> tuple[bool, str, dict[str, Any]]:
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
    metadata: dict[str, Any] = {}

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

    # BUG FIX (P0): Handle duplicate indices in target before creating DataFrame
    # Duplicates cause "cannot reindex on an axis with duplicate labels" error
    if target.index.duplicated().any():
        logger.warning(
            "Duplicate dates detected in target time-series - aggregating by taking mean",
            extra={"duplicates": target.index.duplicated().sum()},
        )
        target = target.groupby(target.index).mean()

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
    Story 6.10.4: Auto-resample high-frequency regressors (weekly/daily) to
    monthly before alignment to prevent high missing ratio.

    Args:
        regressors: Dictionary of regressor series
        target_index: Target DatetimeIndex to align to
        target_series: Optional target series for YoY% detection
        auto_transform_yoy: Auto-transform detected YoY% data (default: True)

    Returns:
        Dictionary of prepared regressor series (skips regressors with too much
        missing data instead of raising - Story 6.10.4)
    """
    prepared = {}

    # Story 6.11: Handle duplicate indices in target (can occur after YTD→Monthly conversion)
    if target_index.duplicated().any():
        logger.warning(
            "Target index has duplicates, deduplicating",
            extra={"duplicates": int(target_index.duplicated().sum())},
        )
        # Keep first occurrence of each date
        unique_mask = ~target_index.duplicated(keep="first")
        target_index = target_index[unique_mask]

    # Story 6.10.4: Detect target frequency for logging purposes
    if len(target_index) >= 2:
        avg_days = (target_index[-1] - target_index[0]).days / (len(target_index) - 1)
        _target_frequency = (
            "monthly"
            if 25 <= avg_days <= 35
            else ("bimonthly" if 50 <= avg_days <= 70 else "irregular")
        )
    else:
        avg_days = 30.0
        _target_frequency = "monthly"

    for name, series in regressors.items():
        working_series = series.copy()

        # Story 6.11: Auto-resample high-frequency data to monthly
        # Always resample if regressor has 3x+ more points than target (weekly/daily data)
        # This works for monthly, bimonthly, or irregular targets because:
        # 1. Weekly/daily data gets aggregated to monthly means
        # 2. Reindex to target dates finds matching month-start dates
        if len(working_series) > len(target_index) * 3:
            # Regressor has 3x+ more points than target - likely weekly or daily data
            logger.info(
                f"Auto-resampling high-frequency regressor {name} to monthly",
                extra={
                    "original_points": len(working_series),
                    "target_points": len(target_index),
                },
            )
            # Resample to month-start with mean aggregation
            working_series = working_series.resample("MS").mean()
            working_series = working_series.dropna()
            logger.info(
                f"Resampled {name} to monthly",
                extra={"new_points": len(working_series)},
            )

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

        # Story 6.11: Handle duplicate indices in working_series before reindex
        if working_series.index.duplicated().any():
            # Keep mean of duplicates
            working_series = working_series.groupby(working_series.index).mean()

        # Reindex to target index
        aligned = working_series.reindex(target_index)

        # Check missing ratio
        missing_count = aligned.isna().sum()
        missing_ratio = missing_count / len(aligned)

        # Story 6.10.4: Skip regressors with too much missing data instead of failing
        if missing_ratio > MAX_MISSING_RATIO:
            logger.warning(
                f"Skipping regressor '{name}' - {missing_ratio:.1%} missing values "
                f"(max allowed: {MAX_MISSING_RATIO:.0%})",
                extra={
                    "regressor": name,
                    "missing_ratio": missing_ratio,
                    "max_allowed": MAX_MISSING_RATIO,
                },
            )
            continue  # Skip this regressor, continue with others

        # Linear interpolation for gaps <= MAX_INTERPOLATION_GAP
        if missing_count > 0:
            # Interpolate with limit
            aligned = aligned.interpolate(method="linear", limit=MAX_INTERPOLATION_GAP)

            # Forward-fill remaining edge cases (max 3 periods)
            aligned = aligned.ffill(limit=MAX_INTERPOLATION_GAP)
            aligned = aligned.bfill(limit=MAX_INTERPOLATION_GAP)

        # Final validation - skip if still has NaN instead of failing
        if aligned.isna().any():
            remaining_missing = aligned.isna().sum()
            logger.warning(
                f"Skipping regressor '{name}' - still has {remaining_missing} missing values after interpolation",
                extra={
                    "regressor": name,
                    "remaining_missing": remaining_missing,
                },
            )
            continue  # Skip this regressor, continue with others

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
        # Story 6.11: Exclude overlapping dates from historical to avoid duplicate indices
        # This can happen when historical data extends into the future period
        non_overlapping_historical = historical[~historical.index.isin(future_values.index)]
        combined = pd.concat([non_overlapping_historical, future_values])
        # Also handle any remaining duplicates (from data issues)
        if combined.index.duplicated().any():
            combined = combined.groupby(combined.index).mean()
        extended[name] = combined

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


# FIX (2025-12-16): Pre-forecasting data quality validation
# Validates time-series data before forecasting to catch data quality issues early
POSITIVE_ONLY_METRICS = {"ebitda", "revenue", "capacity_utilization", "sales_volume"}
ALLOW_NEGATIVE_METRICS = {"variable_cost", "thermal_cost", "electricity_cost"}  # Cost adjustments


def validate_timeseries_for_forecast(
    metric: str, points: list[TimeSeriesPoint]
) -> tuple[bool, list[str]]:
    """Pre-flight validation for time-series data before forecasting.

    FIX (2025-12-16): Detects data quality issues that cause forecast failures:
    1. Scale within expected range (catches kEUR/M€ mixing after extraction)
    2. Sign consistency (positive/negative per metric type)
    3. No extreme swings (>10x between consecutive points = data contamination)

    Args:
        metric: Name of the metric being forecast
        points: List of TimeSeriesPoint data to validate

    Returns:
        Tuple of (is_valid, list_of_issues). is_valid=True if no critical issues.
        Issues are logged as warnings but do not block forecasting.
    """
    if not points:
        return False, ["No data points provided"]

    issues: list[str] = []
    values = [p.value for p in points if p.value is not None]

    if not values:
        return False, ["All data points have None values"]

    metric_lower = metric.lower()

    # Check 1: Sign consistency for positive-only metrics
    if metric_lower in POSITIVE_ONLY_METRICS:
        neg_values = [v for v in values if v < 0]
        if neg_values:
            issues.append(
                f"Found {len(neg_values)} negative values for positive-only metric '{metric}': "
                f"{neg_values[:3]}{'...' if len(neg_values) > 3 else ''}"
            )
            logger.warning(
                f"Data quality issue: Negative values in {metric}",
                extra={
                    "metric": metric,
                    "negative_count": len(neg_values),
                    "sample": neg_values[:3],
                },
            )

    # Check 2: Detect extreme swings (10x jumps indicate data contamination)
    swing_count = 0
    for i in range(1, len(values)):
        if values[i - 1] != 0:
            ratio = abs(values[i] / values[i - 1])
            if ratio > 10 or ratio < 0.1:
                swing_count += 1
                if swing_count <= 3:  # Only log first 3
                    issues.append(
                        f"10x swing at index {i}: {values[i - 1]:.2f} -> {values[i]:.2f} (ratio: {ratio:.1f}x)"
                    )

    if swing_count > 0:
        logger.warning(
            f"Data quality issue: {swing_count} extreme swings (>10x) detected in {metric}",
            extra={"metric": metric, "swing_count": swing_count},
        )

    # Check 3: Scale sanity check for known metrics
    EXPECTED_RANGES = {
        "ebitda": (1, 500),  # 1-500 M€ for SECIL GROUP
        "revenue": (10, 2000),  # 10-2000 M€
        "variable_cost": (10, 500),  # 10-500 EUR/ton
        "capacity_utilization": (0, 100),  # 0-100%
    }

    if metric_lower in EXPECTED_RANGES:
        expected_min, expected_max = EXPECTED_RANGES[metric_lower]
        abs_values = [abs(v) for v in values]
        max_val = max(abs_values)

        if max_val > expected_max * 100:  # 100x threshold for scale detection
            issues.append(
                f"Scale issue: max value {max_val:.0f} exceeds expected max {expected_max} by 100x+ "
                f"(possible kEUR/M€ mixing still present)"
            )
            logger.warning(
                f"Data quality issue: Scale mismatch in {metric}",
                extra={"metric": metric, "max_value": max_val, "expected_max": expected_max},
            )

    # Return validation result (issues are warnings, not blockers)
    is_valid = len(issues) == 0
    if not is_valid:
        logger.info(
            f"Pre-forecast validation found {len(issues)} issues for {metric}",
            extra={"metric": metric, "issue_count": len(issues)},
        )

    return is_valid, issues


# =============================================================================
# Story 7b-6: Model Selection Routing and Model-Specific Generators
# =============================================================================


async def _route_to_model(
    model_name: str,
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Route forecast request to appropriate model function.

    Story 7b-6 AC-7b.6.2: Routes to correct model based on cached selection.

    Args:
        model_name: Name of the model to use (e.g., 'arima', 'prophet', 'xgboost')
        metric: Metric being forecast
        historical_data: Historical time series data
        periods_ahead: Forecast horizon
        external_regressors: Optional external regressors

    Returns:
        ForecastResult from the selected model

    Raises:
        ValueError: If model_name is unknown
    """
    model_routers = {
        "arima": _generate_arima_forecast,
        "ets": _generate_ets_forecast,
        "prophet": _generate_prophet_forecast,
        "xgboost": _generate_xgboost_forecast,
        "lightgbm": _generate_lightgbm_forecast,
        "catboost": _generate_catboost_forecast,
        "chronos": _generate_chronos_forecast,
        "tft": _generate_tft_forecast,
        "linear": _generate_linear_forecast,
    }

    if model_name not in model_routers:
        raise ValueError(f"Unknown model: {model_name}")

    generator = model_routers[model_name]
    return await generator(  # type: ignore[no-any-return,operator]
        metric=metric,
        historical_data=historical_data,
        periods_ahead=periods_ahead,
        external_regressors=external_regressors,
    )


async def _generate_arima_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
    model_source: str = "cached",
) -> ForecastResult:
    """Generate forecast using ARIMA model.

    Story 7b-6 AC-7b.6.2: ARIMA model wrapper.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors
        model_source: Source of model selection ('cached', 'default', 'fallback')

    Returns:
        ForecastResult from ARIMA model
    """

    # Prepare data - ARIMA expects pandas Series
    dates = pd.to_datetime([p.date for p in historical_data.points])
    values = pd.Series([p.value for p in historical_data.points], index=dates)

    # Prepare exogenous variables if provided
    X_train = None
    X_future = None
    if external_regressors:
        # Align regressors to historical dates
        X_train = pd.DataFrame()
        for name, series in external_regressors.items():
            aligned = series.reindex(dates)
            X_train[name] = aligned

        # Generate future dates for forecast
        last_date = dates[-1]
        freq = "MS" if len(dates) >= 2 else "MS"  # Monthly by default
        pd.date_range(start=last_date, periods=periods_ahead + 1, freq=freq)[1:]

        # Prepare future regressors using last known values (constant strategy)
        X_future = pd.DataFrame()
        for name, series in external_regressors.items():
            last_value = series.iloc[-1] if len(series) > 0 else 0.0
            X_future[name] = [last_value] * periods_ahead

    # Fit ARIMA model
    model, metrics, predictions, conf_int = await fit_arima(
        y_train=values,
        X_train=X_train,
        X_future=X_future,
        forecast_horizon=periods_ahead,
    )

    # Convert predictions to ForecastPoints
    forecast_points = []
    last_date = dates[-1]
    for i in range(periods_ahead):
        # Generate next date
        next_date = last_date + pd.DateOffset(months=i + 1)
        label = next_date.strftime("%b %Y")

        forecast_points.append(
            ForecastPoint(
                date=next_date.to_pydatetime(),
                value=float(predictions[i]),
                lower=float(conf_int[i][0]),
                upper=float(conf_int[i][1]),
                label=label,
            )
        )

    # Build result
    regressors_used = list(external_regressors.keys()) if external_regressors else []
    model_type = "arima_multivariate" if regressors_used else "arima_univariate"
    basis_text = f"ARIMA{metrics['order']} model with {len(historical_data.points)} data points"
    if regressors_used:
        basis_text += f" and {len(regressors_used)} regressors"

    return ForecastResult(
        metric_name=metric,
        historical_data=historical_data.points,
        forecast=forecast_points,
        basis=basis_text,
        accuracy_estimate="±10% (ARIMA model)",
        periods_ahead=periods_ahead,
        model_type=model_type,
        regressors_used=regressors_used,
        model_source=model_source,  # type: ignore[arg-type]
    )


async def _generate_ets_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
    model_source: str = "cached",
) -> ForecastResult:
    """Generate forecast using ETS model.

    Story 7b-6 AC-7b.6.2: ETS model wrapper.
    Note: ETS does not support exogenous regressors.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors (ignored for ETS)
        model_source: Source of model selection ('cached', 'default', 'fallback')

    Returns:
        ForecastResult from ETS model
    """
    # Extract time series data
    dates = pd.to_datetime([p.date for p in historical_data.points])
    values = pd.Series([p.value for p in historical_data.points], index=dates)

    # Fit ETS model
    model, metrics, predictions, conf_int = await fit_ets(
        y_train=values,
        forecast_horizon=periods_ahead,
        frequency="M",
    )

    # Convert predictions to ForecastPoints
    forecast_points = []
    last_date = dates[-1]
    for i in range(periods_ahead):
        # Generate next date
        next_date = last_date + pd.DateOffset(months=i + 1)
        label = next_date.strftime("%b %Y")

        forecast_points.append(
            ForecastPoint(
                date=next_date.to_pydatetime(),
                value=float(predictions[i]),
                lower=float(conf_int[i][0]),
                upper=float(conf_int[i][1]),
                label=label,
            )
        )

    # Build result
    basis_text = f"ETS model with {len(historical_data.points)} data points"

    return ForecastResult(
        metric_name=metric,
        historical_data=historical_data.points,
        forecast=forecast_points,
        basis=basis_text,
        accuracy_estimate="±10% (ETS model)",
        periods_ahead=periods_ahead,
        model_type="ets",
        regressors_used=[],
        model_source=model_source,  # type: ignore[arg-type]
    )


async def _generate_prophet_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Generate forecast using Prophet model.

    Story 7b-6 AC-7b.6.2: Prophet model wrapper.
    This uses the existing generate_forecast logic.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors

    Returns:
        ForecastResult from Prophet model
    """
    # Prophet forecasting is the default path in generate_forecast
    # This function exists for routing consistency but delegates to main logic
    raise NotImplementedError("Prophet wrapper - should use main generate_forecast logic")


async def _generate_xgboost_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Generate forecast using XGBoost model.

    Story 7b-6 AC-7b.6.2: XGBoost model wrapper.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors

    Returns:
        ForecastResult from XGBoost model
    """
    # TODO: Implement XGBoost forecasting
    raise NotImplementedError("XGBoost forecasting not yet implemented")


async def _generate_lightgbm_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Generate forecast using LightGBM model.

    Story 7b-6 AC-7b.6.2: LightGBM model wrapper.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors

    Returns:
        ForecastResult from LightGBM model
    """
    # TODO: Implement LightGBM forecasting
    raise NotImplementedError("LightGBM forecasting not yet implemented")


async def _generate_catboost_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Generate forecast using CatBoost model.

    Story 7b-6 AC-7b.6.2: CatBoost model wrapper.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors

    Returns:
        ForecastResult from CatBoost model
    """
    # TODO: Implement CatBoost forecasting
    raise NotImplementedError("CatBoost forecasting not yet implemented")


async def _generate_chronos_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Generate forecast using Chronos model.

    Story 7b-6 AC-7b.6.2: Chronos model wrapper.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors (Chronos may not support)

    Returns:
        ForecastResult from Chronos model
    """
    # TODO: Implement Chronos forecasting (may use generate_chronos_cold_start_forecast)
    raise NotImplementedError("Chronos forecasting not yet implemented")


async def _generate_tft_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Generate forecast using TFT (Temporal Fusion Transformer) model.

    Story 7b-6 AC-7b.6.2: TFT model wrapper.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors

    Returns:
        ForecastResult from TFT model
    """
    # TODO: Implement TFT forecasting
    raise NotImplementedError("TFT forecasting not yet implemented")


async def _generate_linear_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Generate forecast using Linear Regression model.

    Story 7b-6 AC-7b.6.2: Linear model wrapper (Ridge/Lasso).

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors

    Returns:
        ForecastResult from Linear model
    """
    # TODO: Implement Linear forecasting (Ridge/Lasso)
    raise NotImplementedError("Linear forecasting not yet implemented")


async def generate_forecast(
    metric: str,
    historical_data: TimeSeriesData | None = None,
    periods_ahead: int = 4,
    external_regressors: dict[str, pd.Series] | None = None,
    frequency: str = "M",
    future_regressor_strategy: str = "constant",
    use_model_selection: bool = True,
) -> ForecastResult:
    """Generate forecast for financial metric using Prophet + LLM.

    Story 4.2 AC1-AC4: Hybrid forecasting with Prophet statistical model
    and Mistral Large for confidence reasoning.

    Story 6.3: Extended with multi-variate forecasting support.
    Story 7b-6: Integrated with model selection cache for automatic optimal model routing.

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
        use_model_selection: If True, use cached model selection (default: True).
            When enabled, checks model_selection cache and routes to optimal model.
            When disabled, uses default Prophet model.

    Returns:
        ForecastResult with predictions, confidence intervals, and reasoning.
        When external_regressors provided, includes:
        - model_type: 'prophet_multivariate'
        - accuracy_metrics: {'rmse': X, 'mae': Y, 'mape': Z}
        - regressors_used: list of regressor names
        - improvement_vs_baseline: percentage improvement vs Epic 4 baseline
        When use_model_selection=True, includes:
        - model_source: 'cached' (from cache), 'default' (no cache), 'fallback' (error)
        - model_selection_reason: Human-readable explanation of model choice

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

    # Story 7b-6 AC-7b.6.1: Check model selection cache first
    model_source = "default"
    model_selection_reason = None
    selected_model = None
    selected_regressors = None

    if use_model_selection and get_cached_model_selection is not None:
        try:
            cached = await get_cached_model_selection(metric)
            if cached and not cached.is_expired:
                selected_model = cached.best_model
                selected_regressors = cached.regressor_list if cached.use_regressors else None
                model_source = "cached"
                # Get model rationale from data_characteristics if available
                if cached.data_characteristics:
                    model_selection_reason = cached.data_characteristics.get("model_rationale")
                logger.info(
                    f"Using cached model selection for {metric}",
                    extra={
                        "model": selected_model,
                        "source": model_source,
                        "use_regressors": cached.use_regressors,
                        "regressor_count": len(selected_regressors) if selected_regressors else 0,
                    },
                )
            else:
                cache_status = "miss" if not cached else "expired"
                logger.info(
                    f"No valid cache for {metric}, using default Prophet",
                    extra={"cache_status": cache_status},
                )
        except Exception as e:
            # Any error in cache lookup shouldn't break forecasting
            logger.warning(
                f"Error checking model selection cache for {metric}: {e}",
                extra={"error": str(e)},
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
            "use_model_selection": use_model_selection,
            "selected_model": selected_model,
        },
    )

    # Validate minimum data requirement (AC4: 6+ data points for reliability)
    if historical_data is None:
        raise InsufficientDataError(
            "No historical data provided. Either pass historical_data "
            "or use fetch_historical_metric() to load from PostgreSQL."
        )

    # Story 6.13 AC2: Cold-start path for insufficient data
    # Route to Chronos-2 zero-shot when < MIN_DATA_POINTS
    if len(historical_data.points) < MIN_DATA_POINTS:
        logger.info(
            "Cold-start detected: routing to Chronos-2 zero-shot",
            extra={"metric": metric, "data_points": len(historical_data.points)},
        )
        return await generate_chronos_cold_start_forecast(
            metric=metric,
            historical_data=historical_data,
            periods_ahead=periods_ahead,
        )

    # Story 7b-6 AC-7b.6.3: Filter external_regressors based on cached selection
    # This applies to ALL models when cache hit
    filtered_regressors_for_routing = external_regressors
    if selected_model is not None:
        if selected_regressors is not None and external_regressors is not None:
            # Only pass regressors that are in the cached selection AND available
            filtered_regressors_for_routing = {
                name: series
                for name, series in external_regressors.items()
                if name in selected_regressors
            }
            if not filtered_regressors_for_routing:
                # If none of the selected regressors are available, pass None
                filtered_regressors_for_routing = None
        elif selected_regressors is None:
            # use_regressors=False in cache - don't pass any regressors
            filtered_regressors_for_routing = None

    # Story 7b-6 AC-7b.6.2: Route to selected model (including Prophet)
    if selected_model is not None:
        # AC-7b.6.4: Try to route to selected model with fallback
        try:
            result = await _route_to_model(
                model_name=selected_model,
                metric=metric,
                historical_data=historical_data,
                periods_ahead=periods_ahead,
                external_regressors=filtered_regressors_for_routing,
            )
            # Add metadata from cache
            result.model_source = model_source  # type: ignore[assignment]
            if model_selection_reason:
                result.model_selection_reason = model_selection_reason

            # Add LLM explanation
            explanation = await explain_forecast(  # type: ignore[call-arg]
                metric_name=metric,
                forecast_points=result.forecast,
                historical_data=historical_data.points,
            )
            result.confidence_reasoning = explanation

            return result
        except NotImplementedError:
            # Model not yet implemented - fall through to main Prophet path as fallback
            logger.debug(
                f"Model {selected_model} not yet implemented, using main Prophet path for {metric}",
                extra={"metric": metric, "requested_model": selected_model},
            )
            # Update external_regressors to filtered version for Prophet path
            external_regressors = filtered_regressors_for_routing
            # Update source to indicate fallback
            model_source = "fallback"
            model_selection_reason = (
                f"{selected_model} model not yet implemented, using Prophet fallback"
            )
        except Exception as e:
            # Fallback to Prophet on model failure
            logger.warning(
                f"Model {selected_model} failed for {metric}, falling back to Prophet",
                extra={
                    "model": selected_model,
                    "error": str(e),
                    "metric": metric,
                },
            )
            # Update source to indicate fallback
            model_source = "fallback"
            model_selection_reason = f"Fallback due to {selected_model} failure: {str(e)}"
            # Fall through to main Prophet path below

    # FIX (2025-12-16): Pre-flight data quality validation
    # Validates data before forecasting to catch issues like:
    # - Negative values for positive-only metrics (EBITDA, revenue)
    # - Extreme swings (>10x) indicating data contamination
    # - Scale mismatches (kEUR vs M€ that wasn't normalized)
    is_valid, validation_issues = validate_timeseries_for_forecast(
        metric=metric, points=historical_data.points
    )
    if not is_valid:
        # Log issues but don't block forecasting (data already filtered/normalized upstream)
        # The validation serves as a diagnostic tool to detect if upstream fixes are working
        logger.warning(
            f"Pre-forecast validation issues for {metric}: {validation_issues[:3]}",
            extra={
                "metric": metric,
                "issues": validation_issues,
                "data_points": len(historical_data.points),
            },
        )

    # Step 1: Prepare DataFrame for Prophet (requires 'ds' and 'y' columns)
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

    # Step 2: Configure Prophet based on data availability
    # CRITICAL: Only enable yearly seasonality if we have 12+ months of data.
    # With less data, Prophet hallucinates seasonal patterns causing negative forecasts.
    data_span_days = (df["ds"].max() - df["ds"].min()).days
    has_full_year_data = data_span_days >= 335  # ~11 months minimum for yearly seasonality

    # Story 6.23: Detect ALL metrics that need flat growth
    # Cement industry metrics have sparse/irregular patterns where trend extrapolation causes overfitting.
    # Flat growth Prophet achieves much better accuracy than linear trend or external regressors:
    # - Variable Cost: 8.04% MAPE (vs >100% with regressors)
    # - Capacity Utilization: 3.49% MAPE (vs >100% with regressors)
    # - Revenue (Turnover+VAT): 6.32% MAPE (was 787% with regressors)
    # - EBITDA: Testing (was 852% with regressors)
    # - Sales Volume: Testing (was 31% with regressors)
    metric_lower = metric.lower().strip()
    flat_growth_metrics = [
        # Story 6.25: REMOVED variable_cost - Dec 9 achieved 0.7% MAPE with regressors
        # Story 6.25: REMOVED electricity_cost - Dec 9 achieved 3.0% MAPE with regressors
        # Story 6.25: REMOVED avg_selling_price - Dec 9 achieved 1.6% MAPE with regressors
        # Commit 88785ba added these to flat growth causing 9-11x regressions
        # Story 6.24: REMOVED thermal energy - flat growth = 25.48% MAPE, test linear growth
        # Thermal Energy has 69 periods, 1398 rows (NOT sparse), should use Prophet linear growth
        # Utilization metrics (DB names + variable names)
        "capacity_utilization",
        "frequency ratio",
        "utilization",
        # Financial metrics - sparse data patterns (DB names + variable names)
        "revenue",
        "turnover",
        "turnover+vat",
        # Story 6.25: EBITDA REMOVED from flat growth - commit 88785ba regression!
        # Before 88785ba (Dec 9): linear growth + regressors = 0.2-2.5% MAPE
        # After 88785ba (Dec 13): flat growth added EBITDA here = 13.56% MAPE
        # Root cause: Flat growth disables trend component that regressors capture
        "profit",
        "net_income",
        # Story 6.25: REMOVED sales metrics - Dec 9 achieved 0.8% MAPE with regressors
        # Commit 88785ba added these to flat growth = 31.68% MAPE (39.6x regression)
        # Sales volume responds to macroeconomic trends (euribor, diesel, ttf_gas)
    ]
    use_flat_growth = any(metric_kw in metric_lower for metric_kw in flat_growth_metrics)

    # For short data spans, use simpler model (trend only)
    Prophet = _get_prophet_class()  # Lazy-load Prophet on first use

    # FIX (2025-12-14): Detect significant gaps in data that cause Prophet instability
    # EBITDA data often spans multiple years but has multi-month gaps (e.g., Mar 2023 → Jan 2024)
    # This causes changepoint_prior_scale=0.2 to produce negative forecast extrapolations
    # because Prophet treats gaps as potential changepoints, leading to erratic trend estimates
    has_data_gaps = False
    if len(df) >= 2:
        for i in range(len(df) - 1):
            gap_days = (df["ds"].iloc[i + 1] - df["ds"].iloc[i]).days
            if gap_days > 60:  # More than 2 months gap indicates sparse data
                has_data_gaps = True
                logger.info(
                    f"Data gap detected: {gap_days} days between {df['ds'].iloc[i]} and {df['ds'].iloc[i + 1]}",
                    extra={"metric": metric, "gap_days": gap_days},
                )
                break

    # Story 6.24: Special case for Thermal Energy - override gap detection
    # Thermal Energy has expected quarterly gaps from SECIL reports (every ~90 days)
    # These gaps are normal reporting cycles, NOT sparse data that needs conservative priors
    # Without this override, gap detection triggers and breaks fuel price correlation (2.6% → 23.76% MAPE regression)
    if metric.lower() in ("thermal_cost", "thermal energy", "thermal"):
        if has_data_gaps:
            logger.info(
                "Thermal Energy: Overriding gap detection (quarterly reporting pattern is expected)",
                extra={
                    "metric": metric,
                    "original_has_data_gaps": True,
                    "override": "quarterly_pattern",
                },
            )
        has_data_gaps = False  # Override - quarterly pattern is normal

    # Story 6.23: Very conservative changepoint_prior_scale for flat growth
    if use_flat_growth:
        changepoint_prior = 0.001  # Minimal flexibility for flat cost metrics
        logger.info(
            f"Using flat growth for {metric} (detected as sparse data pattern)",
            extra={"metric": metric, "growth": "flat", "changepoint_prior": changepoint_prior},
        )
    elif not has_full_year_data or has_data_gaps:
        changepoint_prior = 0.05  # Conservative for short data OR data with gaps
        if has_data_gaps:
            logger.info(
                f"Using conservative changepoint prior for {metric} due to data gaps",
                extra={
                    "metric": metric,
                    "changepoint_prior": changepoint_prior,
                    "has_data_gaps": True,
                },
            )
    else:
        changepoint_prior = 0.2  # Standard for full year data

    model = Prophet(
        growth="flat" if use_flat_growth else "linear",  # Story 6.23: flat for sparse cost metrics
        yearly_seasonality=has_full_year_data
        and not use_flat_growth,  # Disable seasonality for flat growth
        weekly_seasonality=False,  # Financial data is quarterly/monthly, not weekly
        daily_seasonality=False,
        changepoint_prior_scale=changepoint_prior,
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
    # FIX: Use median of RECENT date differences to handle sparse historical data
    # Story 6.23: Variable Cost data is sparse historically but monthly recently
    if len(df) >= 2:
        # Use last 5 date differences (or all if fewer than 5)
        num_recent = min(5, len(df) - 1)
        start_idx = len(df) - 1 - num_recent
        date_diffs = [
            (df["ds"].iloc[i + 1] - df["ds"].iloc[i]).days for i in range(start_idx, len(df) - 1)
        ]
        median_diff = sorted(date_diffs)[len(date_diffs) // 2]
        is_monthly_data = 25 <= median_diff <= 35
    else:
        is_monthly_data = False

    if is_monthly_data:
        # Story 6.7: Respect frequency parameter - return monthly if requested
        output_monthly = frequency.upper() in ("M", "ME", "MS")

        if output_monthly:
            # Monthly input, monthly output (Story 6.7)
            # FIX (2025-12-14): Use freq="MS" to match historical data format
            # Historical data uses month-start dates (e.g., 2025-10-01)
            # Using "ME" (month-end) caused severe forecast errors because Prophet
            # treated month-end as different time points, causing wild interpolation
            # (e.g., €102M forecast instead of €15K for EBITDA)
            future = model.make_future_dataframe(periods=periods_ahead, freq="MS")

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
                        # Story 6.11: Reindex and fill any NaN with forward-fill then backward-fill
                        reindexed = extended[name].reindex(future["ds"])
                        reindexed = reindexed.ffill().bfill()
                        future[name] = reindexed.values

            prophet_forecast = model.predict(future)

            # FIX (2025-12-14): With freq="MS", Prophet produces clean future dates
            # No need for complex filtering - just take the last periods_ahead rows
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

            # FIX (2025-12-16): Clamp negative values for positive-only metrics
            # EBITDA, revenue, capacity_utilization should never be negative
            if metric.lower() in POSITIVE_ONLY_METRICS:
                clamped_count = 0
                for i, point in enumerate(forecast_points):
                    if point.value < 0:
                        clamped_count += 1
                        forecast_points[i] = ForecastPoint(
                            date=point.date,
                            value=0.0,  # Clamp to 0
                            lower=max(0.0, point.lower),
                            upper=point.upper,
                            label=point.label,
                        )
                if clamped_count > 0:
                    logger.warning(
                        f"Clamped {clamped_count} negative forecast values to 0 for positive-only metric {metric}",
                        extra={"metric": metric, "clamped_count": clamped_count},
                    )

            logger.debug(
                "Monthly forecast generated",
                extra={"periods": periods_ahead, "output_frequency": "monthly"},
            )
        else:
            # Monthly input, quarterly output (aggregate 3 months)
            monthly_periods = periods_ahead * 3  # 3 months per quarter
            # FIX (2025-12-14): Use freq="MS" to match historical data format
            future = model.make_future_dataframe(periods=monthly_periods, freq="MS")

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
                        # Story 6.11: Reindex and fill any NaN with forward-fill then backward-fill
                        reindexed = extended[name].reindex(future["ds"])
                        reindexed = reindexed.ffill().bfill()
                        future[name] = reindexed.values

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
                    # Story 6.11: Reindex and fill any NaN with forward-fill then backward-fill
                    # (matches monthly path at line 1461-1464)
                    reindexed = extended[name].reindex(future["ds"])
                    reindexed = reindexed.ffill().bfill()
                    future[name] = reindexed.values

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
        # Story 7b-6: Model selection metadata
        model_source=model_source,  # type: ignore[arg-type]
        model_selection_reason=model_selection_reason,
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

# Lazy-load sklearn to avoid import overhead (similar to Prophet)
_sklearn_loaded = False


def _get_linear_regression() -> Any:
    """Lazy-load LinearRegression from sklearn."""
    global _sklearn_loaded
    if not _sklearn_loaded:
        from sklearn.linear_model import LinearRegression

        _sklearn_loaded = True
        return LinearRegression
    from sklearn.linear_model import LinearRegression

    return LinearRegression


def _get_ridge_regression() -> Any:
    """Lazy-load Ridge regression from sklearn.

    Story 6.8 AC5: Ridge regression for regularized linear models.
    """
    from sklearn.linear_model import Ridge

    return Ridge


def _get_lasso_regression() -> Any:
    """Lazy-load Lasso regression from sklearn.

    Story 6.8 AC5: Lasso regression for L1 regularization (feature selection).
    """
    from sklearn.linear_model import Lasso

    return Lasso


def _get_time_series_split() -> Any:
    """Lazy-load TimeSeriesSplit from sklearn."""
    from sklearn.model_selection import TimeSeriesSplit

    return TimeSeriesSplit


_xgboost_loaded = False


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


# ===========================================================================
# Story 6.4: XGBoost Hyperparameter Grids
# ===========================================================================

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


# ===========================================================================
# Story 6.12: CatBoost Configuration
# ===========================================================================

_catboost_class: type[CatBoostRegressor] | None = None


def _get_catboost_class() -> type[CatBoostRegressor]:
    """Lazy-load CatBoostRegressor class on first use.

    Story 6.12 AC1: Lazy-load CatBoost to avoid import penalties.
    Story 6.12 Issue #7 fix: Graceful handling if CatBoost not installed.
    Story 6.12 CI fix: Add __sklearn_tags__ compatibility for scikit-learn 1.7+ and 1.8+.

    sklearn 1.8+ requires proper Tags object with regressor-specific fields.
    Fallback to sklearn 1.7.x approach if Tags import fails.

    Returns:
        CatBoostRegressor class from catboost library

    Raises:
        ImportError: If catboost is not installed with helpful message
    """
    global _catboost_class
    if _catboost_class is None:
        try:
            from catboost import CatBoostRegressor

            # Fix sklearn 1.7+ and 1.8+ compatibility: CatBoostRegressor lacks __sklearn_tags__
            # sklearn 1.8+ requires proper Tags object with regressor-specific fields
            # The most robust solution is to create a wrapper class that inherits from
            # sklearn's BaseEstimator to get proper __sklearn_tags__ method resolution
            if not hasattr(CatBoostRegressor, "__sklearn_tags__"):
                from sklearn.base import BaseEstimator

                # Create a wrapper class that adds sklearn compatibility
                # BaseEstimator must be AFTER CatBoostRegressor in MRO to avoid conflicts
                class SklearnCompatibleCatBoost(CatBoostRegressor, BaseEstimator):
                    """CatBoost wrapper with sklearn __sklearn_tags__ compatibility.

                    sklearn 1.7+ and 1.8+ require __sklearn_tags__ method.
                    By inheriting from BaseEstimator, we get proper method resolution.
                    """

                    pass

                # Keep the original class name for compatibility with tests and logging
                SklearnCompatibleCatBoost.__name__ = "CatBoostRegressor"
                SklearnCompatibleCatBoost.__qualname__ = "CatBoostRegressor"
                _catboost_class = SklearnCompatibleCatBoost
            else:
                _catboost_class = CatBoostRegressor
        except ImportError as e:
            logger.error(
                "CatBoost not installed. Install with: pip install catboost>=1.2",
                extra={"error": str(e)},
            )
            raise ImportError(
                "CatBoost is required for Story 6.12 ensemble forecasting. "
                "Install with: pip install catboost>=1.2"
            ) from e
    return cast("type[CatBoostRegressor]", _catboost_class)


# Story 6.12: CatBoost default hyperparameter grid
# CatBoost parameters tuned for time-series forecasting with categorical support
CATBOOST_PARAM_GRID = {
    "iterations": [300, 500, 800],
    "learning_rate": [0.01, 0.03, 0.1],
    "depth": [4, 6, 8],
    "l2_leaf_reg": [1, 3, 5],
}

# Fast mode for testing (reduced grid)
CATBOOST_PARAM_GRID_FAST = {
    "iterations": [500],
    "learning_rate": [0.03],
    "depth": [6],
    "l2_leaf_reg": [3],
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


def fit_ridge_regression(
    X: pd.DataFrame,
    y: pd.Series,
    feature_names: list[str],
    alpha: float = 1.0,
) -> tuple[Any, dict[str, float]]:
    """Fit Ridge Regression with L2 regularization.

    Story 6.8 AC5: Ridge regression for regularized linear models.

    Ridge regression adds L2 penalty to prevent overfitting:
    - Reduces coefficient magnitudes
    - Works well with multicollinearity
    - Never zeroes out coefficients

    Args:
        X: Feature DataFrame (regressors)
        y: Target series (metric values)
        feature_names: Names of features for logging
        alpha: Regularization strength (default: 1.0)

    Returns:
        Tuple of (fitted Ridge model, accuracy metrics dict with rmse/mae/mape)
    """
    Ridge = _get_ridge_regression()
    TimeSeriesSplit = _get_time_series_split()

    model = Ridge(alpha=alpha)

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

        rmse = float(np.sqrt(np.mean((y_val.values - predictions) ** 2)))
        cv_rmse_scores.append(rmse)

        mae = float(np.mean(np.abs(y_val.values - predictions)))
        cv_mae_scores.append(mae)

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
        "Ridge Regression fitted",
        extra={
            "features": feature_names,
            "alpha": alpha,
            "cv_rmse": metrics["rmse"],
            "cv_mae": metrics["mae"],
        },
    )

    return model, metrics


def fit_lasso_regression(
    X: pd.DataFrame,
    y: pd.Series,
    feature_names: list[str],
    alpha: float = 1.0,
) -> tuple[Any, dict[str, float]]:
    """Fit Lasso Regression with L1 regularization.

    Story 6.8 AC5: Lasso regression for L1 regularization (feature selection).

    Lasso regression adds L1 penalty for automatic feature selection:
    - Can zero out coefficients (sparse models)
    - Good for high-dimensional data
    - Built-in feature selection

    Args:
        X: Feature DataFrame (regressors)
        y: Target series (metric values)
        feature_names: Names of features for logging
        alpha: Regularization strength (default: 1.0)

    Returns:
        Tuple of (fitted Lasso model, accuracy metrics dict with rmse/mae/mape)
    """
    Lasso = _get_lasso_regression()
    TimeSeriesSplit = _get_time_series_split()

    model = Lasso(alpha=alpha, max_iter=10000)

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

        rmse = float(np.sqrt(np.mean((y_val.values - predictions) ** 2)))
        cv_rmse_scores.append(rmse)

        mae = float(np.mean(np.abs(y_val.values - predictions)))
        cv_mae_scores.append(mae)

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

    # Log non-zero coefficients for Lasso (feature selection insight)
    non_zero_coefs = sum(1 for c in model.coef_ if abs(c) > 1e-10)

    logger.info(
        "Lasso Regression fitted",
        extra={
            "features": feature_names,
            "alpha": alpha,
            "cv_rmse": metrics["rmse"],
            "cv_mae": metrics["mae"],
            "selected_features": non_zero_coefs,
            "total_features": len(feature_names),
        },
    )

    return model, metrics


def fit_catboost(
    X: pd.DataFrame,
    y: pd.Series,
    fast_mode: bool = False,
) -> tuple[CatBoostRegressor, dict[str, object]]:
    """Fit CatBoost regressor with hyperparameter tuning.

    Story 6.12 AC1: CatBoost with GridSearchCV (5-fold time-series split).

    CatBoost advantages:
    - Native categorical feature support (no encoding needed)
    - Handles missing values automatically
    - Ordered boosting reduces overfitting on small datasets
    - Symmetric trees for fast inference

    Args:
        X: Feature DataFrame (regressors)
        y: Target series (metric values)
        fast_mode: Use reduced param grid for testing (default: False)

    Returns:
        Tuple of (best fitted CatBoostRegressor model, accuracy metrics dict with rmse/mae/mape/best_params)
    """
    CatBoostRegressor = _get_catboost_class()
    GridSearchCV = _get_grid_search_cv()
    TimeSeriesSplit = _get_time_series_split()

    param_grid = CATBOOST_PARAM_GRID_FAST if fast_mode else CATBOOST_PARAM_GRID

    # Use fewer splits for small datasets
    n_splits = min(5, len(X) - 1)
    tscv = TimeSeriesSplit(n_splits=n_splits)

    # Use multiple scoring to get RMSE, MAE
    scoring = {
        "rmse": "neg_root_mean_squared_error",
        "mae": "neg_mean_absolute_error",
    }

    # CatBoost-specific parameters: silent mode and random state
    grid_search = GridSearchCV(
        CatBoostRegressor(
            random_state=42,
            verbose=False,
            loss_function="RMSE",
            allow_writing_files=False,  # Don't create temp files
        ),
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

    # Final refit on all data
    best_model.fit(X, y)
    mape = float(np.mean(mape_scores)) if mape_scores else 0.0

    metrics: dict[str, object] = {
        "rmse": float(best_rmse),
        "mae": float(best_mae),
        "mape": mape,
        "best_params": grid_search.best_params_,
    }

    logger.info(
        "CatBoost fitted",
        extra={
            "best_params": grid_search.best_params_,
            "cv_rmse": best_rmse,
            "cv_mae": best_mae,
            "fast_mode": fast_mode,
        },
    )

    return best_model, metrics


def _fit_and_forecast_catboost(
    X: pd.DataFrame,
    y: pd.Series,
    X_future: pd.DataFrame,
    periods_ahead: int,
    fast_mode: bool = False,
) -> dict[str, Any]:
    """Fit CatBoost and generate forecast (for ThreadPoolExecutor).

    Story 6.12 AC1: Combined fit+forecast for parallel execution.

    Args:
        X: Training feature DataFrame
        y: Target series
        X_future: Future feature values for prediction
        periods_ahead: Number of periods to forecast
        fast_mode: Use reduced hyperparameter grid

    Returns:
        Dict with 'values' list and 'metrics' dict
    """
    model, metrics = fit_catboost(X, y, fast_mode=fast_mode)
    predictions = model.predict(X_future)
    return {
        "values": predictions.tolist()[:periods_ahead],
        "metrics": metrics,
    }


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


# =============================================================================
# Story 7.5: Backward-Compatible Re-exports
# =============================================================================
# These re-exports maintain backward compatibility for external consumers
# that import from raglite.forecasting.hybrid after the refactoring

from raglite.forecasting.ensemble import generate_ensemble_forecast
from raglite.forecasting.models.xgboost_model import (
    _run_xgboost_forecast,
    fit_xgboost,
)

__all__ = [
    "generate_forecast",
    "generate_ensemble_forecast",
    "fetch_historical_metric",
    "explain_forecast",
    "InsufficientDataError",
    "MIN_DATA_POINTS",
    # Re-export XGBoost functions for backward compatibility
    "fit_xgboost",
    "_run_xgboost_forecast",
]
