"""Eurostat API client for EU statistics.

Story 6.8: Tier 2 Data Sources & ML Enhancements (Conditional)

Fetches EU-wide economic and energy data:
- Electricity prices for industrial consumers (nrg_pc_204)

API Documentation: https://ec.europa.eu/eurostat/web/json-and-unicode-web-services
SDMX-JSON: https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/
"""

from __future__ import annotations

import asyncio
import gzip
import json
from datetime import date

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
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
    CONSTRUCTION_DATASET = "sts_copr_m"  # Construction production index
    INDUSTRIAL_PRODUCTION_DATASET = "sts_inpr_m"  # Industrial production index
    BUILDING_PERMITS_DATASET = "sts_cobp_m"  # Building permits (Story 6.18)
    CONSTRUCTION_CONFIDENCE_DATASET = (
        "ei_bsbu_m_r2"  # EC Business Surveys construction (Story 6.19)
    )

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

    def __init__(self, timeout: float | None = None) -> None:
        """Initialize Eurostat client.

        Args:
            timeout: Request timeout in seconds (default: from settings)
        """
        self.base_url = EUROSTAT_API_BASE
        self.timeout = timeout if timeout is not None else float(settings.external_data_timeout)

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

                    # Handle gzip-compressed responses (some Eurostat datasets return gzipped JSON)
                    content = response.content
                    if content[:2] == b"\x1f\x8b":  # Gzip magic number
                        content = gzip.decompress(content)
                        return dict(json.loads(content))

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

        data = await self._fetch_eurostat_data(self.CONSTRUCTION_DATASET, filters)
        return self._parse_construction_data(
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
        """Parse SDMX-JSON index data (common to construction and industrial production).

        Args:
            data: JSON response from Eurostat
            country: Country code
            nace_sector: NACE sector code
            seasonal_adjustment: Seasonal adjustment type
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            List of (date, index_value) tuples
        """
        results: list[tuple[date, float]] = []

        # Get values and dimensions
        values = data.get("value", {})
        dimensions = data.get("dimension", {})
        size = data.get("size", [])

        # Get time dimension
        time_dim = dimensions.get("time", {}).get("category", {}).get("index", {})
        period_by_index = {v: k for k, v in time_dim.items()}

        # Get dimension indices for our filters
        nace_indices = dimensions.get("nace_r2", {}).get("category", {}).get("index", {})
        s_adj_indices = dimensions.get("s_adj", {}).get("category", {}).get("index", {})
        unit_indices = dimensions.get("unit", {}).get("category", {}).get("index", {})
        geo_indices = dimensions.get("geo", {}).get("category", {}).get("index", {})

        # Get the dimension indices for our query
        nace_idx = nace_indices.get(nace_sector)
        s_adj_idx = s_adj_indices.get(seasonal_adjustment)
        unit_idx = unit_indices.get("I21")
        geo_idx = geo_indices.get(country)

        if nace_idx is None or s_adj_idx is None or unit_idx is None or geo_idx is None:
            logger.warning(
                "Could not find dimension indices",
                extra={
                    "nace": nace_sector,
                    "s_adj": seasonal_adjustment,
                    "country": country,
                },
            )
            return results

        # Calculate offset for multi-dimensional indexing
        # SDMX-JSON uses row-major order: index = sum(dim_index * product_of_following_dims)
        # Size array typically: [freq, indic_bt, nace_r2, s_adj, unit, geo, time]
        if len(size) >= 7:
            # Warn if dimension count differs from expected
            if len(size) != 7:
                logger.warning(
                    "Unexpected dimension count in SDMX response",
                    extra={"expected": 7, "actual": len(size)},
                )

            # Calculate stride for each dimension (product of all following dimensions)
            time_stride = 1
            geo_stride = size[6]  # time
            unit_stride = size[6] * size[5]  # time * geo
            s_adj_stride = size[6] * size[5] * size[4]  # time * geo * unit
            nace_stride = size[6] * size[5] * size[4] * size[3]  # time * geo * unit * s_adj

            # For each time period, calculate the flat index
            for time_idx, period in period_by_index.items():
                # Calculate flat index assuming freq_idx=0, indic_bt_idx=0
                flat_idx = (
                    nace_idx * nace_stride
                    + s_adj_idx * s_adj_stride
                    + unit_idx * unit_stride
                    + geo_idx * geo_stride
                    + time_idx * time_stride
                )

                idx_str = str(flat_idx)
                index_value = values.get(idx_str)

                if index_value is None:
                    continue

                # Parse period
                record_date = self._parse_eurostat_period(period)
                if record_date is None:
                    continue

                # Apply date filters
                if start_date and record_date < start_date.replace(day=1):
                    continue
                if end_date and record_date > end_date:
                    continue

                results.append((record_date, float(index_value)))

        return results

    def _parse_construction_data(
        self,
        data: dict,
        country: str,
        nace_sector: str,
        seasonal_adjustment: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[EurostatConstructionOutput]:
        """Parse Eurostat construction output response.

        Args:
            data: JSON response from Eurostat
            country: Country code
            nace_sector: NACE sector code
            seasonal_adjustment: Seasonal adjustment type
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            List of construction output records
        """
        parsed_data = self._parse_sdmx_index_data(
            data, country, nace_sector, seasonal_adjustment, start_date, end_date
        )

        results = [
            EurostatConstructionOutput(
                date=record_date,
                index_value=index_value,
                country=country,
                nace_sector=nace_sector,
                seasonal_adjustment=seasonal_adjustment,
            )
            for record_date, index_value in parsed_data
        ]

        # Sort by date
        results.sort(key=lambda x: x.date)

        logger.info(
            "Parsed Eurostat construction output",
            extra={"count": len(results)},
        )
        return results

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

        data = await self._fetch_eurostat_data(self.INDUSTRIAL_PRODUCTION_DATASET, filters)
        return self._parse_industrial_data(
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
        """Parse Eurostat industrial production response.

        Args:
            data: JSON response from Eurostat
            country: Country code
            nace_sector: NACE sector code
            seasonal_adjustment: Seasonal adjustment type
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            List of industrial production records
        """
        parsed_data = self._parse_sdmx_index_data(
            data, country, nace_sector, seasonal_adjustment, start_date, end_date
        )

        results = [
            EurostatIndustrialProduction(
                date=record_date,
                index_value=index_value,
                country=country,
                nace_sector=nace_sector,
                seasonal_adjustment=seasonal_adjustment,
            )
            for record_date, index_value in parsed_data
        ]

        # Sort by date
        results.sort(key=lambda x: x.date)

        logger.info(
            "Parsed Eurostat industrial production",
            extra={"count": len(results)},
        )
        return results

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

        data = await self._fetch_eurostat_data(self.BUILDING_PERMITS_DATASET, filters)
        return self._parse_building_permits_data(data, country, building_type, start_date, end_date)

    def _parse_building_permits_data(
        self,
        data: dict,
        country: str,
        building_type: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[EurostatBuildingPermits]:
        """Parse Eurostat building permits response.

        Args:
            data: JSON response from Eurostat
            country: Country code
            building_type: Building type code
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            List of building permit records
        """
        results: list[EurostatBuildingPermits] = []

        # Get values and time dimension
        values = data.get("value", {})
        dimensions = data.get("dimension", {})
        time_dim = dimensions.get("time", {}).get("category", {}).get("index", {})

        # Build index to period mapping
        period_by_index = {v: k for k, v in time_dim.items()}

        for idx_str, permits_value in values.items():
            try:
                idx = int(idx_str)
                period = period_by_index.get(idx)

                if not period or permits_value is None:
                    continue

                # Parse period (YYYY-MM)
                record_date = self._parse_eurostat_period(period)
                if record_date is None:
                    continue

                # Apply date filters
                if start_date and record_date < start_date.replace(day=1):
                    continue
                if end_date and record_date > end_date:
                    continue

                results.append(
                    EurostatBuildingPermits(
                        date=record_date,
                        permits_count=int(permits_value),
                        country=country,
                        building_type=building_type,
                    )
                )

            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse Eurostat building permits record",
                    extra={"index": idx_str, "error": str(e)},
                )
                continue

        # Sort by date
        results.sort(key=lambda x: x.date)

        logger.info(
            "Parsed Eurostat building permits",
            extra={"count": len(results)},
        )
        return results

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

        Indicators fetched:
        - BS-CCI-BAL: Construction confidence indicator (main)
        - BS-CEME-BAL: Employment expectations over next 3 months
        - BS-COB-BAL: Evolution of current order books

        Args:
            country: ISO 2-letter country code (default: PT for Portugal)
            start_date: Start of date range (default: 24 months ago)
            end_date: End of date range (default: today)

        Returns:
            List of ECConstructionConfidence records

        Example:
            >>> client = EurostatClient()
            >>> data = await client.fetch_construction_confidence(
            ...     country="PT",
            ...     start_date=date(2024, 1, 1),
            ...     end_date=date(2024, 6, 30),
            ... )
        """
        # Use Statistics API (JSON-stat format) for EC Business Surveys
        base_url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
        url = f"{base_url}/{self.CONSTRUCTION_CONFIDENCE_DATASET}"

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
            extra={"country": country, "dataset": self.CONSTRUCTION_CONFIDENCE_DATASET},
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as e:
            raise ExternalDataFetchError(
                source="Eurostat",
                message=f"Timeout fetching construction confidence: {e}",
            ) from e
        except httpx.HTTPStatusError as e:
            raise ExternalDataFetchError(
                source="Eurostat",
                message=f"HTTP error fetching construction confidence: {e}",
            ) from e

        return self._parse_construction_confidence_data(data, country, start_date, end_date)

    def _parse_construction_confidence_data(
        self,
        data: dict,
        country: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[ECConstructionConfidence]:
        """Parse EC construction confidence JSON-stat response.

        The data is organized with a flat value dictionary indexed by position.
        Position = indic_index * time_count + time_index

        Args:
            data: JSON-stat 2.0 response from Eurostat Statistics API
            country: Country code for the records
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of ECConstructionConfidence records
        """
        results: list[ECConstructionConfidence] = []

        # Get dimensions
        dimensions = data.get("dimension", {})
        time_dim = dimensions.get("time", {}).get("category", {})
        indic_dim = dimensions.get("indic", {}).get("category", {})

        time_index = time_dim.get("index", {})
        indic_index = indic_dim.get("index", {})

        # Get values
        values = data.get("value", {})

        if not time_index or not values:
            logger.warning("No time periods or values in EC construction confidence response")
            return results

        # Map indicator codes
        # BS-CCI-BAL: Construction confidence indicator
        # BS-CEME-BAL: Employment expectations
        # BS-COB-BAL: Order books
        cci_idx = indic_index.get("BS-CCI-BAL")
        employment_idx = indic_index.get("BS-CEME-BAL")
        order_books_idx = indic_index.get("BS-COB-BAL")

        if cci_idx is None:
            logger.warning("Construction confidence indicator (BS-CCI-BAL) not found")
            return results

        time_count = len(time_index)

        # Build data by time period
        period_data: dict[str, dict[str, float | None]] = {}

        for period, t_idx in time_index.items():
            period_data[period] = {
                "confidence_index": None,
                "employment_expectations": None,
                "order_books": None,
            }

            # Get confidence index
            if cci_idx is not None:
                pos = cci_idx * time_count + t_idx
                if str(pos) in values:
                    period_data[period]["confidence_index"] = values[str(pos)]

            # Get employment expectations
            if employment_idx is not None:
                pos = employment_idx * time_count + t_idx
                if str(pos) in values:
                    period_data[period]["employment_expectations"] = values[str(pos)]

            # Get order books
            if order_books_idx is not None:
                pos = order_books_idx * time_count + t_idx
                if str(pos) in values:
                    period_data[period]["order_books"] = values[str(pos)]

        # Convert to records
        for period, indicators in period_data.items():
            if indicators["confidence_index"] is None:
                continue

            # Parse period (YYYY-MM)
            record_date = self._parse_eurostat_period(period)
            if record_date is None:
                continue

            # Apply date filters
            if start_date and record_date < start_date.replace(day=1):
                continue
            if end_date and record_date > end_date:
                continue

            results.append(
                ECConstructionConfidence(
                    date=record_date,
                    confidence_index=indicators["confidence_index"],
                    employment_expectations=indicators["employment_expectations"],
                    order_books=indicators["order_books"],
                    country=country,
                )
            )

        # Sort by date
        results.sort(key=lambda x: x.date)

        logger.info(
            "Parsed EC construction confidence",
            extra={"count": len(results), "country": country},
        )
        return results
