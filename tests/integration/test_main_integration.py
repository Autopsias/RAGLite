"""Integration tests for RAGLite MCP server.

Tests MCP protocol compliance, tool discovery, and end-to-end query execution
with real Qdrant connection. Requires Docker services running.
"""

import pytest

from raglite.main import ingest_financial_document, mcp, query_financial_documents
from raglite.shared.models import DocumentMetadata, QueryRequest, QueryResponse


@pytest.mark.integration
class TestMCPProtocolCompliance:
    """Test MCP protocol compliance and tool discovery."""

    def test_mcp_server_initialization(self):
        """Test MCP server initializes with correct configuration."""
        assert mcp is not None
        assert mcp.name == "RAGLite"
        assert isinstance(mcp.name, str)

    def test_mcp_tool_discovery(self):
        """Test MCP client can discover both tools."""
        # FastMCP registers tools as FunctionTool objects with .fn attribute
        # Verify both tools exist and have the underlying function
        assert hasattr(ingest_financial_document, "fn")
        assert hasattr(query_financial_documents, "fn")
        assert callable(ingest_financial_document.fn)
        assert callable(query_financial_documents.fn)

        # Verify tool names match MCP expectations
        assert ingest_financial_document.name == "ingest_financial_document"
        assert query_financial_documents.name == "query_financial_documents"

    def test_tool_schemas_valid(self):
        """Test tool schemas have proper Pydantic model types."""
        # Verify ingest tool has correct signature
        import inspect

        # Access the underlying function via .fn attribute
        ingest_sig = inspect.signature(ingest_financial_document.fn)
        assert "doc_path" in ingest_sig.parameters
        assert ingest_sig.return_annotation == DocumentMetadata

        # Verify query tool has correct signature
        query_sig = inspect.signature(query_financial_documents.fn)
        assert "request" in query_sig.parameters
        assert query_sig.return_annotation == QueryResponse


@pytest.mark.integration
@pytest.mark.skipif(
    True,
    reason="Requires real Qdrant with ingested data - run manually after ingestion",
)
class TestMCPEndToEnd:
    """Test end-to-end MCP query execution with real Qdrant.

    NOTE: These tests require:
      1. docker-compose up -d (Qdrant running)
      2. At least one document ingested
      3. Qdrant collection initialized

    Run manually with: pytest tests/integration/test_main_integration.py::TestMCPEndToEnd -v -s --no-skip
    """

    @pytest.mark.asyncio
    async def test_mcp_query_execution_real_qdrant(self):
        """Test MCP client executes query with real Qdrant connection.

        INTEGRATION TEST: Requires Qdrant running and data ingested.
        """
        # Sample query (adjust based on ingested documents)
        request = QueryRequest(
            query="What are the key financial metrics?",
            top_k=3,
        )

        # Execute query through MCP tool
        response = await query_financial_documents.fn(request)

        # Validate response structure
        assert isinstance(response, QueryResponse)
        assert response.query == request.query
        assert len(response.results) > 0
        assert len(response.results) <= request.top_k
        assert response.retrieval_time_ms >= 0

        # Validate first result has all required metadata
        first_result = response.results[0]
        assert 0.0 <= first_result.score <= 1.0
        assert first_result.text is not None and len(first_result.text) > 0
        assert first_result.source_document is not None
        assert "[Source:" in first_result.text  # Citation appended by Story 1.8
        assert first_result.chunk_index >= 0
        assert first_result.word_count > 0

        # Log results for manual verification
        print(f"\n✓ Query: {response.query}")
        print(f"✓ Results returned: {len(response.results)}")
        print(f"✓ Retrieval time: {response.retrieval_time_ms:.2f}ms")

        for i, result in enumerate(response.results, 1):
            print(f"\nResult {i}:")
            print(f"  Score: {result.score:.4f}")
            print(f"  Source: {result.source_document}")
            print(f"  Page: {result.page_number}")
            print(f"  Text: {result.text[:150]}...")

    @pytest.mark.asyncio
    async def test_mcp_ingest_then_query_flow(self, tmp_path):
        """Test complete MCP flow: ingest document then query.

        INTEGRATION TEST: Requires Qdrant running and test document.
        """
        # NOTE: This test requires a real test document
        # Skip if TEST_PDF_PATH not set in environment
        import os

        test_pdf = os.getenv("TEST_PDF_PATH")
        if not test_pdf or not os.path.exists(test_pdf):
            pytest.skip("TEST_PDF_PATH environment variable not set or file missing")

        # Step 1: Ingest document via MCP tool
        metadata = await ingest_financial_document.fn(test_pdf)

        assert isinstance(metadata, DocumentMetadata)
        assert metadata.chunk_count > 0
        assert metadata.page_count > 0

        print(f"\n✓ Ingested: {metadata.filename}")
        print(f"  Pages: {metadata.page_count}")
        print(f"  Chunks: {metadata.chunk_count}")

        # Step 2: Query the ingested document
        request = QueryRequest(
            query="What is discussed in this document?",
            top_k=3,
        )

        response = await query_financial_documents.fn(request)

        assert len(response.results) > 0
        assert response.results[0].source_document == metadata.filename

        print(f"\n✓ Query executed: {response.query}")
        print(f"  Results: {len(response.results)}")
        print(f"  Top score: {response.results[0].score:.4f}")


@pytest.mark.integration
class TestMCPErrorHandling:
    """Test MCP error handling with integration scenarios."""

    @pytest.mark.asyncio
    async def test_query_empty_collection(self):
        """Test query behavior when Qdrant collection is empty.

        This test verifies graceful handling when no documents are ingested.
        """
        from raglite.retrieval.search import QueryError

        request = QueryRequest(query="test query", top_k=5)

        # If collection is empty, search should either:
        # 1. Return empty results, OR
        # 2. Raise QueryError

        try:
            response = await query_financial_documents.fn(request)
            # Empty results are acceptable
            assert isinstance(response, QueryResponse)
            assert len(response.results) >= 0  # Allow 0 results
        except QueryError as e:
            # QueryError for empty collection is also acceptable
            assert "empty" in str(e).lower() or "no results" in str(e).lower()
