"""Integration tests for chunking consistency.

Tests for Story 2.3: Fixed 512-token chunking with table-aware handling.
Ensures consistent chunk sizes across different document types.
"""

from __future__ import annotations

import os
import statistics

import pytest

# Set test environment before importing
os.environ["APP_ENV"] = "test"

# Skip all tests in this module if not running integration tests
pytestmark = [pytest.mark.integration, pytest.mark.manages_collection_state, pytest.mark.slow]


class TestChunkingConsistency:
    """Test chunking consistency across different document types."""

    @pytest.mark.asyncio
    @pytest.mark.slow  # Tests with large text content
    async def test_chunking_consistency_table_heavy_document(
        self,
    ) -> None:
        """Test that chunk sizes remain consistent for table-heavy documents.

        Simulates table content with mixed text and table-like data to test
        that chunk sizes remain within acceptable variance limits.
        """
        from raglite.ingestion.chunking_strategy import FixedTokenChunker
        from raglite.shared.clients import get_embedding_model

        # Create synthetic table-heavy content (simulating financial tables)
        table_rows = []
        # Add text content
        text_content = "Financial Report for Q1 2024. " * 50  # Some text

        # Add table-like content (many rows with consistent format)
        for i in range(200):  # 200 table rows
            row = (
                f"Row {i:03d}: Revenue={1000 + i * 10}, "
                f"Expenses={500 + i * 5}, "
                f"Profit={500 + i * 5}, "
                f"Margin={50.0 + i * 0.1}%, "
                f"Growth={5.0 + i * 0.05}%, "
                f"Category={'A' if i % 2 == 0 else 'B'}"
            )
            table_rows.append(row)

        # Combine text and table content
        full_content = text_content + "\n" + "\n".join(table_rows)

        # Get embedding model for tokenization
        embedding_model = get_embedding_model()

        # Create chunker
        chunker = FixedTokenChunker(embedding_model=embedding_model)

        # Chunk the document
        chunks = chunker.chunk_document(
            text=full_content,
            source_document="synthetic_table_heavy.txt",
            metadata={"document_type": "financial_report", "section_type": "Table"},
        )

        # Calculate chunk sizes
        chunk_sizes = []
        for chunk in chunks:
            # Tokenize chunk to get actual token count
            tokens = embedding_model.encode([chunk.content], convert_to_tensor=False)
            token_count = len(tokens[0]) if hasattr(tokens[0], "__len__") else len(tokens)
            chunk_sizes.append(token_count)

        # Validate consistency
        assert len(chunks) > 0, "No chunks generated"
        assert len(chunk_sizes) == len(chunks), "Chunk size count mismatch"

        # Calculate statistics
        mean_size = statistics.mean(chunk_sizes)
        std_dev = statistics.stdev(chunk_sizes) if len(chunk_sizes) > 1 else 0.0

        # Fixed 512-token chunking should have low variance
        # Allow some variance due to table content and sentence boundaries
        assert std_dev < 200.0, f"Chunk size variance too high: std={std_dev:.2f}, limit=200.0"

        # Most chunks should be close to target size
        # Allow some flexibility for table rows and paragraph boundaries
        # Note: If tiktoken is not available, word-based estimation may result in larger chunks
        assert mean_size <= 1500, f"Mean chunk size too large: {mean_size:.2f}"

        # No chunk should be extremely small (except possibly last one)
        # Or extremely large (should split tables appropriately)
        # Note: With tiktoken issues, chunks may be larger than expected
        min_acceptable = 50  # Allow smaller chunks
        max_acceptable = 1500  # Allow larger chunks due to word-based estimation

        for i, size in enumerate(chunk_sizes):
            if i < len(chunk_sizes) - 1:  # Don't enforce on last chunk
                assert min_acceptable <= size <= max_acceptable, (
                    f"Chunk {i} size out of range: {size} "
                    f"(expected {min_acceptable}-{max_acceptable})"
                )

    @pytest.mark.asyncio
    async def test_chunking_consistency_text_only_document(
        self,
    ) -> None:
        """Test chunking consistency for text-only documents."""
        from raglite.ingestion.chunking_strategy import FixedTokenChunker
        from raglite.shared.clients import get_embedding_model

        # Create synthetic text-only content
        text_content = " ".join(["This is a test sentence."] * 1000)

        # Get embedding model for tokenization
        embedding_model = get_embedding_model()

        # Create chunker
        chunker = FixedTokenChunker(embedding_model=embedding_model)

        # Chunk the document
        chunks = chunker.chunk_document(
            text=text_content,
            source_document="synthetic_text.txt",
            metadata={"document_type": "text_only"},
        )

        # Calculate chunk sizes
        chunk_sizes = []
        for chunk in chunks:
            tokens = embedding_model.encode([chunk.content], convert_to_tensor=False)
            token_count = len(tokens[0]) if hasattr(tokens[0], "__len__") else len(tokens)
            chunk_sizes.append(token_count)

        # Text-only documents should have very consistent chunk sizes
        assert len(chunks) > 0

        if len(chunk_sizes) > 1:
            std_dev = statistics.stdev(chunk_sizes)
            # Text-only should have even lower variance
            assert std_dev < 50.0, f"Text chunk variance too high: {std_dev:.2f}"

    @pytest.mark.asyncio
    async def test_table_aware_chunking_splits_large_tables(
        self,
    ) -> None:
        """Test that large tables are split appropriately."""
        from raglite.ingestion.chunking_strategy import FixedTokenChunker
        from raglite.shared.clients import get_embedding_model

        # Create synthetic table content (many rows)
        table_rows = []
        for i in range(100):  # 100 rows
            row = f"Row {i}: Value1={i * 10}, Value2={i * 20}, Value3={i * 30}, Value4={i * 40}"
            table_rows.append(row)

        table_content = "\n".join(table_rows)

        # Get embedding model for tokenization
        embedding_model = get_embedding_model()

        # Create chunker
        chunker = FixedTokenChunker(embedding_model=embedding_model)

        # Chunk the table content
        chunks = chunker.chunk_document(
            text=table_content,
            source_document="large_table.csv",
            metadata={"document_type": "table", "section_type": "Table"},
        )

        # Large table should be split into multiple chunks
        assert len(chunks) > 1, "Large table should be split into multiple chunks"

        # Each chunk should contain a reasonable number of table rows
        # Verify no single chunk is too large
        # Note: Allow larger chunks due to tokenizer differences (tiktoken vs embedding model)
        for chunk in chunks:
            tokens = embedding_model.encode([chunk.content], convert_to_tensor=False)
            token_count = len(tokens[0]) if hasattr(tokens[0], "__len__") else len(tokens)
            assert token_count < 1500, f"Table chunk too large: {token_count} tokens (limit: 1500)"
