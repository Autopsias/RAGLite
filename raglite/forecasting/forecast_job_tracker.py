"""In-memory job tracking for async forecast operations.

MCP Timeout Resolution: Claude Desktop has a 30-second hardcoded MCP client timeout,
but forecasts take ~50 seconds. This module enables an async job pattern that
returns immediately with a job_id for status polling.

Pattern mirrors ingestion/job_tracker.py for consistency.

Thread-Based Background Execution:
MCP tool calls may use different event loops between invocations. Tasks scheduled
with asyncio.create_task() are tied to the current event loop and are lost when
that loop stops. We use threading.Thread with a dedicated event loop to ensure
background jobs survive independently of MCP's event loop lifecycle.
"""

import asyncio
import threading
import uuid
from datetime import UTC, datetime

from raglite.shared.logging import get_logger
from raglite.shared.models import ForecastJobStatus, ForecastQueryRequest, ForecastQueryResponse

logger = get_logger(__name__)

# In-memory job storage
# Format: {job_id: ForecastJobStatus}
_forecast_jobs: dict[str, ForecastJobStatus] = {}


def create_forecast_job(request: ForecastQueryRequest, metric: str, periods_ahead: int) -> str:
    """Create a new async forecast job and return job ID.

    Args:
        request: Original forecast request
        metric: Validated metric name
        periods_ahead: Number of periods to forecast

    Returns:
        Unique job ID (UUID v4)
    """
    job_id = str(uuid.uuid4())

    job_status = ForecastJobStatus(
        job_id=job_id,
        status="pending",
        progress=0,
        started_at=datetime.now(UTC).isoformat(),
        metric=metric,
        periods_ahead=periods_ahead,
    )

    _forecast_jobs[job_id] = job_status

    logger.info(
        "Async forecast job created",
        extra={
            "job_id": job_id,
            "metric": metric,
            "periods_ahead": periods_ahead,
        },
    )

    return job_id


def update_forecast_job_status(
    job_id: str,
    status: str,
    progress: int | None = None,
    result: ForecastQueryResponse | None = None,
    error: str | None = None,
) -> None:
    """Update forecast job status in memory.

    Args:
        job_id: Job identifier
        status: New status ('pending', 'running', 'completed', 'failed')
        progress: Progress percentage (0-100)
        result: Forecast result (only for 'completed')
        error: Error message (only for 'failed')
    """
    if job_id not in _forecast_jobs:
        logger.warning("Attempted to update non-existent forecast job", extra={"job_id": job_id})
        return

    job = _forecast_jobs[job_id]
    job.status = status

    if progress is not None:
        job.progress = progress

    if result is not None:
        job.result = result

    if error is not None:
        job.error = error

    # Set completion timestamp for terminal states
    if status in ["completed", "failed"]:
        job.completed_at = datetime.now(UTC).isoformat()

    logger.info(
        "Forecast job status updated",
        extra={
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "has_result": result is not None,
            "has_error": error is not None,
        },
    )


def get_forecast_job_status(job_id: str) -> ForecastJobStatus | None:
    """Get current forecast job status.

    Args:
        job_id: Job identifier

    Returns:
        ForecastJobStatus or None if job not found
    """
    return _forecast_jobs.get(job_id)


async def run_async_forecast(
    job_id: str,
    request: ForecastQueryRequest,
    metric: str,
    periods_ahead: int,
) -> None:
    """Run forecast in background and update job status.

    Args:
        job_id: Job identifier for status updates
        request: Original forecast request
        metric: Validated metric name
        periods_ahead: Number of periods to forecast
    """
    # Import here to avoid circular imports
    from raglite.mcp.tools.forecast import _execute_forecast_internal

    try:
        # Update to running
        update_forecast_job_status(job_id, "running", progress=10)

        logger.info(
            "Starting async forecast",
            extra={
                "job_id": job_id,
                "metric": metric,
                "periods_ahead": periods_ahead,
            },
        )

        # Update progress as we go through stages
        update_forecast_job_status(job_id, "running", progress=30)

        # Run forecast (this takes ~50 seconds)
        response = await _execute_forecast_internal(request, metric, periods_ahead)

        # Mark as completed
        update_forecast_job_status(job_id, "completed", progress=100, result=response)

        logger.info(
            "Async forecast completed",
            extra={
                "job_id": job_id,
                "metric": metric,
                "model_type": response.model_type,
            },
        )

    except Exception as e:
        # Mark as failed
        error_msg = f"Forecast failed: {str(e)}"
        update_forecast_job_status(job_id, "failed", error=error_msg)

        logger.error(
            "Async forecast failed",
            extra={
                "job_id": job_id,
                "metric": metric,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )


def start_background_forecast(
    job_id: str,
    request: ForecastQueryRequest,
    metric: str,
    periods_ahead: int,
) -> None:
    """Start background forecast job in a SEPARATE THREAD.

    Uses threading.Thread instead of asyncio.create_task() because:
    - MCP may use different event loops between tool calls
    - Tasks scheduled on one loop are lost when that loop stops
    - A separate thread with its own event loop survives independently

    Args:
        job_id: Job identifier
        request: Original forecast request
        metric: Validated metric name
        periods_ahead: Number of periods to forecast
    """

    def run_in_thread() -> None:
        """Execute forecast in a dedicated thread with its own event loop."""
        # Create a NEW event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_async_forecast(job_id, request, metric, periods_ahead))
        except Exception as e:
            # Log any unexpected errors (run_async_forecast handles its own errors)
            logger.error(
                "Background forecast thread failed unexpectedly",
                extra={"job_id": job_id, "error": str(e)},
            )
        finally:
            loop.close()

    # Start daemon thread (won't block server shutdown)
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()

    logger.info(
        "Background forecast job started (thread-based)",
        extra={
            "job_id": job_id,
            "metric": metric,
            "periods_ahead": periods_ahead,
            "thread_name": thread.name,
        },
    )
