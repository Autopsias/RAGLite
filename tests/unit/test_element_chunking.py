"""Unit tests for element-aware chunking algorithm (Story 2.2).

Tests the chunk_elements() function and its helpers that implement
structure-aware chunking respecting element boundaries.
"""

import pytest

from raglite.ingestion.pipeline import (
    _create_chunk,
    _create_chunk_from_buffer,
    _get_overlap,
    _split_large_table,
    chunk_elements,
)
from raglite.shared.models import (
    DocumentElement,
    DocumentMetadata,
    ElementType,
)


class TestChunkElements:
    """Test suite for chunk_elements() function."""

    @pytest.fixture
    def doc_metadata(self):
        """Create sample document metadata for testing."""
        return DocumentMetadata(
            filename="test_document.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-01-18T10:00:00Z",
            page_count=10,
            source_path="/path/to/test_document.pdf",
            chunk_count=0,
        )

    def test_table_not_split_under_2048_tokens(self, doc_metadata):
        """Test tables <2,048 tokens stored as single chunk (AC1)."""
        # Create small table element
        table_elem = DocumentElement(
            element_id="table_1",
            type=ElementType.TABLE,
            content="| Col1 | Col2 |\n|------|------|\n| A | B |",
            page_number=5,
            section_title="Revenue",
            token_count=50,  # < 2,048
            metadata={"docling_type": "TableItem"},
        )

        # Chunk elements
        chunks = chunk_elements([table_elem], doc_metadata, max_tokens=512)

        # Assertions (AC1)
        assert len(chunks) == 1, "Small table should be stored as single chunk"
        assert chunks[0].element_type == ElementType.TABLE
        assert chunks[0].section_title == "Revenue"
        assert "| Col1 | Col2 |" in chunks[0].content
        assert chunks[0].page_number == 5

    def test_large_table_split_at_row_boundaries(self, doc_metadata):
        """Test tables >2,048 tokens split at row boundaries (AC1)."""
        # Create large table content (>2,048 tokens)
        # Markdown table with header + many rows
        header = "| Column1 | Column2 | Column3 |\n|---------|---------|---------|"
        rows = [f"\n| Row{i} | Data{i} | Value{i} |" for i in range(200)]  # Many rows
        large_table_content = header + "".join(rows)

        table_elem = DocumentElement(
            element_id="large_table",
            type=ElementType.TABLE,
            content=large_table_content,
            page_number=10,
            section_title="Cash Flow",
            token_count=2500,  # > 2,048
            metadata={"docling_type": "TableItem"},
        )

        # Chunk elements
        chunks = chunk_elements([table_elem], doc_metadata, max_tokens=512)

        # Assertions (AC1)
        assert len(chunks) > 1, "Large table should be split into multiple chunks"

        # All chunks should be tables
        for chunk in chunks:
            assert chunk.element_type == ElementType.TABLE
            assert chunk.section_title == "Cash Flow"
            assert chunk.page_number == 10
            # Each chunk should have header row
            assert "| Column1 | Column2 | Column3 |" in chunk.content
            assert "|---------|---------|---------|" in chunk.content

    def test_section_header_grouped_with_paragraph(self, doc_metadata):
        """Test section headers grouped with first paragraph (AC1)."""
        # Create section header + paragraph
        section = DocumentElement(
            element_id="sec_1",
            type=ElementType.SECTION_HEADER,
            content="Operating Expenses",
            page_number=7,
            section_title=None,  # Section itself has no parent
            token_count=5,
            metadata={"docling_type": "SectionHeaderItem"},
        )
        paragraph = DocumentElement(
            element_id="para_1",
            type=ElementType.PARAGRAPH,
            content="Our operating expenses increased by 12% year-over-year...",
            page_number=7,
            section_title="Operating Expenses",
            token_count=100,
            metadata={"docling_type": "ParagraphItem"},
        )

        # Chunk elements
        chunks = chunk_elements([section, paragraph], doc_metadata, max_tokens=512)

        # Assertions (AC1)
        assert len(chunks) == 1, "Section + paragraph should be grouped in one chunk"
        assert "Operating Expenses" in chunks[0].content
        assert "12% year-over-year" in chunks[0].content
        assert chunks[0].section_title == "Operating Expenses"

    def test_paragraphs_accumulate_until_limit(self, doc_metadata):
        """Test paragraphs accumulate until max_tokens reached."""
        # Create multiple paragraphs with realistic token counts
        # Each paragraph: "This is paragraph {i} with some content. " * 20 = 8 words * 20 = 160 words ≈ 208 tokens
        paragraphs = [
            DocumentElement(
                element_id=f"para_{i}",
                type=ElementType.PARAGRAPH,
                content=f"This is paragraph {i} with some content. " * 20,
                page_number=1,
                section_title="Introduction",
                token_count=208,  # Realistic: 8 words * 20 repetitions * 1.3 tokens/word
                metadata={"docling_type": "ParagraphItem"},
            )
            for i in range(30)
        ]

        # Chunk elements with max_tokens=512
        chunks = chunk_elements(paragraphs, doc_metadata, max_tokens=512)

        # Assertions
        assert len(chunks) > 1, "Multiple paragraphs should create multiple chunks"
        # Each chunk should not exceed max_tokens significantly
        # (some variation due to overlap which is 128 tokens by default)
        for chunk in chunks:
            # Rough token estimate: word count * 1.3
            estimated_tokens = chunk.word_count * 1.3
            # Allow up to max_tokens + overlap_tokens + some buffer (512 + 128 + 100 = 740)
            assert estimated_tokens <= 740, f"Chunk exceeds max tokens: {estimated_tokens}"

    def test_section_context_preserved_across_chunks(self, doc_metadata):
        """Test section_title preserved for all chunks in that section."""
        # Create section + multiple paragraphs
        elements = [
            DocumentElement(
                element_id="sec_1",
                type=ElementType.SECTION_HEADER,
                content="Financial Performance",
                page_number=1,
                section_title=None,
                token_count=5,
            )
        ]

        # Add many paragraphs to force multiple chunks
        for i in range(50):
            elements.append(
                DocumentElement(
                    element_id=f"para_{i}",
                    type=ElementType.PARAGRAPH,
                    content=f"Paragraph {i} content. " * 10,
                    page_number=1,
                    section_title="Financial Performance",
                    token_count=13,
                )
            )

        # Chunk elements
        chunks = chunk_elements(elements, doc_metadata, max_tokens=512)

        # Assertions (AC2)
        assert len(chunks) > 1, "Should create multiple chunks"
        # All chunks should preserve section context
        for chunk in chunks:
            assert chunk.section_title == "Financial Performance"

    def test_chunk_metadata_includes_element_type(self, doc_metadata):
        """Test each chunk includes element_type field (AC2)."""
        # Create mixed elements
        elements = [
            DocumentElement(
                element_id="table_1",
                type=ElementType.TABLE,
                content="| A | B |\n|---|---|\n| 1 | 2 |",
                page_number=1,
                section_title="Data",
                token_count=20,
            ),
            DocumentElement(
                element_id="para_1",
                type=ElementType.PARAGRAPH,
                content="This is a paragraph",
                page_number=1,
                section_title="Data",
                token_count=10,
            ),
        ]

        # Chunk elements
        chunks = chunk_elements(elements, doc_metadata, max_tokens=512)

        # Assertions (AC2)
        assert len(chunks) == 2
        assert chunks[0].element_type == ElementType.TABLE
        assert chunks[1].element_type == ElementType.PARAGRAPH

    def test_empty_elements_list(self, doc_metadata):
        """Test chunking empty elements list returns empty chunks."""
        chunks = chunk_elements([], doc_metadata, max_tokens=512)
        assert len(chunks) == 0


