"""ICE Futures regressor fetchers.

ICE Futures (Intercontinental Exchange) commodity price data providers.
"""

from datetime import date
from typing import Any

import pandas as pd

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def fetch_ttf_gas(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch TTF natural gas price from ICE Futures.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.ice_futures import ICEFuturesClient

    client_ttf: ICEFuturesClient = ICEFuturesClient()
    ttf_data: list[Any] = await client_ttf.fetch_ttf_gas(start_date, end_date)
    if ttf_data:
        series = pd.Series(
            [d.price for d in ttf_data],
            index=pd.DatetimeIndex([d.date for d in ttf_data]),
        )
        series = series.groupby(level=0).mean()
        return series

    return None


async def fetch_api2_coal(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch API2 coal price from ICE Futures.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.ice_futures import ICEFuturesClient

    client_ice: ICEFuturesClient = ICEFuturesClient()
    coal_data: list[Any] = await client_ice.fetch_api2_coal(start_date, end_date)
    if coal_data:
        series = pd.Series(
            [d.price for d in coal_data],
            index=pd.DatetimeIndex([d.date for d in coal_data]),
        )
        series = series.groupby(level=0).mean()
        return series

    return None
