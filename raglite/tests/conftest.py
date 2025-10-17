"""Pytest configuration and shared fixtures for RAGLite tests.

Provides test fixtures for configuration, mock clients, and test data.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from raglite.shared.config import Settings
from raglite.shared.models import Chunk, DocumentMetadata


@pytest.fixture
def test_settings(monkeypatch: MonkeyPatch) -> Settings:
    """Provide test settings with safe defaults.

    Overrides environment variables to prevent tests from using production values.

    Args:
        monkeypatch: pytest monkeypatch fixture

    Returns:
        Settings instance with test configuration
    """
    monkeypatch.setenv("QDRANT_HOST", "localhost")
    monkeypatch.setenv("QDRANT_PORT", "6333")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("EMBEDDING_MODEL", "intfloat/e5-large-v2")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "1024")
    return Settings()


@pytest.fixture
def mock_qdrant_client() -> MagicMock:
    """Provide a mock Qdrant client for unit tests.

    Returns:
        MagicMock instance configured with typical Qdrant methods
    """
    mock_client = MagicMock()
    mock_client.get_collections.return_value = []
    mock_client.search.return_value = []
    return mock_client


@pytest.fixture
def mock_claude_client() -> MagicMock:
    """Provide a mock Anthropic Claude client for unit tests.

    Returns:
        MagicMock instance configured with typical Claude API methods
    """
    mock_client = MagicMock()
    return mock_client


@pytest.fixture
def sample_document_metadata() -> DocumentMetadata:
    """Provide sample document metadata for testing.

    Returns:
        DocumentMetadata instance with test data
    """
    # Use system temp directory for security
    temp_dir = Path(tempfile.gettempdir())
    test_path = temp_dir / "test_financial_report.pdf"

    return DocumentMetadata(
        filename="test_financial_report.pdf",
        doc_type="PDF",
        ingestion_timestamp="2025-10-04T12:00:00Z",
        page_count=10,
        source_path=str(test_path),
    )


@pytest.fixture
def sample_chunk(sample_document_metadata: DocumentMetadata) -> Chunk:
    """Provide sample chunk for testing.

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
        embedding=[0.1] * 1024,  # Mock embedding vector
    )
