"""TFT training job status tracking.

Story 6.14 AC3: Track job status for testing and monitoring.
"""

from __future__ import annotations

from typing import Any

# Test globals (shared with job_scheduler module)
_test_job_status: dict[str, Any] = {}

# Import the reference from job_scheduler to avoid duplication
# noqa: E402
from raglite.forecasting.tft_training_job.job_scheduler import _test_job_status  # noqa: E402


def get_training_job_status(job_id: str) -> dict[str, Any]:
    """Get the status of a TFT training job.

    Args:
        job_id: Unique identifier for the job

    Returns:
        Dict with job status information
    """
    status: dict[str, Any] = _test_job_status.get(job_id, {"status": "not_found"})
    return status
