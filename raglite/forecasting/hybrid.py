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
    from catboost import CatBoostRegressor
    from chronos import BaseChronosPipeline
    from lightgbm import LGBMRegressor
    from prophet import Prophet
    from pytorch_forecasting import TemporalFusionTransformer
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


# Story 6.13: Lazy-load Chronos-2 pipeline to avoid import-time penalty
# Chronos-2 model loading takes 10-30s on first use, cache singleton
_chronos_pipeline: BaseChronosPipeline | None = None


def _get_chronos_pipeline() -> BaseChronosPipeline:
    """Lazy-load Chronos-2 pipeline on first use.

    Story 6.13 AC1, AC5: Singleton pattern for model caching.
    Uses amazon/chronos-bolt-small (250x faster than original Chronos).

    Returns:
        Chronos-2 pipeline instance (cached after first load)

    Raises:
        ImportError: If chronos-forecasting package not installed
    """
    global _chronos_pipeline
    if _chronos_pipeline is None:
        try:
            from chronos import BaseChronosPipeline

            logger.info("Loading Chronos-2 model (first use, 10-30s)...")
            _chronos_pipeline = BaseChronosPipeline.from_pretrained(
                "amazon/chronos-bolt-small",
                device_map="cpu",  # GPU optional via future config
            )
            logger.info("Chronos-2 model loaded successfully")
        except ImportError as e:
            raise ImportError(
                "Chronos-2 requires 'chronos-forecasting' package. "
                "Install with: uv sync --all-groups"
            ) from e
    return cast("BaseChronosPipeline", _chronos_pipeline)


# Story 6.14: Lazy-load TFT model from checkpoint on first use
# TFT model loading takes <30s on first use, cache singleton
_tft_model: TemporalFusionTransformer | None = None
_tft_checkpoint_path: str | None = None


def _get_tft_model() -> TemporalFusionTransformer | None:
    """Lazy-load TFT model from checkpoint on first use.

    Story 6.14 AC1, AC7: Singleton pattern for model caching.
    Returns None if no trained checkpoint available (graceful degradation).

    Returns:
        TFT model instance (cached after first load), or None if unavailable

    Raises:
        ImportError: If pytorch-forecasting package not installed
    """
    global _tft_model, _tft_checkpoint_path
    if _tft_model is None:
        try:
            # Check model_registry for active checkpoint
            from raglite.external_data.storage import ExternalDataStorage
            from raglite.shared.database import get_session

            session = get_session()
            storage = ExternalDataStorage(session)
            checkpoint_entry = storage.get_active_model("tft")

            if checkpoint_entry is None:
                logger.warning("No TFT checkpoint available - skipping TFT in ensemble")
                return None

            # Try to load active checkpoint
            import torch
            from pytorch_forecasting import TemporalFusionTransformer

            try:
                logger.info(f"Loading TFT model from {checkpoint_entry.checkpoint_path}...")
                # Security: Validate checkpoint path before loading
                if not checkpoint_entry.checkpoint_path or not isinstance(
                    checkpoint_entry.checkpoint_path, str
                ):
                    raise ValueError("Invalid checkpoint path")
                if not checkpoint_entry.checkpoint_path.endswith(".ckpt"):
                    raise ValueError("Checkpoint must be .ckpt file")

                # Load checkpoint with weights_only=False for custom PyTorch Forecasting format
                checkpoint = torch.load(  # nosec B614 - Required for PyTorch Forecasting custom checkpoint format
                    checkpoint_entry.checkpoint_path,
                    map_location="cpu",
                    weights_only=False,
                )
                # Create model from hparams and load state dict
                _tft_model = TemporalFusionTransformer(**checkpoint["hparams"])
                _tft_model.load_state_dict(checkpoint["state_dict"])
                _tft_checkpoint_path = checkpoint_entry.checkpoint_path
                logger.info("TFT model loaded successfully")
            except Exception as load_error:
                # AC5: Fallback to previous checkpoint if current fails
                logger.warning(
                    f"Failed to load active checkpoint: {load_error}. Trying previous checkpoints..."
                )

                # Get checkpoint history (excluding the failed active one)
                history = storage.get_model_history("tft", limit=5)
                for prev_checkpoint in history:
                    if prev_checkpoint.checkpoint_path == checkpoint_entry.checkpoint_path:
                        continue  # Skip the one that just failed

                    try:
                        logger.info(
                            f"Attempting fallback checkpoint: {prev_checkpoint.checkpoint_path}"
                        )
                        # Security: Validate checkpoint path before loading
                        if not prev_checkpoint.checkpoint_path or not isinstance(
                            prev_checkpoint.checkpoint_path, str
                        ):
                            raise ValueError("Invalid checkpoint path")
                        if not prev_checkpoint.checkpoint_path.endswith(".ckpt"):
                            raise ValueError("Checkpoint must be .ckpt file")

                        # Load checkpoint with weights_only=False for custom PyTorch Forecasting format
                        checkpoint = torch.load(  # nosec B614 - Required for PyTorch Forecasting custom checkpoint format
                            prev_checkpoint.checkpoint_path,
                            map_location="cpu",
                            weights_only=False,
                        )
                        _tft_model = TemporalFusionTransformer(**checkpoint["hparams"])
                        _tft_model.load_state_dict(checkpoint["state_dict"])
                        _tft_checkpoint_path = prev_checkpoint.checkpoint_path
                        logger.info(
                            f"Successfully loaded fallback checkpoint (version: {prev_checkpoint.model_version})"
                        )
                        break
                    except Exception as fallback_error:
                        logger.warning(
                            f"Fallback checkpoint {prev_checkpoint.checkpoint_path} also failed: {fallback_error}"
                        )
                        continue

                if _tft_model is None:
                    logger.error("All TFT checkpoints failed to load")
                    return None

        except ImportError as e:
            raise ImportError(
                "TFT requires 'pytorch-forecasting' package. Install with: uv sync --all-groups"
            ) from e
        except Exception as e:
            logger.error(f"Failed to load TFT model: {e}")
            return None
    return cast("TemporalFusionTransformer | None", _tft_model)


