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

import pandas as pd

from raglite.forecasting.regressor_config import get_default_regressors
from raglite.forecasting.regressors.ecb_fetchers import (
    fetch_euribor_3m,
    fetch_gdp_growth,
    fetch_inflation,
)
from raglite.forecasting.regressors.eurostat_fetchers import (
    fetch_construction_confidence,
    fetch_construction_output,
    fetch_eurostat_building_permits,
    fetch_eurostat_electricity,
    fetch_industrial_production,
)
from raglite.forecasting.regressors.ice_fetchers import (
    fetch_api2_coal,
    fetch_ttf_gas,
)
from raglite.forecasting.regressors.misc_fetchers import (
    fetch_diesel,
    fetch_dwelling_completions,
    fetch_housing_transactions,
    fetch_ine_building_permits,
    fetch_ren_electricity,
)
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
            return await fetch_euribor_3m(start_date, end_date)

        elif reg_name == "ttf_gas":
            return await fetch_ttf_gas(start_date, end_date)

        elif reg_name == "api2_coal":
            return await fetch_api2_coal(start_date, end_date)

        elif reg_name == "diesel":
            return await fetch_diesel(start_date, end_date)

        elif reg_name == "eurostat_electricity":
            return await fetch_eurostat_electricity(start_date, end_date)

        elif reg_name == "ren_electricity":
            return await fetch_ren_electricity(start_date, end_date)

        elif reg_name == "construction_output":
            return await fetch_construction_output(start_date, end_date)

        elif reg_name == "industrial_production":
            return await fetch_industrial_production(start_date, end_date)

        elif reg_name == "gdp_growth":
            return await fetch_gdp_growth(start_date, end_date)

        elif reg_name == "inflation":
            return await fetch_inflation(start_date, end_date)

        elif reg_name == "building_permits":
            # Story 6.18: INE building permits with Eurostat fallback
            # Try INE first, fallback to Eurostat
            result = await fetch_ine_building_permits(start_date, end_date)
            if result is None:
                result = await fetch_eurostat_building_permits(start_date, end_date)
            return result

        elif reg_name == "construction_confidence":
            return await fetch_construction_confidence(start_date, end_date)

        elif reg_name == "housing_transactions":
            return await fetch_housing_transactions(start_date, end_date)

        elif reg_name == "dwelling_completions":
            return await fetch_dwelling_completions(start_date, end_date)

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
