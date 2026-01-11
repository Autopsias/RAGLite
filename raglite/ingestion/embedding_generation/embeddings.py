"""Fin-E5 embedding generation for document chunks."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from raglite.shared.logging import get_logger
from raglite.shared.models import Chunk

# Import from parent facade for test compatibility
# Tests patch the facade, so we must import from there at runtime
get_embedding_model: Any | None = None

# Use parent module name for logger to maintain backward compatibility with tests
logger = get_logger("raglite.ingestion.embedding_generation")


# Exception class for embedding operations
class EmbeddingGenerationError(Exception):
    """Raised when embedding generation fails."""

    pass


async def generate_embeddings(chunks: list[Chunk]) -> list[Chunk]:
    """Generate Fin-E5 embeddings for document chunks.

    Processes chunks in batches of 32 for memory efficiency. Populates the
    embedding field of each Chunk with 1024-dimensional vectors.

    Args:
        chunks: List of Chunk objects from chunking pipeline

    Returns:
        Same list with embedding field populated (1024-dimensional vectors)

    Raises:
        EmbeddingGenerationError: If embedding generation fails

    Strategy:
        - Batch processing: 32 chunks per batch for memory efficiency
        - Fin-E5 model: intfloat/e5-large-v2 (1024 dimensions)
        - Model cached: Loaded once at module level, reused across calls
        - Empty chunks: Handled gracefully (skip or zero vector)
        - Performance: <2 minutes target for 300-chunk document

    Example:
        >>> chunks = await chunk_document("Document text...", metadata)
        >>> chunks_with_embeddings = await generate_embeddings(chunks)
        >>> assert all(len(c.embedding) == 1024 for c in chunks_with_embeddings)
    """
    start_time = time.time()

    logger.info(
        "Generating embeddings",
        extra={"chunk_count": len(chunks), "model": "intfloat/e5-large-v2"},
    )

    if not chunks:
        logger.warning("No chunks provided for embedding generation")
        return []

    # Load model (singleton pattern)
    # Look up from parent facade at runtime for test compatibility
    import sys

    parent_module = sys.modules["raglite.ingestion.embedding_generation"]
    model = parent_module.get_embedding_model()
    batch_size = 32

    # Process in batches
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [chunk.content for chunk in batch]

        try:
            # Generate embeddings for batch
            embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False)

            # Populate embedding field (convert numpy array to list for JSON serialization)
            for chunk, embedding in zip(batch, embeddings, strict=False):
                chunk.embedding = embedding.tolist()

            logger.info(
                f"Batch {i // batch_size + 1} complete",
                extra={
                    "batch_size": len(batch),
                    "embeddings_shape": str(embeddings.shape),
                    "batch_index": i // batch_size + 1,
                },
            )

        except Exception as e:
            error_msg = f"Failed to generate embeddings for batch {i // batch_size + 1}: {e}"
            logger.error(
                "Embedding generation failed for batch",
                extra={
                    "batch_index": i // batch_size + 1,
                    "batch_size": len(batch),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise EmbeddingGenerationError(error_msg) from e

    # Calculate final metrics
    duration_ms = int((time.time() - start_time) * 1000)
    embedding_dim = len(chunks[0].embedding) if chunks and chunks[0].embedding else 0

    logger.info(
        "Embedding generation complete",
        extra={
            "chunk_count": len(chunks),
            "dimensions": embedding_dim,
            "duration_ms": duration_ms,
            "chunks_per_second": (
                round(len(chunks) / (duration_ms / 1000), 2) if duration_ms > 0 else 0
            ),
        },
    )

    return chunks
