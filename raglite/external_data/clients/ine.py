"""INE (Instituto Nacional de Estatística) API client.

Story 6.1: Tier 1 External Data Source Integration

Fetches Portuguese economic data:
- Building permits (Licenças de construção)
- Construction output index (Índice de Produção na Construção)
- Construction cost index (Índice de Custos de Construção)

API Documentation: https://www.ine.pt/xportal/xmain?xpgid=ine_api
"""

from __future__ import annotations

import asyncio
import os
from datetime import date

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import (
    INEBuildingPermits,
    INEConstructionConfidence,
    INEConstructionCostIndex,
    INEConstructionOutput,
    INEHousePriceIndex,
)
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# INE API Configuration
INE_API_BASE = "https://www.ine.pt/ine/json_indicador/pindica.jsp"


class INEClient:
    """Client for INE (Instituto Nacional de Estatística) API.

    Provides access to Portuguese construction and housing statistics.

    Example:
        >>> client = INEClient()
        >>> permits = await client.fetch_building_permits(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 3, 31)
        ... )
    """

    # INE indicator codes (verified 2025-12-08)
    # Source: https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_base_dados
    BUILDING_PERMITS_INDICATOR = "0012096"  # Edifícios licenciados (N.º)
    CONSTRUCTION_OUTPUT_INDICATOR = "0011845"  # Índice de produção na construção (Base 2021)
    CONSTRUCTION_COST_INDICATOR = "0011750"  # Índice de custo de construção (Base 2021)

    # Story 6.8 AC2.1: Tier 2 indicator codes
    # Story 6.11.4: Fixed HPI indicator - 0010017 returned wrong data (death statistics)
    # Correct indicator is 0009201 per INE construction/housing page
    HOUSE_PRICE_INDEX_INDICATOR = "0009201"  # Índice de Preços da Habitação (Base 2015)
    CONSTRUCTION_CONFIDENCE_INDICATOR = "0011127"  # Indicador de Confiança da Construção

    # Portuguese month names for parsing API responses
    MONTH_NAMES_PT = {
        "Janeiro": 1,
        "Fevereiro": 2,
        "Março": 3,
        "Abril": 4,
        "Maio": 5,
        "Junho": 6,
        "Julho": 7,
        "Agosto": 8,
        "Setembro": 9,
        "Outubro": 10,
        "Novembro": 11,
        "Dezembro": 12,
    }

    def __init__(self) -> None:
        self.base_url = INE_API_BASE
        self.api_key = settings.ine_api_key
        # Story 6.10.2 AC1: Increased test timeout from 1s to 10s for slow APIs
        # Production timeout unchanged (uses external_data_timeout from settings)
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 10.0 if is_test else float(settings.external_data_timeout)
        # Story 6.10.3 AC2: Add file-based caching for external data
        from raglite.shared.caching import ExternalDataCache

        self._cache = ExternalDataCache(ttl_hours=24)

    def _parse_period_to_date(self, period: str) -> date | None:
        """Parse INE period string to date.

        Handles multiple formats:
            - "Setembro de 2025" (Portuguese month name)
            - "202509" or "2025-09" (YYYYMM)
            - "2025" (year only)
            - "2024T1" or "2024T2" (quarterly format - Story 6.8)

        Args:
            period: Period string from INE API

        Returns:
            date object or None if parsing fails
        """
        import re

        # Try Portuguese month format: "Setembro de 2025"
        month_pattern = r"(\w+)\s+de\s+(\d{4})"
        match = re.match(month_pattern, period)
        if match:
            month_name, year_str = match.groups()
            month = self.MONTH_NAMES_PT.get(month_name)
            if month:
                return date(int(year_str), month, 1)

        # Story 6.8: Try quarterly format: "2024T1", "2024T2", etc.
        quarterly_pattern = r"(\d{4})T([1-4])"
        match = re.match(quarterly_pattern, period)
        if match:
            year_str, quarter_str = match.groups()
            quarter = int(quarter_str)
            # Q1 = Jan, Q2 = Apr, Q3 = Jul, Q4 = Oct
            month = (quarter - 1) * 3 + 1
            return date(int(year_str), month, 1)

        # Try YYYYMM format: "202509"
        if len(period) == 6 and period.isdigit():
            try:
                return date(int(period[:4]), int(period[4:6]), 1)
            except ValueError:
                pass

        # Try year only format: "2025"
        if len(period) == 4 and period.isdigit():
            try:
                return date(int(period), 1, 1)
            except ValueError:
                pass

        return None

    async def _fetch_with_retry(
        self,
        indicator: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Fetch data from INE API with retry logic.

        Args:
            indicator: INE indicator code (7 digits, e.g., '0008074')
            start_date: Start of date range
            end_date: End of date range

        Returns:
            JSON response from API

        Raises:
            ExternalDataFetchError: If all retries fail

        API Documentation:
            https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_api_db

        Endpoint format:
            {host}/ine/json_indicador/pindica.jsp?op=2&varcd={code}&Dim1={periods}&lang=PT

        Dim1 formats:
            - T: All available periods (used for monthly data)
            - S7A2020: Year 2020 (for annual data)
            - S7A2020,S7A2021: Multiple years

        Period response formats (in Dados keys):
            - "Setembro de 2025": Monthly data (Portuguese month name)
            - "2020": Annual data
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [2, 4, 8]  # NFR1: exponential backoff at 2s/4s/8s intervals

        # Use Dim1=T to get all available periods, then filter by date range
        # This avoids issues with indicator-specific Dim1 format requirements
        # Correct API parameters per official documentation
        # https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_api_db
        params = {
            "op": "2",  # Required operation code
            "varcd": indicator,  # Indicator code (e.g., 0012096)
            "Dim1": "T",  # All available periods
            "lang": "PT",  # Language
        }

        headers = {
            "Accept": "application/json",
            "User-Agent": "RAGLite/1.0 (https://github.com/raglite)",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(
                        self.base_url,
                        params=params,
                        headers=headers,
                    )
                    response.raise_for_status()

                    # API returns a list with single element: [{...}]
                    json_data = response.json()
                    if isinstance(json_data, list) and len(json_data) > 0:
                        result = json_data[0]
                        # Check for API error response
                        if "Sucesso" in result:
                            falso = result.get("Sucesso", {}).get("Falso", [])
                            if falso:
                                error_msg = falso[0].get("Msg", "Unknown API error")
                                raise ExternalDataFetchError(
                                    source="INE",
                                    message=f"API error: {error_msg}",
                                )
                        return dict(result)
                    return dict(json_data) if isinstance(json_data, dict) else {}

                except httpx.TimeoutException as e:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "INE API timeout, retrying",
                            extra={
                                "attempt": attempt + 1,
                                "delay": delay,
                                "indicator": indicator,
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "INE API timeout after retries",
                            extra={"indicator": indicator, "error": str(e)},
                        )
                        raise ExternalDataFetchError(
                            source="INE",
                            message=f"Timeout after {max_retries} attempts",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    # Retry on server errors (5xx) or rate limit (429)
                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "INE API error, retrying",
                            extra={
                                "attempt": attempt + 1,
                                "delay": delay,
                                "status": e.response.status_code,
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "INE API request failed",
                            extra={
                                "indicator": indicator,
                                "status": e.response.status_code,
                            },
                        )
                        raise ExternalDataFetchError(
                            source="INE",
                            message=f"HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        # Unreachable but satisfies type checker
        raise ExternalDataFetchError(source="INE", message="Unexpected retry loop exit")

    async def fetch_building_permits(
        self,
        start_date: date,
        end_date: date,
    ) -> list[INEBuildingPermits]:
        """Fetch building permits data.

        Story 6.10.3 AC2: Uses file-based caching to reduce API calls
        and handle transient failures gracefully.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of building permit records
        """
        # Story 6.10.3 AC2: Try cache first
        cache_key = f"ine_building_permits_{start_date}_{end_date}"
        cached = self._cache.get(cache_key)
        if cached:
            logger.info(
                "INE building permits loaded from cache",
                extra={"start": str(start_date), "end": str(end_date)},
            )
            return [INEBuildingPermits(**r) for r in cached]

        logger.info(
            "Fetching INE building permits",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        data = await self._fetch_with_retry(
            self.BUILDING_PERMITS_INDICATOR,
            start_date,
            end_date,
        )

        results = self._parse_building_permits(data, start_date, end_date)

        # Story 6.10.3: Cache results for future use
        if results:
            self._cache.set(cache_key, [r.__dict__ for r in results])

        return results

    async def fetch_construction_output(
        self,
        start_date: date,
        end_date: date,
    ) -> list[INEConstructionOutput]:
        """Fetch construction output index.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of construction output index records
        """
        logger.info(
            "Fetching INE construction output",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        data = await self._fetch_with_retry(
            self.CONSTRUCTION_OUTPUT_INDICATOR,
            start_date,
            end_date,
        )

        return self._parse_construction_output(data, start_date, end_date)

    async def fetch_construction_cost_index(
        self,
        start_date: date,
        end_date: date,
    ) -> list[INEConstructionCostIndex]:
        """Fetch construction cost index.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of construction cost index records
        """
        logger.info(
            "Fetching INE construction cost index",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        data = await self._fetch_with_retry(
            self.CONSTRUCTION_COST_INDICATOR,
            start_date,
            end_date,
        )

        return self._parse_construction_cost_index(data, start_date, end_date)

    def _parse_building_permits(
        self, data: dict, start_date: date | None = None, end_date: date | None = None
    ) -> list[INEBuildingPermits]:
        """Parse INE building permits response.

        Args:
            data: Raw JSON response from INE API
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of building permit records within date range
        """
        results = []
        records = data.get("Dados", {})

        for period, values in records.items():
            try:
                # Parse period using flexible parser
                record_date = self._parse_period_to_date(period)
                if record_date is None:
                    logger.debug(f"Skipping unparseable period: {period}")
                    continue

                # Apply date range filter
                # Use first-of-month comparison for monthly data (Story 6.9.1 AC1)
                # Monthly periods like "Setembro de 2025" parse to 2025-09-01
                # Without this fix, start_date=2025-09-15 would exclude September data
                if start_date and record_date < start_date.replace(day=1):
                    continue
                if end_date and record_date > end_date:
                    continue

                for value_data in values if isinstance(values, list) else [values]:
                    if isinstance(value_data, dict):
                        value = value_data.get("valor")
                        region = str(value_data.get("geodsg", value_data.get("geocod", "Portugal")))
                    else:
                        value = value_data
                        region = "Portugal"

                    if value is not None:
                        results.append(
                            INEBuildingPermits(
                                date=record_date,
                                permits_count=int(float(value)),
                                region=region,
                            )
                        )
            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse INE building permit record",
                    extra={"period": period, "error": str(e)},
                )
                continue

        logger.info(
            "Parsed INE building permits",
            extra={"record_count": len(results)},
        )
        return results

    def _parse_construction_output(
        self, data: dict, start_date: date | None = None, end_date: date | None = None
    ) -> list[INEConstructionOutput]:
        """Parse INE construction output response.

        Args:
            data: Raw JSON response from INE API
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of construction output records within date range
        """
        results = []
        records = data.get("Dados", {})

        for period, values in records.items():
            try:
                # Parse period using flexible parser
                record_date = self._parse_period_to_date(period)
                if record_date is None:
                    logger.debug(f"Skipping unparseable period: {period}")
                    continue

                # Apply date range filter
                # Use first-of-month comparison for monthly data (Story 6.9.1 AC1)
                if start_date and record_date < start_date.replace(day=1):
                    continue
                if end_date and record_date > end_date:
                    continue

                for value_data in values if isinstance(values, list) else [values]:
                    if isinstance(value_data, dict):
                        value = value_data.get("valor")
                        # Filter for Total only (dim_3_t == "Total")
                        dim3_type = value_data.get("dim_3_t", "")
                        if dim3_type and dim3_type != "Total":
                            continue
                    else:
                        value = value_data

                    if value is not None:
                        results.append(
                            INEConstructionOutput(
                                date=record_date,
                                index_value=float(value),
                                yoy_change_pct=None,  # YoY is the value itself for this indicator
                            )
                        )
            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse INE construction output record",
                    extra={"period": period, "error": str(e)},
                )
                continue

        logger.info(
            "Parsed INE construction output",
            extra={"record_count": len(results)},
        )
        return results

    def _parse_construction_cost_index(
        self, data: dict, start_date: date | None = None, end_date: date | None = None
    ) -> list[INEConstructionCostIndex]:
        """Parse INE construction cost index response.

        Args:
            data: Raw JSON response from INE API
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of construction cost index records within date range
        """
        results = []
        records = data.get("Dados", {})

        # Collect values by period to group Total, Materials, Labor
        period_data: dict[date, dict[str, float]] = {}

        for period, values in records.items():
            try:
                # Parse period using flexible parser
                record_date = self._parse_period_to_date(period)
                if record_date is None:
                    logger.debug(f"Skipping unparseable period: {period}")
                    continue

                # Apply date range filter
                # Use first-of-month comparison for monthly data (Story 6.9.1 AC1)
                if start_date and record_date < start_date.replace(day=1):
                    continue
                if end_date and record_date > end_date:
                    continue

                if record_date not in period_data:
                    period_data[record_date] = {}

                for value_data in values if isinstance(values, list) else [values]:
                    if isinstance(value_data, dict):
                        value = value_data.get("valor")
                        factor_type = value_data.get("dim_3_t", "Total")

                        if value is not None:
                            if factor_type == "Total":
                                period_data[record_date]["total"] = float(value)
                            elif factor_type == "Materiais":
                                period_data[record_date]["materials"] = float(value)
                            elif "Mão" in factor_type or "obra" in factor_type.lower():
                                period_data[record_date]["labor"] = float(value)
                    else:
                        if value_data is not None:
                            period_data[record_date]["total"] = float(value_data)

            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse INE construction cost record",
                    extra={"period": period, "error": str(e)},
                )
                continue

        # Convert grouped data to results
        for record_date, values in sorted(period_data.items()):
            if "total" in values:
                results.append(
                    INEConstructionCostIndex(
                        date=record_date,
                        total_index=values["total"],
                        materials_index=values.get("materials"),
                        labor_index=values.get("labor"),
                    )
                )

        logger.info(
            "Parsed INE construction cost index",
            extra={"record_count": len(results)},
        )
        return results

    # =========================================================================
    # Story 6.8 AC2.1: Tier 2 methods
    # =========================================================================

    async def fetch_house_price_index(
        self,
        start_date: date,
        end_date: date,
    ) -> list[INEHousePriceIndex]:
        """Fetch INE House Price Index (HPI).

        Story 6.8 AC2.1: Leading indicator for construction demand.

        Dataset: 0010017 (Índice de Preços da Habitação)
        Coverage: 2009-present, quarterly
        Base year: 2015 = 100

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of house price index records
        """
        logger.info(
            "Fetching INE house price index",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        data = await self._fetch_with_retry(
            self.HOUSE_PRICE_INDEX_INDICATOR,
            start_date,
            end_date,
        )

        return self._parse_house_price_index(data, start_date, end_date)

    async def fetch_construction_confidence(
        self,
        start_date: date,
        end_date: date,
    ) -> list[INEConstructionConfidence]:
        """Fetch INE Construction Confidence Indicator.

        Story 6.8 AC2.1: Sentiment indicator for construction sector.

        Dataset: 0011127 (Indicador de Confiança da Construção)
        Coverage: 1987-present, monthly
        Range: typically -50 to +50

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of construction confidence records
        """
        logger.info(
            "Fetching INE construction confidence",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        data = await self._fetch_with_retry(
            self.CONSTRUCTION_CONFIDENCE_INDICATOR,
            start_date,
            end_date,
        )

        return self._parse_construction_confidence(data, start_date, end_date)

    def _parse_house_price_index(
        self, data: dict, start_date: date | None = None, end_date: date | None = None
    ) -> list[INEHousePriceIndex]:
        """Parse INE house price index response.

        Args:
            data: Raw JSON response from INE API
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of house price index records within date range
        """
        results = []
        records = data.get("Dados", {})

        for period, values in records.items():
            try:
                # Parse period using flexible parser
                record_date = self._parse_period_to_date(period)
                if record_date is None:
                    logger.debug(f"Skipping unparseable period: {period}")
                    continue

                # Apply date range filter
                if start_date and record_date < start_date.replace(day=1):
                    continue
                if end_date and record_date > end_date:
                    continue

                for value_data in values if isinstance(values, list) else [values]:
                    if isinstance(value_data, dict):
                        value = value_data.get("valor")
                        region = str(value_data.get("geodsg", value_data.get("geocod", "Portugal")))
                    else:
                        value = value_data
                        region = "Portugal"

                    if value is not None:
                        results.append(
                            INEHousePriceIndex(
                                date=record_date,
                                index_value=float(value),
                                yoy_change_pct=None,  # Calculated separately if needed
                                region=region,
                            )
                        )
            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse INE house price index record",
                    extra={"period": period, "error": str(e)},
                )
                continue

        logger.info(
            "Parsed INE house price index",
            extra={"record_count": len(results)},
        )
        return results

    def _parse_construction_confidence(
        self, data: dict, start_date: date | None = None, end_date: date | None = None
    ) -> list[INEConstructionConfidence]:
        """Parse INE construction confidence response.

        Args:
            data: Raw JSON response from INE API
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of construction confidence records within date range
        """
        results = []
        records = data.get("Dados", {})

        for period, values in records.items():
            try:
                # Parse period using flexible parser
                record_date = self._parse_period_to_date(period)
                if record_date is None:
                    logger.debug(f"Skipping unparseable period: {period}")
                    continue

                # Apply date range filter
                if start_date and record_date < start_date.replace(day=1):
                    continue
                if end_date and record_date > end_date:
                    continue

                for value_data in values if isinstance(values, list) else [values]:
                    if isinstance(value_data, dict):
                        value = value_data.get("valor")
                        region = str(value_data.get("geodsg", value_data.get("geocod", "Portugal")))
                    else:
                        value = value_data
                        region = "Portugal"

                    if value is not None:
                        results.append(
                            INEConstructionConfidence(
                                date=record_date,
                                confidence_index=float(value),
                                region=region,
                            )
                        )
            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse INE construction confidence record",
                    extra={"period": period, "error": str(e)},
                )
                continue

        logger.info(
            "Parsed INE construction confidence",
            extra={"record_count": len(results)},
        )
        return results
