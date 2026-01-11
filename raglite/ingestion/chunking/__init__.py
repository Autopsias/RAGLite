"""Chunking strategies for RAGLite document processing.

Facade module providing backward-compatible imports for all chunking functionality.
"""

# Core chunking utilities
from raglite.ingestion.chunking.core import (
    FixedTokenChunker,
    _get_tiktoken_encoding,
    chunk_document,
    encoding,
)

# Docling-based chunking
from raglite.ingestion.chunking.docling_items import chunk_by_docling_items

# Table splitting utilities
from raglite.ingestion.chunking.table_splitting import split_large_table_by_rows

__all__ = [
    # Core
    "_get_tiktoken_encoding",
    "encoding",
    "FixedTokenChunker",
    "chunk_document",
    # Docling
    "chunk_by_docling_items",
    # Table splitting
    "split_large_table_by_rows",
]
