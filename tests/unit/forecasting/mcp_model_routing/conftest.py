"""Shared fixtures for MCP Model Routing tests."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest


@pytest.fixture
def sample_time_series_data():
    """Create sample historical time series data for testing."""
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    points = []
    value = 100.0

    for i in range(24):  # 24 months of data
        month = (i % 12) + 1
        year = 2023 + (i // 12)
        date = datetime(year, month, 1)
        points.append(TimeSeriesPoint(date=date, value=value))
        value *= 1.02  # 2% monthly growth

    return TimeSeriesData(
        metric_name="ebitda",
        points=points,
        interval="monthly",
        source_documents=["test.pdf"],
    )


@pytest.fixture
def mock_cached_model_selection():
    """Create mock cached model selection result."""
    from raglite.external_data.storage import CachedModelSelection

    now = datetime.utcnow()
    return CachedModelSelection(
        variable_name="ebitda",
        best_model="arima",
        best_mape=5.5,
        best_mase=0.8,
        use_regressors=True,
        regressor_list=["gas_price", "euribor"],
        candidate_results={"arima_True": {"mape": 5.5, "mase": 0.8}},
        data_characteristics={
            "trend": "linear",
            "seasonality": "yearly",
            "model_rationale": "ARIMA selected: data is difference-stationary (ADF p=0.02)",
        },
        selected_at=now,
        expires_at=now + timedelta(days=7),
    )
