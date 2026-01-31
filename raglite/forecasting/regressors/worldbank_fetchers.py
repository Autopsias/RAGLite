"""World Bank GDP regressor fetchers for Secil geographies.

Multi-Geography Enhancement: Per-country GDP growth regressors.

Secil Geographic Presence:
- Portugal: ~72% of Group EBITDA
- Tunisia: ~10% of Group EBITDA
- Angola: ~8% of Group EBITDA
- Brazil: ~7% of Group EBITDA
- Lebanon: ~3% of Group EBITDA
"""

from __future__ import annotations

import asyncio
from datetime import date

import pandas as pd

from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# EBITDA weights by geography (based on Secil Group structure)
EBITDA_WEIGHTS: dict[str, float] = {
    "portugal": 0.72,
    "tunisia": 0.10,
    "angola": 0.08,
    "brazil": 0.07,
    "lebanon": 0.03,
}


def _interpolate_annual_to_monthly(annual_series: pd.Series) -> pd.Series:
    """Interpolate annual GDP data to monthly frequency.

    Uses linear interpolation between annual values to create monthly series.
    This is appropriate for GDP growth rates which evolve smoothly.

    Args:
        annual_series: Series with annual DatetimeIndex (year-start dates)

    Returns:
        Series with monthly DatetimeIndex
    """
    if annual_series.empty:
        return annual_series

    # Create monthly date range covering the full period
    start = annual_series.index.min()
    end = annual_series.index.max()
    monthly_index = pd.date_range(start=start, end=end, freq="MS")

    # Reindex to monthly and interpolate
    monthly = annual_series.reindex(annual_series.index.union(monthly_index))
    monthly = monthly.interpolate(method="linear")

    # Return only the monthly index points
    return monthly.reindex(monthly_index)


async def _fetch_country_gdp(
    country: str,
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch GDP growth for a specific country and interpolate to monthly.

    Args:
        country: Country name (lowercase, e.g., "portugal", "brazil")
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Monthly GDP growth series, or None if fetch fails
    """
    from raglite.external_data.clients.worldbank.client import (
        SECIL_COUNTRIES,
        WorldBankClient,
    )

    country_code = SECIL_COUNTRIES.get(country.lower())
    if not country_code:
        logger.warning(f"Unknown country: {country}")
        return None

    try:
        client = WorldBankClient()
        # Fetch extra years for interpolation buffer
        annual_gdp = await client.get_gdp_growth(
            country_code,
            start_date.year - 1,
            end_date.year + 1,
        )

        if annual_gdp is None or len(annual_gdp) == 0:
            return None

        # Interpolate to monthly
        monthly_gdp = _interpolate_annual_to_monthly(annual_gdp)
        monthly_gdp.name = f"gdp_{country}"

        # Filter to requested date range
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        monthly_gdp = monthly_gdp[(monthly_gdp.index >= start_ts) & (monthly_gdp.index <= end_ts)]

        logger.info(
            f"Fetched {country} GDP",
            extra={"points": len(monthly_gdp), "country": country},
        )
        return monthly_gdp

    except Exception as e:
        logger.warning(f"Failed to fetch GDP for {country}: {e}")
        return None


# =============================================================================
# Individual Country Fetchers
# =============================================================================


async def fetch_gdp_portugal_wb(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch Portugal GDP growth from World Bank.

    Note: Named with _wb suffix to distinguish from ECB gdp_growth regressor.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Monthly GDP growth series (%), or None if fetch fails
    """
    return await _fetch_country_gdp("portugal", start_date, end_date)


async def fetch_gdp_tunisia(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch Tunisia GDP growth from World Bank.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Monthly GDP growth series (%), or None if fetch fails
    """
    return await _fetch_country_gdp("tunisia", start_date, end_date)


async def fetch_gdp_angola(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch Angola GDP growth from World Bank.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Monthly GDP growth series (%), or None if fetch fails
    """
    return await _fetch_country_gdp("angola", start_date, end_date)


async def fetch_gdp_brazil(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch Brazil GDP growth from World Bank.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Monthly GDP growth series (%), or None if fetch fails
    """
    return await _fetch_country_gdp("brazil", start_date, end_date)


async def fetch_gdp_lebanon(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch Lebanon GDP growth from World Bank.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Monthly GDP growth series (%), or None if fetch fails
    """
    return await _fetch_country_gdp("lebanon", start_date, end_date)


# =============================================================================
# Weighted Composite
# =============================================================================


async def fetch_gdp_weighted_composite(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch weighted GDP composite for all Secil geographies.

    Weights based on EBITDA contribution:
    - Portugal: 72%
    - Tunisia: 10%
    - Angola: 8%
    - Brazil: 7%
    - Lebanon: 3%

    This composite provides a single regressor that captures economic conditions
    across all Secil markets, weighted by their financial importance.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Monthly weighted GDP growth series (%), or None if all fetches fail
    """
    # Fetch all countries in parallel
    tasks = {
        country: _fetch_country_gdp(country, start_date, end_date)
        for country in EBITDA_WEIGHTS.keys()
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    gdp_data = dict(zip(tasks.keys(), results, strict=False))

    # Calculate weighted composite
    composite: pd.Series | None = None
    total_weight = 0.0

    for country, weight in EBITDA_WEIGHTS.items():
        series = gdp_data.get(country)
        if isinstance(series, pd.Series) and len(series) > 0:
            if composite is None:
                composite = series * weight
            else:
                # Align indices and add
                composite = composite.add(series * weight, fill_value=0)
            total_weight += weight

    if composite is not None and total_weight > 0:
        # Normalize by actual weight coverage
        composite = composite / total_weight
        composite.name = "gdp_weighted_composite"

        logger.info(
            "Created weighted GDP composite",
            extra={
                "coverage_pct": round(total_weight * 100, 1),
                "points": len(composite),
                "countries": [c for c, s in gdp_data.items() if isinstance(s, pd.Series)],
            },
        )
        return composite

    logger.warning("Failed to create GDP composite - no country data available")
    return None