class TestSplitLargeTable:
    """Test suite for _split_large_table() helper."""

    def test_split_large_table_preserves_header(self):
        """Test that header row is preserved in all table chunks."""
        # Create large table element
        header_lines = "| Col1 | Col2 |\n|------|------|"
        rows = [f"\n| Row{i} | Data{i} |" for i in range(100)]
        large_table_content = header_lines + "".join(rows)

        table_elem = DocumentElement(
            element_id="large_table",
            type=ElementType.TABLE,
            content=large_table_content,
            page_number=1,
            section_title="Test",
            token_count=2500,
        )

        # Split table
        chunks = _split_large_table(table_elem, max_tokens=512)

        # Assertions (AC1)
        assert len(chunks) > 1, "Large table should be split"
        for chunk_content in chunks:
            assert "| Col1 | Col2 |" in chunk_content, "Header row must be in every chunk"
            assert "|------|------|" in chunk_content, "Separator row must be in every chunk"

    def test_split_large_table_no_partial_rows(self):
        """Test that table chunks contain only complete rows (AC1)."""
        # Create table
        header = "| A | B |\n|---|---|"
        rows = [f"\n| {i} | {i * 2} |" for i in range(50)]
        table_content = header + "".join(rows)

        table_elem = DocumentElement(
            element_id="table",
            type=ElementType.TABLE,
            content=table_content,
            page_number=1,
            token_count=1500,
        )

        # Split table
        chunks = _split_large_table(table_elem, max_tokens=512)

        # Assertions (AC1)
        for chunk_content in chunks:
            lines = chunk_content.split("\n")
            # Each chunk should have header (2 lines) + complete rows
            assert len(lines) >= 3, "Chunk should have at least header + 1 data row"
            # All data rows should be complete (contain |)
            for line in lines[2:]:  # Skip header + separator
                if line.strip():
                    assert line.count("|") >= 2, f"Row appears incomplete: {line}"

    def test_split_small_table_returns_single_chunk(self):
        """Test that small tables are not split."""
        # Create small table
        small_table = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"

        table_elem = DocumentElement(
            element_id="small_table",
            type=ElementType.TABLE,
            content=small_table,
            page_number=1,
            token_count=30,
        )

        # Split table
        chunks = _split_large_table(table_elem, max_tokens=512)

        # Assertions
        assert len(chunks) == 1, "Small table should not be split"
        assert chunks[0] == small_table


