"""ECB (European Central Bank) Statistical Data Warehouse client.

Story 6.9.6: Add EURIBOR data for multivariate forecasting
Story 6.17: Add GDP growth and HICP inflation macroeconomic indicators

Fetches European financial indicators:
- EURIBOR interest rates (3M, 6M, 12M) - monthly averages
- GDP growth rate (quarterly YoY) - for construction demand forecasting
- HICP inflation (monthly) - for pricing and cost forecasting
- Key for cement industry: EURIBOR affects construction financing costs

Data Source: https://data-api.ecb.europa.eu/
API Documentation: https://data.ecb.europa.eu/help/api/overview
"""

from __future__ import annotations

import asyncio
import csv
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


@dataclass
class ECBGDPGrowth:
    """GDP growth rate data point.

    Story 6.17 AC1: GDP growth for forecasting construction demand.
    """

    date: date
    growth_pct: float  # YoY growth as percentage (e.g., 2.5 for 2.5%)
    country: str  # ISO 2-letter code (PT for Portugal)
    frequency: str = "Q"  # Q=Quarterly, M=Monthly (after interpolation)


@dataclass
class ECBInflation:
    """HICP inflation index data point.

    Story 6.17 AC2: HICP inflation for pricing and cost forecasting.
    """

    date: date
    index_value: float  # HICP index (2015=100)
    country: str  # ISO 2-letter code
    yoy_change_pct: float | None = None  # YoY % change (calculated)


