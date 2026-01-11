"""Hybrid search orchestration for RAGLite.

Combines semantic (Fin-E5), keyword (BM25), and SQL table search strategies
with intelligent query routing and result fusion.
"""

import time

from raglite.retrieval.query_classifier import (
    QueryType,
    classify_query,
    classify_query_metadata,
    generate_sql_query,
)
from raglite.retrieval.search.core import QueryError, search_documents
from raglite.retrieval.search.enrichment import enrich_results_with_metadata
from raglite.retrieval.search.fusion import fuse_search_results, fuse_sql_vector_results
from raglite.retrieval.search.reformulation import search_with_reformulation
from raglite.retrieval.sql_table_search import search_tables_sql
from raglite.shared.bm25 import BM25IndexError, compute_bm25_scores, load_bm25_index
from raglite.shared.logging import get_logger
from raglite.shared.models import QueryResult

logger = get_logger(__name__)


async def _execute_sql_only_search(query: str, top_k: int, start_time: float) -> list[QueryResult]:
    """Execute SQL-only search with reformulation fallback.

    Args:
        query: Natural language query
        top_k: Number of results to return
        start_time: Search start timestamp for latency tracking

    Returns:
        List of SQL search results (enriched with metadata)
    """
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
            return await enrich_results_with_metadata(sql_results)
        else:
            logger.warning(
                "SQL search returned 0 results after reformulation - falling back to vector search"
            )
            return []
    except Exception as e:
        logger.error(
            "SQL search failed - falling back to vector search",
            extra={"error": str(e)},
            exc_info=True,
        )
        return []


async def _execute_hybrid_sql_search(query: str, top_k: int) -> list[QueryResult]:
    """Execute hybrid SQL+Vector search component (SQL part only).

    Args:
        query: Natural language query
        top_k: Number of results to return

    Returns:
        List of SQL search results (to be fused with vector results)
    """
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
        return sql_results
    except Exception as e:
        logger.error(
            "SQL component failed in hybrid search",
            extra={"error": str(e)},
            exc_info=True,
        )
        return []


async def _extract_query_metadata(
    query: str, auto_classify: bool, filters: dict[str, str] | None
) -> dict[str, str]:
    """Extract metadata from query for soft boosting.

    Args:
        query: Natural language query
        auto_classify: Whether to enable auto-classification
        filters: Existing filters (if provided, auto-classification is disabled)

    Returns:
        Dictionary of extracted metadata fields
    """
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
    return extracted_metadata


async def _route_sql_query(
    query: str, enable_sql_tables: bool, top_k: int, start_time: float
) -> tuple[list[QueryResult], QueryType]:
    """Route query to SQL backend based on classification.

    Args:
        query: Natural language query
        enable_sql_tables: Whether SQL routing is enabled
        top_k: Number of results to return
        start_time: Search start timestamp for latency tracking

    Returns:
        Tuple of (sql_results, query_type)
        - sql_results: List of SQL results (empty if not routed to SQL)
        - query_type: Classified query type
    """
    sql_results: list[QueryResult] = []

    if not enable_sql_tables:
        return sql_results, QueryType.VECTOR_ONLY

    query_type = classify_query(query)
    logger.info(
        "Query classified for SQL routing",
        extra={"query_type": query_type.value, "query": query[:100]},
    )

    # SQL_ONLY queries: Route to SQL-only search with reformulation fallback
    if query_type == QueryType.SQL_ONLY:
        sql_results = await _execute_sql_only_search(query, top_k, start_time)
        # Note: Caller will check if sql_results is empty and fallback to vector

    # HYBRID queries: Combine SQL + Vector results
    elif query_type == QueryType.HYBRID:
        sql_results = await _execute_hybrid_sql_search(query, top_k)
        # Note: Vector search will be executed by caller and fused with these results

    # VECTOR_ONLY queries: Use vector+BM25 only (no SQL routing)
    else:  # QueryType.VECTOR_ONLY
        logger.info("Routing to vector-only search (text/semantic query)")

    return sql_results, query_type


