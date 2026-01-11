"""Docling PDF converter initialization helpers.

This module contains helper functions for initializing and configuring
the Docling document converter with optimal settings for financial PDFs.
"""

from __future__ import annotations

from pathlib import Path

from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption

from raglite.shared.config import settings
from raglite.shared.logging import get_logger

# Lazy imports for test mocking compatibility
# PyPdfiumDocumentBackend imported inside function to enable test mocking

logger = get_logger(__name__)


def create_docling_converter(pdf_path: Path) -> DocumentConverter:
    """Initialize Docling converter with optimal settings for financial PDFs.

    Story 1.15: Enable table extraction for 97.9% accuracy
    Story 2.1: Use pypdfium backend for 50-60% memory reduction
    Story 2.2: Configure parallel page processing with 8 threads (1.55x speedup)
    Story 2.3: Add document_timeout to prevent indefinite hangs on large PDFs

    Args:
        pdf_path: Path to PDF file for logging purposes

    Returns:
        Configured DocumentConverter instance

    Raises:
        RuntimeError: If converter initialization fails

    Example:
        >>> converter = create_docling_converter(Path("report.pdf"))
        >>> result = converter.convert("report.pdf")
    """
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
        # Lazy import for test mocking compatibility
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
        return converter
    except Exception as e:
        error_msg = f"Failed to initialize Docling converter: {e}"
        logger.error(
            "Docling initialization failed",
            extra={"path": str(pdf_path), "error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(error_msg) from e
