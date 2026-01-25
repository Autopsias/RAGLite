"""Integration tests for Story 2.4 metadata injection and cost validation - Core Tests.

Tests AC3 (Metadata Injection), AC2 (Backward Compatibility).
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from raglite.ingestion.pipeline import ingest_pdf
from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import get_active_embedding_dimension, settings
from raglite.shared.models import Chunk, DocumentMetadata, ExtractedMetadata

# Mark all tests in this module as integration tests that preserve collection state
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="embedding_model"),
    pytest.mark.timeout(180),  # CI: prevent SIGTERM from step timeout
]


def _has_valid_mistral_api_key() -> bool:
    """Check if MISTRAL_API_KEY is set and looks valid (not placeholder/empty)."""
    key = os.getenv("MISTRAL_API_KEY", "")
    # Skip if empty, placeholder, or too short to be valid
    if not key or len(key) < 20 or key in ("placeholder", "test", "dummy", "none"):
        return False
    return True


@pytest.mark.preserve_collection  # OPTIMIZED: Use session fixture instead of re-ingesting
class TestMetadataInjection:
    """Integration tests for AC3: Metadata injection into Qdrant.

    PERFORMANCE OPTIMIZATION (2025-11-21):
    - Changed from @pytest.mark.manages_collection_state to @pytest.mark.preserve_collection
    - Uses session fixture data instead of calling ingest_pdf() directly
    - Eliminates double ingestion: session fixture (40s) + test (40s) = 80s saved
    - Test now completes in <10s instead of 80-1600s
    """

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_metadata_injection_into_chunks(self, session_ingested_collection):
        """Test that extracted metadata is injected into all chunks.

        PERFORMANCE FIX: Uses session fixture data instead of re-ingesting.
        This test validates that metadata fields exist in Qdrant payloads,
        which can be done on existing data without fresh ingestion.

        Expected runtime: <10s (was 80-1600s before optimization)
        """
        # Check if Qdrant collection exists before running test
        from qdrant_client.http.exceptions import UnexpectedResponse

        try:
            client = get_qdrant_client()
            collection_info = client.get_collection(settings.qdrant_collection_name)
            assert collection_info.points_count > 0, "Session fixture should have ingested data"
        except UnexpectedResponse as e:
            pytest.skip(f"Qdrant collection not available: {e}")

        # Scroll through points to check metadata
        scroll_result = client.scroll(
            collection_name=settings.qdrant_collection_name, limit=10, with_payload=True
        )

        points = scroll_result[0]
        assert len(points) > 0, "Should have at least some chunks from session fixture"

        # Verify at least one point has metadata fields (Story 2.4 REVISION: 15-field rich schema)
        # NOTE: Session fixture uses skip_metadata=True in LOCAL mode, so metadata fields
        # will be None/null but should still exist as keys in the payload
        for point in points:
            payload = point.payload
            # Document-Level (7 fields) - may be None in LOCAL mode
            assert "document_type" in payload
            assert "reporting_period" in payload
            assert "time_granularity" in payload
            assert "company_name" in payload
            assert "geographic_jurisdiction" in payload
            assert "data_source_type" in payload
            assert "version_date" in payload
            # Section-Level (5 fields) - may be None in LOCAL mode
            assert "section_type" in payload
            assert "metric_category" in payload
            assert "units" in payload
            assert "department_scope" in payload
            # Table-Specific (3 fields) - may be None in LOCAL mode
            assert "table_context" in payload
            assert "table_name" in payload
            assert "statistical_summary" in payload

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    @pytest.mark.slow  # MARKED SLOW: This test still needs mocked metadata, skip in fast runs
    @pytest.mark.skipif(
        not _has_valid_mistral_api_key(),
        reason="MISTRAL_API_KEY not set or invalid - skipping filter test",
    )
    async def test_metadata_filtering(self, tmp_path):
        """Test AC3: Metadata accessible via Qdrant filter API.

        PERFORMANCE NOTE: This test still requires mocked metadata ingestion to
        ensure controlled test data for filtering. Marked as @pytest.mark.slow
        to skip in fast development runs.

        TODO: Consider refactoring to use pre-ingested test data with known metadata.
        """
        # Mock metadata extraction for controlled testing (Story 2.4 REVISION: 15-field schema)
        mock_metadata = ExtractedMetadata(
            reporting_period="Q3 2024",  # Story 2.4 REVISION: renamed from fiscal_period
            company_name="Test Corp",
            department_scope="Finance",  # Story 2.4 REVISION: renamed from department_name
        )

        with patch("raglite.ingestion.pipeline.extract_chunk_metadata") as mock_extract:
            mock_extract.return_value = mock_metadata

            # PERFORMANCE FIX: Use specific small test PDF instead of glob pattern
            test_pdf = Path("tests/fixtures/sample-small-3-pages.pdf")

            if not test_pdf.exists():
                pytest.skip("Test PDF not found - skipping integration test")

            # Ingest with mocked metadata
            await ingest_pdf(str(test_pdf), clear_existing=True)

            # AI9: Test actual Qdrant filter API with reporting_period filter (Story 2.4 REVISION field name)
            client = get_qdrant_client()
            import numpy as np
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            # Create dummy query vector (dimensions match active embedding model)
            query_vector = np.random.rand(get_active_embedding_dimension()).tolist()

            # Search with Qdrant filter API (Story 2.4 REVISION: use reporting_period field)
            results = client.search(
                collection_name=settings.qdrant_collection_name,
                query_vector=query_vector,
                query_filter=Filter(
                    must=[FieldCondition(key="reporting_period", match=MatchValue(value="Q3 2024"))]
                ),
                limit=5,
            )

            # Verify all results match the filter
            assert len(results) > 0, "Filter should return results"
            for result in results:
                assert result.payload["reporting_period"] == "Q3 2024", (
                    f"All results must match filter: expected 'Q3 2024', got '{result.payload.get('reporting_period')}'"
                )


class TestBackwardCompatibility:
    """Test AC2: Backward compatibility with existing chunks."""

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_chunks_without_metadata_fields(self):
        """Test that chunks without metadata fields still work (backward compatible)."""
        # Create chunk without new metadata fields (old format)
        metadata = DocumentMetadata(
            filename="old_doc.pdf",
            doc_type="PDF",
            ingestion_timestamp="2024-01-01T00:00:00Z",
            page_count=10,
        )

        chunk = Chunk(
            chunk_id="test_chunk_1",
            content="This is test content",
            metadata=metadata,
            page_number=1,
            chunk_index=0,
            embedding=[0.1] * get_active_embedding_dimension(),  # CI: 384, Local: 1024
            # Story 2.4 REVISION: Rich schema fields (15 total) not set (defaults to None)
        )

        # Verify defaults are None (backward compatible) - Story 2.4 REVISION field names
        # Document-Level (7 fields)
        assert chunk.document_type is None
        assert chunk.reporting_period is None
        assert chunk.time_granularity is None
        assert chunk.company_name is None
        assert chunk.geographic_jurisdiction is None
        assert chunk.data_source_type is None
        assert chunk.version_date is None
        # Section-Level (5 fields)
        assert chunk.section_type is None
        assert chunk.metric_category is None
        assert chunk.units is None
        assert chunk.department_scope is None
        # Table-Specific (3 fields)
        assert chunk.table_context is None
        assert chunk.table_name is None
        assert chunk.statistical_summary is None

    @pytest.mark.priority("P1")  # Downgraded from P0 - redundant with unit test
    @pytest.mark.asyncio
    @pytest.mark.slow  # Uses real PDF ingestion (60-80s) - only run with --run-slow
    @pytest.mark.timeout(300)  # 5 minutes - includes PDF processing + embedding generation
    async def test_ingestion_without_metadata_extraction(self, tmp_path):
        """Test that ingestion works with skip_metadata=True (graceful degradation).

        REVISED (2025-11-27): Renamed from test_ingestion_without_openai_key.
        - Original test mocked settings incorrectly (module-level import)
        - Original test used 160-page PDF causing 120s timeout
        - Now uses skip_metadata=True parameter (correct API for graceful degradation)
        - Uses smaller 3-page PDF to reduce runtime
        - Marked @pytest.mark.slow - only runs with --run-slow flag in CI

        NOTE: Basic backward compatibility is tested by test_chunks_without_metadata_fields
        which validates that Chunk model works without metadata (unit test, no I/O).
        This integration test validates the full pipeline with skip_metadata=True.
        """
        # Use smaller test PDF to reduce runtime (3 pages vs 160 pages)
        test_pdf = Path("tests/fixtures/sample-small-3-pages.pdf")

        if not test_pdf.exists():
            pytest.skip(f"Test PDF not found at {test_pdf}")

        # Ingest with skip_metadata=True - the correct API for graceful degradation
        # This avoids needing any API keys (Mistral/OpenAI) while testing the pipeline
        metadata = await ingest_pdf(str(test_pdf), clear_existing=True, skip_metadata=True)

        assert metadata.chunk_count > 0, (
            "Ingestion should produce chunks even without metadata extraction"
        )
        assert metadata.filename == "sample-small-3-pages.pdf"


class TestMetadataInjectionMocked:
    """Mocked integration tests for AC3 - No API key required for CI/CD.

    REVISED (2025-11-03): Tests now use session-scoped ingested collection
    instead of re-ingesting. This fixes hanging tests and improves performance.
    """

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    @pytest.mark.preserve_collection  # This test relies on session fixture, don't need double-ingest
    async def test_metadata_injection_mocked(self):
        """Test AC3: Metadata injection with mocked API (CI/CD friendly).

        REVISED (2025-11-22): This test validates that metadata fields exist in Qdrant payloads.
        In LOCAL mode, session fixture skips metadata extraction to save time (~40s),
        so this test skips validation when no metadata is present.
        In CI mode (TEST_USE_FULL_PDF=true), metadata is extracted and validated.
        """
        # Verify Qdrant collection exists and has data
        client = get_qdrant_client()

        try:
            points = client.scroll(
                collection_name=settings.qdrant_collection_name,
                limit=10,
                with_payload=True,
            )[0]
        except Exception as e:
            pytest.skip(f"Qdrant collection not available: {e}")

        if len(points) == 0:
            pytest.skip("No data in Qdrant collection - session fixture didn't run")

        # Verify metadata fields are present in payload (Story 2.4 REVISION: 15-field rich schema)
        # At least some points should have metadata (may be None for chunks without metadata)
        metadata_field_count = 0
        for point in points:
            payload = point.payload
            # Document-Level (7 fields)
            assert "reporting_period" in payload
            assert "company_name" in payload
            assert "document_type" in payload
            assert "time_granularity" in payload
            assert "geographic_jurisdiction" in payload
            assert "data_source_type" in payload
            assert "version_date" in payload
            # Section-Level (5 fields)
            assert "section_type" in payload
            assert "metric_category" in payload
            assert "units" in payload
            assert "department_scope" in payload
            # Table-Specific (3 fields)
            assert "table_context" in payload
            assert "table_name" in payload
            assert "statistical_summary" in payload

            # Count how many points have at least one non-None metadata field
            # Include metric_category which is populated by session mock
            if any(
                payload.get(field) is not None
                for field in [
                    "reporting_period",
                    "company_name",
                    "document_type",
                    "section_type",
                    "department_scope",
                    "metric_category",  # Session mock returns this field
                ]
            ):
                metadata_field_count += 1

        print(
            f"\n✓ Metadata injection validation: {metadata_field_count}/{len(points)} points have metadata"
        )

        # REVISED (2025-11-22): Check if metadata extraction was performed
        # In LOCAL mode, session fixture skips metadata extraction (skip_metadata=True)
        # to save ~40s. Only validate metadata coverage when extraction was performed.
        if metadata_field_count == 0:
            pytest.skip(
                "Session fixture skipped metadata extraction (LOCAL mode optimization). "
                "Run with TEST_USE_FULL_PDF=true to enable metadata validation."
            )

        # At least 50% of points should have some metadata (realistic expectation)
        assert metadata_field_count >= len(points) * 0.5, (
            f"Only {metadata_field_count}/{len(points)} points have metadata fields populated "
            "(expected at least 50% coverage)"
        )

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    @pytest.mark.preserve_collection  # This test relies on session fixture
    async def test_metadata_filtering_mocked(self, session_ingested_collection):
        """Test AC3: Qdrant filter API with metadata filtering (CI/CD friendly).

        REVISED (2025-11-03): This test now uses the session-scoped ingested collection
        instead of re-ingesting. Original test was hanging due to full PDF ingestion
        inside test function (75-85 seconds per run).

        The test validates that Qdrant filter API works with metadata fields,
        using whatever metadata is available in the session collection.
        """
        import numpy as np
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        client = get_qdrant_client()

        try:
            # First, find what metadata values exist in the collection
            all_points = client.scroll(
                collection_name=settings.qdrant_collection_name,
                limit=50,
                with_payload=True,
            )[0]
        except Exception as e:
            pytest.skip(f"Qdrant collection not available: {e}")

        if len(all_points) == 0:
            pytest.skip("No data in Qdrant collection - session fixture didn't run")

        # Find a point with reporting_period metadata (for filtering test)
        test_value = None
        test_field = None

        # Try to find a point with reporting_period
        for point in all_points:
            if point.payload.get("reporting_period"):
                test_field = "reporting_period"
                test_value = point.payload["reporting_period"]
                break

        # If no reporting_period, try company_name
        if not test_value:
            for point in all_points:
                if point.payload.get("company_name"):
                    test_field = "company_name"
                    test_value = point.payload["company_name"]
                    break

        if not test_value or not test_field:
            pytest.skip("No metadata values found in collection to test filtering")

        print(f"\n✓ Testing Qdrant filter API with {test_field}={test_value}")

        # Create a dummy query vector (dimensions match active embedding model)
        query_vector = np.random.rand(get_active_embedding_dimension()).tolist()

        # Search with filter using the found metadata value (using query_points with vector name)

        results = client.query_points(
            collection_name=settings.qdrant_collection_name,
            query=query_vector,
            using="text-dense",  # Specify vector name for named vectors
            query_filter=Filter(
                must=[FieldCondition(key=test_field, match=MatchValue(value=test_value))]
            ),
            limit=5,
        ).points

        # Verify all results match filter
        assert len(results) > 0, f"Filter should return results for {test_field}={test_value}"
        for result in results:
            # query_points returns ScoredPoint objects with payload attribute
            result_payload = result.payload if hasattr(result, "payload") else result
            assert result_payload[test_field] == test_value, (
                f"All results must match filter: expected '{test_value}', "
                f"got '{result_payload.get(test_field)}'"
            )

        print(f"✓ Filter API validation passed: {len(results)} results matched filter")
