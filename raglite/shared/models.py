"""Pydantic data models for RAGLite.

Defines core data structures used across ingestion and retrieval modules.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Metadata for ingested financial documents.

    Tracks document provenance and ingestion details for source attribution.
    """

    filename: str = Field(..., description="Original document filename")
    doc_type: str = Field(..., description="Document type (PDF, Excel)")
    ingestion_timestamp: str = Field(..., description="ISO8601 timestamp of ingestion")
    page_count: int = Field(default=0, description="Number of pages/sheets in document")
    source_path: str = Field(default="", description="Original file path")
    chunk_count: int = Field(default=0, description="Number of chunks created from document")

    @property
    def document_id(self) -> str:
        """Document identifier (alias for filename for backward compatibility)."""
        return self.filename


class BatchIngestionResult(BaseModel):
    """Results from parallel batch document ingestion.

    Story 5.0.6 AC1: Tracks success/failure counts and per-document results
    for parallel ingestion operations.
    """

    total_documents: int = Field(..., description="Total documents processed")
    successful: int = Field(..., description="Number of successfully ingested documents")
    failed: int = Field(..., description="Number of failed ingestions")
    duration_seconds: float = Field(..., description="Total batch processing time in seconds")
    results: list[DocumentMetadata] = Field(
        default_factory=list, description="Metadata for successfully ingested documents"
    )
    errors: list[dict[str, str]] = Field(
        default_factory=list,
        description="Error details for failed documents (filename, error message)",
    )


class ExtractedMetadata(BaseModel):
    """LLM-extracted business context metadata from financial documents.

    Story 2.4 REVISION (Option B - Full Rich Schema): Expanded from 3 to 15 fields
    based on industry research (INEXDA, FinRAG EMNLP 2024, RAF ACL 2025) showing
    20-25% accuracy gains for rich metadata schemas in financial document RAG.

    References:
    - INEXDA metadata schema (Bank for International Settlements)
    - FinRAG: Metadata-driven retrieval for financial analysis (EMNLP 2024)
    - RAF: Retrieval-Augmented Forecasting with tabular time series (ACL 2025)
    - KX, Deasy Labs, deepset production case studies

    All fields are optional as extraction may not find all information.
    """

    # ===== Document-Level Metadata (7 fields) =====
    document_type: str | None = Field(
        default=None,
        description="Document type: Income Statement, Balance Sheet, Cash Flow Statement, "
        "Operational Report, Earnings Call, Management Discussion, Financial Notes",
    )
    reporting_period: str | None = Field(
        default=None,
        description="Reporting period: Q1 2024, Aug-25 YTD, FY 2023, 2024 Annual, H1 2025",
    )
    time_granularity: str | None = Field(
        default=None,
        description="Time granularity: Daily, Weekly, Monthly, Quarterly, YTD, Annual, Rolling 12-Month",
    )
    company_name: str | None = Field(
        default=None,
        description="Company name: Portugal Cement, CIMPOR, Cimpor Trading, InterCement",
    )
    geographic_jurisdiction: str | None = Field(
        default=None,
        description="Geographic region: Portugal, EU, APAC, Americas, Global",
    )
    data_source_type: str | None = Field(
        default=None,
        description="Data source: Audited, Internal Report, Regulatory Filing, Management Estimate, Preliminary",
    )
    version_date: str | None = Field(
        default=None,
        description="Document version date: 2025-08-15, 2024-Q3-Final, 2024-12-31-Revised",
    )

    # ===== Chunk/Section-Level Metadata (5 fields) =====
    section_type: str | None = Field(
        default=None,
        description="Content type: Narrative, Table, Footnote, Chart Caption, Summary, List, Formula",
    )
    metric_category: str | None = Field(
        default=None,
        description="Financial metric category: Revenue, EBITDA, Operating Expenses, Capital Expenditure, "
        "Cash Flow, Assets, Liabilities, Equity, Ratios, Production Volume, Cost per Unit",
    )
    units: str | None = Field(
        default=None,
        description="Units of measure: EUR, USD, GBP, EUR/ton, USD/MWh, Percentage, Count, Tonnes, MWh, m³",
    )
    department_scope: str | None = Field(
        default=None,
        description="Department: Operations, Finance, Production, Sales, Corporate, HR, IT, Supply Chain",
    )

    # ===== Table-Specific Metadata (3 fields) =====
    table_context: str | None = Field(
        default=None,
        description="LLM-generated description of table purpose, structure, and key insights. "
        "Example: 'Variable costs breakdown by category showing thermal energy, electricity, "
        "raw materials, and packaging costs with EUR/ton units for Aug-25 YTD period'",
    )
    table_name: str | None = Field(
        default=None,
        description="Table title or name: Variable Costs Summary, EBITDA Breakdown by Segment, "
        "Balance Sheet - Assets, Cash Flow Statement - Operating Activities",
    )
    statistical_summary: str | None = Field(
        default=None,
        description="Statistical summary for numerical tables: Mean=5.8, StdDev=1.2, Min=3.5, Max=61.4, "
        "Trend=Increasing 15% YoY",
    )


