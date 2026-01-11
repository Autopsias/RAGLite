"""Search result fusion and ranking utilities.

Extracted from multi_index_search.py to reduce file size.
Handles the weighted fusion of vector and SQL search results.
"""

import logging
from dataclasses import dataclass
from typing import Any


@dataclass
class SearchResult:
    """Search result from multi-index retrieval.

    Unified result format for both vector (Qdrant) and SQL (PostgreSQL) sources.
    Different from raglite.shared.models.SearchResult (which wraps Chunk objects).

    Attributes:
        text: Result text content
        score: Relevance score (0-1, higher is better)
        source: Origin index ("vector" | "sql")
        metadata: Additional metadata (document_id, page_number, etc.)
        document_id: Source document identifier
        page_number: Page number (None if not applicable)
    """

    text: str
    score: float
    source: str  # "vector" | "sql"
    metadata: dict[str, Any]
    document_id: str
    page_number: int | None = None


logger = logging.getLogger(__name__)


def _find_max_scores(
    vector_results: list[SearchResult], sql_results: list[SearchResult]
) -> tuple[float, float]:
    """Find maximum scores for normalization.

    Args:
        vector_results: Results from vector search
        sql_results: Results from SQL search

    Returns:
        Tuple of (max_vector_score, max_sql_score)
    """
    max_vector_score = max((r.score for r in vector_results), default=0.001)
    max_sql_score = max((r.score for r in sql_results), default=1.0)
    return max_vector_score, max_sql_score


def _create_normalized_result(result: SearchResult, normalized_score: float) -> SearchResult:
    """Create a SearchResult with normalized score.

    Args:
        result: Original search result
        normalized_score: Normalized score value

    Returns:
        New SearchResult with normalized score
    """
    return SearchResult(
        text=result.text,
        score=normalized_score,
        source=result.source,
        metadata=result.metadata,
        document_id=result.document_id,
        page_number=result.page_number,
    )


def _process_vector_results(
    vector_results: list[SearchResult], max_vector_score: float
) -> dict[str, SearchResult]:
    """Process vector results with score normalization.

    Args:
        vector_results: Results from vector search
        max_vector_score: Maximum score for normalization

    Returns:
        Dictionary mapping result keys to normalized results
    """
    result_map: dict[str, SearchResult] = {}

    for result in vector_results:
        key = f"{result.document_id}:{result.page_number}"
        normalized_score = result.score / max_vector_score if max_vector_score > 0 else 0

        if key not in result_map or normalized_score > result_map[key].score:
            result_map[key] = _create_normalized_result(result, normalized_score)

    return result_map


def _process_sql_results(
    sql_results: list[SearchResult],
    max_sql_score: float,
    result_map: dict[str, SearchResult],
    alpha: float,
) -> dict[str, SearchResult]:
    """Process SQL results with normalization and fusion.

    Args:
        sql_results: Results from SQL search
        max_sql_score: Maximum score for normalization
        result_map: Existing result map from vector processing
        alpha: Fusion weight for vector results

    Returns:
        Updated result map with SQL results fused
    """
    for result in sql_results:
        key = f"{result.document_id}:{result.page_number}"
        normalized_score = result.score / max_sql_score if max_sql_score > 0 else 0

        if key not in result_map:
            result_map[key] = _create_normalized_result(result, normalized_score)
        else:
            existing = result_map[key]
            if existing.source == "vector" or existing.source == "hybrid":
                fused_score = alpha * existing.score + (1 - alpha) * normalized_score
                result_map[key] = SearchResult(
                    text=existing.text,
                    score=fused_score,
                    source="hybrid",
                    metadata={**existing.metadata, **result.metadata},
                    document_id=existing.document_id,
                    page_number=existing.page_number,
                )
                logger.debug(
                    "Deduplicated and fused",
                    extra={
                        "key": key,
                        "vector_score_normalized": round(existing.score, 4),
                        "sql_score_normalized": round(normalized_score, 4),
                        "fused_score": round(fused_score, 4),
                        "alpha": alpha,
                    },
                )

    return result_map


def merge_results(
    vector_results: list[SearchResult],
    sql_results: list[SearchResult],
    alpha: float = 0.6,
    top_k: int = 5,
) -> list[SearchResult]:
    """Fuse vector and SQL search results using weighted sum with score normalization.

    Story 2.11 AC1 FIX: Fixed score range mismatch bug where RRF scores (0.001-0.03)
    were fused with SQL scores (1.0) without normalization, causing SQL presence to
    dominate ranking regardless of alpha value. Now normalizes both score ranges
    before weighted fusion.

    Fusion Algorithm:
      1. Find max scores from each index
      2. Normalize scores from both indexes to [0,1] range using max-score normalization
      3. Apply weighted sum: final_score = alpha * vector_score + (1 - alpha) * sql_score
      4. Deduplicate: If same document appears in both, use fused score
      5. Re-rank by final_score and return top_k

    Args:
        vector_results: Results from vector search (RRF scores: 0.001-0.03 typical)
        sql_results: Results from SQL search (scores: typically 1.0)
        alpha: Fusion weight (default: 0.6 = 60% vector, 40% SQL)
        top_k: Number of top results to return

    Returns:
        Fused and re-ranked results (top-k by hybrid score)

    Example:
        >>> fused = merge_results(vector_results, sql_results, alpha=0.6, top_k=5)
    """
    if not vector_results and not sql_results:
        logger.warning("No results to fuse from either index")
        return []

    if not sql_results:
        logger.info("SQL results empty, returning vector results only")
        return vector_results[:top_k]

    if not vector_results:
        logger.info("Vector results empty, returning SQL results only")
        return sql_results[:top_k]

    logger.debug(
        "Fusing results with score normalization",
        extra={
            "vector_count": len(vector_results),
            "sql_count": len(sql_results),
            "alpha": alpha,
        },
    )

    # Normalize scores from both indexes before fusion
    max_vector_score, max_sql_score = _find_max_scores(vector_results, sql_results)

    # Process vector results
    result_map = _process_vector_results(vector_results, max_vector_score)

    # Process SQL results and fuse
    result_map = _process_sql_results(sql_results, max_sql_score, result_map, alpha)

    # Re-rank by score and return top-k
    sorted_results = sorted(result_map.values(), key=lambda x: x.score, reverse=True)

    logger.debug(
        "Fusion complete with normalization",
        extra={
            "fused_count": len(sorted_results),
            "top_score": round(sorted_results[0].score, 4) if sorted_results else None,
            "max_vector_score_before_norm": round(max_vector_score, 6),
            "max_sql_score_before_norm": round(max_sql_score, 4),
        },
    )

    return sorted_results[:top_k]
