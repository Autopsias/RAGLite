"""Unit tests for Qdrant vector storage (Story 1.6).

Tests the create_collection and store_vectors_in_qdrant functions with mocked Qdrant client.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from raglite.ingestion.pipeline import (
    VectorStorageError,
    create_collection,
    store_vectors_in_qdrant,
)
from raglite.shared.clients import get_qdrant_client
from raglite.shared.models import Chunk, DocumentMetadata

# Group tests that modify Qdrant singleton state to run on same worker
pytestmark = pytest.mark.xdist_group(name="qdrant_singleton")


class TestQdrantStorage:
    """Test suite for Qdrant vector storage (Story 1.6)."""

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_create_collection_success(self):
        """Test successful collection creation with mocked Qdrant client.

        Verifies create_collection creates collection with correct parameters. AC2.
        """
        with patch("raglite.ingestion.storage.vector_store.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_collections = Mock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections
            mock_get_client.return_value = mock_client

            # Create collection
            create_collection("financial_docs", vector_size=1024)

            # Verify collection was created with correct parameters
            mock_client.create_collection.assert_called_once()
            call_args = mock_client.create_collection.call_args
            assert call_args.kwargs["collection_name"] == "financial_docs"

            # Story 2.1: vectors_config is now a dict with named vectors for hybrid search
            vectors_config = call_args.kwargs["vectors_config"]
            assert isinstance(vectors_config, dict)
            assert "text-dense" in vectors_config
            assert vectors_config["text-dense"].size == 1024
            assert vectors_config["text-dense"].distance.name == "COSINE"

            # Verify sparse vectors config for BM25 (Story 2.1)
            sparse_config = call_args.kwargs["sparse_vectors_config"]
            assert isinstance(sparse_config, dict)
            assert "text-sparse" in sparse_config

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_create_collection_idempotent(self):
        """Test collection creation is idempotent (doesn't error if exists).

        Verifies calling create_collection twice doesn't raise error. AC2.
        """
        with patch("raglite.ingestion.storage.vector_store.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.name = "financial_docs"
            mock_collections = Mock()
            mock_collections.collections = [mock_collection]
            mock_client.get_collections.return_value = mock_collections
            mock_get_client.return_value = mock_client

            # Create collection (should skip because it exists)
            create_collection("financial_docs", vector_size=1024)

            # Verify create_collection was NOT called (already exists)
            mock_client.create_collection.assert_not_called()

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_store_vectors_basic(self):
        """Test storing 10 chunks with embeddings successfully.

        Verifies store_vectors_in_qdrant stores all chunks and metadata. AC3, AC9.
        """
        metadata = DocumentMetadata(
            filename="test_doc.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=2,
            source_path="/tmp/test_doc.pdf",
        )

        chunks = [
            Chunk(
                chunk_id=f"test_doc.pdf_{i}",
                content=f"Test chunk content {i} with financial data",
                metadata=metadata,
                page_number=1,
                embedding=[float(x) for x in range(1024)],
            )
            for i in range(10)
        ]

        with patch("raglite.ingestion.storage.vector_store.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_collections = Mock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections

            # Mock get_collection to return points_count
            mock_collection_info = Mock()
            mock_collection_info.points_count = 10
            mock_client.get_collection.return_value = mock_collection_info

            mock_get_client.return_value = mock_client

            # Store vectors
            points_stored = await store_vectors_in_qdrant(chunks)

            # Assertions
            assert points_stored == 10
            mock_client.upsert.assert_called_once()

            # Verify metadata is preserved in payload
            call_args = mock_client.upsert.call_args
            points = call_args.kwargs["points"]
            assert len(points) == 10

            # Check first point has all required metadata
            first_point = points[0]
            assert first_point.payload["chunk_id"] == "test_doc.pdf_0"
            assert first_point.payload["text"] == "Test chunk content 0 with financial data"
            assert (
                first_point.payload["word_count"] == 7
            )  # "Test chunk content 0 with financial data"
            assert first_point.payload["source_document"] == "test_doc.pdf"
            assert first_point.payload["page_number"] == 1
            assert first_point.payload["chunk_index"] == 0

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_batch_upload_processing(self):
        """Test batch processing for 250 chunks (batches of 100).

        Verifies chunks are uploaded in batches to prevent memory issues. AC10.
        """
        metadata = DocumentMetadata(
            filename="large_doc.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=50,
            source_path="/tmp/large_doc.pdf",
        )

        # Create 250 chunks
        chunks = [
            Chunk(
                chunk_id=f"large_doc.pdf_{i}",
                content=f"Chunk content {i}",
                metadata=metadata,
                page_number=i // 5,
                embedding=[float(x) for x in range(1024)],
            )
            for i in range(250)
        ]

        with patch("raglite.ingestion.storage.vector_store.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_collections = Mock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections

            mock_collection_info = Mock()
            mock_collection_info.points_count = 250
            mock_client.get_collection.return_value = mock_collection_info

            mock_get_client.return_value = mock_client

            # Store vectors with batch_size=100
            points_stored = await store_vectors_in_qdrant(chunks, batch_size=100)

            # Verify 3 batches were uploaded (100, 100, 50)
            assert mock_client.upsert.call_count == 3
            assert points_stored == 250

            # Verify batch sizes
            calls = mock_client.upsert.call_args_list
            assert len(calls[0].kwargs["points"]) == 100  # First batch
            assert len(calls[1].kwargs["points"]) == 100  # Second batch
            assert len(calls[2].kwargs["points"]) == 50  # Third batch

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_metadata_preservation(self):
        """Test all metadata fields are preserved in Qdrant payload.

        Verifies page_number, source_document, chunk_index, etc. preserved. AC3.
        """
        metadata = DocumentMetadata(
            filename="metadata_test.pdf",
            doc_type="PDF",
            ingestion_timestamp=datetime.now().isoformat(),
            page_count=3,
            source_path="/tmp/metadata_test.pdf",
        )

        chunks = [
            Chunk(
                chunk_id=f"metadata_test.pdf_{i}",
                content=f"Content for page {i + 1}",
                metadata=metadata,
                page_number=i + 1,
                chunk_index=i,
                embedding=[float(x) for x in range(1024)],
            )
            for i in range(3)
        ]

        with patch("raglite.ingestion.storage.vector_store.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_collections = Mock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections

            mock_collection_info = Mock()
            mock_collection_info.points_count = 3
            mock_client.get_collection.return_value = mock_collection_info

            mock_get_client.return_value = mock_client

            await store_vectors_in_qdrant(chunks)

            # Get uploaded points
            call_args = mock_client.upsert.call_args
            points = call_args.kwargs["points"]

            # Verify all metadata fields for each chunk
            for i, point in enumerate(points):
                payload = point.payload
                assert payload["chunk_id"] == f"metadata_test.pdf_{i}"
                assert payload["text"] == f"Content for page {i + 1}"
                assert payload["source_document"] == "metadata_test.pdf"
                assert payload["page_number"] == i + 1
                assert payload["chunk_index"] == i
                assert "word_count" in payload

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_empty_chunks_handling(self):
        """Test graceful handling of empty chunk list.

        Verifies function returns 0 and doesn't call Qdrant for empty input. AC7.
        """
        with patch("raglite.ingestion.storage.vector_store.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            # Store empty list
            points_stored = await store_vectors_in_qdrant([])

            # Assertions
            assert points_stored == 0
            mock_client.upsert.assert_not_called()

    @pytest.mark.priority("P3")
    @pytest.mark.asyncio
    async def test_storage_error_handling(self):
        """Test VectorStorageError raised on storage failures.

        Verifies proper error handling when Qdrant upsert fails. AC6.
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
                embedding=[float(x) for x in range(1024)],
            )
        ]

        with patch("raglite.ingestion.storage.vector_store.get_qdrant_client") as mock_get_client:
            mock_client = Mock()
            mock_collections = Mock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections

            # Mock upsert to raise exception
            mock_client.upsert.side_effect = Exception("Connection timeout")

            mock_get_client.return_value = mock_client

            # Verify VectorStorageError is raised
            with pytest.raises(VectorStorageError, match="Failed to store vectors in Qdrant"):
                await store_vectors_in_qdrant(chunks)

    @pytest.mark.priority("P2")
    def test_get_qdrant_client_singleton(self):
        """Test Qdrant client singleton pattern (client reuse).

        Verifies get_qdrant_client returns same instance on multiple calls. AC6.
        """
        # Reset singleton (clean state for test)
        import raglite.shared.clients as clients_module

        clients_module._qdrant_client = None

        with patch("raglite.shared.clients.QdrantClient") as MockQdrantClient:
            mock_client_instance = Mock()
            MockQdrantClient.return_value = mock_client_instance

            # Call twice
            client1 = get_qdrant_client()
            client2 = get_qdrant_client()

            # Verify same instance returned
            assert client1 is client2
            # Verify QdrantClient constructor called only once
            MockQdrantClient.assert_called_once()

        # Reset singleton after test
        clients_module._qdrant_client = None
