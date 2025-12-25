"""Regime change detection for time-series forecasting.

Story 6.8 AC6: Regime change detection using CUSUM, variance, and trend analysis.
Story 7.5: Extracted from hybrid.py for modularity.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from raglite.forecasting.models.base import MIN_DATA_POINTS
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class RegimeChangePoint:
    """Detected regime change in time-series data.

    Story 6.8 AC6: Regime change detection for improved forecasting.

    Attributes:
        date: Date when regime change was detected
        change_type: Type of change ('mean_shift', 'variance_shift', 'trend_break')
        significance: Statistical significance (0-1, higher = more significant)
        pre_regime_mean: Mean value before change point
        post_regime_mean: Mean value after change point
        pre_regime_std: Standard deviation before change point
        post_regime_std: Standard deviation after change point
        description: Human-readable description of the change
    """

    def __init__(
        self,
        date: pd.Timestamp,
        change_type: str,
        significance: float,
        pre_regime_mean: float,
        post_regime_mean: float,
        pre_regime_std: float,
        post_regime_std: float,
        description: str = "",
    ) -> None:
        self.date = date
        self.change_type = change_type
        self.significance = significance
        self.pre_regime_mean = pre_regime_mean
        self.post_regime_mean = post_regime_mean
        self.pre_regime_std = pre_regime_std
        self.post_regime_std = post_regime_std
        self.description = description

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "date": self.date.isoformat(),
            "change_type": self.change_type,
            "significance": self.significance,
            "pre_regime_mean": self.pre_regime_mean,
            "post_regime_mean": self.post_regime_mean,
            "pre_regime_std": self.pre_regime_std,
            "post_regime_std": self.post_regime_std,
            "description": self.description,
        }


class RegimeDetectionResult:
    """Result of regime change detection analysis.

    Attributes:
        change_points: List of detected regime change points
        current_regime: Index of current regime (0-based)
        total_regimes: Total number of regimes detected
        recommendation: Recommendation for forecast model adjustment
    """

    def __init__(
        self,
        change_points: list[RegimeChangePoint],
        current_regime: int,
        total_regimes: int,
        recommendation: str,
    ) -> None:
        self.change_points = change_points
        self.current_regime = current_regime
        self.total_regimes = total_regimes
        self.recommendation = recommendation

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "change_points": [cp.to_dict() for cp in self.change_points],
            "current_regime": self.current_regime,
            "total_regimes": self.total_regimes,
            "recommendation": self.recommendation,
        }


# Story 6.8 AC6: Regime detection constants
MIN_REGIME_DATA_POINTS = 12  # Minimum data points for regime detection
DEFAULT_CUSUM_THRESHOLD = 5.0  # CUSUM threshold (tuned for financial data, higher = fewer changes)
DEFAULT_WINDOW_SIZE = 6  # Rolling window for variance detection (months)


def _calculate_cusum(
    series: pd.Series,
    target_mean: float | None = None,
) -> tuple[pd.Series, pd.Series]:
    """Calculate CUSUM statistics for change point detection.

    CUSUM (Cumulative Sum) control chart detects shifts in the mean.
    Returns both upper and lower CUSUM series.

    Args:
        series: Time-series values
        target_mean: Target mean (default: series mean)

    Returns:
        Tuple of (upper_cusum, lower_cusum) Series
    """
    if target_mean is None:
        target_mean = series.mean()

    # Standardize using series std
    std = series.std()
    if std == 0:
        std = 1.0  # Avoid division by zero

    # Calculate standardized deviations
    z = (series - target_mean) / std

    # CUSUM: cumulative sum of deviations
    # Upper CUSUM detects upward shifts
    # Lower CUSUM detects downward shifts
    cusum_upper = z.cumsum()
    cusum_lower = -z.cumsum()

    return cusum_upper, cusum_lower


def _detect_mean_shifts(
    series: pd.Series,
    threshold: float = DEFAULT_CUSUM_THRESHOLD,
    min_segment_size: int = 6,
) -> list[tuple[pd.Timestamp, float, str]]:
    """Detect mean shifts using CUSUM algorithm.

    Story 6.8 AC6: Mean shift detection for regime changes.

    Args:
        series: Time-series with DatetimeIndex
        threshold: CUSUM threshold for detecting change (default: 4.0)
        min_segment_size: Minimum observations between change points

    Returns:
        List of (date, significance, direction) tuples for detected shifts
    """
    if len(series) < MIN_REGIME_DATA_POINTS:
        return []

    cusum_upper, cusum_lower = _calculate_cusum(series)
    change_points: list[tuple[pd.Timestamp, float, str]] = []

    # Find points where CUSUM exceeds threshold
    # Then reset CUSUM to detect additional changes
    remaining_series = series.copy()

    while len(remaining_series) >= min_segment_size * 2:
        cusum_upper, cusum_lower = _calculate_cusum(remaining_series)

        # Find maximum absolute CUSUM
        max_upper_idx = cusum_upper.abs().idxmax()
        max_lower_idx = cusum_lower.abs().idxmax()
        max_upper = abs(cusum_upper.loc[max_upper_idx])
        max_lower = abs(cusum_lower.loc[max_lower_idx])

        # Determine which CUSUM is larger
        if max_upper >= max_lower and max_upper > threshold:
            change_idx = max_upper_idx
            direction = "increase"
            significance = min(1.0, max_upper / (threshold * 2))
        elif max_lower > threshold:
            change_idx = max_lower_idx
            direction = "decrease"
            significance = min(1.0, max_lower / (threshold * 2))
        else:
            # No more significant changes
            break

        # Get position in remaining series
        pos = remaining_series.index.get_loc(change_idx)

        # Only accept if it divides series into reasonable segments
        if pos >= min_segment_size and len(remaining_series) - pos >= min_segment_size:
            change_points.append(
                (
                    pd.Timestamp(change_idx),
                    significance,
                    direction,
                )
            )

            # Reset: analyze only the portion after the change point
            remaining_series = remaining_series.iloc[pos:]
        else:
            break

    return change_points


def _detect_variance_shifts(
    series: pd.Series,
    window_size: int = DEFAULT_WINDOW_SIZE,
    variance_ratio_threshold: float = 3.0,  # Increased from 2.0 for less noise sensitivity
) -> list[tuple[pd.Timestamp, float]]:
    """Detect variance (volatility) shifts using rolling variance.

    Story 6.8 AC6: Variance shift detection for regime changes.

    Args:
        series: Time-series with DatetimeIndex
        window_size: Rolling window size (default: 6)
        variance_ratio_threshold: Threshold for variance change (default: 2.0)

    Returns:
        List of (date, variance_ratio) tuples for detected shifts
    """
    if len(series) < window_size * 3:
        return []

    # Calculate rolling variance
    rolling_var = series.rolling(window=window_size, min_periods=window_size // 2).var()

    # Detect significant variance changes
    change_points: list[tuple[pd.Timestamp, float]] = []

    for i in range(window_size, len(rolling_var) - window_size):
        pre_var = rolling_var.iloc[i - window_size : i].mean()
        post_var = rolling_var.iloc[i : i + window_size].mean()

        if pre_var > 0 and post_var > 0:
            ratio = max(post_var / pre_var, pre_var / post_var)
            if ratio >= variance_ratio_threshold:
                change_points.append((pd.Timestamp(series.index[i]), ratio))

    # Remove duplicates (keep highest ratio within window)
    if change_points:
        filtered: list[tuple[pd.Timestamp, float]] = []
        sorted_points = sorted(change_points, key=lambda x: x[1], reverse=True)
        used_dates: set[pd.Timestamp] = set()

        for date, ratio in sorted_points:
            # Check if too close to existing point
            too_close = False
            for used_date in used_dates:
                if abs((date - used_date).days) < window_size * 30:  # ~months
                    too_close = True
                    break

            if not too_close:
                filtered.append((date, ratio))
                used_dates.add(date)

        return filtered

    return []


def _detect_trend_breaks(
    series: pd.Series,
    window_size: int = DEFAULT_WINDOW_SIZE,
    slope_change_threshold: float = 1.5,  # Increased from 0.5 for less noise sensitivity
) -> list[tuple[pd.Timestamp, float, str]]:
    """Detect trend direction changes using rolling slope.

    Story 6.8 AC6: Trend break detection for regime changes.

    Args:
        series: Time-series with DatetimeIndex
        window_size: Rolling window size (default: 6)
        slope_change_threshold: Threshold for slope change ratio (default: 0.5)

    Returns:
        List of (date, significance, direction_change) tuples
    """
    if len(series) < window_size * 3:
        return []

    # Calculate rolling slope
    slopes: list[float] = []
    dates: list[pd.Timestamp] = []

    for i in range(window_size, len(series) + 1):
        window = series.iloc[i - window_size : i]
        x = np.arange(len(window))
        y = window.values.astype(float)

        # Linear regression for slope
        if len(x) > 1:
            slope, _ = np.polyfit(x, y, 1)
            slopes.append(slope)
            dates.append(pd.Timestamp(series.index[i - 1]))

    if len(slopes) < 3:
        return []

    # Normalize slopes
    slope_series = pd.Series(slopes, index=pd.DatetimeIndex(dates))
    slope_std = slope_series.std()
    if slope_std == 0:
        return []

    # Detect sign changes or large magnitude changes
    change_points: list[tuple[pd.Timestamp, float, str]] = []

    for i in range(1, len(slopes)):
        prev_slope = slopes[i - 1]
        curr_slope = slopes[i]

        # Sign change (trend reversal)
        if prev_slope * curr_slope < 0:
            significance = abs(curr_slope - prev_slope) / slope_std
            direction = "reversal_up" if curr_slope > prev_slope else "reversal_down"
            if significance > slope_change_threshold:
                change_points.append((dates[i], min(1.0, significance / 3), direction))

        # Large magnitude change (acceleration/deceleration)
        elif abs(curr_slope) > 0 and abs(prev_slope) > 0:
            ratio = abs(curr_slope / prev_slope)
            if ratio > 2 or ratio < 0.5:  # Doubling or halving of slope
                significance = abs(np.log(ratio)) / 2
                direction = "acceleration" if ratio > 1 else "deceleration"
                if significance > slope_change_threshold:
                    change_points.append((dates[i], min(1.0, significance), direction))

    return change_points


def detect_regime_changes(
    series: pd.Series,
    cusum_threshold: float = DEFAULT_CUSUM_THRESHOLD,
    window_size: int = DEFAULT_WINDOW_SIZE,
    include_variance: bool = True,
    include_trend: bool = True,
) -> RegimeDetectionResult:
    """Detect regime changes in time-series data.

    Story 6.8 AC6: Comprehensive regime change detection combining:
    - Mean shifts (CUSUM algorithm)
    - Variance shifts (rolling variance ratio)
    - Trend breaks (slope changes)

    This helps improve forecast accuracy by:
    1. Identifying structural breaks in historical data
    2. Recommending model adjustments (e.g., use only post-change data)
    3. Flagging recent changes that may affect forecast reliability

    Args:
        series: Time-series with DatetimeIndex
        cusum_threshold: Threshold for CUSUM mean shift detection (default: 4.0)
        window_size: Rolling window size for variance/trend (default: 6)
        include_variance: Include variance shift detection (default: True)
        include_trend: Include trend break detection (default: True)

    Returns:
        RegimeDetectionResult with detected change points and recommendations

    Example:
        >>> dates = pd.date_range('2020-01', periods=36, freq='MS')
        >>> values = [100]*12 + [150]*12 + [180]*12  # Two regime changes
        >>> series = pd.Series(values, index=dates)
        >>> result = detect_regime_changes(series)
        >>> print(result.total_regimes)  # 3
    """
    if len(series) < MIN_REGIME_DATA_POINTS:
        logger.warning(
            "Insufficient data for regime detection",
            extra={"data_points": len(series), "minimum": MIN_REGIME_DATA_POINTS},
        )
        return RegimeDetectionResult(
            change_points=[],
            current_regime=0,
            total_regimes=1,
            recommendation="Insufficient data for regime detection. Using full series.",
        )

    # Ensure DatetimeIndex
    if not isinstance(series.index, pd.DatetimeIndex):
        series = series.copy()
        series.index = pd.DatetimeIndex(series.index)

    all_changes: list[RegimeChangePoint] = []

    # 1. Detect mean shifts (CUSUM)
    mean_shifts = _detect_mean_shifts(series, threshold=cusum_threshold)
    for date, significance, direction in mean_shifts:
        # Calculate pre/post statistics
        mask_pre = series.index < date
        mask_post = series.index >= date
        pre_mean = float(series[mask_pre].mean()) if mask_pre.any() else 0.0
        post_mean = float(series[mask_post].mean()) if mask_post.any() else 0.0
        pre_std = float(series[mask_pre].std()) if mask_pre.any() else 0.0
        post_std = float(series[mask_post].std()) if mask_post.any() else 0.0

        pct_change = ((post_mean - pre_mean) / pre_mean * 100) if pre_mean != 0 else 0
        description = f"Mean {direction}: {pre_mean:.1f} → {post_mean:.1f} ({pct_change:+.1f}%)"

        all_changes.append(
            RegimeChangePoint(
                date=date,
                change_type="mean_shift",
                significance=significance,
                pre_regime_mean=pre_mean,
                post_regime_mean=post_mean,
                pre_regime_std=pre_std,
                post_regime_std=post_std,
                description=description,
            )
        )

    # 2. Detect variance shifts
    if include_variance:
        variance_shifts = _detect_variance_shifts(series, window_size=window_size)
        for date, ratio in variance_shifts:
            mask_pre = series.index < date
            mask_post = series.index >= date
            pre_mean = float(series[mask_pre].mean()) if mask_pre.any() else 0.0
            post_mean = float(series[mask_post].mean()) if mask_post.any() else 0.0
            pre_std = float(series[mask_pre].std()) if mask_pre.any() else 0.0
            post_std = float(series[mask_post].std()) if mask_post.any() else 0.0

            significance = min(1.0, (ratio - 1) / 3)
            description = f"Volatility change: {pre_std:.1f} → {post_std:.1f} (ratio: {ratio:.1f}x)"

            all_changes.append(
                RegimeChangePoint(
                    date=date,
                    change_type="variance_shift",
                    significance=significance,
                    pre_regime_mean=pre_mean,
                    post_regime_mean=post_mean,
                    pre_regime_std=pre_std,
                    post_regime_std=post_std,
                    description=description,
                )
            )

    # 3. Detect trend breaks
    if include_trend:
        trend_breaks = _detect_trend_breaks(series, window_size=window_size)
        for date, significance, direction in trend_breaks:
            mask_pre = series.index < date
            mask_post = series.index >= date
            pre_mean = float(series[mask_pre].mean()) if mask_pre.any() else 0.0
            post_mean = float(series[mask_post].mean()) if mask_post.any() else 0.0
            pre_std = float(series[mask_pre].std()) if mask_pre.any() else 0.0
            post_std = float(series[mask_post].std()) if mask_post.any() else 0.0

            description = f"Trend break ({direction})"

            all_changes.append(
                RegimeChangePoint(
                    date=date,
                    change_type="trend_break",
                    significance=significance,
                    pre_regime_mean=pre_mean,
                    post_regime_mean=post_mean,
                    pre_regime_std=pre_std,
                    post_regime_std=post_std,
                    description=description,
                )
            )

    # Sort by date and deduplicate (keep highest significance within 2-month window)
    if all_changes:
        all_changes.sort(key=lambda x: x.date)

        # Deduplicate nearby changes
        deduped: list[RegimeChangePoint] = []
        for cp in all_changes:
            # Check if too close to existing
            is_duplicate = False
            for existing in deduped:
                days_apart = abs((cp.date - existing.date).days)
                if days_apart < 60:  # Within 2 months
                    # Keep higher significance
                    if cp.significance > existing.significance:
                        deduped.remove(existing)
                        deduped.append(cp)
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduped.append(cp)

        all_changes = deduped

    # Determine current regime and generate recommendation
    total_regimes = len(all_changes) + 1
    current_regime = total_regimes - 1  # Last regime (0-indexed)

    # Generate recommendation
    if not all_changes:
        recommendation = (
            "No regime changes detected. Full historical data suitable for forecasting."
        )
    elif len(all_changes) == 1:
        last_change = all_changes[-1]
        days_since = (series.index[-1] - last_change.date).days
        months_since = days_since / 30

        if months_since < 6:
            recommendation = (
                f"Recent regime change detected ({last_change.description}). "
                f"Consider using only post-change data ({months_since:.0f} months) "
                "or adjusting model for structural break."
            )
        else:
            recommendation = (
                f"Regime change detected {months_since:.0f} months ago. "
                "Post-change data should be sufficient for reliable forecasting."
            )
    else:
        last_change = all_changes[-1]
        days_since = (series.index[-1] - last_change.date).days
        months_since = days_since / 30

        recommendation = (
            f"Multiple regime changes detected ({len(all_changes)}). "
            f"Most recent: {last_change.description} ({months_since:.0f} months ago). "
            "Consider using regime-aware forecasting or focusing on post-change period."
        )

    logger.info(
        "Regime change detection completed",
        extra={
            "total_changes": len(all_changes),
            "total_regimes": total_regimes,
            "data_points": len(series),
        },
    )

    return RegimeDetectionResult(
        change_points=all_changes,
        current_regime=current_regime,
        total_regimes=total_regimes,
        recommendation=recommendation,
    )


def get_post_regime_data(
    series: pd.Series,
    detection_result: RegimeDetectionResult,
    min_points: int = MIN_DATA_POINTS,
) -> pd.Series:
    """Get data from the current (most recent) regime only.

    Story 6.8 AC6: Extract post-regime-change data for improved forecasting.

    If using only post-change data would result in fewer than min_points,
    returns the full series with a warning.

    Args:
        series: Full time-series data
        detection_result: Result from detect_regime_changes()
        min_points: Minimum data points required (default: 6)

    Returns:
        Series containing only data from current regime
    """
    if not detection_result.change_points:
        return series

    last_change = detection_result.change_points[-1]
    post_regime = series[series.index >= last_change.date]

    if len(post_regime) < min_points:
        logger.warning(
            "Post-regime data insufficient, using full series",
            extra={
                "post_regime_points": len(post_regime),
                "min_required": min_points,
                "change_date": str(last_change.date),
            },
        )
        return series

    logger.info(
        "Using post-regime data for forecasting",
        extra={
            "original_points": len(series),
            "post_regime_points": len(post_regime),
            "change_date": str(last_change.date),
        },
    )

    return post_regime
