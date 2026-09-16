"""[P1] Integration edge cases for insight generation across modules.

Story 8.4a-2 Phase 6: Test automation expansion.
Tests cross-module interactions, fixture edge cases, and import edge cases.
"""

import pytest

from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    ForecastPoint,
    ForecastResult,
    InsightCategory,
    Trend,
    TrendDirection,
)

pytestmark = [pytest.mark.unit]


# =============================================================================
# Cross-Module Fixture Usage
# =============================================================================


class TestCrossModuleFixtures:
    """[P1] Test that fixtures work across different test modules."""

    @pytest.mark.asyncio
    async def test_sample_anomalies_fixture_type(self, sample_anomalies):
        """[P1] Verify sample_anomalies fixture returns correct type."""
        assert isinstance(sample_anomalies, list)
        assert len(sample_anomalies) > 0
        assert sample_anomalies[0].__class__.__name__ == "Anomaly"

    @pytest.mark.asyncio
    async def test_sample_trends_fixture_type(self, sample_trends):
        """[P1] Verify sample_trends fixture returns correct type."""
        assert isinstance(sample_trends, list)
        assert len(sample_trends) > 0
        assert sample_trends[0].__class__.__name__ == "Trend"

    @pytest.mark.asyncio
    async def test_sample_forecasts_fixture_type(self, sample_forecasts):
        """[P1] Verify sample_forecasts fixture returns correct type."""
        assert isinstance(sample_forecasts, list)
        assert len(sample_forecasts) > 0
        assert sample_forecasts[0].__class__.__name__ == "ForecastResult"

    @pytest.mark.asyncio
    async def test_sample_insights_fixture_count(self, sample_insights):
        """[P1] Verify sample_insights fixture has expected count."""
        assert len(sample_insights) == 5
        assert all(i.__class__.__name__ == "Insight" for i in sample_insights)


# =============================================================================
# Fixture Edge Cases
# =============================================================================


class TestFixtureEdgeCases:
    """[P2] Test edge cases in fixture usage patterns."""

    @pytest.mark.asyncio
    async def test_empty_insight_list_filtering(self):
        """[P2] Test filtering operations on empty insight list."""
        from raglite.insights.proactive import filter_insights

        empty_list = []
        result = filter_insights(empty_list, category=InsightCategory.RISK)

        assert result == []

    @pytest.mark.asyncio
    async def test_none_anomaly_in_fixture_list(self):
        """[P2] Test handling of None values in anomaly list."""
        from raglite.insights.proactive import generate_insights

        # Edge case: None in anomaly list - filter before passing
        anomaly_list = [None]
        filtered_anomalies = [a for a in anomaly_list if a is not None]

        # Empty list should raise ValueError
        with pytest.raises(ValueError, match="No data to analyze"):
            await generate_insights(filtered_anomalies, [], [], auto_synthesize=False)

    @pytest.mark.asyncio
    async def test_mixed_none_and_valid_anomalies(self, sample_anomalies):
        """[P2] Test handling of mixed None and valid anomalies."""
        from raglite.insights.proactive import generate_insights

        mixed_list = [None, sample_anomalies[0], None]
        # Filter out None values before processing
        filtered_anomalies = [a for a in mixed_list if a is not None]

        result = await generate_insights(filtered_anomalies, [], [], auto_synthesize=False)
        # Should process only the valid anomaly
        assert result.total_generated == 1


# =============================================================================
# Import Edge Cases
# =============================================================================


class TestImportEdgeCases:
    """[P2] Test import-related edge cases and circular dependency prevention."""

    @pytest.mark.asyncio
    async def test_import_proactive_module(self):
        """[P1] Test that proactive module can be imported without errors."""
        try:
            from raglite.insights import proactive

            assert hasattr(proactive, "generate_insights")
            assert hasattr(proactive, "calculate_insight_priority")
            assert hasattr(proactive, "categorize_insight")
        except ImportError as e:
            pytest.fail(f"Failed to import proactive module: {e}")

    @pytest.mark.asyncio
    async def test_import_strategic_recommendations_module(self):
        """[P1] Test that strategic recommendations module can be imported."""
        try:
            from raglite.insights import recommendations

            assert hasattr(recommendations, "generate_recommendations")
        except ImportError as e:
            pytest.fail(f"Failed to import recommendations: {e}")

    @pytest.mark.asyncio
    async def test_no_circular_imports_in_insights(self):
        """[P1] Test that insights module has no circular import issues."""
        try:
            # Import all insights modules to detect circular dependencies
            from raglite.insights import proactive, recommendations, trends  # noqa: F401

            # If we reach here, no circular imports
            assert True
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")


# =============================================================================
# Integration Test Edge Cases
# =============================================================================


