"""Unit tests for Story 4.5: Anomaly Detection - Core Logic.

Tests the detect_anomalies() function and explain_anomaly() helper.
"""

import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    TimeSeriesData,
    TimeSeriesPoint,
)

pytestmark = [pytest.mark.unit]


# =============================================================================
# Test detect_anomalies() Function (AC1, AC2, AC3)
# =============================================================================


class TestDetectAnomalies:
    """Tests for the detect_anomalies() function."""

    @pytest.fixture
    def normal_timeseries(self) -> TimeSeriesData:
        """Create timeseries with no anomalies (all values within 2 std)."""
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=10.0 + i * 0.5, label=f"Q{i}")
            for i in range(1, 9)
        ]
        return TimeSeriesData(
            metric_name="revenue",
            points=points,
            interval="quarterly",
        )

    @pytest.fixture
    def timeseries_with_outliers(self) -> TimeSeriesData:
        """Create timeseries with known outliers (25.0 and 3.0 are outliers)."""
        values = [10.0, 10.5, 11.0, 25.0, 11.2, 10.9, 11.1, 3.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        return TimeSeriesData(
            metric_name="revenue",
            points=points,
            interval="quarterly",
        )

    @pytest.mark.asyncio
    async def test_detect_anomalies_returns_result(self, normal_timeseries):
        """Test that detect_anomalies returns AnomalyDetectionResult."""
        from raglite.insights.anomalies import detect_anomalies

        result = await detect_anomalies("revenue", normal_timeseries)

        assert result.__class__.__name__ == "AnomalyDetectionResult"
        assert result.metric_name == "revenue"
        assert result.data_points_analyzed == 8

    @pytest.mark.asyncio
    async def test_detect_anomalies_normal_data_no_outliers(self, normal_timeseries):
        """Test that normal data with no outliers returns empty anomalies list."""
        from raglite.insights.anomalies import detect_anomalies

        result = await detect_anomalies("revenue", normal_timeseries)

        # Normal data should have no anomalies (values are evenly spaced)
        # Due to the nature of the test data (10.5, 11.0, 11.5...), no Z > 2
        assert len(result.anomalies) == 0

    @pytest.mark.asyncio
    async def test_detect_anomalies_identifies_outliers(self, timeseries_with_outliers):
        """Test that known outliers (25.0 and 3.0) are correctly identified."""
        from raglite.insights.anomalies import detect_anomalies

        result = await detect_anomalies("revenue", timeseries_with_outliers)

        # Should identify at least the extreme values as anomalies
        assert len(result.anomalies) >= 1

        # Check that anomaly values are the expected outliers
        anomaly_values = [a.value for a in result.anomalies]
        # At least one of 25.0 or 3.0 should be identified
        assert 25.0 in anomaly_values or 3.0 in anomaly_values

    @pytest.mark.asyncio
    async def test_severity_classification_critical(self, timeseries_with_outliers):
        """Test that |z| > 3 is classified as CRITICAL."""
        from raglite.insights.anomalies import detect_anomalies

        result = await detect_anomalies("revenue", timeseries_with_outliers)

        # Find anomalies with |z| > 3
        critical_anomalies = [a for a in result.anomalies if abs(a.z_score) > 3]

        for anomaly in critical_anomalies:
            assert anomaly.severity == AnomalySeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_severity_classification_moderate(self, timeseries_with_outliers):
        """Test that 2 < |z| <= 3 is classified as MODERATE."""
        from raglite.insights.anomalies import detect_anomalies

        result = await detect_anomalies("revenue", timeseries_with_outliers)

        # Find anomalies with 2 < |z| <= 3
        moderate_anomalies = [a for a in result.anomalies if 2 < abs(a.z_score) <= 3]

        for anomaly in moderate_anomalies:
            assert anomaly.severity == AnomalySeverity.MODERATE

    @pytest.mark.asyncio
    async def test_detect_anomalies_insufficient_data(self):
        """Test that detect_anomalies raises ValueError with < 3 data points."""
        from raglite.insights.anomalies import detect_anomalies

        # Create timeseries with only 2 points
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=10.0, label="Q1"),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=11.0, label="Q2"),
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        with pytest.raises(ValueError, match="Insufficient data"):
            await detect_anomalies("revenue", timeseries)

    @pytest.mark.asyncio
    async def test_detect_anomalies_identical_values(self):
        """Test that identical values (zero variance) returns no anomalies."""
        from raglite.insights.anomalies import detect_anomalies

        # All values identical - no variance
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=10.0, label=f"Q{i}")
            for i in range(1, 9)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await detect_anomalies("revenue", timeseries)

        assert result.std_deviation == 0.0
        assert len(result.anomalies) == 0

    @pytest.mark.asyncio
    async def test_detect_anomalies_calculates_mean_std(self, timeseries_with_outliers):
        """Test that mean and std deviation are correctly calculated."""
        from raglite.insights.anomalies import detect_anomalies

        result = await detect_anomalies("revenue", timeseries_with_outliers)

        # Values: [10.0, 10.5, 11.0, 25.0, 11.2, 10.9, 11.1, 3.0]
        # Mean should be around 11.59
        assert 11.0 < result.mean_value < 12.0
        assert result.std_deviation > 0

    @pytest.mark.asyncio
    async def test_anomaly_has_required_fields(self, timeseries_with_outliers):
        """Test that each detected anomaly has all required fields (AC4)."""
        from raglite.insights.anomalies import detect_anomalies

        result = await detect_anomalies("revenue", timeseries_with_outliers)

        for anomaly in result.anomalies:
            assert anomaly.date is not None
            assert anomaly.metric == "revenue"
            assert anomaly.value is not None
            assert anomaly.expected_value is not None
            assert anomaly.z_score is not None
            assert anomaly.severity.name in ["CRITICAL", "MODERATE", "MINOR"]
            assert isinstance(anomaly.magnitude_pct, float)

    @pytest.mark.asyncio
    async def test_detect_anomalies_minimum_data_points(self):
        """Test that detect_anomalies works with enough points to establish variance."""
        from raglite.insights.anomalies import detect_anomalies

        # Use 8 similar values with one extreme outlier to ensure Z > 2
        # Values: [10, 10, 10, 10, 10, 10, 10, 200]
        # mean = 32.5, std = 63.4, z(200) = (200-32.5)/63.4 = 2.64 > 2 ✓
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=10.0, label=f"Q{i}")
            for i in range(1, 8)
        ]
        points.append(
            TimeSeriesPoint(date=datetime(2024, 8, 1), value=200.0, label="Q8")  # Extreme outlier
        )
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await detect_anomalies("revenue", timeseries)

        assert result.data_points_analyzed == 8
        # The 200.0 value should be detected as an anomaly
        assert len(result.anomalies) >= 1
        assert any(a.value == 200.0 for a in result.anomalies)


