"""Shared fixtures for model selection integration tests.

Marker Strategy:
- integration: All tests require Qdrant/PostgreSQL infrastructure
- preserve_collection: Read-only tests (skip cleanup overhead)

Purpose:
- Time series fixtures (sample_time_series, sample_regressors, etc.)
- Model selection result fixtures
- Database cleanup fixtures
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pytest

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Mark all tests in this subdirectory with standard integration markers
# xdist_group ensures all model_selection tests run on same worker (prevents database race conditions)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="database_writes"),
]


# Note: db_session fixture is now defined in tests/integration/conftest.py (parent)
# to avoid duplication across subdirectories (forecasting/catboost, model_selection, etc.)


@pytest.fixture
def sample_model_selection_result():
    """Create a sample ModelSelectionResult for testing."""
    from raglite.forecasting.model_selection import ModelSelectionResult

    return ModelSelectionResult(
        variable_name="ebitda",
        best_model="prophet",
        best_mape=5.5,
        best_mase=0.8,
        best_with_regressors=True,
        best_regressor_set=["gas_price", "euribor"],
        candidate_results={
            "prophet_True": {"mape": 5.5, "mase": 0.8},
            "prophet_False": {"mape": 6.2, "mase": 0.9},
            "xgboost_True": {"mape": 5.8, "mase": 0.85},
            "xgboost_False": {"mape": 6.5, "mase": 0.95},
        },
        data_characteristics=None,
        cv_folds=5,
        runtime_seconds=45.0,
    )


@pytest.fixture
def cleanup_model_selection(db_session: Session):
    """Clean up model_selection table before tests.

    CRITICAL: Cleanup runs BEFORE yield (setup) to prevent xdist race conditions.
    When multiple workers run in parallel, cleanup-after-test causes constraint violations
    because workers INSERT data concurrently before cleanup runs.

    By cleaning BEFORE the test, we ensure a clean slate for each test regardless of
    parallel execution order.
    """
    # Cleanup BEFORE test (not after)
    try:
        from raglite.external_data.orm_models import ModelSelectionORM

        db_session.query(ModelSelectionORM).delete()
        db_session.commit()
    except Exception:
        db_session.rollback()

    yield
    # No cleanup after test - next test will clean before it runs


# Time series fixtures for model selection tests
@pytest.fixture
def sample_time_series() -> pd.Series:
    """Generate sample monthly time series for testing (36 points = 3 years).

    Creates a realistic financial time series with trend, seasonality, and noise.
    """
    np.random.seed(42)
    dates = pd.date_range(start="2021-01-01", periods=36, freq="MS")
    # Trend + seasonality + noise (similar to financial data)
    trend = np.linspace(100, 200, 36)
    seasonality = 15 * np.sin(2 * np.pi * np.arange(36) / 12)
    noise = np.random.normal(0, 5, 36)
    values = trend + seasonality + noise
    return pd.Series(values, index=dates, name="test_variable")


@pytest.fixture
def sample_regressors(sample_time_series: pd.Series) -> dict[str, pd.Series]:
    """Generate sample external regressors aligned with time series."""
    np.random.seed(43)
    return {
        "gas_price": pd.Series(
            np.linspace(50, 80, 36) + np.random.normal(0, 2, 36),
            index=sample_time_series.index,
            name="gas_price",
        ),
        "euribor": pd.Series(
            np.linspace(0.5, 3.5, 36) + np.random.normal(0, 0.1, 36),
            index=sample_time_series.index,
            name="euribor",
        ),
    }


@pytest.fixture
def short_time_series() -> pd.Series:
    """Generate short time series (8 points) for cold-start testing."""
    dates = pd.date_range(start="2024-01-01", periods=8, freq="MS")
    values = [100, 105, 110, 108, 115, 120, 118, 125]
    return pd.Series(values, index=dates, name="short_variable")


@pytest.fixture
def minimum_time_series() -> pd.Series:
    """Generate minimum viable time series (exactly 12 points)."""
    dates = pd.date_range(start="2024-01-01", periods=12, freq="MS")
    np.random.seed(44)
    values = 100 + np.cumsum(np.random.normal(2, 5, 12))
    return pd.Series(values, index=dates, name="minimum_variable")