class Chunk(BaseModel):
    """Document chunk with content and metadata.

    Represents a semantic chunk of a document after chunking and embedding.
    Simplified in Story 2.3 to use fixed 512-token chunking (no element-aware metadata).

    Story 2.4 REVISION (Option B - Full Rich Schema): Expanded from 3 to 15 metadata fields
    based on industry research showing 20-25% accuracy gains for rich metadata in financial RAG.

    Attributes:
        chunk_id: Unique chunk identifier
        content: Chunk text content
        metadata: Parent document metadata
        page_number: Page number where chunk appears
        chunk_index: Sequential chunk index (0-based)
        embedding: Semantic embedding vector
        parent_chunk_id: Reference to parent chunk for summaries
        word_count: Word count of chunk content

        [15 Rich Metadata Fields - Story 2.4 REVISION]
        Document-Level (7):
            document_type, reporting_period, time_granularity, company_name,
            geographic_jurisdiction, data_source_type, version_date
        Section-Level (5):
            section_type, metric_category, units, department_scope
        Table-Specific (3):
            table_context, table_name, statistical_summary
    """

    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk text content")
    metadata: DocumentMetadata = Field(..., description="Parent document metadata")
    page_number: int = Field(default=0, description="Page number where chunk appears")
    chunk_index: int = Field(default=0, description="Sequential chunk index (0-based)")
    embedding: list[float] = Field(default_factory=list, description="Semantic embedding vector")
    parent_chunk_id: str | None = Field(
        default=None, description="Reference to parent chunk (for table summaries)"
    )
    word_count: int = Field(default=0, description="Word count of chunk content")

    # Story 2.4 REVISION: Full Rich Schema (15 fields) - matches ExtractedMetadata model
    # Document-Level Metadata (7 fields)
    document_type: str | None = Field(default=None, description="Document type")
    reporting_period: str | None = Field(default=None, description="Reporting period")
    time_granularity: str | None = Field(default=None, description="Time granularity")
    company_name: str | None = Field(default=None, description="Company name")
    geographic_jurisdiction: str | None = Field(default=None, description="Geographic region")
    data_source_type: str | None = Field(default=None, description="Data source type")
    version_date: str | None = Field(default=None, description="Document version date")

    # Section-Level Metadata (5 fields)
    section_type: str | None = Field(default=None, description="Content type")
    metric_category: str | None = Field(default=None, description="Financial metric category")
    units: str | None = Field(default=None, description="Units of measure")
    department_scope: str | None = Field(default=None, description="Department scope")

    # Table-Specific Metadata (3 fields)
    table_context: str | None = Field(default=None, description="Table description")
    table_name: str | None = Field(default=None, description="Table title/name")
    statistical_summary: str | None = Field(default=None, description="Statistical summary")


class SearchResult(BaseModel):
    """Vector search result with score and source.

    Returned from Qdrant vector similarity search.
    """

    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    chunk: Chunk = Field(..., description="Retrieved chunk with content and metadata")
    source_citation: str = Field(default="", description="Formatted citation string")


class QueryResult(BaseModel):
    """Vector search result for natural language queries.

    Represents a document chunk retrieved from Qdrant similarity search
    with relevance score and full metadata for source attribution.

    Story 5.0.6 AC5: Added optional metadata field for query-time enrichment.
    """

    score: float = Field(
        ...,
        le=1.0,
        description="Relevance score (typically 0-1, but BM25 hybrid can be negative)",
    )
    text: str = Field(..., description="Chunk text content")
    source_document: str = Field(..., description="Source document filename")
    page_number: int | None = Field(
        ..., description="Page number where chunk appears (None if missing)"
    )
    chunk_index: int = Field(..., description="Sequential chunk index (0-based)")
    word_count: int = Field(..., description="Word count of chunk")
    metadata: ExtractedMetadata | None = Field(
        default=None,
        description="LLM-extracted rich metadata (Story 5.0.6 AC5). "
        "Populated by query-time enrichment when enabled. None if not enriched or extraction failed.",
    )


class QueryRequest(BaseModel):
    """Natural language query request parameters."""

    query: str = Field(..., description="Natural language query string")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")


class QueryResponse(BaseModel):
    """Natural language query response with results."""

    results: list[QueryResult] = Field(..., description="Retrieved chunks sorted by relevance")
    query: str = Field(..., description="Original query string")
    retrieval_time_ms: float = Field(..., description="Retrieval time in milliseconds")


class AnalyticalQueryRequest(BaseModel):
    """Analytical query request for multi-step workflow orchestration (Story 3.5 AC7)."""

    query: str = Field(
        ...,
        max_length=1000,
        description="Natural language analytical query string (max 1000 characters)",
    )
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results per retrieval step")


