"""Shared fixtures for model selection cache tests."""

from datetime import datetime, timedelta

import pytest

from raglite.external_data.storage import CachedModelSelection
from raglite.shared.models import (
    ForecastPoint,
    ForecastResult,
    TimeSeriesData,
    TimeSeriesPoint,
)


@pytest.fixture
def sample_historical_data() -> TimeSeriesData:
    """Create sample time series data for testing."""
    points = [
        TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0),
        TimeSeriesPoint(date=datetime(2024, 2, 1), value=105.0),
        TimeSeriesPoint(date=datetime(2024, 3, 1), value=110.0),
        TimeSeriesPoint(date=datetime(2024, 4, 1), value=108.0),
        TimeSeriesPoint(date=datetime(2024, 5, 1), value=115.0),
        TimeSeriesPoint(date=datetime(2024, 6, 1), value=120.0),
        TimeSeriesPoint(date=datetime(2024, 7, 1), value=118.0),
        TimeSeriesPoint(date=datetime(2024, 8, 1), value=125.0),
    ]
    return TimeSeriesData(
        metric_name="test_metric",
        points=points,
        source_documents=["test_doc.pdf"],
    )


@pytest.fixture
def sample_forecast_result() -> ForecastResult:
    """Create sample forecast result for mocking."""
    return ForecastResult(
        metric_name="test_metric",
        forecast=[
            ForecastPoint(
                date=datetime(2024, 10, 1),
                value=130.0,
                lower=120.0,
                upper=140.0,
                label="2024-Q4",
            ),
        ],
        basis="Test model",
        confidence_reasoning="High confidence",
    )


@pytest.fixture
def cached_selection_with_regressors() -> CachedModelSelection:
    """Create cached model selection with regressors."""
    return CachedModelSelection(
        variable_name="revenue",
        best_model="catboost",
        best_mape=5.5,
        best_mase=0.85,
        use_regressors=True,
        regressor_list=["gdp_growth", "inflation"],
        candidate_results={},
        data_characteristics=None,
        selected_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )


@pytest.fixture
def cached_selection_without_regressors() -> CachedModelSelection:
    """Create cached model selection without regressors."""
    return CachedModelSelection(
        variable_name="sales_volume",
        best_model="chronos",
        best_mape=12.5,
        best_mase=1.24,
        use_regressors=False,
        regressor_list=[],
        candidate_results={},
        data_characteristics=None,
        selected_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )


@pytest.fixture
def expired_cached_selection() -> CachedModelSelection:
    """Create expired cached model selection."""
    return CachedModelSelection(
        variable_name="revenue",
        best_model="catboost",
        best_mape=5.5,
        best_mase=0.85,
        use_regressors=True,
        regressor_list=["gdp_growth"],
        candidate_results={},
        data_characteristics=None,
        selected_at=datetime.utcnow() - timedelta(days=10),
        expires_at=datetime.utcnow() - timedelta(days=3),  # Expired
    )