class ECBClient:
    """Client for ECB Statistical Data Warehouse.

    Provides access to EURIBOR interest rates and macroeconomic indicators
    for multivariate forecasting.

    Story 6.17: Extended with GDP growth and HICP inflation.

    EURIBOR (Euro Interbank Offered Rate) is relevant for cement industry because:
    - It directly affects mortgage rates → housing construction demand
    - It influences business investment decisions → infrastructure projects
    - It's a leading indicator of economic conditions

    GDP Growth and HICP Inflation (Story 6.17):
    - GDP growth correlates with construction activity and demand
    - HICP inflation affects material costs and pricing strategies

    Example:
        >>> client = ECBClient()
        >>> rates = await client.fetch_euribor(
        ...     start_date=date(2020, 1, 1),
        ...     end_date=date(2024, 12, 31),
        ...     tenor="3M"
        ... )
        >>> gdp = await client.fetch_gdp_growth(
        ...     country="PT",
        ...     start_date=date(2020, 1, 1),
        ...     end_date=date(2024, 12, 31),
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

    # Story 6.17 AC1: GDP growth series key template
    # Story 6.24: Fixed series key to match ECB Data Portal format
    # Q.Y.{country}.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.GY
    # Q = Quarterly, Y = Year-on-year, B1GQ = GDP at market prices
    # EUR = Euro currency, LR = Chain linked volume, GY = Growth year-on-year
    # Working example: MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.GY
    GDP_SERIES_TEMPLATE = "Q.Y.{country}.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.GY"
    GDP_SERIES = GDP_SERIES_TEMPLATE  # Alias for backwards compatibility

    # Story 6.17 AC2: HICP series key template
    # M.{country}.N.000000.4.INX
    # M = Monthly, 000000 = All items, 4 = Index, INX = Index level
    HICP_SERIES_TEMPLATE = "M.{country}.N.000000.4.INX"
    HICP_SERIES = HICP_SERIES_TEMPLATE  # Alias for backwards compatibility

    def __init__(self) -> None:
        self.base_url = ECB_API_BASE
        # Story 6.10.2 AC3: Increased test timeout from 1s to 10s for slow APIs
        # Production timeout unchanged (uses external_data_timeout from settings)
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 10.0 if is_test else float(settings.external_data_timeout)
        # Story 6.10.3 AC3: Add file-based caching for external data
        from raglite.shared.caching import ExternalDataCache

        self._cache = ExternalDataCache(ttl_hours=24)

    async def fetch_euribor(
        self,
        start_date: date,
        end_date: date,
        tenor: str = "3M",
    ) -> list[EuriborRate]:
        """Fetch EURIBOR interest rates for date range.

        Story 6.10.3 AC3: Uses file-based caching to reduce API calls
        and handle transient failures gracefully.

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

        # Story 6.10.3 AC3: Try cache first
        cache_key = f"ecb_euribor_{tenor}_{start_date}_{end_date}"
        cached = self._cache.get(cache_key)
        if cached:
            logger.info(
                "ECB EURIBOR rates loaded from cache",
                extra={"start": str(start_date), "end": str(end_date), "tenor": tenor},
            )
            return [EuriborRate(**r) for r in cached]

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

        results = self._parse_euribor_csv(csv_data, tenor)

        # Story 6.10.3: Cache results for future use
        if results:
            self._cache.set(cache_key, [r.__dict__ for r in results])

        return results

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

    # =========================================================================
    # Story 6.17: GDP Growth and HICP Inflation Methods
    # =========================================================================

    def _parse_ecb_period(self, period: str) -> date:
        """Parse ECB period string to date.

        Story 6.17 AC4: Period parsing for quarterly and monthly formats.

        Handles:
        - Monthly: "2024-01" -> date(2024, 1, 1)
        - Quarterly: "2024-Q1" -> date(2024, 1, 1)

        Args:
            period: ECB period string (e.g., "2024-Q1" or "2024-03")

        Returns:
            First day of the period as date
        """
        if "-Q" in period:
            # Quarterly format: "2024-Q1", "2024-Q2", etc.
            year = int(period[:4])
            quarter = int(period[-1])
            month = (quarter - 1) * 3 + 1  # Q1=1, Q2=4, Q3=7, Q4=10
            return date(year, month, 1)
        else:
            # Monthly format: "2024-03"
            year, month = int(period[:4]), int(period[5:7])
            return date(year, month, 1)

    async def fetch_gdp_growth(
        self,
        country: str = "PT",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[ECBGDPGrowth]:
        """Fetch quarterly GDP growth rate from ECB SDW.

        Story 6.17 AC1: GDP growth for Portugal.

        Dataset: MNA (National accounts)
        Coverage: Quarterly, 1999-present

        Note: Results are cached for 24 hours (see ExternalDataCache).

        Args:
            country: ISO 2-letter country code (default: PT)
            start_date: Start of date range (optional filter)
            end_date: End of date range (optional filter)

        Returns:
            List of GDP growth rate records (quarterly frequency)

        Raises:
            ValueError: If end_date < start_date
        """
        # Story 6.17 Code Review #3: Input validation
        if start_date and end_date and end_date < start_date:
            raise ValueError(f"end_date ({end_date}) must be >= start_date ({start_date})")
        # Build cache key
        cache_key = f"ecb_gdp_growth_{country}_{start_date}_{end_date}"
        cached = self._cache.get(cache_key)
        if cached:
            logger.info(
                "ECB GDP growth loaded from cache",
                extra={"country": country, "start": str(start_date), "end": str(end_date)},
            )
            # Convert date strings back to date objects when loading from cache
            results = []
            for r in cached:
                if isinstance(r.get("date"), str):
                    r["date"] = date.fromisoformat(r["date"])
                results.append(ECBGDPGrowth(**r))
            return results

        logger.info(
            "Fetching ECB GDP growth",
            extra={"country": country, "start": str(start_date), "end": str(end_date)},
        )

        # Build series key for country
        series_key = self.GDP_SERIES_TEMPLATE.format(country=country)

        # Use MNA dataset for national accounts
        csv_data = await self._fetch_gdp_series(series_key, start_date, end_date)

        results = self._parse_gdp_csv(csv_data, country)

        # Story 6.17 Code Review #1: Filter results by date range
        if start_date:
            results = [r for r in results if r.date >= start_date]
        if end_date:
            results = [r for r in results if r.date <= end_date]

        # Cache results - convert date to ISO string for JSON serialization
        if results:
            cache_data = []
            for r in results:
                d = r.__dict__.copy()
                d["date"] = r.date.isoformat()
                cache_data.append(d)
            self._cache.set(cache_key, cache_data)

        return results

    async def _fetch_gdp_series(
        self,
        series_key: str,
        start_date: date | None,
        end_date: date | None,
    ) -> str:
        """Fetch GDP series from ECB SDMX API (MNA dataset).

        Args:
            series_key: ECB SDMX series key for GDP
            start_date: Start of date range
            end_date: End of date range

        Returns:
            CSV data as string
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [2, 4, 8]

        # ECB SDMX API URL for MNA dataset
        url = f"{self.base_url}/MNA/{series_key}"
        params = {"format": "csvdata"}

        if start_date:
            params["startPeriod"] = f"{start_date.year}-Q{(start_date.month - 1) // 3 + 1}"
        if end_date:
            params["endPeriod"] = f"{end_date.year}-Q{(end_date.month - 1) // 3 + 1}"

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
                            "ECB GDP API timeout, retrying",
                            extra={"attempt": attempt + 1, "delay": delay},
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="ECB",
                            message=f"GDP timeout after {max_retries} attempts",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    # Story 6.24: ECB GDP endpoint discontinued, fallback to Eurostat
                    if e.response.status_code == 404:
                        # Extract country from series_key (format: Q.Y.PT.W2...)
                        country = series_key.split(".")[2] if "." in series_key else "PT"
                        logger.warning(
                            "ECB GDP endpoint not found (404), falling back to Eurostat",
                            extra={"series_key": series_key, "country": country},
                        )
                        return await self._fetch_gdp_from_eurostat(start_date, end_date, country)

                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "ECB GDP API error, retrying",
                            extra={"attempt": attempt + 1, "status": e.response.status_code},
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="ECB",
                            message=f"GDP HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        raise ExternalDataFetchError(source="ECB", message="GDP unexpected retry loop exit")

    async def _fetch_gdp_from_eurostat(
        self,
        start_date: date | None,
        end_date: date | None,
        country: str = "PT",
    ) -> str:
        """Fetch GDP growth data from Eurostat API as fallback for ECB.

        Story 6.24: ECB discontinued GDP endpoint, use Eurostat replacement.

        Eurostat Dataset: namq_10_gdp (National accounts aggregates)
        Endpoint: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/namq_10_gdp

        Args:
            start_date: Start of date range
            end_date: End of date range
            country: ISO 2-letter country code (default: PT)

        Returns:
            CSV data in ECB-compatible format for _parse_gdp_csv()

        Raises:
            ExternalDataFetchError: If fetch fails
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [2, 4, 8]

        # Eurostat API URL for GDP data
        # Note: namq_10_gdp does not have PC_CHG unit - fetch index and calculate growth
        # Eurostat API returns JSON by default (format=CSV causes HTTP 400)
        url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/namq_10_gdp"
        params = {
            "geo": country,
            "na_item": "B1GQ",  # GDP at market prices
            "unit": "CLV_I10",  # Chain-linked volumes, index 2010=100
            "s_adj": "SCA",  # Seasonally and calendar adjusted
        }

        # Add date range filters if provided
        if start_date:
            params["startPeriod"] = f"{start_date.year}-Q{(start_date.month - 1) // 3 + 1}"
        if end_date:
            params["endPeriod"] = f"{end_date.year}-Q{(end_date.month - 1) // 3 + 1}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()

                    # Parse JSON response and convert to ECB-compatible CSV format
                    eurostat_json = response.json()
                    return self._convert_eurostat_json_to_ecb_format(eurostat_json)

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
                            message=f"GDP timeout after {max_retries} attempts",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "Eurostat API error, retrying",
                            extra={"attempt": attempt + 1, "status": e.response.status_code},
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="Eurostat",
                            message=f"GDP HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        raise ExternalDataFetchError(source="Eurostat", message="GDP unexpected retry loop exit")

    def _convert_eurostat_json_to_ecb_format(self, eurostat_json: dict) -> str:
        """Convert Eurostat JSON GDP index to YoY growth rates in ECB CSV format.

        Story 6.24: Transform Eurostat JSON response to ECB growth rate format.

        Eurostat provides chain-linked volume index (2010=100), which we convert
        to year-on-year percentage change to match ECB's growth_pct format.

        Args:
            eurostat_json: JSON dict from Eurostat API (index values)

        Returns:
            CSV string in ECB-compatible format (YoY % growth)
        """
        from io import StringIO

        # Extract time period mapping and values from JSON
        try:
            time_index = (
                eurostat_json.get("dimension", {})
                .get("time", {})
                .get("category", {})
                .get("index", {})
            )
            values = eurostat_json.get("value", {})
        except (AttributeError, KeyError):
            logger.warning("Invalid Eurostat JSON structure")
            return "TIME_PERIOD,OBS_VALUE\n"

        if not time_index or not values:
            logger.warning("Empty Eurostat GDP response")
            return "TIME_PERIOD,OBS_VALUE\n"

        # Build index lookup: {quarter: index_value}
        # time_index: {"2020-Q1": 0, "2020-Q2": 1, ...}
        # values: {"0": 103.054, "1": 87.549, ...}
        index_by_quarter: dict[str, float] = {}
        for quarter, idx in time_index.items():
            value = values.get(str(idx))
            if value is not None:
                try:
                    index_by_quarter[quarter] = float(value)
                except (ValueError, TypeError):
                    logger.warning(
                        "Invalid Eurostat index value",
                        extra={"time_period": quarter, "value": value},
                    )
                    continue

        # Calculate YoY percentage change
        ecb_rows = []
        sorted_quarters = sorted(index_by_quarter.keys())

        for quarter in sorted_quarters:
            # Parse year and quarter: "2024-Q1" -> year=2024, q=1
            try:
                year = int(quarter[:4])
                q = int(quarter[-1])
            except (ValueError, IndexError):
                continue

            # Calculate previous year same quarter: "2024-Q1" -> "2023-Q1"
            prev_year_quarter = f"{year - 1}-Q{q}"

            if prev_year_quarter in index_by_quarter:
                current_index = index_by_quarter[quarter]
                prev_index = index_by_quarter[prev_year_quarter]

                if prev_index > 0:
                    # YoY % change = ((current - previous) / previous) * 100
                    yoy_growth = ((current_index - prev_index) / prev_index) * 100
                    ecb_rows.append({"TIME_PERIOD": quarter, "OBS_VALUE": f"{yoy_growth:.2f}"})

        # Write ECB-compatible CSV
        output = StringIO()
        if ecb_rows:
            writer = csv.DictWriter(output, fieldnames=["TIME_PERIOD", "OBS_VALUE"])
            writer.writeheader()
            writer.writerows(ecb_rows)

        result = output.getvalue()

        logger.info(
            "Converted Eurostat GDP index to YoY growth",
            extra={
                "eurostat_index_points": len(index_by_quarter),
                "calculated_growth_points": len(ecb_rows),
            },
        )

        return result

    def _parse_gdp_csv(self, csv_data: str, country: str) -> list[ECBGDPGrowth]:
        """Parse ECB SDMX CSV response for GDP growth data.

        Story 6.17 AC4: Unit tests for GDP parsing.

        Args:
            csv_data: CSV string from ECB API
            country: Country code for the results

        Returns:
            List of GDP growth records
        """
        results: list[ECBGDPGrowth] = []

        reader = csv.DictReader(StringIO(csv_data))

        for row in reader:
            try:
                # TIME_PERIOD format: "2024-Q1"
                period = row.get("TIME_PERIOD", "")
                if not period:
                    continue

                record_date = self._parse_ecb_period(period)

                # OBS_VALUE is the YoY growth rate
                growth_str = row.get("OBS_VALUE", "")
                if not growth_str:
                    continue

                growth_pct = float(growth_str)

                results.append(
                    ECBGDPGrowth(
                        date=record_date,
                        growth_pct=growth_pct,
                        country=country,
                        frequency="Q",
                    )
                )

            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse ECB GDP row",
                    extra={"row": str(row)[:100], "error": str(e)},
                )
                continue

        logger.info(
            "Parsed ECB GDP growth rates",
            extra={"record_count": len(results), "country": country},
        )

        return results

    async def fetch_inflation(
        self,
        country: str = "PT",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[ECBInflation]:
        """Fetch monthly HICP inflation index from ECB SDW.

        Story 6.17 AC2: HICP inflation for Portugal.

        Dataset: ICP (HICP - Harmonised Index of Consumer Prices)
        Coverage: Monthly, 1996-present

        Note: Results are cached for 24 hours (see ExternalDataCache).

        Args:
            country: ISO 2-letter country code (default: PT)
            start_date: Start of date range (optional filter)
            end_date: End of date range (optional filter)

        Returns:
            List of HICP inflation index records (monthly frequency)

        Raises:
            ValueError: If end_date < start_date
        """
        # Story 6.17 Code Review #3: Input validation
        if start_date and end_date and end_date < start_date:
            raise ValueError(f"end_date ({end_date}) must be >= start_date ({start_date})")
        # Build cache key
        cache_key = f"ecb_hicp_{country}_{start_date}_{end_date}"
        cached = self._cache.get(cache_key)
        if cached:
            logger.info(
                "ECB HICP loaded from cache",
                extra={"country": country, "start": str(start_date), "end": str(end_date)},
            )
            # Convert date strings back to date objects when loading from cache
            results = []
            for r in cached:
                if isinstance(r.get("date"), str):
                    r["date"] = date.fromisoformat(r["date"])
                results.append(ECBInflation(**r))
            return results

        logger.info(
            "Fetching ECB HICP inflation",
            extra={"country": country, "start": str(start_date), "end": str(end_date)},
        )

        # Build series key for country
        series_key = self.HICP_SERIES_TEMPLATE.format(country=country)

        # Use ICP dataset for HICP
        csv_data = await self._fetch_hicp_series(series_key, start_date, end_date)

        results = self._parse_hicp_csv(csv_data, country)

        # Story 6.17 Code Review #1: Filter results by date range
        if start_date:
            results = [r for r in results if r.date >= start_date]
        if end_date:
            results = [r for r in results if r.date <= end_date]

        # Cache results - convert date to ISO string for JSON serialization
        if results:
            cache_data = []
            for r in results:
                d = r.__dict__.copy()
                d["date"] = r.date.isoformat()
                cache_data.append(d)
            self._cache.set(cache_key, cache_data)

        return results

    async def _fetch_hicp_series(
        self,
        series_key: str,
        start_date: date | None,
        end_date: date | None,
    ) -> str:
        """Fetch HICP series from ECB SDMX API (ICP dataset).

        Args:
            series_key: ECB SDMX series key for HICP
            start_date: Start of date range
            end_date: End of date range

        Returns:
            CSV data as string
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [2, 4, 8]

        # ECB SDMX API URL for ICP dataset
        url = f"{self.base_url}/ICP/{series_key}"
        params = {"format": "csvdata"}

        if start_date:
            params["startPeriod"] = start_date.strftime("%Y-%m")
        if end_date:
            params["endPeriod"] = end_date.strftime("%Y-%m")

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
                            "ECB HICP API timeout, retrying",
                            extra={"attempt": attempt + 1, "delay": delay},
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="ECB",
                            message=f"HICP timeout after {max_retries} attempts",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "ECB HICP API error, retrying",
                            extra={"attempt": attempt + 1, "status": e.response.status_code},
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="ECB",
                            message=f"HICP HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        raise ExternalDataFetchError(source="ECB", message="HICP unexpected retry loop exit")

    def _parse_hicp_csv(self, csv_data: str, country: str) -> list[ECBInflation]:
        """Parse ECB SDMX CSV response for HICP inflation data.

        Story 6.17 AC4: Unit tests for HICP parsing.

        Calculates YoY change when 12 months of historical data is available.

        Args:
            csv_data: CSV string from ECB API
            country: Country code for the results

        Returns:
            List of HICP inflation records
        """
        results: list[ECBInflation] = []
        index_by_month: dict[tuple[int, int], float] = {}

        reader = csv.DictReader(StringIO(csv_data))

        for row in reader:
            try:
                # TIME_PERIOD format: "2024-01"
                period = row.get("TIME_PERIOD", "")
                if not period:
                    continue

                record_date = self._parse_ecb_period(period)

                # OBS_VALUE is the HICP index value
                index_str = row.get("OBS_VALUE", "")
                if not index_str:
                    continue

                index_value = float(index_str)

                # Store for YoY calculation
                index_by_month[(record_date.year, record_date.month)] = index_value

                results.append(
                    ECBInflation(
                        date=record_date,
                        index_value=index_value,
                        country=country,
                        yoy_change_pct=None,  # Will calculate after collecting all data
                    )
                )

            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse ECB HICP row",
                    extra={"row": str(row)[:100], "error": str(e)},
                )
                continue

        # Calculate YoY change for each record
        for record in results:
            prior_year = record.date.year - 1
            prior_month = record.date.month
            prior_key = (prior_year, prior_month)

            if prior_key in index_by_month:
                prior_value = index_by_month[prior_key]
                if prior_value > 0:
                    yoy_change = ((record.index_value - prior_value) / prior_value) * 100
                    record.yoy_change_pct = round(yoy_change, 2)

        logger.info(
            "Parsed ECB HICP inflation",
            extra={"record_count": len(results), "country": country},
        )

        return results


def interpolate_quarterly_to_monthly(
    quarterly_data: list[ECBGDPGrowth],
    method: str = "constant",
) -> list[ECBGDPGrowth]:
    """Interpolate quarterly GDP data to monthly frequency.

    Story 6.17 AC3: Quarterly to monthly alignment for regressors.

    Args:
        quarterly_data: List of quarterly GDP records
        method: Interpolation method (default: "constant")
            - "constant": Each month gets quarter's value (implemented)
            - Other values: Currently not supported, raises NotImplementedError

    Returns:
        List of monthly GDP records

    Raises:
        NotImplementedError: If method is not "constant"

    Example:
        >>> quarterly = [
        ...     ECBGDPGrowth(date=date(2024, 1, 1), growth_pct=2.5, country="PT"),
        ...     ECBGDPGrowth(date=date(2024, 4, 1), growth_pct=2.8, country="PT"),
        ... ]
        >>> monthly = interpolate_quarterly_to_monthly(quarterly)
        >>> len(monthly)
        6
    """
    # Story 6.17 Code Review #2: Validate method parameter
    if method != "constant":
        raise NotImplementedError(
            f"Interpolation method '{method}' not implemented. Use 'constant'."
        )

    if not quarterly_data:
        return []

    monthly_data: list[ECBGDPGrowth] = []

    for quarter in quarterly_data:
        # Get the quarter start month (1, 4, 7, or 10)
        quarter_start_month = quarter.date.month

        # Generate 3 months for this quarter
        for month_offset in range(3):
            month = quarter_start_month + month_offset
            monthly_date = date(quarter.date.year, month, 1)

            monthly_data.append(
                ECBGDPGrowth(
                    date=monthly_date,
                    growth_pct=quarter.growth_pct,  # Constant interpolation
                    country=quarter.country,
                    frequency="M",  # Now monthly
                )
            )

    return monthly_data