from raglite.shared.logging import get_logger
from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesData

logger = get_logger(__name__)


# =============================================================================
# Story 6.8 AC6: Regime Change Detection Data Types
# =============================================================================


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


# Minimum data points required for reliable forecasting
# FIX (2025-12-01): Lowered from 8 to 6 to allow GROUP-level SQL data
# with occasional missing months (e.g., 7 months Feb-Sep missing June)
# Prophet can produce reasonable forecasts with 6+ monthly data points
MIN_DATA_POINTS = 6

# Story 6.3: Constants for multi-variate forecasting
# Story 6.10.4: Increased from 10% to 30% to tolerate date range mismatches
# between external data (2020-2025) and SECIL data (2021-2025)
MAX_MISSING_RATIO = 0.30  # Maximum 30% missing data allowed
MAX_INTERPOLATION_GAP = 3  # Maximum periods to interpolate
MIN_CV_DATA_POINTS = 12  # Minimum points for cross-validation

# Story 6.8 AC6: Regime detection constants
MIN_REGIME_DATA_POINTS = 12  # Minimum data points for regime detection
DEFAULT_CUSUM_THRESHOLD = 5.0  # CUSUM threshold (tuned for financial data, higher = fewer changes)
DEFAULT_WINDOW_SIZE = 6  # Rolling window for variance detection (months)


class InsufficientDataError(Exception):
    """Exception raised when insufficient data for forecasting."""

    pass


# =============================================================================
# Story 6.8 AC6: Regime Change Detection Functions
# =============================================================================


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


# =============================================================================
# Story 6.13: Chronos-2 Cold-Start Forecasting
# =============================================================================