class TestHelperFunctions:
    """Test suite for helper functions."""

    @pytest.fixture
    def doc_metadata(self):
        """Create sample document metadata."""
        return DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-01-18T10:00:00Z",
            page_count=10,
            source_path="/path/to/test.pdf",
        )

    def test_create_chunk(self, doc_metadata):
        """Test _create_chunk() creates chunk with correct metadata."""
        chunk = _create_chunk(
            content="Test content",
            element_type=ElementType.TABLE,
            section_title="Revenue",
            page_number=5,
            chunk_index=3,
            doc_metadata=doc_metadata,
        )

        # Assertions
        assert chunk.content == "Test content"
        assert chunk.element_type == ElementType.TABLE
        assert chunk.section_title == "Revenue"
        assert chunk.page_number == 5
        assert chunk.chunk_index == 3
        assert chunk.word_count == 2  # "Test content" = 2 words

    def test_create_chunk_from_buffer_mixed_elements(self, doc_metadata):
        """Test _create_chunk_from_buffer() marks mixed elements as MIXED."""
        # Create buffer with different element types
        buffer = [
            DocumentElement(
                element_id="sec",
                type=ElementType.SECTION_HEADER,
                content="Section",
                page_number=1,
                token_count=5,
            ),
            DocumentElement(
                element_id="para",
                type=ElementType.PARAGRAPH,
                content="Paragraph",
                page_number=1,
                token_count=10,
            ),
        ]

        chunk = _create_chunk_from_buffer(
            buffer=buffer,
            section_title="Test Section",
            chunk_index=0,
            doc_metadata=doc_metadata,
        )

        # Assertions
        assert chunk.element_type == ElementType.MIXED
        assert "Section" in chunk.content
        assert "Paragraph" in chunk.content
        assert chunk.section_title == "Test Section"

    def test_create_chunk_from_buffer_single_element_type(self, doc_metadata):
        """Test _create_chunk_from_buffer() with homogeneous buffer."""
        # Create buffer with same element type
        buffer = [
            DocumentElement(
                element_id="para1",
                type=ElementType.PARAGRAPH,
                content="First",
                page_number=1,
                token_count=5,
            ),
            DocumentElement(
                element_id="para2",
                type=ElementType.PARAGRAPH,
                content="Second",
                page_number=1,
                token_count=5,
            ),
        ]

        chunk = _create_chunk_from_buffer(
            buffer=buffer,
            section_title=None,
            chunk_index=0,
            doc_metadata=doc_metadata,
        )

        # Assertions
        assert chunk.element_type == ElementType.PARAGRAPH  # All same type
        assert "First" in chunk.content
        assert "Second" in chunk.content

    def test_get_overlap_returns_last_elements(self):
        """Test _get_overlap() returns elements from end of buffer."""
        # Create buffer
        buffer = [
            DocumentElement(
                element_id="elem1",
                type=ElementType.PARAGRAPH,
                content="First",
                page_number=1,
                token_count=10,
            ),
            DocumentElement(
                element_id="elem2",
                type=ElementType.PARAGRAPH,
                content="Second",
                page_number=1,
                token_count=10,
            ),
            DocumentElement(
                element_id="elem3",
                type=ElementType.PARAGRAPH,
                content="Third",
                page_number=1,
                token_count=10,
            ),
        ]

        # Get overlap of 15 tokens
        overlap = _get_overlap(buffer, overlap_tokens=15)

        # Assertions
        # Should return last element (10 tokens) only, as adding elem2 would exceed 15
        assert len(overlap) == 1
        assert overlap[0].element_id == "elem3"

    def test_get_overlap_with_larger_limit(self):
        """Test _get_overlap() with overlap larger than single element."""
        buffer = [
            DocumentElement(
                element_id="elem1",
                type=ElementType.PARAGRAPH,
                content="First",
                page_number=1,
                token_count=10,
            ),
            DocumentElement(
                element_id="elem2",
                type=ElementType.PARAGRAPH,
                content="Second",
                page_number=1,
                token_count=10,
            ),
        ]

        # Get overlap of 25 tokens (should include both elements)
        overlap = _get_overlap(buffer, overlap_tokens=25)

        # Assertions
        assert len(overlap) == 2
        assert overlap[0].element_id == "elem1"
        assert overlap[1].element_id == "elem2"
