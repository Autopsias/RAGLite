"""Main BaseGov client.

Story 8.2 Task 4: Refactored from basegov.py monolith
Orchestrates IMPIC, TED, and OCDS data sources.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

from raglite.external_data.clients.base import BaseExternalClient
from raglite.external_data.clients.basegov import impic, ocds, parsers, ted_api
from raglite.external_data.clients.basegov.config import (
    CACHE_DIR,
    CPV_CONSTRUCTION,
    DADOS_GOV_API_BASE,
    IMPIC_CONTRACTS_DATASET,
    OCDS_DATASET_ID,
    TED_API_BASE,
)
from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import BaseGovContract
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class BaseGovClient(BaseExternalClient):
    """Client for Portuguese public procurement data.

    Story 6.9.5: Updated to use dados.gov.pt IMPIC XLSX dataset as primary source.
    Story 8.2 Task 4: Refactored into modular package structure.

    Data Sources (priority order):
    1. dados.gov.pt IMPIC XLSX - ALL Portuguese contracts (2012-2025)
    2. TED API v3 - Fallback for EU-threshold contracts only

    The IMPIC dataset provides comprehensive coverage of all Portuguese public
    contracts, including those below EU thresholds. Files are organized by year
    (contratos2012.xlsx through contratos2025.xlsx).

    Example:
        >>> client = BaseGovClient()
        >>> contracts = await client.fetch_contracts(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 3, 31),
        ...     cpv_code="45000000"  # Construction works
        ... )
    """

    # CPV codes for construction-related contracts
    CPV_CONSTRUCTION = CPV_CONSTRUCTION
    CPV_BUILDING = "45210000"  # Building construction
    CPV_CIVIL_ENGINEERING = "45220000"  # Civil engineering
    CPV_ROAD = "45233000"  # Highway construction

    # EU procurement thresholds (approximate, as of 2024)
    # Contracts below these thresholds are NOT in TED (but ARE in IMPIC dataset)
    EU_THRESHOLD_WORKS = 5_382_000  # EUR for works
    EU_THRESHOLD_SUPPLIES = 221_000  # EUR for supplies/services (central govt)
    EU_THRESHOLD_SERVICES = 221_000  # EUR for services

    # Cache configuration
    CACHE_DIR = CACHE_DIR
    CACHE_TTL_HOURS = 24  # XLSX files are updated daily/weekly

    def __init__(self) -> None:
        """Initialize BaseGov client."""
        # Story 6.9.5 AC8: Test-aware timeout
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        timeout = 1.0 if is_test else float(settings.external_data_timeout)
        super().__init__(timeout=timeout)

        # Set API endpoints
        self.ted_api_base = TED_API_BASE
        self.dados_gov_base = DADOS_GOV_API_BASE
        self.impic_dataset = IMPIC_CONTRACTS_DATASET
        self.ocds_dataset_id = OCDS_DATASET_ID

        # Cache directory
        self.cache_dir = self.CACHE_DIR
        if not is_test:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_contracts(
        self,
        start_date: date,
        end_date: date,
        cpv_code: str | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[BaseGovContract]:
        """Fetch public works contracts.

        Story 6.9.5 AC4: Updated with IMPIC XLSX as primary source

        Data sources (in priority order):
        1. dados.gov.pt IMPIC XLSX - ALL Portuguese contracts (2012-2025)
        2. TED API v3 - Fallback for EU-threshold contracts only

        The IMPIC dataset includes ALL Portuguese public contracts, not just
        those above EU thresholds. This provides much better coverage than TED.

        Args:
            start_date: Start of date range (publication date)
            end_date: End of date range
            cpv_code: CPV code filter (default: construction works)
            min_value: Minimum contract value in EUR
            max_value: Maximum contract value in EUR
            page: Page number for pagination (used for TED fallback)
            page_size: Results per page (used for TED fallback)

        Returns:
            List of contract records
        """
        if cpv_code is None:
            cpv_code = self.CPV_CONSTRUCTION

        logger.info(
            "Fetching public procurement contracts",
            extra={
                "start": str(start_date),
                "end": str(end_date),
                "cpv": cpv_code,
            },
        )

        results: list[BaseGovContract] = []

        # Try IMPIC XLSX first (primary source - ALL Portuguese contracts)
        try:
            impic_results = await impic.fetch_impic_contracts(
                start_date=start_date,
                end_date=end_date,
                cpv_code=cpv_code,
                timeout=self.timeout,
                cache_dir=self.cache_dir,
            )
            results.extend(impic_results)
            logger.info(
                "Fetched contracts from IMPIC XLSX",
                extra={"count": len(results)},
            )
        except Exception as e:
            logger.warning(
                "IMPIC dataset unavailable, trying TED API fallback",
                extra={"error": str(e)},
            )

        # Try TED API as fallback if IMPIC returned no results
        if not results:
            try:
                ted_results = await ted_api.fetch_ted_contracts(
                    start_date=start_date,
                    end_date=end_date,
                    cpv_code=cpv_code,
                    page=page,
                    page_size=page_size,
                    timeout=self.timeout,
                )
                results.extend(ted_results)
                logger.info(
                    "Fetched contracts from TED API (fallback)",
                    extra={"count": len(results)},
                )
            except ExternalDataFetchError as e:
                logger.warning(
                    "TED API also unavailable",
                    extra={"error": str(e)},
                )

        # Apply value filters if specified
        if min_value is not None:
            results = [r for r in results if r.contract_value_eur >= min_value]
        if max_value is not None:
            results = [r for r in results if r.contract_value_eur <= max_value]

        # Story 6.9.5 AC7: Document limitations
        if not results:
            logger.warning(
                "No contracts found - Check date range and CPV code. "
                "IMPIC dataset covers 2012-2025, TED only includes EU-threshold contracts.",
                extra={
                    "start": str(start_date),
                    "end": str(end_date),
                    "cpv": cpv_code,
                },
            )

        logger.info(
            "Fetched public procurement contracts",
            extra={"record_count": len(results), "source": "IMPIC/TED"},
        )
        return results

    async def fetch_all_contracts(
        self,
        start_date: date,
        end_date: date,
        cpv_code: str | None = None,
    ) -> list[BaseGovContract]:
        """Fetch all contracts in date range (handles pagination).

        Args:
            start_date: Start of date range
            end_date: End of date range
            cpv_code: CPV code filter

        Returns:
            List of all contract records
        """
        all_results: list[BaseGovContract] = []
        page = 1
        page_size = 100

        while True:
            results = await self.fetch_contracts(
                start_date=start_date,
                end_date=end_date,
                cpv_code=cpv_code,
                page=page,
                page_size=page_size,
            )

            if not results:
                break

            all_results.extend(results)

            if len(results) < page_size:
                break

            page += 1

            # Safety limit
            if page > 100:
                logger.warning("Pagination limit reached (100 pages)")
                break

        return all_results

    async def fetch_construction_contracts_summary(
        self,
        year: int,
        month: int | None = None,
    ) -> dict:
        """Fetch summary of construction contracts for a period.

        Args:
            year: Year
            month: Month (optional, for monthly summary)

        Returns:
            Summary dict with total_contracts, total_value, avg_value
        """
        if month:
            start = date(year, month, 1)
            if month == 12:
                end = date(year + 1, 1, 1)
            else:
                end = date(year, month + 1, 1)
            end = end.replace(day=1) - timedelta(days=1)
        else:
            start = date(year, 1, 1)
            end = date(year, 12, 31)

        contracts = await self.fetch_all_contracts(
            start_date=start,
            end_date=end,
            cpv_code=self.CPV_CONSTRUCTION,
        )

        total_value = sum(c.contract_value_eur for c in contracts)
        avg_value = total_value / len(contracts) if contracts else 0

        return {
            "period_start": start,
            "period_end": end,
            "total_contracts": len(contracts),
            "total_value_eur": total_value,
            "avg_value_eur": avg_value,
            "data_source": "dados.gov.pt IMPIC (ALL Portuguese contracts)",
            "note": "Includes all contract values, not just EU-threshold",
        }

    # Legacy method - kept for backward compatibility
    async def _fetch_with_retry_legacy(
        self,
        params: dict,
    ) -> dict:
        """Deprecated: Fetch from Base.gov.pt API.

        Story 6.9.5: This method is deprecated. Base.gov.pt does NOT have a public API.
        Kept for backward compatibility - always returns empty response.

        Args:
            params: Query parameters (ignored)

        Returns:
            Empty dict (API does not exist)
        """
        logger.warning(
            "Deprecated _fetch_with_retry called - "
            "Base.gov.pt does NOT have a public API, use fetch_contracts() instead"
        )
        return {"items": []}

    def _parse_contracts(self, data: dict) -> list[BaseGovContract]:
        """Deprecated: Parse Base.gov.pt response.

        Story 6.9.5: This method is deprecated. Base.gov.pt does NOT have a public API.
        Kept for backward compatibility.

        Returns:
            Empty list
        """
        logger.warning("Deprecated _parse_contracts called - use parsers module functions instead")
        return []

    # Story 8.2: Backward compatibility wrappers for refactored methods
    def _parse_ted_notices(self, data: dict) -> list[BaseGovContract]:
        """Backward compatibility wrapper for parsers.parse_ted_notices().

        Story 8.2 Task 4: Delegate to standalone function in parsers module.

        Args:
            data: TED API response dict

        Returns:
            List of BaseGovContract records
        """
        return parsers.parse_ted_notices(data)

    async def _check_ocds_availability(self) -> dict | None:
        """Backward compatibility wrapper for ocds.check_ocds_availability().

        Story 8.2 Task 4: Delegate to standalone function in ocds module.

        Returns:
            Dataset metadata if available, None otherwise
        """
        return await ocds.check_ocds_availability(timeout=self.timeout)

    def _parse_ocds_data(
        self,
        ocds_data: dict | list,
        start_date: date,
        end_date: date,
        cpv_code: str | None = None,
    ) -> list[BaseGovContract]:
        """Backward compatibility wrapper for parsers.parse_ocds_data().

        Story 8.2 Task 4: Delegate to standalone function in parsers module.

        Args:
            ocds_data: OCDS JSON data
            start_date: Filter start date
            end_date: Filter end date
            cpv_code: CPV code filter

        Returns:
            List of BaseGovContract records
        """
        return parsers.parse_ocds_data(ocds_data, start_date, end_date, cpv_code)
