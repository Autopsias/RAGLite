"""Feature engineering utilities for time series forecasting.

Epic 7 Enhancement: Enhanced feature engineering with rolling statistics,
momentum features, and volatility indicators for improved prediction accuracy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def create_lagged_features(y: pd.Series, n_lags: int) -> pd.DataFrame:
    """Create enhanced lagged features from time series.

    Epic 7 Enhancement: Added rolling statistics, momentum, and volatility features
    based on time series forecasting best practices (Hyndman 2006, McKinsey).

    Features created:
    - Simple lags (1 to n_lags)
    - Rolling statistics (mean, std over 3, 6, 12 periods)
    - Momentum features (first difference, percentage change, YoY diff)
    - Volatility features (rolling range)

    Args:
        y: Time series data
        n_lags: Number of simple lag features to create

    Returns:
        DataFrame with all engineered features, NaN rows dropped
    """
    features = {}

    # 1. Simple lags (existing behavior)
    for i in range(1, n_lags + 1):
        features[f"lag_{i}"] = y.shift(i)

    # 2. Rolling statistics (NEW - shifted to prevent data leakage)
    # For very short series, only create rolling features that preserve training samples
    # Require: (window + shift) + n_lags < len(y) to ensure at least 1 training sample
    for window in [3, 6, 12]:
        # Ensure rolling window won't eliminate all training samples
        # Need: window (for rolling) + 1 (for shift) + n_lags (for lags) <= len(y)
        if len(y) > (window + 1 + n_lags):
            features[f"rolling_mean_{window}"] = y.rolling(window=window).mean().shift(1)
            features[f"rolling_std_{window}"] = y.rolling(window=window).std().shift(1)

    # 3. Momentum features (NEW - shifted to prevent data leakage)
    features["diff_1"] = y.diff(1).shift(1)
    features["pct_change_1"] = y.pct_change(1).shift(1)
    # For diff_12, we need: 12 (diff period) + 1 (shift) + n_lags <= len(y)
    if len(y) > (12 + 1 + n_lags):
        features["diff_12"] = y.diff(12).shift(1)  # YoY momentum

    # 4. Volatility features (NEW - shifted to prevent data leakage)
    # Same check as rolling features to preserve training samples
    if len(y) > (6 + 1 + n_lags):
        features["rolling_range_6"] = (y.rolling(6).max() - y.rolling(6).min()).shift(1)

    df = pd.DataFrame(features)
    return df.dropna()  # Drop rows with NaN from any feature


def _build_prediction_features(
    history: list, n_lags: int, training_columns: list[str]
) -> pd.DataFrame:
    """Build prediction features matching training feature structure.

    Epic 7 Enhancement: Computes all enhanced features for a single prediction step.

    Args:
        history: Historical values including any prior predictions
        n_lags: Number of lag features
        training_columns: Column names from training (for alignment)

    Returns:
        Single-row DataFrame with features matching training structure
    """
    features = {}

    # 1. Simple lags
    for j in range(1, n_lags + 1):
        if len(history) >= j:
            features[f"lag_{j}"] = history[-j]
        else:
            features[f"lag_{j}"] = np.nan

    # 2. Rolling statistics (compute from history)
    arr = np.array(history)
    for window in [3, 6, 12]:
        col_mean = f"rolling_mean_{window}"
        col_std = f"rolling_std_{window}"
        if col_mean in training_columns:
            if len(arr) >= window:
                features[col_mean] = np.mean(arr[-window:])
                features[col_std] = np.std(arr[-window:], ddof=1) if len(arr) >= window else 0.0
            else:
                features[col_mean] = np.mean(arr) if len(arr) > 0 else 0.0
                features[col_std] = np.std(arr, ddof=1) if len(arr) > 1 else 0.0

    # 3. Momentum features
    if "diff_1" in training_columns:
        features["diff_1"] = history[-1] - history[-2] if len(history) >= 2 else 0.0

    if "pct_change_1" in training_columns:
        if len(history) >= 2 and history[-2] != 0:
            features["pct_change_1"] = (history[-1] - history[-2]) / abs(history[-2])
        else:
            features["pct_change_1"] = 0.0

    if "diff_12" in training_columns:
        features["diff_12"] = history[-1] - history[-12] if len(history) >= 12 else 0.0

    # 4. Volatility features
    if "rolling_range_6" in training_columns:
        if len(arr) >= 6:
            features["rolling_range_6"] = float(np.max(arr[-6:]) - np.min(arr[-6:]))
        else:
            features["rolling_range_6"] = float(np.max(arr) - np.min(arr)) if len(arr) > 0 else 0.0

    return pd.DataFrame([features])
