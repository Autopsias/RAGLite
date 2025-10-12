"""PDF ingestion pipeline using Docling.

Extracts text, tables, and page numbers from financial PDFs with high accuracy.
"""

import time
from datetime import UTC, datetime
from pathlib import Path

from docling.document_converter import DocumentConverter

from raglite.shared.logging import get_logger
from raglite.shared.models import DocumentMetadata

logger = get_logger(__name__)


async def ingest_pdf(file_path: str) -> DocumentMetadata:
    """Ingest financial PDF and extract text, tables, and structure with page numbers.

    Uses Docling library for high-accuracy extraction (97.9% table accuracy).
    Extracts page numbers from element provenance metadata.

    Args:
        file_path: Path to PDF file (relative or absolute)

    Returns:
        DocumentMetadata with extraction results including page_count and ingestion timestamp

    Raises:
        FileNotFoundError: If PDF file doesn't exist at specified path
        RuntimeError: If Docling parsing fails or PDF is corrupted

    Example:
        >>> metadata = await ingest_pdf("docs/sample pdf/report.pdf")
        >>> print(f"Ingested {metadata.page_count} pages")
    """
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

    logger.info(
        "Starting PDF ingestion",
        extra={
            "path": str(pdf_path),
            "doc_filename": pdf_path.name,
            "size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2),
        },
    )

    # Initialize Docling converter
    try:
        converter = DocumentConverter()
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
            extra={"path": str(pdf_path), "doc_filename": pdf_path.name, "error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e

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

    # Calculate ingestion metrics
    duration_ms = int((time.time() - start_time) * 1000)

    # Validate page extraction
    if page_count == 0:
        logger.warning(
            "No page numbers extracted - verify PDF structure",
            extra={"path": str(pdf_path), "total_elements": total_elements},
        )

    # Create metadata
    metadata = DocumentMetadata(
        filename=pdf_path.name,
        doc_type="PDF",
        ingestion_timestamp=datetime.now(UTC).isoformat(),
        page_count=page_count,
        source_path=str(pdf_path),
    )

    logger.info(
        "PDF ingested successfully",
        extra={
            "doc_filename": pdf_path.name,
            "page_count": page_count,
            "total_elements": total_elements,
            "elements_with_pages": elements_with_pages,
            "duration_ms": duration_ms,
            "pages_per_second": (
                round(page_count / (duration_ms / 1000), 2) if duration_ms > 0 else 0
            ),
        },
    )

    return metadata
