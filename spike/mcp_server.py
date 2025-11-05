"""FastMCP server for Week 0 Integration Spike.

Implements a minimal MCP server with a single query tool for testing
vector similarity search against Qdrant.
"""

from typing import Any

from config import (
    DEFAULT_TOP_K,
    EMBEDDING_MODEL,
    MCP_SERVER_PORT,
    QDRANT_COLLECTION_NAME,
    QDRANT_URL,
)
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Initialize FastMCP server
mcp = FastMCP("RAGLite-Spike")

# Global clients (initialized on first use)
_qdrant_client = None
_embedding_model = None


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client instance."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=QDRANT_URL, check_compatibility=False)
    return _qdrant_client


def get_embedding_model() -> SentenceTransformer:
    """Get or create embedding model instance."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


class QueryRequest(BaseModel):
    """Request model for financial document query."""

    query: str = Field(..., description="Natural language query about financial documents")
    top_k: int = Field(DEFAULT_TOP_K, description="Number of results to return (default: 5)")


class QueryResult(BaseModel):
    """Single search result from Qdrant."""

    score: float = Field(..., description="Similarity score (0-1, higher is better)")
    chunk_id: str = Field(..., description="Unique chunk identifier")
    text: str = Field(..., description="Retrieved text chunk")
    source_document: str = Field(..., description="Source document filename")
    page_number: int = Field(..., description="Page number in source document")
    chunk_index: int = Field(..., description="Chunk index in document")
    word_count: int = Field(..., description="Word count of chunk")


class QueryResponse(BaseModel):
    """Response model for query tool."""

    query: str = Field(..., description="Original query")
    results: list[QueryResult] = Field(..., description="List of search results")
    results_count: int = Field(..., description="Number of results returned")


# Business logic functions (can be tested directly)


async def execute_query(request: QueryRequest) -> QueryResponse:
    """
    Execute a financial document query (business logic).

    This performs vector similarity search against ingested financial documents.
    It generates an embedding for the query and retrieves the most similar document chunks.

    Args:
        request: Query parameters (query text and top_k)

    Returns:
        QueryResponse with similar document chunks and metadata
    """
    # Get clients
    qdrant = get_qdrant_client()
    model = get_embedding_model()

    # Generate query embedding
    query_embedding = model.encode([request.query])[0].tolist()

    # Search Qdrant using updated API with named vectors (Story 2.1 hybrid search)
    search_results = qdrant.query_points(
        collection_name=QDRANT_COLLECTION_NAME,
        query=query_embedding,
        using="text-dense",  # Named vector for hybrid search
        limit=request.top_k,
    ).points

    # Convert results to QueryResult objects
    results = [
        QueryResult(
            score=result.score,
            chunk_id=str(result.payload.get("chunk_id", "")),  # Convert to string
            text=result.payload.get("text", ""),
            source_document=result.payload.get("source_document", ""),
            page_number=result.payload.get("page_number") or 0,  # Handle None
            chunk_index=result.payload.get("chunk_index", 0),
            word_count=result.payload.get("word_count", 0),
        )
        for result in search_results
    ]

    return QueryResponse(query=request.query, results=results, results_count=len(results))


async def check_health() -> dict[str, Any]:
    """
    Check health status of server and dependencies (business logic).

    Returns:
        Dictionary with health status of Qdrant and embedding model
    """
    status = {
        "server": "healthy",
        "qdrant": "unknown",
        "embedding_model": "unknown",
        "collection": QDRANT_COLLECTION_NAME,
    }

    try:
        # Check Qdrant connection
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections()
        collection_names = [c.name for c in collections.collections]

        if QDRANT_COLLECTION_NAME in collection_names:
            collection_info = qdrant.get_collection(QDRANT_COLLECTION_NAME)
            status["qdrant"] = "healthy"
            status["collection_info"] = {
                "points_count": collection_info.points_count,
                "vector_dimension": collection_info.config.params.vectors.size,
                "distance_metric": collection_info.config.params.vectors.distance.name,
            }
        else:
            status["qdrant"] = "collection_not_found"

    except Exception as e:
        status["qdrant"] = f"error: {str(e)}"

    try:
        # Check embedding model
        model = get_embedding_model()
        test_embedding = model.encode(["test"])
        status["embedding_model"] = "healthy"
        status["embedding_dimension"] = len(test_embedding[0])

    except Exception as e:
        status["embedding_model"] = f"error: {str(e)}"

    return status


# MCP Tool wrappers


@mcp.tool()
async def query_financial_documents(request: QueryRequest) -> QueryResponse:
    """
    Query financial documents using natural language.

    This tool performs vector similarity search against ingested financial documents.
    It generates an embedding for the query and retrieves the most similar document chunks.

    Args:
        request: Query parameters (query text and top_k)

    Returns:
        QueryResponse with similar document chunks and metadata

    Example:
        >>> result = await query_financial_documents(
        ...     QueryRequest(query="What was the total revenue?", top_k=5)
        ... )
    """
    return await execute_query(request)


@mcp.tool()
async def health_check() -> dict[str, Any]:
    """
    Check health status of MCP server and dependencies.

    Returns:
        Dictionary with health status of Qdrant and embedding model
    """
    return await check_health()


if __name__ == "__main__":
    # Run the MCP server
    print("Starting RAGLite MCP Server...")
    print(f"Qdrant URL: {QDRANT_URL}")
    print(f"Collection: {QDRANT_COLLECTION_NAME}")
    print(f"Embedding Model: {EMBEDDING_MODEL}")
    print(f"Port: {MCP_SERVER_PORT}")
    print("\nAvailable tools:")
    print("  - query_financial_documents: Query financial docs via vector search")
    print("  - health_check: Check server health status")
    print("\nStarting server...\n")

    # Note: FastMCP handles server startup via CLI
    # Run with: mcp dev spike/mcp_server.py
    mcp.run()
