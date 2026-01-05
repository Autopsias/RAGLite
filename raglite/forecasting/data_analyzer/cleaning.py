"""Data cleaning utilities for time-series analysis.

This module provides functions for cleaning time-series data before analysis.
"""

from __future__ import annotations

import pandas as pd


def clean_series(series: pd.Series) -> pd.Series:
    """Clean series by handling NaN values.

    Args:
        series: Original time series

    Returns:
        Cleaned time series without NaN values

    Raises:
        ValueError: If series is too short or constant
    """
    # Drop NaN values for analysis
    clean = series.dropna()

    if len(clean) < 4:
        raise ValueError(f"Series too short after cleaning: {len(clean)} observations (minimum: 4)")

    if clean.std() == 0:
        raise ValueError("Constant series cannot be analyzed for time-series properties")

    return clean
