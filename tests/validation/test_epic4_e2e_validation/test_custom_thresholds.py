"""Tests for custom threshold configuration."""

from tests.validation.test_epic4_e2e_validation.orchestrator import Epic4ValidationOrchestrator


class TestCustomThresholds:
    """Tests for custom threshold configuration."""

    def test_custom_thresholds(self):
        """Test orchestrator with custom thresholds."""
        orchestrator = Epic4ValidationOrchestrator(
            forecast_threshold=10.0,  # Stricter
            insight_threshold=85.0,  # Stricter
            recommendation_threshold=90.0,  # Stricter
        )

        assert orchestrator.forecast_validator.threshold_pct == 10.0
        assert orchestrator.insight_validator.threshold_pct == 85.0
        assert orchestrator.recommendation_validator.threshold_pct == 90.0
