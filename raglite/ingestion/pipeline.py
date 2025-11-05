"""Document ingestion pipeline - COMPATIBILITY SHIM.

This module maintains backward compatibility by re-exporting all functions from
the refactored focused modules (Story 3.0.1).

All imports from this module continue to work unchanged while the implementation
has been split into maintainable focused modules.

NEW MODULES (Story 3.0.1 Refactoring):
- document_ingestion.py: PDF/Excel extraction (~750 lines)
- chunking_strategy.py: Text + table-aware chunking (~600 lines)
- embedding_generation.py: Embeddings + metadata (~350 lines)
- storage_operations.py: Qdrant + PostgreSQL storage (~580 lines)

TODO: Update test imports to use new modules directly (can be deferred to separate PR)
"""

from __future__ import annotations

# Test compatibility imports - needed for test mocking
import openpyxl  # noqa: F401

from raglite.shared.clients import (  # noqa: F401
    get_embedding_model,
    get_qdrant_client,
)

# Chunking Strategy Module
from .chunking_strategy import (
    chunk_by_docling_items,
    chunk_document,
    split_large_table_by_rows,
)

# Re-export all functions from focused modules
# This ensures backward compatibility with existing test imports
# Document Ingestion Module
from .document_ingestion import (
    extract_excel,
    ingest_document,
    ingest_pdf,
)

# Embedding Generation Module
from .embedding_generation import (
    EmbeddingGenerationError,
    _metadata_cache,
    extract_chunk_metadata,
    generate_embeddings,
)

# Storage Operations Module
from .storage_operations import (
    VectorStorageError,
    create_collection,
    store_metadata_in_postgresql,
    store_tables_in_postgresql,
    store_vectors_in_qdrant,
)

# Explicit exports for type checkers and IDEs
__all__ = [
    # Exceptions
    "EmbeddingGenerationError",
    "VectorStorageError",
    # Document Ingestion
    "ingest_document",
    "ingest_pdf",
    "extract_excel",
    # Chunking
    "chunk_document",
    "chunk_by_docling_items",
    "split_large_table_by_rows",
    # Embeddings & Metadata
    "_metadata_cache",
    "generate_embeddings",
    "extract_chunk_metadata",
    # Storage
    "create_collection",
    "store_vectors_in_qdrant",
    "store_metadata_in_postgresql",
    "store_tables_in_postgresql",
    # Test compatibility (for mocking)
    "openpyxl",
    "get_qdrant_client",
    "get_embedding_model",
]
