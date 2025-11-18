"""Unit tests for Retrieval Agent.

Story 3.2 AC4: Tests retrieval_agent in isolation using mocked multi_index_search
to prevent external dependencies and validate agent interface/format/error handling.

Test execution time target: <100ms each (framework overhead only, no real DB/LLM calls)
"""

# Check if strands is available
import importlib.util
import json
from unittest.mock import AsyncMock, patch

import pytest

from raglite.agentic.agents.retrieval_agent import retrieval_agent
from raglite.retrieval.multi_index_search import SearchResult

STRANDS_AVAILABLE = importlib.util.find_spec("strands") is not None


class TestRetrievalAgentInterface:
    """Test suite for retrieval agent interface validation (AC1)."""

    @pytest.mark.skipif(not STRANDS_AVAILABLE, reason="Strands not installed (deferred to Epic 3)")
    @pytest.mark.asyncio
    async def test_retrieval_agent_is_tool_decorated(self):
        """Verify @tool decorator applied to retrieval_agent function.

        AC1: Agent decorated with @tool decorator from AWS Strands
        """
        # Check that function has tool attribute (applied by @tool decorator)
        assert hasattr(retrieval_agent, "__wrapped__"), (
            "retrieval_agent must be decorated with @tool"
        )

    @pytest.mark.asyncio
    async def test_retrieval_agent_async_signature(self):
        """Verify async function signature matches Strands conventions.

        AC1: Agent signature follows Strands tool conventions
        """
        import inspect

        # Verify function is async (check __wrapped__ since @tool decorator wraps it)
        wrapped_fn = getattr(retrieval_agent, "__wrapped__", retrieval_agent)
        assert inspect.iscoroutinefunction(wrapped_fn), (
            "retrieval_agent must be async (check __wrapped__)"
        )

        # Verify parameters (use the decorated function's signature)
        sig = inspect.signature(retrieval_agent)
        params = list(sig.parameters.keys())
        assert "instruction" in params, "retrieval_agent must accept 'instruction' parameter"
        assert "context" in params, "retrieval_agent must accept 'context' parameter"

        # Verify default value for context
        assert sig.parameters["context"].default is None, "context default must be None"

    @pytest.mark.asyncio
    async def test_retrieval_agent_returns_json_string(self):
        """Verify retrieval_agent returns JSON string (Strands requirement).

        AC2: Output is JSON-serialized string for Strands compatibility
        """
        # Mock multi_index_search to return empty results
        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = []

            result = await retrieval_agent(instruction="test query", context={"top_k": 5})

            # Verify return type is string
            assert isinstance(result, str), f"Expected str, got {type(result)}"

            # Verify it's valid JSON
            parsed = json.loads(result)
            assert isinstance(parsed, dict), "JSON must be an object/dict"


