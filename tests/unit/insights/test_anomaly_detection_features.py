"""Unit tests for Story 4.5: Anomaly Detection - Core Logic.

Continuation of tests.
"""

import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from raglite.shared.models import (
    AnomalySeverity,
    TimeSeriesData,
    TimeSeriesPoint,
)


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

        # Check for key log messages
        log_messages = [r.message for r in caplog.records]
        assert any("Detecting anomalies" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_logging_no_variance(self, caplog):
        """Test that zero variance case logs appropriately."""
        from raglite.insights.anomalies import detect_anomalies

        caplog.set_level(logging.INFO)

        # All identical values
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=10.0, label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        await detect_anomalies("revenue", timeseries)

        log_messages = [r.message for r in caplog.records]
        assert any("No variance" in msg for msg in log_messages)


# =============================================================================
# Test include_minor Parameter (Advisory Note 1)
# =============================================================================


class TestIncludeMinorParameter:
    """Tests for the include_minor parameter that enables MINOR severity detection."""

    @pytest.fixture
    def timeseries_with_minor_deviation(self) -> TimeSeriesData:
        """Create timeseries with a value that has 1.5 < |z| < 2.0."""
        # Use: [8, 9, 10, 11, 12, 10, 10, 10, 10, 13]
        # mean=10.3, std=1.42, Z(13)=(13-10.3)/1.42≈1.9 - MINOR range
        values = [8.0, 9.0, 10.0, 11.0, 12.0, 10.0, 10.0, 10.0, 10.0, 13.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 11)
        ]
        return TimeSeriesData(metric_name="revenue", points=points, interval="quarterly")

    @pytest.mark.asyncio
    async def test_include_minor_false_excludes_minor_anomalies(
        self, timeseries_with_minor_deviation
    ):
        """Test that include_minor=False (default) excludes MINOR severity."""
        from raglite.insights.anomalies import detect_anomalies

        result = await detect_anomalies("revenue", timeseries_with_minor_deviation)

        # With include_minor=False, only MODERATE and CRITICAL should be detected
        for anomaly in result.anomalies:
            assert anomaly.severity in [
                AnomalySeverity.MODERATE,
                AnomalySeverity.CRITICAL,
            ]
            assert anomaly.severity != AnomalySeverity.MINOR

    @pytest.mark.asyncio
    async def test_include_minor_true_detects_minor_anomalies(self):
        """Test that include_minor=True detects MINOR severity anomalies."""
        from raglite.insights.anomalies import detect_anomalies

        # Create data with values that have 1.5 < |z| <= 2.0
        # Using range [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]:
        # mean = 10, std = sqrt(10) ≈ 3.16
        # Z(15) = (15-10)/3.16 ≈ 1.58 → MINOR
        # Z(5) = (5-10)/3.16 ≈ -1.58 → MINOR
        values = [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0]

        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 12)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await detect_anomalies("revenue", timeseries, include_minor=True)

        # Should detect the 5.0 and 15.0 values as MINOR (Z ≈ ±1.58)
        minor_anomalies = [a for a in result.anomalies if a.severity == AnomalySeverity.MINOR]
        assert len(minor_anomalies) >= 1, "Should detect at least one MINOR anomaly"
        assert result.detection_method == "Z-score analysis (threshold: |z| > 1.5)"

    @pytest.mark.asyncio
    async def test_include_minor_affects_detection_method_string(self):
        """Test that detection_method reflects the threshold used."""
        from raglite.insights.anomalies import detect_anomalies

        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=10.0 + i, label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        # Default (include_minor=False)
        result_default = await detect_anomalies("revenue", timeseries)
        assert result_default.detection_method == "Z-score analysis (threshold: |z| > 2)"

        # With include_minor=True
        result_minor = await detect_anomalies("revenue", timeseries, include_minor=True)
        assert result_minor.detection_method == "Z-score analysis (threshold: |z| > 1.5)"


# =============================================================================
# Test auto_explain Parameter (Advisory Note 2)
# =============================================================================


class TestAutoExplainParameter:
    """Tests for the auto_explain parameter that controls LLM explanation generation."""

    @pytest.fixture
    def timeseries_with_outlier(self) -> TimeSeriesData:
        """Create timeseries with a clear outlier for explanation testing."""
        values = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 50.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        return TimeSeriesData(metric_name="revenue", points=points, interval="quarterly")

    @pytest.mark.asyncio
    async def test_auto_explain_false_leaves_reason_empty(self, timeseries_with_outlier):
        """Test that auto_explain=False (default) does not generate explanations."""
        from raglite.insights.anomalies import detect_anomalies

        result = await detect_anomalies("revenue", timeseries_with_outlier)

        # Default: auto_explain=False, so reason should be empty
        for anomaly in result.anomalies:
            assert anomaly.reason == "", "Reason should be empty when auto_explain=False"

    @pytest.mark.asyncio
    async def test_auto_explain_true_generates_explanations(self, timeseries_with_outlier):
        """Test that auto_explain=True generates LLM explanations."""
        from raglite.insights.anomalies import detect_anomalies

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="The revenue spike is likely due to seasonal factors or a large contract."
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await detect_anomalies("revenue", timeseries_with_outlier, auto_explain=True)

        # With auto_explain=True, anomalies should have explanations
        assert len(result.anomalies) >= 1
        for anomaly in result.anomalies:
            assert anomaly.reason != "", "Reason should be populated when auto_explain=True"
            assert "seasonal" in anomaly.reason.lower() or "spike" in anomaly.reason.lower()

    @pytest.mark.asyncio
    async def test_auto_explain_handles_api_errors_gracefully(self, timeseries_with_outlier):
        """Test that auto_explain handles LLM API errors without failing."""
        from raglite.insights.anomalies import detect_anomalies

        mock_client = MagicMock()
        mock_client.chat.complete.side_effect = Exception("API error")

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await detect_anomalies("revenue", timeseries_with_outlier, auto_explain=True)

        # Should still have anomalies, with fallback explanations
        assert len(result.anomalies) >= 1
        for anomaly in result.anomalies:
            assert "Anomaly detected" in anomaly.reason  # Fallback message

    @pytest.mark.asyncio
    async def test_combined_include_minor_and_auto_explain(self):
        """Test using both include_minor and auto_explain together."""
        from raglite.insights.anomalies import detect_anomalies

        # Create data with both MINOR and MODERATE anomalies
        values = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 12.0, 50.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 11)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test explanation"))]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await detect_anomalies(
                "revenue", timeseries, include_minor=True, auto_explain=True
            )

        # Should detect anomalies with explanations
        assert len(result.anomalies) >= 1
        assert result.detection_method == "Z-score analysis (threshold: |z| > 1.5)"
        for anomaly in result.anomalies:
            assert anomaly.reason != ""
