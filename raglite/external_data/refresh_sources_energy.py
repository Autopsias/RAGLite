"""Energy and commodities refresh functions.

Handles energy-related data sources:
- IPMA: Weather data (temperature impacts energy demand)
- OMIE: Electricity spot prices
- Commodities: CO2 EUA prices
- EU Oil Bulletin: Diesel fuel prices

All functions use retry_with_backoff for resilient operation.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from raglite.external_data.clients import (
    CommoditiesClient,
    EUOilBulletinClient,
    IPMAClient,
    OMIEClient,
)
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


async def refresh_ipma(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh IPMA weather data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    RefreshResult = _import_refresh_result()
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


async def refresh_omie(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh OMIE electricity price data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    RefreshResult = _import_refresh_result()
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


async def refresh_commodities_co2(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh CO2 EUA price data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    RefreshResult = _import_refresh_result()
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


async def refresh_diesel_prices(storage: ExternalDataStorage) -> RefreshResult:
    """Refresh EU diesel price data.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        RefreshResult with operation status
    """
    RefreshResult = _import_refresh_result()
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
