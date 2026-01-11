"""Chunking and search result models.

Defines models for document chunks, vector search results, and workflow metrics.
"""

from pydantic import BaseModel, Field

from raglite.shared.models.document import DocumentMetadata


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
