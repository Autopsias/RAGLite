"""Sample data fixtures for testing.

This module provides sample document metadata and chunk fixtures used across
unit and integration tests.

Fixtures:
    sample_document_metadata: Module-scoped sample PDF document metadata
    sample_chunk: Function-scoped sample text chunk with embedding
"""

import logging

import pytest

from raglite.shared.config import get_active_embedding_dimension
from raglite.shared.models import Chunk, DocumentMetadata

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def sample_document_metadata() -> DocumentMetadata:
    """Provide sample document metadata for testing (module-scoped).

    Module-scoped because metadata is immutable and can be shared.

    Returns:
        DocumentMetadata instance with test data
    """
    metadata = DocumentMetadata(
        filename="test_financial_report.pdf",
        doc_type="PDF",
        ingestion_timestamp="2025-10-04T12:00:00Z",
        page_count=10,
        source_path="/tmp/test_financial_report.pdf",
    )
    return metadata


@pytest.fixture
def sample_chunk(sample_document_metadata: DocumentMetadata) -> Chunk:
    """Provide sample chunk for testing (function-scoped for isolation).

    Function-scoped because tests may modify chunk content.

    Args:
        sample_document_metadata: Fixture providing document metadata

    Returns:
        Chunk instance with test data
    """
    return Chunk(
        chunk_id="chunk-001",
        content="Q3 revenue was $50M, up 20% YoY.",
        metadata=sample_document_metadata,
        page_number=5,
        embedding=[0.1]
        * get_active_embedding_dimension(),  # Mock embedding vector (CI: 384, Local: 1024)
    )
