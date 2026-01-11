"""Storage operations for Qdrant vector database and PostgreSQL metadata.

FACADE MODULE: Re-exports all storage operations for backward compatibility.
Handles vector storage, metadata storage, and SQL table storage for the RAG pipeline.

This module preserves the original public API from storage_operations.py while
organizing code into domain-specific modules:
- vector_store.py: Qdrant vector operations
- metadata_store.py: PostgreSQL chunk metadata
- table_store.py: PostgreSQL table data
"""

# Re-export exception from vector_store
# Re-export PostgreSQL metadata operations
from raglite.ingestion.storage.metadata_store import store_metadata_in_postgresql

# Re-export PostgreSQL table operations
from raglite.ingestion.storage.table_store import store_tables_in_postgresql

# Re-export Qdrant operations
from raglite.ingestion.storage.vector_store import (
    VectorStorageError,
    create_collection,
    store_vectors_in_qdrant,
)

# Explicit public API (matches original storage_operations.py)
__all__ = [
    # Exception
    "VectorStorageError",
    # Qdrant operations
    "create_collection",
    "store_vectors_in_qdrant",
    # PostgreSQL operations
    "store_metadata_in_postgresql",
    "store_tables_in_postgresql",
]
