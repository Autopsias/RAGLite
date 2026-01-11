"""Shared fixtures for ingestion tests.

Provides common mocks for Qdrant, Docling, embeddings, and database operations
to reduce duplication across ingestion test files.
"""

from unittest.mock import Mock

import numpy as np
import pytest


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client with standard methods.

    Returns a Mock QdrantClient with:
    - delete_collection, create_collection, upsert methods
    - get_collections returning empty list (for idempotency checks)
    - get_collection returning mock with points_count
    """
    mock_client = Mock()
    mock_client.delete_collection = Mock()
    mock_client.create_collection = Mock()
    mock_client.upsert = Mock()

    # Mock get_collections() for create_collection() idempotency check
    mock_collections_response = Mock()
    mock_collections_response.collections = []
    mock_client.get_collections = Mock(return_value=mock_collections_response)

    # Mock get_collection() for points_count validation after upsert
    mock_collection_info = Mock()
    mock_collection_info.points_count = 2  # Default: 2 chunks
    mock_client.get_collection = Mock(return_value=mock_collection_info)

    return mock_client


@pytest.fixture
def mock_docling_document():
    """Mock Docling document with standard structure.

    Returns a mock document with:
    - num_pages() returning 2
    - iterate_items() returning 2 mock elements
    - export_to_markdown() returning sample text
    """
    mock_element1 = Mock()
    mock_element1.text = "Financial Report Q4 2024"
    mock_prov1 = Mock()
    mock_prov1.page_no = 1
    mock_element1.prov = [mock_prov1]

    mock_element2 = Mock()
    mock_element2.text = "Revenue Summary"
    mock_prov2 = Mock()
    mock_prov2.page_no = 2
    mock_element2.prov = [mock_prov2]

    mock_document = Mock()
    mock_document.num_pages.return_value = 2
    mock_document.iterate_items.return_value = [
        (mock_element1, 1),
        (mock_element2, 1),
    ]
    mock_document.export_to_markdown.return_value = "Financial Report Q4 2024\nRevenue Summary"

    return mock_document


@pytest.fixture
def mock_docling_result(mock_docling_document):
    """Mock Docling converter result.

    Returns a mock result containing a mock document.
    """
    mock_result = Mock()
    mock_result.document = mock_docling_document
    return mock_result


@pytest.fixture
def mock_embedding_model():
    """Mock embedding model that returns fixed vectors.

    Returns a mock that:
    - encode() returns numpy array of shape (1, 384)
    - Simulates Fin-E5 384-dimensional embeddings
    """
    mock_model = Mock()
    mock_model.encode.return_value = np.array([[0.1] * 384])
    return mock_model


@pytest.fixture
def mock_postgresql_responses():
    """Mock PostgreSQL operation responses.

    Returns tuple of (metadata_response, tables_response) for common operations:
    - store_metadata_in_postgresql: (1, 0) - 1 inserted, 0 skipped
    - store_tables_in_postgresql: (0, 0) - 0 tables inserted
    """
    return {
        "metadata": (1, 0),  # (inserted, skipped)
        "tables": (0, 0),
    }


@pytest.fixture
def mock_table_item():
    """Mock TableItem for testing."""
    from docling_core.types.doc import TableItem

    table_item = Mock(spec=TableItem)
    table_item.export_to_markdown.return_value = "| Test | Table | Data |"
    table_item.caption = None
    return table_item


@pytest.fixture
def mock_result():
    """Mock ConversionResult for table extraction."""
    from docling_core.types.doc import DoclingDocument

    result = Mock()
    result.document = Mock(spec=DoclingDocument)
    return result


def create_table_cell(
    text: str,
    row_idx: int,
    col_idx: int,
    row_span: int = 1,
    col_span: int = 1,
    is_col_header: bool = False,
    is_row_header: bool = False,
) -> Mock:
    """Helper to create mock TableCell for standard layout tests."""
    from docling_core.types.doc import TableCell

    cell = Mock(spec=TableCell)
    cell.text = text
    cell.start_row_offset_idx = row_idx
    cell.end_row_offset_idx = row_idx + row_span
    cell.start_col_offset_idx = col_idx
    cell.end_col_offset_idx = col_idx + col_span
    cell.column_header = is_col_header
    cell.row_header = is_row_header
    return cell
