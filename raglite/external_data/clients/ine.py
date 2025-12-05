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
    INEConstructionCostIndex,
    INEConstructionOutput,
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

    # INE indicator codes
    BUILDING_PERMITS_INDICATOR = "0008074"
    CONSTRUCTION_OUTPUT_INDICATOR = "0008075"
    CONSTRUCTION_COST_INDICATOR = "0008076"

    def __init__(self) -> None:
        self.base_url = INE_API_BASE
        self.api_key = settings.ine_api_key
        # Use test timeout in test environment (per clients.py pattern)
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 1.0 if is_test else float(settings.external_data_timeout)

    async def _fetch_with_retry(
        self,
        indicator: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Fetch data from INE API with retry logic.

        Args:
            indicator: INE indicator code
            start_date: Start of date range
            end_date: End of date range

        Returns:
            JSON response from API

        Raises:
            ExternalDataFetchError: If all retries fail
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [1, 2, 4]  # Exponential backoff

        params = {
            "indOcworkarralisingObraXML": indicator,
            "lang": "PT",
            "varcd": "",
            "Dim1": "",
            "Dim2": "",
            "Dim3": "",
            "min_d": start_date.strftime("%Y%m"),
            "max_d": end_date.strftime("%Y%m"),
        }

        headers = {}
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
                    return response.json()

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

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of building permit records
        """
        logger.info(
            "Fetching INE building permits",
            extra={"start": str(start_date), "end": str(end_date)},
        )

        data = await self._fetch_with_retry(
            self.BUILDING_PERMITS_INDICATOR,
            start_date,
            end_date,
        )

        return self._parse_building_permits(data)

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

        return self._parse_construction_output(data)

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

        return self._parse_construction_cost_index(data)

    def _parse_building_permits(self, data: dict) -> list[INEBuildingPermits]:
        """Parse INE building permits response."""
        results = []
        records = data.get("Dados", {})

        for period, values in records.items():
            try:
                # Period format: YYYYMM
                year = int(period[:4])
                month = int(period[4:6])
                record_date = date(year, month, 1)

                for value_data in values if isinstance(values, list) else [values]:
                    if isinstance(value_data, dict):
                        value = value_data.get("valor")
                        region = value_data.get("geocod", "Portugal")
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

    def _parse_construction_output(self, data: dict) -> list[INEConstructionOutput]:
        """Parse INE construction output response."""
        results = []
        records = data.get("Dados", {})

        for period, values in records.items():
            try:
                year = int(period[:4])
                month = int(period[4:6])
                record_date = date(year, month, 1)

                for value_data in values if isinstance(values, list) else [values]:
                    if isinstance(value_data, dict):
                        value = value_data.get("valor")
                        yoy = value_data.get("variacao_homologa")
                    else:
                        value = value_data
                        yoy = None

                    if value is not None:
                        results.append(
                            INEConstructionOutput(
                                date=record_date,
                                index_value=float(value),
                                yoy_change_pct=float(yoy) if yoy else None,
                            )
                        )
            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse INE construction output record",
                    extra={"period": period, "error": str(e)},
                )
                continue

        return results

    def _parse_construction_cost_index(self, data: dict) -> list[INEConstructionCostIndex]:
        """Parse INE construction cost index response."""
        results = []
        records = data.get("Dados", {})

        for period, values in records.items():
            try:
                year = int(period[:4])
                month = int(period[4:6])
                record_date = date(year, month, 1)

                for value_data in values if isinstance(values, list) else [values]:
                    if isinstance(value_data, dict):
                        total = value_data.get("valor")
                        materials = value_data.get("materiais")
                        labor = value_data.get("mao_obra")
                    else:
                        total = value_data
                        materials = None
                        labor = None

                    if total is not None:
                        results.append(
                            INEConstructionCostIndex(
                                date=record_date,
                                total_index=float(total),
                                materials_index=float(materials) if materials else None,
                                labor_index=float(labor) if labor else None,
                            )
                        )
            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse INE construction cost record",
                    extra={"period": period, "error": str(e)},
                )
                continue

        return results
