"""Shared fixtures for data characteristics analyzer tests.

This conftest provides 37 fixtures for testing the data analyzer module:
- Stationary/non-stationary series
- Trending series (upward/downward)
- Seasonal series (additive/multiplicative/quarterly)
- Volatility series (high/low)
- Short series (cold-start testing)
- Edge cases (constant, NaNs, outliers, negative values)
- Boundary conditions (CV thresholds, seasonal strength boundaries)

NOTE: All data_analyzer tests are skipped in LIGHTWEIGHT_TESTS mode because they
require real statsmodels (adfuller, kpss, acf) functions. The mocked versions
don't return values that match statistical expectations.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip all data_analyzer tests when LIGHTWEIGHT_TESTS=true.

    These tests require real statsmodels functions (adfuller, kpss, acf) that
    cannot be meaningfully mocked - the tests verify statistical properties.
    """
    if os.environ.get("LIGHTWEIGHT_TESTS") != "true":
        return

    skip_lightweight = pytest.mark.skip(
        reason="Data analyzer tests require real statsmodels (not mocked)"
    )
    for item in items:
        # Only skip tests in this directory
        if "data_analyzer" in str(item.fspath):
            item.add_marker(skip_lightweight)


# -----------------------------------------------------------------------------
# Basic Stationarity Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def stationary_series() -> pd.Series:
    """Create a stationary time series (white noise with constant mean/variance).

    Properties:
    - Mean: ~100
    - No trend
    - No seasonality
    - Constant variance
    """
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    values = 100 + np.random.normal(0, 5, 60)
    return pd.Series(values, index=dates, name="stationary_metric")


@pytest.fixture
def non_stationary_series() -> pd.Series:
    """Create a non-stationary time series (random walk).

    Properties:
    - Unit root (non-stationary)
    - Stochastic trend
    - No seasonality
    """
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    # Random walk: y_t = y_{t-1} + epsilon
    increments = np.random.normal(0, 5, 60)
    values = 100 + np.cumsum(increments)
    return pd.Series(values, index=dates, name="random_walk")


# -----------------------------------------------------------------------------
# Trend Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def trending_series() -> pd.Series:
    """Create a time series with a strong upward trend.

    Properties:
    - Clear upward trend (slope ~2.0 per period)
    - Some noise
    - No seasonality
    """
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    trend = np.linspace(100, 220, 60)  # Slope of 2.0 per period
    noise = np.random.normal(0, 5, 60)
    values = trend + noise
    return pd.Series(values, index=dates, name="trending_metric")


@pytest.fixture
def downward_trending_series() -> pd.Series:
    """Create a time series with a strong downward trend.

    Properties:
    - Clear downward trend (slope ~-1.5 per period)
    - Some noise
    """
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    trend = np.linspace(200, 110, 60)  # Negative slope
    noise = np.random.normal(0, 5, 60)
    values = trend + noise
    return pd.Series(values, index=dates, name="downward_metric")


# -----------------------------------------------------------------------------
# Seasonality Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def seasonal_series() -> pd.Series:
    """Create a time series with strong monthly seasonality.

    Properties:
    - Monthly seasonality (period=12)
    - Seasonal strength > 0.3
    - Additive seasonality pattern
    """
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    # Base level + strong seasonal pattern
    base = 100
    seasonality = 30 * np.sin(2 * np.pi * np.arange(60) / 12)
    noise = np.random.normal(0, 3, 60)
    values = base + seasonality + noise
    return pd.Series(values, index=dates, name="seasonal_metric")


@pytest.fixture
def multiplicative_seasonal_series() -> pd.Series:
    """Create a time series with multiplicative seasonality.

    Properties:
    - Seasonality that scales with the level
    - Higher variance when values are higher
    """
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    # Growing base with multiplicative seasonality
    base = np.linspace(100, 200, 60)
    seasonality_factor = 1 + 0.2 * np.sin(2 * np.pi * np.arange(60) / 12)
    noise = np.random.normal(0, 0.02, 60)
    values = base * seasonality_factor * (1 + noise)
    return pd.Series(values, index=dates, name="mult_seasonal_metric")


