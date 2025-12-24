"""External regressor fetching for multi-variate forecasting.

Story 6.11.1: MCP Multi-Variate Forecasting Interface
Story 7.0: REN Data Hub integration for electricity cost
Story 7b-7: Demand-side regressors (housing transactions, dwelling completions)

This module provides functions to fetch external regressor data from various APIs
for use in multi-variate forecasting with Prophet.

Supported regressors:
- euribor_3m: 3-month EURIBOR rate (ECB)
- ttf_gas: TTF natural gas price (ICE Futures)
- api2_coal: API2 coal price (ICE Futures)
- diesel: Diesel price (EU Oil Bulletin)
- eurostat_electricity: Industrial electricity price (Eurostat) - 9 points only
- ren_electricity: Portuguese spot electricity (REN Data Hub) - 60+ monthly points
- housing_transactions: Quarterly housing transactions (Eurostat) - Story 7b-7
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

import pandas as pd

from raglite.forecasting.regressor_config import get_default_regressors
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def interpolate_quarterly_series_to_monthly(
    quarterly_series: pd.Series,
    method: str = "linear",
) -> pd.Series:
    """Interpolate quarterly data to monthly frequency.

    Story 7b-7 AC3: Prophet and other models require monthly regressors.

    Uses linear interpolation (default) to create monthly values from quarterly data.
    This is more appropriate for economic indicators than cubic spline, which can
    create unrealistic oscillations.

    Note: This function is named with '_series_' to avoid shadowing the ECB module's
    interpolate_quarterly_to_monthly which works with ECB-specific types.

    Args:
        quarterly_series: Series with quarterly DatetimeIndex (quarter-end dates)
        method: Interpolation method ('linear', 'ffill', 'cubic')
            - 'linear': Smooth linear interpolation (default, recommended)
            - 'ffill': Forward-fill (step function, preserves original values)
            - 'cubic': Cubic spline (smoother but can overshoot)

    Returns:
        Series with monthly DatetimeIndex

    Example:
        >>> q_data = pd.Series([100, 110, 105],
        ...     index=pd.to_datetime(['2024-03-31', '2024-06-30', '2024-09-30']))
        >>> monthly = interpolate_quarterly_series_to_monthly(q_data)
        >>> len(monthly)  # 7 months (Mar-Sep)
        7
    """
    if quarterly_series.empty:
        return quarterly_series

    # Ensure datetime index
    if not isinstance(quarterly_series.index, pd.DatetimeIndex):
        quarterly_series = quarterly_series.copy()
        quarterly_series.index = pd.to_datetime(quarterly_series.index)

    # Sort by date
    quarterly_series = quarterly_series.sort_index()

    # Resample to month-start frequency and interpolate
    # Use 'MS' (month start) to align with typical financial data
    monthly = quarterly_series.resample("MS").asfreq()

    # Interpolate missing months
    if method == "ffill":
        monthly = monthly.ffill()
    elif method == "cubic":
        monthly = monthly.interpolate(method="cubic")
    else:
        # Default: linear interpolation
        monthly = monthly.interpolate(method="linear")

    # Fill any remaining NaNs at boundaries
    monthly = monthly.bfill().ffill()

    # Drop NaN values that couldn't be filled
    monthly = monthly.dropna()

    logger.debug(
        "Interpolated quarterly to monthly",
        extra={
            "quarterly_points": len(quarterly_series),
            "monthly_points": len(monthly),
            "method": method,
        },
    )

    return monthly


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

        elif reg_name == "ren_electricity":
            # Story 7.0: REN Data Hub Portuguese spot electricity prices
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

        elif reg_name == "construction_output":
            from raglite.external_data.clients.eurostat import EurostatClient

            client_eurostat_constr: EurostatClient = EurostatClient()
            construction_data = await client_eurostat_constr.fetch_construction_output(
                start_date=start_date, end_date=end_date
            )
            if construction_data:
                series = pd.Series(
                    [d.index_value for d in construction_data],
                    index=pd.DatetimeIndex([d.date for d in construction_data]),
                )
                series = series.groupby(level=0).mean()
                return series

        elif reg_name == "industrial_production":
            from raglite.external_data.clients.eurostat import EurostatClient

            client_eurostat_ind: EurostatClient = EurostatClient()
            industrial_data = await client_eurostat_ind.fetch_industrial_production(
                start_date=start_date, end_date=end_date
            )
            if industrial_data:
                series = pd.Series(
                    [d.index_value for d in industrial_data],
                    index=pd.DatetimeIndex([d.date for d in industrial_data]),
                )
                series = series.groupby(level=0).mean()
                return series

        elif reg_name == "gdp_growth":
            # Story 6.17 AC1: GDP growth rate for demand-side forecasting
            from raglite.external_data.clients.ecb import (
                ECBClient,
                interpolate_quarterly_to_monthly,
            )

            client_ecb_gdp: ECBClient = ECBClient()
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

        elif reg_name == "inflation":
            # Story 6.17 AC2: HICP inflation for pricing/cost forecasting
            from raglite.external_data.clients.ecb import ECBClient

            client_ecb_hicp: ECBClient = ECBClient()
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

        elif reg_name == "building_permits":
            # Story 6.18: INE building permits with Eurostat fallback
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
                    national_permits = [
                        p for p in permits_data if p.region.lower() in national_keywords
                    ]

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

            # Fallback to Eurostat
            from raglite.external_data.clients.eurostat import EurostatClient

            try:
                client_eurostat = EurostatClient()
                eurostat_data = await client_eurostat.fetch_building_permits(
                    country="PT", start_date=start_date, end_date=end_date
                )

                if eurostat_data:
                    series = pd.Series(
                        [d.permits_count for d in eurostat_data],
                        index=pd.DatetimeIndex([d.date for d in eurostat_data]),
                    )
                    series = series.groupby(level=0).sum()
                    logger.info(
                        "Fetched building permits regressor",
                        extra={"source": "Eurostat (fallback)", "data_points": len(series)},
                    )
                    return series
            except Exception as e:
                logger.warning(f"Eurostat building permits fallback failed: {e}")

            return None

        elif reg_name == "construction_confidence":
            # Story 6.19: EC Construction Confidence via Eurostat
            from raglite.external_data.clients.eurostat import EurostatClient

            client_eurostat = EurostatClient()
            confidence_data = await client_eurostat.fetch_construction_confidence(
                country="PT", start_date=start_date, end_date=end_date
            )

            if confidence_data:
                series = pd.Series(
                    [d.confidence_index for d in confidence_data],
                    index=pd.DatetimeIndex([d.date for d in confidence_data]),
                )
                series = series.groupby(level=0).mean()
                logger.info(
                    "Fetched construction confidence regressor",
                    extra={"source": "Eurostat (EC)", "data_points": len(series)},
                )
                return series

            return None

        elif reg_name == "housing_transactions":
            # Story 7b-7: Housing transactions (demand-side regressor)
            from raglite.external_data.clients.eurostat_housing import EurostatHousingClient

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

        elif reg_name == "dwelling_completions":
            # Story 7b-7: Dwelling completions (demand-side regressor)
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

        elif reg_name == "omie_spot":
            # NOTE: Currently disabled - too slow (1000+ HTTP requests)
            # Use ren_electricity as faster alternative (same underlying MIBEL data)
            logger.warning(f"Regressor {reg_name} disabled - too slow, use ren_electricity")
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

    # Convert datetime to date if necessary (handles both date and datetime objects)
    dates_as_dates = [
        d.date() if hasattr(d, "date") and callable(d.date) else d for d in historical_data_dates
    ]

    # Extend date range to cover historical period + buffer for alignment
    # Story 6.24: Buffer is now configurable via settings.regressor_buffer_years
    # Production uses 3-year buffer for correlation detection; tests use 1-year for speed
    buffer_days = settings.regressor_buffer_years * 365
    start_date = min(dates_as_dates) - timedelta(days=buffer_days)
    end_date = max(dates_as_dates) + timedelta(days=30 * periods_ahead)

    return await fetch_regressors_for_metric(
        metric=metric,
        start_date=start_date,
        end_date=end_date,
        regressor_names=regressor_names,
    )
