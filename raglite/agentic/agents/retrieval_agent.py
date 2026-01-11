"""Retrieval Agent for agentic workflows.

Story 3.2 AC1-AC3: Implements a @tool decorator-based retrieval agent
that wraps the Epic 2 multi-index search, enabling the orchestrator
to search document knowledge bases.

NOTE: Strands import is optional - agentic workflows deferred until Epic 3.
"""

import json
import time

try:
    from strands import tool
except ImportError:
    # Strands not installed - deferred until Epic 3 (Story 3.1+)
    # For now, use a no-op decorator
    def tool(func):  # type: ignore
        """No-op tool decorator when strands is not available."""
        return func


from raglite.retrieval.multi_index_search import MultiIndexSearchError, multi_index_search
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def _reformulate_query(query: str) -> str:
    """Remove instruction prefixes and simplify query.

    Args:
        query: Original query string

    Returns:
        Reformulated query string
    """
    if query.startswith("Retrieve relevant financial data for:"):
        return query[39:].strip()
    elif query.startswith("Search for:"):
        return query[11:].strip()
    return query


async def _execute_search(query: str, top_k: int) -> tuple[list[dict], str | None]:
    """Execute multi-index search and convert results to JSON format.

    Args:
        query: Search query string
        top_k: Number of results to return

    Returns:
        Tuple of (chunks_data, backend)
    """
    search_results = await multi_index_search(query, top_k=top_k)

    chunks_data = [
        {
            "id": result.document_id,
            "content": result.text,
            "source": result.source,
            "page_number": result.page_number,
            "chunk_index": i,
            "metadata": {
                **result.metadata,
                "score": result.score,
                "search_source": result.source,
            },
        }
        for i, result in enumerate(search_results)
    ]

    backend = search_results[0].source if search_results else None
    return chunks_data, backend


def _build_retrieval_response(
    chunks_data: list[dict],
    query: str,
    backend: str | None,
    latency_ms: float,
    success: bool,
    error_msg: str | None = None,
) -> str:
    """Build JSON response for retrieval agent.

    Args:
        chunks_data: Retrieved document chunks
        query: Search query string
        backend: Search backend used
        latency_ms: Execution time in milliseconds
        success: Whether search succeeded
        error_msg: Optional error message

    Returns:
        JSON-serialized response
    """
    search_metadata: dict[str, object] = {
        "success": success,
        "latency_ms": latency_ms,
        "backend": backend,
    }

    if error_msg:
        search_metadata["error"] = error_msg

    response: dict[str, object] = {
        "chunks": chunks_data,
        "query": query,
        "total_retrieved": len(chunks_data),
        "search_metadata": search_metadata,
    }

    return json.dumps(response)


def _extract_top_k(context: dict | None) -> int:
    """Extract top_k parameter from context.

    Args:
        context: Optional context data

    Returns:
        Number of results to retrieve (default 5)
    """
    top_k = 5
    if context and isinstance(context, dict):
        top_k = context.get("top_k", 5)
    return top_k


def _log_query_reformulation(original_query: str, reformulated_query: str) -> None:
    """Log query reformulation if query changed.

    Args:
        original_query: Original query string
        reformulated_query: Reformulated query string
    """
    if reformulated_query != original_query:
        logger.debug(
            "Query reformulated",
            extra={
                "original": original_query[:80],
                "reformulated": reformulated_query[:80],
            },
        )


@tool
async def retrieval_agent(instruction: str, context: dict | None = None) -> str:
    """Retrieval Agent: Search financial document knowledge base.

    Story 3.2 AC1-AC3: Wraps Epic 2 multi-index search to enable
    agentic workflows to retrieve relevant financial documents.

    Uses AWS Strands @tool decorator for agent coordination.
    Returns JSON-serialized DocumentChunk list with citations and metadata.

    Args:
        instruction: Task instruction containing the search query
        context: Optional context data from previous agents (unused for retrieval)

    Returns:
        JSON string containing:
        {
            "chunks": [DocumentChunk dicts with content, id, source, page_number, metadata],
            "query": Original query string,
            "total_retrieved": Number of chunks returned,
            "search_metadata": {
                "latency_ms": Search execution time,
                "backend": Search backend used ("vector", "sql", or "hybrid"),
                "success": True/False
            }
        }

    Error Handling (AC2):
        If search fails, returns JSON with:
        {
            "chunks": [],
            "query": Original query,
            "total_retrieved": 0,
            "search_metadata": {
                "success": False,
                "error": Error description,
                "backend": null
            }
        }

    Performance Constraints (NFR5):
        - Target execution time: <3s p50, <8s p95
        - Log latency via search_metadata.latency_ms for monitoring
    """
    start_time = time.time()
    success = False
    error_msg = None
    chunks_data: list[dict] = []
    backend = None
    query = instruction

    try:
        top_k = _extract_top_k(context)

        original_query = query
        query = _reformulate_query(query)

        _log_query_reformulation(original_query, query)

        chunks_data, backend = await _execute_search(query, top_k)
        success = True

    except MultiIndexSearchError as e:
        error_msg = f"Multi-index search failed: {str(e)}"
        logger.error(
            "Retrieval agent search failed",
            extra={"query": query[:100], "error": error_msg},
            exc_info=True,
        )
        success = False

    except Exception as e:
        error_msg = f"Retrieval agent error: {str(e)}"
        logger.error(
            "Retrieval agent error",
            extra={"query": query[:100], "error": error_msg},
            exc_info=True,
        )
        success = False

    finally:
        latency_ms = round((time.time() - start_time) * 1000, 2)

    if not success or latency_ms > 4000:
        logger.warning(
            "Retrieval agent slow or failed",
            extra={
                "chunks_count": len(chunks_data),
                "latency_ms": latency_ms,
                "success": success,
            },
        )

    return _build_retrieval_response(chunks_data, query, backend, latency_ms, success, error_msg)
