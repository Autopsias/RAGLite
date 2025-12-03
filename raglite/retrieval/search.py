"""Vector similarity search and retrieval for natural language queries.

Performs semantic search using Fin-E5 embeddings and Qdrant vector database.
Supports hybrid search (BM25 + semantic) for improved keyword precision (Story 2.1).
"""

import re
import time
from typing import Any, cast

from raglite.ingestion.entity_normalizer import expand_entity_synonyms
from raglite.retrieval.query_classifier import (
    QueryType,
    classify_query,
    classify_query_metadata,
    expand_metric_synonyms,
    generate_sql_query,
)
from raglite.retrieval.sql_table_search import search_tables_sql
from raglite.shared.bm25 import BM25IndexError, compute_bm25_scores, load_bm25_index
from raglite.shared.clients import get_embedding_model, get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import QueryResult

logger = get_logger(__name__)


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


# Time period patterns for fallback 3 (query reformulation)
TIME_PERIOD_PATTERNS = [
    r"\bin\s+\d{4}\b",  # "in 2024"
    r"\bfor\s+\d{4}\b",  # "for 2024"
    r"\bfor\s+Q[1-4]\b",  # "for Q3"
    r"\bin\s+Q[1-4]\b",  # "in Q1"
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}\b",
    r"\b\d{4}\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b",
    r"\bQ[1-4]\s+\d{4}\b",  # "Q3 2024"
    r"\b\d{4}\s+Q[1-4]\b",  # "2024 Q3"
    r"\blast\s+year\b",  # "last year"
    r"\bthis\s+year\b",  # "this year"
    r"\blast\s+quarter\b",  # "last quarter"
    r"\bthis\s+quarter\b",  # "this quarter"
]


def _remove_time_periods(query: str) -> str:
    """Remove time period references from query for fallback 3.

    Args:
        query: Original query with time references

    Returns:
        Query with time references removed

    Example:
        >>> _remove_time_periods("What is EBITDA for Q3 2024?")
        "What is EBITDA?"
    """
    result = query
    for pattern in TIME_PERIOD_PATTERNS:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)
    # Clean up extra whitespace
    result = re.sub(r"\s+", " ", result).strip()
    # Clean up dangling punctuation
    result = re.sub(r"\s+\?$", "?", result)
    result = re.sub(r"\s+\.$", ".", result)
    return result


async def reformulate_query(
    original_query: str,
    fallback_level: int = 1,
) -> tuple[str, str]:
    """Reformulate query using fallback chain when SQL returns 0 rows.

    Story 5.0.7 Phase 5.3: Implements 3-stage fallback chain for query reformulation.

    Fallback Chain:
        1. Fallback 1: Expand metric synonyms (e.g., "petcoke" -> "Petcoke Consumption")
        2. Fallback 2: Expand entity synonyms (e.g., "PT" -> "Portugal")
        3. Fallback 3: Remove time period filters (e.g., "for Q3 2024" -> "")

    Args:
        original_query: Original query that returned 0 results
        fallback_level: Which fallback to apply (1, 2, or 3)

    Returns:
        Tuple of (reformulated_query, fallback_description)

    Example:
        >>> query, desc = await reformulate_query("What is petcoke for Q3?", 1)
        >>> # query: "What is Petcoke Consumption for Q3?"
        >>> # desc: "metric_synonym_expansion"
    """
    if fallback_level == 1:
        # Fallback 1: Expand metric synonyms
        synonyms = expand_metric_synonyms(original_query)
        if synonyms:
            # Add first synonym to query for broader matching
            expanded = f"{original_query} {' '.join(synonyms[:3])}"
            logger.info(
                "Query reformulation: metric synonym expansion",
                extra={
                    "original": original_query[:50],
                    "synonyms_added": synonyms[:3],
                    "fallback_level": 1,
                },
            )
            return expanded, "metric_synonym_expansion"
        # No synonyms found, return original
        return original_query, "no_metric_synonyms"

    elif fallback_level == 2:
        # Fallback 2: Expand entity synonyms
        entity_synonyms = expand_entity_synonyms(original_query)
        if entity_synonyms:
            # Add entity variations to query
            expanded = f"{original_query} {' '.join(entity_synonyms[:3])}"
            logger.info(
                "Query reformulation: entity synonym expansion",
                extra={
                    "original": original_query[:50],
                    "entities_added": entity_synonyms[:3],
                    "fallback_level": 2,
                },
            )
            return expanded, "entity_synonym_expansion"
        # No entity synonyms found, return original
        return original_query, "no_entity_synonyms"

    elif fallback_level == 3:
        # Fallback 3: Remove time period filters
        stripped = _remove_time_periods(original_query)
        if stripped != original_query:
            logger.info(
                "Query reformulation: time period removal",
                extra={
                    "original": original_query[:50],
                    "stripped": stripped[:50],
                    "fallback_level": 3,
                },
            )
            return stripped, "time_period_removal"
        # No time periods to remove
        return original_query, "no_time_periods"

    # Invalid fallback level
    return original_query, "invalid_fallback_level"


