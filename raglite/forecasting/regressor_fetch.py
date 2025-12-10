"""External regressor fetching for multi-variate forecasting.

Story 6.11.1: MCP Multi-Variate Forecasting Interface

This module provides functions to fetch external regressor data from various APIs
for use in multi-variate forecasting with Prophet.

Supported regressors:
- euribor_3m: 3-month EURIBOR rate (ECB)
- ttf_gas: TTF natural gas price (ICE Futures)
- api2_coal: API2 coal price (ICE Futures)
- diesel: Diesel price (EU Oil Bulletin)
- eurostat_electricity: Industrial electricity price (Eurostat)
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

import pandas as pd

from raglite.forecasting.regressor_config import get_default_regressors
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def fetch_single_regressor(
    reg_name: str,
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch a single regressor's time series data.

    Args:
        reg_name: Regressor name (e.g., "euribor_3m", "ttf_gas")
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    try:
        if reg_name == "euribor_3m":
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

        elif reg_name == "ttf_gas":
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

        elif reg_name == "api2_coal":
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

        elif reg_name == "diesel":
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

        elif reg_name == "eurostat_electricity":
            from raglite.external_data.clients.eurostat import EurostatClient

            client_eurostat: EurostatClient = EurostatClient()
            electricity_data = await client_eurostat.fetch_electricity_prices(
                start_date=start_date, end_date=end_date
            )
            if electricity_data:
                series = pd.Series(
                    [d.price_eur_kwh for d in electricity_data],
                    index=pd.DatetimeIndex([d.date for d in electricity_data]),
                )
                series = series.groupby(level=0).mean()
                return series

        elif reg_name == "building_permits":
            # NOTE: Currently disabled - INE indicator returns wrong data
            # Story 6.11.4 will fix this
            logger.warning(
                f"Regressor {reg_name} currently disabled - INE indicator returns wrong data"
            )
            return None

        elif reg_name == "omie_spot":
            # NOTE: Currently disabled - too slow (1000+ HTTP requests)
            # Use eurostat_electricity as proxy
            logger.warning(f"Regressor {reg_name} disabled - too slow, use eurostat_electricity")
            return None

        else:
            logger.warning(f"Unknown regressor: {reg_name}")
            return None

    except Exception as e:
        logger.warning(f"Failed to fetch regressor {reg_name}: {e}")
        return None

    return None


async def fetch_regressors_for_metric(
    metric: str,
    start_date: date,
    end_date: date,
    regressor_names: list[str] | None = None,
) -> dict[str, pd.Series]:
    """Fetch external regressors for multi-variate forecasting.

    Story 6.11.1 AC2: MCP tool fetches external regressors when enabled.

    This function:
    1. Determines which regressors to use (explicit or auto-selected)
    2. Fetches each regressor in parallel
    3. Returns only successfully fetched regressors

    Args:
        metric: Target metric name (e.g., "revenue", "ebitda")
        start_date: Historical data start date
        end_date: Historical data end date
        regressor_names: Specific regressors to use, or None for auto-selection

    Returns:
        Dict mapping regressor names to pandas Series with datetime index.
        Empty dict if all fetches fail (enables graceful fallback to univariate).

    Example:
        >>> regressors = await fetch_regressors_for_metric(
        ...     metric="revenue",
        ...     start_date=date(2022, 1, 1),
        ...     end_date=date(2024, 12, 1),
        ... )
        >>> print(regressors.keys())
        dict_keys(['euribor_3m', 'diesel', 'ttf_gas'])
    """
    # Determine which regressors to fetch
    regressors_to_fetch = regressor_names or get_default_regressors(metric)

    logger.info(
        f"Fetching regressors for {metric}",
        extra={
            "metric": metric,
            "regressors": regressors_to_fetch,
            "start": str(start_date),
            "end": str(end_date),
        },
    )

    # Fetch all regressors in parallel
    tasks = [
        fetch_single_regressor(reg_name, start_date, end_date) for reg_name in regressors_to_fetch
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect successful results
    regressors: dict[str, pd.Series] = {}
    for reg_name, result in zip(regressors_to_fetch, results, strict=False):
        if isinstance(result, Exception):
            logger.warning(f"Regressor {reg_name} fetch failed: {result}")
        elif isinstance(result, pd.Series) and len(result) > 0:
            regressors[reg_name] = result
            logger.info(f"Fetched regressor {reg_name}: {len(result)} points")
        else:
            logger.warning(f"Regressor {reg_name} returned no data")

    logger.info(
        "Regressor fetch complete",
        extra={
            "requested": len(regressors_to_fetch),
            "successful": len(regressors),
            "regressors": list(regressors.keys()),
        },
    )

    return regressors


async def fetch_regressors_with_date_range(
    metric: str,
    historical_data_dates: list[date],
    periods_ahead: int = 4,
    regressor_names: list[str] | None = None,
) -> dict[str, pd.Series]:
    """Fetch regressors with appropriate date range for forecasting.

    This convenience function calculates the appropriate date range based on
    historical data dates and forecast horizon.

    Args:
        metric: Target metric name
        historical_data_dates: List of dates from historical time series
        periods_ahead: Number of periods to forecast
        regressor_names: Specific regressors to use, or None for auto-selection

    Returns:
        Dict of regressor name -> pandas Series
    """
    if not historical_data_dates:
        return {}

    # Extend date range to cover historical period + buffer for alignment
    start_date = min(historical_data_dates) - timedelta(days=365)  # 1 year buffer
    end_date = max(historical_data_dates) + timedelta(days=30 * periods_ahead)

    return await fetch_regressors_for_metric(
        metric=metric,
        start_date=start_date,
        end_date=end_date,
        regressor_names=regressor_names,
    )
