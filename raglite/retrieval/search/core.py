"""Core search functionality for RAGLite.

Provides fundamental vector search operations, embedding generation,
and metric discovery.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from raglite.shared.clients import get_embedding_model, get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import QueryResult

if TYPE_CHECKING:
    from qdrant_client.models import Filter

logger = get_logger(__name__)


class QueryError(Exception):
    """Exception raised when vector search query fails."""

    pass


async def get_metric_names(use_cache: bool = True) -> list[str]:
    """Get list of available metric names from database.

    Story 5.0.7 Phase 5.1: Lightweight wrapper reusing existing metric discovery.
    Reuses list_available_metrics() from Story 5.0.4 with built-in caching.

    Args:
        use_cache: Use cached results if available (default True, 5-minute TTL)

    Returns:
        List of metric names (e.g., ["Revenue", "EBITDA", "Variable Cost", ...])

    Example:
        >>> names = await get_metric_names()
        >>> "Revenue" in names
        True
    """
    from raglite.forecasting.metrics import list_available_metrics

    metrics = await list_available_metrics(use_cache=use_cache)
    return [m.name for m in metrics]


async def generate_query_embedding(query: str) -> list[float]:
    """Generate embedding vector for natural language query.

    Args:
        query: Natural language query string

    Returns:
        1024-dimensional embedding vector (list of floats)

    Raises:
        QueryError: If embedding generation fails or query is empty

    Strategy:
        - Reuse embedding model from Story 1.5 (get_embedding_model singleton)
        - Same model as document embeddings (Fin-E5 intfloat/e5-large-v2)
        - Returns list[float] compatible with Qdrant query_points API

    Example:
        >>> embedding = await generate_query_embedding("What is the revenue?")
        >>> len(embedding)
        1024
    """
    if not query or not query.strip():
        raise QueryError("Query cannot be empty")

    try:
        logger.info("Generating query embedding", extra={"query_length": len(query)})
        start_time = time.time()

        model = get_embedding_model()
        embedding = model.encode([query])[0]  # Returns numpy array

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            "Query embedding generated",
            extra={"embedding_dim": len(embedding), "elapsed_ms": round(elapsed_ms, 2)},
        )

        # Convert to list for Qdrant compatibility
        result: list[float] = embedding.tolist()
        return result

    except QueryError:
        # Re-raise QueryError as-is
        raise
    except Exception as e:
        logger.error(f"Query embedding generation failed: {e}", exc_info=True)
        raise QueryError(f"Failed to generate query embedding: {e}") from e


def _build_qdrant_filter(filters: dict[str, str] | None) -> Filter | None:
    """Build Qdrant filter from metadata dictionary.

    Args:
        filters: Dictionary of metadata field names to values, or None

    Returns:
        Qdrant Filter object with conditions, or None if no valid filters

    Strategy:
        - Supports all 15 rich metadata fields from Story 2.4
        - Uses MatchValue for exact string matching
        - Returns None if no valid filter fields provided
    """
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    if not filters:
        return None

    conditions: list[FieldCondition] = []

    # Supported filter fields (all 15 rich metadata fields + legacy source_document)
    supported_fields = [
        # Document-Level (7)
        "document_type",
        "reporting_period",
        "time_granularity",
        "company_name",
        "geographic_jurisdiction",
        "data_source_type",
        "version_date",
        # Section-Level (5)
        "section_type",
        "metric_category",
        "units",
        "department_scope",
        # Table-Specific (3)
        "table_context",
        "table_name",
        "statistical_summary",
        # Legacy
        "source_document",
    ]

    for field in supported_fields:
        if field in filters:
            conditions.append(FieldCondition(key=field, match=MatchValue(value=filters[field])))

    if conditions:
        return Filter(must=conditions)

    return None


def _convert_points_to_results(points: list) -> list[QueryResult]:
    """Convert Qdrant search points to QueryResult objects.

    Args:
        points: List of Qdrant ScoredPoint objects with payloads

    Returns:
        List of QueryResult objects with validated metadata

    Strategy:
        - Validates required metadata (page_number, source_document)
        - Logs warnings for missing metadata but creates results anyway
        - Skips points with no payload (defensive programming)
    """
    results = []

    for point in points:
        payload = point.payload

        # Type guard: Qdrant with_payload=True should always return dict
        if payload is None:
            logger.warning(
                f"Point {point.id} has no payload, skipping",
                extra={"point_id": str(point.id)},
            )
            continue

        # Validate required metadata (CRITICAL for Story 1.8 source attribution)
        if payload.get("page_number") is None:
            logger.warning(
                f"Chunk {payload.get('chunk_id')} missing page_number",
                extra={"chunk_id": payload.get("chunk_id")},
            )

        if not payload.get("source_document"):
            logger.warning(
                f"Chunk {payload.get('chunk_id')} missing source_document",
                extra={"chunk_id": payload.get("chunk_id")},
            )

        results.append(
            QueryResult(
                score=point.score,
                text=payload["text"],
                source_document=payload["source_document"],
                page_number=payload["page_number"],
                chunk_index=payload["chunk_index"],
                word_count=payload["word_count"],
            )
        )

    return results


async def search_documents(
    query: str, top_k: int = 5, filters: dict[str, str] | None = None
) -> list[QueryResult]:
    """Search documents using vector similarity.

    Args:
        query: Natural language query
        top_k: Number of results to return (default: 5)
        filters: Optional metadata filters. Supports all 15 rich metadata fields:
            - Document-Level (7): document_type, reporting_period, time_granularity,
              company_name, geographic_jurisdiction, data_source_type, version_date
            - Section-Level (5): section_type, metric_category, units, department_scope
            - Table-Specific (3): table_context, table_name, statistical_summary
            - Legacy: source_document
            Example: {'metric_category': 'Revenue', 'section_type': 'Table'}

    Returns:
        List of QueryResult objects sorted by relevance (highest score first)

    Raises:
        QueryError: If search fails or query is invalid

    Strategy:
        - Generate query embedding using same model as documents (Fin-E5)
        - Perform Qdrant query_points() with COSINE similarity
        - Convert results to QueryResult objects
        - Validate metadata (page_number, source_document required for Story 1.8)
        - Target: <5s p50 latency (Week 0 baseline: 0.83s)

    Example:
        >>> results = await search_documents("What is the revenue?", top_k=5)
        >>> len(results)
        5
        >>> results[0].score
        0.87
    """
    logger.info(
        "Searching documents",
        extra={
            "query": query[:100],  # Truncate for logging
            "top_k": top_k,
            "filters": filters,
        },
    )
    start_time = time.time()

    try:
        # Generate query embedding
        query_embedding = await generate_query_embedding(query)

        # Get Qdrant client
        qdrant = get_qdrant_client()

        # Build Qdrant filter (if provided) - Story 2.4 REVISION: 15 Rich Metadata Fields
        qdrant_filter = _build_qdrant_filter(filters)

        # Perform vector search
        search_result = qdrant.query_points(
            collection_name=settings.qdrant_collection_name,
            query=query_embedding,
            using="text-dense",  # Named vector for Story 2.1 hybrid search
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        # Convert to QueryResult objects
        results = _convert_points_to_results(search_result.points)

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            "Search complete",
            extra={
                "results_count": len(results),
                "latency_ms": round(elapsed_ms, 2),
                "top_score": round(results[0].score, 4) if results else None,
            },
        )

        return results

    except QueryError:
        # Re-raise QueryError from generate_query_embedding
        raise
    except Exception as e:
        logger.error(f"Document search failed: {e}", exc_info=True)
        raise QueryError(f"Vector search failed: {e}") from e
