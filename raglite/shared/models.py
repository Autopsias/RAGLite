"""Pydantic data models for RAGLite.

Defines core data structures used across ingestion and retrieval modules.
"""

from datetime import datetime
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
        default=None, description="Geographic region: Portugal, EU, APAC, Americas, Global"
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
    """

    score: float = Field(
        ..., le=1.0, description="Relevance score (typically 0-1, but BM25 hybrid can be negative)"
    )
    text: str = Field(..., description="Chunk text content")
    source_document: str = Field(..., description="Source document filename")
    page_number: int | None = Field(
        ..., description="Page number where chunk appears (None if missing)"
    )
    chunk_index: int = Field(..., description="Sequential chunk index (0-based)")
    word_count: int = Field(..., description="Word count of chunk")


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
        default_factory=list, description="List of agents invoked (e.g., ['retrieval', 'analysis'])"
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
        default="raw", description="Time interval: 'raw', 'monthly', 'quarterly', 'yearly'"
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
        default_factory=list, description="Forecast predictions with confidence intervals"
    )
    confidence_reasoning: str = Field(
        default="", description="LLM-generated explanation of confidence intervals"
    )
    basis: str = Field(
        default="", description="Forecast basis (e.g., 'Prophet model trained on 8 quarters')"
    )
    accuracy_estimate: str = Field(default="±15%", description="Expected accuracy per NFR10")
    periods_ahead: int = Field(default=4, description="Number of periods forecasted")


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
        default=None, description="Estimated completion time in seconds (based on page count)"
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
        default=None, description="Job completion timestamp (ISO 8601 format, only when done)"
    )
