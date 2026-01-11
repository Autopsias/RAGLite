"""HTTP client utilities for commodities data fetching.

Story 6.1: Tier 1 External Data Source Integration
Extracted from commodities.py for better modularity.
"""

from __future__ import annotations

import asyncio
import os

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def fetch_with_retry(url: str, timeout: float) -> dict:
    """Fetch data from URL with retry logic.

    Args:
        url: API URL
        timeout: Request timeout in seconds

    Returns:
        JSON response

    Raises:
        ExternalDataFetchError: If all retries fail
    """
    max_retries = settings.external_data_retry_attempts
    retry_delays = [2, 4, 8]  # NFR1: exponential backoff at 2s/4s/8s intervals

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(max_retries):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return dict(response.json())

            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(
                        "Commodities API timeout, retrying",
                        extra={"attempt": attempt + 1, "delay": delay},
                    )
                    await asyncio.sleep(delay)
                else:
                    raise ExternalDataFetchError(
                        source="Commodities",
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
                        source="Commodities",
                        message=f"HTTP {e.response.status_code}",
                        original_error=e,
                    ) from e

    raise ExternalDataFetchError(source="Commodities", message="Unexpected retry loop exit")


def get_timeout() -> float:
    """Get appropriate timeout for commodities API requests.

    Returns:
        Timeout in seconds (10s for tests, configured value for production)
    """
    is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
    return 10.0 if is_test else float(settings.external_data_timeout)
