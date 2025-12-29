"""Unit tests for Story 6.5: Automated Data Refresh Scheduler.

Tests AC6:
- Scheduler configuration and job execution
- Error handling and retry logic
- Manual trigger via MCP tool
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from raglite.external_data.refresh import (
    RETRY_DELAYS,
    RefreshResult,
    check_staleness,
)
from raglite.external_data.scheduler import (
    SOURCE_FREQUENCIES,
    RefreshFrequency,
    _parse_cron_expression,
)


class TestCronExpressionParsing:
    """Tests for cron expression parsing."""

    def test_parse_daily_cron(self) -> None:
        """Test parsing daily cron expression."""
        result = _parse_cron_expression("0 6 * * *")

        assert result["minute"] == "0"
        assert result["hour"] == "6"
        assert result["day"] == "*"
        assert result["month"] == "*"
        assert result["day_of_week"] == "*"

    def test_parse_weekly_cron(self) -> None:
        """Test parsing weekly cron expression (Sunday)."""
        result = _parse_cron_expression("0 6 * * 0")

        assert result["minute"] == "0"
        assert result["hour"] == "6"
        assert result["day"] == "*"
        assert result["month"] == "*"
        assert result["day_of_week"] == "0"

    def test_parse_monthly_cron(self) -> None:
        """Test parsing monthly cron expression (1st day)."""
        result = _parse_cron_expression("0 6 1 * *")

        assert result["minute"] == "0"
        assert result["hour"] == "6"
        assert result["day"] == "1"
        assert result["month"] == "*"
        assert result["day_of_week"] == "*"

    def test_parse_invalid_cron_too_few_parts(self) -> None:
        """Test that invalid cron expression raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cron expression"):
            _parse_cron_expression("0 6 *")

    def test_parse_invalid_cron_too_many_parts(self) -> None:
        """Test that invalid cron expression raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cron expression"):
            _parse_cron_expression("0 6 * * * *")


class TestSourceFrequencies:
    """Tests for source frequency configuration (AC2)."""

    def test_daily_sources_configured(self) -> None:
        """Test that daily sources are configured."""
        daily_sources = [
            name for name, freq in SOURCE_FREQUENCIES.items() if freq == RefreshFrequency.DAILY
        ]

        assert "IPMA" in daily_sources
        assert "OMIE" in daily_sources
        assert "CO2_EUA" in daily_sources

    def test_weekly_sources_configured(self) -> None:
        """Test that weekly sources are configured."""
        weekly_sources = [
            name for name, freq in SOURCE_FREQUENCIES.items() if freq == RefreshFrequency.WEEKLY
        ]

        assert "INE_BuildingPermits" in weekly_sources
        assert "BPstat_MortgageLoans" in weekly_sources
        assert "EUOil_Diesel" in weekly_sources

    def test_monthly_sources_configured(self) -> None:
        """Test that monthly sources are configured."""
        monthly_sources = [
            name for name, freq in SOURCE_FREQUENCIES.items() if freq == RefreshFrequency.MONTHLY
        ]

        assert "INE_ConstructionOutput" in monthly_sources
        assert "INE_ConstructionCostIndex" in monthly_sources
        assert "ATIC_CementConsumption" in monthly_sources


class TestStalenessDetection:
    """Tests for staleness detection (AC5)."""

    def test_check_staleness_fresh_data(self) -> None:
        """Test that fresh data is not flagged as stale."""
        # Data refreshed 5 days ago
        last_refresh = datetime.now(UTC) - timedelta(days=5)

        with patch("raglite.external_data.refresh.settings") as mock_settings:
            mock_settings.external_data_stale_days = 30
            is_stale = check_staleness("test_source", last_refresh)

        assert is_stale is False

    def test_check_staleness_stale_data(self) -> None:
        """Test that old data is flagged as stale (AC5)."""
        # Data refreshed 35 days ago
        last_refresh = datetime.now(UTC) - timedelta(days=35)

        with patch("raglite.external_data.refresh.settings") as mock_settings:
            mock_settings.external_data_stale_days = 30
            is_stale = check_staleness("test_source", last_refresh)

        assert is_stale is True

    def test_check_staleness_never_refreshed(self) -> None:
        """Test that never-refreshed data is flagged as stale."""
        is_stale = check_staleness("test_source", None)

        assert is_stale is True

    def test_check_staleness_exactly_at_threshold(self) -> None:
        """Test staleness at exactly 30 days (not stale)."""
        last_refresh = datetime.now(UTC) - timedelta(days=30)

        with patch("raglite.external_data.refresh.settings") as mock_settings:
            mock_settings.external_data_stale_days = 30
            is_stale = check_staleness("test_source", last_refresh)

        assert is_stale is False

    def test_check_staleness_just_over_threshold(self) -> None:
        """Test staleness at 31 days (stale)."""
        last_refresh = datetime.now(UTC) - timedelta(days=31)

        with patch("raglite.external_data.refresh.settings") as mock_settings:
            mock_settings.external_data_stale_days = 30
            is_stale = check_staleness("test_source", last_refresh)

        assert is_stale is True

    def test_check_staleness_naive_datetime(self) -> None:
        """Test that naive datetime is handled correctly."""
        # Naive datetime (no timezone info)
        last_refresh = datetime.now() - timedelta(days=5)

        with patch("raglite.external_data.refresh.settings") as mock_settings:
            mock_settings.external_data_stale_days = 30
            is_stale = check_staleness("test_source", last_refresh)

        assert is_stale is False


class TestRetryConfiguration:
    """Tests for retry configuration (AC3)."""

    def test_retry_delays_exponential_backoff(self) -> None:
        """Test that retry delays follow exponential backoff (1s, 2s, 4s)."""
        assert RETRY_DELAYS == [1, 2, 4]

    def test_retry_delays_length(self) -> None:
        """Test that there are exactly 3 retry delays."""
        assert len(RETRY_DELAYS) == 3


class TestRefreshResult:
    """Tests for RefreshResult dataclass."""

    def test_refresh_result_success(self) -> None:
        """Test successful refresh result."""
        result = RefreshResult(
            source_name="IPMA",
            success=True,
            records_updated=7,
            duration_seconds=1.5,
            attempts=1,
        )

        assert result.source_name == "IPMA"
        assert result.success is True
        assert result.records_updated == 7
        assert result.duration_seconds == 1.5
        assert result.error_message is None
        assert result.attempts == 1

    def test_refresh_result_failure(self) -> None:
        """Test failed refresh result."""
        result = RefreshResult(
            source_name="OMIE",
            success=False,
            error_message="Connection timeout",
            attempts=3,
        )

        assert result.source_name == "OMIE"
        assert result.success is False
        assert result.records_updated == 0
        assert result.error_message == "Connection timeout"
        assert result.attempts == 3
