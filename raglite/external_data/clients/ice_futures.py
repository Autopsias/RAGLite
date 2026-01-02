"""ICE Futures client for energy commodity data.

Story 6.8: Tier 2 Data Sources & ML Enhancements (Conditional)

Fetches energy commodity prices:
- API2 Coal Index (pet coke proxy, correlation 0.7-0.85)
- TTF Natural Gas (European benchmark)

Data Source Priority:
- Primary: Quandl/Nasdaq Data Link (free tier)
- Fallback: Yahoo Finance (API2) / EEX (TTF)
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from raglite.external_data.clients.ice_futures_http import (
    fetch_quandl_data,
    fetch_yahoo_coal,
    fetch_yahoo_ttf,
)
from raglite.external_data.clients.ice_futures_parsers import (
    load_from_cache,
    parse_quandl_gas_data,
    save_to_cache,
)
from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import API2CoalPrice, CommodityPrice, TTFGasPrice
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Dataset codes for energy commodities
QUANDL_API2_COAL = "ODA/PCOALAU_USD"  # API2 Coal CIF ARA
QUANDL_TTF_GAS = "CHRIS/ICE_TFM1"  # TTF Natural Gas Front Month


class ICEFuturesClient:
    """Client for ICE Futures energy commodity data.

    Provides access to API2 Coal and TTF Natural Gas prices.
    Uses Quandl/Nasdaq Data Link as primary source with fallbacks.

    Story 6.8 AC1.1/AC1.2: Energy commodity data clients

    Example:
        >>> client = ICEFuturesClient()
        >>> coal_prices = await client.fetch_api2_coal(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 3, 31)
        ... )
        >>> gas_prices = await client.fetch_ttf_gas(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 3, 31)
        ... )
    """

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        """Initialize ICE Futures client.

        Args:
            cache_dir: Directory for caching price data
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".raglite" / "ice_futures_cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # API key from settings (optional for Quandl free tier)
        self.quandl_api_key = getattr(settings, "quandl_api_key", None)

        # Story 6.10.2 AC2: Increased test timeout from 1s to 10s for slow APIs
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 10.0 if is_test else float(settings.external_data_timeout)

    async def fetch_api2_coal(
        self,
        start_date: date,
        end_date: date,
    ) -> list[API2CoalPrice]:
        """Fetch API2 Coal (CIF ARA) settlement prices.

        API2 is the European thermal coal benchmark, suitable as
        pet coke price proxy (correlation: 0.7-0.85).

        Story 6.8 AC1.1: API2 Coal Index Client

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of API2 Coal price records

        Primary: Yahoo Finance MTF=F (Coal Futures)
        Fallback: Local cache
        Note: Quandl ODA/PCOALAU_USD permanently withdrawn (2024)
        """
        logger.info(
            "Fetching API2 Coal prices",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        # Primary: Yahoo Finance (Quandl coal datasets withdrawn in 2024)
        try:
            results = await fetch_yahoo_coal(start_date, end_date)
            if results:
                save_to_cache(self.cache_dir, "api2_coal", results)
            return results
        except ExternalDataFetchError as e:
            logger.warning(
                "Yahoo Finance coal fetch failed, using cache",
                extra={"error": str(e)},
            )
            cached = load_from_cache(self.cache_dir, "api2_coal", start_date, end_date)
            return [p for p in cached if isinstance(p, API2CoalPrice)]

    async def fetch_ttf_gas(
        self,
        start_date: date,
        end_date: date,
    ) -> list[TTFGasPrice]:
        """Fetch TTF Natural Gas settlement prices.

        Critical for thermal energy cost forecasting.
        SECIL thermal costs correlate strongly with TTF.

        Story 6.8 AC1.2: TTF Natural Gas Client

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of TTF gas price records

        Primary: Quandl TTF dataset
        Fallback: EEX API
        """
        logger.info(
            "Fetching TTF Natural Gas prices",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        try:
            data = await fetch_quandl_data(
                QUANDL_TTF_GAS,
                start_date,
                end_date,
                self.quandl_api_key,
                self.timeout,
            )
            results = parse_quandl_gas_data(data, start_date, end_date)
            if results:
                save_to_cache(self.cache_dir, "ttf_gas", results)
            return results

        except ExternalDataFetchError as e:
            logger.warning(
                "Quandl TTF fetch failed, trying EEX fallback",
                extra={"error": str(e)},
            )

            try:
                results = await self._fetch_eex_gas(start_date, end_date)
                if results:
                    save_to_cache(self.cache_dir, "ttf_gas", results)
                return results
            except ExternalDataFetchError:
                logger.warning("EEX fallback also failed, using cache")
                cached = load_from_cache(self.cache_dir, "ttf_gas", start_date, end_date)
                return [p for p in cached if isinstance(p, TTFGasPrice)]

    async def _fetch_eex_gas(
        self,
        start_date: date,
        end_date: date,
    ) -> list[TTFGasPrice]:
        """Fetch TTF gas prices from Yahoo Finance (fallback).

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of TTF gas price records

        Note: Uses Yahoo Finance TTF=F ticker which provides Dutch TTF prices.
        """
        logger.info("Fetching TTF gas from Yahoo Finance (EEX fallback)")

        try:
            return await fetch_yahoo_ttf(start_date, end_date)
        except ExternalDataFetchError:
            # Fall back to cache
            cached = load_from_cache(self.cache_dir, "ttf_gas", start_date, end_date)
            if cached:
                return [p for p in cached if isinstance(p, TTFGasPrice)]

            raise ExternalDataFetchError(
                source="Yahoo_Finance",
                message="Failed to fetch TTF gas and no cached data available",
            ) from None

    def load_from_cache(
        self,
        commodity: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CommodityPrice]:
        """Load commodity prices from local cache.

        Args:
            commodity: Commodity type (api2_coal, ttf_gas)
            start_date: Optional filter start date
            end_date: Optional filter end date

        Returns:
            List of cached price records
        """
        return load_from_cache(self.cache_dir, commodity, start_date, end_date)

    def save_to_cache(
        self,
        commodity: str,
        prices: list[CommodityPrice] | list[API2CoalPrice] | list[TTFGasPrice],
    ) -> None:
        """Save commodity prices to local cache.

        Args:
            commodity: Commodity type
            prices: List of price records to cache
        """
        save_to_cache(self.cache_dir, commodity, prices)
