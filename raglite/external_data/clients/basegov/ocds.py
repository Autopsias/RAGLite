"""OCDS client module for BaseGov.

Story 8.2 Task 4: Extract OCDS logic from basegov.py
Handles interaction with dados.gov.pt OCDS dataset (deprecated, kept for compatibility).
"""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from raglite.external_data.clients.basegov.config import DADOS_GOV_API_BASE, OCDS_DATASET_ID
from raglite.external_data.clients.basegov.parsers import parse_ocds_data
from raglite.external_data.models import BaseGovContract
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def check_ocds_availability(timeout: float = 30.0) -> dict[Any, Any] | None:
    """Check if dados.gov.pt OCDS dataset has resources.

    Story 6.9.5 AC1/AC2: Check OCDS dataset availability

    Args:
        timeout: Request timeout in seconds

    Returns:
        Dataset metadata if resources available, None otherwise
    """
    url = f"{DADOS_GOV_API_BASE}/datasets/{OCDS_DATASET_ID}/"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            data: dict[Any, Any] = response.json()

            resources = data.get("resources", [])
            if not resources:
                logger.warning(
                    "dados.gov.pt OCDS dataset has no resources",
                    extra={"dataset_id": OCDS_DATASET_ID},
                )
                return None

            return data

    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning(
            "Failed to check dados.gov.pt OCDS dataset",
            extra={"error": str(e)},
        )
        return None


async def fetch_ocds_contracts(
    start_date: date,
    end_date: date,
    cpv_code: str | None = None,
    timeout: float = 30.0,
) -> list[BaseGovContract]:
    """Fetch contracts from dados.gov.pt OCDS dataset.

    Story 6.9.5 AC2/AC3: OCDS data fetching (when available)

    Currently returns empty list as dataset has no resources.
    Implementation ready for when IMPIC restores the data.

    Args:
        start_date: Start of date range
        end_date: End of date range
        cpv_code: CPV code filter
        timeout: Request timeout in seconds

    Returns:
        List of contracts (empty if dataset unavailable)
    """
    dataset = await check_ocds_availability(timeout)

    if dataset is None:
        return []

    results: list[BaseGovContract] = []

    # When dataset becomes available, fetch and parse OCDS JSON/CSV
    for resource in dataset.get("resources", []):
        resource_format = resource.get("format", "").lower()
        resource_url = resource.get("url")

        if not resource_url:
            continue

        # Prefer JSON format
        if resource_format == "json":
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(resource_url)
                    response.raise_for_status()
                    ocds_data = response.json()

                    parsed = parse_ocds_data(ocds_data, start_date, end_date, cpv_code)
                    results.extend(parsed)
                    break  # Got data from JSON, no need for CSV

            except (httpx.HTTPError, ValueError) as e:
                logger.warning(
                    "Failed to fetch OCDS JSON",
                    extra={"url": resource_url, "error": str(e)},
                )

    return results