async def search_with_reformulation(
    query: str,
    top_k: int = 5,
    max_fallbacks: int = 3,
) -> tuple[list[QueryResult], str | None]:
    """Execute SQL search with automatic query reformulation fallback chain.

    Story 5.0.7 Phase 5.3: Wraps SQL table search with automatic reformulation
    when initial query returns 0 results.

    Args:
        query: Natural language query
        top_k: Number of results to return
        max_fallbacks: Maximum number of reformulation attempts (default: 3)

    Returns:
        Tuple of (results, successful_reformulation_type)
        - results: List of QueryResult objects
        - successful_reformulation_type: Which fallback succeeded (or None if original worked)

    Example:
        >>> results, reformulation = await search_with_reformulation(
        ...     "What is petcoke consumption for Q3 2024?", top_k=5
        ... )
        >>> if reformulation:
        ...     print(f"Found via: {reformulation}")
    """
    # Try original query first
    sql = await generate_sql_query(query)
    if sql:
        results = await search_tables_sql(sql, top_k=top_k)
        if results:
            logger.info(
                "SQL search succeeded with original query",
                extra={"query": query[:50], "results_count": len(results)},
            )
            return results, None

    # Original query returned 0 results - try reformulation chain
    logger.info(
        "SQL returned 0 results - starting reformulation fallback chain",
        extra={"query": query[:50], "max_fallbacks": max_fallbacks},
    )

    for fallback_level in range(1, max_fallbacks + 1):
        reformulated, fallback_type = await reformulate_query(query, fallback_level)

        # Skip if reformulation didn't change the query
        if reformulated == query or fallback_type.startswith("no_"):
            logger.debug(
                f"Fallback {fallback_level} skipped (no change)",
                extra={"fallback_type": fallback_type},
            )
            continue

        # Try reformulated query
        sql = await generate_sql_query(reformulated)
        if sql:
            results = await search_tables_sql(sql, top_k=top_k)
            if results:
                logger.info(
                    "Query reformulation succeeded",
                    extra={
                        "original_query": query[:50],
                        "reformulated_query": reformulated[:50],
                        "fallback_level": fallback_level,
                        "fallback_type": fallback_type,
                        "results_count": len(results),
                    },
                )
                return results, fallback_type

        logger.debug(
            f"Fallback {fallback_level} did not produce results",
            extra={"fallback_type": fallback_type},
        )

    # All fallbacks exhausted - return empty with helpful message
    logger.warning(
        "All query reformulation fallbacks exhausted",
        extra={"query": query[:50], "fallbacks_tried": max_fallbacks},
    )
    return [], None


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

        # Build Qdrant filter (if provided) - Story 2.4 REVISION: 15 Rich Metadata Fields
        qdrant_filter = None
        if filters:
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
                    conditions.append(
                        FieldCondition(key=field, match=MatchValue(value=filters[field]))
                    )

            if conditions:
                # Cast to list union type for mypy compatibility
                qdrant_filter = Filter(must=conditions)

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