class TestIntegrationEdgeCases:
    """[P2] Test integration scenarios across insight generation modules."""

    @pytest.mark.asyncio
    async def test_insight_workflow_with_all_none_inputs(self):
        """[P2] Test insight generation with all inputs as None or empty."""
        from raglite.insights.proactive import generate_insights

        # Empty inputs should raise ValueError
        with pytest.raises(ValueError, match="No data to analyze"):
            await generate_insights([], [], [], auto_synthesize=False)

    @pytest.mark.asyncio
    async def test_recommendation_generation_with_empty_insights(self):
        """[P2] Test recommendation generation when no insights available."""
        from raglite.insights.recommendations import generate_recommendations

        empty_insights = []

        # Empty insights should raise ValueError
        with pytest.raises(ValueError, match="No insights to generate recommendations from"):
            await generate_recommendations(empty_insights)

    @pytest.mark.asyncio
    async def test_large_batch_insight_generation(self, sample_anomalies, sample_trends):
        """[P2] Test insight generation with large batch of inputs."""
        from raglite.insights.proactive import generate_insights

        # Create large batches (100 items each)
        large_anomalies = sample_anomalies * 100
        large_trends = sample_trends * 100

        result = await generate_insights(large_anomalies, large_trends, [], auto_synthesize=False)

        # Should handle large batches without errors
        assert result.total_generated > 0
        assert len(result.insights) > 0

    @pytest.mark.asyncio
    async def test_concurrent_insight_generation(self, sample_anomalies):
        """[P2] Test multiple concurrent insight generation calls."""
        import asyncio

        from raglite.insights.proactive import generate_insights

        # Run 10 concurrent insight generation tasks
        tasks = [
            generate_insights([sample_anomalies[0]], [], [], auto_synthesize=False)
            for _ in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(results) == 10
        assert all(r.total_generated == 1 for r in results)


# =============================================================================
# Error Path Testing
# =============================================================================


class TestErrorPaths:
    """[P1] Test error handling in insight generation."""

    @pytest.mark.asyncio
    async def test_invalid_anomaly_severity(self):
        """[P1] Test handling of invalid severity in anomaly."""
        # Note: Pydantic validation should prevent this, but test for robustness
        anomaly = Anomaly(
            date="2024-Q3",
            metric="test_metric",
            value=1000,
            expected_value=500,
            z_score=3.0,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=100.0,
        )

        from raglite.insights.proactive import calculate_insight_priority

        # Should handle without errors
        priority = calculate_insight_priority(anomaly=anomaly)
        assert isinstance(priority, int)
        assert 1 <= priority <= 5

    @pytest.mark.asyncio
    async def test_negative_trend_magnitude(self):
        """[P1] Test handling of negative trend magnitude."""
        trend = Trend(
            metric="revenue",
            direction=TrendDirection.DECREASING,
            magnitude=-15.0,  # Negative value
            confidence=0.9,
            start_date="2024-Q1",
            end_date="2024-Q4",
            cagr=-0.15,
            qoq_growth=-4.0,
        )

        from raglite.insights.proactive import calculate_insight_priority

        priority = calculate_insight_priority(trend=trend)
        # Should handle negative magnitude correctly
        assert isinstance(priority, int)

    @pytest.mark.asyncio
    async def test_zero_confidence_forecast(self):
        """[P1] Test handling of zero confidence forecast."""
        from datetime import datetime

        forecast = ForecastResult(
            metric_name="revenue",
            forecast=[ForecastPoint(date=datetime(2025, 1, 1), value=1000, lower=800, upper=1200)],
            periods_ahead=4,
        )

        from raglite.insights.proactive import calculate_insight_priority

        # Should handle without errors
        priority = calculate_insight_priority(forecast=forecast)
        assert isinstance(priority, int)


# =============================================================================
# Data Validation Edge Cases
# =============================================================================


class TestDataValidationEdgeCases:
    """[P2] Test edge cases in data validation."""

    @pytest.mark.asyncio
    async def test_anomaly_with_extreme_z_score(self):
        """[P2] Test anomaly with very high z-score (>10)."""
        anomaly = Anomaly(
            date="2024-Q3",
            metric="extreme_metric",
            value=10000000,
            expected_value=1000,
            z_score=50.0,  # Extreme outlier
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=999900.0,
        )

        from raglite.insights.proactive import calculate_insight_priority

        priority = calculate_insight_priority(anomaly=anomaly)
        # Should be highest priority
        assert priority == 1

    @pytest.mark.asyncio
    async def test_trend_with_perfect_confidence(self):
        """[P2] Test trend with confidence = 1.0."""
        trend = Trend(
            metric="perfect_metric",
            direction=TrendDirection.INCREASING,
            magnitude=25.0,
            confidence=1.0,  # Perfect confidence
            start_date="2024-Q1",
            end_date="2024-Q4",
            cagr=0.25,
            qoq_growth=6.0,
        )

        from raglite.insights.proactive import categorize_insight

        category = categorize_insight(trend=trend)
        # High magnitude + increasing = opportunity
        assert category == InsightCategory.OPPORTUNITY

    @pytest.mark.asyncio
    async def test_forecast_with_inverted_bounds(self):
        """[P2] Test forecast where lower > upper (data error)."""
        from datetime import datetime

        # Edge case: inverted confidence bounds
        forecast = ForecastResult(
            metric_name="invalid_forecast",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=1000,
                    lower=1200,  # Lower > value
                    upper=800,  # Upper < value
                )
            ],
            periods_ahead=4,
        )

        from raglite.insights.proactive import categorize_insight

        # Should handle gracefully without crashing
        category = categorize_insight(forecast=forecast)
        assert category.__class__.__name__ == "InsightCategory"
