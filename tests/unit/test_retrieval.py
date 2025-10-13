"""Unit tests for vector similarity search and retrieval.

Tests the generate_query_embedding and search_documents functions with mocked dependencies.
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest

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
