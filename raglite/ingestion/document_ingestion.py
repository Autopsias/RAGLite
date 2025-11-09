"""Document ingestion for PDF and Excel files.

Extracts text, tables, and page numbers from financial documents.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

import openpyxl
import pandas as pd
from qdrant_client.models import (
    Distance,
    SparseIndexParams,
    SparseVectorParams,
    VectorParams,
)

from raglite.ingestion.chunking_strategy import chunk_by_docling_items, chunk_document
from raglite.ingestion.embedding_generation import extract_chunk_metadata, generate_embeddings
from raglite.ingestion.storage_operations import (
    store_metadata_in_postgresql,
    store_tables_in_postgresql,
    store_vectors_in_qdrant,
)
from raglite.ingestion.table_extraction import TableExtractor
from raglite.shared.clients import get_mistral_client, get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import Chunk, DocumentMetadata, ExtractedMetadata

logger = get_logger(__name__)


async def ingest_document(file_path: str) -> DocumentMetadata:
    """Ingest financial document (PDF or Excel) with automatic format detection.

    Routes documents to appropriate extraction handler based on file extension.
    Supports PDF (.pdf) and Excel (.xlsx, .xls) formats.

    Args:
        file_path: Path to document file (relative or absolute)

    Returns:
        DocumentMetadata with extraction results

    Raises:
        FileNotFoundError: If document file doesn't exist
        RuntimeError: If parsing fails or format is unsupported
        ValueError: If file extension is not supported

    Example:
        >>> metadata = await ingest_document("reports/Q4_2024.pdf")
        >>> metadata = await ingest_document("data/financials.xlsx")
    """
    # Resolve file path to check extension
    doc_path = Path(file_path).resolve()

    if not doc_path.exists():
        error_msg = f"Document file not found: {file_path}"
        logger.error(
            "Document ingestion failed - file not found",
            extra={"path": str(doc_path), "error": error_msg},
        )
        raise FileNotFoundError(error_msg)

    # Route based on file extension
    extension = doc_path.suffix.lower()

    if extension == ".pdf":
        return await ingest_pdf(str(doc_path))
    elif extension in [".xlsx", ".xls"]:
        return await extract_excel(str(doc_path))
    else:
        error_msg = f"Unsupported file format: {extension}. Supported formats: .pdf, .xlsx, .xls"
        logger.error(
            "Unsupported document format",
            extra={"path": str(doc_path), "extension": extension},
        )
        raise ValueError(error_msg)


async def ingest_pdf(
    file_path: str, clear_collection: bool = True, skip_metadata: bool = False
) -> DocumentMetadata:
    """Ingest financial PDF and extract text, tables, and structure with page numbers.

    Uses Docling library for high-accuracy extraction (97.9% table accuracy).
    Extracts page numbers from element provenance metadata.

    Args:
        file_path: Path to PDF file (relative or absolute)
        clear_collection: If True, clears existing Qdrant collection before ingestion
                         to prevent data contamination. Default True for clean state.
        skip_metadata: If True, skips LLM metadata extraction (Story 2.4) to avoid API issues.
                       Default False. Use when Mistral API is unavailable.

    Returns:
        DocumentMetadata with extraction results including page_count and ingestion timestamp

    Raises:
        FileNotFoundError: If PDF file doesn't exist at specified path
        RuntimeError: If Docling parsing fails or PDF is corrupted

    Example:
        >>> metadata = await ingest_pdf("docs/sample pdf/report.pdf")
        >>> print(f"Ingested {metadata.page_count} pages")

        >>> # Append to existing collection without clearing
        >>> metadata = await ingest_pdf("report2.pdf", clear_collection=False)

        >>> # Skip metadata extraction to avoid API errors
        >>> metadata = await ingest_pdf("report.pdf", skip_metadata=True)
    """
    # Lazy import Docling: Avoid hanging on import when this module loads
    # Docling initializes PyTorch/CUDA on import which can hang without GPU
    # Only load when actually ingesting PDFs
    from docling.datamodel.accelerator_options import AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.document_converter import DocumentConverter, PdfFormatOption

    start_time = time.time()

    # Checkpoint: Start of function
    print(f"CHECKPOINT: ingest_pdf started for {file_path}", file=sys.stderr, flush=True)

    # Resolve file path
    pdf_path = Path(file_path).resolve()
    print(f"CHECKPOINT: PDF path resolved to {pdf_path}", file=sys.stderr, flush=True)

    if not pdf_path.exists():
        error_msg = f"PDF file not found: {file_path}"
        logger.error(
            "PDF ingestion failed - file not found",
            extra={"path": str(pdf_path), "error": error_msg},
        )
        raise FileNotFoundError(error_msg)

    # Clear Qdrant collection if requested (Story 2.2 fix - prevent data contamination)
    if clear_collection:
        client = get_qdrant_client()
        try:
            client.delete_collection(settings.qdrant_collection_name)
            logger.info(
                "Cleared existing collection",
                extra={"collection": settings.qdrant_collection_name},
            )
        except Exception:
            logger.info(
                "Collection doesn't exist, will create new",
                extra={"collection": settings.qdrant_collection_name},
            )

        # CRITICAL FIX: Also clear PostgreSQL to maintain symmetric data lifecycle
        # This prevents mixed document IDs from accumulating across ingestion runs
        try:
            import psycopg2

            conn_str = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
            conn = psycopg2.connect(conn_str)
            cursor = conn.cursor()

            # Delete all data from both PostgreSQL tables
            cursor.execute("DELETE FROM financial_chunks")
            chunks_deleted = cursor.rowcount
            cursor.execute("DELETE FROM financial_tables")
            tables_deleted = cursor.rowcount

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(
                "Cleared PostgreSQL tables",
                extra={
                    "financial_chunks_deleted": chunks_deleted,
                    "financial_tables_deleted": tables_deleted,
                },
            )
        except Exception as e:
            logger.warning(
                "Failed to clear PostgreSQL tables (might not exist yet)",
                extra={"error": str(e)},
            )

        # Recreate collection with proper config (named vectors + sparse for BM25)
        try:
            client.create_collection(
                collection_name=settings.qdrant_collection_name,
                vectors_config={
                    "text-dense": VectorParams(size=1024, distance=Distance.COSINE),
                },
                sparse_vectors_config={
                    "text-sparse": SparseVectorParams(
                        index=SparseIndexParams(on_disk=False),
                    )
                },
            )
            logger.info(
                "Created fresh collection",
                extra={"collection": settings.qdrant_collection_name, "vector_size": 1024},
            )
        except Exception as e:
            logger.warning(
                "Collection may already exist",
                extra={"collection": settings.qdrant_collection_name, "error": str(e)},
            )

    logger.info(
        "Starting PDF ingestion",
        extra={
            "path": str(pdf_path),
            "doc_filename": pdf_path.name,
            "size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2),
            "clear_collection": clear_collection,
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

        print("CHECKPOINT: Creating DocumentConverter...", file=sys.stderr, flush=True)
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options, backend=PyPdfiumDocumentBackend
                )
            }
        )
        print("CHECKPOINT: DocumentConverter created successfully", file=sys.stderr, flush=True)
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
        print(
            f"CHECKPOINT: Starting Docling conversion of {pdf_path.name}...",
            file=sys.stderr,
            flush=True,
        )
        result = converter.convert(str(pdf_path))
        print(
            f"CHECKPOINT: Docling conversion complete - {result.document.num_pages()} pages",
            file=sys.stderr,
            flush=True,
        )
    except Exception as e:
        error_msg = f"Docling parsing failed for {pdf_path.name}: {e}"
        logger.error(
            "PDF parsing failed",
            extra={"path": str(pdf_path), "doc_filename": pdf_path.name, "error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e

    # Story 2.13 AC1: Extract tables to PostgreSQL (avoid double-conversion)
    # Extract tables from Docling result before chunking to reuse conversion
    print("CHECKPOINT: Starting table extraction...", file=sys.stderr, flush=True)
    logger.info(
        "Extracting tables for SQL storage",
        extra={"doc_filename": pdf_path.name},
    )

    # Skip table extraction in CI if env var set (for debugging hangs)
    skip_table_extraction = os.getenv("SKIP_TABLE_EXTRACTION", "false").lower() == "true"

    try:
        if not skip_table_extraction:
            # Reuse existing converter to avoid duplicate initialization (more efficient)
            # and to enable test mocking (tests can mock converter once, used by both stages)
            extractor = TableExtractor(converter=converter)
            # Milestone 1: Async table extraction with 10x speedup (62 min → 6 min)
            # FIX: Use pdf_path.name (with extension) for consistency with Qdrant document IDs
            table_rows = await extractor.extract_tables_from_result(result, pdf_path.name)
            print(
                f"CHECKPOINT: Table extraction complete - {len(table_rows)} rows",
                file=sys.stderr,
                flush=True,
            )
        else:
            table_rows = []
            print("CHECKPOINT: Table extraction SKIPPED", file=sys.stderr, flush=True)

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
        logger.warning(
            "Table extraction failed - continuing with document ingestion",
            extra={"doc_filename": pdf_path.name, "error": str(e)},
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
    print("CHECKPOINT: Starting chunking...", file=sys.stderr, flush=True)
    chunks = await chunk_by_docling_items(result, metadata)
    print(
        f"CHECKPOINT: Chunking complete - {len(chunks)} chunks created", file=sys.stderr, flush=True
    )

    # Story 2.4 AC1 (REVISED): Extract business context metadata PER CHUNK using Mistral Small
    # ARCHITECTURAL CHANGE: Per-chunk extraction avoids reasoning token overflow and provides
    # more accurate metadata for each chunk (chunks are ~512 tokens, perfect size for Mistral Small)
    # RE-ENABLED for Story 2.6 PostgreSQL data migration
    # NOTE: Performance bugs (sync client, per-request client, no timeout) will be fixed in Task 6 (AC6)
    if settings.mistral_api_key and not skip_metadata:
        logger.info(
            "Starting per-chunk metadata extraction with Mistral Small",
            extra={
                "doc_filename": pdf_path.name,
                "chunk_count": len(chunks),
                "model": settings.metadata_extraction_model,
                "expected_time_sec": len(chunks) * 2,  # ~2 sec per chunk estimate
            },
        )

        # Story 2.6 AC6 FIX: Create single Mistral client for reuse (client pooling)
        # This eliminates per-request connection overhead (10-15x speedup)
        # Now uses shared client factory with timeout configuration
        mistral_client = get_mistral_client()

        # Extract metadata for each chunk with rate limiting (Story 2.4 FIX + Story 2.5 OPTIMIZATION)
        # Semaphore limits concurrent API calls to respect Mistral rate limits
        # RATE LIMIT FIX: Reduced from 20 to 5 concurrent requests to avoid 429 errors
        # Mistral Free API has stricter rate limits than initially tested
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests to Mistral API

        async def extract_for_chunk(chunk: Chunk) -> tuple[Chunk, ExtractedMetadata | None]:
            """Extract metadata for a single chunk with error handling and rate limiting."""
            async with semaphore:  # Limit concurrent requests
                try:
                    # Story 2.6 AC6 FIX: Pass shared client instance to enable connection pooling
                    extracted = await extract_chunk_metadata(
                        text=chunk.content, chunk_id=chunk.chunk_id, client=mistral_client
                    )
                    return (chunk, extracted)
                except Exception as e:
                    # Graceful degradation - continue without metadata for this chunk
                    logger.debug(
                        "Chunk metadata extraction failed (graceful degradation)",
                        extra={"chunk_id": chunk.chunk_id, "error": str(e)},
                    )
                    return (chunk, None)

        # Process chunks with rate-limited concurrency
        results = await asyncio.gather(*[extract_for_chunk(chunk) for chunk in chunks])

        # Inject extracted metadata into chunks (15 RICH SCHEMA fields)
        successful_extractions = 0
        for chunk, extracted_metadata in results:
            if extracted_metadata:
                # Document-Level (7 fields)
                chunk.document_type = extracted_metadata.document_type
                chunk.reporting_period = extracted_metadata.reporting_period
                chunk.time_granularity = extracted_metadata.time_granularity
                chunk.company_name = extracted_metadata.company_name
                chunk.geographic_jurisdiction = extracted_metadata.geographic_jurisdiction
                chunk.data_source_type = extracted_metadata.data_source_type
                chunk.version_date = extracted_metadata.version_date
                # Section-Level (5 fields)
                chunk.section_type = extracted_metadata.section_type
                chunk.metric_category = extracted_metadata.metric_category
                chunk.units = extracted_metadata.units
                chunk.department_scope = extracted_metadata.department_scope
                # Table-Specific (3 fields)
                chunk.table_context = extracted_metadata.table_context
                chunk.table_name = extracted_metadata.table_name
                chunk.statistical_summary = extracted_metadata.statistical_summary
                successful_extractions += 1

        logger.info(
            "Per-chunk metadata extraction complete",
            extra={
                "doc_filename": pdf_path.name,
                "total_chunks": len(chunks),
                "successful_extractions": successful_extractions,
                "success_rate": f"{successful_extractions / len(chunks) * 100:.1f}%",
            },
        )
    else:
        skip_reason = "skip_metadata=True" if skip_metadata else "MISTRAL_API_KEY not configured"
        logger.info(
            f"Metadata extraction skipped - {skip_reason}",
            extra={"doc_filename": pdf_path.name, "skip_metadata": skip_metadata},
        )

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


async def extract_excel(file_path: str) -> DocumentMetadata:
    """Extract financial data from Excel spreadsheet with multi-sheet support.

    Uses openpyxl for Excel parsing and pandas for data manipulation.
    Extracts all sheets preserving numeric formatting and sheet numbers for citations.

    Note: This function is marked async for consistency with the ingestion pipeline
    pattern (ingest_pdf, future chunking/embedding operations). While openpyxl and
    pandas operations are currently synchronous, this allows for future async
    enhancements like streaming large files or parallel sheet processing.

    Args:
        file_path: Path to Excel file (relative or absolute, .xlsx or .xls)

    Returns:
        DocumentMetadata with extraction results including sheet_count as page_count

    Raises:
        FileNotFoundError: If Excel file doesn't exist at specified path
        RuntimeError: If Excel parsing fails, file is password-protected, or corrupted

    Example:
        >>> metadata = await extract_excel("data/financial_report.xlsx")
        >>> print(f"Extracted {metadata.page_count} sheets")
    """
    start_time = time.time()

    # Resolve file path
    excel_path = Path(file_path).resolve()

    if not excel_path.exists():
        error_msg = f"Excel file not found: {file_path}"
        logger.error(
            "Excel extraction failed - file not found",
            extra={"path": str(excel_path), "error": error_msg},
        )
        raise FileNotFoundError(error_msg)

    logger.info(
        "Starting Excel extraction",
        extra={
            "path": str(excel_path),
            "doc_filename": excel_path.name,
            "size_mb": round(excel_path.stat().st_size / (1024 * 1024), 2),
        },
    )

    # Load Excel workbook
    try:
        # data_only=True: Load computed values instead of formulas
        workbook = openpyxl.load_workbook(str(excel_path), data_only=True)
    except openpyxl.utils.exceptions.InvalidFileException as e:
        error_msg = (
            f"Excel parsing failed for {excel_path.name}: Invalid or password-protected file"
        )
        logger.error(
            "Excel file is invalid or password-protected",
            extra={"path": str(excel_path), "doc_filename": excel_path.name, "error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error loading Excel file {excel_path.name}: {e}"
        logger.error(
            "Excel loading failed",
            extra={"path": str(excel_path), "doc_filename": excel_path.name, "error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e

    # Check for empty workbook
    if not workbook.sheetnames:
        logger.warning(
            "Empty Excel workbook - no sheets found",
            extra={"path": str(excel_path), "doc_filename": excel_path.name},
        )
        # Return metadata with zero sheets for empty workbook
        metadata = DocumentMetadata(
            filename=excel_path.name,
            doc_type="Excel",
            ingestion_timestamp=datetime.now(UTC).isoformat(),
            page_count=0,
            source_path=str(excel_path),
        )
        return metadata

    # Extract all sheets with sheet numbers
    sheets_data = []
    total_rows = 0
    skipped_sheets = 0

    try:
        for sheet_number, sheet_name in enumerate(workbook.sheetnames, start=1):
            sheet = workbook[sheet_name]

            # Convert sheet to pandas DataFrame
            # Get all cell values from the sheet
            data = list(sheet.values)

            if not data:
                # Empty sheet - skip but log
                skipped_sheets += 1
                logger.info(
                    "Empty sheet skipped",
                    extra={"sheet_name": sheet_name, "sheet_number": sheet_number},
                )
                continue

            # First row as column headers
            headers = data[0] if data else []
            rows = data[1:] if len(data) > 1 else []

            # Create DataFrame with proper headers
            df = pd.DataFrame(rows, columns=headers)

            # Convert to markdown table format (preserves numeric formatting)
            # to_markdown() preserves numbers, dates, currencies as-is
            sheet_markdown = f"## Sheet {sheet_number}: {sheet_name}\n\n"
            sheet_markdown += df.to_markdown(index=False)

            sheets_data.append(
                {
                    "sheet_name": sheet_name,
                    "sheet_number": sheet_number,
                    "content": sheet_markdown,
                    "row_count": len(df),
                }
            )

            total_rows += len(df)

    except Exception as e:
        error_msg = f"Failed to extract data from sheets in {excel_path.name}: {e}"
        logger.error(
            "Sheet extraction failed",
            extra={"path": str(excel_path), "doc_filename": excel_path.name, "error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e

    # Calculate extraction metrics
    sheet_count = len(sheets_data)

    # Validate sheet extraction
    if sheet_count == 0:
        logger.warning(
            "No sheets extracted - verify Excel file structure",
            extra={"path": str(excel_path), "total_sheets": len(workbook.sheetnames)},
        )

    # Concatenate all sheet markdown for chunking
    full_text = "\n\n".join(sheet["content"] for sheet in sheets_data)

    # Create initial metadata for chunking (use sheet_count as page_count)
    metadata = DocumentMetadata(
        filename=excel_path.name,
        doc_type="Excel",
        ingestion_timestamp=datetime.now(UTC).isoformat(),
        page_count=sheet_count,
        source_path=str(excel_path),
        chunk_count=0,  # Will be updated after chunking
    )

    # Chunk the document if there's content
    chunks = []
    if full_text.strip():
        chunks = await chunk_document(full_text, metadata)

    # Generate embeddings for chunks (Story 1.5)
    chunks_with_embeddings = []
    if chunks:
        chunks_with_embeddings = await generate_embeddings(chunks)

    # Store vectors in Qdrant (Story 1.6)
    if chunks_with_embeddings:
        points_stored = await store_vectors_in_qdrant(
            chunks_with_embeddings, collection_name=settings.qdrant_collection_name
        )
        logger.info(
            "Vectors stored in Qdrant",
            extra={
                "doc_filename": excel_path.name,
                "points_stored": points_stored,
                "collection": settings.qdrant_collection_name,
            },
        )

    # Update metadata with chunk count
    metadata.chunk_count = len(chunks_with_embeddings)

    # Calculate final metrics
    duration_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "Excel extracted successfully",
        extra={
            "doc_filename": excel_path.name,
            "sheet_count": sheet_count,
            "chunk_count": len(chunks_with_embeddings),
            "total_rows": total_rows,
            "skipped_sheets": skipped_sheets,
            "duration_ms": duration_ms,
            "sheets_per_second": (
                round(sheet_count / (duration_ms / 1000), 2) if duration_ms > 0 else 0
            ),
        },
    )

    return metadata
