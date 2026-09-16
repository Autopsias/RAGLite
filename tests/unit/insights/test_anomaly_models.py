"""Unit tests for Story 4.5: Anomaly Detection - Models.

Tests Pydantic models and enums:
- AnomalySeverity enum
- Anomaly model
- AnomalyDetectionResult model
"""

import pytest

from raglite.shared.models import (
    Anomaly,
    AnomalyDetectionResult,
    AnomalySeverity,
)

pytestmark = [pytest.mark.unit]

# =============================================================================
# Test AnomalySeverity Enum (AC3)
# =============================================================================


class TestAnomalySeverity:
    """Tests for the AnomalySeverity enum."""

    def test_severity_values(self):
        """Test that AnomalySeverity has MINOR, MODERATE, CRITICAL values."""
        assert AnomalySeverity.MINOR.value == "minor"
        assert AnomalySeverity.MODERATE.value == "moderate"
        assert AnomalySeverity.CRITICAL.value == "critical"

    def test_severity_is_string_enum(self):
        """Test that AnomalySeverity is a string enum."""
        assert isinstance(AnomalySeverity.MINOR, str)
        assert AnomalySeverity.MINOR == "minor"

    def test_all_severity_levels(self):
        """Test iterating over all severity levels."""
        severities = list(AnomalySeverity)
        assert len(severities) == 3
        assert AnomalySeverity.MINOR in severities
        assert AnomalySeverity.MODERATE in severities
        assert AnomalySeverity.CRITICAL in severities


# =============================================================================
# Test Anomaly Model (AC4)
# =============================================================================


class TestAnomalyModel:
    """Tests for the Anomaly model."""

    def test_anomaly_with_all_fields(self):
        """Test creating Anomaly with all fields populated."""
        anomaly = Anomaly(
            date="Q3 2024",
            metric="revenue",
            value=25.0,
            expected_value=10.5,
            z_score=3.2,
            severity=AnomalySeverity.CRITICAL,
            reason="Significant revenue spike due to seasonal factors",
            magnitude_pct=138.1,
        )

        assert anomaly.date == "Q3 2024"
        assert anomaly.metric == "revenue"
        assert anomaly.value == 25.0
        assert anomaly.expected_value == 10.5
        assert anomaly.z_score == 3.2
        assert anomaly.severity == AnomalySeverity.CRITICAL
        assert "seasonal" in anomaly.reason
        assert anomaly.magnitude_pct == 138.1

    def test_anomaly_default_values(self):
        """Test Anomaly default values for optional fields."""
        anomaly = Anomaly(
            date="2024-01",
            metric="expenses",
            value=50.0,
            expected_value=30.0,
            z_score=2.5,
            severity=AnomalySeverity.MODERATE,
        )

        assert anomaly.reason == ""
        assert anomaly.magnitude_pct == 0.0

    def test_anomaly_serialization(self):
        """Test that Anomaly can be serialized to dict."""
        anomaly = Anomaly(
            date="Q1 2024",
            metric="cash_flow",
            value=5.0,
            expected_value=10.0,
            z_score=-2.3,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=-50.0,
        )

        data = anomaly.model_dump()
        assert data["date"] == "Q1 2024"
        assert data["metric"] == "cash_flow"
        assert data["value"] == 5.0
        assert data["z_score"] == -2.3
        assert data["severity"] == "moderate"

    def test_anomaly_required_fields(self):
        """Test that required fields raise error if missing."""
        with pytest.raises(ValueError):
            Anomaly(
                date="Q1 2024",
                # Missing required fields
            )


# =============================================================================
# Test AnomalyDetectionResult Model (AC1)
# =============================================================================


class TestAnomalyDetectionResultModel:
    """Tests for the AnomalyDetectionResult model."""

    def test_result_with_all_fields(self):
        """Test creating AnomalyDetectionResult with all fields."""
        anomalies = [
            Anomaly(
                date="Q3",
                metric="revenue",
                value=25.0,
                expected_value=10.5,
                z_score=3.2,
                severity=AnomalySeverity.CRITICAL,
            ),
        ]

        result = AnomalyDetectionResult(
            metric_name="revenue",
            anomalies=anomalies,
            data_points_analyzed=8,
            detection_method="Z-score analysis (threshold: |z| > 2)",
            mean_value=10.5,
            std_deviation=2.1,
        )

        assert result.metric_name == "revenue"
        assert len(result.anomalies) == 1
        assert result.data_points_analyzed == 8
        assert "Z-score" in result.detection_method
        assert result.mean_value == 10.5
        assert result.std_deviation == 2.1

    def test_result_default_values(self):
        """Test AnomalyDetectionResult default values."""
        result = AnomalyDetectionResult(
            metric_name="expenses",
            data_points_analyzed=10,
        )

        assert result.anomalies == []
        assert result.detection_method == "Z-score analysis (threshold: |z| > 2)"
        assert result.mean_value == 0.0
        assert result.std_deviation == 0.0

    def test_result_serialization(self):
        """Test that AnomalyDetectionResult can be serialized."""
        result = AnomalyDetectionResult(
            metric_name="revenue",
            anomalies=[],
            data_points_analyzed=5,
            mean_value=100.0,
            std_deviation=10.0,
        )

        data = result.model_dump()
        assert data["metric_name"] == "revenue"
        assert data["anomalies"] == []
        assert data["data_points_analyzed"] == 5
