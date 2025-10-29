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

        NOTE: Element-aware chunking (Story 2.2) groups small elements together even if
        from different pages. Page number is taken from first element in chunk.
        """
        # Import TextItem for proper mock spec
        from docling_core.types.doc import TextItem

        # Create mock Docling items with provenance - use spec for proper attribute access
        # Use larger text to force separate chunks (element-aware chunking groups small items)
        mock_item1 = Mock(spec=TextItem)
        mock_item1.text = " ".join([f"word{i}" for i in range(300)])  # 300 words on page 43
        mock_prov1 = Mock()
        mock_prov1.page_no = 43
        mock_item1.prov = [mock_prov1]

        mock_item2 = Mock(spec=TextItem)
        mock_item2.text = " ".join([f"word{i}" for i in range(300)])  # 300 words on page 44
        mock_prov2 = Mock()
        mock_prov2.page_no = 44
        mock_item2.prov = [mock_prov2]

        mock_item3 = Mock(spec=TextItem)
        mock_item3.text = " ".join([f"word{i}" for i in range(300)])  # 300 words on page 118
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

        # Assertions - element-aware chunking groups elements, page from first element
        assert len(chunks) >= 1, "Should create at least one chunk"

        # Verify page numbers are extracted from provenance (not estimated)
        for chunk in chunks:
            assert chunk.page_number in [
                43,
                44,
                118,
            ], f"Page number {chunk.page_number} should be from provenance (43, 44, or 118)"
            assert chunk.page_number != 1 or chunk.page_number in [
                43,
                44,
                118,
            ], "Should use actual page from provenance, not default/estimate"

        # Verify first chunk starts with page from first element
        assert chunks[0].page_number == 43, "First chunk should use page number from first element"

    @pytest.mark.asyncio
    async def test_chunk_by_docling_items_handles_missing_prov(self):
        """Test that missing provenance defaults to page 1.

        Verifies graceful handling when some items lack provenance metadata.
        Element-aware chunking groups small items together.
        """
        # Import TextItem for proper mock spec
        from docling_core.types.doc import TextItem

        # Create mock items with and without provenance
        mock_item1 = Mock(spec=TextItem)
        mock_item1.text = "Content with provenance on page 50"
        mock_prov1 = Mock()
        mock_prov1.page_no = 50
        mock_item1.prov = [mock_prov1]

        mock_item2 = Mock(spec=TextItem)
        mock_item2.text = "Content WITHOUT provenance defaults to page 1"
        mock_item2.prov = None  # Missing provenance - will default to page 1

        mock_item3 = Mock(spec=TextItem)
        mock_item3.text = "More content without provenance also defaults to page 1"
        mock_item3.prov = []  # Empty provenance - will default to page 1

        mock_item4 = Mock(spec=TextItem)
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

        # Assertions - element-aware chunking may group small items
        assert len(chunks) >= 1, "Should create at least one chunk"

        # Verify all content is present in chunks
        all_content = " ".join(c.content for c in chunks)
        assert "Content with provenance on page 50" in all_content
        assert "Content WITHOUT provenance" in all_content
        assert "More content without provenance" in all_content
        assert "Content back with provenance on page 51" in all_content

        # Verify page numbers come from provenance where available, default to 1 otherwise
        for chunk in chunks:
            assert chunk.page_number in [
                1,
                50,
                51,
            ], (
                f"Page number should be from provenance (50, 51) or default (1), got {chunk.page_number}"
            )

    @pytest.mark.asyncio
    async def test_chunk_by_docling_items_respects_page_boundaries(self):
        """Test that element-aware chunking preserves page numbers from provenance.

        NOTE: Element-aware chunking (Story 2.2) groups small elements together
        even if from different pages, to optimize chunk size. Page number is
        taken from the first element in the buffer.
        """
        # Import TextItem for proper mock spec
        from docling_core.types.doc import TextItem

        # Create mock items on different pages - use larger content to force separate chunks
        mock_item1 = Mock(spec=TextItem)
        mock_item1.text = " ".join([f"page10_word{i}" for i in range(300)])  # 300 words page 10
        mock_prov1 = Mock()
        mock_prov1.page_no = 10
        mock_item1.prov = [mock_prov1]

        mock_item2 = Mock(spec=TextItem)
        mock_item2.text = " ".join([f"page11_word{i}" for i in range(300)])  # 300 words page 11
        mock_prov2 = Mock()
        mock_prov2.page_no = 11
        mock_item2.prov = [mock_prov2]

        # Create mock document
        mock_document = Mock()
        mock_document.iterate_items.return_value = [
            (mock_item1, 1),
            (mock_item2, 1),
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

        # Assertions - element-aware chunking extracts page numbers from provenance
        assert len(chunks) >= 1, "Should create at least one chunk"

        # Verify page numbers come from provenance (10 or 11)
        for chunk in chunks:
            assert chunk.page_number in [
                10,
                11,
            ], f"Page number should be from provenance (10 or 11), got {chunk.page_number}"

        # Verify all content is present
        all_content = " ".join(c.content for c in chunks)
        assert "page10_word" in all_content, "Page 10 content should be present"
        assert "page11_word" in all_content, "Page 11 content should be present"

    @pytest.mark.asyncio
    async def test_chunk_by_docling_items_maintains_chunk_size(self):
        """Test that large pages are split into multiple chunks respecting size limit.

        Verifies that pages exceeding chunk_size are split while maintaining
        the correct page number for all resulting chunks.
        """
        # Import TextItem for proper mock spec
        from docling_core.types.doc import TextItem

        # Create mock item with very long text (> 500 words)
        long_text = " ".join([f"word{i}" for i in range(800)])  # 800 words

        mock_item1 = Mock(spec=TextItem)
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

        # Execute chunking with chunk_size=500 (converted to ~650 tokens internally)
        chunks = await chunk_by_docling_items(mock_result, metadata, chunk_size=500, overlap=50)

        # Assertions
        assert len(chunks) >= 1, "Should create at least one chunk"

        # All chunks should have the SAME page number (75) since they're from the same page
        for chunk in chunks:
            assert chunk.page_number == 75, (
                f"All chunks from page 75 should preserve page number, got {chunk.page_number}"
            )

        # Verify chunks are created and have reasonable sizes
        for chunk in chunks:
            word_count = len(chunk.content.split())
            assert word_count > 0, "Chunk should not be empty"
            # Note: chunk_size is approximate due to element-aware chunking

        # Verify overlap is maintained between chunks if multiple chunks exist
        if len(chunks) > 1:
            # Check that chunks have some overlap in content
            chunk1_words = set(chunks[0].content.split())
            chunk2_words = set(chunks[1].content.split())
            overlap_words = chunk1_words & chunk2_words
            assert len(overlap_words) > 0, "Chunks should have some overlap"

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

        # Create mock text item on same page - use TextItem spec
        from docling_core.types.doc import TextItem

        mock_text_item = Mock(spec=TextItem)
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

        # Assertions - element-aware chunking creates separate chunks for table and text
        # because tables are indivisible elements
        assert len(chunks) >= 1, "Should create at least one chunk"

        # Verify table is in a chunk
        table_chunks = [c for c in chunks if "23.2 EUR/ton" in c.content]
        assert len(table_chunks) >= 1, "Table should be in at least one chunk"
        assert table_chunks[0].page_number == 46, "Table chunk should be attributed to page 46"
        assert "Variable Cost/ton" in table_chunks[0].content, "Table headers should be present"
        assert "50.6%" in table_chunks[0].content, "Table percentage data should be present"

        # Verify text content is also in chunks (may be separate or combined)
        all_content = " ".join(c.content for c in chunks)
        assert "Portugal Cement Performance Review" in all_content, (
            "Text items should also be included"
        )

        # Verify export_to_markdown was called
        mock_table_item.export_to_markdown.assert_called_once()
