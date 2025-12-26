"""Hybrid forecasting - Data preprocessing and validation.

Part of Story 8.1 refactoring to split hybrid.py.

Provides:
- select_regressors: Correlation-based regressor selection
- prepare_regressors: Align, interpolate, and validate regressors
- validate_timeseries_for_forecast: Pre-flight data quality checks
- transform_yoy_to_index: Convert YoY% changes to absolute index
- fetch_historical_metric: Load historical data from PostgreSQL
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from raglite.external_data.storage import ExternalDataStorage

from raglite.shared.logging import get_logger

# Module-level constants
logger = get_logger(__name__)
MAX_MISSING_RATIO = 0.30  # Maximum 30% missing data allowed
MAX_INTERPOLATION_GAP = 3  # Maximum periods to interpolate
POSITIVE_ONLY_METRICS = {"ebitda", "revenue", "capacity_utilization", "sales_volume"}

from raglite.shared.models import TimeSeriesPoint  # noqa: E402


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
