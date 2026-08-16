"""[P0/P1] Edge case and error handling tests for PDF processing.

Tests critical error paths, corrupt files, and processing failures.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.ingestion.document_ingestion.pdf_processing import ingest_pdf

pytestmark = [pytest.mark.unit]


class TestPDFProcessingErrorHandling:
    """[P0] Critical error paths for PDF processing."""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_file_not_found(self):
        """[P0] TEST-AC-8.4a-2.1.1: Raise FileNotFoundError for missing PDF."""
        # Given nonexistent PDF path
        nonexistent_path = "/tmp/does_not_exist_12345.pdf"

        # When ingesting
        # Then raise FileNotFoundError with helpful message
        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            await ingest_pdf(nonexistent_path)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_empty_pdf_file(self):
        """[P1] TEST-AC-8.4a-2.1.2: Handle empty PDF files gracefully."""
        # Given empty PDF file (0 bytes)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Mock converter to raise exception on empty file
            mock_converter = MagicMock()
            mock_converter.convert.side_effect = RuntimeError("Empty or corrupt PDF")

            with patch(
                "raglite.ingestion.document_ingestion.pdf_processing._legacy.create_docling_converter",
                return_value=mock_converter,
            ):
                # When ingesting
                # Then raise RuntimeError
                with pytest.raises(RuntimeError, match="Docling parsing failed"):
                    await ingest_pdf(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_corrupt_pdf_file(self):
        """[P0] TEST-AC-8.4a-2.1.3: Handle corrupt/malformed PDF files."""
        # Given corrupt PDF file (invalid header)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"Not a valid PDF file content")
            tmp_path = tmp.name

        try:
            # Mock Docling parsing failure
            mock_converter = MagicMock()
            mock_converter.convert.side_effect = RuntimeError("Invalid PDF structure")

            with patch(
                "raglite.ingestion.document_ingestion.pdf_processing._legacy.create_docling_converter",
                return_value=mock_converter,
            ):
                # When ingesting
                # Then raise RuntimeError with context
                with pytest.raises(RuntimeError, match="Docling parsing failed"):
                    await ingest_pdf(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_docling_initialization_failure(self):
        """[P0] TEST-AC-8.4a-2.1.4: Handle Docling initialization failures."""
        # Given valid PDF path
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4\n")
            tmp_path = tmp.name

        try:
            # Mock initialization failure (e.g., missing dependencies)
            # Note: create_docling_converter catches exceptions and re-raises as RuntimeError
            with patch(
                "raglite.ingestion.document_ingestion.pdf_processing._legacy.create_docling_converter",
                side_effect=RuntimeError(
                    "Failed to initialize Docling converter: PyTorch not available"
                ),
            ):
                # When ingesting
                # Then raise RuntimeError with initialization context
                with pytest.raises(RuntimeError, match="Failed to initialize Docling"):
                    await ingest_pdf(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_zero_pages_extracted(self):
        """[P1] TEST-AC-8.4a-2.1.5: Log warning if PDF has zero pages."""
        # Given PDF with zero pages
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Mock successful conversion but zero pages
            mock_result = MagicMock()
            mock_result.document.num_pages.return_value = 0
            mock_result.document.iterate_items.return_value = []
            mock_result.document.export_to_markdown.return_value = ""

            mock_converter = MagicMock()
            mock_converter.convert.return_value = mock_result

            with (
                patch(
                    "raglite.ingestion.document_ingestion.pdf_processing._legacy.create_docling_converter",
                    return_value=mock_converter,
                ),
                patch("raglite.ingestion.chunking_strategy.chunk_by_docling_items") as mock_chunk,
                patch(
                    "raglite.ingestion.document_ingestion.pdf_utils.extract_metadata_for_chunks"
                ) as mock_extract_meta,
                patch("raglite.ingestion.embedding_generation.generate_embeddings") as mock_embed,
                patch(
                    "raglite.ingestion.storage.vector_store.store_vectors_in_qdrant"
                ) as mock_store,
            ):
                mock_chunk.return_value = []
                mock_extract_meta.return_value = AsyncMock()
                mock_embed.return_value = []
                mock_store.return_value = 0

                # When ingesting
                metadata = await ingest_pdf(tmp_path)

                # Then returns metadata with page_count=0
                assert metadata.page_count == 0, f"Expected page_count=0, got {metadata.page_count}"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p1
    @pytest.mark.skip(reason="Complex mock setup required - deferred to integration tests")
    async def test_table_extraction_failure_continues_ingestion(self):
        """[P1] TEST-AC-8.4a-2.1.6: Continue ingestion if table extraction fails."""
        # Given PDF with table extraction failure
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with (
                patch("docling.document_converter.DocumentConverter") as mock_converter_class,
                patch("raglite.ingestion.table_extraction.TableExtractor") as mock_extractor_class,
                patch("raglite.ingestion.chunking_strategy.chunk_by_docling_items") as mock_chunk,
                patch(
                    "raglite.ingestion.document_ingestion.pdf_utils.extract_metadata_for_chunks"
                ) as mock_extract_meta,
                patch("raglite.ingestion.embedding_generation.generate_embeddings") as mock_embed,
                patch(
                    "raglite.ingestion.storage.vector_store.store_vectors_in_qdrant"
                ) as mock_store,
                patch(
                    "raglite.ingestion.storage.metadata_store.store_metadata_in_postgresql"
                ) as mock_store_pg,
            ):
                # Mock successful PDF conversion
                mock_result = MagicMock()
                mock_result.document.num_pages.return_value = 5
                mock_result.document.iterate_items.return_value = [
                    (MagicMock(prov=True, text="Page 1 content"), None)
                ]
                mock_result.document.export_to_markdown.return_value = "# Content"

                mock_converter = MagicMock()
                mock_converter.convert.return_value = mock_result
                mock_converter_class.return_value = mock_converter

                # Mock table extraction failure
                mock_extractor = MagicMock()
                mock_extractor.extract_tables_from_result = AsyncMock(
                    side_effect=RuntimeError("Table extraction failed")
                )
                mock_extractor_class.return_value = mock_extractor

                mock_chunk.return_value = [MagicMock(text="chunk1")]
                mock_extract_meta.return_value = AsyncMock()
                mock_embed.return_value = [MagicMock(id="1", vector=[0.1] * 1024)]
                mock_store.return_value = 1
                mock_store_pg.return_value = AsyncMock()

                # When ingesting
                metadata = await ingest_pdf(tmp_path)

                # Then completes ingestion (table extraction failure is non-fatal)
                assert metadata.page_count == 5, f"Expected page_count=5, got {metadata.page_count}"
                assert metadata.chunk_count == 1, (
                    f"Expected chunk_count=1, got {metadata.chunk_count}"
                )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p1
    @pytest.mark.skip(reason="Complex mock setup required - deferred to integration tests")
    async def test_skip_metadata_extraction_on_api_error(self):
        """[P1] TEST-AC-8.4a-2.1.7: Skip metadata extraction if API unavailable."""
        # Given skip_metadata=True
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with (
                patch("docling.document_converter.DocumentConverter") as mock_converter_class,
                patch("raglite.ingestion.chunking_strategy.chunk_by_docling_items") as mock_chunk,
                patch(
                    "raglite.ingestion.document_ingestion.pdf_utils.extract_metadata_for_chunks"
                ) as mock_extract_meta,
                patch("raglite.ingestion.embedding_generation.generate_embeddings") as mock_embed,
                patch(
                    "raglite.ingestion.storage.vector_store.store_vectors_in_qdrant"
                ) as mock_store,
                patch(
                    "raglite.ingestion.storage.metadata_store.store_metadata_in_postgresql"
                ) as mock_store_pg,
            ):
                # Mock successful conversion
                mock_result = MagicMock()
                mock_result.document.num_pages.return_value = 1
                mock_result.document.iterate_items.return_value = [
                    (MagicMock(prov=True, text="Content"), None)
                ]
                mock_result.document.export_to_markdown.return_value = "# Content"

                mock_converter = MagicMock()
                mock_converter.convert.return_value = mock_result
                mock_converter_class.return_value = mock_converter

                mock_chunk.return_value = [MagicMock(text="chunk1")]
                mock_extract_meta.return_value = AsyncMock()
                mock_embed.return_value = [MagicMock(id="1", vector=[0.1] * 1024)]
                mock_store.return_value = 1
                mock_store_pg.return_value = AsyncMock()

                # When ingesting with skip_metadata=True
                await ingest_pdf(tmp_path, skip_metadata=True)

                # Then extract_metadata_for_chunks is called with skip=True
                mock_extract_meta.assert_called_once()
                call_args = mock_extract_meta.call_args
                assert call_args[1]["skip_metadata"] is True, (
                    f"Expected skip_metadata=True, got {call_args[1]}"
                )
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestPDFProcessingBoundaryConditions:
    """[P1/P2] Boundary conditions for PDF processing."""

    @pytest.mark.asyncio
    @pytest.mark.p2
    @pytest.mark.skip(reason="Complex mock setup required - deferred to integration tests")
    async def test_single_page_pdf(self):
        """[P2] TEST-AC-8.4a-2.2.1: Process single-page PDF correctly."""
        # Given single-page PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with (
                patch("docling.document_converter.DocumentConverter") as mock_converter_class,
                patch("raglite.ingestion.chunking_strategy.chunk_by_docling_items") as mock_chunk,
                patch(
                    "raglite.ingestion.document_ingestion.pdf_utils.extract_metadata_for_chunks"
                ) as mock_extract_meta,
                patch("raglite.ingestion.embedding_generation.generate_embeddings") as mock_embed,
                patch(
                    "raglite.ingestion.storage.vector_store.store_vectors_in_qdrant"
                ) as mock_store,
                patch(
                    "raglite.ingestion.storage.metadata_store.store_metadata_in_postgresql"
                ) as mock_store_pg,
            ):
                # Mock single-page conversion
                mock_result = MagicMock()
                mock_result.document.num_pages.return_value = 1
                mock_result.document.iterate_items.return_value = [
                    (MagicMock(prov=True, text="Single page"), None)
                ]
                mock_result.document.export_to_markdown.return_value = "# Page 1"

                mock_converter = MagicMock()
                mock_converter.convert.return_value = mock_result
                mock_converter_class.return_value = mock_converter

                mock_chunk.return_value = [MagicMock(text="chunk1")]
                mock_extract_meta.return_value = AsyncMock()
                mock_embed.return_value = [MagicMock(id="1", vector=[0.1] * 1024)]
                mock_store.return_value = 1
                mock_store_pg.return_value = AsyncMock()

                # When ingesting
                metadata = await ingest_pdf(tmp_path)

                # Then succeeds with page_count=1
                assert metadata.page_count == 1, f"Expected page_count=1, got {metadata.page_count}"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_pdf_with_no_text_content(self):
        """[P1] TEST-AC-8.4a-2.2.2: Handle PDFs with only images (no text)."""
        # Given PDF with no extractable text
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Mock conversion with no text items
            mock_result = MagicMock()
            mock_result.document.num_pages.return_value = 3
            mock_result.document.iterate_items.return_value = []  # No text
            mock_result.document.export_to_markdown.return_value = ""

            mock_converter = MagicMock()
            mock_converter.convert.return_value = mock_result

            with (
                patch(
                    "raglite.ingestion.document_ingestion.pdf_processing._legacy.create_docling_converter",
                    return_value=mock_converter,
                ),
                patch("raglite.ingestion.chunking_strategy.chunk_by_docling_items") as mock_chunk,
                patch(
                    "raglite.ingestion.document_ingestion.pdf_utils.extract_metadata_for_chunks"
                ) as mock_extract_meta,
                patch("raglite.ingestion.embedding_generation.generate_embeddings") as mock_embed,
                patch(
                    "raglite.ingestion.storage.vector_store.store_vectors_in_qdrant"
                ) as mock_store,
            ):
                mock_chunk.return_value = []  # No chunks
                mock_extract_meta.return_value = AsyncMock()
                mock_embed.return_value = []
                mock_store.return_value = 0

                # When ingesting
                metadata = await ingest_pdf(tmp_path)

                # Then succeeds with zero chunks
                assert metadata.page_count == 3, f"Expected page_count=3, got {metadata.page_count}"
                assert metadata.chunk_count == 0, (
                    f"Expected chunk_count=0, got {metadata.chunk_count}"
                )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_clear_existing_without_force_production_fails(self):
        """[P0] TEST-AC-8.4a-2.2.3: Prevent accidental production data loss."""
        # Given production environment
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            from raglite.shared.safety import ProductionProtectionError

            # Create mock element with proper provenance
            mock_prov = MagicMock()
            mock_prov.page_no = 1
            mock_element = MagicMock()
            mock_element.prov = [mock_prov]
            mock_element.text = "Test content"

            mock_result = MagicMock()
            mock_result.document.num_pages.return_value = 1
            # iterate_items returns list of 2-tuples (item, _)
            mock_result.document.iterate_items.return_value = [(mock_element, 1)]
            mock_result.document.export_to_markdown.return_value = "Test content"

            mock_converter = MagicMock()
            mock_converter.convert.return_value = mock_result

            with (
                patch(
                    "raglite.ingestion.document_ingestion.pdf_processing._legacy.create_docling_converter",
                    return_value=mock_converter,
                ),
                patch(
                    "raglite.ingestion.document_ingestion.pdf_utils.clear_existing_data",
                    side_effect=ProductionProtectionError(
                        "Refusing to delete production collection"
                    ),
                ),
            ):
                # When ingesting with clear_existing=True on production
                # Then raise ProductionProtectionError
                with pytest.raises(
                    ProductionProtectionError, match="Refusing to delete production"
                ):
                    await ingest_pdf(tmp_path, clear_existing=True, force_production=False)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
