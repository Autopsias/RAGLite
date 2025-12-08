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

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from raglite.external_data.clients import (
    ATICClient,
    BPstatClient,
    CommoditiesClient,
    EUOilBulletinClient,
    INEClient,
    IPMAClient,
    OMIEClient,
)
from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.scheduler import SOURCE_FREQUENCIES, RefreshFrequency
from raglite.external_data.storage import ExternalDataStorage
from raglite.shared.config import settings
from raglite.shared.database import get_session
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Retry configuration (AC3)
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s


@dataclass
class RefreshResult:
    """Result of a single source refresh operation."""

    source_name: str
    success: bool
    records_updated: int = 0
    duration_seconds: float = 0.0
    error_message: str | None = None
    attempts: int = 1


@dataclass
class BulkRefreshResult:
    """Result of refreshing multiple sources."""

    total_sources: int
    successful: int
    failed: int
    results: list[RefreshResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0


async def _retry_with_backoff(
    coro_func: Any,
    source_name: str,
    *args: Any,
    **kwargs: Any,
) -> tuple[bool, int, str | None, Any]:
    """Execute coroutine with exponential backoff retry.

    AC3: Retry failed jobs with 3 attempts and exponential backoff (1s, 2s, 4s).

    Args:
        coro_func: Async function to execute
        source_name: Source name for logging
        *args: Positional arguments for coro_func
        **kwargs: Keyword arguments for coro_func

    Returns:
        Tuple of (success, attempts, error_message, result)
        result is the return value from coro_func on success, None on failure
    """
    max_attempts = settings.external_data_retry_attempts
    last_error: str | None = None

    for attempt in range(max_attempts):
        try:
            result = await coro_func(*args, **kwargs)
            return True, attempt + 1, None, result

        except ExternalDataFetchError as e:
            last_error = str(e)
            if attempt < max_attempts - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(
                    "External data fetch failed, retrying",
                    extra={
                        "source": source_name,
                        "attempt": attempt + 1,
                        "max_attempts": max_attempts,
                        "delay_seconds": delay,
                        "error": last_error,
                    },
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "External data fetch failed after all retries",
                    extra={
                        "source": source_name,
                        "attempts": max_attempts,
                        "error": last_error,
                    },
                )

        except Exception as e:
            last_error = f"Unexpected error: {type(e).__name__}: {str(e)}"
            logger.error(
                "Unexpected error during external data refresh",
                extra={
                    "source": source_name,
                    "attempt": attempt + 1,
                    "error": last_error,
                },
            )
            if attempt < max_attempts - 1:
                delay = RETRY_DELAYS[attempt]
                await asyncio.sleep(delay)

    return False, max_attempts, last_error, None


def check_staleness(source_name: str, last_refresh_at: datetime | None) -> bool:
    """Check if external data source is stale and log warning if so.

    AC5: Alert if external data >30 days old (WARNING level log).

    Args:
        source_name: Name of the data source
        last_refresh_at: Last refresh timestamp (UTC)

    Returns:
        True if data is stale (>30 days old), False otherwise
    """
    if last_refresh_at is None:
        logger.warning(
            "External data source has never been refreshed",
            extra={"source": source_name, "staleness_days": "never"},
        )
        return True

    # Ensure timezone-aware comparison
    if last_refresh_at.tzinfo is None:
        last_refresh_at = last_refresh_at.replace(tzinfo=UTC)

    now = datetime.now(UTC)
    days_old = (now - last_refresh_at).days

    if days_old > settings.external_data_stale_days:
        logger.warning(
            "External data source is stale",
            extra={
                "source": source_name,
                "staleness_days": days_old,
                "threshold_days": settings.external_data_stale_days,
                "last_refresh": last_refresh_at.isoformat(),
            },
        )
        return True

    return False


async def _refresh_ipma(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh IPMA weather data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    source_name = "IPMA"
    start_time = datetime.now(UTC)

    async def _fetch_and_store() -> int:
        client = IPMAClient()
        today = date.today()
        # Fetch last 7 days of weather data
        observations = await client.fetch_observations(
            start_date=today - timedelta(days=7),
            end_date=today,
        )

        if not observations:
            return 0

        # Store data points
        storage.get_or_create_source(
            source_name=source_name,
            api_endpoint="https://api.ipma.pt",
            data_type="time_series",
            refresh_frequency="daily",
        )

        data_points = [
            {
                "date": obs.date,
                "metric_name": "temperature_avg",
                "value": obs.temperature_c or 0,
                "unit": "celsius",
            }
            for obs in observations
            if obs.temperature_c is not None
        ]

        if data_points:
            return storage.insert_data_points(source_name, data_points, upsert=True)
        return 0

    success, attempts, error, count = await _retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )


async def _refresh_omie(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh OMIE electricity price data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    source_name = "OMIE"
    start_time = datetime.now(UTC)

    async def _fetch_and_store() -> int:
        client = OMIEClient()
        today = date.today()
        # Fetch last 7 days of electricity prices
        prices = await client.fetch_spot_prices(
            start_date=today - timedelta(days=7),
            end_date=today,
        )

        if not prices:
            return 0

        storage.get_or_create_source(
            source_name=source_name,
            api_endpoint="https://www.omie.es/api",
            data_type="time_series",
            refresh_frequency="daily",
        )

        data_points = [
            {
                "date": price.date,
                "metric_name": "electricity_price",
                "value": price.price_eur_mwh,
                "unit": "EUR/MWh",
            }
            for price in prices
        ]

        if data_points:
            return storage.insert_data_points(source_name, data_points, upsert=True)
        return 0

    success, attempts, error, count = await _retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )


async def _refresh_commodities_co2(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh CO2 EUA price data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    source_name = "CO2_EUA"
    start_time = datetime.now(UTC)

    async def _fetch_and_store() -> int:
        client = CommoditiesClient()
        today = date.today()
        # Fetch last 7 days of CO2 prices
        prices = await client.fetch_co2_prices(
            start_date=today - timedelta(days=7),
            end_date=today,
        )

        if not prices:
            return 0

        storage.get_or_create_source(
            source_name=source_name,
            api_endpoint="commodities_api",
            data_type="time_series",
            refresh_frequency="daily",
        )

        data_points = [
            {
                "date": price.date,
                "metric_name": "co2_eua_price",
                "value": price.price,  # Inherited from CommodityPrice
                "unit": "EUR/ton",
            }
            for price in prices
        ]

        if data_points:
            return storage.insert_data_points(source_name, data_points, upsert=True)
        return 0

    success, attempts, error, count = await _retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )


async def _refresh_ine_building_permits(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh INE building permits data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    source_name = "INE_BuildingPermits"
    start_time = datetime.now(UTC)

    async def _fetch_and_store() -> int:
        client = INEClient()
        today = date.today()
        # Fetch last 90 days of building permit data
        permits = await client.fetch_building_permits(
            start_date=today - timedelta(days=90),
            end_date=today,
        )

        if not permits:
            return 0

        storage.get_or_create_source(
            source_name=source_name,
            api_endpoint="https://www.ine.pt/api",
            data_type="time_series",
            refresh_frequency="weekly",
        )

        data_points = [
            {
                "date": permit.date,
                "metric_name": "building_permits",
                "value": permit.permits_count,  # INEBuildingPermits model field
                "unit": "count",
            }
            for permit in permits
        ]

        if data_points:
            return storage.insert_data_points(source_name, data_points, upsert=True)
        return 0

    success, attempts, error, count = await _retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )


async def _refresh_bpstat_mortgage(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh BPstat mortgage loans data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    source_name = "BPstat_MortgageLoans"
    start_time = datetime.now(UTC)

    async def _fetch_and_store() -> int:
        client = BPstatClient()
        today = date.today()
        # Fetch last 90 days of mortgage data
        loans = await client.fetch_mortgage_loans(
            start_date=today - timedelta(days=90),
            end_date=today,
        )

        if not loans:
            return 0

        storage.get_or_create_source(
            source_name=source_name,
            api_endpoint="https://bpstat.bportugal.pt/api",
            data_type="time_series",
            refresh_frequency="weekly",
        )

        data_points = [
            {
                "date": loan.date,
                "metric_name": "mortgage_loans_value",
                "value": loan.total_loans_eur,  # BPstatMortgageLoans model field
                "unit": "EUR",
            }
            for loan in loans
        ]

        if data_points:
            return storage.insert_data_points(source_name, data_points, upsert=True)
        return 0

    success, attempts, error, count = await _retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )


async def _refresh_diesel_prices(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh EU diesel price data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    source_name = "EUOil_Diesel"
    start_time = datetime.now(UTC)

    async def _fetch_and_store() -> int:
        client = EUOilBulletinClient()
        today = date.today()
        # Fetch last 14 days of diesel prices
        prices = await client.fetch_diesel_prices(
            start_date=today - timedelta(days=14),
            end_date=today,
        )

        if not prices:
            return 0

        storage.get_or_create_source(
            source_name=source_name,
            api_endpoint="https://ec.europa.eu/energy/observatory",
            data_type="time_series",
            refresh_frequency="weekly",
        )

        data_points = [
            {
                "date": price.date,
                "metric_name": "diesel_price",
                "value": price.price_eur_litre,  # EUDieselPrice model field
                "unit": "EUR/L",
            }
            for price in prices
        ]

        if data_points:
            return storage.insert_data_points(source_name, data_points, upsert=True)
        return 0

    success, attempts, error, count = await _retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )


async def _refresh_ine_construction(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh INE construction output and cost index data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    source_name = "INE_ConstructionOutput"
    start_time = datetime.now(UTC)

    async def _fetch_and_store() -> int:
        client = INEClient()
        today = date.today()
        # Fetch last 120 days of construction data
        output_data = await client.fetch_construction_output(
            start_date=today - timedelta(days=120),
            end_date=today,
        )

        if not output_data:
            return 0

        storage.get_or_create_source(
            source_name=source_name,
            api_endpoint="https://www.ine.pt/api",
            data_type="time_series",
            refresh_frequency="monthly",
        )

        data_points = [
            {
                "date": data.date,
                "metric_name": "construction_output_index",
                "value": data.index_value,
                "unit": "index",
            }
            for data in output_data
        ]

        if data_points:
            return storage.insert_data_points(source_name, data_points, upsert=True)
        return 0

    success, attempts, error, count = await _retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )


async def _refresh_ine_cost_index(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh INE construction cost index data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    source_name = "INE_ConstructionCostIndex"
    start_time = datetime.now(UTC)

    async def _fetch_and_store() -> int:
        client = INEClient()
        today = date.today()
        # Fetch last 120 days of cost index data
        cost_data = await client.fetch_construction_cost_index(
            start_date=today - timedelta(days=120),
            end_date=today,
        )

        if not cost_data:
            return 0

        storage.get_or_create_source(
            source_name=source_name,
            api_endpoint="https://www.ine.pt/api",
            data_type="time_series",
            refresh_frequency="monthly",
        )

        data_points = [
            {
                "date": data.date,
                "metric_name": "construction_cost_index",
                "value": data.total_index,
                "unit": "index",
            }
            for data in cost_data
        ]

        if data_points:
            return storage.insert_data_points(source_name, data_points, upsert=True)
        return 0

    success, attempts, error, count = await _retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )


async def _refresh_atic_cement(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh ATIC cement consumption data.

    Note: ATIC data requires CSV upload - no public API available.
    This refresh function will return success with 0 records if no CSV is available.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    source_name = "ATIC_CementConsumption"
    start_time = datetime.now(UTC)

    async def _fetch_and_store() -> int:
        client = ATICClient()
        today = date.today()
        # ATIC requires CSV upload - fetch_historical_data needs csv_path
        # Without csv_path, returns empty list with warning
        cement_data = await client.fetch_historical_data(
            start_date=today - timedelta(days=120),
            end_date=today,
            csv_path=None,  # No CSV path available for automated refresh
        )

        if not cement_data:
            # Expected when no CSV is available
            return 0

        storage.get_or_create_source(
            source_name=source_name,
            api_endpoint="atic_csv",
            data_type="time_series",
            refresh_frequency="monthly",
        )

        data_points = [
            {
                "date": data.date,
                "metric_name": "cement_consumption",
                "value": data.consumption_tonnes,  # ATICCementConsumption model field
                "unit": "tonnes",
            }
            for data in cement_data
        ]

        if data_points:
            return storage.insert_data_points(source_name, data_points, upsert=True)
        return 0

    success, attempts, error, count = await _retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )


# Source name to refresh function mapping
SOURCE_REFRESH_FUNCTIONS = {
    "IPMA": _refresh_ipma,
    "OMIE": _refresh_omie,
    "CO2_EUA": _refresh_commodities_co2,
    "INE_BuildingPermits": _refresh_ine_building_permits,
    "BPstat_MortgageLoans": _refresh_bpstat_mortgage,
    "EUOil_Diesel": _refresh_diesel_prices,
    "INE_ConstructionOutput": _refresh_ine_construction,
    "INE_ConstructionCostIndex": _refresh_ine_cost_index,  # Separate function for cost index
    "ATIC_CementConsumption": _refresh_atic_cement,
}


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