def fuse_sql_vector_results(
    sql_results: list[QueryResult],
    vector_results: list[QueryResult],
    top_k: int = 5,
    sql_weight: float = 0.6,
) -> list[QueryResult]:
    """Fuse SQL and vector search results using Reciprocal Rank Fusion (RRF).

    Story 2.13 AC3 Task 3.2: Combine SQL table search with vector search results
    for HYBRID queries that benefit from both structured and semantic retrieval.

    Uses RRF (k=60) to merge rankings, weighted by sql_weight (default 60% SQL, 40% vector).
    SQL results get higher weight because table queries typically demand exact matches.

    Args:
        sql_results: Results from SQL table search (score=1.0)
        vector_results: Results from semantic search (score=0.0-1.0)
        top_k: Number of results to return
        sql_weight: Weight for SQL ranking (default: 0.6 = 60% SQL, 40% vector)

    Returns:
        Fused results ranked by RRF score

    Example:
        >>> sql_results = await search_tables_sql("SELECT * FROM ...", top_k=20)
        >>> vector_results = await search_documents("EBITDA for Portugal", top_k=20)
        >>> fused = fuse_sql_vector_results(sql_results, vector_results, top_k=5)
    """
    if not sql_results and not vector_results:
        return []
    if not sql_results:
        return vector_results[:top_k]
    if not vector_results:
        return sql_results[:top_k]

    logger.debug(
        "Fusing SQL + Vector results with RRF",
        extra={
            "sql_count": len(sql_results),
            "vector_count": len(vector_results),
            "sql_weight": sql_weight,
            "top_k": top_k,
        },
    )

    # RRF constant (standard value from literature)
    k = 60

    # Build result maps and RRF scores
    rrf_scores: dict[tuple[str, int], float] = {}  # Map: (source_doc, chunk_idx) -> RRF score
    result_map = {}  # Map: (source_doc, chunk_idx) -> QueryResult

    # Add SQL ranking contributions (weighted by sql_weight)
    for sql_rank, result in enumerate(sql_results, 1):
        doc_key = (result.source_document, result.chunk_index)
        rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + sql_weight / (k + sql_rank)
        result_map[doc_key] = result

    # Add vector ranking contributions (weighted by 1-sql_weight)
    for vector_rank, result in enumerate(vector_results, 1):
        doc_key = (result.source_document, result.chunk_index)
        rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + (1 - sql_weight) / (k + vector_rank)
        if doc_key not in result_map:  # SQL takes precedence for result object
            result_map[doc_key] = result

    # Create fused results with RRF scores
    fused_results = []
    for doc_key, rrf_score in rrf_scores.items():
        result = result_map[doc_key]
        clamped_score = min(rrf_score, 1.0)  # Clamp for Pydantic validation
        fused_results.append(
            QueryResult(
                score=clamped_score,
                text=result.text,
                source_document=result.source_document,
                page_number=result.page_number,
                chunk_index=result.chunk_index,
                word_count=result.word_count,
            )
        )

    # Sort by RRF score and return top-k
    fused_results_sorted = sorted(fused_results, key=lambda x: x.score, reverse=True)

    logger.debug(
        "SQL+Vector RRF fusion complete",
        extra={
            "fused_count": len(fused_results_sorted),
            "top_score": round(fused_results_sorted[0].score, 6) if fused_results_sorted else None,
        },
    )

    return fused_results_sorted[:top_k]


