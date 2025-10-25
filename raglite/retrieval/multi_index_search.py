"""Multi-index search orchestration for hybrid vector + SQL retrieval.

Story 2.7 AC2-AC3: Implements query routing, parallel execution, and result fusion
for combining Qdrant vector search with PostgreSQL table search.

Architecture Pattern (FinSage):
  - Heuristic-based query classification (no LLM overhead)
  - Parallel index execution for hybrid queries
  - Weighted fusion of results

Expected accuracy improvement: +8-12pp over vector-only baseline.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from raglite.retrieval.query_classifier import QueryType, classify_query
from raglite.retrieval.query_preprocessing import preprocess_query_for_table_search
from raglite.retrieval.search import hybrid_search
from raglite.structured.table_retrieval import (
    TableRetrievalError,
    search_tables,
    search_tables_with_metadata_filter,
)

logger = logging.getLogger(__name__)


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


class MultiIndexSearchError(Exception):
    """Exception raised when multi-index search fails."""

    pass


async def multi_index_search(query: str, top_k: int = 5) -> list[SearchResult]:
    """Multi-index search combining vector (Qdrant) and SQL (PostgreSQL) retrieval.

    Story 2.7 AC2: Orchestrates query classification, index routing, and parallel
    execution for hybrid queries.

    Query Routing Logic:
      - SQL_ONLY: PostgreSQL table search only
      - VECTOR_ONLY: Qdrant semantic search only
      - HYBRID: Both indexes in parallel with result fusion

    Error Handling (AC6):
      - PostgreSQL unavailable → Fallback to vector-only
      - Qdrant unavailable → Fallback to SQL (if applicable) or error
      - Classification failure → Default to vector-only
      - Fusion timeout → Return partial results

    Args:
        query: Natural language query
        top_k: Number of results to return (default: 5)

    Returns:
        List of SearchResult objects ranked by relevance

    Raises:
        MultiIndexSearchError: If both indexes fail or query is invalid

    Example:
        >>> results = await multi_index_search("What is the revenue in Q3?", top_k=5)
        >>> for r in results:
        ...     print(f"[{r.source}] {r.score:.2f}: {r.text[:100]}")
    """
    if not query or not query.strip():
        raise MultiIndexSearchError("Query cannot be empty")

    logger.info("Multi-index search started", extra={"query": query[:100], "top_k": top_k})
    start_time = time.time()

    try:
        # Step 1: Classify query type (AC1)
        query_type = classify_query(query)

        # NEW (Story 2.10 AC3): Log routing decision with metrics
        logger.info(
            "Query routing decision",
            extra={
                "query": query[:100],
                "query_type": query_type.value,
                "top_k": top_k,
            },
        )

        # Step 2: Route to appropriate index(es) (AC2)
        if query_type == QueryType.SQL_ONLY:
            # SQL-only: PostgreSQL table search
            results = await _execute_sql_search(query, top_k)

        elif query_type == QueryType.VECTOR_ONLY:
            # Vector-only: Qdrant semantic search
            results = await _execute_vector_search(query, top_k)

        elif query_type == QueryType.HYBRID:
            # Hybrid: Both indexes in parallel (AC2)
            results = await _execute_hybrid_search(query, top_k)

        else:
            # Fallback to vector search (safe default)
            logger.warning(f"Unknown query type {query_type}, defaulting to vector search")
            results = await _execute_vector_search(query, top_k)

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            "Multi-index search complete",
            extra={
                "query_type": query_type.value,
                "results_count": len(results),
                "latency_ms": round(elapsed_ms, 2),
                "top_score": round(results[0].score, 4) if results else None,
            },
        )

        return results

    except MultiIndexSearchError:
        # Re-raise our own exceptions
        raise

    except Exception as e:
        logger.error(
            "Multi-index search failed",
            extra={"query": query[:100], "error": str(e)},
            exc_info=True,
        )
        raise MultiIndexSearchError(f"Multi-index search failed: {e}") from e


async def _execute_vector_search(query: str, top_k: int) -> list[SearchResult]:
    """Execute vector search using Qdrant semantic search.

    Args:
        query: Natural language query
        top_k: Number of results to return

    Returns:
        List of SearchResult objects from vector search

    Raises:
        MultiIndexSearchError: If vector search fails
    """
    try:
        logger.debug("Executing vector search", extra={"query": query[:100]})

        # Call existing hybrid_search from search.py (Story 2.1)
        vector_results = await hybrid_search(query, top_k=top_k, enable_hybrid=True)

        # Convert QueryResult to SearchResult
        results = [
            SearchResult(
                text=r.text,
                score=r.score,
                source="vector",
                metadata={
                    "source_document": r.source_document,
                    "page_number": r.page_number,
                    "chunk_index": r.chunk_index,
                    "word_count": r.word_count,
                },
                document_id=r.source_document,
                page_number=r.page_number,
            )
            for r in vector_results
        ]

        logger.debug("Vector search complete", extra={"results_count": len(results)})
        return results

    except Exception as e:
        logger.error("Vector search failed", extra={"error": str(e)}, exc_info=True)
        raise MultiIndexSearchError(f"Vector search failed: {e}") from e


async def _execute_sql_search(query: str, top_k: int) -> list[SearchResult]:
    """Execute SQL table search using PostgreSQL.

    Args:
        query: Natural language query or SQL-like query
        top_k: Number of table rows to return

    Returns:
        List of SearchResult objects from SQL search

    Raises:
        MultiIndexSearchError: If SQL search fails
    """
    try:
        logger.debug("Executing SQL search", extra={"query": query[:100]})

        # Story 2.7 Enhancement: Preprocess query to extract keywords and metadata filters
        # This separates business keywords from temporal qualifiers for better matching
        keywords, filters = preprocess_query_for_table_search(query)

        # Call table retrieval with metadata filtering if available
        if filters:
            logger.debug(
                "Using metadata-filtered search",
                extra={"keywords": keywords, "filters": filters},
            )
            sql_results = await search_tables_with_metadata_filter(
                query=keywords, top_k=top_k, filters=filters
            )
        else:
            logger.debug("Using standard search", extra={"keywords": keywords})
            sql_results = await search_tables(query=keywords, top_k=top_k)

        # Convert table rows to SearchResult objects
        # STUB: search_tables returns empty list until Story 2.6 complete
        results = [
            SearchResult(
                text=row.get("text", ""),
                score=row.get("score", 0.5),  # Default score for SQL results
                source="sql",
                metadata=row.get("metadata", {}),
                document_id=row.get("document_id", "unknown"),
                page_number=row.get("page_number"),
            )
            for row in sql_results
        ]

        logger.debug("SQL search complete", extra={"results_count": len(results)})

        # AC6: Fallback to vector search if SQL returns no results
        # NEW (Story 2.10 AC3): Track SQL fallback rate for monitoring
        if not results:
            logger.warning(
                "SQL search returned 0 results - falling back to vector search",
                extra={
                    "query": query[:100],
                    "query_type": "sql_only",
                    "fallback_reason": "empty_sql_results",
                },
            )
            return await _execute_vector_search(query, top_k)

        return results

    except TableRetrievalError as e:
        # AC6: PostgreSQL unavailable → Fallback to vector search
        logger.warning(
            "PostgreSQL connection failed, falling back to vector-only mode",
            extra={"error": str(e)},
        )
        return await _execute_vector_search(query, top_k)

    except Exception as e:
        logger.error("SQL search failed", extra={"error": str(e)}, exc_info=True)
        # AC6: Fallback to vector search on any SQL error
        logger.warning("SQL search failed, falling back to vector search")
        return await _execute_vector_search(query, top_k)


async def _execute_hybrid_search(query: str, top_k: int) -> list[SearchResult]:
    """Execute hybrid search with parallel vector + SQL execution and result fusion.

    Story 2.7 AC2-AC3: Parallel execution using asyncio.gather, followed by
    weighted fusion of results.

    Args:
        query: Natural language query
        top_k: Number of results to return after fusion

    Returns:
        List of SearchResult objects after fusion and re-ranking

    Raises:
        MultiIndexSearchError: If both searches fail
    """
    logger.debug("Executing hybrid search (parallel)", extra={"query": query[:100]})

    try:
        # AC2: Parallel execution using asyncio.gather
        # Set timeout for fusion (5s per AC6)
        vector_task = _execute_vector_search(query, top_k=top_k * 2)  # Cast wider net
        sql_task = _execute_sql_search(query, top_k=top_k * 2)

        # Execute in parallel with 5s timeout (AC6)
        vector_results, sql_results = await asyncio.wait_for(
            asyncio.gather(vector_task, sql_task), timeout=5.0
        )

        logger.debug(
            "Parallel searches complete",
            extra={
                "vector_count": len(vector_results),
                "sql_count": len(sql_results),
            },
        )

        # AC3: Fuse results using weighted sum
        fused_results = merge_results(vector_results, sql_results, alpha=0.6, top_k=top_k)

        return fused_results

    except TimeoutError:
        # AC6: Fusion timeout → Return whichever completed first
        logger.warning("Hybrid search timeout (5s), falling back to vector search only")
        return await _execute_vector_search(query, top_k)

    except Exception as e:
        logger.error("Hybrid search failed", extra={"error": str(e)}, exc_info=True)
        # Fallback to vector search
        logger.warning("Hybrid search failed, falling back to vector search")
        return await _execute_vector_search(query, top_k)


def merge_results(
    vector_results: list[SearchResult],
    sql_results: list[SearchResult],
    alpha: float = 0.6,
    top_k: int = 5,
) -> list[SearchResult]:
    """Fuse vector and SQL search results using weighted sum.

    Story 2.7 AC3: Implements weighted fusion algorithm with deduplication.

    Fusion Algorithm:
      1. Normalize scores from both indexes to [0,1] range
      2. Apply weighted sum: final_score = alpha * vector_score + (1 - alpha) * sql_score
      3. Deduplicate: If same document appears in both, keep higher-scored result
      4. Re-rank by final_score and return top_k

    Args:
        vector_results: Results from vector search
        sql_results: Results from SQL search
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
        "Fusing results",
        extra={
            "vector_count": len(vector_results),
            "sql_count": len(sql_results),
            "alpha": alpha,
        },
    )

    # Step 1: Normalize scores to [0,1] (already normalized from search functions)
    # Vector and SQL scores should already be in [0,1] range

    # Step 2: Weighted sum fusion
    # Create mapping of document_id to best result
    result_map: dict[str, SearchResult] = {}

    # Process vector results
    for result in vector_results:
        key = f"{result.document_id}:{result.page_number}"
        if key not in result_map:
            result_map[key] = result
        else:
            # Duplicate: keep higher score
            if result.score > result_map[key].score:
                result_map[key] = result

    # Process SQL results
    for result in sql_results:
        key = f"{result.document_id}:{result.page_number}"
        if key not in result_map:
            result_map[key] = result
        else:
            # Duplicate found in both indexes: Apply weighted fusion
            existing = result_map[key]
            if existing.source == "vector":
                # Fuse vector + SQL scores
                fused_score = alpha * existing.score + (1 - alpha) * result.score
                result_map[key] = SearchResult(
                    text=existing.text,  # Keep vector text (better quality)
                    score=fused_score,
                    source="hybrid",  # Mark as fused
                    metadata={**existing.metadata, **result.metadata},  # Merge metadata
                    document_id=existing.document_id,
                    page_number=existing.page_number,
                )
                logger.debug(
                    "Deduplicated and fused",
                    extra={
                        "key": key,
                        "vector_score": existing.score,
                        "sql_score": result.score,
                        "fused_score": fused_score,
                    },
                )

    # Step 3: Re-rank by score and return top-k
    all_results = list(result_map.values())
    sorted_results = sorted(all_results, key=lambda x: x.score, reverse=True)

    logger.debug(
        "Fusion complete",
        extra={
            "fused_count": len(sorted_results),
            "top_score": round(sorted_results[0].score, 4) if sorted_results else None,
        },
    )

    return sorted_results[:top_k]
