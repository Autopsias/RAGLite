"""Unit tests for embedding generation functionality (Story 1.5).

Tests the generate_embeddings function with mocked SentenceTransformer model.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import numpy as np
import pytest

from raglite.ingestion.pipeline import (
    EmbeddingGenerationError,
    generate_embeddings,
)
from raglite.shared.clients import get_embedding_model
from raglite.shared.models import Chunk, DocumentMetadata


class TestGenerateEmbeddings:
    """Test suite for embedding generation functionality (Story 1.5)."""

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_generate_embeddings_basic(self):
        """Test basic embedding generation with sample chunks.

        Verifies generate_embeddings populates embedding field for all chunks
        with 1024-dimensional vectors. AC1, AC2.
        """
        # Create 10 sample chunks
        metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=5,
            source_path="/tmp/test.pdf",
        )

        chunks = [
            Chunk(
                chunk_id=f"test.pdf_{i}",
                content=f"Sample financial content for chunk {i}",
                metadata=metadata,
                page_number=i % 5 + 1,
                embedding=[],
            )
            for i in range(10)
        ]

        # Mock SentenceTransformer model - Story 3.0.1: Patch where USED (embedding_generation)
        with patch("raglite.ingestion.embedding_generation.get_embedding_model") as mock_get_model:
            mock_model = Mock()
            # Mock encode to return 1024-dimensional embeddings
            mock_embeddings = np.random.rand(10, 1024).astype(np.float32)
            mock_model.encode.return_value = mock_embeddings
            mock_get_model.return_value = mock_model

            # Generate embeddings
            result_chunks = await generate_embeddings(chunks)

            # Assertions
            assert len(result_chunks) == 10
            assert result_chunks is chunks  # Should modify in-place and return same list

            # Verify all chunks have embeddings populated
            for idx, chunk in enumerate(result_chunks):
                assert chunk.embedding is not None, f"Chunk {idx} has None embedding"
                assert len(chunk.embedding) == 1024, (
                    f"Chunk {idx} embedding has wrong dimensions: {len(chunk.embedding)}"
                )
                assert isinstance(chunk.embedding, list), (
                    "Embedding should be list for JSON serialization"
                )
                assert all(isinstance(x, float) for x in chunk.embedding), (
                    "All embedding values should be floats"
                )

            # Verify model.encode was called with batch_size=32
            mock_model.encode.assert_called_once()
            call_kwargs = mock_model.encode.call_args[1]
            assert call_kwargs["batch_size"] == 32
            assert call_kwargs["show_progress_bar"] is False

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_embedding_dimensions(self):
        """Test that embeddings have exactly 1024 dimensions.

        Verifies Fin-E5 model generates correct vector dimensions. AC2.
        """
        metadata = DocumentMetadata(
            filename="dimensions_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=1,
            source_path="/tmp/dimensions_test.pdf",
        )

        chunk = Chunk(
            chunk_id="dimensions_test.pdf_0",
            content="Test content for dimension validation",
            metadata=metadata,
            page_number=1,
            embedding=[],
        )

        # Mock model to return 1024-dimensional embedding - Patch where USED
        with patch("raglite.ingestion.embedding_generation.get_embedding_model") as mock_get_model:
            mock_model = Mock()
            mock_embedding = np.random.rand(1, 1024).astype(np.float32)
            mock_model.encode.return_value = mock_embedding
            mock_get_model.return_value = mock_model

            result_chunks = await generate_embeddings([chunk])

            # CRITICAL: Verify exact dimension count
            assert len(result_chunks[0].embedding) == 1024, (
                f"Expected 1024 dimensions, got {len(result_chunks[0].embedding)}"
            )

            # Verify all elements are floats
            for idx, value in enumerate(result_chunks[0].embedding):
                assert isinstance(value, float), (
                    f"Embedding value at index {idx} is not float: {type(value)}"
                )

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test batch processing with 100+ chunks.

        Verifies chunks are processed in batches of 32 for memory efficiency. AC3.
        """
        # Create 100 chunks to test batching
        metadata = DocumentMetadata(
            filename="batch_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=50,
            source_path="/tmp/batch_test.pdf",
        )

        chunks = [
            Chunk(
                chunk_id=f"batch_test.pdf_{i}",
                content=f"Batch content {i}",
                metadata=metadata,
                page_number=i % 50 + 1,
                embedding=[],
            )
            for i in range(100)
        ]

        # Mock model and track batch calls - Patch where USED
        with patch("raglite.ingestion.embedding_generation.get_embedding_model") as mock_get_model:
            mock_model = Mock()

            # Track encode calls
            encode_call_count = 0
            batch_sizes = []

            def mock_encode(texts, batch_size=None, show_progress_bar=True):
                nonlocal encode_call_count
                encode_call_count += 1
                batch_sizes.append(len(texts))
                # Return embeddings matching input size
                return np.random.rand(len(texts), 1024).astype(np.float32)

            mock_model.encode.side_effect = mock_encode
            mock_get_model.return_value = mock_model

            # Generate embeddings
            result_chunks = await generate_embeddings(chunks)

            # Assertions
            assert len(result_chunks) == 100

            # Verify batching: 100 chunks / 32 batch_size = 4 batches (32, 32, 32, 4)
            assert encode_call_count == 4, f"Expected 4 batch calls, got {encode_call_count}"
            assert batch_sizes == [
                32,
                32,
                32,
                4,
            ], f"Expected batch sizes [32, 32, 32, 4], got {batch_sizes}"

            # Verify all chunks have embeddings
            for chunk in result_chunks:
                assert len(chunk.embedding) == 1024

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_empty_chunk_handling(self):
        """Test handling of empty chunk list.

        Verifies graceful handling when no chunks provided. AC6.
        """
        # Test with empty list
        result = await generate_embeddings([])

        # Should return empty list without error
        assert result == []

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_embeddings_not_none(self):
        """CRITICAL: Verify all chunks have embeddings != None.

        This test validates AC8 - all chunks must have valid embeddings
        before Qdrant storage. Critical for retrieval accuracy (NFR6).
        """
        # Create 50 chunks
        metadata = DocumentMetadata(
            filename="validation_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=25,
            source_path="/tmp/validation_test.pdf",
        )

        chunks = [
            Chunk(
                chunk_id=f"validation_test.pdf_{i}",
                content=f"Content for validation chunk {i}",
                metadata=metadata,
                page_number=i % 25 + 1,
                embedding=[],
            )
            for i in range(50)
        ]

        # Mock model
        with patch("raglite.ingestion.embedding_generation.get_embedding_model") as mock_get_model:
            mock_model = Mock()

            def mock_encode(texts, batch_size=None, show_progress_bar=True):
                return np.random.rand(len(texts), 1024).astype(np.float32)

            mock_model.encode.side_effect = mock_encode
            mock_get_model.return_value = mock_model

            # Generate embeddings
            result_chunks = await generate_embeddings(chunks)

            # CRITICAL VALIDATION: All chunks must have embeddings != None and not empty
            for idx, chunk in enumerate(result_chunks):
                assert chunk.embedding is not None, (
                    f"Chunk {idx} has None embedding (CRITICAL FAILURE)"
                )
                assert chunk.embedding != [], (
                    f"Chunk {idx} has empty embedding list (CRITICAL FAILURE)"
                )
                assert len(chunk.embedding) == 1024, (
                    f"Chunk {idx} has invalid embedding dimension: {len(chunk.embedding)}"
                )

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_embedding_generation_error_handling(self):
        """Test error handling when embedding generation fails.

        Verifies EmbeddingGenerationError is raised with clear message.
        """
        metadata = DocumentMetadata(
            filename="error_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=1,
            source_path="/tmp/error_test.pdf",
        )

        chunks = [
            Chunk(
                chunk_id="error_test.pdf_0",
                content="Test content",
                metadata=metadata,
                page_number=1,
                embedding=[],
            )
        ]

        # Mock model to raise exception
        with patch("raglite.ingestion.embedding_generation.get_embedding_model") as mock_get_model:
            mock_model = Mock()
            mock_model.encode.side_effect = Exception("GPU out of memory")
            mock_get_model.return_value = mock_model

            # Should raise EmbeddingGenerationError
            with pytest.raises(EmbeddingGenerationError, match="Failed to generate embeddings"):
                await generate_embeddings(chunks)

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_get_embedding_model_singleton(self):
        """Test that get_embedding_model returns cached model (singleton pattern).

        Verifies model is loaded once and reused. AC1.
        """
        # Clear the global embedding model cache before testing
        import raglite.shared.clients as clients_module

        # CRITICAL FIX (2025-12-16): Store and restore ALL global state to prevent
        # mock pollution affecting subsequent tests (especially integration tests).
        # The embedding model singleton uses three globals: _embedding_model,
        # SENTENCE_TRANSFORMERS_AVAILABLE, and _SentenceTransformer.
        original_model = clients_module._embedding_model
        clients_module._embedding_model = None
        original_sentence_transformers_available = clients_module.SENTENCE_TRANSFORMERS_AVAILABLE
        clients_module.SENTENCE_TRANSFORMERS_AVAILABLE = None
        original_sentence_transformer_class = clients_module._SentenceTransformer
        clients_module._SentenceTransformer = None

        try:
            with patch(
                "raglite.shared.clients._get_sentence_transformer_class"
            ) as mock_get_st_class:
                # Mock SentenceTransformer class
                MockST = Mock()
                mock_model = Mock()
                mock_model.get_sentence_embedding_dimension.return_value = 1024
                MockST.return_value = mock_model
                mock_get_st_class.return_value = MockST

                # First call should load model
                model1 = get_embedding_model()
                assert model1 is mock_model

                # Second call should return cached model (no new instantiation)
                model2 = get_embedding_model()
                assert model2 is model1

                # Verify that _get_sentence_transformer_class was called twice (once per get_embedding_model call)
                assert mock_get_st_class.call_count == 2

                # But SentenceTransformer should only be instantiated once (singleton pattern)
                MockST.assert_called_once_with("intfloat/e5-large-v2")
        finally:
            # Restore ALL original state to prevent mock pollution
            clients_module._embedding_model = original_model
            clients_module.SENTENCE_TRANSFORMERS_AVAILABLE = (
                original_sentence_transformers_available
            )
            clients_module._SentenceTransformer = original_sentence_transformer_class

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_generate_embeddings_logging(self, caplog):
        """Test that structured logging includes correct context.

        Verifies logging with extra={} fields for monitoring. AC1.
        """
        import logging

        caplog.set_level(logging.INFO)

        metadata = DocumentMetadata(
            filename="logging_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=1,
            source_path="/tmp/logging_test.pdf",
        )

        chunks = [
            Chunk(
                chunk_id=f"logging_test.pdf_{i}",
                content=f"Logging test content {i}",
                metadata=metadata,
                page_number=1,
                embedding=[],
            )
            for i in range(5)
        ]

        # Mock model
        with patch("raglite.ingestion.embedding_generation.get_embedding_model") as mock_get_model:
            mock_model = Mock()
            mock_model.encode.return_value = np.random.rand(5, 1024).astype(np.float32)
            mock_get_model.return_value = mock_model

            await generate_embeddings(chunks)

            # Verify log messages
            assert "Generating embeddings" in caplog.text
            assert "Embedding generation complete" in caplog.text

            # Verify structured logging context - Story 3.0.1: Logs now come from embedding_generation
            log_records = [
                r for r in caplog.records if r.name == "raglite.ingestion.embedding_generation"
            ]
            assert len(log_records) >= 2

            # Check log has chunk_count in extra
            start_log = next((r for r in log_records if "Generating" in r.message), None)
            assert start_log is not None
            assert hasattr(start_log, "chunk_count")
            assert start_log.chunk_count == 5
