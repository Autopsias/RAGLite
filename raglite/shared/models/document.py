"""Document metadata and ingestion result models.

Defines models for document ingestion, metadata tracking, and batch processing.
"""

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
        models_retrained: List of models retrained after ingestion (if retrain_models=True)
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
    # Model retraining field (Issue 5 fix)
    models_retrained: list[str] | None = Field(
        default=None,
        description="List of models retrained after ingestion (if retrain_models=True)",
    )

    @classmethod
    def from_metadata(
        cls,
        metadata: "DocumentMetadata",
        forecasts_updated: list[str] | None = None,
        forecast_refresh_skipped_reason: str | None = None,
        models_retrained: list[str] | None = None,
    ) -> "IngestionResult":
        """Create IngestionResult from DocumentMetadata with forecast fields.

        Args:
            metadata: Document metadata from ingestion
            forecasts_updated: List of refreshed metrics
            forecast_refresh_skipped_reason: Reason if refresh was skipped
            models_retrained: List of models retrained after ingestion

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
            models_retrained=models_retrained,
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