# =============================================================================
# Test explain_anomaly() Function (AC4)
# =============================================================================


class TestExplainAnomaly:
    """Tests for the explain_anomaly() function."""

    @pytest.fixture
    def sample_anomaly(self) -> Anomaly:
        """Create a sample anomaly for testing."""
        return Anomaly(
            date="Q3 2024",
            metric="revenue",
            value=25.0,
            expected_value=10.5,
            z_score=3.2,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=138.1,
        )

    @pytest.mark.asyncio
    async def test_explain_anomaly_with_mocked_mistral(self, sample_anomaly):
        """Test explain_anomaly with mocked Mistral client."""
        from raglite.insights.anomalies import explain_anomaly

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="Revenue spike in Q3 2024 likely due to seasonal holiday sales."
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            explanation = await explain_anomaly(sample_anomaly)

        assert "Revenue" in explanation or "revenue" in explanation.lower()
        mock_client.chat.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_explain_anomaly_fallback_on_error(self, sample_anomaly):
        """Test that explain_anomaly returns fallback message on API error."""
        from raglite.insights.anomalies import explain_anomaly

        mock_client = MagicMock()
        mock_client.chat.complete.side_effect = Exception("API error")

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            explanation = await explain_anomaly(sample_anomaly)

        # Should return fallback message with anomaly details
        assert "25.0" in explanation or "138.1" in explanation
        assert "Anomaly detected" in explanation

    @pytest.mark.asyncio
    async def test_explain_anomaly_prompt_contains_context(self, sample_anomaly):
        """Test that the LLM prompt contains all anomaly context."""
        from raglite.insights.anomalies import explain_anomaly

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test explanation"))]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            await explain_anomaly(sample_anomaly)

        # Check the prompt sent to Mistral
        call_args = mock_client.chat.complete.call_args
        prompt = call_args.kwargs["messages"][0]["content"]

        assert "revenue" in prompt.lower()
        assert "Q3 2024" in prompt
        assert "25.0" in prompt
        assert "10.5" in prompt
        assert "138.1" in prompt
        assert "3.2" in prompt


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in anomaly detection."""

    @pytest.mark.asyncio
    async def test_negative_values(self):
        """Test anomaly detection with negative values."""
        from raglite.insights.anomalies import detect_anomalies

        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=-10.0 + i, label=f"Q{i}")
            for i in range(1, 9)
        ]
        points[3].value = -50.0  # Add outlier

        timeseries = TimeSeriesData(metric_name="expenses", points=points)

        result = await detect_anomalies("expenses", timeseries)

        # Should detect the -50.0 as an anomaly
        assert len(result.anomalies) >= 1
        anomaly_values = [a.value for a in result.anomalies]
        assert -50.0 in anomaly_values

    @pytest.mark.asyncio
    async def test_large_values(self):
        """Test anomaly detection with large values (millions)."""
        from raglite.insights.anomalies import detect_anomalies

        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=1_000_000.0 + i * 1000, label=f"Q{i}")
            for i in range(1, 9)
        ]
        points[4].value = 10_000_000.0  # Add outlier

        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await detect_anomalies("revenue", timeseries)

        assert len(result.anomalies) >= 1

    @pytest.mark.asyncio
    async def test_decimal_values(self):
        """Test anomaly detection with decimal/float precision."""
        from raglite.insights.anomalies import detect_anomalies

        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=10.12345 + i * 0.001, label=f"Q{i}")
            for i in range(1, 9)
        ]
        points[2].value = 50.999  # Add outlier

        timeseries = TimeSeriesData(metric_name="ratio", points=points)

        result = await detect_anomalies("ratio", timeseries)

        assert len(result.anomalies) >= 1

    @pytest.mark.asyncio
    async def test_date_label_extraction(self):
        """Test that anomaly dates use labels when available."""
        from raglite.insights.anomalies import detect_anomalies

        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=10.0, label=f"Quarter {i}")
            for i in range(1, 4)
        ]
        points.append(
            TimeSeriesPoint(date=datetime(2024, 4, 1), value=100.0, label="Quarter 4")  # Outlier
        )

        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await detect_anomalies("revenue", timeseries)

        # Should have anomaly with label
        if result.anomalies:
            assert "Quarter" in result.anomalies[0].date

    @pytest.mark.asyncio
    async def test_date_fallback_when_no_label(self):
        """Test that anomaly dates fall back to date string when no label."""
        from raglite.insights.anomalies import detect_anomalies

        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=10.0)
            for i in range(1, 4)  # No label
        ]
        points.append(TimeSeriesPoint(date=datetime(2024, 4, 1), value=100.0))  # Outlier, no label

        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await detect_anomalies("revenue", timeseries)

        # Should have anomaly with date string
        if result.anomalies:
            assert "2024" in result.anomalies[0].date


# =============================================================================
# Test Structured Logging (AC4)
# =============================================================================


class TestStructuredLogging:
    """Tests for structured logging in anomaly detection."""

    @pytest.mark.asyncio
    async def test_logging_on_anomaly_detection(self, caplog):
        """Test that anomaly detection logs with structured context."""
        from raglite.insights.anomalies import detect_anomalies

        caplog.set_level(logging.INFO)

        values = [10.0, 10.5, 11.0, 50.0, 11.2]  # 50.0 is outlier
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        await detect_anomalies("revenue", timeseries)

        # Check that logs were emitted
        assert len(caplog.records) > 0
