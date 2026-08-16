"""Shared fixtures for CatBoost integration tests."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pytest

# Set test environment before importing
os.environ["APP_ENV"] = "test"

# Set DYLD_LIBRARY_PATH for XGBoost/CatBoost on macOS
os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/opt/libomp/lib")

if TYPE_CHECKING:
    from raglite.shared.models import TimeSeriesData


# Note: db_session and clean_session fixtures are now defined in
# tests/integration/conftest.py (parent) to avoid duplication across subdirectories


@pytest.fixture
def sample_historical_data() -> TimeSeriesData:
    """Create sample historical data with 20 data points for ML models."""
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    # Generate 20 monthly data points (more than minimum 12 for proper train/test split)
    # Use timezone-naive datetimes for Prophet compatibility
    base_date = datetime(2023, 1, 1)  # No timezone for Prophet
    np.random.seed(42)  # Reproducible random values
    points = [
        TimeSeriesPoint(
            date=base_date + timedelta(days=30 * i),
            value=1000.0 + i * 50.0 + np.random.uniform(-10, 10),  # noqa: S311
            label=f"Month {i + 1}",
        )
        for i in range(20)
    ]
    return TimeSeriesData(
        metric_name="cement_demand",
        points=points,
        interval="monthly",
        source_documents=["test_financial_report.pdf"],
    )


@pytest.fixture
def sample_external_regressors() -> dict[str, pd.Series]:
    """Create sample external regressors with correlation to target."""
    # Use timezone-naive datetimes to match sample_historical_data
    base_date = datetime(2023, 1, 1)  # No timezone
    dates = pd.DatetimeIndex([base_date + timedelta(days=30 * i) for i in range(20)])

    return {
        "building_permits": pd.Series(
            [
                1000,
                1020,
                1050,
                1080,
                1100,
                1150,
                1180,
                1200,
                1250,
                1280,
                1300,
                1350,
                1380,
                1420,
                1450,
                1500,
                1550,
                1600,
                1650,
                1700,
            ],
            index=dates,
        ),
        "electricity_price": pd.Series(
            [
                50.0,
                51.2,
                52.1,
                53.5,
                54.0,
                55.2,
                56.8,
                57.0,
                58.5,
                59.0,
                60.2,
                61.0,
                62.5,
                63.2,
                64.0,
                65.5,
                66.8,
                68.0,
                69.5,
                70.2,
            ],
            index=dates,
        ),
    }
