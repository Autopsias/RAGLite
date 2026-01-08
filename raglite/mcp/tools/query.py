"""Query MCP tools."""

import time

from raglite.agentic.fallback import handle_workflow_failure
from raglite.agentic.planner import QueryComplexity, classify_query_complexity
from raglite.main import mcp
from raglite.mcp.tools.query_helpers import (
    _build_analytical_response,
    _build_simple_query_response,
    _execute_complex_workflow,
    _handle_fallback_response,
    _log_query_completion,
    _transform_search_results_to_query_results,
)
from raglite.retrieval.attribution import generate_citations
from raglite.retrieval.multi_index_search import MultiIndexSearchError, multi_index_search
from raglite.retrieval.search import QueryError
from raglite.shared.logging import get_logger
from raglite.shared.models import (
    AnalyticalQueryRequest,
    AnalyticalQueryResponse,
    QueryRequest,
    QueryResponse,
)

logger = get_logger(__name__)


@mcp.tool()
async def query_financial_documents(request: QueryRequest) -> QueryResponse:
    """Query financial documents using natural language with multi-index search.
    Story 2.7 AC4: Updated to use multi-index search (vector + SQL) with intelligent
    query routing. Maintains backward compatibility with Story 2.1 hybrid search.
    Query pipeline (Story 2.7):
      1. Classify query type (SQL_ONLY, VECTOR_ONLY, or HYBRID)
      2. Route to appropriate index(es):
         - SQL_ONLY → PostgreSQL table search
         - VECTOR_ONLY → Qdrant semantic search
         - HYBRID → Both indexes in parallel with fusion
      3. Generate source citations for each chunk
      4. Return raw chunks with metadata for LLM synthesis
    Args:
        request: Query parameters containing:
          - query: Natural language query string
          - top_k: Number of results to return (default: 5, range: 1-50)
    Returns:
        QueryResponse containing:
          - results: List of QueryResult objects with:
              * text: Chunk content with appended citation
              * score: Similarity score (0-1, higher is better)
              * source_document: Document filename
              * page_number: Page where chunk appears (or None)
              * chunk_index: Sequential chunk index
              * word_count: Chunk word count
          - query: Original query string
          - retrieval_time_ms: Retrieval time in milliseconds
    Raises:
        QueryError: If search fails (empty query, embedding error, index error)
    Example:
        >>> request = QueryRequest(query="What was Q3 revenue?", top_k=5)
        >>> response = await query_financial_documents(request)
        >>> for result in response.results:
        ...     print(f"[{result.score:.2f}] {result.text}")
    """
    logger.info(
        "Query received",
        extra={
            "query": request.query,
            "top_k": request.top_k,
        },
    )
    if not request.query or not request.query.strip():
        error_msg = "Query cannot be empty"
        logger.warning("Empty query rejected", extra={"query": request.query})
        raise QueryError(error_msg)
    try:
        start_time = time.perf_counter()
        search_results = await multi_index_search(request.query, top_k=request.top_k)
        search_duration_ms = (time.perf_counter() - start_time) * 1000

        query_results = _transform_search_results_to_query_results(search_results)
        cited_results = await generate_citations(query_results)
        total_duration_ms = (time.perf_counter() - start_time) * 1000

        _log_query_completion(
            request.query, cited_results, search_results, search_duration_ms, total_duration_ms
        )

        return QueryResponse(
            results=cited_results,
            query=request.query,
            retrieval_time_ms=total_duration_ms,
        )
    except MultiIndexSearchError as e:
        logger.error(
            "Multi-index search failed",
            extra={
                "query": request.query,
                "error": str(e),
            },
            exc_info=True,
        )
        raise QueryError(f"Multi-index search failed: {e}") from e
    except QueryError:
        raise
    except Exception as e:
        logger.error(
            "Query failed",
            extra={
                "query": request.query,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise QueryError(f"Query failed: {e}") from e


async def analytical_query_financial_documents(
    request: AnalyticalQueryRequest,
) -> AnalyticalQueryResponse:
    logger.info(
        "Analytical query received",
        extra={
            "query": request.query,
            "top_k": request.top_k,
        },
    )
    if not request.query or not request.query.strip():
        error_msg = "Query cannot be empty"
        logger.warning("Empty analytical query rejected", extra={"query": request.query})
        raise QueryError(error_msg)
    workflow_start_time = time.perf_counter()
    try:
        complexity = await classify_query_complexity(request.query)
        logger.info(
            "Query classified",
            extra={"query": request.query, "complexity": complexity},
        )
        if complexity == QueryComplexity.SIMPLE:
            logger.info(
                "Routing simple query to Epic 2 basic retrieval",
                extra={"query": request.query, "complexity": complexity},
            )
            basic_request = QueryRequest(query=request.query, top_k=request.top_k)
            basic_response = await query_financial_documents.fn(basic_request)
            workflow_duration_ms = (time.perf_counter() - workflow_start_time) * 1000

            logger.info(
                "Simple query complete (Epic 2 routing)",
                extra={
                    "query": request.query,
                    "results_count": len(basic_response.results),
                    "duration_ms": f"{workflow_duration_ms:.2f}",
                    "routing": "epic2_basic_retrieval",
                },
            )

            return _build_simple_query_response(
                basic_response,
                workflow_duration_ms,
                complexity.value,
            )

        # Complex query workflow
        plan, results, workflow_duration_ms = await _execute_complex_workflow(request, complexity)

        synthesis_result = next(
            (r for r in reversed(results) if r.success and r.agent_type == "synthesis"),
            None,
        )

        if synthesis_result:
            answer = str(synthesis_result.result)
            return _build_analytical_response(
                answer,
                plan,
                results,
                complexity.value,
                workflow_duration_ms,
            )
        else:
            raise RuntimeError("No synthesis result available from workflow")

    except Exception as e:
        workflow_duration_ms = (time.perf_counter() - workflow_start_time) * 1000
        logger.warning(
            "Analytical workflow failed - initiating graceful degradation",
            extra={
                "query": request.query,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": f"{workflow_duration_ms:.2f}",
            },
        )

        partial_results = []
        if "results" in locals():
            partial_results = results

        fallback_response = await handle_workflow_failure(
            query=request.query,
            complexity=complexity if "complexity" in locals() else QueryComplexity.ANALYTICAL,
            partial_results=partial_results,
            error=e,
            total_time_ms=int(workflow_duration_ms),
        )

        return _handle_fallback_response(
            fallback_response,
            complexity.value if "complexity" in locals() else "analytical",
            partial_results,
            workflow_duration_ms,
        )


def parse_forecast_query(query: str) -> tuple[str | None, int | None]:
    import re

    query_lower = query.lower()
    metric_patterns = {
        r"\b(?:revenue|sales|income)\b": "revenue",
        r"\bcash\s*flow\b": "cash_flow",
        r"\b(?:expenses?|costs?|spending)\b": "expenses",
    }
    metric = None
    for pattern, metric_name in metric_patterns.items():
        if re.search(pattern, query_lower):
            metric = metric_name
            break
    periods = None
    if re.search(r"next\s+quarter\b", query_lower):
        periods = 1
    next_n_match = re.search(r"next\s+(\d+)\s+quarters?", query_lower)
    if next_n_match:
        periods = min(int(next_n_match.group(1)), 8)
    for_n_match = re.search(r"for\s+(?:the\s+)?(?:next\s+)?(\d+)\s+quarters?", query_lower)
    if for_n_match:
        periods = min(int(for_n_match.group(1)), 8)
    q_match = re.search(r"q([1-4])\s*(\d{4})", query_lower)
    if q_match:
        from datetime import datetime

        target_quarter = int(q_match.group(1))
        target_year = int(q_match.group(2))
        now = datetime.now()
        current_quarter = (now.month - 1) // 3 + 1
        current_year = now.year
        target_q_ordinal = target_year * 4 + target_quarter
        current_q_ordinal = current_year * 4 + current_quarter
        periods = max(1, target_q_ordinal - current_q_ordinal)
        periods = min(periods, 8)
    return metric, periods
