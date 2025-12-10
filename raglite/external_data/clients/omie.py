"""OMIE (Operador del Mercado Ibérico de Energía) client.

Story 6.1: Tier 1 External Data Source Integration
Story 6.9.2: OMIE Electricity Market Fix (AC1-AC6)

Fetches Iberian electricity market prices:
- Daily spot prices (MIBEL)
- Hourly prices

Data Source: https://www.omie.es/es/file-download

Story 6.9.2 Changes:
- AC1: Updated URL pattern to use file-download endpoint (old /dados/ path returns 404)
- AC2: Enabled follow_redirects=True (OMIE returns 302 redirect)
- AC3: Updated CSV parser for new format (MARGINALPDBC;YEAR;MONTH;DAY;HOUR;PT;ES)
- AC6: Implemented retry logic per NFR1 (exponential backoff 2s/4s/8s)
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
# Story 6.9.2 AC1: Updated from /sites/default/files/dados/ to /es/file-download
# Story 6.9.6: Added historical archive fallback for dates older than 90 days
#
# Recent data (last ~90 days):
#   https://www.omie.es/es/file-download?parents=marginalpdbc&filename={filename}
# Historical archive (older dates):
#   https://www.omie.es/sites/default/files/dados/AGNO_{year}/MES_{month}/TXT/{filename}
OMIE_BASE_URL = "https://www.omie.es/es/file-download"
OMIE_ARCHIVE_URL = "https://www.omie.es/sites/default/files/dados"


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
        # Story 6.10.2 AC2: Increased test timeout from 1s to 10s for slow APIs
        # Production timeout unchanged (uses external_data_timeout from settings)
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 10.0 if is_test else float(settings.external_data_timeout)

    async def _fetch_daily_file(
        self,
        target_date: date,
    ) -> str:
        """Fetch daily price file from OMIE.

        OMIE publishes daily CSV files with hourly prices.

        Story 6.9.2:
        - AC1: Use file-download endpoint with query params
        - AC2: Enable follow_redirects=True (OMIE returns 302)
        - AC6: Exponential backoff per NFR1 (2s/4s/8s)

        Story 6.9.6:
        - Added historical archive fallback for dates older than 90 days
        - file-download endpoint returns 404 for old dates
        - Historical archive has data from 2000+

        Args:
            target_date: Date to fetch prices for

        Returns:
            CSV file content

        Raises:
            ExternalDataFetchError: If fetch fails
        """
        # OMIE file naming convention: marginalpdbc_YYYYMMDD.1
        filename = f"marginalpdbc_{target_date.strftime('%Y%m%d')}.1"

        # Story 6.9.6: Try both URLs - recent endpoint first, then historical archive
        urls_to_try = [
            # Recent data (file-download endpoint)
            f"{self.base_url}?parents=marginalpdbc&filename={filename}",
            # Historical archive (direct file URL)
            f"{OMIE_ARCHIVE_URL}/AGNO_{target_date.year}/MES_{target_date.month:02d}/TXT/{filename}",
        ]

        # Story 6.9.2 AC6: Exponential backoff per NFR1 (2s/4s/8s)
        max_retries = settings.external_data_retry_attempts
        retry_delays = [2, 4, 8]

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for url in urls_to_try:
                for attempt in range(max_retries):
                    try:
                        response = await client.get(url)
                        response.raise_for_status()

                        # Verify we got actual data (not HTML error page)
                        content = response.text
                        if "MARGINALPDBC" in content or "Precio marginal" in content:
                            return content
                        # Not valid OMIE data, try next URL
                        break

                    except httpx.TimeoutException:
                        if attempt < max_retries - 1:
                            delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                            await asyncio.sleep(delay)
                            continue
                        break  # Try next URL after max retries

                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 404:
                            break  # Try next URL
                        # Retry on server errors (5xx) or rate limit (429)
                        should_retry = (
                            e.response.status_code >= 500 or e.response.status_code == 429
                        )
                        if attempt < max_retries - 1 and should_retry:
                            delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                            await asyncio.sleep(delay)
                            continue
                        break  # Try next URL after max retries or non-retryable error

        # If both URLs failed, log and return empty
        # Story 6.10.2 AC4: Changed from INFO to WARNING for better visibility
        logger.warning(
            "OMIE data not available for date",
            extra={"date": str(target_date)},
        )
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

        Story 6.9.2 AC3: Updated parser for new CSV format.
        Story 6.10.3: Fixed parser to handle both old and new OMIE formats.

        Supported formats (semicolon-separated):

        Format A (Legacy - pre-Dec 2024):
        MARGINALPDBC;YEAR;MONTH;DAY;HOUR;PT_PRICE;ES_PRICE;...

        Format B (Current - Dec 2024+):
        - Header line: MARGINALPDBC;
        - Data lines: YEAR;MONTH;DAY;HOUR;PT_PRICE;ES_PRICE;

        Note: Hour is 1-based (1-24), prices may use comma or period as decimal.

        Args:
            content: CSV file content
            target_date: Date of the file

        Returns:
            List of hourly price records
        """
        results = []
        lines = content.strip().split("\n")

        for line in lines:
            # Strip carriage returns for Windows line endings
            line = line.strip()
            parts = line.split(";")

            # Skip header-only lines (e.g., "MARGINALPDBC;") or invalid lines
            if len(parts) < 6:
                continue

            # Determine format and extract indices
            # Format A: MARGINALPDBC;YEAR;MONTH;DAY;HOUR;PT_PRICE;ES_PRICE;...
            # Format B: YEAR;MONTH;DAY;HOUR;PT_PRICE;ES_PRICE;
            if parts[0] == "MARGINALPDBC":
                # Format A (legacy): MARGINALPDBC prefix
                if len(parts) < 7:
                    continue
                hour_idx, price_idx = 4, 5
            else:
                # Format B (current): starts with year
                # Check if first part is a year (4 digits)
                try:
                    year = int(parts[0])
                    if year < 2000 or year > 2100:
                        continue
                except ValueError:
                    # Not a valid data line
                    continue
                hour_idx, price_idx = 3, 4

            try:
                hour = int(parts[hour_idx]) - 1  # Convert 1-24 to 0-23
                # Handle both decimal formats (comma and period)
                price_str = parts[price_idx].replace(",", ".")
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
