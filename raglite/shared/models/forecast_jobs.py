"""Async forecast job models for MCP timeout resolution.

These models enable an async job pattern that returns immediately with a job_id,
allowing the MCP client to poll for results without timing out (Claude Desktop
has a 30-second hardcoded timeout, but forecasts take ~50s).
"""

from typing import Any

from pydantic import BaseModel, Field


class AsyncForecastResponse(BaseModel):
    """Response from async forecast initiation.

    MCP Timeout Resolution: Returns immediately with job_id so the MCP client
    doesn't timeout while waiting for the ~50s forecast execution.
    """

    job_id: str = Field(..., description="Unique job identifier for status polling")
    status: str = Field(default="started", description="Initial job status ('started')")
    message: str = Field(
        ...,
        description="User-friendly message explaining how to check forecast status",
    )
    metric: str = Field(..., description="Metric being forecasted")
    periods_ahead: int = Field(..., description="Number of periods requested")


class ForecastJobStatus(BaseModel):
    """Status response for async forecast job polling.

    MCP Timeout Resolution: Allows polling for forecast job status and retrieving
    results when complete.

    Note: The result field uses Any to avoid circular import with ForecastQueryResponse.
    At runtime, this will contain a ForecastQueryResponse object when status='completed'.
    """

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(
        ...,
        description="Job status: 'pending', 'running', 'completed', or 'failed'",
    )
    progress: int | None = Field(
        default=None, description="Progress percentage (0-100) if available"
    )
    result: Any | None = Field(
        default=None, description="Forecast result (only when status='completed')"
    )
    error: str | None = Field(default=None, description="Error message (only when status='failed')")
    started_at: str | None = Field(
        default=None, description="Job start timestamp (ISO 8601 format)"
    )
    completed_at: str | None = Field(
        default=None,
        description="Job completion timestamp (ISO 8601 format, only when done)",
    )
    metric: str | None = Field(default=None, description="Metric being forecasted")
    periods_ahead: int | None = Field(default=None, description="Number of periods requested")
