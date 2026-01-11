"""BPstat HTTP client with retry logic.

Story 6.9.3 AC2/AC3/AC7: Updated for new API structure
"""

from __future__ import annotations

import asyncio
import os
from datetime import date

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class BPstatHTTPClient:
    """HTTP client for BPstat API with retry logic."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize HTTP client.

        Args:
            api_key: Optional API key for BPstat API
        """
        self.base_url = "https://bpstat.bportugal.pt/api"
        self.api_key = api_key or settings.bpstat_api_key
        # Use test timeout in test environment
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        self.timeout = 1.0 if is_test else float(settings.external_data_timeout)

    async def fetch_observations(
        self,
        series_ids: list[str],
        start_date: date,
        end_date: date,
    ) -> dict:
        """Fetch observations from BPstat API with retry logic.

        Story 6.9.3 AC2/AC3/AC7: Updated for new API structure

        Args:
            series_ids: List of BPstat series identifiers (can fetch multiple in one request)
            start_date: Start of date range
            end_date: End of date range

        Returns:
            JSON response from API with observations data

        Raises:
            ExternalDataFetchError: If all retries fail
        """
        max_retries = settings.external_data_retry_attempts
        # Story 6.9.3 AC7: NFR1 exponential backoff at 2s/4s/8s intervals
        retry_delays = [2, 4, 8]

        # Story 6.9.3 AC2: New API endpoint structure
        # Old (broken): /data/v1/series/{id}/observations
        # New (working): /api/observations/?series_ids={ids}&lang=EN
        url = f"{self.base_url}/observations/"
        params = {
            "series_ids": ",".join(series_ids),
            "lang": "EN",
        }

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url, params=params, headers=headers)
                    response.raise_for_status()
                    return dict(response.json())

                except httpx.TimeoutException as e:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "BPstat API timeout, retrying",
                            extra={
                                "attempt": attempt + 1,
                                "delay": delay,
                                "series_ids": series_ids,
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="BPstat",
                            message=f"Timeout after {max_retries} attempts",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    # Retry on server errors (5xx) or rate limit (429)
                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        logger.warning(
                            "BPstat API error, retrying",
                            extra={
                                "attempt": attempt + 1,
                                "delay": delay,
                                "status": e.response.status_code,
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source="BPstat",
                            message=f"HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        raise ExternalDataFetchError(source="BPstat", message="Unexpected retry loop exit")
