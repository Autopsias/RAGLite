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

from raglite.retrieval.query_classifier import QueryType, classify_query, generate_sql_query
from raglite.retrieval.search import hybrid_search
from raglite.retrieval.sql_table_search import SQLSearchError, search_tables_sql
from raglite.structured.table_retrieval import (
    TableRetrievalError,
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

    # FORCE VISIBLE DEBUG OUTPUT
    print(f"[MULTI_INDEX_SEARCH DEBUG] Function called with query: {query[:80]}", flush=True)
    print(f"[MULTI_INDEX_SEARCH DEBUG] top_k={top_k}", flush=True)

    logger.info("Multi-index search started", extra={"query": query[:100], "top_k": top_k})
    start_time = time.time()

    try:
        # Step 1: Classify query type (AC1)
        query_type = classify_query(query)

        # FORCE VISIBLE DEBUG OUTPUT
        print(f"[MULTI_INDEX_SEARCH DEBUG] Query classified as: {query_type.value}", flush=True)

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
            print("[MULTI_INDEX_SEARCH DEBUG] Routing to SQL_ONLY", flush=True)
            results = await _execute_sql_search(query, top_k)

        elif query_type == QueryType.VECTOR_ONLY:
            # Vector-only: Qdrant semantic search
            print("[MULTI_INDEX_SEARCH DEBUG] Routing to VECTOR_ONLY", flush=True)
            results = await _execute_vector_search(query, top_k)

        elif query_type == QueryType.HYBRID:
            # Hybrid: Both indexes in parallel (AC2)
            print("[MULTI_INDEX_SEARCH DEBUG] Routing to HYBRID", flush=True)
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
    """Execute SQL table search using PostgreSQL text-to-SQL generation.

    Story 2.13 Integration: Uses generate_sql_query() + search_tables_sql() to query
    financial_tables (structured data) instead of financial_chunks (document chunks).

    Args:
        query: Natural language query
        top_k: Number of table rows to return

    Returns:
        List of SearchResult objects from SQL search

    Raises:
        MultiIndexSearchError: If SQL search fails
    """
    try:
        # FORCE VISIBLE DEBUG OUTPUT
        print(f"[SQL_SEARCH DEBUG] _execute_sql_search called with query: {query[:80]}", flush=True)

        logger.debug(
            "Executing SQL search via text-to-SQL generation", extra={"query": query[:100]}
        )

        # Step 1: Generate SQL query using text-to-SQL (Story 2.13 AC1)
        print("[SQL_SEARCH DEBUG] Generating SQL query from natural language...", flush=True)
        sql_query = await generate_sql_query(query)

        if not sql_query:
            logger.warning(
                "SQL generation returned None - falling back to vector search",
                extra={"query": query[:100]},
            )
            print(
                "[SQL_SEARCH DEBUG] SQL generation failed, falling back to vector search",
                flush=True,
            )
            return await _execute_vector_search(query, top_k)

        # FORCE VISIBLE DEBUG OUTPUT
        print(f"[SQL_SEARCH DEBUG] Generated SQL: {sql_query[:150]}", flush=True)
        logger.debug("SQL query generated", extra={"sql_preview": sql_query[:200]})

        # Step 2: Execute SQL against financial_tables (Story 2.13 AC2)
        print("[SQL_SEARCH DEBUG] Executing SQL against financial_tables...", flush=True)
        query_results = await search_tables_sql(sql_query, top_k=top_k)

        # FORCE VISIBLE DEBUG OUTPUT
        print(
            f"[SQL_SEARCH DEBUG] SQL execution complete - rows returned: {len(query_results)}",
            flush=True,
        )

        # Step 3: Convert QueryResult objects to SearchResult objects
        results = [
            SearchResult(
                text=qr.text,
                score=qr.score,  # search_tables_sql returns score=1.0 for all results
                source="sql",
                metadata={
                    "source_document": qr.source_document,
                    "page_number": qr.page_number,
                    "chunk_index": qr.chunk_index,
                },
                document_id=qr.source_document,
                page_number=qr.page_number,
            )
            for qr in query_results
        ]

        logger.debug("SQL search complete", extra={"results_count": len(results)})

        # AC6: Fallback to vector search if SQL returns no results
        if not results:
            logger.warning(
                "SQL search returned 0 results - falling back to vector search",
                extra={
                    "query": query[:100],
                    "query_type": "sql_only",
                    "fallback_reason": "empty_sql_results",
                    "sql_preview": sql_query[:150] if sql_query else "None",
                },
            )
            print(
                "[SQL_SEARCH DEBUG] 0 results from SQL, falling back to vector search", flush=True
            )
            return await _execute_vector_search(query, top_k)

        return results

    except SQLSearchError as e:
        # SQL execution failed (database error, invalid SQL, etc.)
        logger.warning(
            "SQL execution failed, falling back to vector search",
            extra={"error": str(e), "query": query[:100]},
        )
        print(f"[SQL_SEARCH DEBUG] SQLSearchError: {str(e)[:150]}", flush=True)
        return await _execute_vector_search(query, top_k)

    except TableRetrievalError as e:
        # AC6: PostgreSQL unavailable → Fallback to vector search
        logger.warning(
            "PostgreSQL connection failed, falling back to vector-only mode",
            extra={"error": str(e)},
        )
        print(f"[SQL_SEARCH DEBUG] TableRetrievalError: {str(e)[:150]}", flush=True)
        return await _execute_vector_search(query, top_k)

    except Exception as e:
        logger.error("SQL search failed unexpectedly", extra={"error": str(e)}, exc_info=True)
        # AC6: Fallback to vector search on any SQL error
        logger.warning("SQL search failed, falling back to vector search")
        print(f"[SQL_SEARCH DEBUG] Unexpected error: {str(e)[:150]}", flush=True)
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

    # FORCE VISIBLE DEBUG OUTPUT
    print("[HYBRID_SEARCH DEBUG] Starting parallel search", flush=True)

    try:
        # AC2: Parallel execution using asyncio.gather
        # Set timeout for fusion (5s per AC6)
        vector_task = _execute_vector_search(query, top_k=top_k * 2)  # Cast wider net
        sql_task = _execute_sql_search(query, top_k=top_k * 2)

        # Execute in parallel with 5s timeout (AC6)
        vector_results, sql_results = await asyncio.wait_for(
            asyncio.gather(vector_task, sql_task), timeout=5.0
        )

        # FORCE VISIBLE DEBUG OUTPUT
        print(
            f"[HYBRID_SEARCH DEBUG] Parallel searches complete - vector: {len(vector_results)}, sql: {len(sql_results)}",
            flush=True,
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

    # Story 2.11 FIX: Normalize scores from both indexes before fusion
    # RRF scores are typically 0.001-0.03 range
    # SQL scores are typically 1.0 (hardcoded)
    # Without normalization, weighted sum is dominated by SQL presence

    # Find max scores for normalization
    max_vector_score = max((r.score for r in vector_results), default=0.001)
    max_sql_score = max((r.score for r in sql_results), default=1.0)

    # Create mapping of document_id to best result
    result_map: dict[str, SearchResult] = {}

    # Process vector results with normalization
    for result in vector_results:
        key = f"{result.document_id}:{result.page_number}"
        # Normalize vector score to [0,1] range using max-score normalization
        normalized_vector_score = result.score / max_vector_score if max_vector_score > 0 else 0

        if key not in result_map:
            result_map[key] = SearchResult(
                text=result.text,
                score=normalized_vector_score,  # Store normalized score temporarily
                source=result.source,
                metadata=result.metadata,
                document_id=result.document_id,
                page_number=result.page_number,
            )
        else:
            # Duplicate: keep higher normalized score
            if normalized_vector_score > result_map[key].score:
                result_map[key] = SearchResult(
                    text=result.text,
                    score=normalized_vector_score,
                    source=result.source,
                    metadata=result.metadata,
                    document_id=result.document_id,
                    page_number=result.page_number,
                )

    # Process SQL results with normalization and fusion
    for result in sql_results:
        key = f"{result.document_id}:{result.page_number}"
        # Normalize SQL score to [0,1] range using max-score normalization
        normalized_sql_score = result.score / max_sql_score if max_sql_score > 0 else 0

        if key not in result_map:
            result_map[key] = SearchResult(
                text=result.text,
                score=normalized_sql_score,  # Store normalized score temporarily
                source=result.source,
                metadata=result.metadata,
                document_id=result.document_id,
                page_number=result.page_number,
            )
        else:
            # Duplicate found in both indexes: Apply weighted fusion with normalized scores
            existing = result_map[key]
            if existing.source == "vector" or existing.source == "hybrid":
                # Fuse vector + SQL scores using weighted sum (both now normalized)
                fused_score = alpha * existing.score + (1 - alpha) * normalized_sql_score
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
                        "vector_score_normalized": round(existing.score, 4),
                        "sql_score_normalized": round(normalized_sql_score, 4),
                        "fused_score": round(fused_score, 4),
                        "alpha": alpha,
                    },
                )

    # Step 3: Re-rank by score and return top-k
    all_results = list(result_map.values())
    sorted_results = sorted(all_results, key=lambda x: x.score, reverse=True)

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
