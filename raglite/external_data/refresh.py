"""External data refresh logic with retry and staleness detection.

Story 6.5: Automated Data Refresh Scheduler (APScheduler)

Provides refresh functions for each external data source with:
- Exponential backoff retry (AC3): 3 attempts with 1s, 2s, 4s delays
- Structured error logging (AC3)
- Staleness detection (AC5): Warning if data >30 days old
- Source-specific refresh orchestration

Usage:
    >>> from raglite.external_data.refresh import refresh_all_sources, refresh_source
    >>> result = await refresh_all_sources()
    >>> result = await refresh_source("IPMA")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

# Re-export public APIs from helper modules
from raglite.external_data.refresh_helpers import (
    check_staleness,
)
from raglite.external_data.refresh_sources import (
    SOURCE_REFRESH_FUNCTIONS,
    RefreshResult,
)
from raglite.external_data.scheduler import SOURCE_FREQUENCIES, RefreshFrequency
from raglite.external_data.storage import ExternalDataStorage
from raglite.shared.config import settings
from raglite.shared.database import get_session
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BulkRefreshResult:
    """Result of refreshing multiple sources."""

    total_sources: int
    successful: int
    failed: int
    results: list[RefreshResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0


async def refresh_source(source_name: str) -> RefreshResult:
    """Refresh a single external data source.

    AC4: Manual trigger for specific source.

    Args:
        source_name: Name of the source to refresh

    Returns:
        RefreshResult with operation status

    Raises:
        ValueError: If source_name is not recognized
    """
    if source_name not in SOURCE_REFRESH_FUNCTIONS:
        available = list(SOURCE_REFRESH_FUNCTIONS.keys())
        raise ValueError(f"Unknown source: {source_name}. Available: {available}")

    logger.info(f"Starting refresh for source: {source_name}")

    session = get_session()
    storage = ExternalDataStorage(session)

    try:
        result = await SOURCE_REFRESH_FUNCTIONS[source_name](storage)

        if result.success:
            logger.info(
                "Source refresh completed",
                extra={
                    "source": source_name,
                    "records_updated": result.records_updated,
                    "duration_seconds": f"{result.duration_seconds:.2f}",
                    "attempts": result.attempts,
                },
            )
        else:
            logger.error(
                "Source refresh failed",
                extra={
                    "source": source_name,
                    "error": result.error_message,
                    "attempts": result.attempts,
                },
            )

        # Check staleness (AC5)
        source_orm = storage.get_source(source_name)
        if source_orm:
            check_staleness(source_name, source_orm.last_refresh_at)

        return result

    finally:
        session.close()


async def refresh_sources_by_frequency(frequency: RefreshFrequency) -> BulkRefreshResult:
    """Refresh all sources matching a given frequency.

    Called by APScheduler jobs for daily/weekly/monthly refreshes.

    Args:
        frequency: The refresh frequency to filter by

    Returns:
        BulkRefreshResult with all source results
    """
    sources_to_refresh = [name for name, freq in SOURCE_FREQUENCIES.items() if freq == frequency]

    logger.info(
        f"Starting {frequency.value} refresh",
        extra={
            "frequency": frequency.value,
            "sources": sources_to_refresh,
        },
    )

    start_time = datetime.now(UTC)
    results = []
    successful = 0
    failed = 0

    session = get_session()
    storage = ExternalDataStorage(session)

    try:
        for source_name in sources_to_refresh:
            if source_name not in SOURCE_REFRESH_FUNCTIONS:
                logger.warning(f"No refresh function for source: {source_name}")
                continue

            result = await SOURCE_REFRESH_FUNCTIONS[source_name](storage)
            results.append(result)

            if result.success:
                successful += 1
            else:
                failed += 1

            # Check staleness for each source (AC5)
            source_orm = storage.get_source(source_name)
            if source_orm:
                check_staleness(source_name, source_orm.last_refresh_at)

    finally:
        session.close()

    total_duration = (datetime.now(UTC) - start_time).total_seconds()

    logger.info(
        f"Completed {frequency.value} refresh",
        extra={
            "frequency": frequency.value,
            "total_sources": len(sources_to_refresh),
            "successful": successful,
            "failed": failed,
            "duration_seconds": f"{total_duration:.2f}",
        },
    )

    return BulkRefreshResult(
        total_sources=len(sources_to_refresh),
        successful=successful,
        failed=failed,
        results=results,
        total_duration_seconds=total_duration,
    )


async def refresh_all_sources() -> BulkRefreshResult:
    """Refresh all configured external data sources.

    AC4: Manual trigger for all sources.

    Returns:
        BulkRefreshResult with all source results
    """
    all_sources = list(SOURCE_REFRESH_FUNCTIONS.keys())

    logger.info(
        "Starting full refresh of all sources",
        extra={"total_sources": len(all_sources)},
    )

    start_time = datetime.now(UTC)
    results = []
    successful = 0
    failed = 0

    session = get_session()
    storage = ExternalDataStorage(session)

    try:
        for source_name in all_sources:
            result = await SOURCE_REFRESH_FUNCTIONS[source_name](storage)
            results.append(result)

            if result.success:
                successful += 1
            else:
                failed += 1

            # Check staleness (AC5)
            source_orm = storage.get_source(source_name)
            if source_orm:
                check_staleness(source_name, source_orm.last_refresh_at)

    finally:
        session.close()

    total_duration = (datetime.now(UTC) - start_time).total_seconds()

    logger.info(
        "Completed full refresh",
        extra={
            "total_sources": len(all_sources),
            "successful": successful,
            "failed": failed,
            "duration_seconds": f"{total_duration:.2f}",
        },
    )

    return BulkRefreshResult(
        total_sources=len(all_sources),
        successful=successful,
        failed=failed,
        results=results,
        total_duration_seconds=total_duration,
    )


def get_staleness_report() -> list[dict[str, str | int | bool | None]]:
    """Get staleness status for all registered sources.

    AC5: Check all sources for staleness.

    Returns:
        List of dicts with source_name, last_refresh, days_old, is_stale
    """
    session = get_session()
    storage = ExternalDataStorage(session)

    try:
        report: list[dict[str, str | int | bool | None]] = []
        now = datetime.now(UTC)

        for source_name in SOURCE_REFRESH_FUNCTIONS.keys():
            source_orm = storage.get_source(source_name)

            if source_orm is None:
                report.append(
                    {
                        "source_name": source_name,
                        "last_refresh": None,
                        "days_old": None,
                        "is_stale": True,
                        "status": "never_refreshed",
                    }
                )
                continue

            last_refresh = source_orm.last_refresh_at
            if last_refresh is None:
                days_old = None
                is_stale = True
            else:
                if last_refresh.tzinfo is None:
                    last_refresh = last_refresh.replace(tzinfo=UTC)
                days_old = (now - last_refresh).days
                is_stale = days_old > settings.external_data_stale_days

            report.append(
                {
                    "source_name": source_name,
                    "last_refresh": last_refresh.isoformat() if last_refresh else None,
                    "days_old": days_old,
                    "is_stale": is_stale,
                    "status": "stale" if is_stale else "fresh",
                }
            )

        return report

    finally:
        session.close()
