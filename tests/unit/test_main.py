"""Unit tests for RAGLite MCP server (raglite/main.py).

Tests MCP server initialization, tool definitions, error handling,
and logging without requiring actual MCP client connection.
"""

from unittest.mock import AsyncMock, patch

import pytest

from raglite.main import (
    DocumentProcessingError,
    ingest_financial_document,
    mcp,
    query_financial_documents,
)
from raglite.retrieval.search import QueryError
from raglite.shared.models import (
    DocumentMetadata,
    QueryRequest,
    QueryResponse,
    QueryResult,
)


class TestMCPServerInitialization:
    """Test MCP server initialization and configuration."""

    def test_mcp_server_exists(self):
        """Test MCP server instance exists with correct name."""
        assert mcp is not None
        assert mcp.name == "RAGLite"

    def test_mcp_server_tools_registered(self):
        """Test both MCP tools are registered."""
        # FastMCP registers tools as FunctionTool objects with .fn attribute
        assert hasattr(ingest_financial_document, "fn")
        assert hasattr(query_financial_documents, "fn")
        assert callable(ingest_financial_document.fn)
        assert callable(query_financial_documents.fn)


class TestIngestFinancialDocumentTool:
    """Test ingest_financial_document MCP tool."""

    @pytest.mark.asyncio
    async def test_ingest_tool_success(self):
        """Test successful document ingestion returns DocumentMetadata."""
        # Mock Story 1.2 ingestion function
        mock_metadata = DocumentMetadata(
            filename="Q3_2023_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2023-10-13T10:00:00Z",
            page_count=10,
            source_path="/data/Q3_2023_Report.pdf",
            chunk_count=42,
        )

        with patch("raglite.main.ingest_document", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.return_value = mock_metadata

            result = await ingest_financial_document.fn("/data/Q3_2023_Report.pdf")

            assert isinstance(result, DocumentMetadata)
            assert result.filename == "Q3_2023_Report.pdf"
            assert result.chunk_count == 42
            assert result.page_count == 10
            mock_ingest.assert_called_once_with("/data/Q3_2023_Report.pdf")

    @pytest.mark.asyncio
    async def test_ingest_tool_file_not_found(self):
        """Test ingestion with missing file raises DocumentProcessingError."""
        with patch("raglite.main.ingest_document", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.side_effect = FileNotFoundError("File not found")

            with pytest.raises(DocumentProcessingError) as exc_info:
                await ingest_financial_document.fn("/nonexistent/document.pdf")

            assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_ingest_tool_processing_error(self):
        """Test ingestion with processing error raises DocumentProcessingError."""
        with patch("raglite.main.ingest_document", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.side_effect = Exception("PDF parsing failed")

            with pytest.raises(DocumentProcessingError) as exc_info:
                await ingest_financial_document.fn("/data/corrupt.pdf")

            assert "Failed to ingest" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ingest_tool_structured_logging(self, caplog):
        """Test ingestion tool logs with structured extra context."""
        mock_metadata = DocumentMetadata(
            filename="test.pdf",
            doc_type="PDF",
            ingestion_timestamp="2023-10-13T10:00:00Z",
            page_count=5,
            chunk_count=20,
        )

        with patch("raglite.main.ingest_document", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.return_value = mock_metadata

            with caplog.at_level("INFO"):
                await ingest_financial_document.fn("/data/test.pdf")

            # Verify structured logging occurred
            assert any("Ingesting document" in record.message for record in caplog.records)
            assert any("Ingestion complete" in record.message for record in caplog.records)


class TestQueryFinancialDocumentsTool:
    """Test query_financial_documents MCP tool."""

    @pytest.mark.asyncio
    async def test_query_tool_success(self):
        """Test successful query returns QueryResponse with cited results."""
        # Mock Story 1.7 search results
        mock_search_results = [
            QueryResult(
                score=0.95,
                text="Q3 revenue was $10M.",
                source_document="Q3_2023.pdf",
                page_number=3,
                chunk_index=5,
                word_count=20,
            ),
            QueryResult(
                score=0.87,
                text="Operating expenses decreased 15%.",
                source_document="Q3_2023.pdf",
                page_number=7,
                chunk_index=12,
                word_count=18,
            ),
        ]

        # Mock Story 1.8 cited results (with appended citations)
        mock_cited_results = [
            QueryResult(
                score=0.95,
                text="Q3 revenue was $10M.\n\n[Source: Q3_2023.pdf, Page 3, Chunk 5]",
                source_document="Q3_2023.pdf",
                page_number=3,
                chunk_index=5,
                word_count=20,
            ),
            QueryResult(
                score=0.87,
                text="Operating expenses decreased 15%.\n\n[Source: Q3_2023.pdf, Page 7, Chunk 12]",
                source_document="Q3_2023.pdf",
                page_number=7,
                chunk_index=12,
                word_count=18,
            ),
        ]

        with (
            patch("raglite.main.search_documents", new_callable=AsyncMock) as mock_search,
            patch("raglite.main.generate_citations", new_callable=AsyncMock) as mock_citations,
        ):
            mock_search.return_value = mock_search_results
            mock_citations.return_value = mock_cited_results

            request = QueryRequest(query="What was Q3 revenue?", top_k=5)
            response = await query_financial_documents.fn(request)

            assert isinstance(response, QueryResponse)
            assert response.query == "What was Q3 revenue?"
            assert len(response.results) == 2
            assert "[Source:" in response.results[0].text
            assert response.results[0].score == 0.95
            assert response.retrieval_time_ms >= 0

            mock_search.assert_called_once_with("What was Q3 revenue?", 5)
            mock_citations.assert_called_once_with(mock_search_results)

    @pytest.mark.asyncio
    async def test_query_tool_empty_query(self):
        """Test query with empty string raises QueryError."""
        request = QueryRequest(query="", top_k=5)

        with pytest.raises(QueryError) as exc_info:
            await query_financial_documents.fn(request)

        assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_query_tool_whitespace_only_query(self):
        """Test query with whitespace-only string raises QueryError."""
        request = QueryRequest(query="   \n\t  ", top_k=5)

        with pytest.raises(QueryError) as exc_info:
            await query_financial_documents.fn(request)

        assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_query_tool_search_error(self):
        """Test query with search failure re-raises QueryError."""
        with patch("raglite.main.search_documents", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = QueryError("Qdrant connection failed")

            request = QueryRequest(query="valid query", top_k=5)

            with pytest.raises(QueryError) as exc_info:
                await query_financial_documents.fn(request)

            assert "Qdrant connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_query_tool_unexpected_error(self):
        """Test query with unexpected error wraps in QueryError."""
        with patch("raglite.main.search_documents", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("Unexpected failure")

            request = QueryRequest(query="valid query", top_k=5)

            with pytest.raises(QueryError) as exc_info:
                await query_financial_documents.fn(request)

            assert "Query failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_query_tool_structured_logging(self, caplog):
        """Test query tool logs with structured extra context."""
        mock_results = [
            QueryResult(
                score=0.95,
                text="Test result.\n\n[Source: test.pdf, Page 1, Chunk 0]",
                source_document="test.pdf",
                page_number=1,
                chunk_index=0,
                word_count=10,
            )
        ]

        with (
            patch("raglite.main.search_documents", new_callable=AsyncMock) as mock_search,
            patch("raglite.main.generate_citations", new_callable=AsyncMock) as mock_citations,
        ):
            mock_search.return_value = mock_results
            mock_citations.return_value = mock_results

            request = QueryRequest(query="test query", top_k=5)

            with caplog.at_level("INFO"):
                await query_financial_documents.fn(request)

            # Verify structured logging occurred
            assert any("Query received" in record.message for record in caplog.records)
            assert any("Query complete" in record.message for record in caplog.records)


class TestDocumentProcessingError:
    """Test custom DocumentProcessingError exception."""

    def test_exception_creation(self):
        """Test DocumentProcessingError can be raised with message."""
        with pytest.raises(DocumentProcessingError) as exc_info:
            raise DocumentProcessingError("Test error message")

        assert "Test error message" in str(exc_info.value)

    def test_exception_inheritance(self):
        """Test DocumentProcessingError inherits from Exception."""
        assert issubclass(DocumentProcessingError, Exception)