class AnalyticalQueryResponse(BaseModel):
    """Analytical query response with workflow orchestration metadata (Story 3.5 AC7).

    Story 3.6 EXTENSION (AC4, AC6):
    - reasoning_steps: Transparent workflow steps showing what the system did
    - sources: Source documents with citations for answer verification
    """

    answer: str = Field(..., description="Synthesized natural language answer")
    complexity: str = Field(..., description="Query complexity: 'simple' or 'analytical'")
    workflow_metadata: dict[str, Any] = Field(
        ...,
        description=(
            "Workflow execution metadata including task_count, execution_time_ms, "
            "workflow_pattern, and fallback_tier"
        ),
    )
    confidence: str = Field(..., description="Answer confidence: 'high', 'medium', or 'low'")
    limitations: list[str] = Field(
        default_factory=list, description="Limitations or caveats about the answer"
    )

    # Story 3.6 AC4: Reasoning steps for transparency
    reasoning_steps: list[str] = Field(
        default_factory=list,
        description=(
            "Transparent workflow steps taken (e.g., '1. Retrieved 5 documents...', "
            "'2. Analysis Agent calculated 20% YoY growth...', '3. Synthesized answer...')"
        ),
    )

    # Story 3.6 AC6: Source citations for verification
    sources: list[str] = Field(
        default_factory=list,
        description="Source documents with page references (e.g., 'Q3_2023_Report.pdf (page 12)')",
    )


# Story 3.7: AC5 - Workflow metrics tracking for degradation monitoring
class WorkflowMetrics(BaseModel):
    """Workflow execution metrics for degradation tier tracking (AC5).

    These metrics enable monitoring dashboards (Epic 5) and workflow optimization.
    Target rates: Tier 1 ≥95%, Tier 2 <5%, Tier 3 <1%, Tier 4 <0.1%
    """

    query_id: str = Field(..., description="Unique query identifier for correlation")
    query: str = Field(..., description="Original user query (for debugging)")
    tier: str = Field(
        ...,
        description=(
            "Fallback tier: 'full_orchestration', 'partial_analysis', "
            "'retrieval_only', or 'epic1_fallback'"
        ),
    )
    confidence: str = Field(
        ..., description="Answer confidence: 'high', 'medium', 'low', or 'none'"
    )
    execution_time_ms: int = Field(..., description="Total workflow execution time in milliseconds")
    agents_invoked: list[str] = Field(
        default_factory=list,
        description="List of agents invoked (e.g., ['retrieval', 'analysis'])",
    )
    agents_failed: list[str] = Field(
        default_factory=list,
        description="List of agents that failed (e.g., ['synthesis'] for Tier 2)",
    )
    error_type: str | None = Field(
        default=None,
        description="Error type if workflow failed: 'timeout', 'connection', 'api_failure', or 'unexpected'",
    )
    timestamp: str = Field(..., description="Timestamp of workflow execution (ISO 8601 format)")


# Type alias for job identifiers (used in ingestion pipeline)
JobID = str


# Story 4.1: Time-series data extraction models for forecasting
class TimeSeriesPoint(BaseModel):
    """Single data point in a time series.

    Story 4.1 AC2: Data points extracted with timestamps and metric labels.

    Attributes:
        date: Datetime of the data point
        value: Numeric value for the metric
        label: Optional label like "Q3 2024" or "Jan 2024"
    """

    date: datetime = Field(..., description="Datetime of the data point")
    value: float = Field(..., description="Numeric value for the metric")
    label: str | None = Field(default=None, description="Optional label like 'Q3 2024'")


class TimeSeriesData(BaseModel):
    """Time series data for a financial metric.

    Story 4.1 AC1-AC4: Collection of time series data points with metadata.

    Attributes:
        metric_name: Name of the metric (revenue, expenses, ebitda, etc.)
        points: List of TimeSeriesPoint objects sorted by date
        interval: Time interval: "raw", "monthly", "quarterly", "yearly"
        source_documents: List of source document filenames
    """

    metric_name: str = Field(..., description="Name of the financial metric")
    points: list[TimeSeriesPoint] = Field(
        default_factory=list, description="Data points sorted by date"
    )
    interval: str = Field(
        default="raw",
        description="Time interval: 'raw', 'monthly', 'quarterly', 'yearly'",
    )
    source_documents: list[str] = Field(
        default_factory=list, description="Source document filenames"
    )


