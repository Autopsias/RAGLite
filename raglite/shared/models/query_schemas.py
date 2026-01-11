"""Query request and response schemas.

Defines Pydantic schemas for natural language queries, analytical queries, and validation.

Renamed from query.py to avoid naming collision with raglite.mcp.tools.query package.
"""

from typing import Any

from pydantic import BaseModel, Field

from raglite.shared.models.document import ExtractedMetadata


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
