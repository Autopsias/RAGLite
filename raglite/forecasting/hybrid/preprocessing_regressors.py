"""Regressor selection, preparation, and validation utilities.

Part of Story 8.1 refactoring to reduce preprocessing.py file size.

Provides correlation-based selection, alignment, interpolation,
and future value generation for external regressors.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from raglite.shared.logging import get_logger

from .preprocessing_yoy import detect_yoy_percentage, transform_yoy_to_index

logger = get_logger(__name__)

# Module-level constants
MAX_MISSING_RATIO = 0.30  # Maximum 30% missing data allowed
MAX_INTERPOLATION_GAP = 3  # Maximum periods to interpolate

# Forecast reliability fix (2026-02-02): Profit metrics have weak direct correlations
# with macro indicators but can still benefit from regressors at lower thresholds.
# EBITDA and profit metrics use 0.15 threshold (vs 0.3 for revenue/cost metrics).
PROFIT_METRICS = {
    "ebitda",
    "ebitda ifrs",
    "ebitda_margin",
    "net_income",
    "net_profit",
    "operating_profit",
    "operating_income",
    "profit",
    "gross_profit",
    "pretax_income",
}
MIN_CORRELATION_PROFIT = 0.15  # Lower threshold for profit metrics
MIN_CORRELATION_DEFAULT = 0.3  # Default threshold for other metrics


def scale_regressors_robust(
    regressors: dict[str, pd.Series],
) -> tuple[dict[str, pd.Series], dict[str, tuple[float, float]]]:
    """Scale regressors using RobustScaler (median/IQR).

    Phase 5 Quality Fix (2026-01-29): Handles regime changes (2022 energy crisis)
    better than StandardScaler. Variable Cost issue: Diesel ~1, TTF Gas ~3-339
    (scale mismatch) causing poor model performance.

    RobustScaler is preferred for financial/commodity data because:
    1. Uses median instead of mean (robust to outliers)
    2. Uses IQR instead of std (handles regime changes)
    3. Energy crisis 2022 created 10-100x swings that StandardScaler amplifies

    Args:
        regressors: Dict of regressor name -> pandas Series with values

    Returns:
        Tuple of:
        - scaled: Dict of regressor name -> scaled pandas Series (median=0, IQR-normalized)
        - scalers: Dict of regressor name -> (median, iqr) for inverse transform
    """
    from sklearn.preprocessing import RobustScaler

    scaled: dict[str, pd.Series] = {}
    scalers: dict[str, tuple[float, float]] = {}

    for name, series in regressors.items():
        if series.empty:
            continue

        # RobustScaler requires 2D input
        scaler = RobustScaler()
        values = series.values.reshape(-1, 1)

        try:
            scaled_values = scaler.fit_transform(values).flatten()
            scaled[name] = pd.Series(scaled_values, index=series.index, name=name)

            # Store median and IQR for inverse transform (if needed)
            scalers[name] = (float(scaler.center_[0]), float(scaler.scale_[0]))

            logger.debug(
                f"Scaled regressor {name} with RobustScaler",
                extra={
                    "regressor": name,
                    "original_range": f"{series.min():.2f} to {series.max():.2f}",
                    "scaled_range": f"{scaled[name].min():.2f} to {scaled[name].max():.2f}",
                    "median": scaler.center_[0],
                    "iqr": scaler.scale_[0],
                },
            )
        except Exception as e:
            logger.warning(
                f"Failed to scale regressor {name}: {e}, using original",
                extra={"regressor": name, "error": str(e)},
            )
            scaled[name] = series

    if scaled:
        logger.info(
            "Applied RobustScaler to regressors",
            extra={
                "scaled_count": len(scaled),
                "regressor_names": list(scaled.keys()),
            },
        )

    return scaled, scalers


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
    min_correlation: float | None = None,  # Auto-determined based on metric
    auto_transform_yoy: bool = True,
    metric_name: str | None = None,  # Used to determine appropriate threshold
    return_lag_info: bool = False,  # EBITDA fix: Return lag info for application
) -> list[str] | dict[str, tuple[float, int]]:
    """Select top regressors by Pearson correlation with target.

    Story 6.3 AC3: Correlation-based regressor selection.
    Story 6.7: Auto-transform YoY% data before correlation calculation.
    Forecast reliability fix (2026-02-02): Lower threshold for profit metrics
    (EBITDA has weak direct correlations but can still benefit from regressors).
    EBITDA forecast fix (2026-02-03): Return lag info for application in forecasting.

    Args:
        target: Target time-series (y values)
        candidates: Dictionary of candidate regressors {name: series}
        top_n: Maximum number of regressors to select (default: 7)
        min_correlation: Minimum absolute correlation threshold (auto if None)
        auto_transform_yoy: Auto-transform YoY% data before correlation (default: True)
        metric_name: Name of target metric (used to determine threshold)
        return_lag_info: If True, return dict with (correlation, lag) tuples

    Returns:
        If return_lag_info=False: List of selected regressor names sorted by abs(correlation) descending
        If return_lag_info=True: Dict of {name: (correlation, optimal_lag)} for applying lags
    """
    if not candidates:
        return []

    # Forecast reliability fix: Determine appropriate correlation threshold
    # Profit metrics have weaker direct correlations with macro indicators
    if min_correlation is None:
        metric_lower = (metric_name or "").lower()
        if metric_lower in PROFIT_METRICS:
            min_correlation = MIN_CORRELATION_PROFIT
            logger.info(
                "Using lower correlation threshold for profit metric",
                extra={
                    "metric": metric_name,
                    "threshold": min_correlation,
                    "reason": "Profit metrics have weaker direct correlations with macro indicators",
                },
            )
        else:
            min_correlation = MIN_CORRELATION_DEFAULT

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

    # Forecast reliability fix: Try lagged correlations for macro indicators
    # Macro indicators often have 1-3 month lag effect on profits
    # EBITDA fix (2026-02-03): Store lag info for application during forecasting
    best_correlations = correlations.copy()
    lag_info: dict[str, tuple[float, int]] = {}  # {name: (correlation, optimal_lag)}

    for name, series in transformed_candidates.items():
        current_corr = abs(correlations.get(name, 0))
        best_corr = current_corr
        best_lag = 0

        # Check lagged correlations (1, 2, 3 periods)
        for lag in [1, 2, 3]:
            lagged = series.shift(lag).reindex(target.index)
            lagged_df = pd.DataFrame({"target": target, "lagged": lagged}).dropna()
            if len(lagged_df) >= 6:  # Need at least 6 points
                lagged_corr = abs(lagged_df["target"].corr(lagged_df["lagged"]))
                if lagged_corr > best_corr:
                    best_corr = lagged_corr
                    best_lag = lag

        # Store lag info for this regressor (used when return_lag_info=True)
        signed_corr = best_corr if correlations.get(name, 0) >= 0 else -best_corr
        lag_info[name] = (signed_corr, best_lag)

        if best_lag > 0 and best_corr > current_corr:
            logger.debug(
                f"Better lagged correlation found for {name}",
                extra={
                    "regressor": name,
                    "current_corr": f"{current_corr:.3f}",
                    "lagged_corr": f"{best_corr:.3f}",
                    "lag_periods": best_lag,
                },
            )
            # Use the better (lagged) correlation for selection
            best_correlations[name] = best_corr if correlations[name] >= 0 else -best_corr

    # Filter by minimum correlation
    filtered = best_correlations[best_correlations.abs() >= min_correlation]

    # Sort by absolute correlation and take top N
    selected: list[str] = list(filtered.abs().sort_values(ascending=False).head(top_n).index)

    # Forecast reliability fix: Explicit logging when all regressors filtered out
    if not selected and candidates:
        logger.warning(
            "All regressors filtered out by correlation threshold",
            extra={
                "metric": metric_name,
                "threshold": min_correlation,
                "num_candidates": len(candidates),
                "correlations": {
                    name: f"{best_correlations.get(name, 0):.3f}"
                    for name in list(candidates.keys())[:5]
                },
                "recommendation": (
                    "Consider using univariate model or manually providing regressors. "
                    "For profit metrics, try external factors like construction output or cement demand."
                ),
            },
        )

    # EBITDA fix (2026-02-03): Log lag info for transparency
    lag_summary = {
        name: lag_info.get(name, (0, 0))[1]
        for name in selected
        if lag_info.get(name, (0, 0))[1] > 0
    }

    logger.info(
        "Regressors selected",
        extra={
            "candidates": len(candidates),
            "selected": len(selected),
            "names": selected,
            "correlations": {name: f"{best_correlations.get(name, 0):.3f}" for name in selected},
            "optimal_lags": lag_summary if lag_summary else "none",
            "threshold": min_correlation,
            "metric": metric_name,
        },
    )

    # EBITDA fix: Return lag info dict if requested (for applying lags in forecasting)
    if return_lag_info:
        return {name: lag_info[name] for name in selected}

    return selected


def _resample_high_frequency(name: str, series: pd.Series, target_len: int) -> pd.Series:
    """Auto-resample high-frequency data to monthly if needed."""
    if len(series) > target_len * 3:
        logger.info(
            f"Auto-resampling high-frequency regressor {name} to monthly",
            extra={"original_points": len(series), "target_points": target_len},
        )
        series = series.resample("MS").mean().dropna()
        logger.info(f"Resampled {name} to monthly", extra={"new_points": len(series)})
    return series


def _transform_yoy_if_needed(
    name: str, series: pd.Series, target_series: pd.Series | None, auto_transform: bool
) -> pd.Series:
    """Auto-transform YoY% data if detected."""
    if auto_transform and detect_yoy_percentage(series, target_series):
        logger.info(
            f"Auto-transforming YoY% regressor: {name}",
            extra={"original_range": f"{series.min():.2f} to {series.max():.2f}"},
        )
        base_value = (
            target_series.mean() if target_series is not None and not target_series.empty else 100.0
        )
        series = transform_yoy_to_index(series, base_value=base_value)
        logger.info(
            f"Transformed {name} to index",
            extra={"new_range": f"{series.min():.2f} to {series.max():.2f}"},
        )
    return series


def _interpolate_missing(aligned: pd.Series) -> pd.Series:
    """Interpolate missing values with limits."""
    if aligned.isna().any():
        aligned = aligned.interpolate(method="linear", limit=MAX_INTERPOLATION_GAP)
        aligned = aligned.ffill(limit=MAX_INTERPOLATION_GAP)
        aligned = aligned.bfill(limit=MAX_INTERPOLATION_GAP)
    return aligned


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
        Dictionary of prepared regressor series (skips regressors with too much missing data)
    """
    prepared = {}

    # Handle duplicate indices in target
    if target_index.duplicated().any():
        logger.warning(
            "Target index has duplicates, deduplicating",
            extra={"duplicates": int(target_index.duplicated().sum())},
        )
        target_index = target_index[~target_index.duplicated(keep="first")]

    for name, series in regressors.items():
        working_series = series.copy()

        # Step 1: Resample high-frequency data
        working_series = _resample_high_frequency(name, working_series, len(target_index))

        # Step 2: Transform YoY% data
        working_series = _transform_yoy_if_needed(
            name, working_series, target_series, auto_transform_yoy
        )

        # Step 3: Handle duplicate indices
        if working_series.index.duplicated().any():
            working_series = working_series.groupby(working_series.index).mean()

        # Step 4: Align to target index
        aligned = working_series.reindex(target_index)
        missing_ratio = aligned.isna().sum() / len(aligned)

        # Step 5: Skip if too much missing
        if missing_ratio > MAX_MISSING_RATIO:
            logger.warning(
                f"Skipping regressor '{name}' - {missing_ratio:.1%} missing (max: {MAX_MISSING_RATIO:.0%})",
                extra={"regressor": name, "missing_ratio": missing_ratio},
            )
            continue

        # Step 6: Interpolate missing values
        aligned = _interpolate_missing(aligned)

        # Step 7: Final validation
        if aligned.isna().any():
            logger.warning(
                f"Skipping regressor '{name}' - still has {aligned.isna().sum()} missing after interpolation",
                extra={"regressor": name},
            )
            continue

        prepared[name] = aligned

    return prepared