# Story 4.2: Forecasting engine models for Prophet + LLM hybrid approach
class ForecastPoint(BaseModel):
    """Single forecast data point with confidence interval.

    Story 4.2 AC3: Forecast predictions with confidence intervals (FR19).

    Attributes:
        date: Datetime of the forecast point
        value: Predicted value (yhat from Prophet)
        lower: Lower bound of confidence interval (yhat_lower)
        upper: Upper bound of confidence interval (yhat_upper)
        label: Optional label like "Q1 2025" for display
    """

    date: datetime = Field(..., description="Datetime of the forecast point")
    value: float = Field(..., description="Predicted value (yhat)")
    lower: float = Field(..., description="Lower confidence interval (yhat_lower)")
    upper: float = Field(..., description="Upper confidence interval (yhat_upper)")
    label: str | None = Field(default=None, description="Optional label like 'Q1 2025'")


class ForecastResult(BaseModel):
    """Complete forecast result with predictions and reasoning.

    Story 4.2 AC1-AC7: Hybrid forecasting output combining Prophet predictions
    with LLM-generated reasoning and confidence rationale.

    Attributes:
        metric_name: Name of forecasted metric (revenue, cash_flow, expenses)
        historical_data: Original time-series input data
        forecast: List of ForecastPoint predictions
        confidence_reasoning: LLM-generated explanation of confidence intervals
        basis: Description of forecast basis (e.g., "Prophet model trained on 8 quarters")
        accuracy_estimate: Expected accuracy (e.g., "±15% per NFR10")
        periods_ahead: Number of periods forecasted
    """

    metric_name: str = Field(..., description="Name of forecasted metric")
    historical_data: list[TimeSeriesPoint] = Field(
        default_factory=list, description="Original time-series input data"
    )
    forecast: list[ForecastPoint] = Field(
        default_factory=list,
        description="Forecast predictions with confidence intervals",
    )
    confidence_reasoning: str = Field(
        default="", description="LLM-generated explanation of confidence intervals"
    )
    basis: str = Field(
        default="",
        description="Forecast basis (e.g., 'Prophet model trained on 8 quarters')",
    )
    accuracy_estimate: str = Field(default="±15%", description="Expected accuracy per NFR10")
    periods_ahead: int = Field(default=4, description="Number of periods forecasted")


# Story 4.3: Automated forecast updates models
class ForecastRefreshResult(BaseModel):
    """Result of automatic forecast refresh after document ingestion.

    Story 4.3 AC1/AC4: Returned from trigger_forecast_refresh() and included
    in MCP ingestion response to notify users of updated forecasts.

    Attributes:
        document_id: Identifier of the ingested document that triggered refresh
        metrics_refreshed: List of metrics successfully refreshed (e.g., ["revenue"])
        metrics_skipped: List of metrics skipped with reasons (e.g., ["expenses: insufficient data"])
        refresh_duration_ms: Time taken for forecast refresh in milliseconds
        success: Whether refresh completed successfully (partial success = True)
        error_message: Error details if refresh failed completely
    """

    document_id: str = Field(..., description="Document ID that triggered the refresh")
    metrics_refreshed: list[str] = Field(
        default_factory=list, description="Metrics successfully refreshed"
    )
    metrics_skipped: list[str] = Field(
        default_factory=list, description="Metrics skipped with reasons"
    )
    refresh_duration_ms: int = Field(..., description="Refresh duration in milliseconds")
    success: bool = Field(..., description="Whether refresh completed successfully")
    error_message: str | None = Field(default=None, description="Error message if failed")


class IngestionResult(BaseModel):
    """Extended ingestion result with forecast refresh status.

    Story 4.3 AC4: MCP ingestion response enriched with forecast update status.
    Extends DocumentMetadata with forecast-related fields.

    Attributes:
        filename: Original document filename
        doc_type: Document type (PDF, Excel)
        ingestion_timestamp: ISO8601 timestamp of ingestion
        page_count: Number of pages/sheets in document
        source_path: Original file path
        chunk_count: Number of chunks created from document
        forecasts_updated: List of metrics refreshed after ingestion (None if disabled)
        forecast_refresh_skipped_reason: Reason why forecast refresh was skipped (if applicable)
    """

    # DocumentMetadata fields
    filename: str = Field(..., description="Original document filename")
    doc_type: str = Field(..., description="Document type (PDF, Excel)")
    ingestion_timestamp: str = Field(..., description="ISO8601 timestamp of ingestion")
    page_count: int = Field(default=0, description="Number of pages/sheets in document")
    source_path: str = Field(default="", description="Original file path")
    chunk_count: int = Field(default=0, description="Number of chunks created from document")

    # Story 4.3 AC4: Forecast refresh fields
    forecasts_updated: list[str] | None = Field(
        default=None,
        description="List of metrics refreshed after ingestion (e.g., ['revenue', 'expenses'])",
    )
    forecast_refresh_skipped_reason: str | None = Field(
        default=None,
        description="Reason why forecast refresh was skipped (e.g., 'disabled', 'timeout')",
    )

    @classmethod
    def from_metadata(
        cls,
        metadata: "DocumentMetadata",
        forecasts_updated: list[str] | None = None,
        forecast_refresh_skipped_reason: str | None = None,
    ) -> "IngestionResult":
        """Create IngestionResult from DocumentMetadata with forecast fields.

        Args:
            metadata: Document metadata from ingestion
            forecasts_updated: List of refreshed metrics
            forecast_refresh_skipped_reason: Reason if refresh was skipped

        Returns:
            IngestionResult with all fields populated
        """
        return cls(
            filename=metadata.filename,
            doc_type=metadata.doc_type,
            ingestion_timestamp=metadata.ingestion_timestamp,
            page_count=metadata.page_count,
            source_path=metadata.source_path,
            chunk_count=metadata.chunk_count,
            forecasts_updated=forecasts_updated,
            forecast_refresh_skipped_reason=forecast_refresh_skipped_reason,
        )


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


