"""Integration tests for Qdrant vector storage with real database.

Extended tests for store_vectors_in_qdrant with real infrastructure.
"""

import time

import pytest

# Mark all tests in this module as slow integration tests
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]

# Lazy imports for expensive modules - DO NOT import raglite modules at module level!


@pytest.mark.xdist_group(name="embedding_model_reads")
class TestQdrantStorageIntegration:
    """Integration tests for Qdrant vector storage with real database (Story 1.6).

    Note: Tests in this class load the embedding model (3s overhead).
    The @pytest.mark.xdist_group ensures all tests run in the same worker
    to avoid multiple model loads during parallel execution.
    """

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(60)
    @pytest.mark.usefixtures("warmup_embedding_model")
    async def test_storage_end_to_end_validation(self) -> None:
        """Integration test: End-to-end storage validation with real Qdrant.

        Validates:
        - Collection creation works with real Qdrant
        - Chunks with embeddings are stored successfully
        - Points_count matches chunk_count after storage (AC9)
        - All metadata fields are preserved
        """
        # Lazy imports to avoid test discovery overhead
        from raglite.ingestion.pipeline import generate_embeddings, store_vectors_in_qdrant
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.models import Chunk, DocumentMetadata

        # Create test metadata
        metadata = DocumentMetadata(
            filename="integration_test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-10-13T00:00:00",
            page_count=2,
            source_path="/tmp/integration_test.pdf",
        )

        # Create 10 test chunks with real embeddings
        test_chunks = [
            Chunk(
                chunk_id=f"integration_test.pdf_{i}",
                content=f"Integration test content for chunk {i} with financial data and metrics",
                metadata=metadata,
                page_number=(i % 2) + 1,
                embedding=[],
            )
            for i in range(10)
        ]

        # Generate real embeddings
        chunks_with_embeddings = await generate_embeddings(test_chunks)

        # Verify embeddings were generated (dimension depends on CI_FAST_EMBEDDING)
        from raglite.shared.config import get_active_embedding_dimension

        expected_dim = get_active_embedding_dimension()
        assert all(len(c.embedding) == expected_dim for c in chunks_with_embeddings)

        # Create unique test collection
        test_collection = f"test_storage_{int(time.time())}"

        try:
            # Store vectors in Qdrant
            points_stored = await store_vectors_in_qdrant(
                chunks_with_embeddings, collection_name=test_collection
            )

            # Critical validation: points_count matches chunk_count (AC9)
            assert points_stored == 10, f"Expected 10 points stored, got {points_stored}"

            # Verify collection exists and has correct count
            client = get_qdrant_client()
            collection_info = client.get_collection(test_collection)
            assert collection_info.points_count == 10

            # Retrieve one point to verify metadata
            scroll_result = client.scroll(collection_name=test_collection, limit=1)
            points = scroll_result[0]
            assert len(points) == 1

            # Verify metadata fields are preserved
            point = points[0]
            assert point.payload is not None, "Point payload should not be None"
            assert "chunk_id" in point.payload
            assert "text" in point.payload
            assert "word_count" in point.payload
            assert "source_document" in point.payload
            assert "page_number" in point.payload
            assert "chunk_index" in point.payload

            print(f"\n  ✅ Storage validation complete: {points_stored} points stored successfully")
            print(f"  ✅ Metadata preserved: {list(point.payload.keys())}")

        finally:
            # Cleanup: Delete test collection
            client = get_qdrant_client()
            try:
                client.delete_collection(test_collection)
                print(f"  🧹 Test collection '{test_collection}' cleaned up")
            except Exception as e:
                print(f"  ⚠️  Failed to clean up collection: {e}")

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(60)
    @pytest.mark.usefixtures("warmup_embedding_model")
    async def test_storage_retrieval_roundtrip(self) -> None:
        """Integration test: Storage + retrieval round-trip validation.

        Validates:
        - Chunks can be stored and retrieved from Qdrant
        - Retrieved chunks match original metadata
        - Vector search works correctly
        """
        # Lazy imports to avoid test discovery overhead
        from raglite.ingestion.pipeline import generate_embeddings, store_vectors_in_qdrant
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.models import Chunk, DocumentMetadata

        metadata = DocumentMetadata(
            filename="roundtrip_test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-10-13T00:00:00",
            page_count=1,
            source_path="/tmp/roundtrip_test.pdf",
        )

        # Create test chunks with unique content for search
        test_chunks = [
            Chunk(
                chunk_id=f"roundtrip_test.pdf_{i}",
                content=f"Unique financial content about topic {i}: revenue growth projections",
                metadata=metadata,
                page_number=1,
                embedding=[],
            )
            for i in range(5)
        ]

        # Generate embeddings
        chunks_with_embeddings = await generate_embeddings(test_chunks)

        # Create unique test collection
        test_collection = f"test_roundtrip_{int(time.time())}"

        try:
            # Store vectors
            points_stored = await store_vectors_in_qdrant(
                chunks_with_embeddings, collection_name=test_collection
            )
            assert points_stored == 5

            # Perform vector search using first chunk's embedding
            client = get_qdrant_client()
            search_results = client.query_points(
                collection_name=test_collection,
                query=chunks_with_embeddings[0].embedding,
                using="text-dense",  # Named vector for hybrid search (Story 2.1)
                limit=3,
            ).points

            # Verify search returned results
            assert len(search_results) > 0
            assert len(search_results) <= 3

            # First result should be the original chunk (highest similarity)
            top_result = search_results[0]
            assert top_result.payload is not None, "Top result payload should not be None"
            assert top_result.payload["chunk_id"] == "roundtrip_test.pdf_0"
            assert top_result.payload["page_number"] == 1
            assert "revenue growth projections" in top_result.payload["text"]

            print(
                f"\n  ✅ Round-trip validation complete: Stored {points_stored}, retrieved {len(search_results)}"
            )
            print(f"  ✅ Top result score: {top_result.score:.4f}")

        finally:
            # Cleanup
            client = get_qdrant_client()
            try:
                client.delete_collection(test_collection)
                print(f"  🧹 Test collection '{test_collection}' cleaned up")
            except Exception as e:
                print(f"  ⚠️  Failed to clean up collection: {e}")

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(120)
    async def test_performance_validation_300_chunks(self) -> None:
        """Integration test: Performance validation (<30s for 300 chunks).

        Validates:
        - Storage completes in <30 seconds for 300 chunks (AC10)
        - Batch processing works efficiently
        - No performance degradation with larger datasets
        """
        # Lazy imports to avoid test discovery overhead
        from raglite.ingestion.pipeline import generate_embeddings, store_vectors_in_qdrant
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.models import Chunk, DocumentMetadata

        metadata = DocumentMetadata(
            filename="performance_test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-10-13T00:00:00",
            page_count=60,
            source_path="/tmp/performance_test.pdf",
        )

        # Create 300 test chunks
        test_chunks = [
            Chunk(
                chunk_id=f"performance_test.pdf_{i}",
                content=f"Performance test content chunk {i} with extended financial analysis and metrics data for realistic payload size testing purposes",
                metadata=metadata,
                page_number=(i // 5) + 1,
                embedding=[],
            )
            for i in range(300)
        ]

        # Generate embeddings (this will take time, but not counted in storage perf)
        from raglite.shared.config import get_active_embedding_dimension

        expected_dim = get_active_embedding_dimension()
        print("\n  📊 Generating embeddings for 300 chunks...")
        chunks_with_embeddings = await generate_embeddings(test_chunks)
        assert all(len(c.embedding) == expected_dim for c in chunks_with_embeddings)

        # Create unique test collection
        test_collection = f"test_perf_{int(time.time())}"

        try:
            # Measure storage time only (AC10: <30 seconds)
            print("  📊 Testing storage performance...")
            start_time = time.time()

            points_stored = await store_vectors_in_qdrant(
                chunks_with_embeddings, collection_name=test_collection, batch_size=100
            )

            storage_duration = time.time() - start_time

            # Critical validation: <30 seconds for 300 chunks (AC10)
            assert storage_duration < 30, (
                f"Storage took {storage_duration:.2f}s, exceeds 30s target (AC10)"
            )
            assert points_stored == 300

            # Calculate performance metrics
            chunks_per_second = 300 / storage_duration

            print(f"\n  ✅ Performance target met: {storage_duration:.2f}s for 300 chunks")
            print(f"  📈 Throughput: {chunks_per_second:.2f} chunks/second")
            print(f"  ✅ Target: <30s (achieved: {storage_duration:.2f}s)")

        finally:
            # Cleanup
            client = get_qdrant_client()
            try:
                client.delete_collection(test_collection)
                print(f"  🧹 Test collection '{test_collection}' cleaned up")
            except Exception as e:
                print(f"  ⚠️  Failed to clean up collection: {e}")

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(60)
    @pytest.mark.usefixtures("warmup_embedding_model")
    async def test_metadata_preservation_end_to_end(self) -> None:
        """Integration test: Metadata preservation validation (page_number != None).

        Validates:
        - Page numbers flow from chunking → embedding → Qdrant storage
        - All metadata fields preserved end-to-end
        - No data loss during pipeline
        """
        # Lazy imports to avoid test discovery overhead
        from raglite.ingestion.pipeline import (
            chunk_document,
            generate_embeddings,
            store_vectors_in_qdrant,
        )
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.models import DocumentMetadata

        # Create test document with page information
        full_text = """Page 1 content: Executive Summary
Financial highlights for Q4 2024.

Page 2 content: Revenue Analysis
Detailed revenue breakdown by segment."""

        metadata = DocumentMetadata(
            filename="metadata_flow_test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-10-13T00:00:00",
            page_count=2,
            source_path="/tmp/metadata_flow_test.pdf",
        )

        # Chunk document (preserves page numbers from Story 1.2/1.4)
        chunks = await chunk_document(full_text, metadata, chunk_size=50, overlap=10)
        assert len(chunks) > 0
        assert all(c.page_number > 0 for c in chunks), "All chunks must have valid page numbers"

        # Generate embeddings (Story 1.5)
        chunks_with_embeddings = await generate_embeddings(chunks)

        # Create unique test collection
        test_collection = f"test_metadata_{int(time.time())}"

        try:
            # Store in Qdrant (Story 1.6)
            points_stored = await store_vectors_in_qdrant(
                chunks_with_embeddings, collection_name=test_collection
            )
            assert points_stored == len(chunks)

            # Retrieve all points and verify metadata preservation
            client = get_qdrant_client()
            scroll_result = client.scroll(collection_name=test_collection, limit=100)
            points = scroll_result[0]

            assert len(points) == len(chunks)

            # Critical validation: page_number != None for all points
            for point in points:
                assert point.payload is not None, "Point payload should not be None"
                assert point.payload["page_number"] is not None, (
                    f"Point {point.payload['chunk_id']} has None page_number"
                )
                assert point.payload["page_number"] > 0, (
                    f"Point {point.payload['chunk_id']} has invalid page_number: {point.payload['page_number']}"
                )
                assert point.payload["source_document"] == "metadata_flow_test.pdf"
                assert "chunk_index" in point.payload

            print(f"\n  ✅ Metadata preservation validated: {len(points)} points")
            print(
                f"  ✅ All page numbers preserved: {[p.payload['page_number'] if p.payload else 'None' for p in points]}"
            )

        finally:
            # Cleanup
            client = get_qdrant_client()
            try:
                client.delete_collection(test_collection)
                print(f"  🧹 Test collection '{test_collection}' cleaned up")
            except Exception as e:
                print(f"  ⚠️  Failed to clean up collection: {e}")
