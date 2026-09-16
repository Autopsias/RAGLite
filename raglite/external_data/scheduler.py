"""APScheduler setup for automated external data refresh.

Story 6.5: Automated Data Refresh Scheduler (APScheduler)

Provides AsyncIOScheduler for non-blocking job execution integrated with
the MCP server event loop. Jobs are persisted to PostgreSQL for restart recovery.

Usage:
    >>> from raglite.external_data.scheduler import get_scheduler, start_scheduler
    >>> scheduler = get_scheduler()
    >>> await start_scheduler()

Cron Schedules (AC2):
- Daily (06:00 UTC): Weather (IPMA), Electricity (OMIE), CO2 EUA
- Weekly (Sunday 06:00 UTC): Building Permits (INE), Mortgage Loans (BPstat), Diesel
- Monthly (1st day, 06:00 UTC): Construction Output/Cost Index (INE), Cement (ATIC)
"""

from __future__ import annotations

import atexit
from datetime import UTC, datetime
from enum import StrEnum

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Singleton scheduler instance
_scheduler: AsyncIOScheduler | None = None


class RefreshFrequency(StrEnum):
    """Refresh frequency for external data sources."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# Source to frequency mapping (AC2)
SOURCE_FREQUENCIES: dict[str, RefreshFrequency] = {
    # Daily sources (06:00 UTC)
    "IPMA": RefreshFrequency.DAILY,  # Weather
    "OMIE": RefreshFrequency.DAILY,  # Electricity prices
    "CO2_EUA": RefreshFrequency.DAILY,  # Carbon prices (commodities)
    # Weekly sources (Sunday 06:00 UTC)
    "INE_BuildingPermits": RefreshFrequency.WEEKLY,
    "BPstat_MortgageLoans": RefreshFrequency.WEEKLY,
    "EUOil_Diesel": RefreshFrequency.WEEKLY,  # Diesel prices
    # Monthly sources (1st day, 06:00 UTC)
    "INE_ConstructionOutput": RefreshFrequency.MONTHLY,
    "INE_ConstructionCostIndex": RefreshFrequency.MONTHLY,
    "ATIC_CementConsumption": RefreshFrequency.MONTHLY,
}


def _build_postgres_url() -> str:
    """Build PostgreSQL connection URL for APScheduler job store.

    Returns:
        PostgreSQL connection URL
    """
    return (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def _parse_cron_expression(cron_expr: str) -> dict[str, str]:
    """Parse cron expression into APScheduler CronTrigger kwargs.

    Args:
        cron_expr: Cron expression (minute hour day_of_month month day_of_week)

    Returns:
        Dict with keys: minute, hour, day, month, day_of_week

    Raises:
        ValueError: If cron expression is invalid
    """
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expr}. Expected 5 parts.")

    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the singleton scheduler instance.

    Returns:
        AsyncIOScheduler instance configured with PostgreSQL job store

    Note:
        The scheduler is NOT started automatically. Call start_scheduler()
        to begin executing jobs.
    """
    global _scheduler

    if _scheduler is not None:
        return _scheduler

    logger.info(
        "Creating AsyncIOScheduler",
        extra={
            "timezone": settings.scheduler_timezone,
            "job_coalesce": settings.scheduler_job_coalesce,
            "misfire_grace_time": settings.scheduler_misfire_grace_time,
        },
    )

    # Configure job store with PostgreSQL for persistence (AC1)
    jobstores = {
        "default": SQLAlchemyJobStore(url=_build_postgres_url()),
    }

    # Configure scheduler
    _scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        timezone=settings.scheduler_timezone,
        job_defaults={
            "coalesce": settings.scheduler_job_coalesce,
            "misfire_grace_time": settings.scheduler_misfire_grace_time,
            "max_instances": 1,  # Only one instance per job at a time
        },
    )

    # Register atexit handler for graceful shutdown (AC1)
    atexit.register(_shutdown_scheduler_sync)

    logger.info("AsyncIOScheduler created with PostgreSQL job store")
    return _scheduler


def _shutdown_scheduler_sync() -> None:
    """Synchronous shutdown handler for atexit.

    Called automatically on application exit to ensure clean scheduler shutdown.
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        try:
            logger.info("Shutting down scheduler (atexit)")
        except (ValueError, OSError):
            # Ignore logging errors during shutdown (stdout/stderr may be closed)
            pass
        try:
            _scheduler.shutdown(wait=False)
        except Exception as e:
            try:
                logger.warning(f"Error during scheduler shutdown: {e}")
            except (ValueError, OSError):
                # Ignore logging errors during shutdown
                pass


async def shutdown_scheduler() -> None:
    """Graceful async scheduler shutdown.

    AC1: Implement graceful shutdown on application exit.

    Call this in MCP server cleanup handler or application shutdown hook.
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.info("Shutting down scheduler gracefully")
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler shutdown complete")


