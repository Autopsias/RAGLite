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

import asyncio
import json
import os
from datetime import date
from pathlib import Path

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import API2CoalPrice, CommodityPrice, TTFGasPrice
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Quandl/Nasdaq Data Link API
QUANDL_API_BASE = "https://data.nasdaq.com/api/v3/datasets"

# Dataset codes for energy commodities
QUANDL_API2_COAL = "ODA/PCOALAU_USD"  # API2 Coal CIF ARA
QUANDL_TTF_GAS = "CHRIS/ICE_TFM1"  # TTF Natural Gas Front Month

# Yahoo Finance tickers (fallback)
YAHOO_API2_TICKER = "MTF=F"  # Coal futures proxy

# EEX API (fallback for TTF)
EEX_API_BASE = "https://www.eex.com/en/market-data"


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

        # Use test timeout in test environment
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 1.0 if is_test else float(settings.external_data_timeout)

    async def _fetch_with_retry(self, url: str, params: dict | None = None) -> dict:
        """Fetch data from URL with retry logic.

        Args:
            url: API URL
            params: Query parameters

        Returns:
            JSON response

        Raises:
            ExternalDataFetchError: If all retries fail
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [2, 4, 8]  # NFR1: exponential backoff at 2s/4s/8s intervals

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    return dict(response.json())

                except httpx.TimeoutException as e:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "ICE Futures API timeout, retrying",
                            extra={"attempt": attempt + 1, "delay": delay},
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="ICE_Futures",
                            message="Timeout after retries",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="ICE_Futures",
                            message=f"HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        raise ExternalDataFetchError(source="ICE_Futures", message="Unexpected retry loop exit")

    async def _fetch_quandl_data(
        self,
        dataset_code: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Fetch data from Quandl/Nasdaq Data Link.

        Args:
            dataset_code: Quandl dataset code (e.g., "ODA/PCOALAU_USD")
            start_date: Start of date range
            end_date: End of date range

        Returns:
            JSON response with dataset
        """
        url = f"{QUANDL_API_BASE}/{dataset_code}.json"

        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "order": "desc",
        }

        if self.quandl_api_key:
            params["api_key"] = self.quandl_api_key

        logger.info(
            "Fetching Quandl data",
            extra={"dataset": dataset_code, "start": str(start_date), "end": str(end_date)},
        )

        return await self._fetch_with_retry(url, params)

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

        Primary: Quandl/Nasdaq Data Link
        Fallback: Yahoo Finance (delayed)
        """
        logger.info(
            "Fetching API2 Coal prices",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        try:
            data = await self._fetch_quandl_data(
                QUANDL_API2_COAL,
                start_date,
                end_date,
            )
            return self._parse_quandl_coal_data(data, start_date, end_date)

        except ExternalDataFetchError as e:
            logger.warning(
                "Quandl API2 Coal fetch failed, trying Yahoo fallback",
                extra={"error": str(e)},
            )

            try:
                return await self._fetch_yahoo_coal(start_date, end_date)
            except ExternalDataFetchError:
                logger.warning("Yahoo fallback also failed, using cache")
                cached = self.load_from_cache("api2_coal", start_date, end_date)
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
            data = await self._fetch_quandl_data(
                QUANDL_TTF_GAS,
                start_date,
                end_date,
            )
            return self._parse_quandl_gas_data(data, start_date, end_date)

        except ExternalDataFetchError as e:
            logger.warning(
                "Quandl TTF fetch failed, trying EEX fallback",
                extra={"error": str(e)},
            )

            try:
                return await self._fetch_eex_gas(start_date, end_date)
            except ExternalDataFetchError:
                logger.warning("EEX fallback also failed, using cache")
                cached = self.load_from_cache("ttf_gas", start_date, end_date)
                return [p for p in cached if isinstance(p, TTFGasPrice)]

    def _parse_quandl_coal_data(
        self,
        data: dict,
        start_date: date,
        end_date: date,
    ) -> list[API2CoalPrice]:
        """Parse Quandl API2 Coal response.

        Args:
            data: JSON response from Quandl
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            List of API2 Coal price records
        """
        results: list[API2CoalPrice] = []

        dataset = data.get("dataset", data)
        raw_data = dataset.get("data", [])

        for row in raw_data:
            try:
                if len(row) < 2:
                    continue

                date_str = row[0]
                price = row[1]

                if not date_str or price is None:
                    continue

                record_date = date.fromisoformat(date_str)

                if not (start_date <= record_date <= end_date):
                    continue

                results.append(
                    API2CoalPrice(
                        date=record_date,
                        price=float(price),
                        currency="USD",
                    )
                )

            except (ValueError, IndexError) as e:
                logger.warning(
                    "Failed to parse Quandl coal record",
                    extra={"row": row, "error": str(e)},
                )
                continue

        logger.info(
            "Parsed API2 Coal prices",
            extra={"count": len(results)},
        )
        return results

    def _parse_quandl_gas_data(
        self,
        data: dict,
        start_date: date,
        end_date: date,
    ) -> list[TTFGasPrice]:
        """Parse Quandl TTF gas response.

        Args:
            data: JSON response from Quandl
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            List of TTF gas price records
        """
        results: list[TTFGasPrice] = []

        dataset = data.get("dataset", data)
        raw_data = dataset.get("data", [])

        # TTF data columns: Date, Open, High, Low, Settle, Change, Volume, Open Interest
        # We use Settle (index 4) or Open (index 1) if Settle not available
        settle_idx = 4
        open_idx = 1

        for row in raw_data:
            try:
                if len(row) < 2:
                    continue

                date_str = row[0]

                # Try settle price first, then open
                price = None
                if len(row) > settle_idx and row[settle_idx] is not None:
                    price = row[settle_idx]
                elif len(row) > open_idx and row[open_idx] is not None:
                    price = row[open_idx]
                else:
                    price = row[1]  # Fallback to second column

                if not date_str or price is None:
                    continue

                record_date = date.fromisoformat(date_str)

                if not (start_date <= record_date <= end_date):
                    continue

                results.append(
                    TTFGasPrice(
                        date=record_date,
                        price=float(price),
                        currency="EUR",
                    )
                )

            except (ValueError, IndexError) as e:
                logger.warning(
                    "Failed to parse Quandl TTF record",
                    extra={"row": row, "error": str(e)},
                )
                continue

        logger.info(
            "Parsed TTF Gas prices",
            extra={"count": len(results)},
        )
        return results

    async def _fetch_yahoo_coal(
        self,
        start_date: date,
        end_date: date,
    ) -> list[API2CoalPrice]:
        """Fetch coal prices from Yahoo Finance (fallback).

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of coal price records
        """
        # Yahoo Finance API for coal futures proxy
        # Note: This uses yfinance-compatible endpoint
        import time

        period1 = int(time.mktime(start_date.timetuple()))
        period2 = int(time.mktime(end_date.timetuple()))

        url = (
            f"https://query1.finance.yahoo.com/v7/finance/download/{YAHOO_API2_TICKER}"
            f"?period1={period1}&period2={period2}&interval=1d&events=history"
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()

                lines = response.text.strip().split("\n")
                results: list[API2CoalPrice] = []

                for line in lines[1:]:  # Skip header
                    parts = line.split(",")
                    if len(parts) >= 5:
                        try:
                            record_date = date.fromisoformat(parts[0])
                            close_price = float(parts[4])  # Adj Close

                            results.append(
                                API2CoalPrice(
                                    date=record_date,
                                    price=close_price,
                                    currency="USD",
                                )
                            )
                        except (ValueError, IndexError):
                            continue

                return results

        except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
            raise ExternalDataFetchError(
                source="Yahoo_Finance",
                message=f"Failed to fetch coal prices: {e}",
                original_error=e,
            ) from e

    async def _fetch_eex_gas(
        self,
        start_date: date,
        end_date: date,
    ) -> list[TTFGasPrice]:
        """Fetch TTF gas prices from EEX (fallback).

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of TTF gas price records

        Note: EEX requires web scraping or has limited public API.
        This returns cached data if available.
        """
        logger.warning("EEX API requires authentication, using cache fallback")

        # EEX doesn't have a free public API, fall back to cache
        cached = self.load_from_cache("ttf_gas", start_date, end_date)
        if cached:
            return [p for p in cached if isinstance(p, TTFGasPrice)]

        raise ExternalDataFetchError(
            source="EEX",
            message="EEX API requires authentication and no cached data available",
        )

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
        cache_file = self.cache_dir / f"{commodity}_prices.json"

        if not cache_file.exists():
            logger.warning(
                f"No cached data for {commodity}",
                extra={"cache_file": str(cache_file)},
            )
            return []

        try:
            with open(cache_file) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(
                f"Failed to load {commodity} cache",
                extra={"error": str(e)},
            )
            return []

        results: list[CommodityPrice] = []
        for record in data:
            try:
                record_date = date.fromisoformat(record["date"])

                if start_date and record_date < start_date:
                    continue
                if end_date and record_date > end_date:
                    continue

                if commodity == "api2_coal":
                    results.append(
                        API2CoalPrice(
                            date=record_date,
                            price=float(record["price"]),
                            currency=record.get("currency", "USD"),
                        )
                    )
                elif commodity == "ttf_gas":
                    results.append(
                        TTFGasPrice(
                            date=record_date,
                            price=float(record["price"]),
                            currency=record.get("currency", "EUR"),
                        )
                    )

            except (ValueError, KeyError) as e:
                logger.warning(
                    f"Failed to parse cached {commodity} record",
                    extra={"error": str(e)},
                )
                continue

        return results

    def save_to_cache(
        self,
        commodity: str,
        prices: list[CommodityPrice],
    ) -> None:
        """Save commodity prices to local cache.

        Args:
            commodity: Commodity type
            prices: List of price records to cache
        """
        cache_file = self.cache_dir / f"{commodity}_prices.json"

        # Load existing data
        existing = []
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    existing = json.load(f)
            except (OSError, json.JSONDecodeError):
                pass

        # Convert existing to dict keyed by date
        existing_by_date = {r["date"]: r for r in existing}

        # Add new prices (overwrite if date exists)
        for price in prices:
            record = {
                "date": price.date.isoformat(),
                "price": price.price,
                "currency": price.currency,
                "unit": price.unit,
            }
            existing_by_date[price.date.isoformat()] = record

        # Sort by date and save
        sorted_data = sorted(existing_by_date.values(), key=lambda x: x["date"])

        with open(cache_file, "w") as f:
            json.dump(sorted_data, f, indent=2)

        logger.info(
            f"Saved {len(prices)} {commodity} prices to cache",
            extra={"cache_file": str(cache_file), "total_records": len(sorted_data)},
        )
