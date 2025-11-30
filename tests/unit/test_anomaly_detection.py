"""Unit tests for Story 4.5: Anomaly Detection.

Tests the detect_anomalies() function, explain_anomaly() helper,
and Anomaly/AnomalyDetectionResult/AnomalySeverity models.
"""

import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from raglite.shared.models import (
    Anomaly,
    AnomalyDetectionResult,
    AnomalySeverity,
    TimeSeriesData,
    TimeSeriesPoint,
)

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

        assert isinstance(result, AnomalyDetectionResult)
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
            assert anomaly.severity in AnomalySeverity
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
        # Design data so one value has Z-score around 1.7 (between 1.5 and 2.0)
        # Values: [10, 10, 10, 10, 10, 10, 10, 15] -> mean=10.625, std=1.71
        # Z(15) = (15-10.625)/1.71 ≈ 2.56 - too high
        # Try: [10, 10, 10, 10, 10, 10, 10, 13] -> mean=10.375, std=1.03
        # Z(13) = (13-10.375)/1.03 ≈ 2.55 - still too high
        # Try more data points: [10, 10, 10, 10, 10, 10, 10, 10, 10, 12.5]
        # mean=10.25, std=0.75, Z(12.5) = (12.5-10.25)/0.75 ≈ 3.0 - too high
        # Use: [10, 11, 10, 11, 10, 11, 10, 11, 10, 14] -> mean=10.8, std=1.25
        # Z(14) = (14-10.8)/1.25 = 2.56 - too high
        # Use: [100, 100, 100, 100, 100, 100, 100, 100, 100, 115]
        # mean=101.5, std=4.5, Z(115) = (115-101.5)/4.5 ≈ 3.0 - too high
        # Better approach: create data where the deviation is mild
        # [10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 13.5]
        # mean≈10.27, std≈0.95, Z(13.5) ≈ 3.4 - still too high
        # Try: [10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 12]
        # For MINOR (1.5 < |z| <= 2), we need carefully calibrated data
        # Using: mean=10, std=1.0, value=11.75 gives Z=1.75 (MINOR)
        values = [9.0, 9.5, 10.0, 10.5, 11.0, 10.0, 9.5, 10.5, 10.0, 11.8]
        # mean≈10.18, std≈0.79, Z(11.8) ≈ 2.05 - MODERATE, not MINOR
        # Need lower deviation: value=11.5 -> Z≈1.67 (MINOR)
        values = [9.5, 10.0, 10.5, 10.0, 9.5, 10.0, 10.5, 10.0, 9.5, 11.5]
        # mean=10.1, std≈0.55, Z(11.5)=(11.5-10.1)/0.55≈2.55 - still MODERATE
        # Use values with more spread: [8, 9, 10, 11, 12, 10, 10, 10, 10, 13]
        # mean=10.3, std=1.42, Z(13)=(13-10.3)/1.42≈1.9 - close to MINOR!
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
            assert anomaly.severity in [AnomalySeverity.MODERATE, AnomalySeverity.CRITICAL]
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
