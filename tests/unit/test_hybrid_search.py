"""Unit tests for hybrid search (BM25 + semantic fusion) - Story 2.1.

Tests BM25 indexing, score computation, fusion logic, and end-to-end hybrid search.
All tests use mocks to avoid Qdrant/model dependencies.
"""

from unittest.mock import MagicMock, patch

import pytest

from raglite.retrieval.search import fuse_search_results, hybrid_search
from raglite.shared.bm25 import compute_bm25_scores, create_bm25_index
from raglite.shared.models import Chunk, DocumentMetadata, QueryResult


class TestBM25IndexCreation:
    """Test BM25 index creation with rank_bm25 (AC1.4)."""

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

    def test_bm25_index_empty_chunks(self):
        """Test BM25 index creation fails with empty chunks list."""
        # Arrange: Empty chunks list
        chunks = []

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="Cannot create BM25 index from empty chunks"):
            create_bm25_index(chunks)

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


class TestScoreFusion:
    """Test weighted sum fusion of semantic and BM25 scores (AC2.4)."""

    def test_score_fusion_weighted_sum(self):
        """Test fusion with RRF (Reciprocal Rank Fusion) - Story 2.11 fix."""
        # Arrange: Mock semantic results
        semantic_results = [
            QueryResult(
                score=0.9,
                text="Chunk 1",
                source_document="test.pdf",
                page_number=1,
                chunk_index=1,
                word_count=10,
            ),
            QueryResult(
                score=0.8,
                text="Chunk 2",
                source_document="test.pdf",
                page_number=1,
                chunk_index=2,
                word_count=10,
            ),
            QueryResult(
                score=0.7,
                text="Chunk 3",
                source_document="test.pdf",
                page_number=1,
                chunk_index=3,
                word_count=10,
            ),
        ]

        # BM25 scores (raw values, not normalized)
        bm25_scores = [0.0, 5.0, 10.0, 3.0]

        # Create chunk metadata for BM25 score mapping
        chunk_metadata = [
            {"source_document": "test.pdf", "chunk_index": 0},
            {"source_document": "test.pdf", "chunk_index": 1},
            {"source_document": "test.pdf", "chunk_index": 2},
            {"source_document": "test.pdf", "chunk_index": 3},
        ]

        # Act: Fuse with RRF (alpha=0.7)
        fused_results = fuse_search_results(
            semantic_results, bm25_scores, chunk_metadata, alpha=0.7, top_k=3
        )

        # Assert: Verify RRF ranking (not weighted sum!)
        # RRF prioritizes semantic ranking (70%) over BM25 (30%)
        # Semantic ranks: chunk_1=1, chunk_2=2, chunk_3=3
        # BM25 ranks: chunk_2=1 (10.0), chunk_1=2 (5.0), chunk_3=3 (3.0)
        # RRF scores (k=60, alpha=0.7):
        # chunk_1: 0.7/(60+1) + 0.3/(60+2) ≈ 0.0163 (best - semantic rank 1)
        # chunk_2: 0.7/(60+2) + 0.3/(60+1) ≈ 0.0162 (BM25 ranks it 1 but semantic is 2)
        # chunk_3: 0.7/(60+3) + 0.3/(60+3) ≈ 0.0159 (worst - both ranks 3)

        assert len(fused_results) == 3

        # Verify RRF ranking order (semantic priority takes precedence)
        assert fused_results[0].chunk_index == 1  # Highest RRF score (semantic rank 1)
        assert fused_results[1].chunk_index == 2  # Middle RRF score
        assert fused_results[2].chunk_index == 3  # Lowest RRF score (worst in both)

        # Verify correct score order (decreasing)
        assert fused_results[0].score > fused_results[1].score > fused_results[2].score

        # Verify all scores are positive and in RRF range
        assert all(r.score > 0 for r in fused_results)
        assert all(r.score < 0.02 for r in fused_results)  # RRF scores are small

    def test_score_fusion_top_k(self):
        """Test fusion respects top_k parameter."""
        # Arrange: 5 semantic results
        semantic_results = [
            QueryResult(
                score=0.9 - i * 0.1,
                text=f"Chunk {i}",
                source_document="test.pdf",
                page_number=1,
                chunk_index=i,
                word_count=10,
            )
            for i in range(5)
        ]

        bm25_scores = [5.0, 4.0, 3.0, 2.0, 1.0]

        # Create chunk metadata
        chunk_metadata = [{"source_document": "test.pdf", "chunk_index": i} for i in range(5)]

        # Act: Fuse with top_k=3
        fused_results = fuse_search_results(
            semantic_results, bm25_scores, chunk_metadata, alpha=0.7, top_k=3
        )

        # Assert: Only 3 results returned
        assert len(fused_results) == 3

    def test_score_fusion_empty_semantic(self):
        """Test fusion handles empty semantic results."""
        # Arrange: Empty semantic results
        semantic_results = []
        bm25_scores = [5.0, 4.0, 3.0]
        chunk_metadata = [{"source_document": "test.pdf", "chunk_index": i} for i in range(3)]

        # Act: Fuse
        fused_results = fuse_search_results(
            semantic_results, bm25_scores, chunk_metadata, alpha=0.7, top_k=5
        )

        # Assert: Returns empty list
        assert len(fused_results) == 0

    def test_score_fusion_empty_bm25(self):
        """Test fusion falls back to semantic-only if BM25 scores empty."""
        # Arrange: Semantic results but no BM25 scores
        semantic_results = [
            QueryResult(
                score=0.9,
                text="Chunk 0",
                source_document="test.pdf",
                page_number=1,
                chunk_index=0,
                word_count=10,
            ),
        ]
        bm25_scores = []
        chunk_metadata = []

        # Act: Fuse
        fused_results = fuse_search_results(
            semantic_results, bm25_scores, chunk_metadata, alpha=0.7, top_k=5
        )

        # Assert: Returns semantic results unchanged (top_k applied)
        assert len(fused_results) == 1
        assert fused_results[0].score == 0.9  # Unchanged


