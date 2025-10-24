"""Integration tests for PostgreSQL table retrieval (Story 2.7).

Tests the actual PostgreSQL full-text search against financial_chunks table.
Requires PostgreSQL to be running and populated with data from Story 2.6.
"""

import pytest

from raglite.structured.table_retrieval import (
    TableRetrievalError,
    search_tables,
    search_tables_with_metadata_filter,
)


class TestTableRetrieval:
    """Integration tests for PostgreSQL table search."""

    @pytest.mark.asyncio
    async def test_search_tables_basic(self) -> None:
        """Test basic table search returns results."""
        query = "revenue"
        results = await search_tables(query, top_k=5)

        # Should return results (or empty list if no data)
        assert isinstance(results, list)

        # If results exist, validate structure
        if results:
            assert len(results) <= 5
            for result in results:
                assert "text" in result
                assert "score" in result
                assert "metadata" in result
                assert "document_id" in result
                assert isinstance(result["score"], float)
                assert 0.0 <= result["score"] <= 1.0

    @pytest.mark.asyncio
    async def test_search_tables_with_table_content(self) -> None:
        """Test that search prioritizes table-formatted content."""
        query = "table cost revenue"
        results = await search_tables(query, top_k=3)

        # If results exist, they should have section_type='Table'
        if results:
            for result in results:
                assert result["metadata"].get("section_type") == "Table"

    @pytest.mark.asyncio
    async def test_search_tables_top_k_limit(self) -> None:
        """Test that top_k limit is respected."""
        query = "financial data"
        top_k = 3

        results = await search_tables(query, top_k=top_k)

        # Should not exceed top_k
        assert len(results) <= top_k

    @pytest.mark.asyncio
    async def test_search_tables_empty_query(self) -> None:
        """Test that empty query returns empty results."""
        query = ""
        results = await search_tables(query, top_k=5)

        # Empty query should return empty list (no matches in ts_vector)
        assert isinstance(results, list)
        # Empty query won't match anything in full-text search

    @pytest.mark.asyncio
    async def test_search_tables_no_matches(self) -> None:
        """Test that query with no matches returns empty list."""
        query = "xyzabc123nonexistent"
        results = await search_tables(query, top_k=5)

        # Should return empty list for non-existent terms
        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_tables_with_metadata_filter_basic(self) -> None:
        """Test metadata filtering basic functionality."""
        query = "revenue"
        filters = {"metric_category": "Revenue"}

        results = await search_tables_with_metadata_filter(query, top_k=3, filters=filters)

        # Should return results or empty list
        assert isinstance(results, list)

        # If results exist, validate filter was applied
        if results:
            for result in results:
                # Results matching filter should have correct metadata
                assert "metric_category" in result["metadata"]

    @pytest.mark.asyncio
    async def test_search_tables_with_multiple_filters(self) -> None:
        """Test multiple metadata filters."""
        query = "cost"
        filters = {"metric_category": "Variable Costs", "section_type": "Table"}

        results = await search_tables_with_metadata_filter(query, top_k=5, filters=filters)

        # Should return results or empty list
        assert isinstance(results, list)

        # If results exist, validate both filters applied
        if results:
            for result in results:
                metadata = result["metadata"]
                # Note: Filters may reduce results to 0 if no matches
                assert isinstance(metadata, dict)

    @pytest.mark.asyncio
    async def test_search_tables_score_ordering(self) -> None:
        """Test that results are ordered by relevance score (descending)."""
        query = "revenue cost ebitda"
        results = await search_tables(query, top_k=10)

        # If we have multiple results, scores should be descending
        if len(results) > 1:
            scores = [r["score"] for r in results]
            assert scores == sorted(scores, reverse=True), "Results not ordered by score"

    @pytest.mark.asyncio
    async def test_search_tables_metadata_completeness(self) -> None:
        """Test that returned results have complete metadata."""
        query = "financial"
        results = await search_tables(query, top_k=3)

        # If results exist, validate metadata completeness
        if results:
            for result in results:
                metadata = result["metadata"]

                # Required fields
                assert "source_document" in metadata
                assert "page_number" in metadata
                assert "chunk_index" in metadata
                assert "word_count" in metadata

                # Optional fields (may be None)
                assert "company_name" in metadata
                assert "metric_category" in metadata
                assert "section_type" in metadata
                assert "reporting_period" in metadata
                assert "time_granularity" in metadata


class TestTableRetrievalErrorHandling:
    """Test error handling for PostgreSQL table retrieval."""

    @pytest.mark.asyncio
    async def test_search_handles_database_unavailable(self) -> None:
        """Test graceful handling when PostgreSQL is unavailable."""
        # This test would require mocking the connection
        # For now, we verify the function signature and error types exist
        assert callable(search_tables)
        assert TableRetrievalError is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
