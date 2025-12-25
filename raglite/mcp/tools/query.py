"""Query MCP tools."""

import json
import time

from raglite.agentic.fallback import FallbackResponse, handle_workflow_failure
from raglite.agentic.orchestrator import WorkflowExecutor
from raglite.agentic.planner import QueryComplexity, classify_query_complexity, decompose_query
from raglite.main import mcp
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
        from raglite.shared.models import QueryResult

        query_results = [
            QueryResult(
                score=r.score,
                text=r.text,
                source_document=r.document_id,
                page_number=r.page_number,
                chunk_index=r.metadata.get("chunk_index", 0),
                word_count=r.metadata.get("word_count", 0),
            )
            for r in search_results
        ]
        cited_results = await generate_citations(query_results)
        total_duration_ms = (time.perf_counter() - start_time) * 1000
        retrieval_sources = {r.source for r in search_results}
        logger.info(
            "Query complete (multi-index)",
            extra={
                "query": request.query,
                "results_count": len(cited_results),
                "retrieval_sources": list(retrieval_sources),
                "search_time_ms": f"{search_duration_ms:.2f}",
                "total_time_ms": f"{total_duration_ms:.2f}",
                "retrieval_method": "multi-index",
            },
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


@mcp.tool()
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
            reasoning_steps = [
                "1. Classified query as simple (direct retrieval)",
                f"2. Retrieved {len(basic_response.results)} relevant documents via vector search",
                "3. Ranked results by similarity score",
            ]
            sources = [
                f"{r.source_document} (page {r.page_number})"
                if r.page_number is not None
                else r.source_document
                for r in basic_response.results
            ]
            logger.info(
                "Simple query complete (Epic 2 routing)",
                extra={
                    "query": request.query,
                    "results_count": len(basic_response.results),
                    "duration_ms": f"{workflow_duration_ms:.2f}",
                    "routing": "epic2_basic_retrieval",
                },
            )
            answer_parts = ["Based on the retrieved documents:\n"]
            for i, result in enumerate(basic_response.results[:3], 1):
                text_preview = result.text[:200] + "..." if len(result.text) > 200 else result.text
                answer_parts.append(f"{i}. {text_preview}")
            return AnalyticalQueryResponse(
                answer="\n".join(answer_parts),
                complexity=complexity.value,
                workflow_metadata={
                    "task_count": 1,
                    "execution_time_ms": int(workflow_duration_ms),
                    "workflow_pattern": "simple_retrieval",
                    "fallback_tier": "basic_retrieval",
                },
                confidence="high",
                limitations=[],
                reasoning_steps=reasoning_steps,
                sources=sources,
            )
        plan = await decompose_query(request.query, complexity)
        logger.info(
            "Query decomposed",
            extra={
                "query": request.query,
                "task_count": len(plan.tasks),
                "pattern": plan.metadata.get("pattern", "unknown"),
            },
        )
        executor = WorkflowExecutor()
        results = await executor.execute_workflow(plan)
        workflow_duration_ms = (time.perf_counter() - workflow_start_time) * 1000
        synthesis_result = next(
            (r for r in reversed(results) if r.success and r.agent_type == "synthesis"),
            None,
        )
        if synthesis_result:
            answer = str(synthesis_result.result)
            fallback_tier = "full_orchestration"
            confidence = "high"
            limitations: list[str] = []
            reasoning_steps = []
            pattern = plan.metadata.get("pattern", "unknown")
            reasoning_steps.append(f"1. Classified query as analytical ({pattern} pattern)")
            retrieval_results = [r for r in results if r.agent_type == "retrieval" and r.success]
            for i, r in enumerate(retrieval_results, start=2):
                task_desc = next(
                    (t.instruction for t in plan.tasks if t.task_id == r.task_id),
                    "retrieval task",
                )
                # Retrieval agent returns JSON string - parse to get chunk count
                doc_count: str | int = "relevant"
                if isinstance(r.result, str):
                    try:
                        result_data = json.loads(r.result)
                        if isinstance(result_data, dict) and "chunks" in result_data:
                            doc_count = len(result_data["chunks"])
                    except (json.JSONDecodeError, KeyError):
                        pass
                elif isinstance(r.result, list):
                    doc_count = len(r.result)
                reasoning_steps.append(f"{i}. Retrieved {doc_count} documents: {task_desc}")
            analysis_results = [r for r in results if r.agent_type == "analysis" and r.success]
            step_num = len(reasoning_steps) + 1
            for r in analysis_results:
                task_desc = next(
                    (t.instruction for t in plan.tasks if t.task_id == r.task_id),
                    "analysis task",
                )
                reasoning_steps.append(f"{step_num}. Performed analysis: {task_desc}")
                step_num += 1
            task_count = len(results)
            reasoning_steps.append(
                f"{step_num}. Synthesized final answer from {task_count} workflow tasks"
            )
            sources = []
            for r in retrieval_results:
                # Retrieval agent returns JSON string - parse to extract sources
                if isinstance(r.result, str):
                    try:
                        result_data = json.loads(r.result)
                        if isinstance(result_data, dict) and "chunks" in result_data:
                            for chunk in result_data["chunks"]:
                                # Extract document ID and page number from chunk
                                doc_id = chunk.get("id") or chunk.get("source_document")
                                page_num = chunk.get("page_number")
                                if doc_id:
                                    page_ref = f" (page {page_num})" if page_num is not None else ""
                                    source = f"{doc_id}{page_ref}"
                                    if source not in sources:
                                        sources.append(source)
                    except (json.JSONDecodeError, KeyError, TypeError):
                        logger.warning(
                            "Failed to parse retrieval result for sources",
                            extra={"task_id": r.task_id, "result_type": type(r.result).__name__},
                        )
                elif isinstance(r.result, list):
                    # Legacy support for list results (if any agents return this format)
                    for doc in r.result:
                        if hasattr(doc, "document_id"):
                            has_page = hasattr(doc, "page_number") and doc.page_number is not None
                            page_ref = f" (page {doc.page_number})" if has_page else ""
                            source = f"{doc.document_id}{page_ref}"
                        elif hasattr(doc, "source_document"):
                            has_page_num = doc.page_number is not None
                            page_ref = f" (page {doc.page_number})" if has_page_num else ""
                            source = f"{doc.source_document}{page_ref}"
                        else:
                            continue
                        if source not in sources:
                            sources.append(source)
            logger.info(
                "Analytical query complete",
                extra={
                    "query": request.query,
                    "task_count": len(results),
                    "success_count": sum(1 for r in results if r.success),
                    "duration_ms": f"{workflow_duration_ms:.2f}",
                    "fallback_tier": fallback_tier,
                    "sources_count": len(sources),
                },
            )
            return AnalyticalQueryResponse(
                answer=answer,
                complexity=complexity.value,
                workflow_metadata={
                    "task_count": len(results),
                    "execution_time_ms": int(workflow_duration_ms),
                    "workflow_pattern": plan.metadata.get("pattern", "unknown"),
                    "fallback_tier": fallback_tier,
                },
                confidence=confidence,
                limitations=limitations,
                reasoning_steps=reasoning_steps,
                sources=sources,
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
        fallback_response: FallbackResponse = await handle_workflow_failure(
            query=request.query,
            complexity=complexity if "complexity" in locals() else QueryComplexity.ANALYTICAL,
            partial_results=partial_results,
            error=e,
            total_time_ms=int(workflow_duration_ms),
        )
        logger.info(
            "Graceful degradation complete",
            extra={
                "query": request.query,
                "fallback_tier": fallback_response.tier.value,
                "confidence": fallback_response.confidence,
                "duration_ms": f"{workflow_duration_ms:.2f}",
            },
        )
        fallback_reasoning = [
            "1. Classified query as analytical",
            f"2. Attempted multi-step workflow ({len(partial_results)} tasks started)",
            f"3. Workflow failed: {str(e)[:100]}...",
            f"4. Gracefully degraded to {fallback_response.tier.value} tier",
        ]
        fallback_sources = []
        if hasattr(fallback_response, "sources"):
            fallback_sources = fallback_response.sources
        elif hasattr(fallback_response, "results"):
            for result in fallback_response.results[:5]:
                if hasattr(result, "source_document"):
                    has_page = result.page_number is not None
                    page_ref = f" (page {result.page_number})" if has_page else ""
                    fallback_sources.append(f"{result.source_document}{page_ref}")
        return AnalyticalQueryResponse(
            answer=fallback_response.answer,
            complexity=complexity.value if "complexity" in locals() else "analytical",
            workflow_metadata={
                "task_count": len(partial_results),
                "execution_time_ms": fallback_response.execution_time_ms,
                "workflow_pattern": "fallback",
                "fallback_tier": fallback_response.tier.value,
            },
            confidence=fallback_response.confidence,
            limitations=fallback_response.limitations,
            reasoning_steps=fallback_reasoning,
            sources=fallback_sources,
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