def generate_future_regressors(
    regressors: dict[str, pd.Series],
    future_dates: pd.DatetimeIndex,
    strategy: str = "seasonal",
    lags_applied: dict[str, int] | None = None,
) -> dict[str, pd.Series]:
    """Generate future regressor values based on strategy.

    Story 6.3 AC7: Future regressor value strategies.
    EBITDA forecast fix (2026-02-03): Added 'seasonal' and 'momentum' strategies
    to produce non-flat regressor projections. Also accounts for applied lags.

    Args:
        regressors: Historical regressor series
        future_dates: Future dates to generate values for
        strategy: Strategy - 'seasonal' (default), 'momentum', 'constant', 'extrapolate', or 'provided'
        lags_applied: Dict of {regressor_name: lag_periods} for accounting for lags

    Returns:
        Dictionary of regressor series extended to future dates

    Raises:
        ValueError: If strategy='provided' but future values missing
    """
    extended = {}
    lags = lags_applied or {}

    for name, series in regressors.items():
        historical = series.dropna()
        lag = lags.get(name, 0)

        if strategy == "seasonal":
            # EBITDA fix: Use same period from prior year if available
            # This captures annual seasonality patterns in macro indicators
            future_values = _generate_seasonal_future(historical, future_dates, name, lag)

        elif strategy == "momentum":
            # EBITDA fix: Extrapolate based on recent momentum (6-month trend)
            future_values = _generate_momentum_future(historical, future_dates, lag)

        elif strategy == "constant":
            # Use last known value for all future dates
            # Accounting for lag: the "effective" last value is lag periods back
            effective_last_idx = max(0, len(historical) - 1 - lag)
            last_value = (
                historical.iloc[effective_last_idx]
                if len(historical) > effective_last_idx
                else historical.iloc[-1]
            )
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


