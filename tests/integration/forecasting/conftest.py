"""Shared fixtures for forecast query integration tests.

Marker Strategy:
- integration: All tests require Qdrant/PostgreSQL
- preserve_collection: Read-only tests (skip cleanup overhead)
- slow: Tests >1s (defined per-test, not in conftest.py)

Note: 'slow' marker is applied at test/class level in test files,
NOT in conftest.py pytestmark, because different tests in this
subdirectory have different performance characteristics.
"""

from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from raglite.shared.models import (
    ForecastPoint,
    ForecastResult,
    TimeSeriesData,
    TimeSeriesPoint,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Mark all tests in this subdirectory with standard integration markers
# 'slow' marker is NOT applied here - it's applied per-test based on actual duration
# Note: xdist_group removed (2025-01-19) - it was serializing 100+ tests onto single worker
# causing timeouts. Apply @pytest.mark.xdist_group to individual tests that need it.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
]


@pytest.fixture(autouse=True)
def cleanup_forecast_tables(db_session: "Session"):
    """Clean up model_selection and model_weights tables BEFORE each test.

    CRITICAL: autouse=True ensures this runs for EVERY test in forecasting/.
    Cleanup runs BEFORE yield (setup) to prevent xdist race conditions.

    Tables cleaned:
    - model_selection: Caches best model for each variable
    - model_weights: Stores ensemble weights per metric/model

    Without this cleanup, parallel tests on same xdist worker can still
    insert data faster than sequential cleanup can run.
    """
    try:
        from raglite.external_data.orm_models import ModelSelectionORM, ModelWeightORM

        # Cleanup BEFORE test (not after) - prevents race conditions
        db_session.query(ModelSelectionORM).delete()
        db_session.query(ModelWeightORM).delete()
        db_session.commit()
    except Exception:
        db_session.rollback()

    yield
    # No cleanup after - next test will clean before it runs


@pytest.fixture
def sample_quarters():
    """Standard quarters for time-series testing."""
    return [
        (2022, 1),
        (2022, 4),
        (2022, 7),
        (2022, 10),
        (2023, 1),
        (2023, 4),
        (2023, 7),
        (2023, 10),
        (2024, 1),
        (2024, 4),
    ]


@pytest.fixture
def mock_revenue_ts_data(sample_quarters):
    """Create mock time-series data for revenue."""
    return TimeSeriesData(
        metric_name="revenue",
        points=[
            TimeSeriesPoint(
                date=datetime(y, m, 1),
                value=100.0 + i * 5,
                label=f"Q{(m - 1) // 3 + 1} {y}",
            )
            for i, (y, m) in enumerate(sample_quarters)
        ],
        interval="quarterly",
        source_documents=["Q1_2024.pdf", "Q2_2024.pdf", "Annual_2023.pdf"],
    )


@pytest.fixture
def mock_revenue_forecast():
    """Create mock forecast result for revenue."""
    return ForecastResult(
        metric_name="revenue",
        historical_data=[
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=145.0),
            TimeSeriesPoint(date=datetime(2024, 4, 1), value=150.0),
        ],
        forecast=[
            ForecastPoint(
                date=datetime(2024, 7, 1),
                value=155.0,
                lower=140.0,
                upper=170.0,
                label="Q3 2024",
            ),
            ForecastPoint(
                date=datetime(2024, 10, 1),
                value=162.0,
                lower=145.0,
                upper=179.0,
                label="Q4 2024",
            ),
        ],
        confidence_reasoning="Revenue shows consistent 5% quarterly growth with narrow confidence intervals.",
        basis="Prophet model trained on 10 quarters of historical data",
        accuracy_estimate="±15% (NFR10 target)",
        periods_ahead=2,
    )
