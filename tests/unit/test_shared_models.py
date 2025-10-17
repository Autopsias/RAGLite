"""Unit tests for raglite.shared.models module."""

import pytest
from pydantic import ValidationError

from raglite.shared.models import Chunk, DocumentMetadata, SearchResult


@pytest.mark.p0
@pytest.mark.unit
def test_document_metadata_creation() -> None:
    """Test DocumentMetadata model creates successfully with required fields."""
    metadata = DocumentMetadata(
        filename="test.pdf",
        doc_type="PDF",
        ingestion_timestamp="2025-10-04T12:00:00Z",
        page_count=5,
    )

    assert metadata.filename == "test.pdf"
    assert metadata.doc_type == "PDF"
    assert metadata.page_count == 5


@pytest.mark.p0
@pytest.mark.unit
def test_document_metadata_missing_required_field() -> None:
    """Test DocumentMetadata raises ValidationError if required field missing."""
    with pytest.raises(ValidationError):
        DocumentMetadata(
            filename="test.pdf"
            # Missing doc_type and ingestion_timestamp (required fields)
        )  # type: ignore[call-arg]


@pytest.mark.p1
@pytest.mark.unit
def test_chunk_creation(sample_document_metadata: DocumentMetadata) -> None:
    """Test Chunk model creates successfully."""
    chunk = Chunk(
        chunk_id="chunk-001",
        content="Test content",
        metadata=sample_document_metadata,
        page_number=1,
        embedding=[0.1] * 1024,
    )

    assert chunk.chunk_id == "chunk-001"
    assert chunk.content == "Test content"
    assert chunk.page_number == 1
    assert len(chunk.embedding) == 1024


@pytest.mark.p1
@pytest.mark.unit
def test_chunk_default_embedding(sample_document_metadata: DocumentMetadata) -> None:
    """Test Chunk uses empty list as default for embedding field."""
    chunk = Chunk(chunk_id="chunk-002", content="Test", metadata=sample_document_metadata)

    assert chunk.embedding == []


@pytest.mark.p1
@pytest.mark.unit
def test_search_result_score_validation(sample_chunk: Chunk) -> None:
    """Test SearchResult validates score is between 0 and 1."""
    # Valid score
    result = SearchResult(score=0.85, chunk=sample_chunk)
    assert result.score == 0.85

    # Invalid score > 1
    with pytest.raises(ValidationError):
        SearchResult(score=1.5, chunk=sample_chunk)

    # Invalid score < 0
    with pytest.raises(ValidationError):
        SearchResult(score=-0.1, chunk=sample_chunk)
