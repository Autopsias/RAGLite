"""Core document ingestion functions.

Provides the main ingest_document entry point with format detection.
"""

from __future__ import annotations

from pathlib import Path

from raglite.ingestion.document_ingestion.excel_processing import extract_excel
from raglite.ingestion.document_ingestion.pdf_processing import ingest_pdf
from raglite.shared.logging import get_logger
from raglite.shared.models import DocumentMetadata

logger = get_logger(__name__)


async def ingest_document(
    file_path: str, unit_cache: dict[str, str] | None = None
) -> DocumentMetadata:
    """Ingest financial document (PDF or Excel) with automatic format detection.

    Routes documents to appropriate extraction handler based on file extension.
    Supports PDF (.pdf) and Excel (.xlsx, .xls) formats.

    Story 5.0.6 AC3: Supports cross-document unit cache for 30% additional API reduction.

    Args:
        file_path: Path to document file (relative or absolute)
        unit_cache: Optional shared cache for cross-document unit inference (AC3).
                   If None, creates local cache. If provided (from parallel ingestion),
                   enables metric unit reuse across documents in a batch.

    Returns:
        DocumentMetadata with extraction results

    Raises:
        FileNotFoundError: If document file doesn't exist
        RuntimeError: If parsing fails or format is unsupported
        ValueError: If file extension is not supported

    Example:
        >>> metadata = await ingest_document("reports/Q4_2024.pdf")
        >>> metadata = await ingest_document("data/financials.xlsx")

        >>> # Batch ingestion with shared cache (Story 5.0.6 AC3)
        >>> cache = {}
        >>> meta1 = await ingest_document("report1.pdf", unit_cache=cache)
        >>> meta2 = await ingest_document("report2.pdf", unit_cache=cache)  # Reuses cache
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
        return await ingest_pdf(str(doc_path), unit_cache=unit_cache)
    elif extension in [".xlsx", ".xls"]:
        return await extract_excel(str(doc_path))
    else:
        error_msg = f"Unsupported file format: {extension}. Supported formats: .pdf, .xlsx, .xls"
        logger.error(
            "Unsupported document format",
            extra={"path": str(doc_path), "extension": extension},
        )
        raise ValueError(error_msg)
