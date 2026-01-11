"""YoY percentage transformation utilities.

Part of Story 8.1 refactoring to reduce preprocessing.py file size.

Provides YoY% detection and transformation for regressors like
INE Construction Output Index that need conversion before forecasting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


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
