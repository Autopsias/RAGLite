"""World Bank API client for GDP data.

Multi-Geography Enhancement: Fetches GDP growth for Secil geographies.

Data Source: https://api.worldbank.org/v2
API Documentation: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392

No API key required - public data.
"""

from __future__ import annotations

import httpx
import pandas as pd

from raglite.shared.caching import ExternalDataCache
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# ISO 3-letter country codes for Secil geographies
SECIL_COUNTRIES: dict[str, str] = {
    "portugal": "PRT",
    "tunisia": "TUN",
    "angola": "AGO",
    "brazil": "BRA",
    "lebanon": "LBN",
}


class WorldBankClient:
    """Client for World Bank Open Data API.

    Fetches GDP growth rate (annual % change) for multiple countries.
    Used to create multi-geography regressors for Group EBITDA forecasting.

    Example:
        >>> client = WorldBankClient()
        >>> gdp = await client.get_gdp_growth("PRT", 2020, 2024)
        >>> print(gdp)
        2020-01-01    -8.3
        2021-01-01     5.5
        ...
    """

    BASE_URL = "https://api.worldbank.org/v2"

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize World Bank client.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self._cache = ExternalDataCache(ttl_hours=168)  # 7 days cache (annual data)

    async def get_gdp_growth(
        self,
        country_code: str,
        start_year: int,
        end_year: int,
    ) -> pd.Series | None:
        """Fetch annual GDP growth rate for a country.

        Args:
            country_code: ISO 3-letter country code (e.g., "PRT", "BRA")
            start_year: Start year
            end_year: End year

        Returns:
            pandas Series with annual GDP growth (%), indexed by year-start dates.
            None if fetch fails or no data available.
        """
        # Check cache first
        cache_key = f"worldbank_gdp_{country_code}_{start_year}_{end_year}"
        cached = self._cache.get(cache_key)
        if cached:
            logger.info(
                "World Bank GDP loaded from cache",
                extra={"country": country_code, "start": start_year, "end": end_year},
            )
            # Reconstruct series from cached values with proper datetime index
            values = {pd.to_datetime(k): v for k, v in cached["values"].items()}
            series = pd.Series(values, name=cached["name"])
            series = series.sort_index()
            return series

        # NY.GDP.MKTP.KD.ZG = GDP growth (annual %)
        indicator = "NY.GDP.MKTP.KD.ZG"
        url = f"{self.BASE_URL}/country/{country_code}/indicator/{indicator}"
        params = {
            "format": "json",
            "date": f"{start_year}:{end_year}",
            "per_page": 100,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)  # type: ignore[arg-type]
                response.raise_for_status()
                data = response.json()

            # World Bank returns [metadata, data] array
            if len(data) < 2 or not data[1]:
                logger.warning(f"No GDP data from World Bank for {country_code}")
                return None

            # Parse records - filter out null values
            records = [(int(r["date"]), r["value"]) for r in data[1] if r["value"] is not None]
            if not records:
                logger.warning(f"No valid GDP values for {country_code}")
                return None

            # Create Series with year-start dates
            series = pd.Series(
                {pd.Timestamp(year=year, month=1, day=1): value for year, value in records},
                name=f"gdp_{country_code.lower()}",
            )
            series = series.sort_index()

            logger.info(
                "Fetched World Bank GDP",
                extra={
                    "country": country_code,
                    "points": len(series),
                    "start": str(series.index[0].date()),
                    "end": str(series.index[-1].date()),
                },
            )

            # Cache results - convert Timestamp keys to ISO strings for JSON
            self._cache.set(
                cache_key,
                {
                    "values": {str(k): v for k, v in series.to_dict().items()},
                    "index": [str(d) for d in series.index],
                    "name": series.name,
                },
            )

            return series

        except httpx.HTTPError as e:
            logger.warning(f"World Bank API error for {country_code}: {e}")
            return None
        except (KeyError, IndexError, ValueError) as e:
            logger.warning(f"Failed to parse World Bank response for {country_code}: {e}")
            return None
