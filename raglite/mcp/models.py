"""MCP Request/Response Models for RAGLite.

This module contains Pydantic models for MCP tool requests and responses.
Extracted from main.py as part of Story 7.4 refactoring.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


# Story 6.6: External Data Query Models
class ExternalDataQueryRequest(BaseModel):
    """Request model for external data queries."""

    source: str = Field(
        ...,
        description="Source name (e.g., 'INE_BuildingPermits', 'OMIE_Electricity') or 'all' for all sources",
    )
    date_range: str = Field(
        ...,
        description="Date range: ISO format 'YYYY-MM-DD:YYYY-MM-DD' or shortcuts 'last_30_days', 'last_year', 'last_quarter'",
    )
    metric: str | None = Field(
        None,
        description="Optional: specific metric name to filter",
    )


class ExternalDataPoint(BaseModel):
    """Single data point in response."""

    date: date
    metric_name: str
    value: float
    unit: str | None


class ExternalDataQueryResponse(BaseModel):
    """Response model for external data queries."""

    source_name: str
    data_frequency: str | None
    last_refresh: datetime | None
    data_points: list[ExternalDataPoint]
    visualization_hint: str | None
    record_count: int


# Story 6.12: Model Weight Admin Models
class ModelWeightAdminRequest(BaseModel):
    """Request model for model weight administration.

    Story 6.12 AC5: MCP admin tool for viewing/modifying model weights.
    """

    action: str = Field(
        ...,
        description="Action: 'view' (show weights), 'run_backtest' (trigger backtest), 'reset' (delete and reset to static)",
    )
    metric: str | None = Field(
        None,
        description="Optional: Filter to specific metric (e.g., 'cement_demand'). None = all metrics.",
    )


class ModelWeightAdminResponse(BaseModel):
    """Response model for model weight administration."""

    action: str
    success: bool
    message: str
    weights: list[dict] | None = None
    backtest_status: dict | None = None
