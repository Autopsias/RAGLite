"""Shared fixtures for timeseries extraction tests.

Common imports and fixtures shared across test modules.
"""

from datetime import datetime

import pytest

from raglite.shared.models import TimeSeriesData, TimeSeriesPoint


@pytest.fixture
def sample_timeseries_points() -> list[TimeSeriesPoint]:
    """Fixture providing sample time series points for testing."""
    return [
        TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0, label="Jan 2024"),
        TimeSeriesPoint(date=datetime(2024, 2, 1), value=110.0, label="Feb 2024"),
        TimeSeriesPoint(date=datetime(2024, 3, 1), value=120.0, label="Mar 2024"),
    ]


@pytest.fixture
def sample_timeseries_data(sample_timeseries_points) -> TimeSeriesData:
    """Fixture providing sample TimeSeriesData for testing."""
    return TimeSeriesData(
        metric_name="revenue",
        points=sample_timeseries_points,
        interval="monthly",
        source_documents=["test.pdf"],
    )
