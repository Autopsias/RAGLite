"""Chunking strategy for document segmentation - COMPATIBILITY SHIM.

This module has been refactored into raglite.ingestion.chunking package.
All imports are redirected for backward compatibility.
"""

from raglite.ingestion.chunking import (
    FixedTokenChunker,
    _get_tiktoken_encoding,
    chunk_by_docling_items,
    chunk_document,
    encoding,
    split_large_table_by_rows,
)

__all__ = [
    "_get_tiktoken_encoding",
    "encoding",
    "FixedTokenChunker",
    "chunk_document",
    "chunk_by_docling_items",
    "split_large_table_by_rows",
]
