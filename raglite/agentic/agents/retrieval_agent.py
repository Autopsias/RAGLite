"""Retrieval Agent for agentic workflows.

Story 3.2 AC1-AC3: Implements a @tool decorator-based retrieval agent
that wraps the Epic 2 multi-index search, enabling the orchestrator
to search document knowledge bases.
"""

import json
import time

from strands import tool

from raglite.retrieval.multi_index_search import (
    MultiIndexSearchError,
    multi_index_search,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


@tool
async def retrieval_agent(query: str, top_k: int = 5) -> str:
    """Retrieval Agent: Search financial document knowledge base.

    Story 3.2 AC1-AC3: Wraps Epic 2 multi-index search to enable
    agentic workflows to retrieve relevant financial documents.

    Uses AWS Strands @tool decorator for agent coordination.
    Returns JSON-serialized DocumentChunk list with citations and metadata.

    Args:
        query: Natural language search query (required)
        top_k: Number of document chunks to retrieve (default: 5)

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
    chunks_data = []
    backend = None

    try:
        logger.info(
            "Retrieval agent called",
            extra={"query": query[:100], "top_k": top_k},
        )

        # Call Epic 2 multi-index search (AC3: direct function call, no duplication)
        search_results = await multi_index_search(query, top_k=top_k)

        # Convert SearchResult to DocumentChunk JSON-serializable dicts
        # Preserve all citation metadata (AC2): page numbers, doc IDs, scores, section types
        chunks_data = [
            {
                "id": result.document_id,
                "content": result.text,
                "source": result.source,
                "page_number": result.page_number,
                "chunk_index": i,  # Preserve result ranking
                "metadata": {
                    **result.metadata,  # Preserve all Epic 2 metadata
                    "score": result.score,  # Add relevance score for ranking
                    "search_source": result.source,  # Include backend used
                },
            }
            for i, result in enumerate(search_results)
        ]

        success = True
        backend = search_results[0].source if search_results else None

        logger.info(
            "Retrieval agent completed",
            extra={
                "query": query[:100],
                "chunks_returned": len(chunks_data),
                "success": True,
                "backend": backend,
            },
        )

    except MultiIndexSearchError as e:
        # Epic 2 search failed - return empty results with error metadata (AC2)
        error_msg = f"Multi-index search failed: {str(e)}"
        logger.error(
            "Retrieval agent search failed",
            extra={
                "query": query[:100],
                "error": error_msg,
            },
            exc_info=True,
        )
        success = False

    except Exception as e:
        # Unexpected error - graceful degradation (NFR24)
        error_msg = f"Retrieval agent error: {str(e)}"
        logger.error(
            "Retrieval agent error",
            extra={
                "query": query[:100],
                "error": error_msg,
            },
            exc_info=True,
        )
        success = False

    finally:
        latency_ms = round((time.time() - start_time) * 1000, 2)

    # Build return JSON (AC2: JSON-serialized output for Strands)
    search_metadata: dict[str, object] = {
        "success": success,
        "latency_ms": latency_ms,
        "backend": backend,
    }

    # Add error metadata if search failed
    if error_msg:
        search_metadata["error"] = error_msg

    response: dict[str, object] = {
        "chunks": chunks_data,
        "query": query,
        "total_retrieved": len(chunks_data),
        "search_metadata": search_metadata,
    }

    logger.info(
        "Retrieval agent returning results",
        extra={
            "chunks_count": len(chunks_data),
            "latency_ms": latency_ms,
            "success": success,
        },
    )

    # Return JSON string (Strands requirement: @tool functions return strings)
    return json.dumps(response)
