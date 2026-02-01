"""Tests for Epic4ValidationOrchestrator."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from tests.validation.forecast_accuracy import create_growth_data
from tests.validation.test_epic4_e2e_validation.orchestrator import (
    Epic4ValidationOrchestrator,
    create_comprehensive_test_data,
)
from tests.validation.test_insight_quality import INSIGHT_TEST_SCENARIOS
from tests.validation.test_recommendation_alignment import RECOMMENDATION_TEST_SCENARIOS


@pytest.fixture
def orchestrator() -> Epic4ValidationOrchestrator:
    """Create orchestrator instance for tests."""
    return Epic4ValidationOrchestrator()


@pytest.fixture
def test_data() -> dict[str, pd.DataFrame]:
    """Create test data for validation."""
    return create_comprehensive_test_data(months=24)


class TestOrchestrator:
    """Tests for validation orchestrator."""

    @pytest.mark.asyncio
    @pytest.mark.validation
    async def test_run_full_validation(
        self,
        orchestrator: Epic4ValidationOrchestrator,
        test_data: dict[str, pd.DataFrame],
    ):
        """Test complete validation pipeline execution.

        Story 4.10 AC1-AC4: Full E2E validation.
        """
        # Mock LLM calls for faster validation
        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_response = AsyncMock()
            mock_response.choices = [
                AsyncMock(message=AsyncMock(content='{"summary": "Test forecast"}'))
            ]
            mock_client.return_value.chat.complete.return_value = mock_response

            result = await orchestrator.run_full_validation(forecast_data=test_data)

        # Validate result structure
        assert result.__class__.__name__ == "Epic4ValidationResult"
        assert len(result.forecast_results) == 4  # revenue, expenses, cash_flow, ebitda
        assert result.insight_result is not None
        assert result.recommendation_result is not None
        assert result.summary != ""
        assert len(result.improvement_recommendations) > 0

        # Log results
        print(f"\n{result.summary}")
        print("\nImprovement Recommendations:")
        for rec in result.improvement_recommendations:
            print(f"  - {rec}")

    @pytest.mark.asyncio
    async def test_validate_forecasts_only(
        self,
        orchestrator: Epic4ValidationOrchestrator,
    ):
        """Test forecast validation in isolation."""
        test_data = {
            "revenue": create_growth_data(datetime(2021, 1, 1), periods=12),
        }

        # Mock LLM
        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_response = AsyncMock()
            mock_response.choices = [AsyncMock(message=AsyncMock(content='{"summary": "Test"}'))]
            mock_client.return_value.chat.complete.return_value = mock_response

            results = await orchestrator.validate_forecasts(test_data)

        assert len(results) == 1
        assert results[0].metric_name == "revenue"

    @pytest.mark.asyncio
    async def test_validate_insights_only(
        self,
        orchestrator: Epic4ValidationOrchestrator,
    ):
        """Test insight validation in isolation."""
        # Use subset of scenarios for faster test
        scenarios = INSIGHT_TEST_SCENARIOS[:3]

        result = await orchestrator.validate_insights(scenarios)

        assert result.total_scenarios == 3

    @pytest.mark.asyncio
    async def test_validate_recommendations_only(
        self,
        orchestrator: Epic4ValidationOrchestrator,
    ):
        """Test recommendation validation in isolation."""
        # Use subset of scenarios for faster test
        scenarios = RECOMMENDATION_TEST_SCENARIOS[:3]

        result = await orchestrator.validate_recommendations(scenarios)

        assert result.total_scenarios == 3
