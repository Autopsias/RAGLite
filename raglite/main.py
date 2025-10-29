"""RAGLite MCP Server - Model Context Protocol entry point.

This module implements the FastMCP server that exposes RAGLite capabilities
to MCP clients (Claude Desktop, etc.). Provides two core tools:
  1. ingest_financial_document - Ingest PDF/Excel documents
  2. query_financial_documents - Query documents using natural language

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

from raglite.ingestion.pipeline import ingest_document
from raglite.retrieval.attribution import generate_citations
from raglite.retrieval.multi_index_search import MultiIndexSearchError, multi_index_search
from raglite.retrieval.search import QueryError
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import DocumentMetadata, QueryRequest, QueryResponse

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
    mcp.run()
