"""Unit tests for synthesis_agent module (Story 3.4 AC1-AC3).

Tests the synthesis agent's ability to combine multi-source results (retrieval + analysis)
into coherent natural language answers with proper source attribution.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from raglite.agentic.agents.synthesis_methods import (
    _synthesize_with_mistral,
)
from raglite.agentic.agents.synthesis_utils import (
    _synthesize_simple,
)


class TestSimpleSynthesis:
    """Test simple synthesis without LLM (no API key required)."""

    def test_simple_synthesis_retrieval_only(self):
        """Test simple synthesis with retrieval results only."""
        retrieval_results = [
            {"content": "Q3 revenue was $50M", "source": "report.pdf"},
            {"content": "Q3 EBITDA was $12M", "source": "report.pdf"},
        ]
        query = "What was Q3 performance?"

        result, reasoning_steps, sources = _synthesize_simple(retrieval_results, [], query)

        assert "Based on the query: What was Q3 performance?" in result
        assert "Retrieved 2 relevant documents:" in result
        assert "Q3 revenue was $50M" in result
        assert "report.pdf" in result
        assert len(reasoning_steps) > 0
        assert "report.pdf" in sources

    def test_simple_synthesis_analysis_only(self):
        """Test simple synthesis with analysis results only."""
        analysis_results = [
            {
                "calculation": "revenue_growth",
                "formatted_value": "+20%",
                "reasoning": "Revenue increased from $100M to $120M",
            }
        ]
        query = "What is the revenue growth?"

        result, reasoning_steps, sources = _synthesize_simple([], analysis_results, query)

        assert "Based on the query: What is the revenue growth?" in result
        assert "Analysis Results (1 calculations):" in result
        assert "+20%" in result
        assert "Revenue increased from $100M to $120M" in result
        assert len(reasoning_steps) > 0
        assert len(sources) == 0

    def test_simple_synthesis_combined_sources(self):
        """Test simple synthesis with both retrieval and analysis results."""
        retrieval_results = [{"content": "Revenue was $120M", "source": "report.pdf"}]
        analysis_results = [
            {
                "calculation": "growth",
                "formatted_value": "+20%",
                "reasoning": "YoY increase",
            }
        ]
        query = "Analyze revenue growth"

        result, reasoning_steps, sources = _synthesize_simple(
            retrieval_results, analysis_results, query
        )

        assert "Retrieved 1 relevant documents:" in result
        assert "Analysis Results (1 calculations):" in result
        assert "Revenue was $120M" in result
        assert "+20%" in result

    def test_simple_synthesis_limits_chunks(self):
        """Test simple synthesis only shows top 3 document chunks."""
        retrieval_results = [
            {"content": f"Chunk {i} content", "source": f"source{i}.pdf"} for i in range(10)
        ]
        query = "Test query"

        result, reasoning_steps, sources = _synthesize_simple(retrieval_results, [], query)

        # Should only show top 3 chunks
        assert "1. Chunk 0 content" in result
        assert "2. Chunk 1 content" in result
        assert "3. Chunk 2 content" in result
        # Should not show chunk 4+
        assert "Chunk 3 content" not in result
        # Only collects sources from displayed chunks (top 3)
        assert len(sources) == 3
        assert "source0.pdf" in sources
        assert "source1.pdf" in sources
        assert "source2.pdf" in sources


class TestMistralSynthesis:
    """Test Mistral AI-powered synthesis."""

    @pytest.mark.asyncio
    async def test_mistral_synthesis_builds_context(self):
        """Test Mistral synthesis builds proper context from results."""
        retrieval_results = [{"content": "Revenue: $50M", "source": "report.pdf"}]
        analysis_results = [
            {
                "calculation": "growth",
                "formatted_value": "+15%",
                "reasoning": "YoY increase",
            }
        ]
        query = "What is revenue growth?"

        # Mock Mistral client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "answer": "Revenue grew 15% to $50M",
                "reasoning_steps": [
                    "Step 1: Check revenue",
                    "Step 2: Calculate growth",
                ],
            }
        )
        mock_client.chat.complete.return_value = mock_response

        with patch(
            "raglite.agentic.agents.synthesis_methods.get_mistral_client",
            return_value=mock_client,
        ):
            answer, reasoning, sources = await _synthesize_with_mistral(
                retrieval_results, analysis_results, query
            )

        assert answer == "Revenue grew 15% to $50M"
        assert len(reasoning) == 2
        assert "report.pdf" in sources

    @pytest.mark.asyncio
    async def test_mistral_synthesis_handles_non_json_response(self):
        """Test Mistral synthesis handles non-JSON responses gracefully."""
        retrieval_results = [{"content": "Test content", "source": "test.pdf"}]
        query = "Test query"

        # Mock Mistral client with non-JSON response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Plain text answer without JSON"
        mock_client.chat.complete.return_value = mock_response

        with patch(
            "raglite.agentic.agents.synthesis_methods.get_mistral_client",
            return_value=mock_client,
        ):
            answer, reasoning, sources = await _synthesize_with_mistral(
                retrieval_results, [], query
            )

        assert answer == "Plain text answer without JSON"
        assert reasoning == ["Direct synthesis from Mistral response"]

    @pytest.mark.asyncio
    async def test_mistral_synthesis_deduplicates_sources(self):
        """Test Mistral synthesis deduplicates source citations."""
        retrieval_results = [
            {"content": "Content 1", "source": "report.pdf"},
            {"content": "Content 2", "source": "report.pdf"},
            {"content": "Content 3", "source": "analysis.pdf"},
        ]
        query = "Test query"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"answer": "Test answer"})
        mock_client.chat.complete.return_value = mock_response

        with patch(
            "raglite.agentic.agents.synthesis_methods.get_mistral_client",
            return_value=mock_client,
        ):
            _, _, sources = await _synthesize_with_mistral(retrieval_results, [], query)

        # Should have 2 unique sources, not 3
        assert len(sources) == 2
        assert "report.pdf" in sources
        assert "analysis.pdf" in sources

    @pytest.mark.asyncio
    async def test_mistral_synthesis_handles_none_response(self):
        """Test Mistral synthesis handles None response content gracefully."""
        retrieval_results = [{"content": "Test content", "source": "test.pdf"}]
        query = "Test query"

        # Mock Mistral client with None response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None  # None response
        mock_client.chat.complete.return_value = mock_response

        with patch(
            "raglite.agentic.agents.synthesis_methods.get_mistral_client",
            return_value=mock_client,
        ):
            answer, reasoning, sources = await _synthesize_with_mistral(
                retrieval_results, [], query
            )

        # Should handle None gracefully and return empty string
        assert answer == ""
        assert reasoning == ["Direct synthesis from Mistral response"]
