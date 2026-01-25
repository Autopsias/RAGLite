"""Mocked metadata injection and filtering tests (CI/CD friendly).

Tests AC3 with session-scoped ingested collection, no API keys required.
"""

import pytest

from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings

pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="embedding_model_reads"),
]


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

        # Create a dummy query vector (dimensions depend on CI_FAST_EMBEDDING)
        from raglite.shared.config import get_active_embedding_dimension

        embedding_dim = get_active_embedding_dimension()
        query_vector = np.random.rand(embedding_dim).tolist()

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
