"""Eurostat API client for EU statistics.

Story 6.8: Tier 2 Data Sources & ML Enhancements (Conditional)

Fetches EU-wide economic and energy data:
- Electricity prices for industrial consumers (nrg_pc_204)

API Documentation: https://ec.europa.eu/eurostat/web/json-and-unicode-web-services
SDMX-JSON: https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/
"""

from __future__ import annotations

import asyncio
import os
from datetime import date

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import EurostatElectricityPrice
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Eurostat API Configuration
EUROSTAT_API_BASE = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1"


class EurostatClient:
    """Client for Eurostat EU statistics API.

    Provides access to EU-wide economic and energy data.

    Story 6.8 AC1.3: Eurostat electricity prices for industrial consumers

    Example:
        >>> client = EurostatClient()
        >>> prices = await client.fetch_electricity_prices(
        ...     country="PT",
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 3, 31)
        ... )
    """

    # Dataset codes
    ELECTRICITY_DATASET = "nrg_pc_204"  # Electricity prices for industry

    # Consumption bands for industrial consumers
    # https://ec.europa.eu/eurostat/statistics-explained/index.php/Glossary:Electricity_consumption_bands
    CONSUMPTION_BANDS = {
        "IA": "< 20 MWh",
        "IB": "20-500 MWh",
        "IC": "500-2000 MWh",  # Default
        "ID": "2000-20000 MWh",
        "IE": "20000-70000 MWh",
        "IF": "70000-150000 MWh",
        "IG": "> 150000 MWh",
    }

    def __init__(self) -> None:
        """Initialize Eurostat client."""
        self.base_url = EUROSTAT_API_BASE

        # Use test timeout in test environment
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 1.0 if is_test else float(settings.external_data_timeout)

    async def _fetch_with_retry(self, url: str, params: dict | None = None) -> dict:
        """Fetch data from Eurostat API with retry logic.

        Args:
            url: API URL
            params: Query parameters

        Returns:
            JSON response

        Raises:
            ExternalDataFetchError: If all retries fail
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [2, 4, 8]  # NFR1: exponential backoff

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
                            "Eurostat API timeout, retrying",
                            extra={"attempt": attempt + 1, "delay": delay},
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="Eurostat",
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
                            source="Eurostat",
                            message=f"HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        raise ExternalDataFetchError(source="Eurostat", message="Unexpected retry loop exit")

    async def _fetch_eurostat_data(
        self,
        dataset: str,
        filters: dict[str, str],
    ) -> dict:
        """Fetch data from Eurostat SDMX API.

        Args:
            dataset: Dataset code (e.g., "nrg_pc_204")
            filters: Filter parameters (geo, consband, unit, etc.)

        Returns:
            JSON-stat response
        """
        # Build filter string for SDMX query
        filter_parts = []
        for key, value in filters.items():
            filter_parts.append(f"{key}={value}")

        filter_str = "&".join(filter_parts) if filter_parts else ""

        url = f"{self.base_url}/data/{dataset}"
        if filter_str:
            url = f"{url}?{filter_str}"

        params = {
            "format": "JSON",
            "lang": "EN",
        }

        logger.info(
            "Fetching Eurostat data",
            extra={"dataset": dataset, "filters": filters},
        )

        return await self._fetch_with_retry(url, params)

    async def fetch_electricity_prices(
        self,
        country: str = "PT",
        start_date: date | None = None,
        end_date: date | None = None,
        consumption_band: str = "IC",  # 500-2000 MWh/year (medium industrial)
        include_taxes: bool = False,
    ) -> list[EurostatElectricityPrice]:
        """Fetch monthly electricity prices from Eurostat.

        Story 6.8 AC1.3: Industrial electricity prices

        Dataset: nrg_pc_204 (electricity prices for industrial consumers)
        Coverage: 2008-present, semi-annual (S1/S2) or annual

        Complements OMIE with longer historical data for Portugal.

        Args:
            country: ISO 2-letter country code (default: PT for Portugal)
            start_date: Start of date range
            end_date: End of date range
            consumption_band: Consumption band code (default: IC = 500-2000 MWh/year)
            include_taxes: Whether to include taxes in price (default: False)

        Returns:
            List of electricity price records
        """
        logger.info(
            "Fetching Eurostat electricity prices",
            extra={
                "country": country,
                "start": str(start_date) if start_date else "all",
                "end": str(end_date) if end_date else "all",
            },
        )

        # Tax component filter
        tax_component = "I_TAX" if include_taxes else "X_TAX"

        filters = {
            "geo": country,
            "consom": consumption_band,
            "tax": tax_component,
            "unit": "KWH",  # EUR per kWh
            "currency": "EUR",
        }

        data = await self._fetch_eurostat_data(self.ELECTRICITY_DATASET, filters)
        return self._parse_electricity_data(
            data, country, consumption_band, tax_component, start_date, end_date
        )

    def _parse_electricity_data(
        self,
        data: dict,
        country: str,
        consumption_band: str,
        tax_component: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[EurostatElectricityPrice]:
        """Parse Eurostat electricity price response.

        Args:
            data: JSON response from Eurostat
            country: Country code
            consumption_band: Consumption band code
            tax_component: Tax component (I_TAX or X_TAX)
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            List of electricity price records
        """
        results: list[EurostatElectricityPrice] = []

        # Get values and time dimension
        values = data.get("value", {})
        dimensions = data.get("dimension", {})
        time_dim = dimensions.get("time", {}).get("category", {}).get("index", {})

        # Build index to period mapping
        period_by_index = {v: k for k, v in time_dim.items()}

        for idx_str, price in values.items():
            try:
                idx = int(idx_str)
                period = period_by_index.get(idx)

                if not period or price is None:
                    continue

                # Parse period (YYYY-MM or YYYY-S1/S2)
                record_date = self._parse_eurostat_period(period)
                if record_date is None:
                    continue

                # Apply date filters
                if start_date and record_date < start_date.replace(day=1):
                    continue
                if end_date and record_date > end_date:
                    continue

                results.append(
                    EurostatElectricityPrice(
                        date=record_date,
                        price_eur_kwh=float(price),
                        country=country,
                        consumption_band=consumption_band,
                        tax_component=tax_component,
                    )
                )

            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse Eurostat electricity record",
                    extra={"index": idx_str, "error": str(e)},
                )
                continue

        # Sort by date
        results.sort(key=lambda x: x.date)

        logger.info(
            "Parsed Eurostat electricity prices",
            extra={"count": len(results)},
        )
        return results

    def _parse_eurostat_period(self, period: str) -> date | None:
        """Parse Eurostat period string to date.

        Handles multiple formats:
        - "2024-01" (monthly)
        - "2024-S1" (first semester)
        - "2024-S2" (second semester)
        - "2024" (annual)

        Args:
            period: Period string from Eurostat

        Returns:
            date object or None if parsing fails
        """
        try:
            # Monthly format: YYYY-MM
            if "-" in period and len(period) == 7 and period[5:].isdigit():
                year = int(period[:4])
                month = int(period[5:7])
                return date(year, month, 1)

            # Semester format: YYYY-S1 or YYYY-S2
            if "-S" in period:
                year = int(period[:4])
                semester = int(period[-1])
                month = 1 if semester == 1 else 7
                return date(year, month, 1)

            # Annual format: YYYY
            if len(period) == 4 and period.isdigit():
                return date(int(period), 1, 1)

        except ValueError:
            pass

        return None
