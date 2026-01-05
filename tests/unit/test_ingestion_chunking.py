"""Unit tests for document chunking functionality (Story 1.4).

Tests the chunk_document function with various document types and sizes.
"""

from datetime import datetime

import pytest

from raglite.ingestion.pipeline import chunk_document
from raglite.shared.models import Chunk, DocumentMetadata


class TestChunkDocument:
    """Test suite for document chunking functionality."""

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_chunk_document_basic(self):
        """Test basic chunking with 1000-word document.

        Verifies chunk_document returns correct number of chunks with proper
        size and overlap. AC1, AC6.
        """
        # Create 1000-word test text
        words = [f"word{i}" for i in range(1000)]
        full_text = " ".join(words)

        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=10,
            source_path="/tmp/test.pdf",
        )

        # Chunk with default parameters (500 words, 50 overlap)
        chunks = await chunk_document(full_text, metadata, chunk_size=500, overlap=50)

        # Should create 3 chunks: [0:500], [450:950], [900:1000]
        # Chunk 1: words 0-499 (500 words)
        # Chunk 2: words 450-949 (500 words, 50-word overlap with chunk 1)
        # Chunk 3: words 900-999 (100 words, 50-word overlap with chunk 2)
        assert len(chunks) == 3
        assert isinstance(chunks[0], Chunk)
        assert chunks[0].chunk_id == "test.pdf_0"
        assert chunks[1].chunk_id == "test.pdf_1"
        assert chunks[2].chunk_id == "test.pdf_2"

        # Verify chunk sizes
        chunk1_words = chunks[0].content.split()
        chunk2_words = chunks[1].content.split()
        chunk3_words = chunks[2].content.split()

        assert len(chunk1_words) == 500
        assert len(chunk2_words) == 500
        assert len(chunk3_words) == 100  # Last chunk is shorter

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_chunk_overlap(self):
        """Test that chunks have correct 50-word overlap.

        Verifies last 50 words of chunk N match first 50 words of chunk N+1.
        AC1, AC6.
        """
        # Create 1000-word test text with numbered words
        words = [f"word{i}" for i in range(1000)]
        full_text = " ".join(words)

        metadata = DocumentMetadata(
            filename="overlap_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=5,
            source_path="/tmp/overlap_test.pdf",
        )

        chunks = await chunk_document(full_text, metadata, chunk_size=500, overlap=50)

        # Verify overlap between chunk 0 and chunk 1
        chunk0_words = chunks[0].content.split()
        chunk1_words = chunks[1].content.split()

        # Last 50 words of chunk 0
        chunk0_last_50 = chunk0_words[-50:]

        # First 50 words of chunk 1
        chunk1_first_50 = chunk1_words[:50]

        # Should match exactly
        assert chunk0_last_50 == chunk1_first_50

        # Verify specific word positions
        assert chunk0_last_50[0] == "word450"
        assert chunk0_last_50[-1] == "word499"
        assert chunk1_first_50[0] == "word450"
        assert chunk1_first_50[-1] == "word499"

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_chunk_page_numbers(self):
        """CRITICAL: Verify all chunks have page_number != None.

        This test addresses AC8 and AC9 - ensures page numbers are populated
        for all chunks to enable source attribution (NFR7 requirement).
        """
        # Create multi-page document (2000 words ~ 10 pages)
        words = [f"page{i % 10}_word{i}" for i in range(2000)]
        full_text = " ".join(words)

        metadata = DocumentMetadata(
            filename="multipage.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=10,
            source_path="/tmp/multipage.pdf",
        )

        chunks = await chunk_document(full_text, metadata, chunk_size=500, overlap=50)

        # CRITICAL: All chunks must have page_number != None and > 0
        for idx, chunk in enumerate(chunks):
            assert chunk.page_number is not None, f"Chunk {idx} has None page_number"
            assert chunk.page_number > 0, (
                f"Chunk {idx} has invalid page_number: {chunk.page_number}"
            )
            assert chunk.page_number <= metadata.page_count, (
                f"Chunk {idx} page_number {chunk.page_number} exceeds page_count {metadata.page_count}"
            )

        # Verify page numbers are reasonable (should increase through document)
        # First chunk should be page 1
        assert chunks[0].page_number == 1

        # Last chunk should be near last page (within 1-2 pages)
        assert chunks[-1].page_number >= metadata.page_count - 2

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_chunk_short_document(self):
        """Test document shorter than chunk size.

        Should return single chunk with correct page number. AC1, AC6.
        """
        # Create 200-word document (less than 500-word chunk size)
        words = [f"short{i}" for i in range(200)]
        full_text = " ".join(words)

        metadata = DocumentMetadata(
            filename="short.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=2,
            source_path="/tmp/short.pdf",
        )

        chunks = await chunk_document(full_text, metadata, chunk_size=500, overlap=50)

        # Should return exactly 1 chunk
        assert len(chunks) == 1
        assert chunks[0].chunk_id == "short.pdf_0"
        assert len(chunks[0].content.split()) == 200
        assert chunks[0].page_number == 1  # Should be page 1

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_chunk_empty_document(self):
        """Test empty document handling.

        Should return empty list without crashing. AC6.
        """
        metadata = DocumentMetadata(
            filename="empty.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=0,
            source_path="/tmp/empty.pdf",
        )

        # Test with empty string
        chunks = await chunk_document("", metadata)
        assert chunks == []

        # Test with whitespace only
        chunks = await chunk_document("   \n\n  ", metadata)
        assert chunks == []

    @pytest.mark.priority("P3")
    @pytest.mark.asyncio
    async def test_chunk_invalid_parameters(self):
        """Test invalid chunk_size or overlap parameters.

        Should raise ValueError with clear message. AC6.
        """
        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=5,
            source_path="/tmp/test.pdf",
        )

        full_text = "Some test content here"

        # Test negative chunk_size
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            await chunk_document(full_text, metadata, chunk_size=-100, overlap=50)

        # Test zero chunk_size
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            await chunk_document(full_text, metadata, chunk_size=0, overlap=50)

        # Test negative overlap
        with pytest.raises(ValueError, match="overlap must be non-negative"):
            await chunk_document(full_text, metadata, chunk_size=500, overlap=-10)

        # Test overlap >= chunk_size
        with pytest.raises(ValueError, match="overlap.*must be less than chunk_size"):
            await chunk_document(full_text, metadata, chunk_size=500, overlap=500)

        with pytest.raises(ValueError, match="overlap.*must be less than chunk_size"):
            await chunk_document(full_text, metadata, chunk_size=500, overlap=600)
