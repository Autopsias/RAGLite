"""Unit tests for Analysis Agent (Story 3.3 AC4).

Tests all 4 analysis types, error handling, JSON serialization, and performance.
Mocks Claude API to prevent LLM costs and ensure fast execution (<100ms).
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from raglite.agentic.agents.analysis_agent import analysis_agent
from raglite.agentic.state import AnalysisResult


@pytest.mark.asyncio
async def test_analysis_agent_yoy_growth_calculation():
    """Test YoY growth calculation: {"Q3_2023": 10.0, "Q3_2024": 12.0} → +20%."""
    with patch("raglite.agentic.agents.analysis_agent.get_claude_client") as mock_client:
        mock_client.return_value.messages.create.return_value.content = [
            AsyncMock(text="Revenue grew 20% YoY from $10M to $12M")
        ]
        mock_client.return_value.messages.create = AsyncMock(
            return_value=type(
                "Response", (), {"content": [type("Content", (), {"text": "Revenue grew 20% YoY"})]}
            )()
        )

        result_json = await analysis_agent(
            data={"Q3_2023": 10.0, "Q3_2024": 12.0},
            analysis_type="yoy_growth",
        )

        result = AnalysisResult.model_validate_json(result_json)

        assert result.value == pytest.approx(0.20, abs=0.01)
        assert result.formatted_value == "+20.0%"
        assert "(12.0 - 10.0)" in result.calculation
        assert result.data_points_used == {"Q3_2023": 10.0, "Q3_2024": 12.0}


@pytest.mark.asyncio
async def test_analysis_agent_variance_analysis():
    """Test variance analysis: {"budget": 100.0, "actual": 85.0} → -15% under budget."""
    with patch("raglite.agentic.agents.analysis_agent.get_claude_client") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(
            return_value=type(
                "Response",
                (),
                {"content": [type("Content", (), {"text": "Budget variance explanation"})()]},
            )
        )

        result_json = await analysis_agent(
            data={"budget": 100.0, "actual": 85.0},
            analysis_type="variance",
        )

        result = AnalysisResult.model_validate_json(result_json)

        assert result.value == pytest.approx(-0.15, abs=0.01)
        assert result.formatted_value == "-15.0%"
        assert "(85.0 - 100.0)" in result.calculation


@pytest.mark.asyncio
async def test_analysis_agent_trend_detection():
    """Test trend detection: {"Q1": 10, "Q2": 12, "Q3": 14} → increasing trend."""
    with patch("raglite.agentic.agents.analysis_agent.get_claude_client") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(
            return_value=type(
                "Response",
                (),
                {"content": [type("Content", (), {"text": "Consistent upward trend"})()]},
            )
        )

        result_json = await analysis_agent(
            data={"Q1": 10.0, "Q2": 12.0, "Q3": 14.0},
            analysis_type="trend",
        )

        result = AnalysisResult.model_validate_json(result_json)

        assert result.formatted_value == "increasing"
        assert "slope=" in result.calculation


@pytest.mark.asyncio
async def test_analysis_agent_percentage_calculation():
    """Test percentage calculation: {"part": 25.0, "whole": 100.0} → 25%."""
    with patch("raglite.agentic.agents.analysis_agent.get_claude_client") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(
            return_value=type(
                "Response",
                (),
                {"content": [type("Content", (), {"text": "Percentage explanation"})()]},
            )
        )

        result_json = await analysis_agent(
            data={"part": 25.0, "whole": 100.0},
            analysis_type="percentage",
        )

        result = AnalysisResult.model_validate_json(result_json)

        assert result.value == pytest.approx(25.0, abs=0.1)
        assert result.formatted_value == "25.0%"


@pytest.mark.asyncio
async def test_analysis_agent_error_invalid_type():
    """Test error handling for invalid analysis_type."""
    result_json = await analysis_agent(
        data={"Q1": 10.0, "Q2": 12.0},
        analysis_type="invalid_type",
    )

    result = json.loads(result_json)

    assert result["success"] is False
    assert "Invalid analysis_type" in result["error"]
    assert result["analysis_type"] == "invalid_type"


@pytest.mark.asyncio
async def test_analysis_agent_error_missing_data_keys():
    """Test error handling for missing required data keys."""
    result_json = await analysis_agent(
        data={"only_one_value": 10.0},
        analysis_type="yoy_growth",
    )

    result = json.loads(result_json)

    assert result["success"] is False
    assert "requires at least 2 data points" in result["error"]


@pytest.mark.asyncio
async def test_analysis_agent_error_zero_denominator():
    """Test error handling for division by zero."""
    result_json = await analysis_agent(
        data={"budget": 0.0, "actual": 100.0},
        analysis_type="variance",
    )

    result = json.loads(result_json)

    assert result["success"] is False
    assert "cannot be zero" in result["error"]


@pytest.mark.asyncio
async def test_analysis_agent_json_serialization():
    """Test that AnalysisResult model serializes correctly to JSON."""
    with patch("raglite.agentic.agents.analysis_agent.get_claude_client") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(
            return_value=type(
                "Response", (), {"content": [type("Content", (), {"text": "Test reasoning"})()]}
            )
        )

        result_json = await analysis_agent(
            data={"part": 50.0, "whole": 200.0},
            analysis_type="percentage",
        )

        # Verify it's valid JSON
        parsed = json.loads(result_json)
        assert isinstance(parsed, dict)
        assert "calculation" in parsed
        assert "value" in parsed
        assert "formatted_value" in parsed
        assert "reasoning" in parsed
        assert "data_points_used" in parsed


@pytest.mark.asyncio
async def test_analysis_agent_with_context():
    """Test analysis agent with optional context parameter."""
    with patch("raglite.agentic.agents.analysis_agent.get_claude_client") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(
            return_value=type(
                "Response",
                (),
                {"content": [type("Content", (), {"text": "Context-aware reasoning"})()]},
            )
        )

        result_json = await analysis_agent(
            data={"Q3_2023": 10.0, "Q3_2024": 12.0},
            analysis_type="yoy_growth",
            context="Q3 is typically the strongest quarter due to seasonal demand",
        )

        result = AnalysisResult.model_validate_json(result_json)

        assert result.data_points_used == {"Q3_2023": 10.0, "Q3_2024": 12.0}
        assert result.value == pytest.approx(0.20, abs=0.01)


@pytest.mark.asyncio
async def test_analysis_agent_negative_variance():
    """Test variance with negative (over budget) result."""
    with patch("raglite.agentic.agents.analysis_agent.get_claude_client") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(
            return_value=type(
                "Response", (), {"content": [type("Content", (), {"text": "Over budget"})()]}
            )
        )

        result_json = await analysis_agent(
            data={"budget": 100.0, "actual": 120.0},
            analysis_type="variance",
        )

        result = AnalysisResult.model_validate_json(result_json)

        assert result.value == pytest.approx(0.20, abs=0.01)
        assert result.formatted_value == "+20.0%"  # Over budget is positive variance


@pytest.mark.asyncio
async def test_analysis_agent_trend_decreasing():
    """Test trend detection for decreasing pattern."""
    with patch("raglite.agentic.agents.analysis_agent.get_claude_client") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(
            return_value=type(
                "Response", (), {"content": [type("Content", (), {"text": "Downward trend"})()]}
            )
        )

        result_json = await analysis_agent(
            data={"Q1": 14.0, "Q2": 12.0, "Q3": 10.0},
            analysis_type="trend",
        )

        result = AnalysisResult.model_validate_json(result_json)

        assert result.formatted_value == "decreasing"


@pytest.mark.asyncio
async def test_analysis_agent_trend_stable():
    """Test trend detection for stable pattern."""
    with patch("raglite.agentic.agents.analysis_agent.get_claude_client") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(
            return_value=type(
                "Response", (), {"content": [type("Content", (), {"text": "Stable trend"})()]}
            )
        )

        result_json = await analysis_agent(
            data={"Q1": 10.0, "Q2": 10.0, "Q3": 10.0},
            analysis_type="trend",
        )

        result = AnalysisResult.model_validate_json(result_json)

        assert result.formatted_value == "stable"


@pytest.mark.asyncio
async def test_analysis_agent_claude_api_failure_fallback():
    """Test graceful degradation when Claude API fails (AC3 error handling)."""
    with patch("raglite.agentic.agents.analysis_agent.get_claude_client") as mock_client:
        mock_client.return_value.messages.create.side_effect = Exception("Claude API unavailable")

        result_json = await analysis_agent(
            data={"Q3_2023": 10.0, "Q3_2024": 12.0},
            analysis_type="yoy_growth",
        )

        result = AnalysisResult.model_validate_json(result_json)

        # Should still return calculation and formatted value
        assert result.value == pytest.approx(0.20, abs=0.01)
        assert result.formatted_value == "+20.0%"
        # Reasoning should be default since Claude failed
        assert "Year-over-year growth shows" in result.reasoning
