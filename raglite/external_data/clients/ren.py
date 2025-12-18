"""REN Data Hub client for Portuguese electricity market data.

Story 7.0: Electricity Cost Forecasting Fix via REN Integration

Fetches Portuguese electricity market data from REN Data Hub:
- Daily spot prices (day-ahead market, hourly)
- Monthly average prices

Data Source: https://datahub.ren.pt/
API Base: https://servicebus.ren.pt/datahubapi/
License: Public data (Portuguese grid operator)
Updates: Daily for daily data, Monthly for monthly aggregates

IMPORTANT: This client provides Portuguese electricity spot prices (OMIE/MIBEL)
through REN's cleaned API, which is faster than direct OMIE access.
"""

from __future__ import annotations

import asyncio
import calendar
import os
from datetime import date, timedelta
from typing import Any, cast

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import RENElectricityPrice
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# REN Data Hub API Base URL
REN_API_BASE = "https://servicebus.ren.pt/datahubapi/electricity"

# API Endpoints
DAILY_PRICES_URL = f"{REN_API_BASE}/ElectricityMarketPricesDaily"
MONTHLY_PRICES_URL = f"{REN_API_BASE}/ElectricityMarketPricesMonthly"


class RENClient:
    """Client for REN Data Hub Portuguese electricity prices.

    REN (Redes Energéticas Nacionais) is the Portuguese grid operator.
    Their Data Hub provides cleaned OMIE/MIBEL electricity market data.

    No API token required - uses public JSON endpoints.

    Example:
        >>> client = RENClient()
        >>> prices = await client.fetch_daily_prices(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 1, 31),
        ... )
    """

    def __init__(self) -> None:
        """Initialize REN Data Hub client.

        No API token required - uses public JSON API.
        """
        # Use external data timeout settings
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 10.0 if is_test else float(settings.external_data_timeout)

        # Cache for monthly data (avoid re-fetching same month)
        self._monthly_cache: dict[str, RENElectricityPrice] = {}

    async def fetch_daily_prices(
        self,
        start_date: date,
        end_date: date,
    ) -> list[RENElectricityPrice]:
        """Fetch daily electricity prices for date range.

        Fetches hourly prices from REN and calculates daily averages.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of daily average electricity price records

        Raises:
            ExternalDataFetchError: If fetch fails
        """
        logger.info(
            "Fetching REN electricity prices",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        prices: list[RENElectricityPrice] = []
        current_date = start_date

        # Fetch day by day (REN API requires specific date)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while current_date <= end_date:
                try:
                    daily_price = await self._fetch_single_day(client, current_date)
                    if daily_price:
                        prices.append(daily_price)
                except ExternalDataFetchError as e:
                    # Log warning but continue with other days
                    logger.warning(
                        "Failed to fetch REN price for date",
                        extra={"date": str(current_date), "error": str(e)},
                    )

                current_date += timedelta(days=1)

                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)

        logger.info(
            "Fetched REN electricity prices",
            extra={"record_count": len(prices)},
        )

        return prices

    async def _fetch_single_day(
        self,
        client: httpx.AsyncClient,
        target_date: date,
    ) -> RENElectricityPrice | None:
        """Fetch hourly prices for a single day and calculate daily average.

        Args:
            client: httpx async client
            target_date: Date to fetch

        Returns:
            Daily average price or None if not available
        """
        params = {
            "culture": "en-US",
            "date": target_date.strftime("%Y-%m-%d"),
        }

        response = await self._fetch_with_retry(client, DAILY_PRICES_URL, params)

        if not response:
            return None

        # Parse response: series[0].data contains hourly prices
        try:
            series = response.get("series", [])
            if not series or not series[0].get("data"):
                logger.debug(
                    "No price data in REN response",
                    extra={"date": str(target_date)},
                )
                return None

            hourly_prices = series[0]["data"]

            # Filter out None/null values
            valid_prices = [p for p in hourly_prices if p is not None]
            if not valid_prices:
                return None

            # Calculate daily average
            daily_avg = sum(valid_prices) / len(valid_prices)

            return RENElectricityPrice(
                date=target_date,
                hour=None,  # Daily average, not specific hour
                price_eur_mwh=round(daily_avg, 2),
                price_type="daily_avg",
            )

        except (KeyError, IndexError, TypeError) as e:
            logger.warning(
                "Failed to parse REN daily response",
                extra={"date": str(target_date), "error": str(e)},
            )
            return None

    async def fetch_monthly_average(
        self,
        year: int,
        month: int,
    ) -> RENElectricityPrice | None:
        """Fetch monthly average electricity price.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Monthly average price or None if not available
        """
        cache_key = f"{year}-{month:02d}"

        # Check cache first
        if cache_key in self._monthly_cache:
            return self._monthly_cache[cache_key]

        logger.debug(
            "Fetching REN monthly price",
            extra={"year": year, "month": month},
        )

        params = {
            "culture": "en-US",
            "year": str(year),
            "month": f"{month:02d}",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await self._fetch_with_retry(client, MONTHLY_PRICES_URL, params)

        if not response:
            return None

        # Parse response: {month_name: {PT: {Average Price: X}}}
        try:
            month_name = calendar.month_name[month]

            if month_name not in response:
                logger.debug(
                    "Month not in REN response",
                    extra={"year": year, "month": month},
                )
                return None

            month_data = response[month_name]
            pt_data = month_data.get("PT", {})
            avg_price = pt_data.get("Average Price")

            if avg_price is None:
                return None

            price = RENElectricityPrice(
                date=date(year, month, 1),
                hour=None,
                price_eur_mwh=float(avg_price),
                price_type="monthly_avg",
            )

            # Cache the result
            self._monthly_cache[cache_key] = price

            return price

        except (KeyError, TypeError, ValueError) as e:
            logger.warning(
                "Failed to parse REN monthly response",
                extra={"year": year, "month": month, "error": str(e)},
            )
            return None

    async def fetch_monthly_prices_range(
        self,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
    ) -> list[RENElectricityPrice]:
        """Fetch monthly average prices for a date range.

        More efficient than daily fetches for long date ranges.

        Args:
            start_year: Start year
            start_month: Start month (1-12)
            end_year: End year
            end_month: End month (1-12)

        Returns:
            List of monthly average electricity price records
        """
        logger.info(
            "Fetching REN monthly prices range",
            extra={
                "start": f"{start_year}-{start_month:02d}",
                "end": f"{end_year}-{end_month:02d}",
            },
        )

        prices: list[RENElectricityPrice] = []
        year, month = start_year, start_month

        while (year, month) <= (end_year, end_month):
            price = await self.fetch_monthly_average(year, month)
            if price:
                prices.append(price)

            # Move to next month
            month += 1
            if month > 12:
                month = 1
                year += 1

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.05)

        logger.info(
            "Fetched REN monthly prices",
            extra={"record_count": len(prices)},
        )

        return prices

    async def _fetch_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict,
    ) -> dict | None:
        """Fetch URL with exponential backoff retry logic.

        Args:
            client: httpx async client
            url: API URL
            params: Query parameters

        Returns:
            JSON response dict or None if failed

        Raises:
            ExternalDataFetchError: After all retries exhausted
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [1, 2, 4]

        for attempt in range(max_retries):
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return cast(dict[str, Any], response.json())

            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                    logger.warning(
                        "REN API timeout, retrying",
                        extra={"attempt": attempt + 1, "delay": delay},
                    )
                    await asyncio.sleep(delay)
                    continue
                raise ExternalDataFetchError(
                    source="REN",
                    message=f"API timeout after {max_retries} attempts",
                ) from None

            except httpx.HTTPStatusError as e:
                # Retry on server errors (5xx) or rate limit (429)
                should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                if attempt < max_retries - 1 and should_retry:
                    delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                    logger.warning(
                        "REN API error, retrying",
                        extra={
                            "status": e.response.status_code,
                            "attempt": attempt + 1,
                            "delay": delay,
                        },
                    )
                    await asyncio.sleep(delay)
                    continue

                # 400/404 or other client errors - return None (no data for this date)
                # 400 can occur for dates before REN's data coverage starts
                if e.response.status_code in (400, 404):
                    logger.debug(
                        "REN API returned no data",
                        extra={"status": e.response.status_code, "url": url},
                    )
                    return None

                raise ExternalDataFetchError(
                    source="REN",
                    message=f"HTTP error: {e.response.status_code}",
                ) from e

            except Exception as e:
                raise ExternalDataFetchError(
                    source="REN",
                    message=f"Failed to fetch: {e}",
                ) from e

        return None

    def clear_cache(self) -> None:
        """Clear cached monthly data.

        Useful for forcing a fresh download of the latest data.
        """
        self._monthly_cache.clear()
        logger.info("Cleared REN monthly cache")
