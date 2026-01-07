"""PDF document processing and ingestion.

Handles PDF-specific ingestion using Docling for high-accuracy extraction.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from raglite.ingestion.document_ingestion.pdf_processing.docling_helpers import (
    create_docling_converter,
)
from raglite.ingestion.document_ingestion.pdf_utils import (
    extract_metadata_for_chunks,
)
from raglite.shared.clients import get_mistral_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import DocumentMetadata

# Keep logger name backward compatible for tests expecting old module path
logger = get_logger("raglite.ingestion.document_ingestion.pdf_processing")


def _validate_pdf_path(file_path: str) -> Path:
    """Validate PDF file path and return resolved Path object.

    Args:
        file_path: Path to PDF file (relative or absolute)

    Returns:
        Resolved Path object

    Raises:
        FileNotFoundError: If PDF file doesn't exist
    """
    pdf_path = Path(file_path).resolve()

    if not pdf_path.exists():
        error_msg = f"PDF file not found: {file_path}"
        logger.error(
            "PDF ingestion failed - file not found",
            extra={"path": str(pdf_path), "error": error_msg},
        )
        raise FileNotFoundError(error_msg)

    return pdf_path


async def _initialize_ingestion(
    pdf_path: Path,
    clear_existing: bool,
    force_production: bool,
) -> tuple:
    """Initialize PDF ingestion: clear data, log start, create converter.

    Args:
        pdf_path: Resolved path to PDF file
        clear_existing: If True, clears existing data before ingestion
        force_production: If True, allows clearing production data

    Returns:
        Tuple of (converter, guard)
    """
    from raglite.shared.safety import SafetyGuard

    # Clear Qdrant collection if requested
    if clear_existing:
        from raglite.ingestion.document_ingestion.pdf_utils import (
            clear_existing_data,
            create_qdrant_collection,
            get_qdrant_client,
        )

        await clear_existing_data(force_production=force_production)
        client = get_qdrant_client()
        create_qdrant_collection(client)

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

    converter = create_docling_converter(pdf_path)
    return converter, guard


async def _extract_and_store_tables(
    result: Any,
    pdf_path: Path,
    converter: Any,
    unit_cache: dict[str, str] | None,
) -> list[dict[str, Any]]:
    """Extract tables from Docling result and store in PostgreSQL.

    Args:
        result: Docling conversion result
        pdf_path: Path to PDF file
        converter: Docling converter instance
        unit_cache: Optional shared unit cache for cross-document inference

    Returns:
        List of table rows extracted (may be empty if extraction fails)
    """
    import os

    skip_table_extraction = os.getenv("SKIP_TABLE_EXTRACTION", "false").lower() == "true"

    table_rows: list[dict[str, Any]] = []

    try:
        if not skip_table_extraction:
            from raglite.ingestion.adaptive_table.core.extractor import TableExtractor

            extractor = TableExtractor(converter=converter)
            table_rows = await extractor.extract_tables_from_result(
                result, pdf_path.name, unit_cache=unit_cache
            )

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
            from raglite.ingestion.storage.postgresql_store import store_tables_in_postgresql

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

        return table_rows

    except Exception as e:
        # Don't fail ingestion if table extraction fails - log and continue
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
        return []


def _calculate_page_metrics(result: Any, pdf_path: Path) -> tuple[int, int, int]:
    """Calculate page count and element metrics from Docling result.

    Args:
        result: Docling conversion result
        pdf_path: Path to PDF file

    Returns:
        Tuple of (page_count, total_elements, elements_with_pages)
    """
    page_count = result.document.num_pages()  # type: ignore[attr-defined]

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

    return page_count, total_elements, elements_with_pages


async def _process_chunks_and_store(
    result: Any,
    metadata: DocumentMetadata,
    pdf_path: Path,
    skip_metadata: bool,
) -> list:
    """Process document chunks: extract metadata, generate embeddings, store vectors.

    Args:
        result: Docling conversion result
        metadata: Initial document metadata
        pdf_path: Path to PDF file
        skip_metadata: If True, skip LLM metadata extraction

    Returns:
        List of chunks with embeddings
    """
    from raglite.ingestion.chunking.docling_items import chunk_by_docling_items
    from raglite.ingestion.embedding_generation.embeddings import generate_embeddings

    # Chunk the document using Docling items with provenance
    chunks = await chunk_by_docling_items(result, metadata)

    # Extract business context metadata per chunk using Mistral Small
    mistral_client = get_mistral_client()
    await extract_metadata_for_chunks(chunks, pdf_path.name, mistral_client, skip_metadata)

    # Generate embeddings for chunks
    chunks_with_embeddings = await generate_embeddings(chunks)

    # Store vectors in Qdrant
    if chunks_with_embeddings:
        from raglite.ingestion.storage.metadata_store import store_metadata_in_postgresql
        from raglite.ingestion.storage.vector_store import store_vectors_in_qdrant

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

        # Store metadata in PostgreSQL for structured filtering
        records_stored, records_skipped = await store_metadata_in_postgresql(chunks_with_embeddings)
        logger.info(
            "Metadata stored in PostgreSQL",
            extra={
                "doc_filename": pdf_path.name,
                "records_stored": records_stored,
                "records_skipped": records_skipped,
            },
        )

    return chunks_with_embeddings


def _log_ingestion_complete(
    pdf_path: Path,
    page_count: int,
    chunk_count: int,
    total_elements: int,
    elements_with_pages: int,
    start_time: float,
) -> None:
    """Log successful ingestion completion with metrics.

    Args:
        pdf_path: Path to PDF file
        page_count: Number of pages in document
        chunk_count: Number of chunks created
        total_elements: Total Docling elements found
        elements_with_pages: Elements with page number data
        start_time: Ingestion start timestamp
    """
    duration_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "PDF ingested successfully",
        extra={
            "doc_filename": pdf_path.name,
            "page_count": page_count,
            "chunk_count": chunk_count,
            "total_elements": total_elements,
            "elements_with_pages": elements_with_pages,
            "duration_ms": duration_ms,
            "pages_per_second": (
                round(page_count / (duration_ms / 1000), 2) if duration_ms > 0 else 0
            ),
        },
    )


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

    Story 4.0.6: Changed default from clear_collection=True to clear_existing=False.
    Story 5.0.6 AC3: Supports cross-document unit cache for 30% API reduction.

    Args:
        file_path: Path to PDF file (relative or absolute)
        clear_existing: Clear Qdrant/PostgreSQL before ingestion (default: False)
        skip_metadata: Skip LLM metadata extraction (default: False)
        force_production: Allow clear_existing on production (default: False)
        unit_cache: Optional shared cache for cross-document unit inference

    Returns:
        DocumentMetadata with extraction results

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        RuntimeError: If Docling parsing fails
        ProductionProtectionError: If clear_existing=True on production without force_production
    """
    start_time = time.time()

    # Validate file path
    pdf_path = _validate_pdf_path(file_path)

    # Initialize ingestion (clear data, log, create converter)
    converter, guard = await _initialize_ingestion(pdf_path, clear_existing, force_production)

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

    # Extract and store tables in PostgreSQL
    logger.info(
        "Extracting tables for SQL storage",
        extra={"doc_filename": pdf_path.name},
    )
    await _extract_and_store_tables(result, pdf_path, converter, unit_cache)

    # Calculate page count and element metrics
    page_count, total_elements, elements_with_pages = _calculate_page_metrics(result, pdf_path)

    # Create initial metadata for chunking
    metadata = DocumentMetadata(
        filename=pdf_path.name,
        doc_type="PDF",
        ingestion_timestamp=datetime.now(UTC).isoformat(),
        page_count=page_count,
        source_path=str(pdf_path),
        chunk_count=0,  # Will be updated after chunking
    )

    # Process chunks: extract metadata, generate embeddings, store vectors
    chunks_with_embeddings = await _process_chunks_and_store(
        result, metadata, pdf_path, skip_metadata
    )

    # Update metadata with chunk count
    metadata.chunk_count = len(chunks_with_embeddings)

    # Log completion with metrics
    _log_ingestion_complete(
        pdf_path,
        page_count,
        len(chunks_with_embeddings),
        total_elements,
        elements_with_pages,
        start_time,
    )

    return metadata