class IngestionJobStatus(BaseModel):
    """Status response for async ingestion job polling.

    Story 4.0.3 AC5: Status polling for async ingestion jobs.
    """

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(
        ...,
        description="Job status: 'pending', 'in_progress', 'completed', or 'failed'",
    )
    progress: int | None = Field(
        default=None, description="Progress percentage (0-100) if available"
    )
    result: DocumentMetadata | None = Field(
        default=None, description="Ingestion result (only when status='completed')"
    )
    error: str | None = Field(default=None, description="Error message (only when status='failed')")
    started_at: str | None = Field(
        default=None, description="Job start timestamp (ISO 8601 format)"
    )
    completed_at: str | None = Field(
        default=None,
        description="Job completion timestamp (ISO 8601 format, only when done)",
    )


# Story 4.4: Forecast Query Tool MCP models
class ForecastQueryRequest(BaseModel):
    """Request for financial forecast query via MCP.

    Story 4.4 AC1: MCP tool parameters for forecast queries.
    Story 5.0.1 Enhancement: Supports SQL-based extraction for any metric in database.
    Supports both structured parameters and natural language queries.

    Attributes:
        metric: Metric to forecast (e.g., revenue, turnover, ebitda, cash_flow, expenses, capex).
                Accepts any financial metric name - will search database via SQL and documents via hybrid search.
        periods_ahead: Number of quarters to forecast (1-8, default 4).
        query: Optional natural language query (e.g., "turnover forecast next quarter").
    """

    metric: str | None = Field(
        default=None,
        description="Metric to forecast: revenue, turnover, cash_flow, expenses, ebitda, capex, or any financial metric name",
    )
    periods_ahead: int = Field(
        default=4,
        ge=1,
        le=8,
        description="Number of quarters to forecast (1-8)",
    )
    query: str | None = Field(
        default=None,
        description="Optional natural language query (e.g., 'revenue forecast next quarter')",
    )


class ForecastQueryResponse(BaseModel):
    """Response for financial forecast query via MCP.

    Story 4.4 AC2/AC3: Forecast results with confidence intervals and explanations.

    Attributes:
        metric_name: Name of forecasted metric.
        forecast: List of ForecastPoint predictions with confidence intervals.
        basis: Description of historical data used for forecast.
        confidence_reasoning: LLM-generated explanation of forecast confidence.
        methodology: Forecasting methodology description.
        accuracy_estimate: Expected forecast accuracy (±15% per NFR10).
        source_documents: Documents used for time-series data extraction.
        periods_ahead: Number of periods forecasted.
    """

    metric_name: str = Field(..., description="Name of forecasted metric")
    forecast: list[ForecastPoint] = Field(
        default_factory=list,
        description="Forecast predictions with confidence intervals",
    )
    basis: str = Field(
        ...,
        description="Description of historical data used for forecast",
    )
    confidence_reasoning: str = Field(
        default="",
        description="LLM-generated explanation of forecast confidence",
    )
    methodology: str = Field(
        default="Prophet + Mistral Large hybrid forecasting",
        description="Forecasting methodology description",
    )
    accuracy_estimate: str = Field(
        default="±15% (NFR10 target)",
        description="Expected forecast accuracy",
    )
    source_documents: list[str] = Field(
        default_factory=list,
        description="Documents used for time-series data extraction",
    )
    periods_ahead: int = Field(..., description="Number of periods forecasted")

    @classmethod
    def from_forecast_result(
        cls,
        result: "ForecastResult",
        source_documents: list[str] | None = None,
    ) -> "ForecastQueryResponse":
        """Create ForecastQueryResponse from ForecastResult.

        Story 4.4 AC2/AC3: Factory method for MCP response creation.

        Args:
            result: ForecastResult from generate_forecast()
            source_documents: List of source document filenames

        Returns:
            ForecastQueryResponse with all fields populated
        """
        return cls(
            metric_name=result.metric_name,
            forecast=result.forecast,
            basis=result.basis,
            confidence_reasoning=result.confidence_reasoning,
            methodology="Prophet + Mistral Large hybrid forecasting",
            accuracy_estimate=result.accuracy_estimate,
            source_documents=source_documents or [],
            periods_ahead=result.periods_ahead,
        )