def fuse_search_results(
    semantic_results: list[QueryResult],
    bm25_scores: list[float],
    chunk_metadata: list[dict[str, Any]],
    alpha: float = 0.7,
    top_k: int = 5,
    metadata_boost: dict[str, str] | None = None,
) -> list[QueryResult]:
    """Fuse semantic and BM25 search results using Reciprocal Rank Fusion (RRF).

    Story 2.11 FIX: Replaced weighted sum fusion with Reciprocal Rank Fusion (RRF)
    to preserve raw fusion scores and avoid score normalization artifacts.

    RRF Algorithm (Cormack et al.):
        score(doc) = sum over all rankings: 1 / (k + rank(doc))
        where k=60 is the RRF constant (standard value from literature)

    This approach:
    - Preserves realistic score variance (no artificial 1.0 normalization)
    - Handles score ranges naturally without normalization
    - Research-proven for hybrid search (better than weighted sum)
    - Supports optional metadata boosting via score multipliers

    Args:
        semantic_results: Results from semantic search (already sorted by score)
        bm25_scores: BM25 scores for all chunks in corpus (same order as indexed)
        chunk_metadata: Metadata mapping BM25 array positions to (source_document, chunk_index)
        alpha: Fusion weight (default: 0.7 = 70% semantic, 30% BM25)
        top_k: Number of top results to return
        metadata_boost: Optional metadata extracted from query for soft boosting.
                        Format: {'metric_category': 'EBITDA', 'company_name': 'Portugal'}
                        Matching chunks get 1.2x score boost per field match.

    Returns:
        Fused and re-ranked results (top-k by RRF score)

    Example:
        >>> semantic_results = await search_documents("EBITDA margin for Portugal", top_k=20)
        >>> bm25, _, metadata = load_bm25_index()
        >>> bm25_scores = compute_bm25_scores(bm25, "EBITDA margin for Portugal")
        >>> query_metadata = {"metric_category": "EBITDA", "company_name": "Portugal"}
        >>> fused = fuse_search_results(semantic_results, bm25_scores, metadata,
        ...                              alpha=0.7, top_k=5, metadata_boost=query_metadata)
    """
    if not semantic_results:
        logger.warning("No semantic results to fuse")
        return []

    if not bm25_scores or len(bm25_scores) == 0:
        logger.warning("No BM25 scores provided - returning semantic results only")
        return semantic_results[:top_k]

    logger.debug(
        "Fusing search results with RRF",
        extra={
            "semantic_count": len(semantic_results),
            "bm25_scores_count": len(bm25_scores),
            "has_metadata": len(chunk_metadata) > 0,
            "alpha": alpha,
            "top_k": top_k,
        },
    )

    # Build mapping from (source_document, chunk_index) to BM25 array position
    chunk_to_bm25_pos: dict[tuple[str, int], int] = {}
    if chunk_metadata:
        for bm25_pos, metadata in enumerate(chunk_metadata):
            source_doc = metadata.get("source_document", "")
            chunk_idx = metadata.get("chunk_index", 0)
            key = (source_doc, chunk_idx)
            chunk_to_bm25_pos[key] = bm25_pos

    # Create BM25 ranking by sorting scores (descending)
    bm25_ranking = sorted(
        enumerate(bm25_scores), key=lambda x: x[1], reverse=True
    )  # List of (bm25_pos, score) tuples

    # Build rank mappings for RRF
    # Semantic ranking: already sorted by score (rank = index + 1)
    # BM25 ranking: sort by score and assign ranks
    bm25_rank_map: dict[int, int] = {
        bm25_pos: rank + 1 for rank, (bm25_pos, _) in enumerate(bm25_ranking)
    }

    # Reciprocal Rank Fusion (RRF) with k=60 (standard constant)
    k = 60  # RRF constant from Cormack et al.
    rrf_scores: dict[tuple[str, int], float] = {}  # Map: (source_doc, chunk_idx) -> RRF score
    result_map = {}  # Map: (source_doc, chunk_idx) -> QueryResult

    # Add semantic ranking contributions (weighted by alpha)
    for semantic_rank, result in enumerate(semantic_results, 1):
        doc_key = (result.source_document, result.chunk_index)
        # RRF contribution from semantic ranking
        rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + alpha / (k + semantic_rank)
        result_map[doc_key] = result

    # Add BM25 ranking contributions (weighted by 1-alpha)
    for result in semantic_results:
        doc_key = (result.source_document, result.chunk_index)
        bm25_pos_opt = chunk_to_bm25_pos.get(doc_key)

        if bm25_pos_opt is not None and bm25_pos_opt in bm25_rank_map:
            bm25_rank: int = bm25_rank_map[bm25_pos_opt]
            # RRF contribution from BM25 ranking
            rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + (1 - alpha) / (k + bm25_rank)

    # Apply metadata boosting if provided (1.2x multiplier per field match)
    if metadata_boost and chunk_metadata:
        for doc_key, rrf_score in list(rrf_scores.items()):
            bm25_pos_opt = chunk_to_bm25_pos.get(doc_key)
            if bm25_pos_opt is not None and bm25_pos_opt < len(chunk_metadata):
                chunk_meta: dict[str, Any] = chunk_metadata[bm25_pos_opt]
                boost_multiplier = 1.0
                matches = []

                # Check each metadata field for fuzzy matches
                for field, query_value in metadata_boost.items():
                    chunk_value = chunk_meta.get(field)
                    if chunk_value and query_value:
                        query_lower = str(query_value).lower()
                        chunk_lower = str(chunk_value).lower()

                        if query_lower in chunk_lower or chunk_lower in query_lower:
                            boost_multiplier *= 1.2
                            matches.append(field)

                # Apply boost
                if matches:
                    original_score = rrf_score
                    rrf_scores[doc_key] *= boost_multiplier
                    logger.debug(
                        "Metadata boost applied",
                        extra={
                            "chunk": f"{doc_key[0]}:{doc_key[1]}",
                            "matched_fields": matches,
                            "boost_multiplier": round(boost_multiplier, 2),
                            "original_score": round(original_score, 6),
                            "boosted_score": round(rrf_scores[doc_key], 6),
                        },
                    )

    # Story 2.11 FIX: NO score normalization - preserve raw RRF scores
    # RRF scores are naturally small (0.0-0.02 range) and maintain relative ranking
    # This fixes the score=1.0 normalization bug from Story 2.4

    # Create QueryResult objects with RRF scores
    fused_results = []
    for doc_key, rrf_score in rrf_scores.items():
        result = result_map[doc_key]
        # Clamp to [0,1] range for Pydantic validation (RRF scores are typically <<1.0)
        clamped_score = min(rrf_score, 1.0)
        fused_results.append(
            QueryResult(
                score=clamped_score,
                text=result.text,
                source_document=result.source_document,
                page_number=result.page_number,
                chunk_index=result.chunk_index,
                word_count=result.word_count,
            )
        )

    # Sort by RRF score (descending) and return top-k
    fused_results_sorted = sorted(fused_results, key=lambda x: x.score, reverse=True)

    logger.debug(
        "RRF fusion complete",
        extra={
            "fused_count": len(fused_results_sorted),
            "top_score": round(fused_results_sorted[0].score, 6) if fused_results_sorted else None,
            "metadata_boosted": metadata_boost is not None and len(metadata_boost) > 0,
        },
    )

    return fused_results_sorted[:top_k]


