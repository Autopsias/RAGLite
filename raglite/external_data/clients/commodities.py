"""Commodities price client (Coal, Petcoke, CO2 EUA).

Story 6.1: Tier 1 External Data Source Integration

Fetches commodity prices relevant to cement industry:
- Coal prices
- Petcoke (petroleum coke) prices
- CO2 EUA (EU Emissions Trading System) prices

Note: These sources often require web scraping or manual data entry.
This client provides a unified interface with local caching support.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import date
from pathlib import Path

import httpx

from raglite.external_data.exceptions import (
    ExternalDataFetchError,
)
from raglite.external_data.models import CO2EUAPrice, CoalPrice, CommodityPrice, PetcokePrice
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Data source URLs (for reference - often require scraping)
COAL_DATA_SOURCES = {
    "argus": "https://www.argusmedia.com/en/coal",
    "ici": "https://www.icis.com/explore/commodities/energy/coal/",
}

CO2_DATA_SOURCES = {
    "ember": "https://ember-climate.org/data/carbon-price-viewer/",
    "icap": "https://icapcarbonaction.com/en/ets-prices",
}


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

        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 1.0 if is_test else float(settings.external_data_timeout)

    async def _fetch_with_retry(self, url: str) -> dict:
        """Fetch data from URL with retry logic.

        Args:
            url: API URL

        Returns:
            JSON response

        Raises:
            ExternalDataFetchError: If all retries fail
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [1, 2, 4]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    return dict(response.json())

                except httpx.TimeoutException as e:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "Commodities API timeout, retrying",
                            extra={"attempt": attempt + 1, "delay": delay},
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="Commodities",
                            message="Timeout after retries",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    # Retry on server errors (5xx) or rate limit (429)
                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="Commodities",
                            message=f"HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        raise ExternalDataFetchError(source="Commodities", message="Unexpected retry loop exit")

    async def fetch_co2_prices(
        self,
        start_date: date,
        end_date: date,
    ) -> list[CO2EUAPrice]:
        """Fetch CO2 EUA prices from Ember Climate.

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

        # Ember Climate has a public API for carbon prices
        url = "https://api.ember-climate.org/v1/carbon-price-tracker/eu-ets"

        try:
            data = await self._fetch_with_retry(url)
            return self._parse_co2_prices(data, start_date, end_date)
        except ExternalDataFetchError:
            # Fall back to cache
            logger.warning("Failed to fetch CO2 prices from API, using cache")
            cached_results = self.load_from_cache("co2_eua", start_date, end_date)
            # Cast is safe: load_from_cache with "co2_eua" only returns CO2EUAPrice instances
            return [item for item in cached_results if isinstance(item, CO2EUAPrice)]

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

    def _parse_co2_prices(
        self,
        data: dict,
        start_date: date,
        end_date: date,
    ) -> list[CO2EUAPrice]:
        """Parse CO2 EUA price data.

        Args:
            data: API response
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            List of CO2 EUA price records
        """
        results: list[CO2EUAPrice] = []

        for record in data.get("data", []):
            try:
                date_str = record.get("date")
                if not date_str:
                    continue

                record_date = date.fromisoformat(date_str)
                if not (start_date <= record_date <= end_date):
                    continue

                price = record.get("price", record.get("value"))
                if price is None:
                    continue

                results.append(
                    CO2EUAPrice(
                        date=record_date,
                        price=float(price),
                        currency="EUR",
                    )
                )
            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse CO2 price record",
                    extra={"error": str(e)},
                )
                continue

        return results

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

                # Create appropriate model based on commodity type
                price_obj: CommodityPrice
                if commodity == "coal":
                    price_obj = CoalPrice(
                        date=record_date,
                        price=float(record["price"]),
                        currency=record.get("currency", "EUR"),
                        grade=record.get("grade"),
                    )
                elif commodity == "petcoke":
                    price_obj = PetcokePrice(
                        date=record_date,
                        price=float(record["price"]),
                        currency=record.get("currency", "EUR"),
                        sulfur_content_pct=record.get("sulfur_content_pct"),
                    )
                elif commodity == "co2_eua":
                    price_obj = CO2EUAPrice(
                        date=record_date,
                        price=float(record["price"]),
                        currency=record.get("currency", "EUR"),
                    )
                else:
                    price_obj = CommodityPrice(
                        date=record_date,
                        commodity=commodity,
                        price=float(record["price"]),
                        currency=record.get("currency", "EUR"),
                        unit=record.get("unit", "EUR/tonne"),
                    )
                results.append(price_obj)
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

            # Add commodity-specific fields
            if isinstance(price, CoalPrice):
                record["grade"] = price.grade
            elif isinstance(price, PetcokePrice):
                record["sulfur_content_pct"] = price.sulfur_content_pct
            elif isinstance(price, CO2EUAPrice):
                record["market"] = price.market

            existing_by_date[price.date.isoformat()] = record

        # Sort by date and save
        sorted_data = sorted(existing_by_date.values(), key=lambda x: x["date"])

        with open(cache_file, "w") as f:
            json.dump(sorted_data, f, indent=2)

        logger.info(
            f"Saved {len(prices)} {commodity} prices to cache",
            extra={"cache_file": str(cache_file), "total_records": len(sorted_data)},
        )

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
        import csv

        path = Path(csv_path)
        if not path.exists():
            raise ExternalDataFetchError(
                source="Commodities",
                message=f"CSV file not found: {csv_path}",
            )

        results: list[CommodityPrice] = []

        with open(path) as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    record_date = date.fromisoformat(row["date"])
                    price_val = float(row["price"])
                    currency = row.get("currency", "EUR")
                    unit = row.get("unit", "EUR/tonne")

                    price_obj: CommodityPrice
                    if commodity == "coal":
                        price_obj = CoalPrice(
                            date=record_date,
                            price=price_val,
                            currency=currency,
                            grade=row.get("grade"),
                        )
                    elif commodity == "petcoke":
                        price_obj = PetcokePrice(
                            date=record_date,
                            price=price_val,
                            currency=currency,
                            sulfur_content_pct=(
                                float(row["sulfur_content_pct"])
                                if row.get("sulfur_content_pct")
                                else None
                            ),
                        )
                    elif commodity == "co2_eua":
                        price_obj = CO2EUAPrice(
                            date=record_date,
                            price=price_val,
                            currency=currency,
                        )
                    else:
                        price_obj = CommodityPrice(
                            date=record_date,
                            commodity=commodity,
                            price=price_val,
                            currency=currency,
                            unit=unit,
                        )
                    results.append(price_obj)
                except (ValueError, KeyError) as e:
                    logger.warning(
                        f"Failed to parse CSV row for {commodity}",
                        extra={"error": str(e)},
                    )
                    continue

        # Save to cache
        self.save_to_cache(commodity, results)

        logger.info(
            f"Imported {len(results)} {commodity} prices from CSV",
            extra={"csv_path": str(csv_path)},
        )

        return results
