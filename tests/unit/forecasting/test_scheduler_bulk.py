"""Unit tests for Story 6.5: Automated Data Refresh Scheduler.

Tests AC6:
- Scheduler configuration and job execution
- Error handling and retry logic
- Manual trigger via MCP tool
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.external_data.refresh import (
    BulkRefreshResult,
    RefreshResult,
)
from raglite.external_data.scheduler import (
    RefreshFrequency,
)


class TestBulkRefreshResult:
    """Tests for BulkRefreshResult dataclass."""

    def test_bulk_refresh_result(self) -> None:
        """Test bulk refresh result aggregation."""
        results = [
            RefreshResult(source_name="IPMA", success=True, records_updated=7),
            RefreshResult(source_name="OMIE", success=True, records_updated=5),
            RefreshResult(source_name="CO2_EUA", success=False, error_message="API error"),
        ]

        bulk = BulkRefreshResult(
            total_sources=3,
            successful=2,
            failed=1,
            results=results,
            total_duration_seconds=5.0,
        )

        assert bulk.total_sources == 3
        assert bulk.successful == 2
        assert bulk.failed == 1
        assert len(bulk.results) == 3
        assert bulk.total_duration_seconds == 5.0


class TestRefreshFrequencyEnum:
    """Tests for RefreshFrequency enum."""

    def test_frequency_values(self) -> None:
        """Test that frequency enum has expected values."""
        assert RefreshFrequency.DAILY.value == "daily"
        assert RefreshFrequency.WEEKLY.value == "weekly"
        assert RefreshFrequency.MONTHLY.value == "monthly"


class TestRetryWithBackoff:
    """Tests for retry with exponential backoff (AC3)."""

    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self) -> None:
        """Test successful operation on first attempt."""
        from raglite.external_data.refresh_helpers import retry_with_backoff

        async def success_func() -> int:
            return 42

        with patch("raglite.external_data.refresh_helpers.settings") as mock_settings:
            mock_settings.external_data_retry_attempts = 3
            success, attempts, error, result = await retry_with_backoff(success_func, "test_source")

        assert success is True
        assert attempts == 1
        assert error is None
        assert result == 42

    @pytest.mark.asyncio
    async def test_retry_success_second_attempt(self) -> None:
        """Test successful operation after first retry."""
        from raglite.external_data.exceptions import ExternalDataFetchError
        from raglite.external_data.refresh_helpers import retry_with_backoff

        call_count = 0

        async def fail_then_success() -> int:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ExternalDataFetchError("test", "First attempt fails")
            return 7

        with patch("raglite.external_data.refresh_helpers.settings") as mock_settings:
            mock_settings.external_data_retry_attempts = 3
            with patch("raglite.external_data.refresh_helpers.asyncio.sleep", new=AsyncMock()):
                success, attempts, error, result = await retry_with_backoff(
                    fail_then_success, "test_source"
                )

        assert success is True
        assert attempts == 2
        assert error is None
        assert result == 7

    @pytest.mark.asyncio
    async def test_retry_all_attempts_fail(self) -> None:
        """Test failure after all retry attempts (AC3)."""
        from raglite.external_data.exceptions import ExternalDataFetchError
        from raglite.external_data.refresh_helpers import retry_with_backoff

        async def always_fails() -> int:
            raise ExternalDataFetchError("test", "Always fails")

        with patch("raglite.external_data.refresh_helpers.settings") as mock_settings:
            mock_settings.external_data_retry_attempts = 3
            with patch("raglite.external_data.refresh_helpers.asyncio.sleep", new=AsyncMock()):
                success, attempts, error, result = await retry_with_backoff(
                    always_fails, "test_source"
                )

        assert success is False
        assert attempts == 3
        assert "Always fails" in str(error)
        assert result is None

    @pytest.mark.asyncio
    async def test_retry_unexpected_error(self) -> None:
        """Test retry behavior with unexpected exception."""
        from raglite.external_data.refresh_helpers import retry_with_backoff

        async def raises_unexpected() -> int:
            raise RuntimeError("Unexpected error")

        with patch("raglite.external_data.refresh_helpers.settings") as mock_settings:
            mock_settings.external_data_retry_attempts = 3
            with patch("raglite.external_data.refresh_helpers.asyncio.sleep", new=AsyncMock()):
                success, attempts, error, result = await retry_with_backoff(
                    raises_unexpected, "test_source"
                )

        assert success is False
        assert attempts == 3
        assert "RuntimeError" in str(error)
        assert result is None


class TestRefreshSource:
    """Tests for refresh_source function (AC4)."""

    @pytest.mark.asyncio
    async def test_refresh_unknown_source_raises(self) -> None:
        """Test that unknown source name raises ValueError."""
        from raglite.external_data.refresh import refresh_source

        with pytest.raises(ValueError, match="Unknown source"):
            await refresh_source("UNKNOWN_SOURCE")

    @pytest.mark.asyncio
    async def test_refresh_source_returns_result(self) -> None:
        """Test that refresh_source returns RefreshResult."""
        from raglite.external_data.refresh import refresh_source

        # Mock the refresh function via the SOURCE_REFRESH_FUNCTIONS mapping
        mock_refresh_result = RefreshResult(
            source_name="IPMA",
            success=True,
            records_updated=7,
        )

        async def mock_ipma_refresh(storage):
            return mock_refresh_result

        with patch("raglite.external_data.refresh.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            with patch(
                "raglite.external_data.refresh.SOURCE_REFRESH_FUNCTIONS",
                {"IPMA": mock_ipma_refresh},
            ):
                with patch(
                    "raglite.external_data.refresh.ExternalDataStorage"
                ) as mock_storage_class:
                    mock_storage = MagicMock()
                    mock_storage.get_source.return_value = None
                    mock_storage_class.return_value = mock_storage

                    result = await refresh_source("IPMA")

        assert result.__class__.__name__ == "RefreshResult"
        assert result.source_name == "IPMA"
        assert result.success is True


class TestTriggerJobNow:
    """Tests for trigger_job_now function."""

    @pytest.mark.asyncio
    async def test_trigger_existing_job(self) -> None:
        """Test triggering an existing job."""
        import raglite.external_data.scheduler as scheduler_module
        from raglite.external_data.scheduler import trigger_job_now

        # Create a mock scheduler with a job
        mock_scheduler = MagicMock()
        mock_job = MagicMock()
        mock_scheduler.get_job.return_value = mock_job
        scheduler_module._scheduler = mock_scheduler

        result = await trigger_job_now("refresh_daily")

        assert result is True
        mock_scheduler.get_job.assert_called_once_with("refresh_daily")
        mock_scheduler.modify_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_nonexistent_job(self) -> None:
        """Test triggering a job that doesn't exist."""
        import raglite.external_data.scheduler as scheduler_module
        from raglite.external_data.scheduler import trigger_job_now

        # Create a mock scheduler with no jobs
        mock_scheduler = MagicMock()
        mock_scheduler.get_job.return_value = None
        scheduler_module._scheduler = mock_scheduler

        result = await trigger_job_now("nonexistent_job")

        assert result is False
        mock_scheduler.get_job.assert_called_once_with("nonexistent_job")
        mock_scheduler.modify_job.assert_not_called()


