"""Unit tests for strands_poc.py module.

This module tests the AWS Strands POC functions and agent definitions
used for Epic 3 multi-agent orchestration validation.

Coverage Focus:
- Mock functions (mock_multi_index_search, mock_generate_citations)
- Pydantic output models (RetrievalOutput, SynthesisOutput)
- Agent factory (create_orchestrator)
- Error handling and edge cases

All tests use mocks to avoid real AWS Strands API calls.

NOTE: Tests will skip gracefully if strands is not installed (deferred to Epic 3).
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

# Check if strands is available - skip all tests if not
try:
    import strands  # noqa: F401

    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

# Skip entire module if strands not installed
pytestmark = pytest.mark.skipif(
    not STRANDS_AVAILABLE, reason="AWS Strands not installed (deferred to Epic 3)"
)


class TestMockFunctions:
    """Test mock data generation functions."""

    @pytest.mark.asyncio
    async def test_mock_multi_index_search_basic(self):
        """Test mock_multi_index_search returns expected structure."""
        from strands_poc import mock_multi_index_search

        query = "What was Q3 revenue?"
        result = await mock_multi_index_search(query)

        assert isinstance(result, dict)
        assert "chunks" in result
        assert "query" in result
        assert "latency_ms" in result
        assert result["query"] == query
        assert len(result["chunks"]) > 0

    @pytest.mark.asyncio
    async def test_mock_multi_index_search_chunk_structure(self):
        """Test mock chunks have required fields."""
        from strands_poc import mock_multi_index_search

        result = await mock_multi_index_search("test query")
        chunks = result["chunks"]

        for chunk in chunks:
            assert "text" in chunk
            assert "score" in chunk
            assert "page" in chunk
            assert isinstance(chunk["text"], str)
            assert isinstance(chunk["score"], float)
            assert isinstance(chunk["page"], int)

    @pytest.mark.asyncio
    async def test_mock_multi_index_search_empty_query(self):
        """Test mock_multi_index_search handles empty query."""
        from strands_poc import mock_multi_index_search

        result = await mock_multi_index_search("")
        assert isinstance(result, dict)
        assert result["query"] == ""

    @pytest.mark.asyncio
    async def test_mock_generate_citations_basic(self):
        """Test mock_generate_citations appends sources."""
        from strands_poc import mock_generate_citations

        chunks = [
            {"text": "Q3 revenue was $150M", "page": 3},
            {"text": "Operating expenses up 15%", "page": 5},
        ]
        answer = "Based on the data, revenue increased."

        result = await mock_generate_citations(chunks, answer)

        assert isinstance(result, str)
        assert answer in result
        assert "Sources:" in result
        assert "Page 3" in result
        assert "Page 5" in result

    @pytest.mark.asyncio
    async def test_mock_generate_citations_empty_chunks(self):
        """Test mock_generate_citations handles empty chunks list."""
        from strands_poc import mock_generate_citations

        chunks = []
        answer = "No sources available."

        result = await mock_generate_citations(chunks, answer)
        assert answer in result
        assert "Sources:" in result

    @pytest.mark.asyncio
    async def test_mock_generate_citations_truncates_long_text(self):
        """Test mock_generate_citations truncates chunk text to 50 chars."""
        from strands_poc import mock_generate_citations

        long_text = "A" * 100
        chunks = [{"text": long_text, "page": 1}]
        answer = "Test"

        result = await mock_generate_citations(chunks, answer)
        # Should truncate to 50 chars + "..."
        assert long_text[:50] in result
        assert len([line for line in result.split("\n") if long_text in line]) == 0


class TestPydanticModels:
    """Test Pydantic output models for type validation."""

    def test_retrieval_output_valid(self):
        """Test RetrievalOutput validates correct data."""
        from strands_poc import RetrievalOutput

        data = {
            "chunks": [{"text": "sample", "score": 0.9, "page": 1}],
            "query": "test query",
            "chunk_count": 1,
        }
        output = RetrievalOutput(**data)

        assert output.query == "test query"
        assert output.chunk_count == 1
        assert len(output.chunks) == 1

    def test_retrieval_output_empty_chunks(self):
        """Test RetrievalOutput handles empty chunks."""
        from strands_poc import RetrievalOutput

        data = {"chunks": [], "query": "test", "chunk_count": 0}
        output = RetrievalOutput(**data)

        assert output.chunk_count == 0
        assert output.chunks == []

    def test_retrieval_output_missing_field(self):
        """Test RetrievalOutput rejects missing required fields."""
        from strands_poc import RetrievalOutput

        data = {"chunks": [], "query": "test"}  # Missing chunk_count

        with pytest.raises(ValidationError):
            RetrievalOutput(**data)

    def test_synthesis_output_valid(self):
        """Test SynthesisOutput validates correct data."""
        from strands_poc import SynthesisOutput

        data = {"answer": "Based on data, revenue increased.", "source_count": 2}
        output = SynthesisOutput(**data)

        assert output.answer == "Based on data, revenue increased."
        assert output.source_count == 2

    def test_synthesis_output_zero_sources(self):
        """Test SynthesisOutput handles zero sources."""
        from strands_poc import SynthesisOutput

        data = {"answer": "No data available.", "source_count": 0}
        output = SynthesisOutput(**data)

        assert output.source_count == 0

    def test_synthesis_output_missing_field(self):
        """Test SynthesisOutput rejects missing required fields."""
        from strands_poc import SynthesisOutput

        data = {"answer": "test"}  # Missing source_count

        with pytest.raises(ValidationError):
            SynthesisOutput(**data)


class TestAgentFunctions:
    """Test Strands agent functions (retrieval and synthesis)."""

    @pytest.mark.asyncio
    async def test_retrieval_agent_success(self):
        """Test retrieval_agent returns valid JSON output."""
        from strands_poc import retrieval_agent

        result = await retrieval_agent("What was Q3 revenue?")

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "chunks" in parsed
        assert "query" in parsed
        assert "chunk_count" in parsed

    @pytest.mark.asyncio
    async def test_retrieval_agent_empty_query(self):
        """Test retrieval_agent handles empty query."""
        from strands_poc import retrieval_agent

        result = await retrieval_agent("")
        parsed = json.loads(result)

        assert parsed["query"] == ""
        assert isinstance(parsed["chunks"], list)

    @pytest.mark.asyncio
    @patch("strands_poc.mock_multi_index_search")
    async def test_retrieval_agent_uses_mock_search(self, mock_search):
        """Test retrieval_agent calls mock_multi_index_search."""
        mock_search.return_value = {"chunks": [], "query": "test", "latency_ms": 50}

        from strands_poc import retrieval_agent

        await retrieval_agent("test query")
        mock_search.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_synthesis_agent_success(self):
        """Test synthesis_agent generates answer from retrieval results."""
        from strands_poc import synthesis_agent

        retrieval_json = json.dumps(
            {
                "chunks": [{"text": "Q3 revenue $150M", "page": 3}],
                "query": "What was Q3 revenue?",
            }
        )

        result = await synthesis_agent(retrieval_json)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "answer" in parsed
        assert "source_count" in parsed
        assert parsed["source_count"] == 1

    @pytest.mark.asyncio
    async def test_synthesis_agent_empty_chunks(self):
        """Test synthesis_agent handles empty retrieval results."""
        from strands_poc import synthesis_agent

        retrieval_json = json.dumps({"chunks": [], "query": "test"})

        result = await synthesis_agent(retrieval_json)
        parsed = json.loads(result)

        assert parsed["source_count"] == 0

    @pytest.mark.asyncio
    async def test_synthesis_agent_invalid_json(self):
        """Test synthesis_agent handles invalid JSON input."""
        from strands_poc import synthesis_agent

        with pytest.raises(json.JSONDecodeError):
            await synthesis_agent("not valid json")


class TestCreateOrchestrator:
    """Test orchestrator creation and configuration."""

    @patch("strands_poc.Agent")
    @patch("strands_poc.MistralModel")
    def test_create_orchestrator_returns_agent(self, mock_mistral_class, mock_agent_class):
        """Test create_orchestrator returns configured Agent."""
        from strands_poc import create_orchestrator

        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        result = create_orchestrator()

        assert result == mock_agent_instance
        mock_agent_class.assert_called_once()

    @patch("strands_poc.Agent")
    @patch("strands_poc.MistralModel")
    def test_create_orchestrator_configures_mistral(self, mock_mistral_class, mock_agent_class):
        """Test create_orchestrator uses Mistral model from settings."""
        from raglite.shared.config import settings
        from strands_poc import create_orchestrator

        create_orchestrator()

        mock_mistral_class.assert_called_once_with(
            api_key=settings.mistral_api_key,
            model_id=settings.metadata_extraction_model,
        )

    @patch("strands_poc.Agent")
    @patch("strands_poc.MistralModel")
    def test_create_orchestrator_registers_tools(self, mock_mistral_class, mock_agent_class):
        """Test create_orchestrator registers retrieval and synthesis tools."""
        from strands_poc import create_orchestrator, retrieval_agent, synthesis_agent

        create_orchestrator()

        # Verify Agent was called with tools parameter
        call_kwargs = mock_agent_class.call_args[1]
        assert "tools" in call_kwargs
        tools = call_kwargs["tools"]
        assert retrieval_agent in tools
        assert synthesis_agent in tools

    @patch("strands_poc.Agent")
    @patch("strands_poc.MistralModel")
    def test_create_orchestrator_system_prompt(self, mock_mistral_class, mock_agent_class):
        """Test create_orchestrator includes orchestration instructions."""
        from strands_poc import create_orchestrator

        create_orchestrator()

        call_kwargs = mock_agent_class.call_args[1]
        assert "system_prompt" in call_kwargs
        system_prompt = call_kwargs["system_prompt"]
        assert "RAG orchestration" in system_prompt
        assert "retrieval_agent" in system_prompt
        assert "synthesis_agent" in system_prompt


class TestValidatePOC:
    """Test POC validation workflow."""

    @pytest.mark.asyncio
    @patch("strands_poc.create_orchestrator")
    async def test_validate_poc_success_path(self, mock_create_orchestrator):
        """Test validate_poc returns True on successful orchestration."""
        # Mock orchestrator with successful result
        mock_orchestrator = MagicMock()
        mock_result = MagicMock()
        mock_result.__str__ = MagicMock(return_value="Success response with citations")

        # Use AsyncMock for async invoke method
        mock_orchestrator.invoke_async = AsyncMock(return_value=mock_result)
        mock_create_orchestrator.return_value = mock_orchestrator

        from strands_poc import validate_poc

        # Run validation
        result = await validate_poc()

        assert result is True
        mock_orchestrator.invoke_async.assert_called_once()

    @pytest.mark.asyncio
    @patch("strands_poc.create_orchestrator")
    async def test_validate_poc_handles_exception(self, mock_create_orchestrator):
        """Test validate_poc returns False on orchestrator error."""
        mock_orchestrator = MagicMock()
        mock_orchestrator.invoke_async = AsyncMock(side_effect=Exception("API error"))
        mock_create_orchestrator.return_value = mock_orchestrator

        from strands_poc import validate_poc

        result = await validate_poc()

        assert result is False

    @pytest.mark.asyncio
    @patch("strands_poc.create_orchestrator")
    async def test_validate_poc_checks_latency(self, mock_create_orchestrator):
        """Test validate_poc validates latency budget."""
        mock_orchestrator = MagicMock()
        mock_result = MagicMock()
        mock_result.__str__ = MagicMock(return_value="Response")

        # Simulate slow response (3 seconds)
        async def slow_invoke(*args):
            await asyncio.sleep(3)
            return mock_result

        mock_orchestrator.invoke_async = slow_invoke
        mock_create_orchestrator.return_value = mock_orchestrator

        from strands_poc import validate_poc

        # Should still complete but report latency failure
        result = await validate_poc()

        # Result is False because latency exceeds 2s budget
        assert result is False
