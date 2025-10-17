"""Document ingestion module for RAGLite.

Handles PDF and Excel ingestion with Docling and openpyxl.
"""

from raglite.ingestion.pipeline import ingest_pdf

__all__ = ["ingest_pdf"]