@pytest.mark.asyncio
class TestHybridSearchEndToEnd:
    """Test hybrid search end-to-end with mocks (AC2.4)."""

    @patch("raglite.retrieval.search.classify_query")
    @patch("raglite.retrieval.search.search_documents")
    @patch("raglite.retrieval.search.load_bm25_index")
    @patch("raglite.retrieval.search.compute_bm25_scores")
    async def test_hybrid_search_combines_results(
        self, mock_compute_bm25, mock_load_bm25, mock_search_docs, mock_classify
    ):
        """Test hybrid search combines semantic and BM25 results."""
        # Arrange: Mock query classifier to return VECTOR_ONLY (skip SQL routing)
        from raglite.retrieval.query_classifier import QueryType

        mock_classify.return_value = QueryType.VECTOR_ONLY

        # Mock semantic search results
        mock_search_docs.return_value = [
            QueryResult(
                score=0.8,
                text="EBITDA margin is 23.2 percent",
                source_document="test.pdf",
                page_number=1,
                chunk_index=0,
                word_count=10,
            ),
            QueryResult(
                score=0.7,
                text="Revenue increased by 15 percent",
                source_document="test.pdf",
                page_number=1,
                chunk_index=1,
                word_count=10,
            ),
        ]

        # Mock BM25 index and scores
        mock_bm25 = MagicMock()
        chunk_metadata = [
            {"source_document": "test.pdf", "chunk_index": 0},
            {"source_document": "test.pdf", "chunk_index": 1},
        ]
        mock_load_bm25.return_value = (mock_bm25, [], chunk_metadata)
        mock_compute_bm25.return_value = [10.0, 5.0]  # BM25 prefers chunk 0

        # Act: Perform hybrid search
        results = await hybrid_search("What is the margin?", top_k=2, alpha=0.7)

        # Assert: Verify search called with wider net
        mock_search_docs.assert_called_once()
        call_kwargs = mock_search_docs.call_args[1]
        assert call_kwargs["top_k"] >= 20  # Casts wider net

        # Verify BM25 index loaded and scores computed
        mock_load_bm25.assert_called_once()
        mock_compute_bm25.assert_called_once_with(mock_bm25, "What is the margin?")

        # Verify results returned
        assert len(results) == 2
        assert all(isinstance(r, QueryResult) for r in results)

    @patch("raglite.retrieval.search.search_documents")
    async def test_hybrid_search_disabled_fallback(self, mock_search_docs):
        """Test hybrid search falls back to semantic-only when disabled."""
        # Arrange: Mock semantic results
        mock_search_docs.return_value = [
            QueryResult(
                score=0.9,
                text="Test result",
                source_document="test.pdf",
                page_number=1,
                chunk_index=0,
                word_count=10,
            ),
        ]

        # Act: Hybrid search with enable_hybrid=False
        results = await hybrid_search("Test query", top_k=5, enable_hybrid=False)

        # Assert: Called semantic search directly with top_k=5 (no expansion)
        mock_search_docs.assert_called_once()
        call_kwargs = mock_search_docs.call_args[1]
        assert call_kwargs["top_k"] == 5  # No expansion when hybrid disabled

        assert len(results) == 1

    @patch("raglite.retrieval.search.search_documents")
    @patch("raglite.retrieval.search.load_bm25_index")
    async def test_hybrid_search_bm25_unavailable_fallback(self, mock_load_bm25, mock_search_docs):
        """Test hybrid search falls back if BM25 index unavailable."""
        # Arrange: Semantic search succeeds, BM25 index missing
        mock_search_docs.return_value = [
            QueryResult(
                score=0.9,
                text="Test result",
                source_document="test.pdf",
                page_number=1,
                chunk_index=0,
                word_count=10,
            ),
        ]
        mock_load_bm25.side_effect = FileNotFoundError("BM25 index not found")

        # Act: Hybrid search with missing BM25 index
        results = await hybrid_search("Test query", top_k=5)

        # Assert: Returns semantic results (fallback)
        assert len(results) == 1
        assert results[0].score == 0.9

    @patch("raglite.retrieval.search.search_documents")
    @patch("raglite.retrieval.search.load_bm25_index")
    @patch("raglite.retrieval.search.compute_bm25_scores")
    async def test_hybrid_search_improves_ranking(
        self, mock_compute_bm25, mock_load_bm25, mock_search_docs
    ):
        """Test hybrid search improves ranking by boosting keyword matches."""
        # Arrange: Semantic ranks chunk_2 higher, but BM25 ranks chunk_1 higher
        mock_search_docs.return_value = [
            QueryResult(
                score=0.85,
                text="Revenue performance metrics quarterly report",
                source_document="test.pdf",
                page_number=1,
                chunk_index=2,  # Changed from 1 to avoid chunk 0 filtering
                word_count=10,
            ),
            QueryResult(
                score=0.80,
                text="EBITDA margin 23.2 EUR per ton Portugal",
                source_document="test.pdf",
                page_number=1,
                chunk_index=1,  # Changed from 0 to avoid filtering
                word_count=10,
            ),
        ]

        # BM25 strongly prefers chunk_1 (has exact keywords)
        # Note: Include chunk 0 (filtered to 0.0) in BM25 scores
        mock_bm25 = MagicMock()
        chunk_metadata = [
            {"source_document": "test.pdf", "chunk_index": 0},
            {"source_document": "test.pdf", "chunk_index": 1},
            {"source_document": "test.pdf", "chunk_index": 2},
        ]
        mock_load_bm25.return_value = (mock_bm25, [], chunk_metadata)
        mock_compute_bm25.return_value = [
            0.0,
            15.0,
            3.0,
        ]  # Chunk 0 filtered, normalized: [0.0, 1.0, 0.2]

        # Act: Hybrid search with alpha=0.7 (Story 2.11: Uses RRF, not weighted sum)
        results = await hybrid_search("EBITDA 23.2", top_k=2, alpha=0.7)

        # Assert: Verify hybrid ranking with RRF algorithm
        # RRF (Reciprocal Rank Fusion) formula: alpha/(k+semantic_rank) + (1-alpha)/(k+bm25_rank), k=60
        # chunk_2: 0.7/(60+1) + 0.3/(60+2) ≈ 0.01632 (semantic rank 1, BM25 rank 2)
        # chunk_1: 0.7/(60+2) + 0.3/(60+1) ≈ 0.01621 (semantic rank 2, BM25 rank 1)
        # RRF prioritizes semantic ranking (70%) over BM25 (30%), so chunk_2 ranks first
        assert results[0].chunk_index == 2  # Semantic score (0.85) wins with alpha=0.7
        assert results[1].chunk_index == 1
        assert results[0].score > results[1].score  # RRF scores are ordered