class TestRetrievalAgentReturnFormat:
    """Test suite for retrieval agent output format validation (AC2)."""

    @pytest.mark.asyncio
    async def test_retrieval_agent_return_structure(self):
        """Verify JSON return structure with all required fields.

        AC2: Output contains chunks, query, total_retrieved, search_metadata
        """
        mock_results = [
            SearchResult(
                text="Annual revenue reached $5.2B",
                score=0.95,
                source="vector",
                metadata={"section": "Financial Overview"},
                document_id="doc_1",
                page_number=15,
            ),
            SearchResult(
                text="Operating expenses were $3.1B",
                score=0.92,
                source="vector",
                metadata={"section": "Financial Overview"},
                document_id="doc_1",
                page_number=15,
            ),
        ]

        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = mock_results

            result = await retrieval_agent(instruction="revenue query", context={"top_k": 5})
            parsed = json.loads(result)

            # Verify top-level structure
            assert "chunks" in parsed, "Response must contain 'chunks' field"
            assert "query" in parsed, "Response must contain 'query' field"
            assert "total_retrieved" in parsed, "Response must contain 'total_retrieved' field"
            assert "search_metadata" in parsed, "Response must contain 'search_metadata' field"

            # Verify counts
            assert len(parsed["chunks"]) == 2, "Should return 2 chunks"
            assert parsed["total_retrieved"] == 2, "total_retrieved should be 2"
            assert parsed["query"] == "revenue query", "Query should be preserved"

    @pytest.mark.asyncio
    async def test_retrieval_agent_chunk_format(self):
        """Verify DocumentChunk format with all citation metadata.

        AC2: Chunks include id, content, source, page_number, chunk_index, metadata
        AC2: Citations include page numbers, document IDs, scores, section types (NFR7)
        """
        mock_results = [
            SearchResult(
                text="Net profit margin improved to 18%",
                score=0.96,
                source="vector",
                metadata={"section": "Profitability Analysis", "chunk_index": 1},
                document_id="doc_1",
                page_number=18,
            ),
        ]

        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = mock_results

            result = await retrieval_agent(instruction="profit query", context={"top_k": 5})
            parsed = json.loads(result)

            chunk = parsed["chunks"][0]

            # Verify required fields
            assert chunk["id"] == "doc_1", "Chunk must have 'id' field (document_id)"
            assert chunk["content"] == "Net profit margin improved to 18%", (
                "Chunk must have 'content' field (text)"
            )
            assert chunk["source"] == "vector", "Chunk must have 'source' field"
            assert chunk["page_number"] == 18, "Chunk must have 'page_number' field"
            assert chunk["chunk_index"] == 0, (
                "Chunk must have 'chunk_index' field (ranking position)"
            )
            assert isinstance(chunk["metadata"], dict), "Chunk must have 'metadata' dict"

            # Verify citation metadata (NFR7: source attribution accuracy)
            assert "score" in chunk["metadata"], "Metadata must include 'score' (relevance)"
            assert "section" in chunk["metadata"], "Metadata must preserve 'section' from search"
            assert chunk["metadata"]["search_source"] == "vector", (
                "Metadata must include search backend"
            )

    @pytest.mark.asyncio
    async def test_retrieval_agent_search_metadata(self):
        """Verify search_metadata structure with success/latency/backend.

        AC2: search_metadata includes success, latency_ms, backend
        """
        mock_results = [
            SearchResult(
                text="Capital expenditures totaled $420M",
                score=0.94,
                source="sql",
                metadata={},
                document_id="doc_2",
                page_number=22,
            ),
        ]

        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = mock_results

            result = await retrieval_agent(instruction="capex query", context={"top_k": 5})
            parsed = json.loads(result)

            metadata = parsed["search_metadata"]

            # Verify required fields
            assert "success" in metadata, "search_metadata must include 'success'"
            assert metadata["success"] is True, "Success should be True for valid search"
            assert "latency_ms" in metadata, "search_metadata must include 'latency_ms'"
            assert isinstance(metadata["latency_ms"], (int, float)), "latency_ms must be numeric"
            assert metadata["latency_ms"] >= 0, "latency_ms must be non-negative"
            assert "backend" in metadata, "search_metadata must include 'backend'"
            assert metadata["backend"] in ["vector", "sql", "hybrid"], "backend must be valid type"


class TestRetrievalAgentMultiIndexIntegration:
    """Test suite for multi-index search integration (AC3)."""

    @pytest.mark.asyncio
    async def test_retrieval_agent_calls_multi_index_search(self):
        """Verify retrieval_agent wraps multi_index_search directly (no duplication).

        AC3: Agent wraps multi_index_search() from raglite.retrieval.multi_index_search
        """
        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = []

            await retrieval_agent(instruction="test query", context={"top_k": 7})

            # Verify multi_index_search was called exactly once
            mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieval_agent_passes_parameters_correctly(self):
        """Verify query and top_k parameters passed through to multi_index_search.

        AC3: Preserves query and top_k parameter routing
        """
        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = []

            await retrieval_agent(instruction="revenue in Q3", context={"top_k": 10})

            # Verify parameters passed correctly
            mock_search.assert_called_once_with("revenue in Q3", top_k=10)

    @pytest.mark.asyncio
    async def test_retrieval_agent_preserves_search_classification(self):
        """Verify search results preserve query classification (simple/table/analytical).

        AC3: Leverages existing query classification logic
        """
        # Return results that simulate different query types
        mock_results = [
            SearchResult(
                text="Simple financial fact",
                score=0.95,
                source="vector",
                metadata={"query_type": "simple"},
                document_id="doc_1",
                page_number=10,
            ),
            SearchResult(
                text="Table data from SQL",
                score=0.90,
                source="sql",
                metadata={"query_type": "table"},
                document_id="table_1",
                page_number=None,
            ),
        ]

        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = mock_results

            result = await retrieval_agent(instruction="mixed query", context={"top_k": 5})
            parsed = json.loads(result)

            # Verify both results returned (no duplication, direct pass-through)
            assert len(parsed["chunks"]) == 2, "Agent should return all multi_index_search results"
            assert parsed["chunks"][0]["source"] == "vector", "Should preserve vector source"
            assert parsed["chunks"][1]["source"] == "sql", "Should preserve SQL source"


