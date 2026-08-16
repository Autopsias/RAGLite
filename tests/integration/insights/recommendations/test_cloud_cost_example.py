"""Tests for specific cloud cost example (AC5)."""

from datetime import UTC, datetime

import pytest

from raglite.shared.models import RecommendationCategory

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


class TestCloudCostExample:
    """Tests for specific cloud cost example (AC5)."""

    @pytest.mark.asyncio
    async def test_cloud_cost_generates_risk_mitigation(self, cloud_cost_scenario: dict):
        """AC5: Cloud cost anomaly generates RISK_MITIGATION recommendation."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.category == RecommendationCategory.RISK_MITIGATION

    @pytest.mark.asyncio
    async def test_cloud_cost_high_impact(self, cloud_cost_scenario: dict):
        """AC5: Cloud cost recommendation has high impact score >= 8."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.impact_score >= 8

    @pytest.mark.asyncio
    async def test_cloud_cost_high_urgency(self, cloud_cost_scenario: dict):
        """AC5: Cloud cost recommendation has high urgency."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.urgency == "high"

    @pytest.mark.asyncio
    async def test_cloud_cost_preserves_evidence(self, cloud_cost_scenario: dict):
        """AC5: Cloud cost recommendation preserves supporting evidence."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.supporting_evidence == cloud_cost_scenario["insight"].supporting_data
        assert "cloud_budget" in rec.supporting_evidence
        assert "budget_variance" in rec.supporting_evidence


class TestDataIntegrity:
    """Tests for data integrity through recommendation pipeline."""

    @pytest.mark.asyncio
    async def test_sources_preserved(self, cloud_cost_scenario: dict):
        """Data integrity: Sources from insight preserved in recommendation."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.sources == cloud_cost_scenario["insight"].sources

    @pytest.mark.asyncio
    async def test_supporting_data_preserved(self, cloud_cost_scenario: dict):
        """Data integrity: Supporting data from insight preserved as evidence."""
        from raglite.insights.recommendations import generate_recommendations

        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        rec = result.recommendations[0]

        assert rec.supporting_evidence == cloud_cost_scenario["insight"].supporting_data

    @pytest.mark.asyncio
    async def test_timestamp_is_set(self, cloud_cost_scenario: dict):
        """Data integrity: Recommendation has valid timestamp."""
        from raglite.insights.recommendations import generate_recommendations

        before = datetime.now(UTC)
        result = await generate_recommendations(
            [cloud_cost_scenario["insight"]], auto_synthesize=False
        )
        after = datetime.now(UTC)

        rec = result.recommendations[0]
        assert before <= rec.created_at <= after
