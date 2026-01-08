"""Helper functions for query MCP tools."""

import json
import time
from typing import TYPE_CHECKING, Any

from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from raglite.shared.models import AnalyticalQueryResponse

logger = get_logger(__name__)


def _transform_search_results_to_query_results(search_results: Any) -> Any:
    """Transform multi-index search results to QueryResult objects.

    Args:
        search_results: Results from multi_index_search

    Returns:
        List of QueryResult objects
    """
    from raglite.shared.models import QueryResult

    return [
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


def _log_query_completion(
    query: str,
    cited_results: Any,
    search_results: Any,
    search_duration_ms: float,
    total_duration_ms: float,
) -> None:
    """Log query completion with metadata.

    Args:
        query: Original query string
        cited_results: Results with citations
        search_results: Raw search results
        search_duration_ms: Time for search in ms
        total_duration_ms: Total time including citations in ms
    """
    retrieval_sources = {r.source for r in search_results}
    logger.info(
        "Query complete (multi-index)",
        extra={
            "query": query,
            "results_count": len(cited_results),
            "retrieval_sources": list(retrieval_sources),
            "search_time_ms": f"{search_duration_ms:.2f}",
            "total_time_ms": f"{total_duration_ms:.2f}",
            "retrieval_method": "multi-index",
        },
    )


def _build_simple_query_response(
    basic_response: Any, workflow_duration_ms: float, complexity: str
) -> "AnalyticalQueryResponse":
    """Build AnalyticalQueryResponse for simple queries.

    Args:
        basic_response: Response from basic query tool
        workflow_duration_ms: Execution time in milliseconds
        complexity: Query complexity classification

    Returns:
        AnalyticalQueryResponse with simple query results
    """
    from raglite.shared.models import AnalyticalQueryResponse

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

    answer_parts = ["Based on the retrieved documents:\n"]
    for i, result in enumerate(basic_response.results[:3], 1):
        text_preview = result.text[:200] + "..." if len(result.text) > 200 else result.text
        answer_parts.append(f"{i}. {text_preview}")

    return AnalyticalQueryResponse(
        answer="\n".join(answer_parts),
        complexity=complexity,
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


def _extract_sources_from_results(results: Any) -> list[str]:
    """Extract source document references from workflow results.

    Args:
        results: List of WorkflowResult objects

    Returns:
        List of unique source references
    """
    retrieval_results = [r for r in results if r.agent_type == "retrieval" and r.success]
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

    return sources


def _build_reasoning_steps(plan: Any, results: Any) -> list[str]:
    """Build reasoning steps from workflow plan and results.

    Args:
        plan: Query decomposition plan
        results: Workflow execution results

    Returns:
        List of reasoning step strings
    """
    reasoning_steps = []
    pattern = plan.metadata.get("pattern", "unknown")
    reasoning_steps.append(f"1. Classified query as analytical ({pattern} pattern)")

    # Add retrieval steps
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

    # Add analysis steps
    analysis_results = [r for r in results if r.agent_type == "analysis" and r.success]
    step_num = len(reasoning_steps) + 1
    for r in analysis_results:
        task_desc = next(
            (t.instruction for t in plan.tasks if t.task_id == r.task_id),
            "analysis task",
        )
        reasoning_steps.append(f"{step_num}. Performed analysis: {task_desc}")
        step_num += 1

    # Add synthesis step
    task_count = len(results)
    reasoning_steps.append(f"{step_num}. Synthesized final answer from {task_count} workflow tasks")

    return reasoning_steps


def _build_analytical_response(
    answer: str,
    plan: Any,
    results: Any,
    complexity: str,
    workflow_duration_ms: float,
) -> "AnalyticalQueryResponse":
    """Build AnalyticalQueryResponse for complex analytical queries.

    Args:
        answer: Synthesized answer from workflow
        plan: Query decomposition plan
        results: Workflow execution results
        complexity: Query complexity classification
        workflow_duration_ms: Execution time in milliseconds

    Returns:
        AnalyticalQueryResponse with full workflow results
    """
    from raglite.shared.models import AnalyticalQueryResponse

    reasoning_steps = _build_reasoning_steps(plan, results)
    sources = _extract_sources_from_results(results)

    logger.info(
        "Analytical query complete",
        extra={
            "query": plan.metadata.get("query", "unknown"),
            "task_count": len(results),
            "success_count": sum(1 for r in results if r.success),
            "duration_ms": f"{workflow_duration_ms:.2f}",
            "fallback_tier": "full_orchestration",
            "sources_count": len(sources),
        },
    )

    return AnalyticalQueryResponse(
        answer=answer,
        complexity=complexity,
        workflow_metadata={
            "task_count": len(results),
            "execution_time_ms": int(workflow_duration_ms),
            "workflow_pattern": plan.metadata.get("pattern", "unknown"),
            "fallback_tier": "full_orchestration",
        },
        confidence="high",
        limitations=[],
        reasoning_steps=reasoning_steps,
        sources=sources,
    )


def _build_fallback_response_sources(fallback_response: Any) -> list[str]:
    """Extract sources from fallback response.

    Args:
        fallback_response: FallbackResponse from graceful degradation

    Returns:
        List of source references
    """
    fallback_sources = []
    if hasattr(fallback_response, "sources"):
        fallback_sources = fallback_response.sources
    elif hasattr(fallback_response, "results"):
        for result in fallback_response.results[:5]:
            if hasattr(result, "source_document"):
                has_page = result.page_number is not None
                page_ref = f" (page {result.page_number})" if has_page else ""
                fallback_sources.append(f"{result.source_document}{page_ref}")
    return fallback_sources


def _handle_fallback_response(
    fallback_response: Any,
    complexity: str,
    partial_results: Any,
    workflow_duration_ms: float,
) -> "AnalyticalQueryResponse":
    """Build AnalyticalQueryResponse from fallback.

    Args:
        fallback_response: FallbackResponse from graceful degradation
        complexity: Query complexity classification
        partial_results: Partial workflow results before failure
        workflow_duration_ms: Total execution time in milliseconds

    Returns:
        AnalyticalQueryResponse with fallback results
    """
    from raglite.shared.models import AnalyticalQueryResponse

    fallback_sources = _build_fallback_response_sources(fallback_response)

    logger.info(
        "Graceful degradation complete",
        extra={
            "fallback_tier": fallback_response.tier.value,
            "confidence": fallback_response.confidence,
            "duration_ms": f"{workflow_duration_ms:.2f}",
        },
    )

    return AnalyticalQueryResponse(
        answer=fallback_response.answer,
        complexity=complexity,
        workflow_metadata={
            "task_count": len(partial_results),
            "execution_time_ms": fallback_response.execution_time_ms,
            "workflow_pattern": "fallback",
            "fallback_tier": fallback_response.tier.value,
        },
        confidence=fallback_response.confidence,
        limitations=fallback_response.limitations,
        reasoning_steps=[
            "1. Classified query as analytical",
            f"2. Attempted multi-step workflow ({len(partial_results)} tasks started)",
            "3. Workflow failed - gracefully degraded",
            f"4. Fallback to {fallback_response.tier.value} tier",
        ],
        sources=fallback_sources,
    )


async def _execute_complex_workflow(request: Any, complexity: Any) -> tuple[Any, Any, float]:
    """Execute complex analytical workflow.

    Args:
        request: Analytical query request
        complexity: Query complexity classification

    Returns:
        Tuple of (plan, results, workflow_duration_ms)
    """
    from raglite.agentic.orchestrator import WorkflowExecutor
    from raglite.agentic.planner import decompose_query

    workflow_start_time = time.perf_counter()

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

    return plan, results, workflow_duration_ms
