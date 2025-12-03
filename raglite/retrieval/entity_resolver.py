"""Semantic entity resolution using Fin-E5 embeddings.

Phase 5.2: This module provides semantic entity resolution to match
query entities to canonical forms using embedding similarity.

Unlike Phase 2's string-matching normalization (entity_normalizer.py),
this module uses Fin-E5 embeddings to resolve semantic variations that
don't match exact patterns (e.g., "Portuguese Cement" -> "Portugal").

Usage:
    from raglite.retrieval.entity_resolver import resolve_entity_semantic

    entity = resolve_entity_semantic("Portuguese Cement operations")
    # Returns "Portugal" if similarity > 0.7, else None
"""

import logging
from functools import lru_cache

import numpy as np

from raglite.ingestion.entity_normalizer import get_all_canonical_entities
from raglite.shared.clients import get_embedding_model

logger = logging.getLogger(__name__)

# Cosine similarity threshold for entity matching
# Empirically validated: 0.7 balances precision/recall for financial entities
SIMILARITY_THRESHOLD = 0.7


@lru_cache(maxsize=1)
def _get_canonical_entity_embeddings() -> tuple[list[str], np.ndarray]:
    """Pre-compute embeddings for all canonical entities (cached).

    Returns:
        Tuple of (entity_names, embeddings_matrix)
        - entity_names: List of canonical entity names
        - embeddings_matrix: numpy array of shape (n_entities, embedding_dim)

    Note:
        Uses LRU cache to avoid recomputing embeddings on each call.
        Cache is invalidated when process restarts.
    """
    entities = get_all_canonical_entities()

    if not entities:
        logger.warning("No canonical entities found for embedding generation")
        return [], np.array([])

    model = get_embedding_model()

    # Generate embeddings for all canonical entities
    embeddings = model.encode(entities, show_progress_bar=False)

    logger.info(
        "Canonical entity embeddings cached",
        extra={
            "entity_count": len(entities),
            "embedding_dim": embeddings.shape[1] if len(embeddings) > 0 else 0,
        },
    )

    return entities, embeddings


def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Cosine similarity score in range [-1, 1]
    """
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))


def resolve_entity_semantic(
    query: str,
    threshold: float = SIMILARITY_THRESHOLD,
) -> str | None:
    """Resolve entity from query using Fin-E5 semantic embeddings.

    Phase 5.2: Uses embedding similarity to match query text to canonical
    entity names. More robust than pattern matching for semantic variations.

    Args:
        query: Natural language query or entity description
        threshold: Minimum cosine similarity for match (default: 0.7)

    Returns:
        Canonical entity name if similarity > threshold, else None.

    Examples:
        >>> resolve_entity_semantic("Portuguese Cement")
        'Portugal'  # similarity ~0.85

        >>> resolve_entity_semantic("Secil Company")
        'Secil'  # similarity ~0.75

        >>> resolve_entity_semantic("Unknown Corp XYZ")
        None  # similarity < 0.7
    """
    if not query or not query.strip():
        return None

    query = query.strip()

    # Get cached canonical entity embeddings
    entities, entity_embeddings = _get_canonical_entity_embeddings()

    if len(entities) == 0:
        logger.warning("No canonical entities available for semantic resolution")
        return None

    # Generate embedding for query
    model = get_embedding_model()
    query_embedding = model.encode([query], show_progress_bar=False)[0]

    # Compute similarities with all canonical entities
    similarities = []
    for i, entity_embedding in enumerate(entity_embeddings):
        sim = _cosine_similarity(query_embedding, entity_embedding)
        similarities.append((entities[i], sim))

    # Sort by similarity (descending)
    similarities.sort(key=lambda x: x[1], reverse=True)

    # Get best match
    best_entity, best_similarity = similarities[0]

    # Log similarity scores for threshold tuning
    logger.debug(
        "Entity semantic resolution scores",
        extra={
            "query": query[:50],
            "best_match": best_entity,
            "best_similarity": round(best_similarity, 4),
            "top_3": [(e, round(s, 4)) for e, s in similarities[:3]],
            "threshold": threshold,
        },
    )

    # Check if best match meets threshold
    if best_similarity >= threshold:
        logger.info(
            "Entity resolved semantically",
            extra={
                "query": query[:50],
                "resolved_entity": best_entity,
                "similarity": round(best_similarity, 4),
            },
        )
        return best_entity

    # No match above threshold
    logger.debug(
        "Entity not resolved (below threshold)",
        extra={
            "query": query[:50],
            "best_match": best_entity,
            "best_similarity": round(best_similarity, 4),
            "threshold": threshold,
        },
    )
    return None


def resolve_entities_in_query(
    query: str,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[tuple[str, float]]:
    """Find all potential entity matches in a query with scores.

    Useful for queries that may reference multiple entities or for
    debugging/tuning the similarity threshold.

    Args:
        query: Natural language query
        threshold: Minimum cosine similarity for inclusion

    Returns:
        List of (entity, similarity) tuples above threshold, sorted by similarity.

    Example:
        >>> resolve_entities_in_query("Compare Portugal and Tunisia cement")
        [('Portugal', 0.82), ('Tunisia', 0.78), ('Cement', 0.71)]
    """
    if not query or not query.strip():
        return []

    query = query.strip()

    # Get cached canonical entity embeddings
    entities, entity_embeddings = _get_canonical_entity_embeddings()

    if len(entities) == 0:
        return []

    # Generate embedding for query
    model = get_embedding_model()
    query_embedding = model.encode([query], show_progress_bar=False)[0]

    # Compute similarities with all canonical entities
    matches = []
    for i, entity_embedding in enumerate(entity_embeddings):
        sim = _cosine_similarity(query_embedding, entity_embedding)
        if sim >= threshold:
            matches.append((entities[i], round(sim, 4)))

    # Sort by similarity (descending)
    matches.sort(key=lambda x: x[1], reverse=True)

    logger.debug(
        "Multiple entities resolved in query",
        extra={
            "query": query[:50],
            "matches_count": len(matches),
            "matches": matches[:5],
        },
    )

    return matches