class TestRetrievalAgentErrorHandling:
    """Test suite for error handling and graceful degradation (AC2, NFR24)."""

    @pytest.mark.asyncio
    async def test_retrieval_agent_handles_search_failure(self):
        """Verify agent returns empty results with error metadata on search failure.

        AC2: If search fails → return empty results with error metadata
        NFR24: Graceful degradation - user always receives response
        """
        from raglite.retrieval.multi_index_search import MultiIndexSearchError

        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.side_effect = MultiIndexSearchError("Database connection failed")

            result = await retrieval_agent(instruction="test query", context={"top_k": 5})
            parsed = json.loads(result)

            # Verify graceful degradation
            assert parsed["total_retrieved"] == 0, "Should have 0 chunks on error"
            assert parsed["chunks"] == [], "chunks should be empty list on error"
            assert parsed["search_metadata"]["success"] is False, "success should be False"
            assert "error" in parsed["search_metadata"], "Should include error message"
            assert "Database connection failed" in parsed["search_metadata"]["error"]

    @pytest.mark.asyncio
    async def test_retrieval_agent_handles_unexpected_exception(self):
        """Verify agent handles unexpected exceptions gracefully.

        NFR24: Graceful degradation for any error type
        """
        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.side_effect = RuntimeError("Unexpected error: out of memory")

            result = await retrieval_agent(instruction="test query", context={"top_k": 5})
            parsed = json.loads(result)

            # Verify graceful degradation
            assert parsed["search_metadata"]["success"] is False
            assert "error" in parsed["search_metadata"]
            # Query should still be preserved for debugging
            assert parsed["query"] == "test query"

    @pytest.mark.asyncio
    async def test_retrieval_agent_always_returns_valid_json(self):
        """Verify agent always returns valid, parseable JSON even on error.

        AC2: Output is always valid JSON string
        """
        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.side_effect = ValueError("Invalid input")

            result = await retrieval_agent(instruction="test", context={"top_k": 5})

            # Should be parseable JSON even on error
            parsed = json.loads(result)
            assert "chunks" in parsed
            assert "query" in parsed
            assert "search_metadata" in parsed


class TestRetrievalAgentJSONSerialization:
    """Test suite for JSON serialization (AC2)."""

    @pytest.mark.asyncio
    async def test_retrieval_agent_serializes_special_characters(self):
        """Verify JSON serialization handles special characters correctly.

        AC2: Special characters (quotes, newlines) handled correctly
        """
        mock_results = [
            SearchResult(
                text='The CEO said "Revenue grew by 50%"\nQ4 was strong.',
                score=0.95,
                source="vector",
                metadata={"section": 'CEO "Statement"'},
                document_id="doc_1",
                page_number=10,
            ),
        ]

        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = mock_results

            result = await retrieval_agent(instruction="CEO statement", context={"top_k": 5})

            # Should be valid JSON
            parsed = json.loads(result)
            chunk = parsed["chunks"][0]

            # Verify special characters preserved
            assert "Revenue grew by 50%" in chunk["content"]
            assert "Q4 was strong." in chunk["content"]
            assert '"' in chunk["metadata"]["section"]

    @pytest.mark.asyncio
    async def test_retrieval_agent_serializes_large_chunks(self):
        """Verify JSON serialization handles large chunks without truncation.

        AC2: Large chunks (>2000 chars) serialize without truncation
        """
        large_text = "x" * 3000  # Create 3000 char text

        mock_results = [
            SearchResult(
                text=large_text,
                score=0.95,
                source="vector",
                metadata={"large": True},
                document_id="doc_1",
                page_number=10,
            ),
        ]

        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = mock_results

            result = await retrieval_agent(instruction="large text", context={"top_k": 5})
            parsed = json.loads(result)

            chunk = parsed["chunks"][0]
            # Verify no truncation
            assert len(chunk["content"]) == 3000, "Large chunk should not be truncated"
            assert chunk["content"] == large_text


class TestRetrievalAgentPerformance:
    """Test suite for performance constraints (AC4, NFR5)."""

    @pytest.mark.asyncio
    async def test_retrieval_agent_execution_time_under_100ms(self):
        """Verify unit test execution time <100ms (no real DB/LLM calls).

        AC4: Test execution time <100ms (framework overhead only)
        """
        import time

        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            # Return empty results to minimize overhead
            mock_search.return_value = []

            start = time.time()
            await retrieval_agent(instruction="test query", context={"top_k": 5})
            elapsed_ms = (time.time() - start) * 1000

            # Unit test must complete in <100ms (no real searches)
            assert elapsed_ms < 100, f"Execution took {elapsed_ms:.1f}ms, must be <100ms"

    @pytest.mark.asyncio
    async def test_retrieval_agent_logs_latency_in_metadata(self):
        """Verify execution latency tracked in search_metadata.latency_ms.

        NFR5: Latency logged for monitoring
        """
        import asyncio

        with patch(
            "raglite.agentic.agents.retrieval_agent.multi_index_search", new_callable=AsyncMock
        ) as mock_search:
            # Simulate some delay
            async def delayed_search(*args, **kwargs):
                await asyncio.sleep(0.010)  # 10ms delay
                return []

            mock_search.side_effect = delayed_search

            result = await retrieval_agent(instruction="test query", context={"top_k": 5})
            parsed = json.loads(result)

            # Latency should be recorded
            assert "latency_ms" in parsed["search_metadata"]
            assert parsed["search_metadata"]["latency_ms"] >= 10, "Should capture actual latency"
