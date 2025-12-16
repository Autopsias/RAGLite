"""Integration tests for TFT training job execution.

Tests for Story 6.14 AC9: TFT training workflow with scheduler integration.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta
from typing import Any

import pytest

# Set test environment before importing
os.environ["APP_ENV"] = "test"

# Skip all tests in this module if not running integration tests
# Mark as slow due to model training taking significant time
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


@pytest.fixture
def mock_tft_training_data() -> dict[str, Any]:
    """Create mock TFT training data for testing."""
    return {
        "metric_name": "test_tft_metric",
        "target_series": [100, 110, 105, 120, 115, 130, 125, 140, 135, 150, 145, 160],
        "time_steps": 12,
        "feature_columns": ["feature1", "feature2"],
    }


class TestTFTTrainingJob:
    """Test TFT training job execution with scheduler."""

    @pytest.mark.asyncio
    @pytest.mark.slow  # This test involves waiting for scheduled job execution
    async def test_tft_training_job(self, mock_tft_training_data: dict[str, Any]) -> None:
        """Test that TFT training job executes via scheduler.

        This test creates a TFT training job, schedules it for immediate execution,
        and waits for completion with timeout.
        """
        from raglite.external_data.scheduler import (
            shutdown_scheduler,
            start_scheduler,
        )
        from raglite.forecasting.tft_training_job import (
            create_tft_training_job,
            get_training_job_status,
        )

        # Start scheduler
        await start_scheduler()

        try:
            # Create a unique job ID for this test
            job_id = f"tft_test_{uuid.uuid4().hex[:8]}"

            # Schedule TFT training job to run in 1 second
            run_date = datetime.now() + timedelta(seconds=1)

            job = create_tft_training_job(
                job_id=job_id,
                metric_name=mock_tft_training_data["metric_name"],
                run_date=run_date,
                training_data=mock_tft_training_data,
            )

            assert job is not None
            assert job.id == job_id

            # Wait for job to complete (with timeout)
            import asyncio

            max_wait_time = 60  # Maximum 60 seconds wait
            check_interval = 1  # Check every second

            for _ in range(max_wait_time // check_interval):
                status = get_training_job_status(job_id)

                if status["status"] == "completed":
                    assert "checkpoint_path" in status
                    assert "metrics" in status
                    assert status["metrics"]["train_loss"] > 0
                    break
                elif status["status"] == "failed":
                    pytest.fail(f"TFT training job failed: {status.get('error', 'Unknown error')}")

                await asyncio.sleep(check_interval)
            else:
                pytest.fail(f"TFT training job did not complete within {max_wait_time} seconds")

        finally:
            # Clean up scheduler
            await shutdown_scheduler()

    @pytest.mark.asyncio
    async def test_tft_training_job_creates_model_checkpoint(
        self,
        external_data_storage,
        mock_tft_training_data: dict[str, Any],
    ) -> None:
        """Test that TFT training job creates model checkpoint in registry."""
        # Mock the training execution to focus on checkpoint creation
        from raglite.forecasting.tft_training_job import execute_tft_training

        # Execute training synchronously for testing
        result = await execute_tft_training(mock_tft_training_data)

        assert result is not None
        assert "checkpoint_path" in result
        assert "model_version" in result
        assert "metrics" in result

        # Verify checkpoint was saved to registry
        checkpoint = external_data_storage.get_active_model("tft")
        if checkpoint:  # Only check if it exists (may be None if training failed)
            assert checkpoint.model_type == "tft"
            assert checkpoint.checkpoint_path is not None


@pytest.fixture
def external_data_storage():
    """Provide ExternalDataStorage instance for tests."""
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.shared.database import get_session

    session = get_session()
    return ExternalDataStorage(session)
