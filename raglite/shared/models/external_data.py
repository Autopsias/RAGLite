"""External data and regressor models.

Defines models for external data sources, regressors, and async ingestion.
"""

from datetime import date as date_type

from pydantic import BaseModel, Field


class RegressorInfo(BaseModel):
    """Information about a single regressor for MCP responses.

    Story 6.22 AC2: Regressor metadata for list_available_regressors tool.

    Attributes:
        name: Regressor identifier (e.g., 'ttf_gas', 'euribor_3m')
        display_name: Human-readable name (e.g., 'TTF Natural Gas Price')
        source: Data source (e.g., 'ICE', 'ECB', 'Eurostat')
        available: Can currently fetch data
        last_refresh: Last successful fetch timestamp
        data_range: Available date range
        correlation: Correlation with metric (if requested)
        unit: Data unit (e.g., 'EUR/MWh', '%')
    """

    name: str = Field(..., description="Regressor identifier")
    display_name: str = Field(..., description="Human-readable name")
    source: str = Field(..., description="Data source")
    available: bool = Field(..., description="Can currently fetch data")
    last_refresh: str | None = Field(None, description="Last successful fetch timestamp")
    data_range: str | None = Field(None, description="Available date range")
    correlation: float | None = Field(None, description="Correlation with metric")
    unit: str | None = Field(None, description="Data unit")


class RegressorListResponse(BaseModel):
    """Response for listing available regressors via MCP.

    Story 6.22 AC2: list_available_regressors tool response.

    Attributes:
        regressors: List of available regressors
        total_count: Total number of regressors
        available_count: Number currently available (can fetch)
    """

    regressors: list[RegressorInfo] = Field(..., description="List of available regressors")
    total_count: int = Field(..., description="Total number of regressors")
    available_count: int = Field(..., description="Number currently available")


class RegressorDataPoint(BaseModel):
    """Single regressor data point for MCP responses.

    Story 6.22 AC3: Time series data point for get_regressor_data tool.

    Attributes:
        date: Date of the data point
        value: Regressor value
    """

    date: date_type = Field(..., description="Date of the data point")
    value: float = Field(..., description="Regressor value")


class RegressorDataResponse(BaseModel):
    """Response for fetching regressor data via MCP.

    Story 6.22 AC3: get_regressor_data tool response.

    Attributes:
        regressor_name: Regressor identifier
        display_name: Human-readable name
        source: Data source
        unit: Data unit
        data_points: Time series data
        record_count: Number of data points
        date_range: Actual date range returned
        visualization_hint: Suggested visualization type
    """

    regressor_name: str = Field(..., description="Regressor identifier")
    display_name: str = Field(..., description="Human-readable name")
    source: str = Field(..., description="Data source")
    unit: str | None = Field(None, description="Data unit")
    data_points: list[RegressorDataPoint] = Field(..., description="Time series data")
    record_count: int = Field(..., description="Number of data points")
    date_range: str = Field(..., description="Actual date range returned")
    visualization_hint: str | None = Field(None, description="Suggested visualization type")


# Story 4.0.3: Async ingestion models for large document processing
class AsyncIngestionRequest(BaseModel):
    """Request parameters for async document ingestion.

    Story 4.0.3 AC5: Async ingestion for large documents (150-200 pages).
    Returns immediately with job ID instead of blocking.
    """

    doc_path: str = Field(..., description="Absolute or relative path to document file")


class AsyncIngestionResponse(BaseModel):
    """Response from async document ingestion initiation.

    Story 4.0.3 AC5: Immediate response with job ID for status polling.
    """

    job_id: str = Field(..., description="Unique job identifier for status polling")
    status: str = Field(default="started", description="Initial job status ('started')")
    message: str = Field(
        ...,
        description="User-friendly message (e.g., 'Ingestion started for large-file.pdf. Use get_ingestion_status to check progress.')",
    )
    estimated_time_s: int | None = Field(
        default=None,
        description="Estimated completion time in seconds (based on page count)",
    )
