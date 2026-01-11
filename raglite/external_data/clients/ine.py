"""INE (Instituto Nacional de Estatística) API client.

Story 6.1: Tier 1 External Data Source Integration
Story 8.3: Refactored for modularity (facade pattern)

Fetches Portuguese economic data:
- Building permits (Licenças de construção)
- Construction output index (Índice de Produção na Construção)
- Construction cost index (Índice de Custos de Construção)

API Documentation: https://www.ine.pt/xportal/xmain?xpgid=ine_api
"""

from __future__ import annotations

import os
from datetime import date

from raglite.external_data.clients import ine_http, ine_parsers
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

    def __init__(self) -> None:
        self.base_url = INE_API_BASE
        self.api_key = settings.ine_api_key
        # Story 6.10.2 AC1: Increased test timeout from 1s to 10s for slow APIs
        # Further increased to 60s for slow INE API responses
        # Production timeout unchanged (uses external_data_timeout from settings)
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 60.0 if is_test else float(settings.external_data_timeout)
        # Story 6.10.3 AC2: Add file-based caching for external data
        from raglite.shared.caching import ExternalDataCache

        self._cache = ExternalDataCache(ttl_hours=24)

    async def _fetch_with_retry(
        self,
        indicator: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Fetch data from INE API with retry logic.

        Delegates to ine_http.fetch_with_retry for implementation.
        """
        return await ine_http.fetch_with_retry(
            self.base_url,
            indicator,
            start_date,
            end_date,
            self.timeout,
            self.api_key,
        )

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

        results = ine_parsers.parse_building_permits(data, start_date, end_date)

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

        return ine_parsers.parse_construction_output(data, start_date, end_date)

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

        return ine_parsers.parse_construction_cost_index(data, start_date, end_date)

    # Backward compatibility wrapper methods for tests
    def _parse_building_permits(
        self, data: dict, start_date: date | None = None, end_date: date | None = None
    ) -> list[INEBuildingPermits]:
        """Backward compatibility wrapper for tests."""
        return ine_parsers.parse_building_permits(data, start_date, end_date)

    def _parse_construction_output(
        self, data: dict, start_date: date | None = None, end_date: date | None = None
    ) -> list[INEConstructionOutput]:
        """Backward compatibility wrapper for tests."""
        return ine_parsers.parse_construction_output(data, start_date, end_date)

    def _parse_construction_cost_index(
        self, data: dict, start_date: date | None = None, end_date: date | None = None
    ) -> list[INEConstructionCostIndex]:
        """Backward compatibility wrapper for tests."""
        return ine_parsers.parse_construction_cost_index(data, start_date, end_date)

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

        return ine_parsers.parse_house_price_index(data, start_date, end_date)

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

        return ine_parsers.parse_construction_confidence(data, start_date, end_date)
