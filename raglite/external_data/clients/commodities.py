"""Commodities price client (Coal, Petcoke, CO2 EUA).

Story 6.1: Tier 1 External Data Source Integration

Fetches commodity prices relevant to cement industry:
- Coal prices
- Petcoke (petroleum coke) prices
- CO2 EUA (EU Emissions Trading System) prices

Note: These sources often require web scraping or manual data entry.
This client provides a unified interface with local caching support.

Refactored for file size compliance:
- HTTP logic: commodities_http.py
- Parsing logic: commodities_parsers.py
- Cache operations: commodities_cache.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from raglite.external_data.clients.commodities_cache import (
    import_from_csv as _import_from_csv,
)
from raglite.external_data.clients.commodities_cache import (
    load_from_cache as _load_from_cache,
)
from raglite.external_data.clients.commodities_cache import (
    save_to_cache as _save_to_cache,
)
from raglite.external_data.clients.commodities_http import fetch_with_retry, get_timeout
from raglite.external_data.clients.commodities_parsers import parse_co2_prices, validate_co2_prices
from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import CO2EUAPrice, CoalPrice, CommodityPrice, PetcokePrice
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Data source URLs (for reference - often require scraping)
COAL_DATA_SOURCES = {
    "argus": "https://www.argusmedia.com/en/coal",
    "ici": "https://www.icis.com/explore/commodities/energy/coal/",
}

CO2_DATA_SOURCES = {
    # Ember rebranded from ember-climate.org to ember-energy.org (2025-01-01)
    # Story 6.9.1 AC4: Updated to new domain
    "ember": "https://ember-energy.org/data/carbon-price-viewer/",
    "icap": "https://icapcarbonaction.com/en/ets-prices",
}

# Story 6.29 P3: REMOVED KRBN fallback - it was providing wrong data
# KRBN is a Global Carbon ETF (~$30 USD share price), NOT EU ETS prices (~€70-85/tCO2)
# The values are completely different instruments and cannot be used interchangeably
# See: https://tradingeconomics.com/commodity/carbon for real EU ETS prices

# Sandbag Carbon Price Viewer - sources data from ICAP (official EU ETS prices)
# Historical data up to April 2025, EUR/tCO2
SANDBAG_CARBON_URL = "https://sandbag.be/carbon-price-viewer/"


class CommoditiesClient:
    """Client for commodity price data.

    Provides access to coal, petcoke, and CO2 EUA prices.
    Since these sources often don't have public APIs, this client
    supports both API fetching (where available) and local file loading.

    Example:
        >>> client = CommoditiesClient()
        >>> # From API (if available)
        >>> prices = await client.fetch_co2_prices(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 3, 31)
        ... )
        >>> # From local cache
        >>> prices = client.load_from_cache("coal")
    """

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        """Initialize commodities client.

        Args:
            cache_dir: Directory for caching price data
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".raglite" / "commodities_cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Story 6.10.2 AC2: Increased test timeout from 1s to 10s for slow APIs
        self.timeout = get_timeout()

    async def fetch_co2_prices(
        self,
        start_date: date,
        end_date: date,
    ) -> list[CO2EUAPrice]:
        """Fetch CO2 EUA prices from available sources.

        Story 6.29 P3: Removed KRBN ETF fallback - it provided wrong data.
        KRBN is a Global Carbon ETF (~$30 USD), NOT EU ETS prices (~€70-85/tCO2).

        Current fallback chain:
        1. Ember Energy API (deprecated as of 2025-01)
        2. Cache (if validated)

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of CO2 EUA price records
        """
        logger.info(
            "Fetching CO2 EUA prices",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        # Ember Energy API (likely deprecated - returns 404 as of Dec 2024)
        # Keeping for potential future reactivation
        url = "https://api.ember-energy.org/v1/carbon-price-tracker/eu-ets"

        try:
            data = await fetch_with_retry(url, self.timeout)
            results = parse_co2_prices(data, start_date, end_date)
            # Validate prices are in expected range
            validated = validate_co2_prices(results)
            if validated:
                return validated
        except ExternalDataFetchError:
            logger.warning(
                "Ember CO2 API unavailable (deprecated as of 2025-01)",
                extra={"url": url},
            )

        # Story 6.29 P3: REMOVED Yahoo Finance KRBN fallback
        # KRBN ETF share price (~$30) is NOT the same as EU ETS carbon price (~€70-85)
        # This was causing MASE of 7.63 due to fundamentally wrong data

        # Fall back to cache (only if contains validated data)
        logger.warning(
            "CO2 price API unavailable, checking cache",
            extra={"note": "Consider importing CSV with correct EU ETS prices"},
        )
        cached_results = self.load_from_cache("co2_eua", start_date, end_date)
        co2_results = [item for item in cached_results if isinstance(item, CO2EUAPrice)]

        # Validate cached data - reject if prices are too low (likely KRBN contamination)
        validated = validate_co2_prices(co2_results)
        if not validated:
            logger.error(
                "CO2 cache contains invalid data (prices below €40, likely KRBN contamination)",
                extra={
                    "cached_count": len(co2_results),
                    "min_price": min((p.price for p in co2_results), default=0),
                    "action": "Import correct EU ETS prices via CSV",
                },
            )
            return []

        return validated

    # Story 6.29 P3: DEPRECATED - KRBN provides fundamentally wrong data
    # KRBN is a Global Carbon ETF (~$30 USD share price)
    # EU ETS carbon prices are ~€70-85/tCO2 - completely different instruments
    # This method is kept for reference but should NOT be used
    async def _fetch_yahoo_co2_DEPRECATED(
        self,
        start_date: date,
        end_date: date,
    ) -> list[CO2EUAPrice]:
        """DEPRECATED: Do not use - KRBN ETF is not a valid EU ETS proxy.

        This method was returning KRBN ETF share prices (~$30 USD) instead of
        actual EU ETS carbon prices (~€70-85/tCO2). The data types are completely
        different and cannot be used interchangeably.

        See Story 6.29 P3 for details.
        """
        raise ExternalDataFetchError(
            source="Yahoo_Finance",
            message="KRBN fallback disabled - provides wrong data type (ETF price vs carbon price)",
        )

    async def fetch_coal_prices(
        self,
        start_date: date,
        end_date: date,
    ) -> list[CoalPrice]:
        """Fetch coal prices.

        Note: Coal price APIs are typically commercial. This method
        attempts to fetch from available sources or falls back to cache.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of coal price records
        """
        logger.info(
            "Fetching coal prices",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        # Coal prices typically require commercial APIs
        # Fall back to cache/manual data
        cached_results = self.load_from_cache("coal", start_date, end_date)
        # Cast is safe: load_from_cache with "coal" only returns CoalPrice instances
        return [item for item in cached_results if isinstance(item, CoalPrice)]

    async def fetch_petcoke_prices(
        self,
        start_date: date,
        end_date: date,
    ) -> list[PetcokePrice]:
        """Fetch petcoke prices.

        Note: Petcoke price APIs are typically commercial. This method
        falls back to cache.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of petcoke price records
        """
        logger.info(
            "Fetching petcoke prices",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        cached_results = self.load_from_cache("petcoke", start_date, end_date)
        # Cast is safe: load_from_cache with "petcoke" only returns PetcokePrice instances
        return [item for item in cached_results if isinstance(item, PetcokePrice)]

    def load_from_cache(
        self,
        commodity: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CommodityPrice]:
        """Load commodity prices from local cache.

        Args:
            commodity: Commodity type (coal, petcoke, co2_eua)
            start_date: Optional filter start date
            end_date: Optional filter end date

        Returns:
            List of cached price records
        """
        return _load_from_cache(self.cache_dir, commodity, start_date, end_date)

    def save_to_cache(
        self,
        commodity: str,
        prices: list[CommodityPrice] | list[CO2EUAPrice] | list[CoalPrice] | list[PetcokePrice],
    ) -> None:
        """Save commodity prices to local cache.

        Args:
            commodity: Commodity type
            prices: List of price records to cache
        """
        _save_to_cache(self.cache_dir, commodity, prices)

    def import_from_csv(
        self,
        commodity: str,
        csv_path: str | Path,
    ) -> list[CommodityPrice]:
        """Import commodity prices from CSV file.

        Expected CSV format:
        date,price,currency,unit,[commodity-specific columns]

        Args:
            commodity: Commodity type
            csv_path: Path to CSV file

        Returns:
            List of imported price records
        """
        return _import_from_csv(self.cache_dir, commodity, csv_path)
