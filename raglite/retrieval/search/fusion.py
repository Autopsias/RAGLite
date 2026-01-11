"""Result fusion algorithms for RAGLite.

Provides Reciprocal Rank Fusion (RRF) for combining results from
SQL+vector and BM25+vector search strategies.
"""

from typing import Any

from raglite.shared.logging import get_logger
from raglite.shared.models import QueryResult

logger = get_logger(__name__)


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


def _build_bm25_position_map(
    chunk_metadata: list[dict[str, Any]],
) -> dict[tuple[str, int], int]:
    """Build mapping from (source_document, chunk_index) to BM25 array position.

    Args:
        chunk_metadata: Metadata mapping BM25 positions to chunks

    Returns:
        Dictionary mapping (source_doc, chunk_idx) to BM25 position
    """
    chunk_to_bm25_pos: dict[tuple[str, int], int] = {}
    for bm25_pos, metadata in enumerate(chunk_metadata):
        source_doc = metadata.get("source_document", "")
        chunk_idx = metadata.get("chunk_index", 0)
        key = (source_doc, chunk_idx)
        chunk_to_bm25_pos[key] = bm25_pos
    return chunk_to_bm25_pos


def _create_bm25_rank_map(bm25_scores: list[float]) -> dict[int, int]:
    """Create rank mapping for BM25 scores.

    Args:
        bm25_scores: BM25 scores for all chunks in corpus

    Returns:
        Dictionary mapping BM25 position to rank (1-indexed)
    """
    bm25_ranking = sorted(enumerate(bm25_scores), key=lambda x: x[1], reverse=True)
    return {bm25_pos: rank + 1 for rank, (bm25_pos, _) in enumerate(bm25_ranking)}


def _calculate_rrf_scores(
    semantic_results: list[QueryResult],
    chunk_to_bm25_pos: dict[tuple[str, int], int],
    bm25_rank_map: dict[int, int],
    alpha: float,
    k: int = 60,
) -> tuple[dict[tuple[str, int], float], dict[tuple[str, int], QueryResult]]:
    """Calculate Reciprocal Rank Fusion scores for semantic and BM25 results.

    Args:
        semantic_results: Results from semantic search (already sorted)
        chunk_to_bm25_pos: Mapping from chunk key to BM25 position
        bm25_rank_map: Mapping from BM25 position to rank
        alpha: Fusion weight (0.7 = 70% semantic, 30% BM25)
        k: RRF constant (default: 60)

    Returns:
        Tuple of (rrf_scores dict, result_map dict)
    """
    rrf_scores: dict[tuple[str, int], float] = {}
    result_map: dict[tuple[str, int], QueryResult] = {}

    # Add semantic ranking contributions (weighted by alpha)
    for semantic_rank, result in enumerate(semantic_results, 1):
        doc_key = (result.source_document, result.chunk_index)
        rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + alpha / (k + semantic_rank)
        result_map[doc_key] = result

    # Add BM25 ranking contributions (weighted by 1-alpha)
    for result in semantic_results:
        doc_key = (result.source_document, result.chunk_index)
        bm25_pos_opt = chunk_to_bm25_pos.get(doc_key)

        if bm25_pos_opt is not None and bm25_pos_opt in bm25_rank_map:
            bm25_rank: int = bm25_rank_map[bm25_pos_opt]
            rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + (1 - alpha) / (k + bm25_rank)

    return rrf_scores, result_map


def _apply_metadata_boosting(
    rrf_scores: dict[tuple[str, int], float],
    metadata_boost: dict[str, str],
    chunk_metadata: list[dict[str, Any]],
    chunk_to_bm25_pos: dict[tuple[str, int], int],
) -> None:
    """Apply metadata boosting to RRF scores (modifies rrf_scores in-place).

    Args:
        rrf_scores: RRF scores to boost (modified in-place)
        metadata_boost: Query metadata for soft boosting
        chunk_metadata: Chunk metadata to match against
        chunk_to_bm25_pos: Mapping from chunk key to BM25 position
    """
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


def _create_fused_results(
    rrf_scores: dict[tuple[str, int], float],
    result_map: dict[tuple[str, int], QueryResult],
) -> list[QueryResult]:
    """Create QueryResult objects from RRF scores.

    Args:
        rrf_scores: RRF scores for each chunk
        result_map: Mapping from chunk key to QueryResult

    Returns:
        List of QueryResult objects with RRF scores
    """
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
    return fused_results


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
    chunk_to_bm25_pos = _build_bm25_position_map(chunk_metadata) if chunk_metadata else {}

    # Create BM25 ranking by sorting scores (descending)
    bm25_rank_map = _create_bm25_rank_map(bm25_scores)

    # Reciprocal Rank Fusion (RRF) with k=60 (standard constant)
    k = 60  # RRF constant from Cormack et al.
    rrf_scores, result_map = _calculate_rrf_scores(
        semantic_results, chunk_to_bm25_pos, bm25_rank_map, alpha, k
    )

    # Apply metadata boosting if provided (1.2x multiplier per field match)
    if metadata_boost and chunk_metadata:
        _apply_metadata_boosting(rrf_scores, metadata_boost, chunk_metadata, chunk_to_bm25_pos)

    # Story 2.11 FIX: NO score normalization - preserve raw RRF scores
    # RRF scores are naturally small (0.0-0.02 range) and maintain relative ranking
    # This fixes the score=1.0 normalization bug from Story 2.4

    # Create QueryResult objects with RRF scores
    fused_results = _create_fused_results(rrf_scores, result_map)

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
