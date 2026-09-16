"""Unit tests for hybrid search (BM25 + semantic fusion) - Story 2.1.

Tests BM25 indexing, score computation, fusion logic, and end-to-end hybrid search.
All tests use mocks to avoid Qdrant/model dependencies.
"""

import pytest

from raglite.shared.bm25 import compute_bm25_scores, create_bm25_index
from raglite.shared.models import Chunk, DocumentMetadata

pytestmark = [pytest.mark.unit]


class TestBM25IndexCreation:
    """Test BM25 index creation with rank_bm25 (AC1.4)."""

    @pytest.mark.priority("P1")
    def test_bm25_index_creation_success(self):
        """Test successful BM25 index creation with 10 sample chunks."""
        # Arrange: Create 10 test chunks
        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-01-01T00:00:00Z",
            page_count=5,
            source_path="/test/test.pdf",
            chunk_count=10,
        )

        chunks = [
            Chunk(
                chunk_id=f"test_{i}",
                content=f"Financial report EBITDA margin {i} EUR/ton revenue {i * 10}",
                metadata=metadata,
                page_number=1 + (i // 2),
                chunk_index=i,
                embedding=[],
            )
            for i in range(10)
        ]

        # Act: Create BM25 index
        bm25, tokenized_docs = create_bm25_index(chunks, k1=1.7, b=0.6)

        # Assert: Verify index created successfully
        assert bm25 is not None
        assert len(tokenized_docs) == 10
        assert all(len(doc) > 0 for doc in tokenized_docs)  # All docs tokenized

        # Verify tokenization
        assert "EBITDA" in tokenized_docs[0]
        assert "margin" in tokenized_docs[0]

        # Verify BM25 can compute scores
        query_tokens = ["EBITDA", "margin"]
        scores = bm25.get_scores(query_tokens)
        assert len(scores) == 10
        assert all(isinstance(s, int | float) for s in scores)

    @pytest.mark.priority("P2")
    def test_bm25_index_empty_chunks(self):
        """Test BM25 index creation fails with empty chunks list."""
        # Arrange: Empty chunks list
        chunks = []

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="Cannot create BM25 index from empty chunks"):
            create_bm25_index(chunks)

    @pytest.mark.priority("P1")
    def test_bm25_index_parameters(self):
        """Test BM25 index respects k1 and b parameters."""
        # Arrange: Create chunks
        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-01-01T00:00:00Z",
            page_count=1,
            source_path="/test/test.pdf",
            chunk_count=3,
        )

        chunks = [
            Chunk(
                chunk_id=f"test_{i}",
                content="EBITDA margin revenue financial report",
                metadata=metadata,
                page_number=1,
                chunk_index=i,
                embedding=[],
            )
            for i in range(3)
        ]

        # Act: Create index with custom parameters
        bm25, _ = create_bm25_index(chunks, k1=1.7, b=0.6)

        # Assert: Index parameters set (stored in BM25Okapi object)
        assert bm25.k1 == 1.7
        assert bm25.b == 0.6


class TestBM25Query:
    """Test BM25 score computation for queries (AC1.4)."""

    @pytest.mark.priority("P1")
    def test_bm25_query_scores(self):
        """Test BM25 query returns scores for all chunks."""
        # Arrange: Create BM25 index with financial content
        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-01-01T00:00:00Z",
            page_count=1,
            source_path="/test/test.pdf",
            chunk_count=5,
        )

        chunks = [
            Chunk(
                chunk_id="chunk_0",
                content="EBITDA margin is 23.2 percent for Portugal Cement",
                metadata=metadata,
                page_number=1,
                chunk_index=0,
                embedding=[],
            ),
            Chunk(
                chunk_id="chunk_1",
                content="Revenue increased by 15 percent year over year",
                metadata=metadata,
                page_number=1,
                chunk_index=1,
                embedding=[],
            ),
            Chunk(
                chunk_id="chunk_2",
                content="Variable cost per ton is 23.2 EUR in Portugal",
                metadata=metadata,
                page_number=1,
                chunk_index=2,
                embedding=[],
            ),
            Chunk(
                chunk_id="chunk_3",
                content="EBITDA IFRS margin shows strong performance",
                metadata=metadata,
                page_number=1,
                chunk_index=3,
                embedding=[],
            ),
            Chunk(
                chunk_id="chunk_4",
                content="The company reported quarterly earnings today",
                metadata=metadata,
                page_number=1,
                chunk_index=4,
                embedding=[],
            ),
        ]

        bm25, tokenized_docs = create_bm25_index(chunks, k1=1.7, b=0.6)

        # Act: Query with "EBITDA"
        scores = compute_bm25_scores(bm25, "EBITDA")

        # Assert: Scores returned for all chunks
        assert len(scores) == 5
        assert all(isinstance(s, int | float) for s in scores)

        # Chunks with "EBITDA" should have higher scores
        assert scores[0] > scores[1]  # chunk_0 has EBITDA, chunk_1 doesn't
        assert scores[3] > scores[4]  # chunk_3 has EBITDA, chunk_4 doesn't

    @pytest.mark.priority("P1")
    def test_bm25_query_relevant_ranking(self):
        """Test BM25 ranks relevant chunks higher."""
        # Arrange: Create chunks with varying relevance
        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-01-01T00:00:00Z",
            page_count=1,
            source_path="/test/test.pdf",
            chunk_count=3,
        )

        chunks = [
            Chunk(
                chunk_id="highly_relevant",
                content="EBITDA margin EBITDA EBITDA financial metric",
                metadata=metadata,
                page_number=1,
                chunk_index=0,
                embedding=[],
            ),
            Chunk(
                chunk_id="somewhat_relevant",
                content="The EBITDA shows positive trends this quarter",
                metadata=metadata,
                page_number=1,
                chunk_index=1,
                embedding=[],
            ),
            Chunk(
                chunk_id="not_relevant",
                content="Revenue and expenses are reported separately",
                metadata=metadata,
                page_number=1,
                chunk_index=2,
                embedding=[],
            ),
        ]

        bm25, _ = create_bm25_index(chunks, k1=1.7, b=0.6)

        # Act: Query with "EBITDA"
        scores = compute_bm25_scores(bm25, "EBITDA")

        # Assert: Highly relevant chunk has highest score
        assert scores[0] > scores[1] > scores[2]
