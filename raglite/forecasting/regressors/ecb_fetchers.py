"""ECB regressor fetchers.

European Central Bank data providers for forecasting regressors.
"""

from datetime import date

import pandas as pd

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def fetch_euribor_3m(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch 3-month EURIBOR rate from ECB.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.ecb import ECBClient

    client = ECBClient()
    data = await client.fetch_euribor(tenor="3M", start_date=start_date, end_date=end_date)
    if data:
        series = pd.Series(
            [d.rate_pct for d in data],
            index=pd.DatetimeIndex([d.date for d in data]),
        )
        # Deduplicate by date (aggregate duplicates)
        series = series.groupby(level=0).mean()
        return series

    return None


async def fetch_gdp_growth(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch GDP growth rate from ECB (quarterly, interpolated to monthly).

    Story 6.17 AC1: GDP growth rate for demand-side forecasting.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with monthly datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.ecb import (
        ECBClient,
        interpolate_quarterly_to_monthly,
    )

    client_ecb_gdp = ECBClient()
    quarterly_gdp = await client_ecb_gdp.fetch_gdp_growth(
        country="PT", start_date=start_date, end_date=end_date
    )
    if quarterly_gdp:
        # Interpolate quarterly to monthly for Prophet alignment
        monthly_gdp = interpolate_quarterly_to_monthly(quarterly_gdp)
        series = pd.Series(
            [d.growth_pct for d in monthly_gdp],
            index=pd.DatetimeIndex([d.date for d in monthly_gdp]),
        )
        series = series.groupby(level=0).mean()
        return series

    return None


async def fetch_inflation(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch HICP inflation from ECB.

    Story 6.17 AC2: HICP inflation for pricing/cost forecasting.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.ecb import ECBClient

    client_ecb_hicp = ECBClient()
    hicp_data = await client_ecb_hicp.fetch_inflation(
        country="PT", start_date=start_date, end_date=end_date
    )
    if hicp_data:
        series = pd.Series(
            [d.index_value for d in hicp_data],
            index=pd.DatetimeIndex([d.date for d in hicp_data]),
        )
        series = series.groupby(level=0).mean()
        return series

    return None
