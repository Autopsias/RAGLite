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
