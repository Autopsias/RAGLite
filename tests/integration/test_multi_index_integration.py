"""Integration tests for multi-index search (Story 2.7 AC4).

Tests the end-to-end multi-index search pipeline including:
- Query classification
- Index routing (SQL_ONLY, VECTOR_ONLY, HYBRID)
- Result fusion
- Error handling and fallback logic
"""

import pytest

from raglite.retrieval.multi_index_search import (
    MultiIndexSearchError,
    SearchResult,
    merge_results,
    multi_index_search,
)
from raglite.retrieval.query_classifier import QueryType, classify_query


class TestMultiIndexIntegration:
    """Integration tests for multi-index search pipeline."""

    @pytest.mark.asyncio
    async def test_vector_only_query_routing(self) -> None:
        """Test that VECTOR_ONLY queries route to Qdrant only."""
        query = "Explain the company's growth strategy"

        # Verify classification
        query_type = classify_query(query)
        assert query_type == QueryType.VECTOR_ONLY

        # Execute search (should only hit Qdrant, not PostgreSQL)
        # NOTE: This will use vector search since PostgreSQL is stubbed
        results = await multi_index_search(query, top_k=3)

        # Verify results structure
        assert isinstance(results, list)
        # All results should be from vector source (PostgreSQL is stubbed)
        for result in results:
            assert isinstance(result, SearchResult)
            assert result.source == "vector"  # No SQL results from stub

    @pytest.mark.asyncio
    async def test_sql_only_query_routing(self) -> None:
        """Test that SQL_ONLY queries route to PostgreSQL (with fallback to vector)."""
        query = "Show me the table for operating expenses"

        # Verify classification
        query_type = classify_query(query)
        assert query_type == QueryType.SQL_ONLY

        # Execute search
        # NOTE: Since PostgreSQL is stubbed (Story 2.6 incomplete), this will
        # fall back to vector search per AC6 error handling
        results = await multi_index_search(query, top_k=3)

        # Verify results structure
        assert isinstance(results, list)
        # Should fall back to vector since SQL is stubbed
        for result in results:
            assert isinstance(result, SearchResult)
            assert result.source == "vector"  # Fallback from SQL stub

    @pytest.mark.asyncio
    async def test_hybrid_query_routing(self) -> None:
        """Test that HYBRID queries route to both indexes with fusion."""
        query = "Why did EBITDA increase 15% in Q3?"

        # Verify classification
        query_type = classify_query(query)
        assert query_type == QueryType.HYBRID

        # Execute search
        results = await multi_index_search(query, top_k=5)

        # Verify results structure
        assert isinstance(results, list)
        assert len(results) <= 5  # Should return top_k or fewer

        for result in results:
            assert isinstance(result, SearchResult)
            # Source should be "vector" (SQL stub) or "hybrid" (if both had results)
            assert result.source in ["vector", "sql", "hybrid"]

    @pytest.mark.asyncio
    async def test_empty_query_error(self) -> None:
        """Test that empty queries raise appropriate error."""
        with pytest.raises(MultiIndexSearchError, match="Query cannot be empty"):
            await multi_index_search("", top_k=5)

        with pytest.raises(MultiIndexSearchError, match="Query cannot be empty"):
            await multi_index_search("   ", top_k=5)

    def test_result_fusion_vector_only(self) -> None:
        """Test fusion with only vector results."""
        vector_results = [
            SearchResult(
                text="Result 1",
                score=0.9,
                source="vector",
                metadata={},
                document_id="doc1",
            ),
            SearchResult(
                text="Result 2",
                score=0.8,
                source="vector",
                metadata={},
                document_id="doc2",
            ),
        ]

        fused = merge_results(vector_results, [], alpha=0.6, top_k=5)

        assert len(fused) == 2
        assert fused[0].score == 0.9  # Preserved ordering
        assert all(r.source == "vector" for r in fused)

    def test_result_fusion_sql_only(self) -> None:
        """Test fusion with only SQL results."""
        sql_results = [
            SearchResult(
                text="Table row 1",
                score=0.85,
                source="sql",
                metadata={},
                document_id="table1",
            ),
            SearchResult(
                text="Table row 2",
                score=0.75,
                source="sql",
                metadata={},
                document_id="table2",
            ),
        ]

        fused = merge_results([], sql_results, alpha=0.6, top_k=5)

        assert len(fused) == 2
        assert fused[0].score == 0.85  # Preserved ordering
        assert all(r.source == "sql" for r in fused)

    def test_result_fusion_hybrid(self) -> None:
        """Test fusion with both vector and SQL results."""
        vector_results = [
            SearchResult(
                text="Vector result",
                score=0.9,
                source="vector",
                metadata={},
                document_id="doc1",
                page_number=1,
            ),
        ]

        sql_results = [
            SearchResult(
                text="SQL result",
                score=0.7,
                source="sql",
                metadata={},
                document_id="doc2",
                page_number=2,
            ),
        ]

        # Alpha = 0.6 means 60% vector, 40% SQL
        fused = merge_results(vector_results, sql_results, alpha=0.6, top_k=5)

        assert len(fused) == 2
        # Vector result should be ranked higher (0.9 > weighted SQL score)
        assert fused[0].document_id == "doc1"
        assert fused[1].document_id == "doc2"

    def test_result_fusion_deduplication(self) -> None:
        """Test that duplicate documents are deduplicated and fused.

        Story 2.11 AC1: Tests score normalization before fusion.
        With normalization, scores are normalized to [0,1] before weighted fusion:
        - Vector score 0.8 / max(0.8) = 1.0 (normalized)
        - SQL score 0.6 / max(0.6) = 1.0 (normalized)
        - Fused score: 0.6 * 1.0 + 0.4 * 1.0 = 1.0
        """
        # Same document appears in both indexes with different scores
        vector_results = [
            SearchResult(
                text="Vector version",
                score=0.8,
                source="vector",
                metadata={"chunk_index": 5},
                document_id="doc1",
                page_number=1,
            ),
        ]

        sql_results = [
            SearchResult(
                text="SQL version",
                score=0.6,
                source="sql",
                metadata={"table_row": 10},
                document_id="doc1",
                page_number=1,  # Same doc, same page
            ),
        ]

        fused = merge_results(vector_results, sql_results, alpha=0.6, top_k=5)

        # Should have only 1 result after deduplication
        assert len(fused) == 1

        # Story 2.11 FIX: Fused score with normalization
        # max_vector_score = 0.8, max_sql_score = 0.6
        # normalized_vector = 0.8/0.8 = 1.0
        # normalized_sql = 0.6/0.6 = 1.0
        # fused_score = 0.6 * 1.0 + 0.4 * 1.0 = 1.0
        assert abs(fused[0].score - 1.0) < 0.01

        # Should be marked as "hybrid" source
        assert fused[0].source == "hybrid"

        # Metadata should be merged
        assert "chunk_index" in fused[0].metadata
        assert "table_row" in fused[0].metadata

    def test_result_fusion_top_k_limit(self) -> None:
        """Test that fusion respects top_k limit."""
        vector_results = [
            SearchResult(
                text=f"Result {i}",
                score=0.9 - i * 0.1,
                source="vector",
                metadata={},
                document_id=f"doc{i}",
            )
            for i in range(10)
        ]

        fused = merge_results(vector_results, [], alpha=0.6, top_k=3)

        # Should return only top 3 results
        assert len(fused) == 3
        assert fused[0].score == 0.9
        assert fused[1].score == 0.8
        assert fused[2].score == 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
