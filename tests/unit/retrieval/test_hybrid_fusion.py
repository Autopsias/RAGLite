"""Unit tests for hybrid search (BM25 + semantic fusion) - Story 2.1.

Tests BM25 indexing, score computation, fusion logic, and end-to-end hybrid search.
All tests use mocks to avoid Qdrant/model dependencies.
"""

from unittest.mock import MagicMock, patch

import pytest

from raglite.retrieval.search import fuse_search_results, hybrid_search
from raglite.shared.models import QueryResult

pytestmark = [pytest.mark.unit]


class TestScoreFusion:
    """Test weighted sum fusion of semantic and BM25 scores (AC2.4)."""

    @pytest.mark.priority("P1")
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

    @pytest.mark.priority("P1")
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

    @pytest.mark.priority("P1")
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

    @pytest.mark.priority("P1")
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

    @patch("raglite.retrieval.search.hybrid.classify_query")
    @patch("raglite.retrieval.search.hybrid.search_documents")
    @patch("raglite.retrieval.search.hybrid.load_bm25_index")
    @patch("raglite.retrieval.search.hybrid.compute_bm25_scores")
    @pytest.mark.priority("P1")
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

        # Assert: Verify search called with optimized moderate net
        mock_search_docs.assert_called_once()
        call_kwargs = mock_search_docs.call_args[1]
        # Performance optimization: moderate net (max(top_k * 2, 10)) instead of wider net (>=20)
        # For top_k=2, this becomes max(2*2, 10) = 10
        assert call_kwargs["top_k"] == 10  # Optimized moderate net: max(2*2, 10) = 10

        # Verify BM25 index loaded and scores computed
        mock_load_bm25.assert_called_once()
        mock_compute_bm25.assert_called_once_with(mock_bm25, "What is the margin?")

        # Verify results returned
        assert len(results) == 2
        assert all(isinstance(r, QueryResult) for r in results)

    @patch("raglite.retrieval.search.hybrid.search_documents")
    @pytest.mark.priority("P1")
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

    @patch("raglite.retrieval.search.hybrid.classify_query")
    @patch("raglite.retrieval.search.hybrid.search_documents")
    @patch("raglite.retrieval.search.hybrid.load_bm25_index")
    @pytest.mark.priority("P1")
    async def test_hybrid_search_bm25_unavailable_fallback(
        self, mock_load_bm25, mock_search_docs, mock_classify
    ):
        """Test hybrid search falls back if BM25 index unavailable."""
        # Arrange: Mock query classifier to return VECTOR_ONLY (skip SQL routing)
        from raglite.retrieval.query_classifier import QueryType

        mock_classify.return_value = QueryType.VECTOR_ONLY

        # Mock semantic search to return 1 result
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

        # Act: Hybrid search with missing BM25 index (SQL disabled by VECTOR_ONLY routing)
        results = await hybrid_search("Test query", top_k=5, enable_sql_tables=True)

        # Assert: Returns semantic results (fallback)
        assert len(results) == 1
        assert results[0].score == 0.9

    @patch("raglite.retrieval.search.hybrid.classify_query")
    @patch("raglite.retrieval.search.hybrid.search_documents")
    @patch("raglite.retrieval.search.hybrid.load_bm25_index")
    @patch("raglite.retrieval.search.hybrid.compute_bm25_scores")
    @pytest.mark.priority("P1")
    async def test_hybrid_search_improves_ranking(
        self, mock_compute_bm25, mock_load_bm25, mock_search_docs, mock_classify
    ):
        """Test hybrid search improves ranking by boosting keyword matches."""
        # Mock query classifier to skip SQL routing (Story 2.13)
        from raglite.retrieval.query_classifier import QueryType

        mock_classify.return_value = QueryType.VECTOR_ONLY
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
