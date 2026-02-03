"""Shared fixtures for forecasting module tests.

Performance Optimization:
- Heavy dependencies imported at module level (not inside test functions)
- Prevents 5-15s import overhead per test
- Related: Strategic Analysis finding - deferred imports cause timeout issues
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import numpy as np
import pandas as pd
import pytest

# MODULE-LEVEL IMPORTS: Prevent per-test import overhead
# These imports are expensive (statsmodels, pmdarima) and should load once
# DO NOT move these inside test functions - causes 5-15s overhead per test
try:
    from raglite.forecasting.forecast_helpers import (
        generate_forecast,
        prepare_forecast_data,
    )
    from raglite.forecasting.model_selection import ModelSelectionResult

    FORECASTING_AVAILABLE = True
except ImportError:
    # Allow tests to run even if forecasting dependencies not installed
    FORECASTING_AVAILABLE = False
    ModelSelectionResult = None
    generate_forecast = None
    prepare_forecast_data = None


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


@pytest.fixture
def mock_mistral_client():
    """Mock Mistral client for classification tests.

    Prevents real API calls in unit tests.
    Returns a mock with AsyncMock for embeddings.generate().
    """
    mock_client = Mock()
    mock_client.embeddings = Mock()
    mock_client.embeddings.create = AsyncMock(
        return_value=Mock(data=[Mock(embedding=[0.1] * 1024)])
    )
    return mock_client


@pytest.fixture
def mock_claude_client():
    """Mock Claude client for synthesis tests.

    Prevents real API calls in unit tests.
    Returns a mock with messages.create() method.
    """
    mock_client = Mock()
    mock_client.messages = Mock()
    mock_client.messages.create = Mock(return_value=Mock(content=[Mock(text="Mocked response")]))
    return mock_client


@pytest.fixture
def mock_postgresql_client():
    """Mock PostgreSQL connection for storage tests.

    Prevents real database connections in unit tests.
    Returns a mock connection with cursor().
    """
    mock_cursor = Mock()
    mock_cursor.fetchone = Mock(return_value=None)
    mock_cursor.fetchall = Mock(return_value=[])
    mock_cursor.execute = Mock()

    mock_conn = Mock()
    mock_conn.cursor = Mock(return_value=mock_cursor)
    mock_conn.commit = Mock()
    mock_conn.rollback = Mock()

    return mock_conn


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for vector search tests.

    Prevents real vector database connections in unit tests.
    Returns a mock client with search() method.
    """
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_client.search = Mock(return_value=[])
    mock_client.retrieve = Mock(return_value=[])
    mock_client.upsert = Mock(return_value=Mock(status="success"))

    return mock_client
