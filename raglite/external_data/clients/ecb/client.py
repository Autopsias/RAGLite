"""ECB (European Central Bank) Statistical Data Warehouse client.

Story 8.2 Task 5: ECB client refactoring

Fetches European financial indicators:
- EURIBOR interest rates (3M, 6M, 12M) - monthly averages
- GDP growth rate (quarterly YoY) - for construction demand forecasting
- HICP inflation (monthly) - for pricing and cost forecasting

Data Source: https://data-api.ecb.europa.eu/
API Documentation: https://data.ecb.europa.eu/help/api/overview
"""

from __future__ import annotations

import os
from datetime import date

from raglite.external_data.clients.base import BaseExternalClient
from raglite.external_data.clients.ecb.config import (
    EURIBOR_SERIES,
    GDP_SERIES_TEMPLATE,
    HICP_SERIES_TEMPLATE,
)
from raglite.external_data.clients.ecb.fetchers import (
    fetch_gdp_series,
    fetch_hicp_series,
    fetch_series,
)
from raglite.external_data.clients.ecb.models import ECBGDPGrowth, ECBInflation, EuriborRate
from raglite.external_data.clients.ecb.parsers import (
    parse_euribor_csv,
    parse_gdp_csv,
    parse_hicp_csv,
)
from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class ECBClient(BaseExternalClient):
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

    # Story 6.17: Expose series templates as class attributes for backward compatibility
    GDP_SERIES = GDP_SERIES_TEMPLATE
    GDP_SERIES_TEMPLATE = GDP_SERIES_TEMPLATE
    HICP_SERIES = HICP_SERIES_TEMPLATE
    HICP_SERIES_TEMPLATE = HICP_SERIES_TEMPLATE
    EURIBOR_SERIES = EURIBOR_SERIES

    def __init__(self) -> None:
        # Story 6.10.2 AC3: Increased test timeout from 1s to 10s for slow APIs
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        timeout = 10.0 if is_test else float(settings.external_data_timeout)
        super().__init__(timeout=timeout)
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
        if tenor not in EURIBOR_SERIES:
            raise ValueError(
                f"Invalid tenor: {tenor}. Must be one of: {list(EURIBOR_SERIES.keys())}"
            )

        # Try cache first
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

        series_key = EURIBOR_SERIES[tenor]
        csv_data = await fetch_series(series_key, start_date, end_date, self.timeout)

        results = parse_euribor_csv(csv_data, tenor)

        # Cache results for future use
        if results:
            self._cache.set(cache_key, [r.__dict__ for r in results])

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
        for tenor in EURIBOR_SERIES:
            try:
                rates = await self.fetch_euribor(start_date, end_date, tenor)
                results[tenor] = rates
            except ExternalDataFetchError as e:
                logger.warning(f"Failed to fetch EURIBOR {tenor}: {e}")

        return results

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
        # Input validation
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
        series_key = GDP_SERIES_TEMPLATE.format(country=country)

        # Use MNA dataset for national accounts
        csv_data = await fetch_gdp_series(series_key, start_date, end_date, self.timeout)

        results = parse_gdp_csv(csv_data, country)

        # Filter results by date range
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
        # Input validation
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
        series_key = HICP_SERIES_TEMPLATE.format(country=country)

        # Use ICP dataset for HICP
        csv_data = await fetch_hicp_series(series_key, start_date, end_date, self.timeout)

        results = parse_hicp_csv(csv_data, country)

        # Filter results by date range
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

    # Story 8.2 Backward Compatibility Wrappers
    # These methods delegate to standalone functions for test compatibility

    def _parse_hicp_csv(self, csv_data: str, country: str = "PT") -> list[ECBInflation]:
        """Backward compatibility wrapper for parse_hicp_csv.

        Story 8.2: Tests expect this as a method. Delegates to standalone function.
        """
        return parse_hicp_csv(csv_data, country)

    def _parse_gdp_csv(self, csv_data: str, country: str) -> list[ECBGDPGrowth]:
        """Backward compatibility wrapper for parse_gdp_csv.

        Story 8.2: Tests expect this as a method. Delegates to standalone function.
        """
        from raglite.external_data.clients.ecb.parsers import parse_gdp_csv

        return parse_gdp_csv(csv_data, country)

    async def _fetch_series(self, series_key: str, start_date: date, end_date: date) -> str:
        """Backward compatibility wrapper for fetch_series.

        Story 8.2: Tests expect this as a method. Delegates to standalone function.
        """
        return await fetch_series(series_key, start_date, end_date, self.timeout)

    def _parse_ecb_period(self, period: str) -> date:
        """Backward compatibility wrapper for parse_ecb_period.

        Story 8.2: Tests expect this as a method. Delegates to standalone function.
        """
        from raglite.external_data.clients.ecb.utils import parse_ecb_period

        return parse_ecb_period(period)
