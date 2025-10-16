"""Unit tests for page number extraction from Docling provenance (Story 1.13).

Tests the chunk_by_docling_items function to verify accurate page number
extraction from Docling metadata instead of character position estimation.
"""

from unittest.mock import Mock

import pytest

from raglite.ingestion.pipeline import chunk_by_docling_items
from raglite.shared.models import DocumentMetadata


class TestChunkByDoclingItems:
    """Test suite for Docling-based chunking with provenance extraction."""

    @pytest.mark.asyncio
    async def test_chunk_by_docling_items_extracts_page_numbers(self):
        """Test that chunk_by_docling_items extracts actual page numbers from provenance.

        Verifies that page numbers come from item.prov[0].page_no, not estimates.
        """
        # Create mock Docling items with provenance
        mock_item1 = Mock()
        mock_item1.text = "This is content on page 43"
        mock_prov1 = Mock()
        mock_prov1.page_no = 43
        mock_item1.prov = [mock_prov1]

        mock_item2 = Mock()
        mock_item2.text = "This is content on page 44"
        mock_prov2 = Mock()
        mock_prov2.page_no = 44
        mock_item2.prov = [mock_prov2]

        mock_item3 = Mock()
        mock_item3.text = "This is content on page 118"
        mock_prov3 = Mock()
        mock_prov3.page_no = 118
        mock_item3.prov = [mock_prov3]

        # Create mock document
        mock_document = Mock()
        mock_document.iterate_items.return_value = [
            (mock_item1, 1),
            (mock_item2, 1),
            (mock_item3, 1),
        ]

        # Create mock ConversionResult
        mock_result = Mock()
        mock_result.document = mock_document

        # Create metadata
        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-10-13T00:00:00Z",
            page_count=120,
            source_path="/test/test.pdf",
            chunk_count=0,
        )

        # Execute chunking
        chunks = await chunk_by_docling_items(mock_result, metadata)

        # Assertions
        assert len(chunks) == 3, "Should create 3 chunks for 3 pages"
        assert chunks[0].page_number == 43, "First chunk should be page 43"
        assert chunks[1].page_number == 44, "Second chunk should be page 44"
        assert chunks[2].page_number == 118, "Third chunk should be page 118"

        # Verify no estimation (actual pages, not sequential 1, 2, 3)
        assert chunks[0].page_number != 1, "Should use actual page from provenance, not estimate"
        assert chunks[1].page_number != 2, "Should use actual page from provenance, not estimate"
        assert chunks[2].page_number != 3, "Should use actual page from provenance, not estimate"

    @pytest.mark.asyncio
    async def test_chunk_by_docling_items_handles_missing_prov(self):
        """Test that missing provenance falls back to last known page with warning.

        Verifies graceful handling when some items lack provenance metadata.
        """
        # Create mock items with and without provenance
        mock_item1 = Mock()
        mock_item1.text = "Content with provenance on page 50"
        mock_prov1 = Mock()
        mock_prov1.page_no = 50
        mock_item1.prov = [mock_prov1]

        mock_item2 = Mock()
        mock_item2.text = "Content WITHOUT provenance"
        mock_item2.prov = None  # Missing provenance

        mock_item3 = Mock()
        mock_item3.text = "More content without provenance"
        mock_item3.prov = []  # Empty provenance

        mock_item4 = Mock()
        mock_item4.text = "Content back with provenance on page 51"
        mock_prov4 = Mock()
        mock_prov4.page_no = 51
        mock_item4.prov = [mock_prov4]

        # Create mock document
        mock_document = Mock()
        mock_document.iterate_items.return_value = [
            (mock_item1, 1),
            (mock_item2, 1),
            (mock_item3, 1),
            (mock_item4, 1),
        ]

        # Create mock ConversionResult
        mock_result = Mock()
        mock_result.document = mock_document

        # Create metadata
        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-10-13T00:00:00Z",
            page_count=60,
            source_path="/test/test.pdf",
            chunk_count=0,
        )

        # Execute chunking
        chunks = await chunk_by_docling_items(mock_result, metadata)

        # Assertions
        assert len(chunks) == 2, "Should create 2 chunks (items grouped by page)"
        assert chunks[0].page_number == 50, "First chunk should be page 50"
        # Items 2 and 3 without prov should be grouped into page 50 chunk
        assert "Content with provenance on page 50" in chunks[0].content
        assert "Content WITHOUT provenance" in chunks[0].content
        assert "More content without provenance" in chunks[0].content
        assert chunks[1].page_number == 51, "Second chunk should be page 51"
        assert "Content back with provenance on page 51" in chunks[1].content

    @pytest.mark.asyncio
    async def test_chunk_by_docling_items_respects_page_boundaries(self):
        """Test that chunks don't span page boundaries.

        Verifies that content from different pages is kept in separate chunks.
        """
        # Create mock items on different pages
        mock_item1 = Mock()
        mock_item1.text = "Page 10 content line 1"
        mock_prov1 = Mock()
        mock_prov1.page_no = 10
        mock_item1.prov = [mock_prov1]

        mock_item2 = Mock()
        mock_item2.text = "Page 10 content line 2"
        mock_prov2 = Mock()
        mock_prov2.page_no = 10
        mock_item2.prov = [mock_prov2]

        mock_item3 = Mock()
        mock_item3.text = "Page 11 content line 1"
        mock_prov3 = Mock()
        mock_prov3.page_no = 11
        mock_item3.prov = [mock_prov3]

        mock_item4 = Mock()
        mock_item4.text = "Page 11 content line 2"
        mock_prov4 = Mock()
        mock_prov4.page_no = 11
        mock_item4.prov = [mock_prov4]

        # Create mock document
        mock_document = Mock()
        mock_document.iterate_items.return_value = [
            (mock_item1, 1),
            (mock_item2, 1),
            (mock_item3, 1),
            (mock_item4, 1),
        ]

        # Create mock ConversionResult
        mock_result = Mock()
        mock_result.document = mock_document

        # Create metadata
        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-10-13T00:00:00Z",
            page_count=15,
            source_path="/test/test.pdf",
            chunk_count=0,
        )

        # Execute chunking
        chunks = await chunk_by_docling_items(mock_result, metadata)

        # Assertions
        assert len(chunks) == 2, "Should create 2 chunks for 2 pages"
        assert chunks[0].page_number == 10, "First chunk should be page 10"
        assert chunks[1].page_number == 11, "Second chunk should be page 11"

        # Verify content grouping by page
        assert "Page 10 content line 1" in chunks[0].content, "Page 10 chunk should contain line 1"
        assert "Page 10 content line 2" in chunks[0].content, "Page 10 chunk should contain line 2"
        assert "Page 11" not in chunks[0].content, (
            "Page 10 chunk should NOT contain page 11 content"
        )

        assert "Page 11 content line 1" in chunks[1].content, "Page 11 chunk should contain line 1"
        assert "Page 11 content line 2" in chunks[1].content, "Page 11 chunk should contain line 2"
        assert "Page 10" not in chunks[1].content, (
            "Page 11 chunk should NOT contain page 10 content"
        )

    @pytest.mark.asyncio
    async def test_chunk_by_docling_items_maintains_chunk_size(self):
        """Test that large pages are split into multiple chunks respecting size limit.

        Verifies that pages exceeding chunk_size are split while maintaining
        the correct page number for all resulting chunks.
        """
        # Create mock item with very long text (> 500 words)
        long_text = " ".join([f"word{i}" for i in range(800)])  # 800 words

        mock_item1 = Mock()
        mock_item1.text = long_text
        mock_prov1 = Mock()
        mock_prov1.page_no = 75
        mock_item1.prov = [mock_prov1]

        # Create mock document
        mock_document = Mock()
        mock_document.iterate_items.return_value = [(mock_item1, 1)]

        # Create mock ConversionResult
        mock_result = Mock()
        mock_result.document = mock_document

        # Create metadata
        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-10-13T00:00:00Z",
            page_count=100,
            source_path="/test/test.pdf",
            chunk_count=0,
        )

        # Execute chunking with chunk_size=500
        chunks = await chunk_by_docling_items(mock_result, metadata, chunk_size=500, overlap=50)

        # Assertions
        assert len(chunks) >= 2, "Large page should be split into multiple chunks"

        # All chunks should have the SAME page number (75) since they're from the same page
        for chunk in chunks:
            assert chunk.page_number == 75, (
                f"All chunks from page 75 should preserve page number, got {chunk.page_number}"
            )

        # Verify chunk sizes are reasonable (~500 words)
        for chunk in chunks:
            word_count = len(chunk.content.split())
            assert word_count <= 550, (
                f"Chunk size {word_count} should not exceed target significantly"
            )
            assert word_count > 0, "Chunk should not be empty"

        # Verify overlap is maintained between chunks
        if len(chunks) > 1:
            # Check that last words of chunk N appear in first words of chunk N+1
            chunk1_words = chunks[0].content.split()
            chunk2_words = chunks[1].content.split()
            # With 50-word overlap, some words should appear in both
            assert len(set(chunk1_words[-50:]) & set(chunk2_words[:50])) > 0, (
                "Chunks should have overlap"
            )

    @pytest.mark.asyncio
    async def test_chunk_by_docling_items_handles_table_items(self):
        """Test that TableItem objects are processed via export_to_markdown() (Story 1.15).

        Verifies that table items with financial data are extracted as markdown
        and included in chunks with correct page attribution.
        """
        # Import TableItem for isinstance check
        from docling_core.types.doc import TableItem

        # Create mock TableItem with financial data
        mock_table_item = Mock(spec=TableItem)
        mock_table_item.export_to_markdown.return_value = """
| Metric | Value | Budget | LY |
|--------|-------|--------|-----|
| Variable Cost/ton | 23.2 EUR/ton | 20.3 | 29.4 |
| EBITDA Margin | 50.6% | 48.2% | 52.1% |
"""
        mock_prov_table = Mock()
        mock_prov_table.page_no = 46
        mock_table_item.prov = [mock_prov_table]

        # Create mock text item on same page
        mock_text_item = Mock()
        mock_text_item.text = "Portugal Cement Performance Review"
        mock_prov_text = Mock()
        mock_prov_text.page_no = 46
        mock_text_item.prov = [mock_prov_text]

        # Create mock document with TableItem and text item
        mock_document = Mock()
        mock_document.iterate_items.return_value = [
            (mock_table_item, 1),
            (mock_text_item, 1),
        ]

        # Create mock ConversionResult
        mock_result = Mock()
        mock_result.document = mock_document

        # Create metadata
        metadata = DocumentMetadata(
            filename="performance_review.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-10-16T00:00:00Z",
            page_count=160,
            source_path="/test/performance_review.pdf",
            chunk_count=0,
        )

        # Execute chunking
        chunks = await chunk_by_docling_items(mock_result, metadata)

        # Assertions
        assert len(chunks) == 1, "Should create 1 chunk for page 46 (table + text)"
        assert chunks[0].page_number == 46, "Chunk should be attributed to page 46"

        # Verify table markdown is in the chunk content
        assert "23.2 EUR/ton" in chunks[0].content, "Table financial data should be in chunk"
        assert "50.6%" in chunks[0].content, "Table percentage data should be in chunk"
        assert "Variable Cost/ton" in chunks[0].content, "Table headers should be in chunk"

        # Verify text content is also in the chunk
        assert "Portugal Cement Performance Review" in chunks[0].content, (
            "Text items should also be included"
        )

        # Verify export_to_markdown was called
        mock_table_item.export_to_markdown.assert_called_once()
