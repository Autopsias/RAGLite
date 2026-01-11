"""Backward compatibility tests for metadata fields (AC2).

Tests Story 2.4 graceful degradation and backward compatibility.
"""

from pathlib import Path

import pytest

from raglite.ingestion.pipeline import ingest_pdf

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


class TestBackwardCompatibility:
    """Test AC2: Backward compatibility with existing chunks."""

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_chunks_without_metadata_fields(self):
        """Test that chunks without metadata fields still work (backward compatible)."""
        from raglite.shared.models import Chunk, DocumentMetadata

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
            embedding=[0.1] * 1024,
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
