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

    Story 2.4: Extracted using GPT-5 nano for query filtering and precision boosting.
    All fields are optional as extraction may not find all information.
    """

    fiscal_period: str | None = Field(
        default=None, description="Fiscal period (e.g., 'Q3 2024', 'FY 2023')"
    )
    company_name: str | None = Field(
        default=None, description="Company name (e.g., 'ACME Corporation')"
    )
    department_name: str | None = Field(
        default=None, description="Department name (e.g., 'Finance', 'Operations')"
    )


class Chunk(BaseModel):
    """Document chunk with content and metadata.

    Represents a semantic chunk of a document after chunking and embedding.
    Simplified in Story 2.3 to use fixed 512-token chunking (no element-aware metadata).

    Story 2.4 additions: LLM-extracted business context metadata for filtering.

    Attributes:
        chunk_id: Unique chunk identifier
        content: Chunk text content
        metadata: Parent document metadata
        page_number: Page number where chunk appears
        chunk_index: Sequential chunk index (0-based)
        embedding: Semantic embedding vector
        parent_chunk_id: Reference to parent chunk for summaries (for Story 2.4)
        word_count: Word count of chunk content
        fiscal_period: LLM-extracted fiscal period (Story 2.4)
        company_name: LLM-extracted company name (Story 2.4)
        department_name: LLM-extracted department name (Story 2.4)
    """

    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk text content")
    metadata: DocumentMetadata = Field(..., description="Parent document metadata")
    page_number: int = Field(default=0, description="Page number where chunk appears")
    chunk_index: int = Field(default=0, description="Sequential chunk index (0-based)")
    embedding: list[float] = Field(default_factory=list, description="Semantic embedding vector")
    parent_chunk_id: str | None = Field(
        default=None, description="Reference to parent chunk (for table summaries in Story 2.4)"
    )
    word_count: int = Field(default=0, description="Word count of chunk content")
    # Story 2.4: LLM-extracted business context metadata
    fiscal_period: str | None = Field(
        default=None, description="Fiscal period (e.g., 'Q3 2024', 'FY 2023')"
    )
    company_name: str | None = Field(
        default=None, description="Company name (e.g., 'ACME Corporation')"
    )
    department_name: str | None = Field(
        default=None, description="Department name (e.g., 'Finance', 'Operations')"
    )


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