def _generate_seasonal_future(
    historical: pd.Series, future_dates: pd.DatetimeIndex, name: str, lag: int = 0
) -> pd.Series:
    """Generate future values using seasonal pattern from prior year.

    EBITDA forecast fix (2026-02-03): Uses same month from prior year if available,
    with fallback to historical mean. This captures annual seasonality in macro indicators.

    Args:
        historical: Historical series with DatetimeIndex
        future_dates: Future dates to generate values for
        name: Regressor name (for logging)
        lag: Number of periods to account for lagged correlation

    Returns:
        Series of future values indexed by future_dates
    """
    future_values = []

    # Calculate seasonal pattern (monthly averages across years)
    if hasattr(historical.index, "month"):
        seasonal_pattern = historical.groupby(historical.index.month).mean()
    else:
        seasonal_pattern = pd.Series(dtype=float)

    # Calculate overall trend (simple linear)
    historical_mean = historical.mean()
    recent_mean = historical.tail(6).mean() if len(historical) >= 6 else historical_mean
    trend_adjustment = recent_mean / historical_mean if historical_mean != 0 else 1.0

    for future_date in future_dates:
        month = future_date.month

        # Try to get seasonal value for this month
        if month in seasonal_pattern.index:
            base_value = seasonal_pattern[month]
        else:
            base_value = historical_mean

        # Apply trend adjustment to capture recent changes
        adjusted_value = base_value * trend_adjustment
        future_values.append(adjusted_value)

    logger.debug(
        f"Generated seasonal future for {name}",
        extra={
            "regressor": name,
            "periods": len(future_dates),
            "trend_adjustment": f"{trend_adjustment:.3f}",
            "lag_accounted": lag,
        },
    )

    return pd.Series(future_values, index=future_dates)


