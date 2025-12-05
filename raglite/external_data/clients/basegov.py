"""Base.gov.pt (Portuguese Public Procurement) client.

Story 6.1: Tier 1 External Data Source Integration

Fetches Portuguese public works contract data:
- Contract values
- Contracting entities
- Contractors
- CPV codes

Data Source: https://www.base.gov.pt/Base4/pt/
"""

from __future__ import annotations

import asyncio
import os
from datetime import date, timedelta

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import BaseGovContract
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Base.gov.pt API
BASEGOV_API_BASE = "https://www.base.gov.pt/Base4/pt/pesquisa"


class BaseGovClient:
    """Client for Base.gov.pt public procurement data.

    Base.gov.pt is the Portuguese public procurement portal containing
    all public works contracts.

    Example:
        >>> client = BaseGovClient()
        >>> contracts = await client.fetch_contracts(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 3, 31),
        ...     cpv_code="45000000"  # Construction works
        ... )
    """

    # CPV codes for construction-related contracts
    CPV_CONSTRUCTION = "45000000"  # Construction works
    CPV_BUILDING = "45210000"  # Building construction
    CPV_CIVIL_ENGINEERING = "45220000"  # Civil engineering
    CPV_ROAD = "45233000"  # Highway construction

    def __init__(self) -> None:
        self.base_url = BASEGOV_API_BASE
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 1.0 if is_test else float(settings.external_data_timeout)

    async def _fetch_with_retry(
        self,
        params: dict,
    ) -> dict:
        """Fetch data from Base.gov.pt with retry logic.

        Args:
            params: Query parameters

        Returns:
            JSON response

        Raises:
            ExternalDataFetchError: If all retries fail
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [1, 2, 4]

        url = f"{self.base_url}/resultados"

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
                            "Base.gov.pt timeout, retrying",
                            extra={"attempt": attempt + 1, "delay": delay},
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="BaseGov",
                            message="Timeout after retries",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    # Retry on server errors (5xx) or rate limit (429)
                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="BaseGov",
                            message=f"HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        raise ExternalDataFetchError(source="BaseGov", message="Unexpected retry loop exit")

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

        Args:
            start_date: Start of date range (publication date)
            end_date: End of date range
            cpv_code: CPV code filter (default: construction works)
            min_value: Minimum contract value in EUR
            max_value: Maximum contract value in EUR
            page: Page number for pagination
            page_size: Results per page

        Returns:
            List of contract records
        """
        if cpv_code is None:
            cpv_code = self.CPV_CONSTRUCTION

        logger.info(
            "Fetching Base.gov.pt contracts",
            extra={
                "start": str(start_date),
                "end": str(end_date),
                "cpv": cpv_code,
            },
        )

        params = {
            "tipo": "contratos",
            "dtInicio": start_date.strftime("%Y-%m-%d"),
            "dtFim": end_date.strftime("%Y-%m-%d"),
            "cpv": cpv_code,
            "pagina": page,
            "tamanhoPagina": page_size,
        }

        if min_value is not None:
            params["precoMin"] = str(min_value)
        if max_value is not None:
            params["precoMax"] = str(max_value)

        data = await self._fetch_with_retry(params)
        results = self._parse_contracts(data)

        logger.info(
            "Fetched Base.gov.pt contracts",
            extra={"record_count": len(results)},
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
        all_results = []
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
                logger.warning("Base.gov.pt pagination limit reached (100 pages)")
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
        }

    def _parse_contracts(self, data: dict) -> list[BaseGovContract]:
        """Parse Base.gov.pt contract response.

        Args:
            data: API response

        Returns:
            List of contract records
        """
        results = []

        for item in data.get("items", data.get("contratos", [])):
            try:
                pub_date_str = item.get("dataPublicacao", item.get("data_publicacao"))
                if not pub_date_str:
                    continue

                # Parse date (format varies)
                if "T" in pub_date_str:
                    pub_date = date.fromisoformat(pub_date_str.split("T")[0])
                else:
                    pub_date = date.fromisoformat(pub_date_str)

                contract_value = item.get("precoContratual", item.get("valor", 0))
                if isinstance(contract_value, str):
                    contract_value = float(contract_value.replace(",", ".").replace(" ", ""))

                results.append(
                    BaseGovContract(
                        publication_date=pub_date,
                        contract_id=str(item.get("id", item.get("idContrato", ""))),
                        description=item.get("objectoContrato", item.get("descricao")),
                        contract_value_eur=float(contract_value),
                        contracting_entity=item.get("entidadeAdjudicante", item.get("adjudicante")),
                        contractor=item.get("adjudicatario", item.get("contratado")),
                        cpv_code=item.get("cpv"),
                        execution_location=item.get("localizacao"),
                    )
                )
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(
                    "Failed to parse Base.gov.pt contract",
                    extra={"error": str(e)},
                )
                continue

        return results
