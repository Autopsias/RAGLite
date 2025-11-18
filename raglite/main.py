"""RAGLite MCP Server - Model Context Protocol entry point.

This module implements the FastMCP server that exposes RAGLite capabilities
to MCP clients (Claude Desktop, etc.). Provides three core tools:
  1. ingest_financial_document - Ingest PDF/Excel documents
  2. query_financial_documents - Query documents using natural language (Epic 1-2)
  3. analytical_query_financial_documents - Advanced multi-step analytical queries (Epic 3)

The server follows standard MCP pattern: tools return raw data (chunks with metadata),
and the LLM client (Claude) synthesizes natural language answers.

Example:
    Start server locally:
    $ uv run python -m raglite.main

    Connect Claude Desktop to:
    - Server Name: RAGLite
    - Transport: stdio
"""

import time

from fastmcp import FastMCP

from raglite.agentic.fallback import FallbackResponse, handle_workflow_failure
from raglite.agentic.orchestrator import WorkflowExecutor
from raglite.agentic.planner import QueryComplexity, classify_query_complexity, decompose_query
from raglite.ingestion.pipeline import ingest_document
from raglite.retrieval.attribution import generate_citations
from raglite.retrieval.multi_index_search import MultiIndexSearchError, multi_index_search
from raglite.retrieval.search import QueryError
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import (
    AnalyticalQueryRequest,
    AnalyticalQueryResponse,
    DocumentMetadata,
    QueryRequest,
    QueryResponse,
)

# Initialize structured logger
logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP("RAGLite")


class DocumentProcessingError(Exception):
    """Raised when document ingestion or processing fails.

    This exception is raised for any failure during document processing,
    including file not found, parsing errors, embedding generation failures,
    and vector storage errors.
    """

    pass


