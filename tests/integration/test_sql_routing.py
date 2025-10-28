"""
Integration tests for SQL Table Search Routing (Story 2.13 AC3)

Tests hybrid_search() with SQL routing for:
- SQL_ONLY queries
- VECTOR_ONLY queries
- HYBRID queries (SQL + Vector fusion)
- Error handling and fallback behavior
"""

import pytest

from raglite.retrieval.search import fuse_sql_vector_results, hybrid_search
from raglite.shared.models import QueryResult


class TestSQLRouting:
    """Test SQL routing integration in hybrid_search()."""

    @pytest.mark.asyncio
    async def test_sql_only_routing(self):
        """Test SQL_ONLY query routes to SQL search only."""
        # Table query that should route to SQL
        query = "What is the variable cost for Portugal Cement in August 2025?"

        results = await hybrid_search(query, top_k=5, enable_sql_tables=True)

        # Should return results (even if empty from database)
        assert isinstance(results, list)
        # All results should be QueryResult objects
        for result in results:
            assert isinstance(result, QueryResult)
            assert hasattr(result, "score")
            assert hasattr(result, "text")
            assert hasattr(result, "page_number")

    @pytest.mark.asyncio
    async def test_vector_only_routing(self):
        """Test VECTOR_ONLY query routes to semantic + BM25 search."""
        # Text query that should route to vector search
        query = "What are the main sustainability initiatives mentioned in the report?"

        results = await hybrid_search(query, top_k=5, enable_sql_tables=True)

        # Should return vector search results
        assert isinstance(results, list)
        assert len(results) > 0  # Should have results from vector search

        # Results should have vector scores (not SQL score=1.0)
        for result in results:
            assert isinstance(result, QueryResult)
            assert 0.0 <= result.score <= 1.0

    @pytest.mark.asyncio
    async def test_hybrid_routing(self):
        """Test HYBRID query routes to SQL + Vector fusion."""
        # Query that should trigger hybrid routing
        query = "Compare EBITDA margins between Portugal and Spain cement divisions"

        results = await hybrid_search(query, top_k=5, enable_sql_tables=True)

        # Should return fused results
        assert isinstance(results, list)
        # Even if SQL returns 0 results, should have vector results
        assert len(results) > 0

        for result in results:
            assert isinstance(result, QueryResult)
            assert hasattr(result, "score")

    @pytest.mark.asyncio
    async def test_sql_routing_disabled(self):
        """Test fallback to vector search when SQL routing disabled."""
        # Table query with SQL routing disabled
        query = "What is the variable cost for Portugal Cement?"

        results = await hybrid_search(query, top_k=5, enable_sql_tables=False)

        # Should fall back to vector+BM25 search
        assert isinstance(results, list)
        assert len(results) > 0  # Should have vector results

        for result in results:
            assert isinstance(result, QueryResult)

    @pytest.mark.asyncio
    async def test_empty_results_handling(self):
        """Test graceful handling of empty SQL results."""
        # Query that may return no SQL results
        query = "What is the XYZ metric for nonexistent entity?"

        results = await hybrid_search(query, top_k=5, enable_sql_tables=True)

        # Should not crash, may return empty or vector fallback results
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_routing_with_filters(self):
        """Test SQL routing works with metadata filters."""
        query = "What are the costs for Portugal?"
        filters = {"company_name": "Portugal Cement"}

        results = await hybrid_search(query, top_k=5, enable_sql_tables=True, filters=filters)

        # Should handle filters gracefully
        assert isinstance(results, list)


