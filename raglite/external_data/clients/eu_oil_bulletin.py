"""EU Oil Bulletin client.

Story 6.1: Tier 1 External Data Source Integration

Fetches EU fuel prices:
- Diesel prices (weekly, by country)
- Gasoline prices

Data Source: https://ec.europa.eu/energy/observatory/reports/
"""

from __future__ import annotations

import asyncio
import os
import xml.etree.ElementTree as ET  # nosec B405 - XML from trusted EU gov source
from datetime import date

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import EUDieselPrice
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# EU Oil Bulletin API
EU_OIL_BULLETIN_BASE = "https://ec.europa.eu/energy/observatory/reports"


class EUOilBulletinClient:
    """Client for EU Oil Bulletin fuel prices.

    The EU Oil Bulletin provides weekly fuel prices for all EU member states.

    Example:
        >>> client = EUOilBulletinClient()
        >>> prices = await client.fetch_diesel_prices(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 3, 31),
        ...     country="Portugal"
        ... )
    """

    # Country codes for EU Oil Bulletin
    COUNTRY_CODES = {
        "Portugal": "PT",
        "Spain": "ES",
        "France": "FR",
        "Germany": "DE",
        "Italy": "IT",
        "Netherlands": "NL",
        "Belgium": "BE",
    }

    def __init__(self) -> None:
        self.base_url = EU_OIL_BULLETIN_BASE
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 1.0 if is_test else float(settings.external_data_timeout)

    async def _fetch_bulletin_data(
        self,
        year: int,
    ) -> str:
        """Fetch annual oil bulletin data.

        Args:
            year: Year to fetch

        Returns:
            CSV/XML content

        Raises:
            ExternalDataFetchError: If fetch fails
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [1, 2, 4]

        # EU Oil Bulletin publishes weekly data in annual files
        url = f"{self.base_url}/Oil_Bulletin_Prices_History.xml"

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
                            "EU Oil Bulletin timeout, retrying",
                            extra={"attempt": attempt + 1, "delay": delay},
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="EU_Oil_Bulletin",
                            message="Timeout fetching bulletin data",
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
                            source="EU_Oil_Bulletin",
                            message=f"HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        return ""

    async def fetch_diesel_prices(
        self,
        start_date: date,
        end_date: date,
        country: str = "Portugal",
    ) -> list[EUDieselPrice]:
        """Fetch diesel prices for a country.

        Args:
            start_date: Start of date range
            end_date: End of date range
            country: Country name (default: Portugal)

        Returns:
            List of diesel price records
        """
        logger.info(
            "Fetching EU Oil Bulletin diesel prices",
            extra={
                "start": str(start_date),
                "end": str(end_date),
                "country": country,
            },
        )

        country_code = self.COUNTRY_CODES.get(country, "PT")

        # Fetch data for relevant years
        results = []
        years = set(range(start_date.year, end_date.year + 1))

        for year in years:
            try:
                content = await self._fetch_bulletin_data(year)
                if content:
                    year_prices = self._parse_bulletin_xml(
                        content, country_code, start_date, end_date
                    )
                    results.extend(year_prices)
            except ExternalDataFetchError as e:
                logger.warning(
                    "Failed to fetch EU Oil Bulletin data",
                    extra={"year": year, "error": str(e)},
                )

        logger.info(
            "Fetched EU Oil Bulletin diesel prices",
            extra={"record_count": len(results), "country": country},
        )
        return results

    def _parse_bulletin_xml(
        self,
        content: str,
        country_code: str,
        start_date: date,
        end_date: date,
    ) -> list[EUDieselPrice]:
        """Parse EU Oil Bulletin XML data.

        Args:
            content: XML content
            country_code: ISO country code
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            List of diesel price records
        """
        results: list[EUDieselPrice] = []

        try:
            root = ET.fromstring(content)  # nosec B314 - XML from trusted EU gov source
        except ET.ParseError as e:
            logger.warning(
                "Failed to parse EU Oil Bulletin XML",
                extra={"error": str(e)},
            )
            return results

        # Find all OilPrice elements (handles any nesting level)
        for elem in root.iter("OilPrice"):
            date_str = elem.get("date")
            country = elem.get("country")
            price_str = elem.get("diesel")

            if not all([date_str, country, price_str]):
                continue

            if country != country_code:
                continue

            try:
                if date_str is None:
                    continue
                record_date = date.fromisoformat(date_str)
                if not (start_date <= record_date <= end_date):
                    continue

                if price_str is None:
                    continue
                price = float(price_str)
                results.append(
                    EUDieselPrice(
                        date=record_date,
                        price_eur_litre=price,
                        country=self._code_to_country(country_code),
                        tax_included=True,
                    )
                )
            except ValueError as e:
                logger.warning(
                    "Failed to parse EU Oil Bulletin record",
                    extra={"date": date_str, "error": str(e)},
                )
                continue

        return results

    def _code_to_country(self, code: str) -> str:
        """Convert country code to name."""
        for name, c in self.COUNTRY_CODES.items():
            if c == code:
                return name
        return code

    async def fetch_weekly_prices(
        self,
        week_date: date,
        country: str = "Portugal",
    ) -> EUDieselPrice | None:
        """Fetch diesel price for a specific week.

        Args:
            week_date: Any date within the target week
            country: Country name

        Returns:
            Diesel price for that week or None
        """
        # EU Oil Bulletin publishes on Mondays
        # Find the Monday of the week containing week_date
        days_since_monday = week_date.weekday()
        monday = week_date.replace(day=week_date.day - days_since_monday)

        prices = await self.fetch_diesel_prices(
            start_date=monday,
            end_date=monday,
            country=country,
        )

        return prices[0] if prices else None