async def enrich_results_with_metadata(results: list[QueryResult]) -> list[QueryResult]:
    """Enrich query results with LLM-extracted metadata at query time.

    Story 5.0.6 AC5: Compensates for skipped metadata extraction during ingestion
    by enriching top-k results with rich metadata schema at query time.

    This function enables the performance optimization of skipping metadata extraction
    during ingestion (saving 400+ API calls per document) while maintaining query
    quality through selective enrichment of only the retrieved results.

    Strategy:
    1. Extract metadata from each result's text in parallel (asyncio.gather)
    2. Apply 2.5 second timeout for entire batch (graceful degradation)
    3. If timeout occurs, return results without metadata (no failure)
    4. Attach extracted metadata to QueryResult objects

    Args:
        results: List of QueryResult objects from retrieval (typically top-5)

    Returns:
        Same QueryResult objects with metadata fields populated (or unchanged if timeout)

    Performance:
        - Parallel processing: All results enriched concurrently
        - Timeout: 2.5 seconds total (graceful degradation)
        - Cost: FREE (Mistral Small 3.2)
        - Latency budget: Fits within 5s p50, 15s p95 NFR13 target

    Example:
        >>> results = await hybrid_search("What is the EBITDA?", top_k=5)
        >>> enriched = await enrich_results_with_metadata(results)
        >>> print(enriched[0].text, enriched[0].metadata)
    """
    import asyncio

    from raglite.ingestion.embedding_generation import extract_chunk_metadata
    from raglite.shared.clients import get_mistral_client

    # AC5: Only enrich if enabled in config
    if not settings.query_time_metadata_enabled:
        logger.debug("Query-time metadata enrichment disabled (skip)")
        return results

    # AC5: Graceful degradation if no API key
    if not settings.mistral_api_key:
        logger.debug("Mistral API key not configured - skipping metadata enrichment")
        return results

    if not results:
        return results

    logger.info(
        "Enriching results with metadata at query time",
        extra={"result_count": len(results), "timeout_seconds": 2.5},
    )

    start_time = time.time()

    # Create shared Mistral client for connection pooling
    client = get_mistral_client()

    # AC5: Extract metadata for all results in parallel with timeout
    async def enrich_single_result(result: QueryResult, index: int) -> QueryResult:
        """Extract metadata for a single result with error handling."""
        try:
            # Extract metadata using existing function (reuses 15-field rich schema)
            chunk_id = f"query_result_{index}"
            metadata = await extract_chunk_metadata(result.text, chunk_id, client)

            # Story 5.0.6 AC5: Attach extracted metadata to QueryResult
            result.metadata = metadata

            logger.debug(
                "Metadata extracted and attached for result",
                extra={
                    "index": index,
                    "company_name": metadata.company_name,
                    "reporting_period": metadata.reporting_period,
                    "metric_category": metadata.metric_category,
                },
            )

            return result

        except Exception as e:
            logger.warning(
                "Metadata extraction failed for result (graceful degradation)",
                extra={"index": index, "error": str(e)},
            )
            return result

    try:
        # AC5: Parallel enrichment with 2.5s timeout
        enrichment_tasks = [enrich_single_result(r, i) for i, r in enumerate(results)]
        enriched_results = await asyncio.wait_for(
            asyncio.gather(*enrichment_tasks, return_exceptions=True), timeout=2.5
        )

        # Filter out exceptions from gather
        final_results: list[QueryResult] = []
        for i, result in enumerate(enriched_results):
            if isinstance(result, Exception):
                logger.warning(f"Enrichment task failed: {result}")
                # Use original result (not the exception)
                final_results.append(results[i])
            else:
                # Type narrowing: result is QueryResult here
                final_results.append(cast(QueryResult, result))

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            "Query-time metadata enrichment complete",
            extra={
                "result_count": len(final_results),
                "latency_ms": round(elapsed_ms, 1),
                "within_budget": elapsed_ms < 2500,
            },
        )

        return final_results

    except TimeoutError:
        # AC5: Graceful degradation - return results without metadata
        elapsed_ms = (time.time() - start_time) * 1000
        logger.warning(
            "Query-time metadata enrichment timed out (graceful degradation)",
            extra={"timeout_ms": 2500, "elapsed_ms": round(elapsed_ms, 1)},
        )
        return results