# Story 4.5: Anomaly detection models
class AnomalySeverity(str, Enum):
    """Severity levels for detected anomalies.

    Story 4.5 AC3: Anomaly severity scoring based on Z-score thresholds.
    - CRITICAL: |z| > 3.0 - Extreme outlier requiring immediate attention
    - MODERATE: |z| > 2.0 - Significant deviation from expected values
    - MINOR: |z| > 1.5 - Small deviation, may indicate emerging trend
    """

    MINOR = "minor"
    MODERATE = "moderate"
    CRITICAL = "critical"


class Anomaly(BaseModel):
    """Detected anomaly in financial time-series data.

    Story 4.5 AC2/AC4: Anomaly with full context for analysis and reporting.

    Attributes:
        date: Date/period of the anomaly (e.g., "2024-Q3", "Jan 2024")
        metric: Name of the financial metric
        value: Actual observed value
        expected_value: Expected value based on historical mean
        z_score: Standard deviations from mean (negative = below mean)
        severity: Severity level based on Z-score thresholds
        reason: LLM-generated explanation of the anomaly
        magnitude_pct: Percentage deviation from expected value
    """

    date: str = Field(..., description="Date/period of anomaly (e.g., '2024-Q3')")
    metric: str = Field(..., description="Name of the financial metric")
    value: float = Field(..., description="Actual observed value")
    expected_value: float = Field(..., description="Expected value based on mean")
    z_score: float = Field(..., description="Standard deviations from mean")
    severity: AnomalySeverity = Field(..., description="Anomaly severity level")
    reason: str = Field(default="", description="LLM-generated explanation")
    magnitude_pct: float = Field(
        default=0.0,
        description="Percentage deviation from expected ((value-expected)/expected * 100)",
    )


class AnomalyDetectionResult(BaseModel):
    """Result of anomaly detection analysis.

    Story 4.5 AC1: Complete anomaly detection result with metadata.

    Attributes:
        metric_name: Name of the analyzed metric
        anomalies: List of detected Anomaly objects
        data_points_analyzed: Number of data points processed
        detection_method: Statistical method used for detection
        mean_value: Mean of analyzed data
        std_deviation: Standard deviation of analyzed data
    """

    metric_name: str = Field(..., description="Name of analyzed metric")
    anomalies: list[Anomaly] = Field(
        default_factory=list,
        description="List of detected anomalies",
    )
    data_points_analyzed: int = Field(..., description="Number of data points processed")
    detection_method: str = Field(
        default="Z-score analysis (threshold: |z| > 2)",
        description="Statistical method used for detection",
    )
    mean_value: float = Field(default=0.0, description="Mean of analyzed data")
    std_deviation: float = Field(default=0.0, description="Standard deviation of data")


# Story 4.6: Trend analysis and pattern recognition models
class TrendDirection(str, Enum):
    """Direction of detected trend.

    Story 4.6 AC3: Trend direction characterization.

    - INCREASING: Growth > 5% (CAGR threshold)
    - DECREASING: Growth < -5% (CAGR threshold)
    - STABLE: -5% <= growth <= 5%
    - CYCLICAL: Seasonal pattern detected (reserved for future)
    """

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    CYCLICAL = "cyclical"


class Trend(BaseModel):
    """Detected trend in financial time-series data.

    Story 4.6 AC1/AC3: Trend with direction and magnitude.

    Attributes:
        metric: Name of the financial metric (e.g., "revenue", "expenses")
        direction: Trend direction (INCREASING, DECREASING, STABLE, CYCLICAL)
        magnitude: Magnitude as percentage (e.g., 15.2 for 15.2% CAGR)
        confidence: Statistical confidence score (0.0 to 1.0)
        start_date: Start of trend period (e.g., "2024-Q1")
        end_date: End of trend period (e.g., "2024-Q4")
        description: LLM-generated trend explanation
        cagr: Compound Annual Growth Rate
        qoq_growth: Quarter-over-Quarter average growth rate
    """

    metric: str = Field(..., description="Name of the financial metric")
    direction: TrendDirection = Field(..., description="Trend direction")
    magnitude: float = Field(..., description="Magnitude as percentage (e.g., 15.2 for 15.2% CAGR)")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Statistical confidence")
    start_date: str = Field(..., description="Start of trend period (e.g., '2024-Q1')")
    end_date: str = Field(..., description="End of trend period (e.g., '2024-Q4')")
    description: str = Field(default="", description="LLM-generated trend explanation")
    cagr: float = Field(default=0.0, description="Compound Annual Growth Rate")
    qoq_growth: float = Field(default=0.0, description="Quarter-over-Quarter average growth rate")


