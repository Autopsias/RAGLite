"""Eurostat API client for EU statistics.

Story 8.2 Task 6: Eurostat client refactoring

Fetches EU-wide economic and energy data:
- Electricity prices for industrial consumers (nrg_pc_204)
- Construction output index
- Industrial production index
- Building permits
- Construction confidence

API Documentation: https://ec.europa.eu/eurostat/web/json-and-unicode-web-services
SDMX-JSON: https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/
"""

from __future__ import annotations

from datetime import date

from raglite.external_data.clients.base import BaseExternalClient
from raglite.external_data.clients.eurostat.config import (
    BUILDING_PERMITS_DATASET,
    CONSTRUCTION_CONFIDENCE_DATASET,
    CONSTRUCTION_DATASET,
    CONSUMPTION_BANDS,
    ELECTRICITY_DATASET,
    INDUSTRIAL_PRODUCTION_DATASET,
)
from raglite.external_data.clients.eurostat.fetchers import fetch_eurostat_data
from raglite.external_data.clients.eurostat.parsers import (
    parse_building_permits_data,
    parse_construction_confidence_data,
    parse_construction_data,
    parse_electricity_data,
    parse_industrial_data,
    parse_sdmx_index_data,
)
from raglite.external_data.clients.eurostat.utils import parse_eurostat_period
from raglite.external_data.models import (
    ECConstructionConfidence,
    EurostatBuildingPermits,
    EurostatConstructionOutput,
    EurostatElectricityPrice,
    EurostatIndustrialProduction,
)
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class EurostatClient(BaseExternalClient):
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

    # Expose dataset constants as class attributes for backward compatibility
    ELECTRICITY_DATASET = ELECTRICITY_DATASET
    CONSTRUCTION_DATASET = CONSTRUCTION_DATASET
    INDUSTRIAL_PRODUCTION_DATASET = INDUSTRIAL_PRODUCTION_DATASET
    BUILDING_PERMITS_DATASET = BUILDING_PERMITS_DATASET
    CONSTRUCTION_CONFIDENCE_DATASET = CONSTRUCTION_CONFIDENCE_DATASET
    CONSUMPTION_BANDS = CONSUMPTION_BANDS

    def __init__(self, timeout: float | None = None) -> None:
        """Initialize Eurostat client.

        Args:
            timeout: Request timeout in seconds (default: from settings)
        """
        if timeout is None:
            timeout = float(settings.external_data_timeout)
        super().__init__(timeout=timeout)

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

        data = await self._fetch_eurostat_data(ELECTRICITY_DATASET, filters)
        return parse_electricity_data(
            data, country, consumption_band, tax_component, start_date, end_date
        )

    async def fetch_construction_output(
        self,
        country: str = "PT",
        start_date: date | None = None,
        end_date: date | None = None,
        nace_sector: str = "F",  # Construction sector
        seasonal_adjustment: str = "SCA",
    ) -> list[EurostatConstructionOutput]:
        """Fetch monthly construction output index from Eurostat.

        Story 6.16 AC1: Construction production index

        Dataset: sts_copr_m (Short-term statistics: Production in construction)
        Coverage: Monthly, 2000-present

        Args:
            country: ISO 2-letter country code (default: PT)
            start_date: Start of date range
            end_date: End of date range
            nace_sector: NACE Rev. 2 sector (default: F = Construction)
            seasonal_adjustment: Adjustment type (SCA, NSA, WDA)

        Returns:
            List of construction output index records
        """
        logger.info(
            "Fetching Eurostat construction output",
            extra={
                "country": country,
                "start": str(start_date) if start_date else "all",
                "end": str(end_date) if end_date else "all",
            },
        )

        filters = {
            "geo": country,
            "nace_r2": nace_sector,
            "s_adj": seasonal_adjustment,
            "unit": "I21",  # Index 2021=100
        }

        data = await self._fetch_eurostat_data(CONSTRUCTION_DATASET, filters)
        return parse_construction_data(
            data, country, nace_sector, seasonal_adjustment, start_date, end_date
        )

    async def fetch_industrial_production(
        self,
        country: str = "PT",
        start_date: date | None = None,
        end_date: date | None = None,
        nace_sector: str = "B-D",  # Mining, manufacturing, energy
        seasonal_adjustment: str = "SCA",
    ) -> list[EurostatIndustrialProduction]:
        """Fetch monthly industrial production index from Eurostat.

        Story 6.16 AC2: Industrial production index

        Dataset: sts_inpr_m (Industrial production)
        Coverage: Monthly, 2000-present

        Args:
            country: ISO 2-letter country code (default: PT)
            start_date: Start of date range
            end_date: End of date range
            nace_sector: NACE Rev. 2 sector (default: B-D)
            seasonal_adjustment: Adjustment type (SCA, NSA, WDA)

        Returns:
            List of industrial production index records
        """
        logger.info(
            "Fetching Eurostat industrial production",
            extra={
                "country": country,
                "start": str(start_date) if start_date else "all",
                "end": str(end_date) if end_date else "all",
            },
        )

        filters = {
            "geo": country,
            "nace_r2": nace_sector,
            "s_adj": seasonal_adjustment,
            "unit": "I21",  # Index 2021=100
        }

        data = await self._fetch_eurostat_data(INDUSTRIAL_PRODUCTION_DATASET, filters)
        return parse_industrial_data(
            data, country, nace_sector, seasonal_adjustment, start_date, end_date
        )

    async def fetch_building_permits(
        self,
        country: str = "PT",
        start_date: date | None = None,
        end_date: date | None = None,
        building_type: str = "TOTAL",  # TOTAL, RES (residential), NRES (non-residential)
    ) -> list[EurostatBuildingPermits]:
        """Fetch building permits from Eurostat.

        Story 6.18 AC2: Eurostat building permits backup for INE

        Dataset: sts_cobp_m (Building permits - number of dwellings)
        Coverage: 2000-present, monthly

        Args:
            country: ISO 2-letter country code (default: PT)
            start_date: Start of date range
            end_date: End of date range
            building_type: Building type (TOTAL, RES, NRES)

        Returns:
            List of building permit records
        """
        logger.info(
            "Fetching Eurostat building permits",
            extra={
                "country": country,
                "start": str(start_date) if start_date else "all",
                "end": str(end_date) if end_date else "all",
            },
        )

        filters = {
            "geo": country,
            "building": building_type,
            "unit": "NR",  # Number
        }

        data = await self._fetch_eurostat_data(BUILDING_PERMITS_DATASET, filters)
        return parse_building_permits_data(data, country, building_type, start_date, end_date)

    async def fetch_construction_confidence(
        self,
        country: str = "PT",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[ECConstructionConfidence]:
        """Fetch construction confidence from EC Business Surveys via Eurostat.

        Story 6.19: EC Construction Confidence Index

        Dataset: ei_bsbu_m_r2 (Construction confidence indicator and survey results)
        Source: European Commission DG ECFIN via Eurostat
        Coverage: 1980-present, monthly

        Args:
            country: ISO 2-letter country code (default: PT for Portugal)
            start_date: Start of date range (default: 24 months ago)
            end_date: End of date range (default: today)

        Returns:
            List of ECConstructionConfidence records
        """
        # Use Statistics API (JSON-stat format) for EC Business Surveys
        base_url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
        url = f"{base_url}/{CONSTRUCTION_CONFIDENCE_DATASET}"

        # Build time period filter
        if start_date:
            since_period = start_date.strftime("%Y-%m")
        else:
            since_period = "2022-01"

        if end_date:
            until_period = end_date.strftime("%Y-%m")
        else:
            until_period = None

        params = {
            "geo": country,
            "s_adj": "SA",  # Seasonally adjusted
            "format": "JSON",
            "lang": "en",
            "sinceTimePeriod": since_period,
        }
        if until_period:
            params["untilTimePeriod"] = until_period

        logger.info(
            "Fetching EC construction confidence",
            extra={"country": country, "dataset": CONSTRUCTION_CONFIDENCE_DATASET},
        )

        # Use base class retry infrastructure instead of manual httpx.AsyncClient
        response = await self._fetch_with_retry(url, params=params)
        data = response.json()

        return parse_construction_confidence_data(data, country, start_date, end_date)

    # Backward compatibility wrapper methods for Story 8.2 refactoring
    # Tests expect these methods to exist on the client instance

    async def _fetch_eurostat_data(self, dataset: str, params: dict | None = None) -> dict:
        """Backward compatibility wrapper for fetch_eurostat_data.

        Args:
            dataset: Dataset code (e.g., "nrg_pc_204")
            params: Query parameters (filters dict)

        Returns:
            JSON-stat response
        """
        filters = params or {}
        return await fetch_eurostat_data(dataset, filters, self.timeout)

    def _parse_construction_data(
        self,
        data: dict,
        country: str,
        nace_sector: str,
        seasonal_adjustment: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[EurostatConstructionOutput]:
        """Backward compatibility wrapper for parse_construction_data."""
        return parse_construction_data(
            data, country, nace_sector, seasonal_adjustment, start_date, end_date
        )

    def _parse_industrial_data(
        self,
        data: dict,
        country: str,
        nace_sector: str,
        seasonal_adjustment: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[EurostatIndustrialProduction]:
        """Backward compatibility wrapper for parse_industrial_data."""
        return parse_industrial_data(
            data, country, nace_sector, seasonal_adjustment, start_date, end_date
        )

    def _parse_sdmx_index_data(
        self,
        data: dict,
        country: str,
        nace_sector: str,
        seasonal_adjustment: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[tuple[date, float]]:
        """Backward compatibility wrapper for parse_sdmx_index_data."""
        return parse_sdmx_index_data(
            data, country, nace_sector, seasonal_adjustment, start_date, end_date
        )

    def _parse_eurostat_period(self, period: str) -> date | None:
        """Backward compatibility wrapper for parse_eurostat_period."""
        return parse_eurostat_period(period)
