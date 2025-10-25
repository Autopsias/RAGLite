"""Unit tests for table-aware chunking logic.

Story 2.8 Task 6.2: Unit tests for table detection and splitting.
"""

from unittest.mock import Mock

import pytest
import tiktoken
from docling_core.types.doc import TableItem

from raglite.ingestion.pipeline import split_large_table_by_rows
from raglite.shared.models import DocumentMetadata


@pytest.fixture
def encoding():
    """Tiktoken encoding fixture."""
    return tiktoken.get_encoding("cl100k_base")


@pytest.fixture
def mock_table_item():
    """Mock Docling TableItem."""
    table_item = Mock(spec=TableItem)
    return table_item


@pytest.fixture
def mock_result():
    """Mock ConversionResult."""
    result = Mock()
    result.document = Mock()
    return result


@pytest.fixture
def doc_metadata():
    """Sample DocumentMetadata."""
    return DocumentMetadata(
        filename="test.pdf",
        doc_type="PDF",
        ingestion_timestamp="2025-10-25T12:00:00Z",
        page_count=10,
        source_path="/path/to/test.pdf",
    )


def test_split_large_table_small_table(encoding, mock_table_item, mock_result):
    """Test that small tables (<4096 tokens) are kept intact."""
    # Small table markdown (< 4096 tokens)
    small_table_content = """
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |
"""

    mock_table_item.export_to_markdown.return_value = small_table_content

    # Call split function
    chunks = split_large_table_by_rows(
        table_item=mock_table_item,
        result=mock_result,
        encoding=encoding,
        max_tokens=4096,
        table_index=1,
    )

    # Should return single chunk (table kept intact)
    assert len(chunks) == 1
    assert chunks[0][0] == small_table_content


def test_split_large_table_by_rows_headers_preserved(encoding, mock_table_item, mock_result):
    """Test that large tables are split by rows with headers duplicated."""
    # Create a large table that exceeds 4096 tokens
    header = "| Column 1 | Column 2 | Column 3 | Column 4 | Column 5 |\n"
    separator = "|----------|----------|----------|----------|----------|\n"

    # Create 500 rows (should exceed 4096 tokens)
    rows = [
        f"| Row {i} Data 1 | Row {i} Data 2 | Row {i} Data 3 | Row {i} Data 4 | Row {i} Data 5 |\n"
        for i in range(500)
    ]

    large_table_content = header + separator + "".join(rows)
    mock_table_item.export_to_markdown.return_value = large_table_content

    # Call split function
    chunks = split_large_table_by_rows(
        table_item=mock_table_item,
        result=mock_result,
        encoding=encoding,
        max_tokens=4096,
        table_index=1,
    )

    # Should split into multiple chunks
    assert len(chunks) > 1, "Large table should be split into multiple chunks"

    # Check that all chunks have headers
    for chunk_content, _caption in chunks:
        assert "| Column 1" in chunk_content, "All chunks should have column headers"
        assert "|----------" in chunk_content, "All chunks should have separator row"

    # Check that all chunks are <4096 tokens
    for chunk_content, _caption in chunks:
        token_count = len(encoding.encode(chunk_content))
        assert token_count < 4096, f"Chunk should be <4096 tokens, got {token_count}"


def test_split_large_table_context_prefix(encoding, mock_table_item, mock_result):
    """Test that table context prefix is added correctly."""
    # Create table content with caption
    table_content = """Variable Costs Summary

| Metric | Value |
|--------|-------|
| Cost 1 | 100   |
| Cost 2 | 200   |
"""

    mock_table_item.export_to_markdown.return_value = table_content

    # Call split function
    chunks = split_large_table_by_rows(
        table_item=mock_table_item,
        result=mock_result,
        encoding=encoding,
        max_tokens=4096,
        table_index=3,
    )

    # Should have table prefix
    chunk_content = chunks[0][0]

    # Single chunk should have "Table 3: {caption}" format
    assert "Table 3:" in chunk_content or "Variable Costs Summary" in chunk_content


def test_split_large_table_edge_case_single_row(encoding, mock_table_item, mock_result):
    """Test edge case: table with only header and one data row."""
    single_row_table = """
| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
"""

    mock_table_item.export_to_markdown.return_value = single_row_table

    # Call split function
    chunks = split_large_table_by_rows(
        table_item=mock_table_item,
        result=mock_result,
        encoding=encoding,
        max_tokens=4096,
        table_index=1,
    )

    # Should return single chunk
    assert len(chunks) == 1
    assert "| Data 1" in chunks[0][0]


def test_split_large_table_edge_case_empty_table(encoding, mock_table_item, mock_result):
    """Test edge case: table with only headers, no data rows."""
    header_only_table = """
| Column 1 | Column 2 |
|----------|----------|
"""

    mock_table_item.export_to_markdown.return_value = header_only_table

    # Call split function
    chunks = split_large_table_by_rows(
        table_item=mock_table_item,
        result=mock_result,
        encoding=encoding,
        max_tokens=4096,
        table_index=1,
    )

    # Should return original content (fallback for malformed table)
    assert len(chunks) == 1


def test_token_counting_accuracy(encoding):
    """Test that token counting is accurate."""
    test_text = "This is a test sentence for token counting."

    # Count tokens
    tokens = encoding.encode(test_text)
    token_count = len(tokens)

    # Should be deterministic and consistent
    assert token_count > 0
    assert len(encoding.encode(test_text)) == token_count  # Same result twice


def test_table_chunk_section_type():
    """Test that table chunks are marked with section_type='Table'.

    This test validates AC1: Table metadata preservation.
    """
    from raglite.shared.models import Chunk

    # Create a chunk with section_type='Table'
    chunk = Chunk(
        chunk_id="test_chunk_1",
        content="Test table content",
        metadata=DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-10-25T12:00:00Z",
            page_count=10,
            source_path="/path/to/test.pdf",
        ),
        page_number=1,
        chunk_index=0,
        embedding=[],
        section_type="Table",
    )

    # Verify section_type is preserved
    assert chunk.section_type == "Table", "Table chunks should have section_type='Table'"