class CorrelationResult(BaseModel):
    """Correlation between two financial metrics.

    Story 4.6 AC1: Correlation detection between metrics using Pearson correlation.

    Attributes:
        metric_a: First metric name
        metric_b: Second metric name
        correlation_coefficient: Pearson correlation coefficient (-1.0 to 1.0)
        p_value: Statistical significance (p-value)
        interpretation: Human-readable interpretation (e.g., "Strong positive correlation")
    """

    metric_a: str = Field(..., description="First metric name")
    metric_b: str = Field(..., description="Second metric name")
    correlation_coefficient: float = Field(
        ..., ge=-1.0, le=1.0, description="Pearson correlation coefficient"
    )
    p_value: float = Field(..., description="Statistical significance (p-value)")
    interpretation: str = Field(
        default="",
        description="Human-readable interpretation (e.g., 'Strong positive correlation')",
    )


class TrendAnalysisResult(BaseModel):
    """Result of trend analysis across multiple metrics.

    Story 4.6 AC1: Complete trend analysis result with metadata.

    Attributes:
        trends: List of detected Trend objects
        correlations: List of detected CorrelationResult objects
        metrics_analyzed: Number of metrics processed
        analysis_method: Methods used for analysis (CAGR, QoQ, Pearson correlation)
    """

    trends: list[Trend] = Field(default_factory=list, description="List of detected trends")
    correlations: list[CorrelationResult] = Field(
        default_factory=list, description="List of detected correlations"
    )
    metrics_analyzed: int = Field(..., description="Number of metrics processed")
    analysis_method: str = Field(
        default="Statistical analysis (CAGR, QoQ, Pearson correlation)",
        description="Methods used for analysis",
    )


# Story 4.7: Proactive insight generation models
class InsightCategory(str, Enum):
    """Category of proactive insight.

    Story 4.7 AC2: Insight categorization.

    - RISK: Negative trend, forecast downturn, critical anomaly
    - OPPORTUNITY: Positive trend, growth potential
    - ANOMALY: Unexplained outlier requiring investigation
    - TREND: Notable pattern (neutral - could be good or bad)
    - STRATEGIC_PRIORITY: High-impact area needing attention
    """

    RISK = "risk"
    OPPORTUNITY = "opportunity"
    ANOMALY = "anomaly"
    TREND = "trend"
    STRATEGIC_PRIORITY = "strategic_priority"


class Insight(BaseModel):
    """Proactive insight generated from financial analysis.

    Story 4.7 AC2/AC3/AC5: Insight with category, priority, and supporting data.

    Attributes:
        category: Insight category (risk, opportunity, anomaly, trend, strategic_priority)
        priority: Priority level (1=critical, 5=low)
        summary: One-sentence insight summary
        supporting_data: Data points supporting the insight
        rationale: LLM-generated explanation
        sources: Source documents/metrics cited
        recommended_action: Suggested next step
        created_at: Insight generation timestamp
    """

    category: InsightCategory = Field(..., description="Insight category")
    priority: int = Field(
        ...,
        ge=1,
        le=5,
        description="Priority (1=critical, 5=low)",
    )
    summary: str = Field(..., description="One-sentence insight summary")
    supporting_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Data points supporting the insight",
    )
    rationale: str = Field(default="", description="LLM-generated explanation")
    sources: list[str] = Field(
        default_factory=list,
        description="Source documents/metrics cited",
    )
    recommended_action: str = Field(
        default="",
        description="Suggested next step",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Insight generation timestamp",
    )


class InsightGenerationResult(BaseModel):
    """Result of proactive insight generation.

    Story 4.7 AC1: Complete insight generation result with metadata.

    Attributes:
        insights: List of generated insights sorted by priority
        total_generated: Total insights before filtering
        generation_method: Method used for insight generation
        metrics_analyzed: Number of unique metrics processed
    """

    insights: list[Insight] = Field(
        default_factory=list,
        description="List of generated insights sorted by priority",
    )
    total_generated: int = Field(..., description="Total insights before filtering")
    generation_method: str = Field(
        default="LLM synthesis (Mistral Large)",
        description="Method used for insight generation",
    )
    metrics_analyzed: int = Field(..., description="Number of unique metrics processed")


# Story 4.8: Strategic recommendation engine models
class RecommendationCategory(str, Enum):
    """Category of strategic recommendation.

    Story 4.8 AC1: Recommendation categorization based on insight type.

    - COST_REDUCTION: Reduce expenses, improve efficiency
    - REVENUE_GROWTH: Increase revenue, expand market
    - RISK_MITIGATION: Address risks, prevent losses
    - OPERATIONAL_EFFICIENCY: Streamline processes
    - STRATEGIC_INVESTMENT: Capital allocation decisions
    """

    COST_REDUCTION = "cost_reduction"
    REVENUE_GROWTH = "revenue_growth"
    RISK_MITIGATION = "risk_mitigation"
    OPERATIONAL_EFFICIENCY = "operational_efficiency"
    STRATEGIC_INVESTMENT = "strategic_investment"


