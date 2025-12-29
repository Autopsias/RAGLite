"""Unit tests for vector similarity search and retrieval.

Tests the generate_query_embedding and search_documents functions with mocked dependencies.
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from raglite.retrieval.search import QueryError, generate_query_embedding

pytestmark = [pytest.mark.unit]


class TestGenerateQueryEmbedding:
    """Test suite for query embedding generation."""

    @pytest.mark.priority("P1")
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

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_generate_query_embedding_empty_query(self):
        """Test that QueryError is raised for empty query string.

        Verifies error handling for invalid input.
        """
        with pytest.raises(QueryError, match="Query cannot be empty"):
            await generate_query_embedding("")

        with pytest.raises(QueryError, match="Query cannot be empty"):
            await generate_query_embedding("   ")  # Whitespace only

    @pytest.mark.priority("P1")
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
