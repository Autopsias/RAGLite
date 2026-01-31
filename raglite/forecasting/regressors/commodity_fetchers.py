"""Commodity price regressor fetchers (Petcoke, CO2 EUA).

Validation Fix: Creates fetchers for commodity prices used as regressors.
These wrap the CommoditiesClient and return pandas Series for Prophet models.

Supported commodities:
- petcoke: Petroleum coke prices (USD/ton)
- co2_eua: EU ETS carbon prices (EUR/tCO2)
"""

from datetime import date

import pandas as pd

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def fetch_petcoke_prices(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch petcoke prices from CommoditiesClient with cache fallback.

    Petcoke is petroleum coke, a byproduct of oil refining used as fuel
    in cement kilns. Prices are typically commercial (Argus/Platts) so
    this function relies on cached data.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if no data available
    """
    from raglite.external_data.clients.commodities import CommoditiesClient

    client = CommoditiesClient()

    try:
        results = await client.fetch_petcoke_prices(start_date, end_date)

        if results:
            series = pd.Series(
                [p.price for p in results],
                index=pd.DatetimeIndex([p.date for p in results]),
            )
            # Deduplicate by date (take mean if multiple values)
            series = series.groupby(level=0).mean()
            logger.info(
                "Fetched petcoke prices",
                extra={"points": len(series), "start": str(start_date), "end": str(end_date)},
            )
            return series

        logger.warning("No petcoke price data available - cache may be empty")
        return None

    except Exception as e:
        logger.warning(f"Failed to fetch petcoke prices: {e}")
        return None


async def fetch_co2_eua_prices(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch CO2 EUA prices from CommoditiesClient with cache fallback.

    EU ETS (European Union Emissions Trading System) carbon prices.
    The Ember API was deprecated in Jan 2025, so this relies on cache.

    Note: Cache must contain validated EU ETS prices (~70-85 EUR/tCO2).
    KRBN ETF data (~$30 USD) has been rejected as invalid.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if no data available
    """
    from raglite.external_data.clients.commodities import CommoditiesClient

    client = CommoditiesClient()

    try:
        results = await client.fetch_co2_prices(start_date, end_date)

        if results:
            series = pd.Series(
                [p.price for p in results],
                index=pd.DatetimeIndex([p.date for p in results]),
            )
            # Deduplicate by date (take mean if multiple values)
            series = series.groupby(level=0).mean()
            logger.info(
                "Fetched CO2 EUA prices",
                extra={"points": len(series), "start": str(start_date), "end": str(end_date)},
            )
            return series

        logger.warning(
            "No CO2 EUA price data available - cache may be empty or contain invalid data"
        )
        return None

    except Exception as e:
        logger.warning(f"Failed to fetch CO2 EUA prices: {e}")
        return None