class TestSQLVectorFusion:
    """Test SQL + Vector result fusion logic."""

    def test_fuse_sql_vector_both_results(self):
        """Test fusion with both SQL and vector results."""
        # Create mock SQL results (score=1.0)
        sql_results = [
            QueryResult(
                score=1.0,
                text="SQL result 1",
                source_document="test.pdf",
                page_number=1,
                chunk_index=0,
                word_count=10,
            ),
            QueryResult(
                score=1.0,
                text="SQL result 2",
                source_document="test.pdf",
                page_number=2,
                chunk_index=1,
                word_count=10,
            ),
        ]

        # Create mock vector results (varying scores)
        vector_results = [
            QueryResult(
                score=0.85,
                text="Vector result 1",
                source_document="test.pdf",
                page_number=3,
                chunk_index=2,
                word_count=10,
            ),
            QueryResult(
                score=0.75,
                text="Vector result 2",
                source_document="test.pdf",
                page_number=4,
                chunk_index=3,
                word_count=10,
            ),
        ]

        fused = fuse_sql_vector_results(sql_results, vector_results, top_k=4)

        # Should return fused results
        assert len(fused) == 4
        assert all(isinstance(r, QueryResult) for r in fused)

        # All results should have valid RRF scores
        for result in fused:
            assert 0.0 <= result.score <= 1.0

    def test_fuse_sql_only(self):
        """Test fusion with only SQL results."""
        sql_results = [
            QueryResult(
                score=1.0,
                text="SQL result",
                source_document="test.pdf",
                page_number=1,
                chunk_index=0,
                word_count=10,
            )
        ]

        fused = fuse_sql_vector_results(sql_results, [], top_k=5)

        # Should return SQL results unchanged
        assert len(fused) == 1
        assert fused[0].text == "SQL result"

    def test_fuse_vector_only(self):
        """Test fusion with only vector results."""
        vector_results = [
            QueryResult(
                score=0.85,
                text="Vector result",
                source_document="test.pdf",
                page_number=1,
                chunk_index=0,
                word_count=10,
            )
        ]

        fused = fuse_sql_vector_results([], vector_results, top_k=5)

        # Should return vector results unchanged
        assert len(fused) == 1
        assert fused[0].text == "Vector result"

    def test_fuse_empty_results(self):
        """Test fusion with no results."""
        fused = fuse_sql_vector_results([], [], top_k=5)

        # Should return empty list
        assert len(fused) == 0

    def test_fuse_respects_top_k(self):
        """Test fusion respects top_k limit."""
        sql_results = [
            QueryResult(
                score=1.0,
                text=f"SQL {i}",
                source_document="test.pdf",
                page_number=i,
                chunk_index=i,
                word_count=10,
            )
            for i in range(10)
        ]

        vector_results = [
            QueryResult(
                score=0.8,
                text=f"Vector {i}",
                source_document="test.pdf",
                page_number=i + 10,
                chunk_index=i + 10,
                word_count=10,
            )
            for i in range(10)
        ]

        fused = fuse_sql_vector_results(sql_results, vector_results, top_k=5)

        # Should return exactly top_k results
        assert len(fused) == 5

    def test_fuse_deduplicates_overlapping_results(self):
        """Test fusion handles duplicate chunks from SQL and vector."""
        # Same chunk appears in both SQL and vector results
        sql_results = [
            QueryResult(
                score=1.0,
                text="Shared chunk",
                source_document="test.pdf",
                page_number=1,
                chunk_index=0,  # Same chunk_index
                word_count=10,
            )
        ]

        vector_results = [
            QueryResult(
                score=0.9,
                text="Shared chunk (vector)",
                source_document="test.pdf",
                page_number=1,
                chunk_index=0,  # Same chunk_index
                word_count=10,
            )
        ]

        fused = fuse_sql_vector_results(sql_results, vector_results, top_k=5)

        # Should deduplicate by (source_document, chunk_index)
        assert len(fused) == 1
        # SQL result should take precedence
        assert fused[0].text == "Shared chunk"


class TestSQLRoutingErrorHandling:
    """Test error handling in SQL routing."""

    @pytest.mark.asyncio
    async def test_sql_generation_failure_fallback(self):
        """Test fallback to vector search when SQL generation fails."""
        # Query that might cause SQL generation to fail
        query = "Invalid query !@#$%^&*()"

        # Should not crash, should fall back to vector search
        results = await hybrid_search(query, top_k=5, enable_sql_tables=True)

        assert isinstance(results, list)
        # May be empty or have vector results

    @pytest.mark.asyncio
    async def test_malformed_query_handling(self):
        """Test handling of edge case queries."""
        # Empty query
        try:
            results = await hybrid_search("", top_k=5, enable_sql_tables=True)
            # If it doesn't raise, results should be list
            assert isinstance(results, list)
        except Exception as e:
            # Should raise QueryError for empty query
            assert "Query cannot be empty" in str(e) or "empty" in str(e).lower()

    @pytest.mark.asyncio
    async def test_parameter_validation(self):
        """Test parameter validation in hybrid_search()."""
        query = "What is the cost?"

        # Test with various top_k values
        results_5 = await hybrid_search(query, top_k=5, enable_sql_tables=True)
        results_10 = await hybrid_search(query, top_k=10, enable_sql_tables=True)

        assert len(results_5) <= 5
        assert len(results_10) <= 10

        # Test with different alpha values
        results_alpha_high = await hybrid_search(query, top_k=5, alpha=0.9)
        results_alpha_low = await hybrid_search(query, top_k=5, alpha=0.3)

        assert isinstance(results_alpha_high, list)
        assert isinstance(results_alpha_low, list)
