"""Eurostat API fetch methods with retry logic.

Story 8.2 Task 6: Eurostat client refactoring
"""

import gzip
import json

from raglite.external_data.clients.base import BaseExternalClient
from raglite.external_data.clients.eurostat.config import EUROSTAT_API_BASE
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Shared client instance for retry infrastructure
_client = BaseExternalClient()


async def fetch_with_retry(url: str, params: dict | None, timeout: float) -> dict:
    """Fetch data from Eurostat API with retry logic.

    Args:
        url: API URL
        params: Query parameters
        timeout: Request timeout in seconds

    Returns:
        JSON response

    Raises:
        ExternalDataFetchError: If all retries fail
    """
    # Use base class retry infrastructure
    _client.timeout = timeout
    response = await _client._fetch_with_retry(url, params=params)

    # Handle gzip-compressed responses (some Eurostat datasets return gzipped JSON)
    content = response.content
    if content[:2] == b"\x1f\x8b":  # Gzip magic number
        content = gzip.decompress(content)
        return dict(json.loads(content))

    return dict(response.json())


async def fetch_eurostat_data(dataset: str, filters: dict[str, str], timeout: float) -> dict:
    """Fetch data from Eurostat SDMX API.

    Args:
        dataset: Dataset code (e.g., "nrg_pc_204")
        filters: Filter parameters (geo, consband, unit, etc.)
        timeout: Request timeout in seconds

    Returns:
        JSON-stat response
    """
    # Build filter string for SDMX query
    filter_parts = []
    for key, value in filters.items():
        filter_parts.append(f"{key}={value}")

    filter_str = "&".join(filter_parts) if filter_parts else ""

    url = f"{EUROSTAT_API_BASE}/data/{dataset}"
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

    return await fetch_with_retry(url, params, timeout)
