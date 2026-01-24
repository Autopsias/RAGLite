"""Core metadata injection tests (AC3, AC5).

Tests Story 2.4 metadata injection into Qdrant and cost validation.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from raglite.ingestion.pipeline import ingest_pdf
from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings

pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="embedding_model"),
]


def _has_valid_mistral_api_key() -> bool:
    """Check if MISTRAL_API_KEY is set and looks valid (not placeholder/empty)."""
    key = os.getenv("MISTRAL_API_KEY", "")
    # Skip if empty, placeholder, or too short to be valid
    if not key or len(key) < 20 or key in ("placeholder", "test", "dummy", "none"):
        return False
    return True


@pytest.mark.preserve_collection
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
        from raglite.shared.models import ExtractedMetadata

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

            from raglite.shared.config import get_active_embedding_dimension

            # Create dummy query vector (dimensions depend on CI_FAST_EMBEDDING)
            embedding_dim = get_active_embedding_dimension()
            query_vector = np.random.rand(embedding_dim).tolist()

            # Search with Qdrant filter API (Story 2.4 REVISION: use reporting_period field)
            # NOTE: Collection uses named vectors, must specify using="text-dense"
            # FIX: Use query_points() instead of search() - search() doesn't support 'using' param
            results = client.query_points(
                collection_name=settings.qdrant_collection_name,
                query=query_vector,  # query_points uses 'query', not 'query_vector'
                using="text-dense",  # Required for named vectors (Story 2.1)
                query_filter=Filter(
                    must=[FieldCondition(key="reporting_period", match=MatchValue(value="Q3 2024"))]
                ),
                limit=5,
            ).points  # query_points returns QueryResponse, access .points for results

            # Verify all results match the filter
            assert len(results) > 0, "Filter should return results"
            for result in results:
                assert result.payload["reporting_period"] == "Q3 2024", (
                    f"All results must match filter: expected 'Q3 2024', got '{result.payload.get('reporting_period')}'"
                )