async def start_scheduler() -> None:
    """Start the scheduler and register all refresh jobs.

    AC1/AC2: Configure AsyncIOScheduler with scheduled jobs.

    This should be called during MCP server startup.
    """
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled via configuration")
        return

    scheduler = get_scheduler()

    if scheduler.running:
        logger.warning("Scheduler already running")
        return

    # Register jobs for each frequency
    _register_refresh_jobs(scheduler)

    # Start the scheduler
    scheduler.start()

    logger.info(
        "Scheduler started",
        extra={
            "job_count": len(scheduler.get_jobs()),
            "timezone": settings.scheduler_timezone,
        },
    )


def _register_refresh_jobs(scheduler: AsyncIOScheduler) -> None:
    """Register all refresh jobs with appropriate cron triggers.

    AC2: Configure refresh schedules per source frequency.

    Args:
        scheduler: The AsyncIOScheduler instance
    """
    # Import refresh function here to avoid circular imports
    from raglite.external_data.refresh import refresh_sources_by_frequency

    # Daily jobs
    daily_cron = _parse_cron_expression(settings.refresh_cron_daily)
    scheduler.add_job(
        refresh_sources_by_frequency,
        CronTrigger(**daily_cron, timezone=settings.scheduler_timezone),
        id="refresh_daily",
        name="Daily External Data Refresh",
        args=[RefreshFrequency.DAILY],
        replace_existing=True,
    )
    logger.info(
        "Registered daily refresh job",
        extra={"cron": settings.refresh_cron_daily},
    )

    # Weekly jobs
    weekly_cron = _parse_cron_expression(settings.refresh_cron_weekly)
    scheduler.add_job(
        refresh_sources_by_frequency,
        CronTrigger(**weekly_cron, timezone=settings.scheduler_timezone),
        id="refresh_weekly",
        name="Weekly External Data Refresh",
        args=[RefreshFrequency.WEEKLY],
        replace_existing=True,
    )
    logger.info(
        "Registered weekly refresh job",
        extra={"cron": settings.refresh_cron_weekly},
    )

    # Monthly jobs
    monthly_cron = _parse_cron_expression(settings.refresh_cron_monthly)
    scheduler.add_job(
        refresh_sources_by_frequency,
        CronTrigger(**monthly_cron, timezone=settings.scheduler_timezone),
        id="refresh_monthly",
        name="Monthly External Data Refresh",
        args=[RefreshFrequency.MONTHLY],
        replace_existing=True,
    )
    logger.info(
        "Registered monthly refresh job",
        extra={"cron": settings.refresh_cron_monthly},
    )

    # Story 6.12: Weekly backtest job (Sunday 03:00 UTC)
    _register_backtest_job(scheduler)


def _register_backtest_job(scheduler: AsyncIOScheduler) -> None:
    """Register weekly backtest job for adaptive weight calculation.

    Story 6.12 AC3: Schedule backtest for Sunday 03:00 UTC (after data refresh at 06:00).

    Args:
        scheduler: The AsyncIOScheduler instance
    """
    from raglite.forecasting.backtest_job import run_weekly_backtest
    from raglite.forecasting.tft_training_job import run_weekly_tft_training

    # Story 6.14: TFT training job (Sunday 2am UTC, BEFORE backtest at 3am)
    tft_training_cron = _parse_cron_expression(settings.refresh_cron_tft_training)
    scheduler.add_job(
        run_weekly_tft_training,
        CronTrigger(**tft_training_cron, timezone=settings.scheduler_timezone),
        id="tft_training_weekly",
        name="Weekly TFT Training",
        replace_existing=True,
    )
    logger.info(
        "Registered weekly TFT training job",
        extra={"cron": settings.refresh_cron_tft_training},
    )

    backtest_cron = _parse_cron_expression(settings.refresh_cron_backtest)
    scheduler.add_job(
        run_weekly_backtest,
        CronTrigger(**backtest_cron, timezone=settings.scheduler_timezone),
        id="backtest_weekly",
        name="Weekly Model Backtest",
        replace_existing=True,
    )
    logger.info(
        "Registered weekly backtest job",
        extra={"cron": settings.refresh_cron_backtest},
    )


def get_next_run_times() -> dict[str, datetime | None]:
    """Get next scheduled run times for all jobs.

    Returns:
        Dict mapping job_id to next_run_time (UTC)
    """
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()

    return {job.id: job.next_run_time for job in jobs}


def get_job_info() -> list[dict]:
    """Get information about all scheduled jobs.

    Returns:
        List of dicts with job_id, name, next_run_time, trigger
    """
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()

    return [
        {
            "job_id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        }
        for job in jobs
    ]


async def trigger_job_now(job_id: str) -> bool:
    """Manually trigger a scheduled job immediately.

    Args:
        job_id: The job identifier (e.g., "refresh_daily")

    Returns:
        True if job was triggered, False if not found
    """
    scheduler = get_scheduler()

    job = scheduler.get_job(job_id)
    if job is None:
        logger.warning(f"Job not found: {job_id}")
        return False

    # Modify job to run immediately
    scheduler.modify_job(job_id, next_run_time=datetime.now(UTC))
    logger.info(f"Triggered job: {job_id}")
    return True