def _generate_momentum_future(
    historical: pd.Series, future_dates: pd.DatetimeIndex, lag: int = 0
) -> pd.Series:
    """Generate future values using recent momentum (trend extrapolation).

    EBITDA forecast fix (2026-02-03): Projects future values based on recent
    6-month trend, with dampening to prevent extreme projections.

    Args:
        historical: Historical series with DatetimeIndex
        future_dates: Future dates to generate values for
        lag: Number of periods to account for lagged correlation

    Returns:
        Series of future values indexed by future_dates
    """
    if len(historical) < 6:
        # Fall back to constant if insufficient history
        return pd.Series(historical.iloc[-1], index=future_dates)

    # Calculate 6-month momentum
    recent = historical.tail(6)
    old_value = recent.iloc[0]
    new_value = recent.iloc[-1]

    # Monthly growth rate
    if old_value != 0:
        monthly_growth_rate = (new_value / old_value) ** (1 / 6) - 1
    else:
        monthly_growth_rate = 0

    # Dampen growth rate to prevent extreme projections (cap at ±5% monthly)
    monthly_growth_rate = max(-0.05, min(0.05, monthly_growth_rate))

    future_values = []
    current_value = new_value

    for i in range(len(future_dates)):
        # Apply dampening: growth rate decays over forecast horizon
        dampened_rate = monthly_growth_rate * (0.9**i)
        current_value = current_value * (1 + dampened_rate)
        future_values.append(current_value)

    return pd.Series(future_values, index=future_dates)