class Recommendation(BaseModel):
    """Strategic recommendation generated from financial insights.

    Story 4.8 AC2/AC3: Recommendation with impact score and rationale.

    Attributes:
        category: Recommendation category
        impact_score: Impact score (1=low, 10=high)
        title: Short recommendation title
        description: Detailed recommendation description
        rationale: LLM-generated explanation of why this matters
        supporting_evidence: Data points supporting the recommendation
        action_steps: Concrete action steps (3-5 items)
        urgency: Urgency level (high, medium, low)
        sources: Source insights/documents cited
        created_at: Recommendation generation timestamp
    """

    category: RecommendationCategory = Field(..., description="Recommendation category")
    impact_score: int = Field(
        ...,
        ge=1,
        le=10,
        description="Impact score (1=low, 10=high)",
    )
    title: str = Field(..., description="Short recommendation title")
    description: str = Field(..., description="Detailed recommendation description")
    rationale: str = Field(
        default="",
        description="LLM-generated explanation of why this matters",
    )
    supporting_evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Data points supporting the recommendation",
    )
    action_steps: list[str] = Field(
        default_factory=list,
        description="Concrete action steps (3-5 items)",
    )
    urgency: str = Field(
        default="medium",
        description="Urgency level: high, medium, low",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Source insights/documents cited",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Recommendation generation timestamp",
    )


class RecommendationResult(BaseModel):
    """Result of strategic recommendation generation.

    Story 4.8 AC1: Complete recommendation result with metadata.

    Attributes:
        recommendations: List of recommendations sorted by impact (descending)
        total_generated: Total recommendations before filtering
        generation_method: Method used for recommendation generation
        insights_analyzed: Number of insights processed
    """

    recommendations: list[Recommendation] = Field(
        default_factory=list,
        description="List of recommendations sorted by impact (descending)",
    )
    total_generated: int = Field(..., description="Total recommendations before filtering")
    generation_method: str = Field(
        default="LLM synthesis (Mistral Large)",
        description="Method used for recommendation generation",
    )
    insights_analyzed: int = Field(..., description="Number of insights processed")


# Story 4.9: Proactive Insights MCP Tool models
class InsightsQueryRequest(BaseModel):
    """Request for proactive financial insights via MCP.

    Story 4.9 AC1: MCP tool parameters for insight queries.
    Supports both structured parameters and natural language queries.

    Attributes:
        category: Optional filter by insight category (RISK, OPPORTUNITY, etc.)
        time_period: Optional time period filter (last_quarter, ytd, etc.)
        limit: Maximum insights to return (1-20, default 5)
        include_recommendations: Include strategic recommendations (default True)
        query: Optional natural language query for context-aware filtering
    """

    category: str | None = Field(
        default=None,
        description="Filter by category: RISK, OPPORTUNITY, ANOMALY, TREND, STRATEGIC_PRIORITY",
    )
    time_period: str | None = Field(
        default=None,
        description="Time period: last_quarter, last_year, ytd, current_quarter",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum insights to return (1-20, default 5)",
    )
    include_recommendations: bool = Field(
        default=True,
        description="Include strategic recommendations from Story 4.8",
    )
    query: str | None = Field(
        default=None,
        description="Natural language query for context-aware filtering",
    )


class InsightsQueryResponse(BaseModel):
    """Response from proactive insights MCP tool.

    Story 4.9 AC2/AC4: Ranked insights with conversational formatting.

    Attributes:
        insights: Ranked insights (priority 1=highest first)
        recommendations: Strategic recommendations (impact 10=highest first)
        total_insights: Total insights before limit
        total_recommendations: Total recommendations before filtering
        formatted_summary: LLM-friendly executive summary
        time_period_analyzed: Time period covered by analysis
        generation_time_ms: Total generation time in milliseconds
        source_documents: Documents analyzed for insights
    """

    insights: list[Insight] = Field(
        default_factory=list,
        description="Ranked insights (priority 1=highest first)",
    )
    recommendations: list[Recommendation] = Field(
        default_factory=list,
        description="Strategic recommendations (impact 10=highest first)",
    )
    total_insights: int = Field(..., description="Total insights before limit")
    total_recommendations: int = Field(..., description="Total recommendations before filtering")
    formatted_summary: str = Field(
        default="",
        description="LLM-friendly executive summary",
    )
    time_period_analyzed: str = Field(
        default="",
        description="Time period covered by analysis",
    )
    generation_time_ms: float = Field(
        default=0.0,
        description="Total generation time in milliseconds",
    )
    source_documents: list[str] = Field(
        default_factory=list,
        description="Documents analyzed for insights",
    )
