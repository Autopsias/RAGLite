"""Document ingestion package for PDF and Excel files.

Public API for document ingestion with automatic format detection.

This package provides the primary import path for document ingestion functions.
Import from this package or directly from submodules:

    # Package import (recommended for convenience)
    from raglite.ingestion.document_ingestion import ingest_pdf, ingest_document

    # Submodule import (for specific functions)
    from raglite.ingestion.document_ingestion.pdf_processing import ingest_pdf

NOTE: The old `raglite.ingestion.document_ingestion.py` file (shim) is deprecated.
"""

from __future__ import annotations

from raglite.ingestion.document_ingestion.collection import ingest_documents_parallel
from raglite.ingestion.document_ingestion.constants import (
    ALLOWED_URL_SCHEMES,
    MAX_BASE64_CONTENT_SIZE_BYTES,
    MAX_URL_DOWNLOAD_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    URL_DOMAIN_ALLOWLIST,
    URL_DOWNLOAD_TIMEOUT_CONNECT,
    URL_DOWNLOAD_TIMEOUT_TOTAL,
)
from raglite.ingestion.document_ingestion.core import ingest_document
from raglite.ingestion.document_ingestion.excel_processing import extract_excel
from raglite.ingestion.document_ingestion.pdf_processing import ingest_pdf
from raglite.ingestion.document_ingestion.temp_files import (
    temp_file_from_base64,
    temp_file_from_url,
)

__all__ = [
    "ingest_document",
    "ingest_pdf",
    "extract_excel",
    "ingest_documents_parallel",
    "temp_file_from_base64",
    "temp_file_from_url",
    "ALLOWED_URL_SCHEMES",
    "MAX_BASE64_CONTENT_SIZE_BYTES",
    "MAX_URL_DOWNLOAD_SIZE_BYTES",
    "SUPPORTED_EXTENSIONS",
    "URL_DOMAIN_ALLOWLIST",
    "URL_DOWNLOAD_TIMEOUT_CONNECT",
    "URL_DOWNLOAD_TIMEOUT_TOTAL",
]
