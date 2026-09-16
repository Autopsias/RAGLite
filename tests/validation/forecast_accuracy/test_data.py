"""Test data fixtures for forecast accuracy validation.

Story 4.10 Task 1.3: Test fixtures with known patterns.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def create_growth_data(
    start_date: datetime,
    periods: int = 12,
    start_value: float = 100000.0,
    growth_rate: float = 0.05,
    noise_pct: float = 0.02,
) -> pd.DataFrame:
    """Create synthetic growth data for validation.

    Story 4.10 Task 1.3: Test fixture with known growth pattern.

    Args:
        start_date: Start date for time series
        periods: Number of periods (default 12 quarters = 3 years)
        start_value: Starting value
        growth_rate: Per-period growth rate (default 5%)
        noise_pct: Random noise as percentage of value (default 2%)

    Returns:
        DataFrame with 'ds' and 'y' columns
    """
    np.random.seed(42)  # Reproducible results
    dates = [start_date + timedelta(days=91 * i) for i in range(periods)]
    values = []

    current_value = start_value
    for i in range(periods):
        # Add growth
        current_value = start_value * ((1 + growth_rate) ** i)
        # Add noise
        noise = current_value * noise_pct * (np.random.random() - 0.5) * 2
        values.append(current_value + noise)

    return pd.DataFrame({"ds": dates, "y": values})


def create_seasonal_data(
    start_date: datetime,
    periods: int = 12,
    base_value: float = 100000.0,
    seasonal_amplitude: float = 0.2,
    noise_pct: float = 0.02,
) -> pd.DataFrame:
    """Create synthetic seasonal data for validation.

    Story 4.10 Task 1.3: Test fixture with seasonal pattern.

    Args:
        start_date: Start date for time series
        periods: Number of periods (default 12 quarters = 3 years)
        base_value: Base value around which seasonal variation occurs
        seasonal_amplitude: Seasonal variation as percentage (default 20%)
        noise_pct: Random noise as percentage of value (default 2%)

    Returns:
        DataFrame with 'ds' and 'y' columns
    """
    np.random.seed(42)
    dates = [start_date + timedelta(days=91 * i) for i in range(periods)]
    values = []

    for i in range(periods):
        # Quarterly seasonality (Q4 high, Q2 low)
        quarter = (i % 4) + 1
        seasonal_factor = {
            1: 0.0,  # Q1: baseline
            2: -seasonal_amplitude,  # Q2: low
            3: 0.0,  # Q3: baseline
            4: seasonal_amplitude,  # Q4: high
        }[quarter]

        value = base_value * (1 + seasonal_factor)
        noise = value * noise_pct * (np.random.random() - 0.5) * 2
        values.append(value + noise)

    return pd.DataFrame({"ds": dates, "y": values})


def create_volatile_data(
    start_date: datetime,
    periods: int = 12,
    base_value: float = 100000.0,
    volatility: float = 0.15,
) -> pd.DataFrame:
    """Create synthetic volatile data for validation.

    Story 4.10 Task 1.3: Test fixture with high volatility (edge case).

    Args:
        start_date: Start date for time series
        periods: Number of periods
        base_value: Base value
        volatility: Standard deviation as percentage of value (default 15%)

    Returns:
        DataFrame with 'ds' and 'y' columns
    """
    np.random.seed(42)
    dates = [start_date + timedelta(days=91 * i) for i in range(periods)]
    values = []

    for _ in range(periods):
        variation = base_value * volatility * np.random.randn()
        value = base_value + variation
        values.append(max(value, base_value * 0.5))  # Floor at 50% of base

    return pd.DataFrame({"ds": dates, "y": values})
