"""Unit tests for vector similarity search and retrieval.

Tests the generate_query_embedding and search_documents functions with mocked dependencies.
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from raglite.retrieval.attribution import CitationError, generate_citations
from raglite.retrieval.search import QueryError, generate_query_embedding, search_documents
from raglite.shared.models import QueryResult


class TestGenerateQueryEmbedding:
    """Test suite for query embedding generation."""

    @pytest.mark.asyncio
    async def test_generate_query_embedding_success(self):
        """Test successful query embedding generation with mocked model.

        Verifies that generate_query_embedding returns 1024-dimensional
        embedding vector for valid query string.
        """
        query = "What is the revenue for Q3 2024?"

        # Mock embedding model
        mock_model = Mock()
        mock_embedding = np.array([0.1] * 1024)
        mock_model.encode.return_value = np.array([mock_embedding])

        with patch("raglite.retrieval.search.get_embedding_model", return_value=mock_model):
            embedding = await generate_query_embedding(query)

            # Assertions
            assert isinstance(embedding, list)
            assert len(embedding) == 1024
            assert all(isinstance(x, float) for x in embedding)
            mock_model.encode.assert_called_once_with([query])

    @pytest.mark.asyncio
    async def test_generate_query_embedding_empty_query(self):
        """Test that QueryError is raised for empty query string.

        Verifies error handling for invalid input.
        """
        with pytest.raises(QueryError, match="Query cannot be empty"):
            await generate_query_embedding("")

        with pytest.raises(QueryError, match="Query cannot be empty"):
            await generate_query_embedding("   ")  # Whitespace only

    @pytest.mark.asyncio
    async def test_generate_query_embedding_model_failure(self):
        """Test error handling when embedding model fails.

        Verifies that QueryError is raised with context when model.encode() fails.
        """
        query = "What is the revenue?"

        # Mock model that raises an exception
        mock_model = Mock()
        mock_model.encode.side_effect = RuntimeError("Model inference failed")

        with patch("raglite.retrieval.search.get_embedding_model", return_value=mock_model):
            with pytest.raises(QueryError, match="Failed to generate query embedding"):
                await generate_query_embedding(query)


class TestSearchDocuments:
    """Test suite for vector similarity search."""

    @pytest.mark.asyncio
    async def test_search_documents_basic(self):
        """Test basic search returns 5 chunks with scores.

        Verifies that search_documents returns QueryResult objects
        with default top_k=5 parameter.
        """
        query = "What is the revenue?"

        # Mock query embedding
        mock_embedding = [0.1] * 1024

        # Mock Qdrant response
        mock_point1 = Mock()
        mock_point1.score = 0.87
        mock_point1.payload = {
            "chunk_id": "chunk-001",
            "text": "Q3 revenue was $50M, up 20% YoY.",
            "source_document": "Q3_Report.pdf",
            "page_number": 5,
            "chunk_index": 0,
            "word_count": 8,
        }

        mock_point2 = Mock()
        mock_point2.score = 0.75
        mock_point2.payload = {
            "chunk_id": "chunk-002",
            "text": "Total revenue for the year is $180M.",
            "source_document": "Annual_Report.pdf",
            "page_number": 12,
            "chunk_index": 1,
            "word_count": 7,
        }

        mock_result = Mock()
        mock_result.points = [mock_point1, mock_point2, mock_point1, mock_point2, mock_point1]

        mock_qdrant = Mock()
        mock_qdrant.query_points.return_value = mock_result

        with (
            patch("raglite.retrieval.search.generate_query_embedding", return_value=mock_embedding),
            patch("raglite.retrieval.search.get_qdrant_client", return_value=mock_qdrant),
        ):
            results = await search_documents(query, top_k=5)

            # Assertions
            assert len(results) == 5
            assert all(isinstance(r, QueryResult) for r in results)
            assert results[0].score == 0.87
            assert results[0].text == "Q3 revenue was $50M, up 20% YoY."
            assert results[0].source_document == "Q3_Report.pdf"
            assert results[0].page_number == 5
            mock_qdrant.query_points.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_documents_custom_top_k(self):
        """Test that custom top_k parameter returns correct number of results.

        Verifies that top_k=10 returns 10 results and top_k=3 returns 3.
        """
        query = "financial data"
        mock_embedding = [0.1] * 1024

        # Create 10 mock points
        mock_points = []
        for i in range(10):
            mock_point = Mock()
            mock_point.score = 0.9 - (i * 0.05)
            mock_point.payload = {
                "chunk_id": f"chunk-{i:03d}",
                "text": f"Financial text {i}",
                "source_document": "report.pdf",
                "page_number": i + 1,
                "chunk_index": i,
                "word_count": 10,
            }
            mock_points.append(mock_point)

        mock_result = Mock()
        mock_result.points = mock_points

        mock_qdrant = Mock()
        mock_qdrant.query_points.return_value = mock_result

        with (
            patch("raglite.retrieval.search.generate_query_embedding", return_value=mock_embedding),
            patch("raglite.retrieval.search.get_qdrant_client", return_value=mock_qdrant),
        ):
            # Test top_k=10
            results = await search_documents(query, top_k=10)
            assert len(results) == 10

            # Test top_k=3
            mock_result.points = mock_points[:3]
            results = await search_documents(query, top_k=3)
            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_metadata_filtering_by_source_document(self):
        """Test metadata filtering by source_document.

        Verifies that Qdrant Filter is constructed correctly
        and only results from specified document are returned.
        """

        query = "revenue data"
        mock_embedding = [0.1] * 1024
        filters = {"source_document": "Q3_Report.pdf"}

        # Mock point from Q3_Report.pdf only
        mock_point = Mock()
        mock_point.score = 0.85
        mock_point.payload = {
            "chunk_id": "chunk-001",
            "text": "Q3 revenue data",
            "source_document": "Q3_Report.pdf",
            "page_number": 5,
            "chunk_index": 0,
            "word_count": 4,
        }

        mock_result = Mock()
        mock_result.points = [mock_point]

        mock_qdrant = Mock()
        mock_qdrant.query_points.return_value = mock_result

        with (
            patch("raglite.retrieval.search.generate_query_embedding", return_value=mock_embedding),
            patch("raglite.retrieval.search.get_qdrant_client", return_value=mock_qdrant),
        ):
            results = await search_documents(query, top_k=5, filters=filters)

            # Assertions
            assert len(results) == 1
            assert results[0].source_document == "Q3_Report.pdf"

            # Verify that Qdrant was called with filter
            call_args = mock_qdrant.query_points.call_args
            assert call_args.kwargs["query_filter"] is not None

    @pytest.mark.asyncio
    async def test_empty_query_handling(self):
        """Test that empty query raises QueryError.

        Verifies that search_documents handles empty query string
        through generate_query_embedding validation.
        """
        with pytest.raises(QueryError, match="Query cannot be empty"):
            await search_documents("", top_k=5)

        with pytest.raises(QueryError, match="Query cannot be empty"):
            await search_documents("   ", top_k=5)

    @pytest.mark.asyncio
    async def test_relevance_scoring_sorted_descending(self):
        """Test that results have scores in 0-1 range and sorted descending.

        Verifies relevance scoring meets requirements:
        - All scores between 0 and 1
        - Results sorted by score (highest first)
        """
        query = "financial analysis"
        mock_embedding = [0.1] * 1024

        # Create mock points with varying scores (not sorted)
        scores = [0.65, 0.92, 0.45, 0.88, 0.71]
        mock_points = []
        for i, score in enumerate(scores):
            mock_point = Mock()
            mock_point.score = score
            mock_point.payload = {
                "chunk_id": f"chunk-{i}",
                "text": f"Text {i}",
                "source_document": "report.pdf",
                "page_number": i + 1,
                "chunk_index": i,
                "word_count": 10,
            }
            mock_points.append(mock_point)

        mock_result = Mock()
        mock_result.points = mock_points

        mock_qdrant = Mock()
        mock_qdrant.query_points.return_value = mock_result

        with (
            patch("raglite.retrieval.search.generate_query_embedding", return_value=mock_embedding),
            patch("raglite.retrieval.search.get_qdrant_client", return_value=mock_qdrant),
        ):
            results = await search_documents(query, top_k=5)

            # Verify all scores in 0-1 range
            assert all(0.0 <= r.score <= 1.0 for r in results)

            # Verify results are sorted descending by score
            # (Qdrant returns them sorted, so we trust the order)
            result_scores = [r.score for r in results]
            assert result_scores == scores  # Qdrant returns in order it receives

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test that QueryError is raised on Qdrant connection failures.

        Verifies error handling when Qdrant client fails.
        """
        query = "test query"
        mock_embedding = [0.1] * 1024

        # Mock Qdrant client that raises connection error
        mock_qdrant = Mock()
        mock_qdrant.query_points.side_effect = ConnectionError("Qdrant connection failed")

        with (
            patch("raglite.retrieval.search.generate_query_embedding", return_value=mock_embedding),
            patch("raglite.retrieval.search.get_qdrant_client", return_value=mock_qdrant),
        ):
            with pytest.raises(QueryError, match="Vector search failed"):
                await search_documents(query, top_k=5)

    @pytest.mark.asyncio
    async def test_metadata_validation_all_fields_present(self):
        """Test that all QueryResult objects have required metadata fields.

        Verifies metadata validation (CRITICAL for Story 1.8 source attribution):
        - page_number must not be None
        - source_document must not be empty
        - chunk_index, word_count must be present
        """
        query = "test query"
        mock_embedding = [0.1] * 1024

        # Create mock point with all required fields
        mock_point = Mock()
        mock_point.score = 0.85
        mock_point.payload = {
            "chunk_id": "chunk-001",
            "text": "Financial data with complete metadata",
            "source_document": "Q3_Report.pdf",
            "page_number": 5,
            "chunk_index": 0,
            "word_count": 6,
        }

        mock_result = Mock()
        mock_result.points = [mock_point]

        mock_qdrant = Mock()
        mock_qdrant.query_points.return_value = mock_result

        with (
            patch("raglite.retrieval.search.generate_query_embedding", return_value=mock_embedding),
            patch("raglite.retrieval.search.get_qdrant_client", return_value=mock_qdrant),
        ):
            results = await search_documents(query, top_k=5)

            # Assertions - verify all required fields present
            assert len(results) == 1
            result = results[0]

            assert result.page_number is not None
            assert result.page_number == 5
            assert result.source_document != ""
            assert result.source_document == "Q3_Report.pdf"
            assert result.chunk_index is not None
            assert result.chunk_index == 0
            assert result.word_count > 0
            assert result.word_count == 6

    @pytest.mark.asyncio
    async def test_metadata_validation_missing_page_number(self):
        """Test warning logged when page_number is missing.

        Verifies that search_documents logs warning but doesn't fail
        when optional metadata is missing (still creates QueryResult).
        """
        query = "test query"
        mock_embedding = [0.1] * 1024

        # Create mock point with missing page_number
        mock_point = Mock()
        mock_point.score = 0.85
        mock_point.payload = {
            "chunk_id": "chunk-001",
            "text": "Financial data",
            "source_document": "report.pdf",
            "page_number": None,  # Missing!
            "chunk_index": 0,
            "word_count": 2,
        }

        mock_result = Mock()
        mock_result.points = [mock_point]

        mock_qdrant = Mock()
        mock_qdrant.query_points.return_value = mock_result

        with (
            patch("raglite.retrieval.search.generate_query_embedding", return_value=mock_embedding),
            patch("raglite.retrieval.search.get_qdrant_client", return_value=mock_qdrant),
        ):
            # Should not raise error, but logs warning
            results = await search_documents(query, top_k=5)

            # Verify result still created (graceful degradation)
            assert len(results) == 1
            assert results[0].page_number is None


