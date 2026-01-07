"""Shared fixtures and helpers for PDF ingestion tests.

This module provides reusable mock builders for PDF ingestion testing,
reducing code duplication across test files.
"""

from unittest.mock import Mock

from raglite.shared.models import DocumentMetadata


def create_mock_element(text: str, page_no: int) -> Mock:
    """Create a mock Docling element with text and page provenance.

    Args:
        text: The text content of the element
        page_no: The page number for provenance

    Returns:
        Mock element with .text and .prov attributes
    """
    mock_element = Mock()
    mock_element.text = text
    mock_prov = Mock()
    mock_prov.page_no = page_no
    mock_element.prov = [mock_prov]
    return mock_element


def create_mock_document(
    num_pages: int,
    elements: list[Mock],
    markdown: str | None = None,
) -> Mock:
    """Create a mock Docling document.

    Args:
        num_pages: Number of pages in the document
        elements: List of mock elements from create_mock_element()
        markdown: Optional markdown export text

    Returns:
        Mock document with iterate_items() and export_to_markdown()
    """
    mock_document = Mock()
    mock_document.num_pages.return_value = num_pages
    mock_document.iterate_items.return_value = [(elem, 1) for elem in elements]
    mock_document.export_to_markdown.return_value = markdown or "\n".join(
        elem.text for elem in elements
    )
    return mock_document


def create_mock_qdrant_client(points_count: int = 1) -> Mock:
    """Create a mock Qdrant client with standard configuration.

    Args:
        points_count: Number of points to report in collection

    Returns:
        Mock Qdrant client with standard methods configured
    """
    mock_qdrant_client = Mock()
    mock_qdrant_client.delete_collection = Mock()
    mock_qdrant_client.create_collection = Mock()
    mock_qdrant_client.upsert = Mock()

    # Mock get_collections() for create_collection() idempotency check
    mock_collections_response = Mock()
    mock_collections_response.collections = []
    mock_qdrant_client.get_collections = Mock(return_value=mock_collections_response)

    # Mock get_collection() for points_count validation after upsert
    mock_collection_info = Mock()
    mock_collection_info.points_count = points_count
    mock_qdrant_client.get_collection = Mock(return_value=mock_collection_info)

    return mock_qdrant_client


def create_mock_chunk(
    chunk_id: str,
    content: str,
    filename: str,
    page_number: int,
    chunk_index: int,
    page_count: int,
    word_count: int,
) -> Mock:
    """Create a mock chunk with embedding and metadata.

    Args:
        chunk_id: Unique chunk identifier
        content: Chunk text content
        filename: Source document filename
        page_number: Page number where chunk appears
        chunk_index: Index of chunk in document
        page_count: Total pages in document
        word_count: Number of words in chunk

    Returns:
        Mock chunk object with all required attributes
    """
    return type(
        "MockChunk",
        (),
        {
            "chunk_id": chunk_id,
            "content": content,
            "metadata": DocumentMetadata(
                filename=filename,
                doc_type="PDF",
                ingestion_timestamp="2024-01-01T00:00:00",
                page_count=page_count,
            ),
            "page_number": page_number,
            "chunk_index": chunk_index,
            "embedding": [0.1] * 1024,
            "word_count": word_count,
        },
    )()


def create_standard_docling_patches() -> tuple:
    """Create standard Docling patches for PDF ingestion tests.

    After refactoring, we patch the converter creation function in the _legacy module.
    This is more maintainable and works with lazy imports.

    Returns:
        Tuple of patch targets for use with patch()
    """
    base_patches = [
        "raglite.ingestion.document_ingestion.pdf_processing._legacy.create_docling_converter",
    ]
    return tuple(base_patches)
