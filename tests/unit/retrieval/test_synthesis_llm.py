"""Unit tests for synthesis_agent module (Story 3.4 AC1-AC3).

Tests the synthesis agent's ability to combine multi-source results (retrieval + analysis)
into coherent natural language answers with proper source attribution.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.agentic.agents.synthesis_agent import synthesis_agent
from raglite.agentic.agents.synthesis_methods import _synthesize_with_openai
from raglite.agentic.state import SynthesisResult


class TestOpenAISynthesis:
    """Test OpenAI GPT-4o-powered synthesis."""

    @pytest.mark.asyncio
    async def test_openai_synthesis_not_available(self):
        """Test OpenAI synthesis when openai package not installed."""
        # Temporarily make OPENAI_AVAILABLE False
        with patch("raglite.agentic.agents.synthesis_methods.OPENAI_AVAILABLE", False):
            with pytest.raises(ImportError, match="openai package not installed"):
                await _synthesize_with_openai([], [], "test query")

    @pytest.mark.asyncio
    async def test_openai_synthesis_success(self):
        """Test OpenAI synthesis with valid API key."""
        retrieval_results = [{"content": "Revenue: $50M", "source": "report.pdf"}]
        query = "What is the revenue?"

        # Mock OpenAI client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {"answer": "Revenue is $50M", "reasoning_steps": ["Checked report.pdf"]}
        )
        mock_client.chat.completions.create.return_value = mock_response

        with patch(
            "raglite.agentic.agents.synthesis_methods.AsyncOpenAI",
            return_value=mock_client,
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                answer, reasoning, sources = await _synthesize_with_openai(
                    retrieval_results, [], query
                )

        assert answer == "Revenue is $50M"
        assert len(reasoning) == 1
        assert "report.pdf" in sources

    @pytest.mark.asyncio
    async def test_openai_synthesis_no_api_key(self):
        """Test OpenAI synthesis raises error when API key missing."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable not set"):
                await _synthesize_with_openai([], [], "test query")

    @pytest.mark.asyncio
    async def test_openai_synthesis_custom_model(self):
        """Test OpenAI synthesis supports custom model selection."""
        retrieval_results = [{"content": "Test", "source": "test.pdf"}]
        query = "Test query"

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"answer": "Test answer"})
        mock_client.chat.completions.create.return_value = mock_response

        with patch(
            "raglite.agentic.agents.synthesis_methods.AsyncOpenAI",
            return_value=mock_client,
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                await _synthesize_with_openai(retrieval_results, [], query, model="gpt-4-turbo")

        # Verify correct model was passed
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_openai_synthesis_handles_none_response(self):
        """Test OpenAI synthesis handles None response content gracefully."""
        retrieval_results = [{"content": "Test content", "source": "test.pdf"}]
        query = "Test query"

        # Mock OpenAI client with None response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None  # None response
        mock_client.chat.completions.create.return_value = mock_response

        with patch(
            "raglite.agentic.agents.synthesis_methods.AsyncOpenAI",
            return_value=mock_client,
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                answer, reasoning, sources = await _synthesize_with_openai(
                    retrieval_results, [], query
                )

        # Should handle None gracefully and return empty string
        assert answer == ""
        assert reasoning == ["Direct synthesis from OpenAI response"]


class TestSynthesisAgent:
    """Test synthesis agent orchestration and error handling."""

    @pytest.mark.asyncio
    async def test_synthesis_agent_extracts_context(self):
        """Test synthesis agent extracts results from context dict."""
        context = {
            "task_1": json.dumps(
                {
                    "chunks": [{"content": "Revenue: $50M", "source": "report.pdf"}],
                    "query": "Test query",
                }
            ),
            "task_2": json.dumps(
                {
                    "calculation": "growth",
                    "formatted_value": "+15%",
                    "reasoning": "YoY increase",
                }
            ),
        }

        # In test mode, synthesis agent uses simple synthesis
        result_json = await synthesis_agent("Synthesize results", context)

        result = json.loads(result_json)
        # Simple synthesis output
        assert "Based on the query: Test query" in result["answer"]
        assert "Revenue: $50M" in result["answer"]
        assert "growth = +15%" in result["answer"]
        assert result["metadata"]["retrieval_count"] == 1
        assert result["metadata"]["analysis_count"] == 1
        assert result["metadata"]["synthesis_type"] == "simple"

    @pytest.mark.asyncio
    async def test_synthesis_agent_validates_empty_query(self):
        """Test synthesis agent validates empty query."""
        context = {"task_1": json.dumps({"chunks": [{"content": "Test", "source": "test.pdf"}]})}

        result_json = await synthesis_agent("", context)
        result = json.loads(result_json)

        assert result["metadata"]["error"] is True
        assert "Query cannot be empty" in result["reasoning_steps"][0]

    @pytest.mark.asyncio
    async def test_synthesis_agent_validates_empty_results(self):
        """Test synthesis agent validates empty retrieval and analysis results."""
        result_json = await synthesis_agent("Test query", {})
        result = json.loads(result_json)

        assert result["metadata"]["error"] is True
        assert (
            "Synthesis requires at least retrieval_results or analysis_results"
            in result["reasoning_steps"][0]
        )

    @pytest.mark.asyncio
    async def test_synthesis_agent_fallback_to_mistral(self):
        """Test synthesis agent falls back to Mistral when OpenAI fails."""
        context = {
            "task_1": json.dumps(
                {"chunks": [{"content": "Test", "source": "test.pdf"}], "query": "Test"}
            )
        }

        # Mock OpenAI failure and bypass test mode
        with patch(
            "raglite.agentic.agents.synthesis_methods._synthesize_with_openai",
            side_effect=Exception("OpenAI API error"),
        ):
            # Mock successful Mistral fallback
            with patch(
                "raglite.agentic.agents.synthesis_methods._synthesize_with_mistral"
            ) as mock_mistral:
                mock_mistral.return_value = (
                    "Mistral answer",
                    ["Reasoning"],
                    ["test.pdf"],
                )
                # Temporarily disable test mode to test fallback behavior
                with patch.dict("os.environ", {}, clear=True):
                    result_json = await synthesis_agent("Test query", context)

        result = json.loads(result_json)
        assert result["answer"] == "Mistral answer"
        assert result["metadata"]["synthesis_type"] == "mistral-large"

    @pytest.mark.asyncio
    async def test_synthesis_agent_handles_dict_context(self):
        """Test synthesis agent handles context with dict (not JSON string) values."""
        context = {
            "task_1": {
                "chunks": [{"content": "Revenue: $50M", "source": "report.pdf"}],
                "query": "Test query",
            }
        }

        # Mock OpenAI synthesis
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"answer": "Test answer"})
        mock_client.chat.completions.create.return_value = mock_response

        with patch(
            "raglite.agentic.agents.synthesis_methods.AsyncOpenAI",
            return_value=mock_client,
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result_json = await synthesis_agent("Test query", context)

        result = json.loads(result_json)
        assert result["metadata"]["retrieval_count"] == 1

    @pytest.mark.asyncio
    async def test_synthesis_agent_skips_invalid_context_entries(self):
        """Test synthesis agent gracefully skips invalid context entries."""
        context = {
            "task_1": json.dumps(
                {
                    "chunks": [{"content": "Valid", "source": "test.pdf"}],
                    "query": "Test",
                }
            ),
            "task_2": "invalid json string {{{",
            "task_3": None,
        }

        # Mock OpenAI synthesis
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"answer": "Test answer"})
        mock_client.chat.completions.create.return_value = mock_response

        with patch(
            "raglite.agentic.agents.synthesis_methods.AsyncOpenAI",
            return_value=mock_client,
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result_json = await synthesis_agent("Test query", context)

        result = json.loads(result_json)
        # Should only count valid context entry
        assert result["metadata"]["retrieval_count"] == 1

    @pytest.mark.asyncio
    async def test_synthesis_agent_uses_instruction_as_query_fallback(self):
        """Test synthesis agent uses instruction as query when not in context."""
        context = {"task_1": json.dumps({"chunks": [{"content": "Test", "source": "test.pdf"}]})}

        # Mock OpenAI synthesis
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"answer": "Test answer"})
        mock_client.chat.completions.create.return_value = mock_response

        with patch(
            "raglite.agentic.agents.synthesis_methods.AsyncOpenAI",
            return_value=mock_client,
        ):
            # Bypass test mode to test OpenAI synthesis
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
                result_json = await synthesis_agent("What is the revenue?", context)

        result = json.loads(result_json)
        # Query extracted from instruction
        assert result["answer"] == "Test answer"


class TestSynthesisResultModel:
    """Test SynthesisResult Pydantic model."""

    def test_synthesis_result_creation(self):
        """Test SynthesisResult model validation."""
        result = SynthesisResult(
            answer="Revenue grew 15% to $50M",
            reasoning_steps=["Step 1: Check revenue", "Step 2: Calculate growth"],
            sources=["report.pdf", "analysis.pdf"],
            metadata={"retrieval_count": 2, "analysis_count": 1},
        )

        assert result.answer == "Revenue grew 15% to $50M"
        assert len(result.reasoning_steps) == 2
        assert len(result.sources) == 2
        assert result.metadata["retrieval_count"] == 2

    def test_synthesis_result_json_serialization(self):
        """Test SynthesisResult can serialize to JSON."""
        result = SynthesisResult(
            answer="Test answer",
            reasoning_steps=["Step 1"],
            sources=["test.pdf"],
            metadata={"confidence": 0.95},
        )

        json_str = result.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["answer"] == "Test answer"
        assert len(parsed["reasoning_steps"]) == 1
        assert parsed["metadata"]["confidence"] == 0.95
