"""Pydantic data models for RAGLite.

Defines core data structures used across ingestion and retrieval modules.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ElementType(str, Enum):
    """Element types detected by Docling.

    Used to classify document chunks by their semantic structure type,
    enabling element-aware retrieval and metadata filtering.
    """

    TABLE = "table"
    SECTION_HEADER = "section_header"
    PARAGRAPH = "paragraph"
    LIST = "list"
    FIGURE = "figure"
    MIXED = "mixed"  # Chunk contains multiple element types


class DocumentElement(BaseModel):
    """Structured element from Docling parsing.

    Represents a single document element (table, section, paragraph)
    with its content, type, and position metadata. Used as intermediate
    representation before chunking.

    Attributes:
        element_id: Unique ID from Docling or generated identifier
        type: Element type classification (table, section, paragraph, etc.)
        content: Raw Markdown content of the element
        page_number: Page number where element appears
        section_title: Parent section header text for context (None if no parent)
        token_count: Estimated token count via tiktoken for chunking decisions
        metadata: Additional element-specific metadata from Docling
    """

    element_id: str = Field(..., description="Unique element identifier")
    type: ElementType = Field(..., description="Element type classification")
    content: str = Field(..., description="Raw Markdown content")
    page_number: int = Field(..., description="Page number where element appears")
    section_title: str | None = Field(
        default=None, description="Parent section header text for context"
    )
    token_count: int = Field(default=0, description="Estimated token count via tiktoken")
    metadata: dict = Field(default_factory=dict, description="Additional element-specific metadata")


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


class Chunk(BaseModel):
    """Document chunk with content and metadata.

    Represents a semantic chunk of a document after chunking and embedding.
    Enhanced in Story 2.2 with element-type metadata for structure-aware retrieval.

    Attributes:
        chunk_id: Unique chunk identifier
        content: Chunk text content
        metadata: Parent document metadata
        page_number: Page number where chunk appears
        chunk_index: Sequential chunk index (0-based)
        embedding: Semantic embedding vector
        element_type: Primary element type (table, section, paragraph, etc.) - NEW in Story 2.2
        section_title: Parent section header for context - NEW in Story 2.2
        parent_chunk_id: Reference to parent chunk for summaries - NEW in Story 2.2 (for Story 2.4)
        word_count: Word count of chunk content - NEW in Story 2.2
    """

    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk text content")
    metadata: DocumentMetadata = Field(..., description="Parent document metadata")
    page_number: int = Field(default=0, description="Page number where chunk appears")
    chunk_index: int = Field(default=0, description="Sequential chunk index (0-based)")
    embedding: list[float] = Field(default_factory=list, description="Semantic embedding vector")
    # NEW FIELDS for Story 2.2: Element-aware chunking
    element_type: ElementType = Field(
        default=ElementType.MIXED, description="Primary element type in chunk"
    )
    section_title: str | None = Field(
        default=None, description="Parent section header text for context"
    )
    parent_chunk_id: str | None = Field(
        default=None, description="Reference to parent chunk (for table summaries in Story 2.4)"
    )
    word_count: int = Field(default=0, description="Word count of chunk content")


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
