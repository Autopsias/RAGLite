"""Pydantic data models for RAGLite.

Defines core data structures used across ingestion and retrieval modules.
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


# Type alias for job identifiers (used in ingestion pipeline)
JobID = str