@pytest.fixture
def quarterly_series() -> pd.Series:
    """Create a quarterly time series with seasonal pattern.

    Properties:
    - Quarterly frequency
    - Seasonal period = 4
    """
    np.random.seed(42)
    dates = pd.date_range(start="2016-01-01", periods=28, freq="QS")
    base = 1000
    seasonality = 100 * np.sin(2 * np.pi * np.arange(28) / 4)
    noise = np.random.normal(0, 20, 28)
    values = base + seasonality + noise
    return pd.Series(values, index=dates, name="quarterly_metric")


@pytest.fixture
def seasonal_strength_weak_series() -> pd.Series:
    """[P2] Series with weak seasonality (strength ~0.15).

    Tests seasonal detection near threshold (0.1 for period detection).
    """
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    base = 100
    # Weak seasonality (amplitude 5, noise 8)
    seasonality = 5 * np.sin(2 * np.pi * np.arange(60) / 12)
    noise = np.random.default_rng(42).normal(0, 8, 60)
    values = base + seasonality + noise
    return pd.Series(values, index=dates, name="weak_seasonal")


@pytest.fixture
def seasonal_strength_boundary_series() -> pd.Series:
    """[P1] Series with seasonal strength exactly at 0.3 threshold.

    Tests ADDITIVE vs NONE classification boundary.
    """
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    base = 100
    # Tuned to get ACF ~0.3 at lag 12
    seasonality = 15 * np.sin(2 * np.pi * np.arange(60) / 12)
    noise = np.random.default_rng(42).normal(0, 5, 60)
    values = base + seasonality + noise
    return pd.Series(values, index=dates, name="boundary_seasonal")


# -----------------------------------------------------------------------------
# Volatility Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def high_volatility_series() -> pd.Series:
    """Create a time series with high volatility (CV > 0.3).

    Properties:
    - Coefficient of variation > 0.3
    - High variance relative to mean
    """
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    # Low mean with high variance -> high CV
    values = 50 + np.random.normal(0, 25, 60)
    values = np.abs(values)  # Keep positive
    return pd.Series(values, index=dates, name="volatile_metric")


@pytest.fixture
def low_volatility_series() -> pd.Series:
    """Create a time series with low volatility (CV < 0.1).

    Properties:
    - Coefficient of variation < 0.1
    - Low variance relative to mean
    """
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    # High mean with low variance -> low CV
    values = 1000 + np.random.normal(0, 30, 60)
    return pd.Series(values, index=dates, name="stable_metric")


@pytest.fixture
def cv_threshold_low_series() -> pd.Series:
    """[P1] Series with CV exactly at LOW/MEDIUM boundary (CV = 0.1).

    Tests volatility classification at exact threshold.
    """
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    # Target: CV = std/mean = 0.1, mean = 100, std = 10
    np.random.seed(42)
    values = 100 + np.random.normal(0, 10, 60)
    return pd.Series(values, index=dates, name="cv_threshold_low")


@pytest.fixture
def cv_threshold_high_series() -> pd.Series:
    """[P1] Series with CV exactly at MEDIUM/HIGH boundary (CV = 0.3).

    Tests volatility classification at exact threshold.
    """
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    # Target: CV = 0.3, mean = 100, std = 30
    np.random.seed(42)
    values = 100 + np.random.normal(0, 30, 60)
    return pd.Series(values, index=dates, name="cv_threshold_high")


# -----------------------------------------------------------------------------
# Short Series Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def short_series() -> pd.Series:
    """Create a short time series (only 6 data points) for cold-start testing."""
    dates = pd.date_range(start="2024-01-01", periods=6, freq="MS")
    values = [100, 105, 110, 108, 115, 120]
    return pd.Series(values, index=dates, name="short_metric")