async def hybrid_search(
    query: str,
    top_k: int = 5,
    alpha: float = 0.7,
    filters: dict[str, str] | None = None,
    enable_hybrid: bool = True,
    auto_classify: bool = False,
    enable_sql_tables: bool = True,
) -> list[QueryResult]:
    """Perform hybrid search combining semantic (Fin-E5) and keyword (BM25) matching.

    Story 2.13 AC3: SQL Table Search Integration - Adds intelligent query routing
    to SQL table search for structured financial queries (70-80% accuracy).

    Story 2.11 AC3: Auto-classification DISABLED by default (70.2% accuracy < 80% threshold).
    Analysis showed incorrect metadata extractions harm retrieval more than they help.

    Story 2.4 Enhancement: Now supports automatic query metadata classification for
    intelligent filter extraction from natural language queries.

    Improves retrieval precision for financial queries containing specific terms
    (e.g., "EBITDA") and numbers (e.g., "23.2 EUR/ton") by combining semantic
    understanding with exact keyword matching and metadata-aware filtering.

    Args:
        query: Natural language query
        top_k: Number of results to return (default: 5)
        alpha: Fusion weight - 0.7 = 70% semantic, 30% BM25 (default: 0.7)
        filters: Optional metadata filters (e.g., {'source_document': 'Q3_Report.pdf'})
                 If provided, disables auto_classify
        enable_hybrid: If False, falls back to semantic-only search (default: True)
        auto_classify: If True and filters=None, automatically extract metadata filters
                       from query using LLM classification (default: True)
        enable_sql_tables: If True, enables SQL table search routing for structured
                           queries (default: True). Classified as SQL_ONLY/VECTOR_ONLY/HYBRID.

    Returns:
        List of QueryResult objects ranked by hybrid score (highest first)

    Raises:
        QueryError: If search fails or query is invalid

    Strategy:
        - If auto_classify enabled and no filters: Extract metadata filters from query
        - Retrieve top-20 semantic results with filters (cast wider net for fusion)
        - Load BM25 index and compute BM25 scores for query
        - Fuse semantic + BM25 using weighted sum (alpha=0.7)
        - Return top-k hybrid-ranked results
        - Fallback to semantic-only if BM25 index unavailable

    Example:
        >>> # Automatic metadata filtering
        >>> results = await hybrid_search("What is the EBITDA margin for Portugal?", top_k=5)
        >>> # Filters extracted: {'metric_category': 'EBITDA', 'company_name': 'Portugal Cement'}

        >>> # Explicit filters (disables auto_classify)
        >>> results = await hybrid_search(
        ...     "What is the margin?",
        ...     filters={'metric_category': 'EBITDA'},
        ...     top_k=5
        ... )
    """
    logger.info(
        "Hybrid search started",
        extra={
            "query": query[:100],
            "top_k": top_k,
            "alpha": alpha,
            "enable_hybrid": enable_hybrid,
            "auto_classify": auto_classify,
            "filters_provided": filters is not None,
            "enable_sql_tables": enable_sql_tables,
        },
    )
    start_time = time.time()

    # Story 2.13 AC3: SQL Table Search Routing
    # Initialize SQL results for potential HYBRID fusion
    sql_results: list[QueryResult] = []

    # Classify query and route to appropriate search backend(s)
    if enable_sql_tables:
        query_type = classify_query(query)
        logger.info(
            "Query classified for SQL routing",
            extra={"query_type": query_type.value, "query": query[:100]},
        )

        # SQL_ONLY queries: Route to SQL-only search with reformulation fallback
        if query_type == QueryType.SQL_ONLY:
            logger.info("Routing to SQL-only search (structured table query)")
            try:
                # Story 5.0.7 Phase 5.3: Use reformulation fallback chain
                sql_results, reformulation_type = await search_with_reformulation(
                    query, top_k=top_k, max_fallbacks=3
                )

                if sql_results:
                    elapsed_ms = (time.time() - start_time) * 1000
                    logger.info(
                        "SQL-only search complete",
                        extra={
                            "results_count": len(sql_results),
                            "latency_ms": round(elapsed_ms, 2),
                            "reformulation_type": reformulation_type,
                        },
                    )
                    # Story 5.0.6 AC5: Enrich results with metadata at query time
                    sql_results = await enrich_results_with_metadata(sql_results)
                    return sql_results
                else:
                    logger.warning(
                        "SQL search returned 0 results after reformulation - falling back to vector search"
                    )
            except Exception as e:
                logger.error(
                    "SQL search failed - falling back to vector search",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                # Fall through to vector search

        # HYBRID queries: Combine SQL + Vector results
        elif query_type == QueryType.HYBRID:
            logger.info("Routing to HYBRID search (SQL + Vector fusion)")
            try:
                # Generate and execute SQL query
                sql = await generate_sql_query(query)
                sql_results = []
                if sql:
                    sql_results = await search_tables_sql(sql, top_k=top_k * 2)
                    logger.info(
                        "SQL component complete",
                        extra={
                            "sql_results": len(sql_results),
                            "sql_preview": sql[:100],
                        },
                    )
                else:
                    logger.warning("SQL generation returned None - using vector-only")

                # Continue with vector search below (will be fused with SQL results)
                # Store sql_results for fusion after vector search completes
                # We'll handle fusion in Task 3.2

            except Exception as e:
                logger.error(
                    "SQL component failed in hybrid search",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                sql_results = []
                # Fall through to vector search

        # VECTOR_ONLY queries: Use vector+BM25 only (no SQL routing)
        else:  # QueryType.VECTOR_ONLY
            logger.info("Routing to vector-only search (text/semantic query)")
            # Fall through to existing vector+BM25 logic below

    # Story 2.4 Enhancement: Automatic query metadata classification for SOFT BOOSTING
    # Extract metadata from query but DON'T filter - use for score boosting instead
    extracted_metadata = {}
    if auto_classify and filters is None:
        logger.info("Auto-classifying query for metadata boosting (soft filtering)")
        extracted_metadata = await classify_query_metadata(query)
        if extracted_metadata:
            logger.info(
                "Metadata extracted for score boosting",
                extra={
                    "extracted_metadata": extracted_metadata,
                    "field_count": len(extracted_metadata),
                },
            )
        else:
            logger.info("No metadata extracted - using semantic/BM25 only")

    # Fallback to semantic-only if hybrid disabled
    if not enable_hybrid:
        logger.info("Hybrid search disabled - using semantic-only")
        return await search_documents(query, top_k=top_k, filters=filters)

    try:
        # Step 1: Retrieve semantic results WITHOUT hard filtering (for soft boosting)
        # Optimized: Cast moderate net for better performance
        semantic_top_k = max(top_k * 2, 10)  # Moderate net (minimum 10, not 20)
        # NOTE: Explicitly pass filters=None for soft boosting approach (no hard filtering)
        semantic_results = await search_documents(query, top_k=semantic_top_k, filters=filters)

        if not semantic_results:
            logger.warning("No semantic results found")
            return []

        # Step 2: Fusion logic - SQL+Vector for HYBRID queries, BM25+Vector for TEXT queries
        # Story 2.13 AC3 Task 3.2: Check if we have SQL results from HYBRID routing
        if sql_results:
            # HYBRID query: Fuse SQL + Vector results
            logger.info("Fusing SQL + Vector results for HYBRID query")
            hybrid_results = fuse_sql_vector_results(
                sql_results,
                semantic_results,
                top_k=top_k,
                sql_weight=0.6,  # 60% SQL, 40% vector
            )

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                "HYBRID search complete (SQL+Vector)",
                extra={
                    "results_count": len(hybrid_results),
                    "latency_ms": round(elapsed_ms, 2),
                    "top_score": round(hybrid_results[0].score, 4) if hybrid_results else None,
                    "sql_count": len(sql_results),
                    "vector_count": len(semantic_results),
                },
            )

            return hybrid_results

        # TEXT query: Load BM25 index and compute scores
        try:
            bm25, _, chunk_metadata = load_bm25_index()
            bm25_scores = compute_bm25_scores(bm25, query)

            # Step 3: Fuse results with metadata boosting (if metadata extracted)
            hybrid_results = fuse_search_results(
                semantic_results,
                bm25_scores,
                chunk_metadata,
                alpha=alpha,
                top_k=top_k,
                metadata_boost=extracted_metadata if extracted_metadata else None,
            )

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                "Hybrid search complete (BM25+Vector)",
                extra={
                    "results_count": len(hybrid_results),
                    "latency_ms": round(elapsed_ms, 2),
                    "top_score": round(hybrid_results[0].score, 4) if hybrid_results else None,
                    "semantic_count": len(semantic_results),
                    "fusion_alpha": alpha,
                    "metadata_boosted": (
                        len(extracted_metadata) > 0 if extracted_metadata else False
                    ),
                },
            )

            # Story 5.0.6 AC5: Enrich results with metadata at query time
            hybrid_results = await enrich_results_with_metadata(hybrid_results)
            return hybrid_results

        except (BM25IndexError, FileNotFoundError) as e:
            # Fallback to semantic-only if BM25 index unavailable
            logger.warning(
                "BM25 index unavailable - falling back to semantic-only search",
                extra={"error": str(e)},
            )
            # Story 5.0.6 AC5: Enrich results with metadata at query time
            fallback_results = semantic_results[:top_k]
            fallback_results = await enrich_results_with_metadata(fallback_results)
            return fallback_results

    except QueryError:
        # Re-raise QueryError from search_documents
        raise
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}", exc_info=True)
        raise QueryError(f"Hybrid search failed: {e}") from e
