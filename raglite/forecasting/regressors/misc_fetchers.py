"""Miscellaneous regressor fetchers.

Data providers from various sources: EU Oil Bulletin, REN, INE, Eurostat Housing.
"""

from datetime import date
from typing import Any

import pandas as pd

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def fetch_diesel(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch diesel prices from EU Oil Bulletin.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.eu_oil_bulletin import EUOilBulletinClient

    client_oil: EUOilBulletinClient = EUOilBulletinClient()
    diesel_data: list[Any] = await client_oil.fetch_diesel_prices(start_date, end_date)
    if diesel_data:
        series = pd.Series(
            [d.price_eur_litre for d in diesel_data],
            index=pd.DatetimeIndex([d.date for d in diesel_data]),
        )
        series = series.groupby(level=0).mean()
        return series

    return None


async def fetch_ren_electricity(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch Portuguese spot electricity prices from REN Data Hub.

    Story 7.0: REN Data Hub for electricity cost (60+ monthly points).

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.ren import RENClient

    client_ren = RENClient()

    # Calculate year/month range for monthly fetch (more efficient)
    start_year, start_month = start_date.year, start_date.month
    end_year, end_month = end_date.year, end_date.month

    ren_data = await client_ren.fetch_monthly_prices_range(
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
    )

    if ren_data:
        series = pd.Series(
            [d.price_eur_mwh for d in ren_data],
            index=pd.DatetimeIndex([d.date for d in ren_data]),
        )
        series = series.groupby(level=0).mean()
        logger.info(
            "Fetched REN electricity regressor",
            extra={"source": "REN Data Hub", "data_points": len(series)},
        )
        return series

    return None


async def fetch_ine_building_permits(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch building permits from INE (Portugal's statistics office).

    Story 6.18: INE building permits with Eurostat fallback.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.ine import INEClient

    try:
        client_ine = INEClient()
        permits_data = await client_ine.fetch_building_permits(
            start_date=start_date, end_date=end_date
        )

        if permits_data:
            # Check if we have national totals (avoid double-counting with regions)
            # Code Review Issue 1: Filter for national data if available
            national_keywords = ("portugal", "total", "nacional", "pt")
            national_permits = [p for p in permits_data if p.region.lower() in national_keywords]

            if national_permits:
                # Use national totals (still need aggregation - INE returns multiple records per month)
                # BUG FIX: INE API returns Portugal data broken down by building type/purpose
                # Multiple "Portugal" entries per month need to be summed to get monthly total
                series = pd.Series(
                    [p.permits_count for p in national_permits],
                    index=pd.DatetimeIndex([p.date for p in national_permits]),
                )
                series = series.groupby(level=0).sum()  # Aggregate duplicate months
            else:
                # Aggregate regional data to national monthly totals
                # Code Review Issue 2: Use pandas groupby for consistent aggregation
                series = pd.Series(
                    [p.permits_count for p in permits_data],
                    index=pd.DatetimeIndex([p.date for p in permits_data]),
                )
                series = series.groupby(level=0).sum()

            series = series.sort_index()
            logger.info(
                "Fetched building permits regressor",
                extra={"source": "INE", "data_points": len(series)},
            )
            return series

    except Exception as e:
        logger.warning(f"INE building permits failed, trying Eurostat fallback: {e}")
        return None

    return None


async def fetch_housing_transactions(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch housing transactions from Eurostat Housing.

    Story 7b-7: Housing transactions (demand-side regressor).

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with monthly datetime index (interpolated from quarterly),
        or None if fetch fails
    """
    from raglite.external_data.clients.eurostat_housing import EurostatHousingClient

    # Import interpolation function from parent module
    from raglite.forecasting.regressor_fetch import interpolate_quarterly_series_to_monthly

    client_housing = EurostatHousingClient()
    transactions_data = await client_housing.fetch_housing_transactions(
        country="PT", start_date=start_date, end_date=end_date
    )

    if transactions_data:
        # Create quarterly series from transaction data
        quarterly_series = pd.Series(
            [d.transaction_count for d in transactions_data],
            index=pd.DatetimeIndex([d.date for d in transactions_data]),
        )
        quarterly_series = quarterly_series.groupby(level=0).sum()

        # Interpolate quarterly to monthly for Prophet alignment
        monthly_series = interpolate_quarterly_series_to_monthly(quarterly_series)

        logger.info(
            "Fetched housing transactions regressor",
            extra={
                "source": "Eurostat (prc_hpi_inx)",
                "quarterly_points": len(quarterly_series),
                "monthly_points": len(monthly_series),
            },
        )
        return monthly_series

    return None


async def fetch_dwelling_completions(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch dwelling completions from Eurostat Housing.

    Story 7b-7: Dwelling completions (demand-side regressor).

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with monthly datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.eurostat_housing import EurostatHousingClient

    client_dwelling = EurostatHousingClient()
    completions_data = await client_dwelling.fetch_dwelling_completions(
        country="PT", start_date=start_date, end_date=end_date
    )

    if completions_data:
        # Create monthly series from completion data
        monthly_series = pd.Series(
            [d.completion_count for d in completions_data],
            index=pd.DatetimeIndex([d.date for d in completions_data]),
        )
        monthly_series = monthly_series.groupby(level=0).sum()

        logger.info(
            "Fetched dwelling completions regressor",
            extra={
                "source": "Eurostat (sts_cobp_m)",
                "monthly_points": len(monthly_series),
            },
        )
        return monthly_series

    return None
