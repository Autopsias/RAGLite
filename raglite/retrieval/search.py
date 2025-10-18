"""Vector similarity search and retrieval for natural language queries.

Performs semantic search using Fin-E5 embeddings and Qdrant vector database.
Supports hybrid search (BM25 + semantic) for improved keyword precision (Story 2.1).
"""

import time
from typing import Any

from raglite.shared.bm25 import BM25IndexError, compute_bm25_scores, load_bm25_index
from raglite.shared.clients import get_embedding_model, get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import QueryResult

logger = get_logger(__name__)


class QueryError(Exception):
    """Exception raised when vector search query fails."""

    pass


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


async def search_documents(
    query: str, top_k: int = 5, filters: dict[str, str] | None = None
) -> list[QueryResult]:
    """Search documents using vector similarity.

    Args:
        query: Natural language query
        top_k: Number of results to return (default: 5)
        filters: Optional metadata filters (e.g., {'source_document': 'Q3_Report.pdf'})

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
    from qdrant_client.models import FieldCondition, Filter, MatchValue

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

        # Build Qdrant filter (if provided)
        qdrant_filter = None
        if filters and "source_document" in filters:
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="source_document", match=MatchValue(value=filters["source_document"])
                    )
                ]
            )

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
        results = []
        for point in search_result.points:
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


def fuse_search_results(
    semantic_results: list[QueryResult],
    bm25_scores: list[float],
    chunk_metadata: list[dict[str, Any]],
    alpha: float = 0.7,
    top_k: int = 5,
) -> list[QueryResult]:
    """Fuse semantic and BM25 search results using weighted sum.

    Combines semantic similarity scores with BM25 keyword matching scores to
    improve retrieval precision for financial queries with specific terms/numbers.

    Args:
        semantic_results: Results from semantic search (already sorted by score)
        bm25_scores: BM25 scores for all chunks in corpus (same order as indexed)
        chunk_metadata: Metadata mapping BM25 array positions to (source_document, chunk_index)
        alpha: Fusion weight (default: 0.7 = 70% semantic, 30% BM25)
        top_k: Number of top results to return

    Returns:
        Fused and re-ranked results (top-k by hybrid score)

    Strategy:
        - Build mapping from (source_document, chunk_index) to BM25 array position
        - Normalize semantic scores (already in [0, 1] from COSINE distance)
        - Normalize BM25 scores to [0, 1] (divide by max score)
        - For each semantic result, find matching BM25 score using metadata mapping
        - Combine: hybrid_score = alpha * semantic + (1 - alpha) * bm25
        - Re-rank by hybrid score and return top-k

    Example:
        >>> semantic_results = await search_documents("EBITDA margin", top_k=20)
        >>> bm25, _, metadata = load_bm25_index()
        >>> bm25_scores = compute_bm25_scores(bm25, "EBITDA margin")
        >>> fused = fuse_search_results(semantic_results, bm25_scores, metadata, alpha=0.7, top_k=5)
    """
    if not semantic_results:
        logger.warning("No semantic results to fuse")
        return []

    if not bm25_scores or len(bm25_scores) == 0:
        logger.warning("No BM25 scores provided - returning semantic results only")
        return semantic_results[:top_k]

    logger.debug(
        "Fusing search results",
        extra={
            "semantic_count": len(semantic_results),
            "bm25_scores_count": len(bm25_scores),
            "has_metadata": len(chunk_metadata) > 0,
            "alpha": alpha,
            "top_k": top_k,
        },
    )

    # Build mapping from (source_document, chunk_index) to BM25 array position
    # This handles the case where Qdrant chunk_index values are per-document
    chunk_to_bm25_pos = {}
    if chunk_metadata:
        for bm25_pos, metadata in enumerate(chunk_metadata):
            source_doc = metadata.get("source_document", "")
            chunk_idx = metadata.get("chunk_index", 0)
            key = (source_doc, chunk_idx)
            chunk_to_bm25_pos[key] = bm25_pos

    # Normalize BM25 scores to [0, 1]
    bm25_max = max(bm25_scores) if bm25_scores else 1.0
    bm25_normalized = [score / bm25_max if bm25_max > 0 else 0 for score in bm25_scores]

    # Map semantic results to their chunk indices and compute hybrid scores
    fused_results = []
    for result in semantic_results:
        # Find BM25 score for this chunk using metadata mapping
        lookup_key = (result.source_document, result.chunk_index)
        chunk_bm25_pos = chunk_to_bm25_pos.get(lookup_key)

        if chunk_bm25_pos is None or chunk_bm25_pos >= len(bm25_normalized):
            # No BM25 score available for this chunk - use semantic only
            logger.debug(
                f"No BM25 mapping for {result.source_document} chunk {result.chunk_index}, using semantic only",
                extra={
                    "source_document": result.source_document,
                    "chunk_index": result.chunk_index,
                },
            )
            hybrid_score = result.score
        else:
            # Semantic scores from Qdrant COSINE are already in [0, 1] range
            semantic_score = result.score
            bm25_score = bm25_normalized[chunk_bm25_pos]

            # Weighted fusion: alpha * semantic + (1 - alpha) * bm25
            hybrid_score = alpha * semantic_score + (1 - alpha) * bm25_score

        # Create new QueryResult with hybrid score
        fused_result = QueryResult(
            score=hybrid_score,
            text=result.text,
            source_document=result.source_document,
            page_number=result.page_number,
            chunk_index=result.chunk_index,
            word_count=result.word_count,
        )
        fused_results.append(fused_result)

    # Sort by hybrid score (descending) and return top-k
    fused_results_sorted = sorted(fused_results, key=lambda x: x.score, reverse=True)

    logger.debug(
        "Fusion complete",
        extra={
            "fused_count": len(fused_results_sorted),
            "top_score": round(fused_results_sorted[0].score, 4) if fused_results_sorted else None,
        },
    )

    return fused_results_sorted[:top_k]


async def hybrid_search(
    query: str,
    top_k: int = 5,
    alpha: float = 0.7,
    filters: dict[str, str] | None = None,
    enable_hybrid: bool = True,
) -> list[QueryResult]:
    """Perform hybrid search combining semantic (Fin-E5) and keyword (BM25) matching.

    Improves retrieval precision for financial queries containing specific terms
    (e.g., "EBITDA") and numbers (e.g., "23.2 EUR/ton") by combining semantic
    understanding with exact keyword matching.

    Args:
        query: Natural language query
        top_k: Number of results to return (default: 5)
        alpha: Fusion weight - 0.7 = 70% semantic, 30% BM25 (default: 0.7)
        filters: Optional metadata filters (e.g., {'source_document': 'Q3_Report.pdf'})
        enable_hybrid: If False, falls back to semantic-only search (default: True)

    Returns:
        List of QueryResult objects ranked by hybrid score (highest first)

    Raises:
        QueryError: If search fails or query is invalid

    Strategy:
        - Retrieve top-20 semantic results (cast wider net for fusion)
        - Load BM25 index and compute BM25 scores for query
        - Fuse semantic + BM25 using weighted sum (alpha=0.7)
        - Return top-k hybrid-ranked results
        - Fallback to semantic-only if BM25 index unavailable

    Example:
        >>> results = await hybrid_search("What is the EBITDA margin?", top_k=5)
        >>> results[0].score  # Hybrid score (semantic + BM25)
        0.89
    """
    logger.info(
        "Hybrid search started",
        extra={
            "query": query[:100],
            "top_k": top_k,
            "alpha": alpha,
            "enable_hybrid": enable_hybrid,
        },
    )
    start_time = time.time()

    # Fallback to semantic-only if hybrid disabled
    if not enable_hybrid:
        logger.info("Hybrid search disabled - using semantic-only")
        return await search_documents(query, top_k=top_k, filters=filters)

    try:
        # Step 1: Retrieve semantic results (top-20 for better fusion coverage)
        semantic_top_k = max(top_k * 4, 20)  # Cast wider net (minimum 20)
        semantic_results = await search_documents(query, top_k=semantic_top_k, filters=filters)

        if not semantic_results:
            logger.warning("No semantic results found")
            return []

        # Step 2: Load BM25 index and compute scores
        try:
            bm25, _, chunk_metadata = load_bm25_index()
            bm25_scores = compute_bm25_scores(bm25, query)

            # Step 3: Fuse results (pass chunk_metadata for proper mapping)
            hybrid_results = fuse_search_results(
                semantic_results, bm25_scores, chunk_metadata, alpha=alpha, top_k=top_k
            )

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                "Hybrid search complete",
                extra={
                    "results_count": len(hybrid_results),
                    "latency_ms": round(elapsed_ms, 2),
                    "top_score": round(hybrid_results[0].score, 4) if hybrid_results else None,
                    "semantic_count": len(semantic_results),
                    "fusion_alpha": alpha,
                },
            )

            return hybrid_results

        except (BM25IndexError, FileNotFoundError) as e:
            # Fallback to semantic-only if BM25 index unavailable
            logger.warning(
                "BM25 index unavailable - falling back to semantic-only search",
                extra={"error": str(e)},
            )
            return semantic_results[:top_k]

    except QueryError:
        # Re-raise QueryError from search_documents
        raise
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}", exc_info=True)
        raise QueryError(f"Hybrid search failed: {e}") from e
