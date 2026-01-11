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