async def _execute_sql_vector_fusion(
    sql_results: list[QueryResult],
    semantic_results: list[QueryResult],
    top_k: int,
    start_time: float,
) -> list[QueryResult]:
    """Execute SQL+Vector fusion for hybrid queries.

    Args:
        sql_results: SQL search results
        semantic_results: Vector search results
        top_k: Number of results to return
        start_time: Search start timestamp for latency tracking

    Returns:
        List of fused results
    """
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


async def _execute_vector_bm25_fusion(
    query: str,
    semantic_results: list[QueryResult],
    top_k: int,
    alpha: float,
    extracted_metadata: dict[str, str],
    start_time: float,
) -> list[QueryResult]:
    """Execute BM25+Vector fusion for text queries.

    Args:
        query: Natural language query
        semantic_results: Semantic search results from vector DB
        top_k: Number of results to return
        alpha: Fusion weight (0.7 = 70% semantic, 30% BM25)
        extracted_metadata: Metadata extracted from query for score boosting
        start_time: Search start timestamp for latency tracking

    Returns:
        List of fused and enriched results

    Raises:
        BM25IndexError: If BM25 index unavailable (caller handles fallback)
    """
    bm25, _, chunk_metadata = load_bm25_index()
    bm25_scores = compute_bm25_scores(bm25, query)

    # Fuse results with metadata boosting (if metadata extracted)
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
            "metadata_boosted": (len(extracted_metadata) > 0 if extracted_metadata else False),
        },
    )

    # Story 5.0.6 AC5: Enrich results with metadata at query time
    return await enrich_results_with_metadata(hybrid_results)


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

    Combines semantic understanding with exact keyword matching. Routes SQL queries
    to table search (Story 2.13), supports auto-classification (Story 2.4, disabled
    by default per Story 2.11 - 70.2% < 80% threshold).

    Args:
        query: Natural language query
        top_k: Number of results to return (default: 5)
        alpha: Fusion weight - 0.7 = 70% semantic, 30% BM25
        filters: Optional metadata filters; if provided, disables auto_classify
        enable_hybrid: If False, falls back to semantic-only search
        auto_classify: If True and no filters, extract metadata from query via LLM
        enable_sql_tables: If True, route structured queries to SQL table search

    Returns:
        List of QueryResult objects ranked by hybrid score (highest first)

    Raises:
        QueryError: If search fails or query is invalid
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

    # Story 2.13 AC3: SQL Table Search Routing - Classify and route to SQL if enabled
    sql_results, query_type = await _route_sql_query(query, enable_sql_tables, top_k, start_time)

    # If SQL_ONLY query returned results, return them immediately
    if query_type == QueryType.SQL_ONLY and sql_results:
        return sql_results

    # Story 2.4 Enhancement: Extract metadata for soft boosting (not hard filtering)
    extracted_metadata = await _extract_query_metadata(query, auto_classify, filters)

    # Fallback to semantic-only if hybrid disabled
    if not enable_hybrid:
        logger.info("Hybrid search disabled - using semantic-only")
        return await search_documents(query, top_k=top_k, filters=filters)

    try:
        # Step 1: Retrieve semantic results (cast moderate net for fusion)
        semantic_top_k = max(top_k * 2, 10)  # Moderate net (minimum 10, not 20)
        semantic_results = await search_documents(query, top_k=semantic_top_k, filters=filters)

        if not semantic_results:
            logger.warning("No semantic results found")
            return []

        # Step 2: Fusion logic - SQL+Vector for HYBRID queries, BM25+Vector for TEXT queries
        if sql_results:
            # HYBRID query: Fuse SQL + Vector results
            return await _execute_sql_vector_fusion(
                sql_results, semantic_results, top_k, start_time
            )

        # TEXT query: Fuse BM25 + Vector results
        try:
            return await _execute_vector_bm25_fusion(
                query, semantic_results, top_k, alpha, extracted_metadata, start_time
            )
        except (BM25IndexError, FileNotFoundError) as e:
            # Fallback to semantic-only if BM25 index unavailable
            logger.warning(
                "BM25 index unavailable - falling back to semantic-only search",
                extra={"error": str(e)},
            )
            fallback_results = semantic_results[:top_k]
            fallback_results = await enrich_results_with_metadata(fallback_results)
            return fallback_results

    except QueryError:
        # Re-raise QueryError from search_documents
        raise
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}", exc_info=True)
        raise QueryError(f"Hybrid search failed: {e}") from e