class TestMCPTool:
    """Tests for refresh_external_data MCP tool (AC4)."""

    @pytest.mark.asyncio
    async def test_mcp_tool_refresh_all(self) -> None:
        """Test MCP tool refreshes all sources."""
        from raglite.main import refresh_external_data

        mock_result = BulkRefreshResult(
            total_sources=8,
            successful=7,
            failed=1,
            results=[
                RefreshResult(source_name="IPMA", success=True, records_updated=7),
            ],
            total_duration_seconds=10.0,
        )

        with patch(
            "raglite.external_data.refresh.refresh_all_sources",
            new=AsyncMock(return_value=mock_result),
        ):
            # Access the underlying function via .fn attribute (FastMCP pattern)
            response = await refresh_external_data.fn(source_name=None)

        import json

        data = json.loads(response)
        assert data["total_sources"] == 8
        assert data["successful"] == 7
        assert data["failed"] == 1

    @pytest.mark.asyncio
    async def test_mcp_tool_refresh_specific_source(self) -> None:
        """Test MCP tool refreshes specific source."""
        from raglite.main import refresh_external_data

        mock_result = RefreshResult(
            source_name="IPMA",
            success=True,
            records_updated=7,
            duration_seconds=1.5,
        )

        with patch(
            "raglite.external_data.refresh.refresh_source",
            new=AsyncMock(return_value=mock_result),
        ):
            # Access the underlying function via .fn attribute (FastMCP pattern)
            response = await refresh_external_data.fn(source_name="IPMA")

        import json

        data = json.loads(response)
        assert data["source_name"] == "IPMA"
        assert data["success"] is True
        assert data["records_updated"] == 7

    @pytest.mark.asyncio
    async def test_mcp_tool_invalid_source_returns_error(self) -> None:
        """Test MCP tool returns error for invalid source."""
        from raglite.main import refresh_external_data

        with patch(
            "raglite.external_data.refresh.refresh_source",
            new=AsyncMock(side_effect=ValueError("Unknown source: INVALID")),
        ):
            # Access the underlying function via .fn attribute (FastMCP pattern)
            response = await refresh_external_data.fn(source_name="INVALID")

        import json

        data = json.loads(response)
        assert "error" in data
        assert "Unknown source" in data["error"]
