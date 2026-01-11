"""PDF document processing and ingestion module.

This module provides PDF-specific ingestion using Docling for high-accuracy extraction.
"""

# Re-export public API from _legacy
# Re-export dependencies for test mocking compatibility
# These are imported by _legacy and tests mock them at this path
from raglite.ingestion.document_ingestion.pdf_utils import (
    clear_existing_data,
    create_qdrant_collection,
)
from raglite.ingestion.document_ingestion.pdf_utils import (
    get_qdrant_client as get_qdrant_client_utils,
)
from raglite.ingestion.embedding_generation import generate_embeddings
from raglite.ingestion.storage import (
    store_metadata_in_postgresql,
    store_tables_in_postgresql,
    store_vectors_in_qdrant,
)
from raglite.ingestion.table_extraction import TableExtractor
from raglite.shared.clients import get_mistral_client, get_qdrant_client

from ._legacy import ingest_pdf

# Re-export qdrant_client utils for test mocking compatibility
get_qdrant_client_utils = get_qdrant_client_utils

__all__ = [
    "ingest_pdf",
    # Test mocking compatibility
    "clear_existing_data",
    "create_qdrant_collection",
    "generate_embeddings",
    "get_mistral_client",
    "get_qdrant_client",
    "get_qdrant_client_utils",
    "store_metadata_in_postgresql",
    "store_tables_in_postgresql",
    "store_vectors_in_qdrant",
    "TableExtractor",
]
