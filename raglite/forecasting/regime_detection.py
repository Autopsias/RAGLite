"""Regime change detection for time-series forecasting.

Story 6.8 AC6: Regime change detection using CUSUM, variance, and trend analysis.
Story 7.5: Extracted from hybrid.py for modularity.

This module provides the main API and re-exports from specialized submodules.
"""

from __future__ import annotations

import pandas as pd

from raglite.forecasting.models.base import MIN_DATA_POINTS

# Import detection algorithms
from raglite.forecasting.regime_detection_cusum import detect_mean_shifts

# Re-export data models and constants
from raglite.forecasting.regime_detection_models import (
    DEFAULT_CUSUM_THRESHOLD,
    DEFAULT_WINDOW_SIZE,
    MIN_REGIME_DATA_POINTS,
    RegimeChangePoint,
    RegimeDetectionResult,
)
from raglite.forecasting.regime_detection_trend import detect_trend_breaks
from raglite.forecasting.regime_detection_variance import detect_variance_shifts
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Export public API
__all__ = [
    "RegimeChangePoint",
    "RegimeDetectionResult",
    "MIN_REGIME_DATA_POINTS",
    "DEFAULT_CUSUM_THRESHOLD",
    "DEFAULT_WINDOW_SIZE",
    "detect_regime_changes",
    "get_post_regime_data",
]


def _calculate_pre_post_stats(
    series: pd.Series, date: pd.Timestamp
) -> tuple[float, float, float, float]:
    """Calculate pre/post regime statistics for a change point."""
    mask_pre = series.index < date
    mask_post = series.index >= date
    pre_mean = float(series[mask_pre].mean()) if mask_pre.any() else 0.0
    post_mean = float(series[mask_post].mean()) if mask_post.any() else 0.0
    pre_std = float(series[mask_pre].std()) if mask_pre.any() else 0.0
    post_std = float(series[mask_post].std()) if mask_post.any() else 0.0
    return pre_mean, post_mean, pre_std, post_std


def _deduplicate_changes(changes: list[RegimeChangePoint]) -> list[RegimeChangePoint]:
    """Deduplicate nearby changes, keeping highest significance within 2-month window."""
    if not changes:
        return changes

    changes.sort(key=lambda x: x.date)
    deduped: list[RegimeChangePoint] = []

    for cp in changes:
        is_duplicate = False
        for existing in deduped:
            days_apart = abs((cp.date - existing.date).days)
            if days_apart < 60:  # Within 2 months
                if cp.significance > existing.significance:
                    deduped.remove(existing)
                    deduped.append(cp)
                is_duplicate = True
                break

        if not is_duplicate:
            deduped.append(cp)

    return deduped


def _generate_recommendation(changes: list[RegimeChangePoint], series: pd.Series) -> str:
    """Generate recommendation based on detected regime changes."""
    if not changes:
        return "No regime changes detected. Full historical data suitable for forecasting."

    last_change = changes[-1]
    days_since = (series.index[-1] - last_change.date).days
    months_since = days_since / 30

    if len(changes) == 1:
        if months_since < 6:
            return (
                f"Recent regime change detected ({last_change.description}). "
                f"Consider using only post-change data ({months_since:.0f} months) "
                "or adjusting model for structural break."
            )
        return (
            f"Regime change detected {months_since:.0f} months ago. "
            "Post-change data should be sufficient for reliable forecasting."
        )

    return (
        f"Multiple regime changes detected ({len(changes)}). "
        f"Most recent: {last_change.description} ({months_since:.0f} months ago). "
        "Consider using regime-aware forecasting or focusing on post-change period."
    )


def _detect_mean_shifts(series: pd.Series, threshold: float) -> list[RegimeChangePoint]:
    """Detect mean shifts and create change points."""
    changes = []
    for date, significance, direction in detect_mean_shifts(series, threshold=threshold):
        pre_mean, post_mean, pre_std, post_std = _calculate_pre_post_stats(series, date)
        pct_change = ((post_mean - pre_mean) / pre_mean * 100) if pre_mean != 0 else 0
        changes.append(
            RegimeChangePoint(
                date=date,
                change_type="mean_shift",
                significance=significance,
                pre_regime_mean=pre_mean,
                post_regime_mean=post_mean,
                pre_regime_std=pre_std,
                post_regime_std=post_std,
                description=f"Mean {direction}: {pre_mean:.1f} → {post_mean:.1f} ({pct_change:+.1f}%)",
            )
        )
    return changes


def _detect_variance_changes(series: pd.Series, window_size: int) -> list[RegimeChangePoint]:
    """Detect variance shifts and create change points."""
    changes = []
    for date, ratio in detect_variance_shifts(series, window_size=window_size):
        pre_mean, post_mean, pre_std, post_std = _calculate_pre_post_stats(series, date)
        changes.append(
            RegimeChangePoint(
                date=date,
                change_type="variance_shift",
                significance=min(1.0, (ratio - 1) / 3),
                pre_regime_mean=pre_mean,
                post_regime_mean=post_mean,
                pre_regime_std=pre_std,
                post_regime_std=post_std,
                description=f"Volatility change: {pre_std:.1f} → {post_std:.1f} (ratio: {ratio:.1f}x)",
            )
        )
    return changes


def _detect_trend_changes(series: pd.Series, window_size: int) -> list[RegimeChangePoint]:
    """Detect trend breaks and create change points."""
    changes = []
    for date, significance, direction in detect_trend_breaks(series, window_size=window_size):
        pre_mean, post_mean, pre_std, post_std = _calculate_pre_post_stats(series, date)
        changes.append(
            RegimeChangePoint(
                date=date,
                change_type="trend_break",
                significance=significance,
                pre_regime_mean=pre_mean,
                post_regime_mean=post_mean,
                pre_regime_std=pre_std,
                post_regime_std=post_std,
                description=f"Trend break ({direction})",
            )
        )
    return changes


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

    Args:
        series: Time-series with DatetimeIndex
        cusum_threshold: Threshold for CUSUM mean shift detection (default: 4.0)
        window_size: Rolling window size for variance/trend (default: 6)
        include_variance: Include variance shift detection (default: True)
        include_trend: Include trend break detection (default: True)

    Returns:
        RegimeDetectionResult with detected change points and recommendations
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

    # Detect all change types using helper functions
    all_changes = _detect_mean_shifts(series, cusum_threshold)
    if include_variance:
        all_changes.extend(_detect_variance_changes(series, window_size))
    if include_trend:
        all_changes.extend(_detect_trend_changes(series, window_size))

    # Deduplicate and finalize
    all_changes = _deduplicate_changes(all_changes)
    total_regimes = len(all_changes) + 1
    recommendation = _generate_recommendation(all_changes, series)

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
        current_regime=total_regimes - 1,
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
