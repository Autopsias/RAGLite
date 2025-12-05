"""OMIE (Operador del Mercado Ibérico de Energía) client.

Story 6.1: Tier 1 External Data Source Integration

Fetches Iberian electricity market prices:
- Daily spot prices (MIBEL)
- Hourly prices

Data Source: https://www.omie.es/sites/default/files/dados/
"""

from __future__ import annotations

import asyncio
import os
from datetime import date, timedelta

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import OMIEElectricityPrice
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# OMIE Data URLs
OMIE_BASE_URL = "https://www.omie.es/sites/default/files/dados"


class OMIEClient:
    """Client for OMIE electricity market data.

    OMIE operates the Iberian electricity market (MIBEL) covering
    Portugal and Spain.

    Example:
        >>> client = OMIEClient()
        >>> prices = await client.fetch_spot_prices(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 1, 31)
        ... )
    """

    def __init__(self) -> None:
        self.base_url = OMIE_BASE_URL
        self.api_key = settings.omie_api_key  # Usually not needed
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 1.0 if is_test else float(settings.external_data_timeout)

    async def _fetch_daily_file(
        self,
        target_date: date,
    ) -> str:
        """Fetch daily price file from OMIE.

        OMIE publishes daily CSV files with hourly prices.

        Args:
            target_date: Date to fetch prices for

        Returns:
            CSV file content

        Raises:
            ExternalDataFetchError: If fetch fails
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [1, 2, 4]

        # OMIE file naming convention: marginalpdbc_YYYYMMDD.1
        filename = f"marginalpdbc_{target_date.strftime('%Y%m%d')}.1"
        url = f"{self.base_url}/AGNO_{target_date.year}/MES_{target_date.month:02d}/TXT/{filename}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    return response.text

                except httpx.TimeoutException as e:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "OMIE fetch timeout, retrying",
                            extra={
                                "attempt": attempt + 1,
                                "delay": delay,
                                "date": str(target_date),
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="OMIE",
                            message=f"Timeout fetching {target_date}",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    # 404 is expected for future dates or missing data
                    if e.response.status_code == 404:
                        logger.info(
                            "OMIE data not available for date",
                            extra={"date": str(target_date)},
                        )
                        return ""

                    # Retry on server errors (5xx) or rate limit (429)
                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="OMIE",
                            message=f"HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        return ""

    async def fetch_spot_prices(
        self,
        start_date: date,
        end_date: date,
        include_hourly: bool = False,
    ) -> list[OMIEElectricityPrice]:
        """Fetch electricity spot prices for date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            include_hourly: If True, return hourly prices; if False, return daily average

        Returns:
            List of electricity price records
        """
        logger.info(
            "Fetching OMIE spot prices",
            extra={
                "start": str(start_date),
                "end": str(end_date),
                "hourly": include_hourly,
            },
        )

        results = []
        current_date = start_date

        while current_date <= end_date:
            try:
                content = await self._fetch_daily_file(current_date)
                if content:
                    daily_prices = self._parse_daily_file(content, current_date)
                    if include_hourly:
                        results.extend(daily_prices)
                    else:
                        # Calculate daily average
                        if daily_prices:
                            avg_price = sum(p.price_eur_mwh for p in daily_prices) / len(
                                daily_prices
                            )
                            results.append(
                                OMIEElectricityPrice(
                                    date=current_date,
                                    hour=None,
                                    price_eur_mwh=round(avg_price, 2),
                                    market="MIBEL",
                                    price_type="spot_daily_avg",
                                )
                            )
            except ExternalDataFetchError as e:
                logger.warning(
                    "Failed to fetch OMIE data for date",
                    extra={"date": str(current_date), "error": str(e)},
                )

            current_date += timedelta(days=1)

        logger.info(
            "Fetched OMIE spot prices",
            extra={"record_count": len(results)},
        )
        return results

    def _parse_daily_file(
        self,
        content: str,
        target_date: date,
    ) -> list[OMIEElectricityPrice]:
        """Parse OMIE daily price file.

        OMIE CSV format (semicolon-separated):
        Hour;Portugal;Spain
        1;XX.XX;YY.YY
        ...

        Args:
            content: CSV file content
            target_date: Date of the file

        Returns:
            List of hourly price records
        """
        results = []
        lines = content.strip().split("\n")

        for line in lines[1:]:  # Skip header
            try:
                parts = line.split(";")
                if len(parts) >= 2:
                    hour = int(parts[0]) - 1  # OMIE uses 1-24, we use 0-23
                    # Portugal price is usually in column 2 (index 1)
                    price_str = parts[1].replace(",", ".")
                    price = float(price_str)

                    results.append(
                        OMIEElectricityPrice(
                            date=target_date,
                            hour=hour,
                            price_eur_mwh=price,
                            market="MIBEL",
                            price_type="spot",
                        )
                    )
            except (ValueError, IndexError) as e:
                logger.warning(
                    "Failed to parse OMIE line",
                    extra={"line": line[:50], "error": str(e)},
                )
                continue

        return results

    async def fetch_monthly_average(
        self,
        year: int,
        month: int,
    ) -> OMIEElectricityPrice | None:
        """Fetch monthly average electricity price.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Monthly average price or None if not available
        """
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)

        daily_prices = await self.fetch_spot_prices(start, end, include_hourly=False)

        if not daily_prices:
            return None

        avg_price = sum(p.price_eur_mwh for p in daily_prices) / len(daily_prices)

        return OMIEElectricityPrice(
            date=start,
            hour=None,
            price_eur_mwh=round(avg_price, 2),
            market="MIBEL",
            price_type="monthly_avg",
        )
