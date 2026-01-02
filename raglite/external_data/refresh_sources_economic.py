"""Economic and financial indicator refresh functions.

Handles economic data sources:
- INE: Building permits, construction output, construction cost index
- BPstat: Mortgage loans
- ATIC: Cement consumption

All functions use retry_with_backoff for resilient operation.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from raglite.external_data.clients import ATICClient, BPstatClient, INEClient
from raglite.external_data.refresh_helpers import retry_with_backoff
from raglite.external_data.storage import ExternalDataStorage

if TYPE_CHECKING:
    from raglite.external_data.refresh_sources import RefreshResult


# Import RefreshResult from main module to avoid circular dependency
# This will be defined in refresh_sources.py
def _import_refresh_result() -> type[RefreshResult]:
    """Lazy import to avoid circular dependency."""
    from raglite.external_data.refresh_sources import RefreshResult

    return RefreshResult


async def refresh_ine_building_permits(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh INE building permits data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    RefreshResult = _import_refresh_result()
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

    success, attempts, error, count = await retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )


async def refresh_bpstat_mortgage(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh BPstat mortgage loans data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    RefreshResult = _import_refresh_result()
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

    success, attempts, error, count = await retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )


async def refresh_ine_construction(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh INE construction output and cost index data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    RefreshResult = _import_refresh_result()
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

    success, attempts, error, count = await retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )


async def refresh_ine_cost_index(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh INE construction cost index data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    RefreshResult = _import_refresh_result()
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

    success, attempts, error, count = await retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )


async def refresh_atic_cement(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh ATIC cement consumption data.

    Note: ATIC data requires CSV upload - no public API available.
    This refresh function will return success with 0 records if no CSV is available.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    RefreshResult = _import_refresh_result()
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

    success, attempts, error, count = await retry_with_backoff(_fetch_and_store, source_name)
    duration = (datetime.now(UTC) - start_time).total_seconds()

    return RefreshResult(
        source_name=source_name,
        success=success,
        records_updated=count if success and count else 0,
        duration_seconds=duration,
        error_message=error,
        attempts=attempts,
    )
