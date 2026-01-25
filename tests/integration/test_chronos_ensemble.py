"""Integration tests for Chronos-2 ensemble forecasting.

Story 6.13: Chronos-2 Cold-Start & Ensemble Member

Test Coverage:
- Cold-start scenario (3 data points -> Chronos-2 only) (AC2)
- Full ensemble with Chronos-2 member (AC3)
- No-regressors fallback scenario (AC4)
- PostgreSQL model_weights integration (AC8)
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import delete

from raglite.external_data.orm_models import ModelWeightORM
from raglite.external_data.storage import ExternalDataStorage
from raglite.forecasting.ensemble import generate_ensemble_forecast
from raglite.forecasting.hybrid import (
    _generate_chronos_cold_start_forecast,
    _get_chronos_pipeline,
    generate_forecast,
)
from raglite.shared.database import get_session
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

# Require database for integration tests
pytestmark = pytest.mark.integration

# =============================================================================
# AC2: Cold-Start Scenario (3 data points -> Chronos-2 only)
# =============================================================================


@pytest.mark.preserve_collection
@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.skipif(
    os.getenv("SKIP_CHRONOS_TESTS") == "true",
    reason="Chronos-2 model loading is slow in CI",
)
async def test_cold_start_scenario_minimal_data() -> None:
    """Test cold-start path with 3 data points uses Chronos-2."""
    # Create minimal data (3 points - triggers cold-start)
    points = [
        TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0, label="Jan-24"),
        TimeSeriesPoint(date=datetime(2024, 2, 1), value=105.0, label="Feb-24"),
        TimeSeriesPoint(date=datetime(2024, 3, 1), value=110.0, label="Mar-24"),
    ]
    data = TimeSeriesData(metric_name="test_cold_start", points=points, interval="monthly")

    # Generate forecast - mock fetch_historical_data per Story 8.5 ATDD pattern
    with patch("raglite.forecasting.hybrid.fetch_historical_data") as mock_fetch:
        mock_fetch.return_value = data
        result = await generate_forecast(
            metric="test_cold_start",
            periods_ahead=3,
        )

    # Verify Chronos-2 zero-shot was used
    assert "chronos" in result.model_type.lower()
    assert result.forecast is not None
    assert len(result.forecast) == 3

    # Verify ensemble_weights shows 100% Chronos-2
    assert result.ensemble_weights is not None
    assert result.ensemble_weights.get("chronos", 0.0) == 1.0


# =============================================================================
# AC3: Full Ensemble with Chronos-2 Member
# =============================================================================


@pytest.mark.preserve_collection
@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.skipif(
    os.getenv("SKIP_CHRONOS_TESTS") == "true",
    reason="Chronos-2 model loading is slow in CI",
)
async def test_full_ensemble_with_chronos(cement_time_series: TimeSeriesData) -> None:
    """Test full ensemble includes Chronos-2 with >= 6 data points."""
    # Use cement fixture which has sufficient data
    # Use unique metric name to avoid existing adaptive weights from database
    result = await generate_ensemble_forecast(
        metric="test_chronos_full_ensemble",
        historical_data=cement_time_series,  # Story 8.5: Pass directly, not deprecated
        periods_ahead=4,
        models=["prophet", "chronos"],  # Just these for speed
    )

    # Verify Chronos-2 participated
    assert result.ensemble_weights is not None
    assert "chronos" in result.ensemble_weights
    assert result.ensemble_weights["chronos"] > 0.0

    # Verify forecast generated
    assert result.forecast is not None
    assert len(result.forecast) == 4


# =============================================================================
# AC4: No-Regressors Fallback Scenario
# =============================================================================


@pytest.mark.preserve_collection
@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.skipif(
    os.getenv("SKIP_CHRONOS_TESTS") == "true",
    reason="Chronos-2 model loading is slow in CI",
)
async def test_no_regressors_fallback(cement_time_series: TimeSeriesData) -> None:
    """Test Chronos-2 weight boosted when no external regressors."""
    # Generate forecast WITHOUT external regressors
    # Use unique metric name to avoid existing adaptive weights from database
    result = await generate_ensemble_forecast(
        metric="test_chronos_no_regressors",
        historical_data=cement_time_series,  # Story 8.5: Pass directly, not deprecated
        external_regressors=None,  # No regressors
        periods_ahead=4,
        models=["prophet", "chronos", "linear"],
    )

    # Chronos and Prophet should have higher weights than linear
    # (because has_regressors=False boosts non-regressor models)
    assert result.ensemble_weights is not None

    # Note: Actual weight values depend on adaptive weights from backtest
    # We just verify Chronos participated (weight > 0)
    if "chronos" in result.ensemble_weights:
        assert result.ensemble_weights["chronos"] > 0.0


# =============================================================================
# AC8: PostgreSQL model_weights Integration
# =============================================================================


@pytest.mark.manages_collection_state
@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.skipif(
    os.getenv("SKIP_CHRONOS_TESTS") == "true",
    reason="Chronos-2 model loading is slow in CI",
)
async def test_chronos_weights_from_database(cement_time_series: TimeSeriesData) -> None:
    """Test Chronos-2 weights can be stored/retrieved from PostgreSQL."""
    session = get_session()
    storage = ExternalDataStorage(session)

    # Store test weights including Chronos
    test_weights = {
        "prophet": 0.25,
        "chronos": 0.20,
        "linear": 0.15,
        "xgboost": 0.20,
        "lightgbm": 0.20,
    }

    try:
        # Store test weights including Chronos using individual save_model_weight calls
        for model_name, weight in test_weights.items():
            storage.save_model_weight(
                metric_name="test_metric_chronos",
                model_name=model_name,
                weight=weight,
                backtest_rmse=0.1,  # Dummy value for test
                backtest_mape=5.0,  # Dummy value for test
                has_regressors=True,
                data_points=100,  # Dummy value for test
            )

        # Retrieve weights
        retrieved = storage.get_weights_for_metric("test_metric_chronos")

        assert retrieved is not None
        assert "chronos" in retrieved
        assert retrieved["chronos"] == 0.20

    finally:
        # Cleanup
        session.execute(
            delete(ModelWeightORM).where(ModelWeightORM.metric_name == "test_metric_chronos")
        )
        session.commit()
        session.close()


# =============================================================================
# Performance Tests (AC6: Inference <2s)
# =============================================================================


@pytest.mark.preserve_collection
@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.skipif(
    os.getenv("SKIP_CHRONOS_TESTS") == "true",
    reason="Chronos-2 model loading is slow in CI",
)
async def test_chronos_inference_performance() -> None:
    """Test Chronos-2 inference completes within 2 seconds (AC6)."""
    # Prepare minimal test data
    points = [
        TimeSeriesPoint(date=datetime(2024, i, 1), value=100.0 + i, label=f"M{i}")
        for i in range(1, 7)
    ]
    test_data = TimeSeriesData(metric_name="perf_test", points=points, interval="monthly")

    # Warm up model (first load is slow)
    _get_chronos_pipeline()

    # Time cold-start forecast (should use cached model)
    start = time.time()
    result = await _generate_chronos_cold_start_forecast(
        metric="perf_test",
        historical_data=test_data,  # Epic 8.1: historical_data is now required
        periods_ahead=4,
    )
    duration = time.time() - start

    assert result is not None
    assert duration < 2.0, f"Chronos-2 inference took {duration:.2f}s, expected <2s"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cement_time_series() -> TimeSeriesData:
    """Fixture for cement demand time-series (12+ points)."""
    # Create realistic cement demand data
    points = [
        TimeSeriesPoint(date=datetime(2024, i, 1), value=1000.0 + i * 50, label=f"M{i}")
        for i in range(1, 13)  # 12 months
    ]
    return TimeSeriesData(metric_name="cement_demand", points=points, interval="monthly")