async def _generate_chronos_cold_start_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int = 4,
) -> ForecastResult:
    """Generate zero-shot forecast using Chronos-2 for cold-start scenarios.

    Story 6.13 AC2: Cold-start path when historical_data < MIN_DATA_POINTS.
    Uses Chronos-2 foundation model which requires NO training and works
    with as few as 3 data points.

    Args:
        metric: Metric name
        historical_data: Time-series data (3-5 points typically)
        periods_ahead: Number of periods to forecast

    Returns:
        ForecastResult with Chronos-2 zero-shot predictions and confidence intervals

    Raises:
        InsufficientDataError: If <3 data points (absolute minimum for Chronos-2)
    """
    import torch

    # Input validation: Check for empty data
    if historical_data is None or len(historical_data.points) == 0:
        raise InsufficientDataError("Chronos-2 requires minimum 3 data points. Got 0.")

    if len(historical_data.points) < 3:
        raise InsufficientDataError(
            f"Chronos-2 requires minimum 3 data points. Got {len(historical_data.points)}."
        )

    # Input validation: Check for NaN values
    values = [float(p.value) for p in historical_data.points]
    if all(np.isnan(v) for v in values):
        raise InsufficientDataError(
            f"Chronos-2 received all-NaN values. Got {len(values)} NaN values."
        )

    logger.info(
        "Cold-start path: using Chronos-2 zero-shot",
        extra={
            "metric": metric,
            "data_points": len(historical_data.points),
            "periods_ahead": periods_ahead,
        },
    )

    # Load Chronos-2 pipeline (cached singleton)
    pipeline = _get_chronos_pipeline()

    # Prepare input tensor from historical data
    inputs = torch.tensor(values, dtype=torch.float32).unsqueeze(0)  # Shape: (1, T)

    # Generate forecast with prediction intervals
    # Chronos-Bolt uses simplified API: predict(inputs, prediction_length)
    forecast = pipeline.predict(
        inputs=inputs,
        prediction_length=periods_ahead,
    )

    # Extract quantiles from forecast tensor
    # forecast shape: (1, num_samples, prediction_length)
    forecast_samples = forecast.squeeze(0).numpy()  # Shape: (num_samples, prediction_length)

    # Calculate quantiles: 10% (lower), 50% (median), 90% (upper)
    lower_bound = np.percentile(forecast_samples, 10, axis=0).tolist()  # 10th percentile
    median_forecast = np.percentile(forecast_samples, 50, axis=0).tolist()  # Median
    upper_bound = np.percentile(forecast_samples, 90, axis=0).tolist()  # 90th percentile

    # Generate future dates
    last_date = historical_data.points[-1].date
    forecast_dates = pd.date_range(start=last_date, periods=periods_ahead + 1, freq="MS")[1:]

    # Build forecast points with confidence intervals
    forecast_points = [
        ForecastPoint(
            date=forecast_dates[i].to_pydatetime(),
            value=float(median_forecast[i]),
            lower=float(lower_bound[i]),
            upper=float(upper_bound[i]),
            label=f"{forecast_dates[i].strftime('%b-%y')}",
        )
        for i in range(periods_ahead)
    ]

    return ForecastResult(
        metric_name=metric,
        forecast=forecast_points,
        model_type="chronos-2-zero-shot",
        confidence_reasoning=(
            f"Zero-shot forecast using Chronos-2 foundation model. "
            f"Cold-start scenario with only {len(historical_data.points)} data points. "
            f"Chronos-2 is pre-trained on diverse time-series datasets and requires no training. "
            f"Wider confidence intervals reflect limited historical context."
        ),
        basis=f"Chronos-2 zero-shot model (cold-start with {len(historical_data.points)} data points)",
        periods_ahead=periods_ahead,
        ensemble_weights={"chronos": 1.0},  # 100% Chronos-2 for cold-start
    )


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

    # Story 6.13 AC2: Cold-start path for insufficient data
    # Route to Chronos-2 zero-shot when < MIN_DATA_POINTS
    if len(historical_data.points) < MIN_DATA_POINTS:
        logger.info(
            "Cold-start detected: routing to Chronos-2 zero-shot",
            extra={"metric": metric, "data_points": len(historical_data.points)},
        )
        return await _generate_chronos_cold_start_forecast(
            metric=metric,
            historical_data=historical_data,
            periods_ahead=periods_ahead,
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
        # Energy cost metrics (DB names + variable names) - KEEP thermal_cost only
        "thermal_cost",
        "thermal energy",
        "fuel_cost",
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


# ===========================================================================
# Story 6.8 AC4: LightGBM Configuration
# ===========================================================================

_lightgbm_loaded = False


def _get_lightgbm_regressor() -> Any:
    """Lazy-load LGBMRegressor from lightgbm."""
    global _lightgbm_loaded
    if not _lightgbm_loaded:
        from lightgbm import LGBMRegressor

        _lightgbm_loaded = True
        return LGBMRegressor
    from lightgbm import LGBMRegressor

    return LGBMRegressor


# Story 6.8 AC4: Default LightGBM hyperparameter grid
# LightGBM parameters tuned for time-series forecasting
LIGHTGBM_PARAM_GRID = {
    "n_estimators": [50, 100, 200],
    "num_leaves": [15, 31, 63],
    "learning_rate": [0.01, 0.1, 0.2],
    "min_child_samples": [5, 10, 20],
}

# Fast mode for testing (reduced grid)
LIGHTGBM_PARAM_GRID_FAST = {
    "n_estimators": [100],
    "num_leaves": [31],
    "learning_rate": [0.1],
    "min_child_samples": [10],
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


def fit_lightgbm(
    X: pd.DataFrame,
    y: pd.Series,
    fast_mode: bool = False,
) -> tuple[LGBMRegressor, dict[str, object]]:
    """Fit LightGBM regressor with hyperparameter tuning.

    Story 6.8 AC4: LightGBM with GridSearchCV (5-fold time-series split).

    LightGBM advantages over XGBoost:
    - Faster training (histogram-based algorithm)
    - Better handling of categorical features
    - Lower memory usage

    Args:
        X: Feature DataFrame (regressors)
        y: Target series (metric values)
        fast_mode: Use reduced param grid for testing (default: False)

    Returns:
        Tuple of (best fitted LGBMRegressor model, accuracy metrics dict with rmse/mae/mape/best_params)
    """
    LGBMRegressor = _get_lightgbm_regressor()
    GridSearchCV = _get_grid_search_cv()
    TimeSeriesSplit = _get_time_series_split()

    param_grid = LIGHTGBM_PARAM_GRID_FAST if fast_mode else LIGHTGBM_PARAM_GRID

    # Use fewer splits for small datasets
    n_splits = min(5, len(X) - 1)
    tscv = TimeSeriesSplit(n_splits=n_splits)

    # Use multiple scoring to get RMSE, MAE
    scoring = {
        "rmse": "neg_root_mean_squared_error",
        "mae": "neg_mean_absolute_error",
    }

    grid_search = GridSearchCV(
        LGBMRegressor(random_state=42, verbosity=-1),
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
        "LightGBM fitted",
        extra={
            "best_params": grid_search.best_params_,
            "cv_rmse": best_rmse,
            "cv_mae": best_mae,
            "fast_mode": fast_mode,
        },
    )

    return best_model, metrics


def _fit_and_forecast_lightgbm(
    X: pd.DataFrame,
    y: pd.Series,
    X_future: pd.DataFrame,
    periods_ahead: int,
    fast_mode: bool = False,
) -> dict[str, Any]:
    """Fit LightGBM and generate forecast (for ThreadPoolExecutor).

    Story 6.8 AC4: Combined fit+forecast for parallel execution.

    Args:
        X: Training feature DataFrame
        y: Target series
        X_future: Future feature values for prediction
        periods_ahead: Number of periods to forecast
        fast_mode: Use reduced hyperparameter grid

    Returns:
        Dict with 'values' list and 'metrics' dict
    """
    model, metrics = fit_lightgbm(X, y, fast_mode=fast_mode)
    predictions = model.predict(X_future)
    return {
        "values": predictions.tolist()[:periods_ahead],
        "metrics": metrics,
    }


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


def _fit_and_forecast_chronos(
    y: pd.Series,
    periods_ahead: int,
    external_regressors: pd.DataFrame | None = None,
) -> dict[str, Any] | None:
    """Generate Chronos-2 forecast (for ThreadPoolExecutor).

    Story 6.13 AC3, AC4: Zero-shot forecasting with optional covariates.
    Chronos-2 requires NO training - it's a pre-trained foundation model.

    Args:
        y: Target time-series values
        periods_ahead: Number of periods to forecast
        external_regressors: Optional external covariates (NOT USED in initial implementation)

    Returns:
        Dict with 'values' list and 'metrics' dict, or None if inference fails
    """
    import time

    import torch

    from raglite.shared.config import settings

    # Input validation: Check for NaN or empty arrays
    if y is None or len(y) == 0:
        logger.warning("Chronos-2 received empty input array", extra={"data_points": 0})
        return None

    if y.isna().all():
        logger.warning(
            "Chronos-2 received all-NaN input",
            extra={"data_points": len(y), "nan_count": y.isna().sum()},
        )
        return None

    logger.info(
        "Starting Chronos-2 inference",
        extra={
            "data_points": len(y),
            "periods_ahead": periods_ahead,
            "has_regressors": external_regressors is not None,
        },
    )

    try:
        start_time = time.time()

        # Load Chronos-2 pipeline (cached singleton)
        pipeline = _get_chronos_pipeline()

        # Prepare input tensor
        inputs = torch.tensor(y.values, dtype=torch.float32).unsqueeze(0)  # Shape: (1, T)

        # Generate forecast (zero-shot, no training)
        # Chronos-Bolt uses simplified API: predict(inputs, prediction_length)
        # NOTE: Chronos-2 DOES support covariates in v2.0+, but we use simple
        # time-series only for ensemble consistency. Future story can add covariates.
        forecast = pipeline.predict(
            inputs=inputs,
            prediction_length=periods_ahead,
        )

        # Extract median forecast (50th percentile)
        forecast_samples = forecast.squeeze(0).numpy()  # Shape: (num_samples, prediction_length)
        median_forecast = np.percentile(forecast_samples, 50, axis=0)

        # Calculate elapsed time
        elapsed = time.time() - start_time

        # Log completion with timing (AC6: timeout monitoring)
        logger.info(
            "Chronos-2 inference completed",
            extra={
                "elapsed_seconds": round(elapsed, 3),
                "periods_ahead": periods_ahead,
                "timeout_threshold": settings.chronos_inference_timeout,
            },
        )

        # Warn if inference exceeded timeout threshold (AC6)
        if elapsed > settings.chronos_inference_timeout:
            logger.warning(
                "Chronos-2 inference exceeded timeout threshold",
                extra={
                    "elapsed_seconds": round(elapsed, 3),
                    "timeout_threshold": settings.chronos_inference_timeout,
                    "overage_seconds": round(elapsed - settings.chronos_inference_timeout, 3),
                },
            )

        # Return format matching other models
        return {
            "values": median_forecast.tolist(),
            "metrics": {},  # Zero-shot model has no training metrics
        }

    except Exception as e:
        logger.error(
            "Chronos-2 inference failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "data_points": len(y),
                "periods_ahead": periods_ahead,
            },
        )
        return None  # Graceful fallback - None indicates model failure


def _fit_and_forecast_tft(
    y: pd.Series,
    periods_ahead: int,
    external_regressors: pd.DataFrame | None = None,
) -> dict[str, Any] | None:
    """Generate TFT forecast from pre-trained checkpoint (for ThreadPoolExecutor).

    Story 6.14 AC5, AC7: Offline-trained model inference with graceful degradation.
    TFT requires OFFLINE TRAINING - checkpoint must exist in model_registry.

    Args:
        y: Target time-series values
        periods_ahead: Number of periods to forecast
        external_regressors: Optional external covariates (for TFT v2)

    Returns:
        Dict with 'values' list and 'metrics' dict, or None if no checkpoint available
    """
    import time

    logger.info(
        "Starting TFT inference",
        extra={
            "data_points": len(y),
            "periods_ahead": periods_ahead,
            "has_regressors": external_regressors is not None,
        },
    )

    try:
        start_time = time.time()

        # Load TFT model from checkpoint (cached singleton)
        # Returns None if no trained checkpoint available (graceful degradation)
        model = _get_tft_model()

        if model is None:
            logger.warning("No TFT checkpoint available - skipping TFT forecast")
            return None

        # Prepare data for TFT inference
        # TFT requires TimeSeriesDataSet format with time_idx, group_ids, target
        from pytorch_forecasting import TimeSeriesDataSet

        # Create DataFrame in TFT format
        df = pd.DataFrame(
            {
                "time_idx": range(len(y)),
                "metric_name": "target_metric",  # Single group for now
                "value": y.values,
            }
        )

        # Create minimal TimeSeriesDataSet for prediction
        # Use same parameters as training (from TFT_TRAINING_CONFIG)
        max_encoder_length = 12  # From settings.tft_encoder_length
        max_prediction_length = periods_ahead

        # Need sufficient history for encoder
        if len(y) < max_encoder_length:
            logger.warning(f"Insufficient data for TFT (need {max_encoder_length}, have {len(y)})")
            return None

        # Create dataset for inference
        # Use last max_encoder_length points as context
        dataset = TimeSeriesDataSet(
            df,
            time_idx="time_idx",
            target="value",
            group_ids=["metric_name"],
            min_encoder_length=max_encoder_length,
            max_encoder_length=max_encoder_length,
            min_prediction_length=1,
            max_prediction_length=max_prediction_length,
            add_relative_time_idx=True,
            add_target_scales=True,
            add_encoder_length=True,
            time_varying_known_reals=[],
            time_varying_unknown_reals=[],
            static_categoricals=[],
        )

        # Generate predictions
        dataloader = dataset.to_dataloader(train=False, batch_size=1, num_workers=0)

        # Force CPU inference to avoid MPS memory allocation issues
        import torch

        device = torch.device("cpu")
        model = model.to(device)
        model.eval()

        # Get predictions from model (using Trainer for consistent behavior)
        import lightning.pytorch as pl

        trainer = pl.Trainer(accelerator="cpu", logger=False, enable_progress_bar=False)
        predictions = trainer.predict(model, dataloader)

        # Extract point forecast (median quantile, index 3 out of 7 quantiles)
        # TFT outputs quantiles: [0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98]
        # trainer.predict returns a list of batch predictions
        if predictions and len(predictions) > 0:
            batch_pred = predictions[0]  # First batch
            if hasattr(batch_pred, "prediction"):
                # Raw output format
                point_forecast = batch_pred.prediction[0, :, 3].cpu().numpy().tolist()
            elif isinstance(batch_pred, dict) and "prediction" in batch_pred:
                point_forecast = batch_pred["prediction"][0, :, 3].cpu().numpy().tolist()
            else:
                # Tensor output - check if it's actually a tensor-like object
                if hasattr(batch_pred, "shape") and hasattr(batch_pred, "cpu"):
                    # Tensor-like object (e.g., torch.Tensor)
                    try:
                        # MyPy can't infer this is a tensor, so we need to cast it
                        point_forecast = batch_pred[0, :, 3].cpu().numpy().tolist()  # type: ignore[call-overload]
                    except (IndexError, TypeError) as e:
                        logger.warning(f"Failed to extract tensor data: {e}")
                        return None
                elif hasattr(batch_pred, "__getitem__") and isinstance(batch_pred, list):
                    # List output
                    try:
                        point_forecast = (
                            batch_pred[0][3] if isinstance(batch_pred[0], list) else batch_pred[0]
                        )
                    except (IndexError, TypeError) as e:
                        logger.warning(f"Failed to extract list data: {e}")
                        return None
                else:
                    logger.warning("Unexpected batch_pred format for tensor output")
                    return None
        else:
            logger.warning("TFT prediction returned empty results")
            return None

        elapsed = time.time() - start_time

        logger.info(
            "TFT inference complete",
            extra={
                "forecast_length": len(point_forecast),
                "inference_time_ms": elapsed * 1000,
            },
        )

        return {
            "values": point_forecast,
            "metrics": {
                "inference_time_ms": elapsed * 1000,
            },
        }

    except Exception as e:
        logger.error(
            "TFT inference failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "data_points": len(y),
                "periods_ahead": periods_ahead,
            },
        )
        return None  # Graceful fallback - None indicates model failure


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
    if not predictions:
        # No predictions available, return empty list
        return []

    # Use the maximum prediction length across all models
    n_periods = max(len(pred) for pred in predictions.values())
    result = [0.0] * n_periods

    for model in models:
        if model not in predictions:
            continue  # Skip models that don't have predictions
        pred_values = predictions[model]
        # Add predictions for available periods
        for i in range(len(pred_values)):
            result[i] += pred_values[i] * normalized[model]

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
    Story 6.12: Added CatBoost to ensemble.
    Story 6.13: Added Chronos-2 to ensemble.
    Story 6.14: Added TFT to ensemble.

    Args:
        metric: Metric name (e.g., "cement_demand")
        historical_data: Time-series data from extraction
        external_regressors: Dict of regressor series from PostgreSQL
        periods_ahead: Number of periods to forecast (default: 4)
        models: Models to use (default: ["prophet", "linear", "xgboost", "lightgbm", "catboost", "chronos", "tft"])
        weights: Model weights (default from settings)
        fast_mode: Use fast hyperparameter grid for XGBoost/LightGBM/CatBoost (default: False)

    Returns:
        ForecastResult with ensemble predictions and per-model details

    Raises:
        InsufficientDataError: If <6 data points available
    """
    from raglite.forecasting.adaptive_weights import get_adaptive_weights, handle_model_failure
    from raglite.shared.config import settings

    # Default models and weights from settings
    if models is None:
        models = settings.forecasting_models.split(",")

    # Story 6.12 AC4: Try adaptive weights, fallback to static if not available
    has_regressors = external_regressors is not None and len(external_regressors) > 0
    if weights is None:
        try:
            # Get adaptive weights from PostgreSQL (with static fallback)
            weights = get_adaptive_weights(metric, has_regressors=has_regressors)
            logger.info(
                "Using adaptive weights",
                extra={"metric": metric, "weights": weights, "has_regressors": has_regressors},
            )
        except Exception as e:
            logger.warning(
                f"Failed to get adaptive weights, using static: {e}",
                extra={"metric": metric},
            )
            weights = {
                "prophet": settings.ensemble_weight_prophet,
                "linear": settings.ensemble_weight_linear,
                "xgboost": settings.ensemble_weight_xgboost,
                "lightgbm": settings.ensemble_weight_lightgbm,  # Story 6.8 AC4
                "catboost": settings.ensemble_weight_catboost,  # Story 6.12
                "chronos": settings.ensemble_weight_chronos,  # Story 6.13
                "tft": settings.ensemble_weight_tft,  # Story 6.14
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
    # Story 6.12 AC4: Track failed models for weight re-normalization (initialize early)
    failed_models: list[str] = []

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
    if "linear" in models:
        if len(X.columns) > 0 and X_future is not None:
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
        else:
            # Story 6.12 AC4: Linear skipped due to no regressors - add to failed_models for weight re-normalization
            logger.info("Linear model skipped: requires external regressors (len(X.columns)=0)")
            failed_models.append("linear")

    # XGBoost task (sync, via ThreadPoolExecutor)
    if "xgboost" in models:
        if len(X.columns) > 0 and X_future is not None:
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
        else:
            # Story 6.12 AC4: XGBoost skipped due to no regressors - add to failed_models for weight re-normalization
            logger.info("XGBoost model skipped: requires external regressors (len(X.columns)=0)")
            failed_models.append("xgboost")

    # LightGBM task (sync, via ThreadPoolExecutor) - Story 6.8 AC4
    if "lightgbm" in models:
        if len(X.columns) > 0 and X_future is not None:
            # Create explicit copies for thread safety
            X_copy_lgb = X.copy()
            y_copy_lgb = y.copy()
            X_future_copy_lgb = X_future.copy()
            fast_mode_copy_lgb = fast_mode

            def run_lightgbm() -> dict[str, Any]:
                return _fit_and_forecast_lightgbm(
                    X_copy_lgb, y_copy_lgb, X_future_copy_lgb, periods_ahead, fast_mode_copy_lgb
                )

            tasks.append(loop.run_in_executor(_sklearn_executor, run_lightgbm))
            task_names.append("lightgbm")
        else:
            # Story 6.12 AC4: LightGBM skipped due to no regressors - add to failed_models for weight re-normalization
            logger.info("LightGBM model skipped: requires external regressors (len(X.columns)=0)")
            failed_models.append("lightgbm")

    # CatBoost task (sync, via ThreadPoolExecutor) - Story 6.12
    if "catboost" in models:
        if len(X.columns) > 0 and X_future is not None:
            # Create explicit copies for thread safety
            X_copy_cat = X.copy()
            y_copy_cat = y.copy()
            X_future_copy_cat = X_future.copy()
            fast_mode_copy_cat = fast_mode

            def run_catboost() -> dict[str, Any]:
                return _fit_and_forecast_catboost(
                    X_copy_cat, y_copy_cat, X_future_copy_cat, periods_ahead, fast_mode_copy_cat
                )

            tasks.append(loop.run_in_executor(_sklearn_executor, run_catboost))
            task_names.append("catboost")
        else:
            # Story 6.12 AC4: CatBoost skipped due to no regressors - add to failed_models for weight re-normalization
            logger.info("CatBoost model skipped: requires external regressors (len(X.columns)=0)")
            failed_models.append("catboost")

    # Chronos-2 task (sync, via ThreadPoolExecutor) - Story 6.13
    # Chronos-2 works with OR without regressors (pure time-series model)
    if "chronos" in models:
        # Create explicit copy for thread safety
        y_copy_chronos = y.copy()
        periods_copy_chronos = periods_ahead

        def run_chronos() -> dict[str, Any] | None:
            return _fit_and_forecast_chronos(
                y_copy_chronos,
                periods_copy_chronos,
                external_regressors=None,  # Not using covariates in v1
            )

        tasks.append(loop.run_in_executor(_sklearn_executor, run_chronos))
        task_names.append("chronos")

    # TFT task (sync, via ThreadPoolExecutor) - Story 6.14
    # TFT works with pre-trained checkpoint from offline training
    if "tft" in models:
        # Create explicit copy for thread safety
        y_copy_tft = y.copy()
        periods_copy_tft = periods_ahead
        X_copy_tft = X.copy() if len(X.columns) > 0 else None

        def run_tft() -> dict[str, Any] | None:
            return _fit_and_forecast_tft(
                y_copy_tft,
                periods_copy_tft,
                external_regressors=X_copy_tft,
            )

        tasks.append(loop.run_in_executor(_sklearn_executor, run_tft))
        task_names.append("tft")

    # Execute all models in parallel
    if tasks:
        logger.info(
            "Running ensemble models in parallel",
            extra={"models": task_names, "parallel_count": len(tasks)},
        )
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results - Story 6.12 AC4: Handle failures with weight re-normalization
        for name, result in zip(task_names, results, strict=False):
            if isinstance(result, Exception):
                logger.warning(f"{name.capitalize()} model failed: {result}")
                failed_models.append(name)
                continue

            # Handle None return (graceful failure from model)
            if result is None:
                logger.warning(f"{name.capitalize()} model returned None (graceful failure)")
                failed_models.append(name)
                continue

            if name == "prophet":
                prophet_result = cast(ForecastResult, result)
                predictions["prophet"] = [p.value for p in prophet_result.forecast]
                metrics_results["prophet"] = prophet_result.accuracy_metrics
                successful_models.append("prophet")
                logger.info("Prophet model succeeded (parallel)")
            else:
                # Linear, XGBoost, LightGBM, CatBoost, or Chronos result is a dict with values and metrics
                result_dict = cast("dict[str, Any]", result)
                predictions[name] = result_dict["values"]
                metrics_value = result_dict.get("metrics")
                if metrics_value is not None:
                    metrics_results[name] = cast("dict[str, Any]", metrics_value)
                successful_models.append(name)
                logger.info(f"{name.capitalize()} model succeeded (parallel)")

                # Log Chronos-2 ensemble participation (Issue 7)
                if name == "chronos":
                    logger.info(
                        "Chronos-2 participating in ensemble",
                        extra={
                            "ensemble_weight": weights.get("chronos", 0.0),
                            "forecast_periods": len(result_dict["values"]),
                        },
                    )
    else:
        logger.info("No models configured to run")

    # Story 6.12 AC4: Re-normalize weights after model failures
    if failed_models and weights:
        for failed in failed_models:
            weights = handle_model_failure(weights, failed)
        logger.info(
            "Weights re-normalized after model failures",
            extra={"failed_models": failed_models, "new_weights": weights},
        )

    # Normalize weights to only include successful models
    # This ensures when only a subset of models are requested (e.g., prophet+catboost)
    # and one fails (e.g., catboost), the remaining model gets weight 1.0
    if successful_models and weights:
        remaining = {k: weights.get(k, 0.0) for k in successful_models if weights.get(k, 0.0) > 0}
        if remaining:
            total = sum(remaining.values())
            if total > 0:
                weights = {k: v / total for k, v in remaining.items()}
                logger.info(
                    "Weights normalized to successful models only",
                    extra={"successful_models": successful_models, "final_weights": weights},
                )

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

    # Aggregate accuracy metrics from individual models
    combined_metrics: dict[str, float] = {}
    if metrics_results:
        rmse_values = [
            float(m.get("rmse", 0))
            for m in metrics_results.values()
            if isinstance(m.get("rmse"), (int, float)) and m.get("rmse", 0) > 0
        ]
        mae_values = [
            float(m.get("mae", 0))
            for m in metrics_results.values()
            if isinstance(m.get("mae"), (int, float)) and m.get("mae", 0) > 0
        ]
        mape_values = [
            float(m.get("mape", 0))
            for m in metrics_results.values()
            if isinstance(m.get("mape"), (int, float)) and m.get("mape", 0) > 0
        ]
        if rmse_values:
            combined_metrics["rmse"] = float(np.mean(rmse_values))
        if mae_values:
            combined_metrics["mae"] = float(np.mean(mae_values))
        if mape_values:
            combined_metrics["mape"] = float(np.mean(mape_values))

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