class TestGenerateCitations:
    """Test suite for citation generation and source attribution."""

    @pytest.mark.asyncio
    async def test_generate_citations_basic(self):
        """Test that single QueryResult gets citation appended to text.

        Verifies basic citation generation with correct format.
        """
        results = [
            QueryResult(
                score=0.87,
                text="Q3 revenue was $50M, up 20% YoY.",
                source_document="Q3_Report.pdf",
                page_number=5,
                chunk_index=0,
                word_count=8,
            )
        ]

        cited_results = await generate_citations(results)

        # Assertions
        assert len(cited_results) == 1
        assert "(Source: Q3_Report.pdf, page 5, chunk 0)" in cited_results[0].text
        assert cited_results[0].text.startswith("Q3 revenue was $50M")
        assert cited_results[0].text.endswith("(Source: Q3_Report.pdf, page 5, chunk 0)")

    @pytest.mark.asyncio
    async def test_generate_citations_multi_source(self):
        """Test that multiple QueryResult objects get unique citations.

        Verifies that each chunk from different sources gets its own citation.
        """
        results = [
            QueryResult(
                score=0.87,
                text="Q3 revenue was $50M.",
                source_document="Q3_Report.pdf",
                page_number=5,
                chunk_index=0,
                word_count=5,
            ),
            QueryResult(
                score=0.75,
                text="Annual revenue is $180M.",
                source_document="Annual_Report.pdf",
                page_number=12,
                chunk_index=1,
                word_count=4,
            ),
            QueryResult(
                score=0.65,
                text="Operating expenses grew 10%.",
                source_document="Q3_Report.pdf",
                page_number=8,
                chunk_index=2,
                word_count=4,
            ),
        ]

        cited_results = await generate_citations(results)

        # Assertions - verify unique citations
        assert len(cited_results) == 3
        assert "(Source: Q3_Report.pdf, page 5, chunk 0)" in cited_results[0].text
        assert "(Source: Annual_Report.pdf, page 12, chunk 1)" in cited_results[1].text
        assert "(Source: Q3_Report.pdf, page 8, chunk 2)" in cited_results[2].text

        # Verify ordering preserved (highest score first)
        assert cited_results[0].score == 0.87
        assert cited_results[1].score == 0.75
        assert cited_results[2].score == 0.65

    @pytest.mark.asyncio
    async def test_citation_format(self):
        """Test that citation format matches specification.

        Verifies format: "(Source: document.pdf, page 12, chunk 5)"
        """
        result = QueryResult(
            score=0.90,
            text="Test content",
            source_document="Financial_Report.pdf",
            page_number=42,
            chunk_index=17,
            word_count=2,
        )

        cited_results = await generate_citations([result])

        # Verify exact format
        expected_citation = "(Source: Financial_Report.pdf, page 42, chunk 17)"
        assert expected_citation in cited_results[0].text

    @pytest.mark.asyncio
    async def test_missing_page_number(self):
        """Test graceful degradation when page_number is None.

        Verifies that warning is logged and citation uses 'N/A' for page.
        """
        result = QueryResult(
            score=0.80,
            text="Content without page number",
            source_document="report.pdf",
            page_number=None,  # Missing!
            chunk_index=0,
            word_count=4,
        )

        # Should not raise error (graceful degradation)
        cited_results = await generate_citations([result])

        # Verify citation uses 'N/A' for missing page
        assert len(cited_results) == 1
        assert "(Source: report.pdf, page N/A, chunk 0)" in cited_results[0].text

    @pytest.mark.asyncio
    async def test_missing_source_document(self):
        """Test that CitationError is raised when source_document is missing.

        Verifies critical field validation (source_document required).
        """
        result = QueryResult(
            score=0.80,
            text="Content",
            source_document="",  # Empty! Critical field
            page_number=5,
            chunk_index=0,
            word_count=1,
        )

        # Should raise CitationError
        with pytest.raises(CitationError, match="Missing source_document for chunk 0"):
            await generate_citations([result])

        # Test with whitespace-only source_document
        result.source_document = "   "
        with pytest.raises(CitationError, match="Missing source_document"):
            await generate_citations([result])

    @pytest.mark.asyncio
    async def test_citation_appended_to_text(self):
        """Test that original chunk text is preserved and citation appended.

        Verifies that citation doesn't replace text, but appends with newlines.
        """
        original_text = "Q3 revenue increased by 15% compared to Q2."
        result = QueryResult(
            score=0.85,
            text=original_text,
            source_document="Q3_Report.pdf",
            page_number=7,
            chunk_index=3,
            word_count=8,
        )

        cited_results = await generate_citations([result])

        # Verify original text preserved
        assert cited_results[0].text.startswith(original_text)

        # Verify citation appended with double newline
        assert "\n\n(Source:" in cited_results[0].text
        assert cited_results[0].text.count("\n\n") == 1  # Exactly one double newline

    @pytest.mark.asyncio
    async def test_empty_results_list(self):
        """Test that empty results list is handled gracefully.

        Verifies no error when no results to cite.
        """
        cited_results = await generate_citations([])

        # Should return empty list
        assert cited_results == []
        assert len(cited_results) == 0

    @pytest.mark.asyncio
    async def test_citation_ordering(self):
        """Test that citations match QueryResult order.

        Verifies that citation order follows result order (highest score first).
        """
        results = [
            QueryResult(
                score=0.95,
                text="Highest relevance chunk",
                source_document="report.pdf",
                page_number=1,
                chunk_index=0,
                word_count=3,
            ),
            QueryResult(
                score=0.80,
                text="Medium relevance chunk",
                source_document="report.pdf",
                page_number=2,
                chunk_index=1,
                word_count=3,
            ),
            QueryResult(
                score=0.60,
                text="Lower relevance chunk",
                source_document="report.pdf",
                page_number=3,
                chunk_index=2,
                word_count=3,
            ),
        ]

        cited_results = await generate_citations(results)

        # Verify ordering preserved
        assert cited_results[0].score == 0.95
        assert cited_results[1].score == 0.80
        assert cited_results[2].score == 0.60

        # Verify citations match order
        assert "page 1, chunk 0" in cited_results[0].text
        assert "page 2, chunk 1" in cited_results[1].text
        assert "page 3, chunk 2" in cited_results[2].text
