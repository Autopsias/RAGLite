"""ECB (European Central Bank) Statistical Data Warehouse client.

Story 6.9.6: Add EURIBOR data for multivariate forecasting

Fetches European financial indicators:
- EURIBOR interest rates (3M, 6M, 12M) - monthly averages
- Key for cement industry: EURIBOR affects construction financing costs

Data Source: https://data-api.ecb.europa.eu/
API Documentation: https://data.ecb.europa.eu/help/api/overview
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import date
from io import StringIO

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# ECB SDMX API Configuration
ECB_API_BASE = "https://data-api.ecb.europa.eu/service/data"


@dataclass
class EuriborRate:
    """EURIBOR interest rate data point."""

    date: date
    rate_pct: float  # Interest rate as percentage (e.g., -0.5 or 3.5)
    tenor: str  # "3M", "6M", or "12M"


class ECBClient:
    """Client for ECB Statistical Data Warehouse.

    Provides access to EURIBOR interest rates for multivariate forecasting.

    EURIBOR (Euro Interbank Offered Rate) is relevant for cement industry because:
    - It directly affects mortgage rates → housing construction demand
    - It influences business investment decisions → infrastructure projects
    - It's a leading indicator of economic conditions

    Example:
        >>> client = ECBClient()
        >>> rates = await client.fetch_euribor(
        ...     start_date=date(2020, 1, 1),
        ...     end_date=date(2024, 12, 31),
        ...     tenor="3M"
        ... )
    """

    # ECB SDMX series keys for EURIBOR
    # Format: FM.M.U2.EUR.RT.MM.EURIBOR{tenor}D_.HSTA
    # HSTA = Historical close, average of observations through period
    EURIBOR_SERIES = {
        "3M": "M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA",
        "6M": "M.U2.EUR.RT.MM.EURIBOR6MD_.HSTA",
        "12M": "M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA",
    }

    def __init__(self) -> None:
        self.base_url = ECB_API_BASE
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 1.0 if is_test else float(settings.external_data_timeout)

    async def fetch_euribor(
        self,
        start_date: date,
        end_date: date,
        tenor: str = "3M",
    ) -> list[EuriborRate]:
        """Fetch EURIBOR interest rates for date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            tenor: EURIBOR tenor - "3M", "6M", or "12M" (default: "3M")

        Returns:
            List of EURIBOR rate records (monthly averages)
        """
        if tenor not in self.EURIBOR_SERIES:
            raise ValueError(
                f"Invalid tenor: {tenor}. Must be one of: {list(self.EURIBOR_SERIES.keys())}"
            )

        logger.info(
            "Fetching ECB EURIBOR rates",
            extra={
                "start": str(start_date),
                "end": str(end_date),
                "tenor": tenor,
            },
        )

        series_key = self.EURIBOR_SERIES[tenor]
        csv_data = await self._fetch_series(series_key, start_date, end_date)

        return self._parse_euribor_csv(csv_data, tenor)

    async def _fetch_series(
        self,
        series_key: str,
        start_date: date,
        end_date: date,
    ) -> str:
        """Fetch data series from ECB SDMX API.

        Args:
            series_key: ECB SDMX series key
            start_date: Start of date range
            end_date: End of date range

        Returns:
            CSV data as string

        Raises:
            ExternalDataFetchError: If fetch fails
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [2, 4, 8]

        # ECB SDMX API URL
        url = f"{self.base_url}/FM/{series_key}"
        params = {
            "startPeriod": start_date.strftime("%Y-%m"),
            "endPeriod": end_date.strftime("%Y-%m"),
            "format": "csvdata",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    return response.text

                except httpx.TimeoutException as e:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "ECB API timeout, retrying",
                            extra={"attempt": attempt + 1, "delay": delay},
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="ECB",
                            message=f"Timeout after {max_retries} attempts",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "ECB API error, retrying",
                            extra={"attempt": attempt + 1, "status": e.response.status_code},
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="ECB",
                            message=f"HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        raise ExternalDataFetchError(source="ECB", message="Unexpected retry loop exit")

    def _parse_euribor_csv(self, csv_data: str, tenor: str) -> list[EuriborRate]:
        """Parse ECB SDMX CSV response for EURIBOR data.

        Args:
            csv_data: CSV string from ECB API
            tenor: EURIBOR tenor

        Returns:
            List of EURIBOR rate records
        """
        import csv

        results: list[EuriborRate] = []

        reader = csv.DictReader(StringIO(csv_data))

        for row in reader:
            try:
                # TIME_PERIOD format: "2020-01"
                period = row.get("TIME_PERIOD", "")
                if not period or len(period) < 7:
                    continue

                year, month = int(period[:4]), int(period[5:7])
                record_date = date(year, month, 1)

                # OBS_VALUE is the interest rate (can be negative)
                rate_str = row.get("OBS_VALUE", "")
                if not rate_str:
                    continue

                rate = float(rate_str)

                results.append(
                    EuriborRate(
                        date=record_date,
                        rate_pct=rate,
                        tenor=tenor,
                    )
                )

            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse ECB row",
                    extra={"row": str(row)[:100], "error": str(e)},
                )
                continue

        logger.info(
            "Parsed ECB EURIBOR rates",
            extra={"record_count": len(results), "tenor": tenor},
        )

        return results

    async def fetch_all_tenors(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, list[EuriborRate]]:
        """Fetch all EURIBOR tenors (3M, 6M, 12M).

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dict mapping tenor to list of rates
        """
        results = {}
        for tenor in self.EURIBOR_SERIES:
            try:
                rates = await self.fetch_euribor(start_date, end_date, tenor)
                results[tenor] = rates
            except ExternalDataFetchError as e:
                logger.warning(f"Failed to fetch EURIBOR {tenor}: {e}")

        return results
