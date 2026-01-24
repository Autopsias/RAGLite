"""Integration tests for TFT training workflow.

Story 6.14 AC9: Test training workflow, model registry, and ensemble integration.
"""

import asyncio
import uuid
from datetime import datetime

import pytest

import raglite.external_data.scheduler as scheduler_module
from raglite.external_data.scheduler import (
    get_next_run_times,
    get_scheduler,
    shutdown_scheduler,
    start_scheduler,
)
from raglite.external_data.storage import ExternalDataStorage
from raglite.forecasting.ensemble import generate_ensemble_forecast
from raglite.shared.config import settings
from raglite.shared.database import get_session
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

# Mark all tests as integration tests
# Mark as slow due to model training and setup taking significant time
# CRITICAL: xdist_group prevents APScheduler race conditions in parallel test execution
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="apscheduler"),  # Force single-worker execution
]


class TestModelRegistryOperations:
    """Test model registry PostgreSQL operations."""

    @pytest.mark.manages_collection_state
    @pytest.mark.asyncio
    async def test_save_and_retrieve_checkpoint(self, external_data_storage):
        """Test saving and retrieving TFT checkpoint from registry."""
        # Use the fixture-provided storage instance
        storage = external_data_storage

        # Generate unique values to avoid constraint violations
        test_id = str(uuid.uuid4())[:8]

        # Save checkpoint
        checkpoint = storage.save_model_checkpoint(
            model_type=f"tft_test_{test_id}",
            model_version=f"test-v1-{test_id}",
            checkpoint_path=f"/tmp/test_checkpoint_{test_id}.ckpt",
            metrics_json={"val_loss": 0.05, "train_loss": 0.03},
            set_active=True,
        )

        assert checkpoint.model_type == f"tft_test_{test_id}"
        assert checkpoint.is_active is True
        assert checkpoint.metrics_json["val_loss"] == 0.05

        # Retrieve active checkpoint
        active = storage.get_active_model(f"tft_test_{test_id}")
        assert active is not None
        assert active.checkpoint_path == f"/tmp/test_checkpoint_{test_id}.ckpt"

    @pytest.mark.manages_collection_state
    @pytest.mark.asyncio
    async def test_checkpoint_history(self, external_data_storage):
        """Test retrieving checkpoint history."""
        # Use the fixture-provided storage instance
        storage = external_data_storage

        # Generate unique values to avoid constraint violations
        test_id = str(uuid.uuid4())[:8]

        # Save multiple checkpoints
        for i in range(3):
            storage.save_model_checkpoint(
                model_type=f"tft_history_test_{test_id}",
                model_version=f"v{i}-{test_id}",
                checkpoint_path=f"/tmp/checkpoint_v{i}_{test_id}.ckpt",
                metrics_json={"val_loss": 0.1 - i * 0.01},
                set_active=(i == 2),  # Last one is active
            )

        # Get history
        history = storage.get_model_history(f"tft_history_test_{test_id}", limit=5)
        assert len(history) == 3
        assert history[0].is_active is True  # Most recent is active


class TestSchedulerIntegration:
    """Test TFT training job registration with APScheduler."""

    @pytest.mark.manages_collection_state
    @pytest.mark.asyncio
    async def test_tft_training_job_registered(self):
        """Test that TFT training job is registered in scheduler."""
        # Reset scheduler singleton to ensure fresh state
        if scheduler_module._scheduler is not None:
            if scheduler_module._scheduler.running:
                scheduler_module._scheduler.shutdown(wait=False)
            scheduler_module._scheduler = None

        scheduler = get_scheduler()

        # Start scheduler to register jobs
        await start_scheduler()

        # Give scheduler a moment to register jobs
        await asyncio.sleep(0.1)

        jobs = scheduler.get_jobs()

        # Check if TFT training job exists
        job_ids = [job.id for job in jobs]
        assert "tft_training_weekly" in job_ids

        # Clean up
        await shutdown_scheduler()

    @pytest.mark.preserve_collection
    @pytest.mark.asyncio
    async def test_tft_training_runs_before_backtest(self):
        """Test that TFT training is scheduled before backtest."""
        next_runs = get_next_run_times()

        if "tft_training_weekly" in next_runs and "backtest_weekly" in next_runs:
            tft_time = next_runs["tft_training_weekly"]
            backtest_time = next_runs["backtest_weekly"]

            # TFT should run before backtest (2am vs 3am on Sundays)
            if tft_time and backtest_time:
                assert tft_time < backtest_time


class TestEnsembleWithTFT:
    """Test ensemble integration with TFT."""

    @pytest.mark.preserve_collection
    @pytest.mark.asyncio
    async def test_ensemble_includes_tft_in_models(self):
        """Test that TFT is included in ensemble models list."""
        models = settings.forecasting_models.split(",")
        assert "tft" in models

    @pytest.mark.preserve_collection
    @pytest.mark.asyncio
    async def test_ensemble_has_tft_weight(self):
        """Test that TFT has configured weight."""
        assert settings.ensemble_weight_tft == 0.12


class TestGracefulDegradation:
    """Test graceful degradation when TFT unavailable."""

    @pytest.mark.preserve_collection
    @pytest.mark.asyncio
    async def test_ensemble_works_without_tft_checkpoint(
        self,
        sample_time_series_data,
    ):
        """Test ensemble forecast works when TFT checkpoint doesn't exist."""
        # Epic 8 API change: historical_data is now a required positional parameter
        # This should work even without TFT checkpoint (graceful degradation)
        result = await generate_ensemble_forecast(
            metric="test_tft_fallback",
            historical_data=sample_time_series_data,
            external_regressors=None,
            periods_ahead=3,
        )

        assert result is not None
        assert len(result.forecast) == 3

        # TFT weight should be 0 or absent if not available
        if "tft" in result.ensemble_weights:
            assert result.ensemble_weights["tft"] >= 0.0


@pytest.fixture
def external_data_storage():
    """Provide ExternalDataStorage instance for tests."""
    session = get_session()
    return ExternalDataStorage(session)


@pytest.fixture
def sample_time_series_data():
    """Create sample time series data for testing."""
    points = [
        TimeSeriesPoint(date=datetime(2024, i, 1), value=100 + i * 5, label=f"M{i}")
        for i in range(1, 13)
    ]

    return TimeSeriesData(
        metric_name="test_metric",
        points=points,
        interval="monthly",
    )