@pytest.fixture
def very_short_series() -> pd.Series:
    """Create a very short time series (only 4 data points) for edge case testing."""
    dates = pd.date_range(start="2024-01-01", periods=4, freq="MS")
    values = [100, 110, 105, 115]
    return pd.Series(values, index=dates, name="very_short_metric")


@pytest.fixture
def short_window_series() -> pd.Series:
    """[P2] Series shorter than rolling volatility window.

    Tests rolling volatility when len(series) < window.
    """
    dates = pd.date_range(start="2024-01-01", periods=8, freq="MS")
    np.random.seed(42)
    values = 100 + np.random.normal(0, 10, 8)
    return pd.Series(values, index=dates, name="short_window")


@pytest.fixture
def exactly_twelve_points() -> pd.Series:
    """[P2] Series with exactly 12 points (cold-start boundary).

    Tests cold-start detection at exact threshold.
    """
    dates = pd.date_range(start="2024-01-01", periods=12, freq="MS")
    values = [100, 105, 110, 108, 115, 120, 118, 125, 130, 128, 135, 140]
    return pd.Series(values, index=dates, name="exactly_twelve")


@pytest.fixture
def exactly_twenty_four_points() -> pd.Series:
    """[P2] Series with exactly 24 points (TFT recommendation threshold).

    Tests TFT inclusion at exact threshold.
    """
    dates = pd.date_range(start="2022-01-01", periods=24, freq="MS")
    np.random.seed(42)
    values = 100 + np.cumsum(np.random.normal(2, 5, 24))
    return pd.Series(values, index=dates, name="exactly_24")


# -----------------------------------------------------------------------------
# Edge Case Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def constant_series() -> pd.Series:
    """Create a constant time series (all same values) for edge case testing."""
    dates = pd.date_range(start="2020-01-01", periods=30, freq="MS")
    values = [100.0] * 30
    return pd.Series(values, index=dates, name="constant_metric")


@pytest.fixture
def series_with_nans() -> pd.Series:
    """Create a time series with missing values (NaNs)."""
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    values = 100 + np.random.normal(0, 10, 60)
    # Insert NaNs at specific positions
    values[5] = np.nan
    values[15] = np.nan
    values[25] = np.nan
    values[35] = np.nan
    values[45] = np.nan
    return pd.Series(values, index=dates, name="nan_metric")


@pytest.fixture
def series_with_outliers() -> pd.Series:
    """Create a time series with outliers for IQR testing."""
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    values = 100 + np.random.normal(0, 5, 60)
    # Insert outliers (values > 1.5 * IQR from median)
    values[10] = 200  # High outlier
    values[30] = 10  # Low outlier
    values[50] = 220  # Another high outlier
    return pd.Series(values, index=dates, name="outlier_metric")


@pytest.fixture
def non_stationary_d2_series() -> pd.Series:
    """[P1] Series requiring d=2 differencing (integrated of order 2).

    Tests suggested_differencing=2 detection.
    """
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    # Double cumulative sum to create I(2) series
    np.random.seed(42)
    increments = np.random.normal(0, 1, 60)
    first_diff = np.cumsum(increments)
    values = 100 + np.cumsum(first_diff)
    return pd.Series(values, index=dates, name="d2_series")


@pytest.fixture
def mixed_characteristics_series() -> pd.Series:
    """[P1] Series with multiple characteristics (trend + seasonality + volatility).

    Tests integration of multiple recommendation paths.
    """
    dates = pd.date_range(start="2020-01-01", periods=60, freq="MS")
    np.random.seed(42)
    # Trend + seasonality + high volatility
    trend = np.linspace(100, 200, 60)
    seasonality = 20 * np.sin(2 * np.pi * np.arange(60) / 12)
    noise = np.random.normal(0, 40, 60)  # High volatility
    values = trend + seasonality + noise
    return pd.Series(values, index=dates, name="mixed_characteristics")