@mcp.tool()
async def ingest_financial_document(doc_path: str) -> DocumentMetadata:
    """Ingest financial PDF or Excel document into RAGLite knowledge base.

    Processes the document through the complete ingestion pipeline:
      1. Extract text/tables (Docling for PDF, openpyxl for Excel)
      2. Chunk content into semantic units
      3. Generate embeddings (Fin-E5 model)
      4. Store vectors in Qdrant with metadata

    **Performance & Timeout Considerations:**
      - Small files (<10 pages): ~2-5 minutes (MCP timeout safe)
      - Large files (>10 pages): May timeout in MCP clients
      - Processing time: ~20-30 seconds per page (Docling + embedding generation)

    **For Large Files:** Use CLI ingestion to avoid MCP timeouts:
        ```bash
        cd /path/to/RAGLite
        uv run python -c "
        import asyncio
        from raglite.ingestion.pipeline import ingest_document
        asyncio.run(ingest_document('/path/to/large.pdf'))
        "
        ```
        Then query via MCP after ingestion completes.

    Args:
        doc_path: Absolute or relative path to document file (.pdf, .xlsx, .xls)

    Returns:
        DocumentMetadata with ingestion results including:
          - filename: Original document name
          - doc_type: PDF or Excel
          - ingestion_timestamp: ISO8601 timestamp
          - page_count: Number of pages/sheets
          - chunk_count: Number of chunks created

    Raises:
        DocumentProcessingError: If ingestion fails (file not found, parsing error,
            embedding generation failure, or storage error)

    Example:
        >>> metadata = await ingest_financial_document("/data/Q3_2023_Report.pdf")
        >>> print(f"Ingested {metadata.chunk_count} chunks from {metadata.filename}")

    Note:
        Epic 4 (Production Readiness) will add async job queue for large file ingestion
        with progress tracking. See docs/future-enhancements.md for research roadmap.
    """
    logger.info("Ingesting document", extra={"path": doc_path})

    try:
        # Call Story 1.2 ingestion pipeline
        start_time = time.perf_counter()
        metadata = await ingest_document(doc_path)
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "Ingestion complete",
            extra={
                "doc_id": metadata.filename,
                "doc_type": metadata.doc_type,
                "chunks": metadata.chunk_count,
                "pages": metadata.page_count,
                "duration_ms": f"{duration_ms:.2f}",
            },
        )
        return metadata

    except FileNotFoundError as e:
        logger.error(
            "Document not found",
            extra={"path": doc_path, "error": str(e)},
            exc_info=True,
        )
        raise DocumentProcessingError(f"Document not found: {doc_path}") from e

    except Exception as e:
        logger.error(
            "Ingestion failed",
            extra={"path": doc_path, "error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise DocumentProcessingError(f"Failed to ingest {doc_path}: {e}") from e


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

    # Validate query
    if not request.query or not request.query.strip():
        error_msg = "Query cannot be empty"
        logger.warning("Empty query rejected", extra={"query": request.query})
        raise QueryError(error_msg)

    try:
        # Story 2.7: Call multi-index search (vector + SQL routing)
        start_time = time.perf_counter()
        search_results = await multi_index_search(request.query, top_k=request.top_k)
        search_duration_ms = (time.perf_counter() - start_time) * 1000

        # Convert SearchResult to QueryResult for backward compatibility
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

        # Call Story 1.8 citation generation
        cited_results = await generate_citations(query_results)
        total_duration_ms = (time.perf_counter() - start_time) * 1000

        # AC4: Observability logging (classification, index usage, timing)
        retrieval_sources = {r.source for r in search_results}
        logger.info(
            "Query complete (multi-index)",
            extra={
                "query": request.query,
                "results_count": len(cited_results),
                "retrieval_sources": list(
                    retrieval_sources
                ),  # ["vector"], ["sql"], or ["vector", "sql", "hybrid"]
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
        # Story 2.7: Multi-index search error
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
        # Re-raise QueryError (already logged in search.py)
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
    """Query financial documents using multi-step agentic workflow orchestration.

    Story 3.5 AC7: Advanced analytical queries using workflow decomposition and
    specialized agent coordination (Retrieval → Analysis → Synthesis).

    This tool handles complex analytical queries that require multi-step reasoning:
    - YoY/QoQ growth calculations
    - Variance analysis and driver identification
    - Trend analysis over multiple periods
    - Comparative financial analysis

    Workflow pipeline:
      1. Classify query complexity (simple vs analytical)
      2. Decompose analytical queries into sub-tasks with dependencies
      3. Execute workflow with specialized agents (retrieval, analysis, synthesis)
      4. Synthesize final answer with workflow metadata
      5. Graceful degradation to basic search if workflow fails (AC8)

    Args:
        request: Analytical query parameters containing:
          - query: Natural language analytical query
          - top_k: Number of results per retrieval step (default: 5)

    Returns:
        AnalyticalQueryResponse containing:
          - answer: Synthesized natural language answer
          - complexity: Query complexity classification ("simple" or "analytical")
          - workflow_metadata: Execution details:
              * task_count: Number of workflow tasks executed
              * execution_time_ms: Total workflow execution time
              * workflow_pattern: Pattern used (yoy_growth, variance_analysis, etc.)
              * fallback_tier: Quality tier ("full", "partial", "epic1_fallback")
          - confidence: Answer confidence level ("high", "medium", "low")
          - limitations: List of caveats or limitations (empty for full workflow)

    Raises:
        QueryError: If query is empty or invalid

    Example - YoY Growth Analysis:
        >>> request = AnalyticalQueryRequest(
        ...     query="Calculate YoY revenue growth from 2022 to 2023",
        ...     top_k=5
        ... )
        >>> response = await analytical_query_financial_documents(request)
        >>> print(response.answer)
        "Revenue grew 15.3% year-over-year from $245M in 2022 to $283M in 2023..."
        >>> print(response.workflow_metadata)
        {
            "task_count": 4,
            "execution_time_ms": 2847,
            "workflow_pattern": "yoy_growth",
            "fallback_tier": "full"
        }

    Example - Variance Analysis:
        >>> request = AnalyticalQueryRequest(
        ...     query="Explain the variance in Q3 operating expenses"
        ... )
        >>> response = await analytical_query_financial_documents(request)
        >>> print(response.answer)
        "Q3 operating expenses increased by $12M (8.5%)..."

    Example - Comparative Analysis:
        >>> request = AnalyticalQueryRequest(
        ...     query="Compare Q3 2023 revenue with Q3 2024 revenue"
        ... )
        >>> response = await analytical_query_financial_documents(request)
        >>> print(response.answer)
        "Q3 2024 revenue was $283M compared to $245M in Q3 2023..."
        >>> print(response.reasoning_steps)
        ["1. Classified query as analytical (comparative pattern)",
         "2. Retrieved Q3 2023 financial documents",
         "3. Retrieved Q3 2024 financial documents",
         "4. Performed comparative analysis",
         "5. Synthesized final answer from 4 workflow tasks"]

    Note - Graceful Degradation (AC8):
        If the workflow fails (timeout, agent error), the system automatically
        falls back to Epic 1 basic retrieval, ensuring users always get a response.
        The fallback_tier field indicates the quality level:
        - "full": All agents succeeded
        - "partial": Some agents succeeded, partial answer provided
        - "epic1_fallback": Workflow failed, basic search results returned
    """
    logger.info(
        "Analytical query received",
        extra={
            "query": request.query,
            "top_k": request.top_k,
        },
    )

    # Validate query
    if not request.query or not request.query.strip():
        error_msg = "Query cannot be empty"
        logger.warning("Empty analytical query rejected", extra={"query": request.query})
        raise QueryError(error_msg)

    workflow_start_time = time.perf_counter()

    try:
        # Step 1: Classify query complexity (AC1)
        complexity = await classify_query_complexity(request.query)

        logger.info(
            "Query classified",
            extra={"query": request.query, "complexity": complexity},
        )

        # Story 3.6 AC3: Conditional routing - simple queries to Epic 2, analytical to Epic 3
        if complexity == QueryComplexity.SIMPLE:
            logger.info(
                "Routing simple query to Epic 2 basic retrieval",
                extra={"query": request.query, "complexity": complexity},
            )

            # Route to Epic 2 basic retrieval tool
            basic_request = QueryRequest(query=request.query, top_k=request.top_k)
            basic_response = await query_financial_documents.fn(basic_request)

            workflow_duration_ms = (time.perf_counter() - workflow_start_time) * 1000

            # Story 3.6 AC4: Build reasoning steps for transparency
            reasoning_steps = [
                "1. Classified query as simple (direct retrieval)",
                f"2. Retrieved {len(basic_response.results)} relevant documents via vector search",
                "3. Ranked results by similarity score",
            ]

            # Story 3.6 AC6: Extract source citations from results
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

            # Convert QueryResponse to AnalyticalQueryResponse format
            # Synthesize answer from top results
            answer_parts = ["Based on the retrieved documents:\n"]
            for i, result in enumerate(basic_response.results[:3], 1):
                # Truncate long results for summary
                text_preview = result.text[:200] + "..." if len(result.text) > 200 else result.text
                answer_parts.append(f"{i}. {text_preview}")

            return AnalyticalQueryResponse(
                answer="\n".join(answer_parts),
                complexity=complexity.value,
                workflow_metadata={
                    "task_count": 1,
                    "execution_time_ms": int(workflow_duration_ms),
                    "workflow_pattern": "simple_retrieval",
                    "fallback_tier": "epic2_routing",
                },
                confidence="high",
                limitations=[],
                reasoning_steps=reasoning_steps,
                sources=sources,
            )

        # Analytical queries continue with Epic 3 workflow orchestration
        # Step 2: Decompose query into workflow plan (AC2)
        plan = await decompose_query(request.query, complexity)

        logger.info(
            "Query decomposed",
            extra={
                "query": request.query,
                "task_count": len(plan.tasks),
                "pattern": plan.metadata.get("pattern", "unknown"),
            },
        )

        # Step 3: Execute workflow with specialized agents (AC3, AC4, AC5)
        executor = WorkflowExecutor()
        results = await executor.execute_workflow(plan)

        workflow_duration_ms = (time.perf_counter() - workflow_start_time) * 1000

        # Step 4: Extract final synthesis result
        synthesis_result = next(
            (r for r in reversed(results) if r.success and r.agent_type == "synthesis"),
            None,
        )

        if synthesis_result:
            # Full workflow succeeded
            answer = str(synthesis_result.result)
            fallback_tier = "full"
            confidence = "high"
            limitations: list[str] = []

            # Story 3.6 AC4: Build reasoning steps from workflow execution
            reasoning_steps = []
            pattern = plan.metadata.get("pattern", "unknown")
            reasoning_steps.append(f"1. Classified query as analytical ({pattern} pattern)")

            # Add retrieval steps
            retrieval_results = [r for r in results if r.agent_type == "retrieval" and r.success]
            for i, r in enumerate(retrieval_results, start=2):
                task_desc = next(
                    (t.instruction for t in plan.tasks if t.task_id == r.task_id), "retrieval task"
                )
                # Extract document count if available in result
                doc_count = len(r.result) if isinstance(r.result, list) else "relevant"
                reasoning_steps.append(f"{i}. Retrieved {doc_count} documents: {task_desc}")

            # Add analysis steps
            analysis_results = [r for r in results if r.agent_type == "analysis" and r.success]
            step_num = len(reasoning_steps) + 1
            for r in analysis_results:
                task_desc = next(
                    (t.instruction for t in plan.tasks if t.task_id == r.task_id), "analysis task"
                )
                reasoning_steps.append(f"{step_num}. Performed analysis: {task_desc}")
                step_num += 1

            # Add synthesis step
            task_count = len(results)
            reasoning_steps.append(
                f"{step_num}. Synthesized final answer from {task_count} workflow tasks"
            )

            # Story 3.6 AC6: Extract source citations from retrieval results
            sources = []
            for r in retrieval_results:
                if isinstance(r.result, list):
                    # Extract sources from retrieval results (SearchResult or QueryResult objects)
                    for doc in r.result:
                        if hasattr(doc, "document_id"):
                            # SearchResult from multi_index_search
                            has_page = hasattr(doc, "page_number") and doc.page_number is not None
                            page_ref = f" (page {doc.page_number})" if has_page else ""
                            source = f"{doc.document_id}{page_ref}"
                        elif hasattr(doc, "source_document"):
                            # QueryResult from query_financial_documents
                            has_page_num = doc.page_number is not None
                            page_ref = f" (page {doc.page_number})" if has_page_num else ""
                            source = f"{doc.source_document}{page_ref}"
                        else:
                            continue

                        if source not in sources:  # Deduplicate
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
            # No synthesis result - partial failure
            # AC8: Graceful degradation
            raise RuntimeError("No synthesis result available from workflow")

    except Exception as e:
        # AC8: Graceful degradation - handle workflow failure
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

        # Get partial results if available
        partial_results = []
        if "results" in locals():
            partial_results = results

        # Call fallback handler (AC8: Task 4.2, 4.3, 4.4)
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

        # Story 3.6 AC4: Build reasoning steps for fallback
        fallback_reasoning = [
            "1. Classified query as analytical",
            f"2. Attempted multi-step workflow ({len(partial_results)} tasks started)",
            f"3. Workflow failed: {str(e)[:100]}...",
            f"4. Gracefully degraded to {fallback_response.tier.value} tier",
        ]

        # Story 3.6 AC6: Extract sources from fallback response if available
        fallback_sources = []
        if hasattr(fallback_response, "sources"):
            fallback_sources = fallback_response.sources
        elif hasattr(fallback_response, "results"):
            # Extract from Epic 1 fallback results
            for result in fallback_response.results[:5]:
                if hasattr(result, "source_document"):
                    has_page = result.page_number is not None
                    page_ref = f" (page {result.page_number})" if has_page else ""
                    fallback_sources.append(f"{result.source_document}{page_ref}")

        # Return fallback response
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


# Module-level execution for direct startup
if __name__ == "__main__":
    logger.info(
        "Starting RAGLite MCP Server",
        extra={
            "qdrant_host": settings.qdrant_host,
            "qdrant_port": settings.qdrant_port,
            "collection": settings.qdrant_collection_name,
        },
    )
    mcp.run(show_banner=False)
