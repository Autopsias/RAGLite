"""Shared fixtures for forecasting module tests."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_time_series_data():
    """Create sample historical time series data for testing."""
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    points = []
    datetime(2023, 1, 1)
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


@pytest.fixture
def base_document_metadata():
    """Create base DocumentMetadata for auto_update tests."""
    from raglite.shared.models import DocumentMetadata

    return DocumentMetadata(
        filename="Test_Document.pdf",
        doc_type="PDF",
        ingestion_timestamp="2025-11-27T10:00:00Z",
    )


@pytest.fixture
def forecast_refresh_result_success():
    """Create successful ForecastRefreshResult for testing."""
    from raglite.shared.models import ForecastRefreshResult

    return ForecastRefreshResult(
        document_id="Q3_Report.pdf",
        metrics_refreshed=["revenue", "expenses"],
        metrics_skipped=[],
        refresh_duration_ms=1500,
        success=True,
        error_message=None,
    )


@pytest.fixture
def ingestion_result_with_forecasts():
    """Create IngestionResult with forecast updates."""
    from raglite.shared.models import IngestionResult

    return IngestionResult(
        filename="Q3_Report.pdf",
        doc_type="PDF",
        ingestion_timestamp="2025-11-27T10:00:00Z",
        page_count=40,
        source_path="/data/Q3_Report.pdf",
        chunk_count=120,
        forecasts_updated=["revenue", "expenses"],
        forecast_refresh_skipped_reason=None,
    )


@pytest.fixture
def monthly_series() -> pd.Series:
    """Create a monthly time series with 36 data points (3 years).

    Simulates financial data with trend and seasonality.
    """
    dates = pd.date_range(start="2022-01-01", periods=36, freq="MS")
    # Trend + seasonality + noise
    trend = np.linspace(100, 200, 36)
    seasonality = 20 * np.sin(np.linspace(0, 6 * np.pi, 36))
    noise = np.random.default_rng(42).normal(0, 5, 36)
    values = trend + seasonality + noise
    return pd.Series(values, index=dates, name="revenue")


@pytest.fixture
def quarterly_series() -> pd.Series:
    """Create a quarterly time series with 16 data points (4 years)."""
    dates = pd.date_range(start="2021-01-01", periods=16, freq="QS")
    # Simple trend with some noise
    trend = np.linspace(1000, 1500, 16)
    noise = np.random.default_rng(42).normal(0, 20, 16)
    values = trend + noise
    return pd.Series(values, index=dates, name="ebitda")


@pytest.fixture
def short_series() -> pd.Series:
    """Create a short time series (only 4 data points) for edge case testing."""
    dates = pd.date_range(start="2024-01-01", periods=4, freq="MS")
    values = [100, 110, 105, 115]
    return pd.Series(values, index=dates, name="metric")
