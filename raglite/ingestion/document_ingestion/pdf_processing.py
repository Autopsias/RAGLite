"""PDF document processing and ingestion.

Handles PDF-specific ingestion using Docling for high-accuracy extraction.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

from raglite.ingestion.chunking_strategy import chunk_by_docling_items
from raglite.ingestion.document_ingestion.pdf_utils import (
    clear_existing_data,
    create_qdrant_collection,
    extract_metadata_for_chunks,
)
from raglite.ingestion.embedding_generation import generate_embeddings
from raglite.ingestion.storage import (
    store_metadata_in_postgresql,
    store_tables_in_postgresql,
    store_vectors_in_qdrant,
)
from raglite.ingestion.table_extraction import TableExtractor
from raglite.shared.clients import get_mistral_client, get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import DocumentMetadata

logger = get_logger(__name__)


async def ingest_pdf(
    file_path: str,
    clear_existing: bool = False,
    skip_metadata: bool = False,
    force_production: bool = False,
    unit_cache: dict[str, str] | None = None,
) -> DocumentMetadata:
    """Ingest financial PDF and extract text, tables, and structure with page numbers.

    Uses Docling library for high-accuracy extraction (97.9% table accuracy).
    Extracts page numbers from element provenance metadata.

    Story 4.0.6: Changed default from clear_collection=True to clear_existing=False
    to prevent accidental data loss. Production operations require explicit override.

    Story 5.0.6 AC3: Supports cross-document unit cache for 30% additional API reduction.

    Args:
        file_path: Path to PDF file (relative or absolute)
        clear_existing: If True, clears existing Qdrant collection and PostgreSQL
                       tables before ingestion. Default False to preserve data.
        skip_metadata: If True, skips LLM metadata extraction (Story 2.4) to avoid API issues.
                       Default False. Use when Mistral API is unavailable.
        force_production: If True, allows clear_existing on production database.
                         Required for intentional production data replacement.
        unit_cache: Optional shared cache for cross-document unit inference (AC3).
                   If None, creates local cache. If provided (from parallel ingestion),
                   enables metric unit reuse across documents in a batch.

    Returns:
        DocumentMetadata with extraction results including page_count and ingestion timestamp

    Raises:
        FileNotFoundError: If PDF file doesn't exist at specified path
        RuntimeError: If Docling parsing fails or PDF is corrupted
        ProductionProtectionError: If clear_existing=True on production without force_production

    Example:
        >>> metadata = await ingest_pdf("docs/sample pdf/report.pdf")
        >>> print(f"Ingested {metadata.page_count} pages")

        >>> # Clear existing data (safe in test environment)
        >>> metadata = await ingest_pdf("report.pdf", clear_existing=True)

        >>> # Clear production data (requires explicit override)
        >>> metadata = await ingest_pdf("report.pdf", clear_existing=True, force_production=True)

        >>> # Skip metadata extraction to avoid API errors
        >>> metadata = await ingest_pdf("report.pdf", skip_metadata=True)

        >>> # Batch ingestion with shared cache (Story 5.0.6 AC3)
        >>> cache = {}
        >>> meta1 = await ingest_pdf("report1.pdf", unit_cache=cache)
        >>> meta2 = await ingest_pdf("report2.pdf", unit_cache=cache)  # Reuses cache
    """
    # Lazy import Docling: Avoid hanging on import when this module loads
    # Docling initializes PyTorch/CUDA on import which can hang without GPU
    # Only load when actually ingesting PDFs
    from docling.datamodel.accelerator_options import AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.document_converter import DocumentConverter, PdfFormatOption

    start_time = time.time()

    # Resolve file path
    pdf_path = Path(file_path).resolve()

    if not pdf_path.exists():
        error_msg = f"PDF file not found: {file_path}"
        logger.error(
            "PDF ingestion failed - file not found",
            extra={"path": str(pdf_path), "error": error_msg},
        )
        raise FileNotFoundError(error_msg)

    # Clear Qdrant collection if requested (Story 2.2 fix - prevent data contamination)
    # Story 4.0.6: Default changed to False, requires explicit clear_existing=True
    if clear_existing:
        await clear_existing_data(force_production=force_production)
        # Recreate collection with proper config (named vectors + sparse for BM25)
        client = get_qdrant_client()
        create_qdrant_collection(client)

    from raglite.shared.safety import SafetyGuard

    guard = SafetyGuard()

    logger.info(
        "Starting PDF ingestion",
        extra={
            "path": str(pdf_path),
            "doc_filename": pdf_path.name,
            "size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2),
            "clear_existing": clear_existing,
            "environment": "PRODUCTION" if guard.is_production else "TEST",
        },
    )

    # Initialize Docling converter with table extraction enabled (Story 1.15 fix)
    # Configure table structure recognition to extract table cell data
    # Story 2.1: Use pypdfium backend for 50-60% memory reduction
    try:
        # Story 2.2: Configure parallel page processing
        # Thread count configurable via PDF_PROCESSING_THREADS env var (default: 8)
        # NOTE: Default AcceleratorOptions is 4 threads - we use 8 for 1.55x speedup
        thread_count = settings.pdf_processing_threads

        # Story 2.3 Fix: Add document_timeout to prevent indefinite hangs on large PDFs
        # Timeout set to 1500s (25 minutes) for 160-page PDFs
        # Based on: 40-page = 3m51s, 160-page expected = ~15-18min, buffer = 25min
        pipeline_options = PdfPipelineOptions(
            do_table_structure=True,
            do_ocr=False,  # Disable OCR for 50% speedup - financial PDFs have embedded text
            accelerator_options=AcceleratorOptions(
                num_threads=thread_count,
                device="cpu",  # CRITICAL: Force CPU-only mode to prevent CUDA hang on CI runners
            ),
            document_timeout=1500,  # 25 minutes max per document
        )
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

        # Story 2.1: PyPdfium backend (optimized)
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options, backend=PyPdfiumDocumentBackend
                )
            }
        )
        logger.info(
            "Docling converter initialized with pypdfium backend and table extraction",
            extra={
                "table_mode": "ACCURATE",
                "backend": "pypdfium",
                "num_threads": thread_count,
                "path": str(pdf_path),
            },
        )
    except Exception as e:
        error_msg = f"Failed to initialize Docling converter: {e}"
        logger.error(
            "Docling initialization failed",
            extra={"path": str(pdf_path), "error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e

    # Convert PDF with Docling
    try:
        result = converter.convert(str(pdf_path))
    except Exception as e:
        error_msg = f"Docling parsing failed for {pdf_path.name}: {e}"
        logger.error(
            "PDF parsing failed",
            extra={
                "path": str(pdf_path),
                "doc_filename": pdf_path.name,
                "error": str(e),
            },
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e

    # Story 2.13 AC1: Extract tables to PostgreSQL (avoid double-conversion)
    # Extract tables from Docling result before chunking to reuse conversion
    logger.info(
        "Extracting tables for SQL storage",
        extra={"doc_filename": pdf_path.name},
    )

    # Skip table extraction in CI if env var set (for debugging hangs)
    import os

    skip_table_extraction = os.getenv("SKIP_TABLE_EXTRACTION", "false").lower() == "true"

    try:
        if not skip_table_extraction:
            # Reuse existing converter to avoid duplicate initialization (more efficient)
            # and to enable test mocking (tests can mock converter once, used by both stages)
            extractor = TableExtractor(converter=converter)
            # Milestone 1: Async table extraction with 10x speedup (62 min → 6 min)
            # Story 5.0.6 AC3: Pass unit_cache for cross-document reuse
            # FIX: Use pdf_path.name (with extension) for consistency with Qdrant document IDs
            table_rows = await extractor.extract_tables_from_result(
                result, pdf_path.name, unit_cache=unit_cache
            )
        else:
            table_rows = []

        if table_rows:
            logger.info(
                "Tables extracted from document",
                extra={
                    "doc_filename": pdf_path.name,
                    "table_count": len({row["table_index"] for row in table_rows}),
                    "row_count": len(table_rows),
                },
            )

            # Store tables in PostgreSQL
            rows_stored, rows_skipped = await store_tables_in_postgresql(table_rows)
            logger.info(
                "Table storage complete",
                extra={
                    "doc_filename": pdf_path.name,
                    "rows_stored": rows_stored,
                    "rows_skipped": rows_skipped,
                },
            )
        else:
            logger.info(
                "No tables found in document",
                extra={"doc_filename": pdf_path.name},
            )
    except Exception as e:
        # Don't fail ingestion if table extraction fails - log and continue
        # Story: Fix PostgreSQL Data Synchronization Gap - Make failures visible
        logger.warning(
            "Table extraction failed - document will have vectors but no structured tables in PostgreSQL. "
            "Run 'python scripts/backfill-postgresql-tables.py' to fix after resolving the error.",
            extra={
                "doc_filename": pdf_path.name,
                "error": str(e),
                "error_type": type(e).__name__,
                "action_required": "backfill_tables",
            },
            exc_info=True,
        )

    # Extract page count from DoclingDocument
    # Use num_pages() method which returns total page count
    page_count = result.document.num_pages()

    # Count elements with provenance data for metrics
    total_elements = 0
    elements_with_pages = 0

    for item, _ in result.document.iterate_items():
        total_elements += 1
        if hasattr(item, "prov") and item.prov:
            elements_with_pages += 1

    # Validate page extraction
    if page_count == 0:
        logger.warning(
            "No page numbers extracted - verify PDF structure",
            extra={"path": str(pdf_path), "total_elements": total_elements},
        )

    # Extract full text from Docling result
    # Use export_to_markdown() to get structured text with tables
    try:
        result.document.export_to_markdown()
    except Exception as e:
        logger.warning(
            "Failed to export markdown - falling back to plain text",
            extra={"path": str(pdf_path), "error": str(e)},
        )
        # Fallback: concatenate all text from elements
        "\n".join(item.text for item, _ in result.document.iterate_items() if hasattr(item, "text"))

    # Create initial metadata for chunking
    metadata = DocumentMetadata(
        filename=pdf_path.name,
        doc_type="PDF",
        ingestion_timestamp=datetime.now(UTC).isoformat(),
        page_count=page_count,
        source_path=str(pdf_path),
        chunk_count=0,  # Will be updated after chunking
    )

    # Chunk the document using Docling items with provenance (Story 1.13 fix)
    # This extracts actual page numbers from Docling metadata instead of estimating
    chunks = await chunk_by_docling_items(result, metadata)

    # Story 2.4 AC1 (REVISED): Extract business context metadata PER CHUNK using Mistral Small
    # Story 2.6 AC6 FIX: Create single Mistral client for reuse (client pooling)
    mistral_client = get_mistral_client()
    await extract_metadata_for_chunks(chunks, pdf_path.name, mistral_client, skip_metadata)

    # Generate embeddings for chunks (Story 1.5)
    chunks_with_embeddings = await generate_embeddings(chunks)

    # Store vectors in Qdrant (Story 1.6)
    if chunks_with_embeddings:
        points_stored = await store_vectors_in_qdrant(
            chunks_with_embeddings, collection_name=settings.qdrant_collection_name
        )
        logger.info(
            "Vectors stored in Qdrant",
            extra={
                "doc_filename": pdf_path.name,
                "points_stored": points_stored,
                "collection": settings.qdrant_collection_name,
            },
        )

        # Story 2.6 AC4: Store metadata in PostgreSQL for structured filtering
        # Only attempts storage if chunks have extracted metadata (company_name, metric_category, etc.)
        records_stored, records_skipped = await store_metadata_in_postgresql(chunks_with_embeddings)
        logger.info(
            "Metadata stored in PostgreSQL",
            extra={
                "doc_filename": pdf_path.name,
                "records_stored": records_stored,
                "records_skipped": records_skipped,
            },
        )

    # Update metadata with chunk count
    metadata.chunk_count = len(chunks_with_embeddings)

    # Calculate ingestion metrics
    duration_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "PDF ingested successfully",
        extra={
            "doc_filename": pdf_path.name,
            "page_count": page_count,
            "chunk_count": len(chunks_with_embeddings),
            "total_elements": total_elements,
            "elements_with_pages": elements_with_pages,
            "duration_ms": duration_ms,
            "pages_per_second": (
                round(page_count / (duration_ms / 1000), 2) if duration_ms > 0 else 0
            ),
        },
    )

    return metadata
