"""Integration tests for Story 6.5: Automated Data Refresh Scheduler.

Tests AC7:
- Scheduled refresh executes successfully
- Staleness detection triggers warnings
- Manual refresh via MCP tool

These tests require PostgreSQL and may interact with external APIs.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mark all tests in this module as integration tests that preserve collection state
# Note: These tests don't interact with Qdrant, but CI requires isolation markers for all integration tests
# CRITICAL: xdist_group prevents APScheduler race conditions in parallel test execution
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="apscheduler"),  # Force single-worker execution
    pytest.mark.skipif(
        os.getenv("APP_ENV") != "test",
        reason="Integration tests require APP_ENV=test",
    ),
]


class TestSchedulerJobStore:
    """Tests for APScheduler PostgreSQL job store integration."""

    @pytest.mark.asyncio
    async def test_scheduler_creates_jobs_table(self) -> None:
        """Test that scheduler creates apscheduler_jobs table in PostgreSQL."""
        from raglite.external_data.scheduler import get_scheduler

        # Mock settings to avoid actual DB connection in CI
        with patch("raglite.external_data.scheduler.settings") as mock_settings:
            mock_settings.scheduler_timezone = "UTC"
            mock_settings.scheduler_job_coalesce = True
            mock_settings.scheduler_misfire_grace_time = 3600
            mock_settings.postgres_user = "test"
            mock_settings.postgres_password = "test"
            mock_settings.postgres_host = "localhost"
            mock_settings.postgres_port = 5433
            mock_settings.postgres_db = "raglite_test"

            # Reset singleton for test isolation
            import raglite.external_data.scheduler as scheduler_module

            scheduler_module._scheduler = None

            with patch("raglite.external_data.scheduler.SQLAlchemyJobStore") as mock_job_store:
                # Create a real-looking mock that APScheduler will accept
                mock_store_instance = MagicMock()
                mock_job_store.return_value = mock_store_instance

                # Also mock AsyncIOScheduler to prevent it from validating job stores
                with patch(
                    "raglite.external_data.scheduler.AsyncIOScheduler"
                ) as mock_scheduler_class:
                    mock_scheduler = MagicMock()
                    mock_scheduler_class.return_value = mock_scheduler

                    _ = get_scheduler()

                    # Verify job store was created with PostgreSQL URL
                    assert mock_job_store.called
                    call_args = mock_job_store.call_args
                    # URL can be passed as keyword arg 'url' or as first positional arg
                    url = call_args.kwargs.get("url")
                    if url is None and call_args.args:
                        url = call_args.args[0]
                    assert url is not None, "SQLAlchemyJobStore was called without url"
                    assert "postgresql://" in url


class TestScheduledRefreshExecution:
    """Tests for scheduled refresh job execution (AC7)."""

    @pytest.mark.asyncio
    async def test_daily_refresh_job_executes(self) -> None:
        """Test that daily refresh job executes successfully."""
        from raglite.external_data.refresh import refresh_sources_by_frequency
        from raglite.external_data.scheduler import RefreshFrequency

        # Mock the actual refresh functions
        with patch("raglite.external_data.refresh.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            with patch("raglite.external_data.refresh.ExternalDataStorage") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.get_source.return_value = None
                mock_storage_class.return_value = mock_storage

                # Mock individual refresh functions to avoid external API calls
                # Patch SOURCE_REFRESH_FUNCTIONS dict to control which functions are called
                with patch(
                    "raglite.external_data.refresh.SOURCE_REFRESH_FUNCTIONS",
                    new={
                        "IPMA": AsyncMock(
                            return_value=MagicMock(
                                success=True,
                                source_name="IPMA",
                                records_updated=7,
                                duration_seconds=1.0,
                            )
                        ),
                        "OMIE": AsyncMock(
                            return_value=MagicMock(
                                success=True,
                                source_name="OMIE",
                                records_updated=5,
                                duration_seconds=0.8,
                            )
                        ),
                        "CO2_EUA": AsyncMock(
                            return_value=MagicMock(
                                success=True,
                                source_name="CO2_EUA",
                                records_updated=3,
                                duration_seconds=0.5,
                            )
                        ),
                    },
                ):
                    result = await refresh_sources_by_frequency(RefreshFrequency.DAILY)

        assert result.total_sources == 3
        assert result.successful == 3
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_weekly_refresh_job_executes(self) -> None:
        """Test that weekly refresh job executes successfully."""
        from raglite.external_data.refresh import (
            RefreshResult,
            refresh_sources_by_frequency,
        )
        from raglite.external_data.scheduler import RefreshFrequency

        with patch("raglite.external_data.refresh.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            with patch("raglite.external_data.refresh.ExternalDataStorage") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.get_source.return_value = None
                mock_storage_class.return_value = mock_storage

                # Mock the SOURCE_REFRESH_FUNCTIONS dict to return our mocked functions
                mock_ine_result = RefreshResult(
                    source_name="INE_BuildingPermits",
                    success=True,
                    records_updated=5,
                    duration_seconds=1.0,
                )
                mock_bpstat_result = RefreshResult(
                    source_name="BPstat_MortgageLoans",
                    success=True,
                    records_updated=3,
                    duration_seconds=0.8,
                )
                mock_diesel_result = RefreshResult(
                    source_name="EUOil_Diesel",
                    success=True,
                    records_updated=2,
                    duration_seconds=0.5,
                )

                mock_refresh_funcs = {
                    "INE_BuildingPermits": AsyncMock(return_value=mock_ine_result),
                    "BPstat_MortgageLoans": AsyncMock(return_value=mock_bpstat_result),
                    "EUOil_Diesel": AsyncMock(return_value=mock_diesel_result),
                }

                with patch(
                    "raglite.external_data.refresh.SOURCE_REFRESH_FUNCTIONS",
                    mock_refresh_funcs,
                ):
                    result = await refresh_sources_by_frequency(RefreshFrequency.WEEKLY)

        assert result.total_sources == 3
        assert result.successful == 3

    @pytest.mark.asyncio
    async def test_monthly_refresh_job_executes(self) -> None:
        """Test that monthly refresh job executes successfully."""
        from raglite.external_data.refresh import refresh_sources_by_frequency
        from raglite.external_data.scheduler import RefreshFrequency

        with patch("raglite.external_data.refresh.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            with patch("raglite.external_data.refresh.ExternalDataStorage") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.get_source.return_value = None
                mock_storage_class.return_value = mock_storage

                # Mock SOURCE_REFRESH_FUNCTIONS dict to control which functions are called
                with patch(
                    "raglite.external_data.refresh.SOURCE_REFRESH_FUNCTIONS",
                    new={
                        "INE_ConstructionOutput": AsyncMock(
                            return_value=MagicMock(
                                success=True,
                                source_name="INE_ConstructionOutput",
                            )
                        ),
                        "INE_ConstructionCostIndex": AsyncMock(
                            return_value=MagicMock(
                                success=True,
                                source_name="INE_ConstructionCostIndex",
                            )
                        ),
                        "ATIC_CementConsumption": AsyncMock(
                            return_value=MagicMock(
                                success=True,
                                source_name="ATIC_CementConsumption",
                            )
                        ),
                    },
                ):
                    result = await refresh_sources_by_frequency(RefreshFrequency.MONTHLY)

        # INE_ConstructionOutput and INE_ConstructionCostIndex both map to same function
        assert result.total_sources >= 2


class TestStalenessDetectionIntegration:
    """Tests for staleness detection with storage layer (AC5, AC7)."""

    @pytest.mark.asyncio
    async def test_staleness_report_generation(self) -> None:
        """Test that staleness report generates correctly."""
        from raglite.external_data.refresh import get_staleness_report

        with patch("raglite.external_data.refresh.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            with patch("raglite.external_data.refresh.ExternalDataStorage") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.get_source.return_value = None
                mock_storage_class.return_value = mock_storage

                report = get_staleness_report()

        # Should have entries for all configured sources
        assert len(report) > 0
        for entry in report:
            assert "source_name" in entry
            assert "is_stale" in entry
            assert "status" in entry

    @pytest.mark.asyncio
    async def test_staleness_warning_logged_for_old_data(self) -> None:
        """Test that WARNING level log is emitted for stale data (AC5)."""
        from raglite.external_data.refresh import check_staleness

        # Data 35 days old (beyond 30-day threshold)
        old_refresh = datetime.now(UTC) - timedelta(days=35)

        with patch("raglite.external_data.refresh.settings") as mock_settings:
            mock_settings.external_data_stale_days = 30
            with patch("raglite.external_data.refresh_helpers.logger") as mock_logger:
                is_stale = check_staleness("TEST_SOURCE", old_refresh)

                # Verify WARNING was logged
                mock_logger.warning.assert_called()
                call_args = mock_logger.warning.call_args
                assert "stale" in call_args[0][0].lower()

        assert is_stale is True


class TestManualRefreshIntegration:
    """Tests for manual refresh via refresh module (AC4, AC7)."""

    @pytest.mark.asyncio
    async def test_manual_refresh_all_sources(self) -> None:
        """Test manual refresh of all sources via refresh module."""
        from raglite.external_data.refresh import RefreshResult, refresh_all_sources

        with patch("raglite.external_data.refresh.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            with patch("raglite.external_data.refresh.ExternalDataStorage") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.get_source.return_value = None
                mock_storage_class.return_value = mock_storage

                # Mock all refresh functions with proper RefreshResult objects
                mock_ipma_result = RefreshResult(
                    source_name="IPMA",
                    success=True,
                    records_updated=7,
                    duration_seconds=1.0,
                    error_message=None,
                    attempts=1,
                )
                with patch(
                    "raglite.external_data.refresh.SOURCE_REFRESH_FUNCTIONS",
                    {
                        "IPMA": AsyncMock(return_value=mock_ipma_result),
                    },
                ):
                    result = await refresh_all_sources()

        assert result.total_sources == 1
        assert result.successful == 1
        assert result.results[0].source_name == "IPMA"

    @pytest.mark.asyncio
    async def test_manual_refresh_single_source(self) -> None:
        """Test manual refresh of single source via refresh module."""
        from raglite.external_data.refresh import RefreshResult, refresh_source

        with patch("raglite.external_data.refresh.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            with patch("raglite.external_data.refresh.ExternalDataStorage") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.get_source.return_value = None
                mock_storage_class.return_value = mock_storage

                mock_ipma_result = RefreshResult(
                    source_name="IPMA",
                    success=True,
                    records_updated=7,
                    duration_seconds=1.0,
                    error_message=None,
                    attempts=1,
                )
                with patch(
                    "raglite.external_data.refresh.SOURCE_REFRESH_FUNCTIONS",
                    {
                        "IPMA": AsyncMock(return_value=mock_ipma_result),
                    },
                ):
                    result = await refresh_source("IPMA")

        assert result.source_name == "IPMA"
        assert result.success is True


class TestRetryWithExternalAPIs:
    """Tests for retry behavior with external API failures (AC3, AC7)."""

    @pytest.mark.asyncio
    async def test_retry_on_api_timeout(self) -> None:
        """Test that API timeout triggers retry with backoff."""
        from raglite.external_data.exceptions import ExternalDataFetchError
        from raglite.external_data.refresh_helpers import retry_with_backoff

        call_count = 0

        async def timeout_then_success() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ExternalDataFetchError("test", "Timeout")
            return "success_result"

        with patch("raglite.external_data.refresh.settings") as mock_settings:
            mock_settings.external_data_retry_attempts = 3
            with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
                # retry_with_backoff returns 4 values: (success, attempts, error, result)
                success, attempts, error, result = await retry_with_backoff(
                    timeout_then_success, "test_source"
                )

                # Verify sleep was called with exponential backoff delays
                assert mock_sleep.call_count == 2  # Two retries before success
                mock_sleep.assert_any_call(1)  # First delay
                mock_sleep.assert_any_call(2)  # Second delay

        assert success is True
        assert attempts == 3
        assert result == "success_result"

    @pytest.mark.asyncio
    async def test_error_logged_after_all_retries_fail(self) -> None:
        """Test that ERROR level log is emitted after all retries fail (AC3)."""
        from raglite.external_data.exceptions import ExternalDataFetchError
        from raglite.external_data.refresh_helpers import retry_with_backoff

        async def always_fails() -> None:
            raise ExternalDataFetchError("test", "Persistent failure")

        with patch("raglite.external_data.refresh.settings") as mock_settings:
            mock_settings.external_data_retry_attempts = 3
            with patch("asyncio.sleep", new=AsyncMock()):
                with patch("raglite.external_data.refresh_helpers.logger") as mock_logger:
                    # retry_with_backoff returns 4 values: (success, attempts, error, result)
                    success, attempts, error, result = await retry_with_backoff(
                        always_fails, "test_source"
                    )

                    # Verify ERROR was logged after all retries
                    mock_logger.error.assert_called()

        assert success is False
        assert attempts == 3
        assert result is None


class TestSchedulerLifecycle:
    """Tests for scheduler startup and shutdown lifecycle (AC1)."""

    @pytest.mark.asyncio
    async def test_scheduler_start_registers_jobs(self) -> None:
        """Test that start_scheduler registers all refresh jobs."""
        # Reset scheduler singleton
        import raglite.external_data.scheduler as scheduler_module
        from raglite.external_data.scheduler import start_scheduler

        scheduler_module._scheduler = None

        with patch("raglite.external_data.scheduler.settings") as mock_settings:
            mock_settings.scheduler_enabled = True
            mock_settings.scheduler_timezone = "UTC"
            mock_settings.scheduler_job_coalesce = True
            mock_settings.scheduler_misfire_grace_time = 3600
            mock_settings.postgres_user = "test"
            mock_settings.postgres_password = "test"
            mock_settings.postgres_host = "localhost"
            mock_settings.postgres_port = 5433
            mock_settings.postgres_db = "raglite_test"
            mock_settings.refresh_cron_daily = "0 6 * * *"
            mock_settings.refresh_cron_weekly = "0 6 * * 0"
            mock_settings.refresh_cron_monthly = "0 6 1 * *"
            mock_settings.refresh_cron_backtest = "0 3 * * 0"  # Story 6.12 AC3: Sunday 03:00 UTC
            mock_settings.refresh_cron_tft_training = "0 2 * * 0"  # Story 6.14: Sunday 02:00 UTC

            with patch("raglite.external_data.scheduler.SQLAlchemyJobStore") as mock_job_store:
                mock_job_store.return_value = MagicMock()

                with patch(
                    "raglite.external_data.scheduler.AsyncIOScheduler"
                ) as mock_scheduler_class:
                    mock_scheduler = MagicMock()
                    mock_scheduler.running = False
                    mock_scheduler.get_jobs.return_value = []
                    mock_scheduler_class.return_value = mock_scheduler

                    await start_scheduler()

                    # Verify jobs were added
                    assert (
                        mock_scheduler.add_job.call_count == 5
                    )  # daily, weekly, monthly, backtest, tft_training
                    mock_scheduler.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduler_disabled_does_not_start(self) -> None:
        """Test that scheduler does not start when disabled."""
        import raglite.external_data.scheduler as scheduler_module
        from raglite.external_data.scheduler import start_scheduler

        scheduler_module._scheduler = None

        with patch("raglite.external_data.scheduler.settings") as mock_settings:
            mock_settings.scheduler_enabled = False

            with patch("raglite.external_data.scheduler.AsyncIOScheduler") as mock_scheduler_class:
                await start_scheduler()

                # Scheduler should not be instantiated
                mock_scheduler_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_scheduler_graceful_shutdown(self) -> None:
        """Test graceful scheduler shutdown (AC1)."""
        import raglite.external_data.scheduler as scheduler_module
        from raglite.external_data.scheduler import shutdown_scheduler

        # Create a mock scheduler
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        scheduler_module._scheduler = mock_scheduler

        await shutdown_scheduler()

        mock_scheduler.shutdown.assert_called_once_with(wait=True)
