"""Embedding and metadata generation for document chunks.

Generates semantic embeddings and extracts contextual metadata for RAG retrieval.
"""

from typing import TYPE_CHECKING, Any, cast

# Import shared client functions first (for re-export and test compatibility)
from raglite.shared.clients import get_embedding_model, get_mistral_client

if TYPE_CHECKING:
    from collections.abc import Callable

# Inject client functions into submodules before importing from them
# This allows tests to patch the facade and have submodules use the mocks
import raglite.ingestion.embedding_generation.embeddings as _embeddings_module
import raglite.ingestion.embedding_generation.metadata as _metadata_module

# Use setattr to avoid type errors with module attribute assignment
_embeddings_module.get_embedding_model = get_embedding_model
_metadata_module.get_mistral_client = get_mistral_client

# Now import from submodules (which have the injected functions)
from .embeddings import EmbeddingGenerationError, generate_embeddings  # noqa: E402
from .metadata import _metadata_cache, extract_chunk_metadata  # noqa: E402

__all__ = [
    "EmbeddingGenerationError",
    "generate_embeddings",
    "extract_chunk_metadata",
    "_metadata_cache",
    "get_mistral_client",
    "get_embedding_model",
]
