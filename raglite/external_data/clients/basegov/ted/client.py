"""TED API client core functionality.

Story 8.2 Task 4: Extract HTTP client and retry logic from ted_api.
"""

from __future__ import annotations

import asyncio
from datetime import date

import httpx

from raglite.external_data.clients.basegov.config import TED_API_BASE
from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def fetch_ted_notices(
    start_date: date,
    end_date: date,
    cpv_code: str | None = None,
    page: int = 1,
    limit: int = 100,
    timeout: float = 30.0,
) -> dict:
    """Fetch notices from TED API v3.

    Story 6.9.5 AC2/AC6: TED API for EU-threshold contracts

    Args:
        start_date: Start of date range
        end_date: End of date range
        cpv_code: CPV code filter
        page: Page number
        limit: Results per page
        timeout: Request timeout in seconds

    Returns:
        TED API response dict

    Raises:
        ExternalDataFetchError: If all retries fail
    """
    max_retries = settings.external_data_retry_attempts
    # Story 6.9.5 AC8: NFR1 exponential backoff at 2s/4s/8s intervals
    retry_delays = [2, 4, 8]

    url = f"{TED_API_BASE}/notices/search"

    # Build TED query
    # TED uses its own query language
    query_parts = [
        "(place-of-performance = PT)",  # Portugal
        f"(publication-date >= {start_date.isoformat()})",
        f"(publication-date <= {end_date.isoformat()})",
    ]

    if cpv_code:
        query_parts.append(f"(cpv = {cpv_code}*)")

    query = " AND ".join(query_parts)

    payload = {
        "query": query,
        "fields": [
            "publication-number",
            "publication-date",
            "notice-title",
            "buyer-name",
            "winner-name",
            "total-value",
            "cpv",
            "place-of-performance",
            "contract-nature",
        ],
        "page": page,
        "limit": limit,
        "scope": "ALL",  # Include historical and active
        "onlyLatestVersions": True,
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(max_retries):
            try:
                logger.info(
                    "Fetching TED notices",
                    extra={
                        "query": query[:100],
                        "page": page,
                        "attempt": attempt + 1,
                    },
                )

                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                return dict(response.json())  # type: ignore[no-any-return]

            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(
                        "TED API timeout, retrying",
                        extra={"attempt": attempt + 1, "delay": delay},
                    )
                    await asyncio.sleep(delay)
                else:
                    raise ExternalDataFetchError(
                        source="BaseGov_TED",
                        message=f"TED API timeout after {max_retries} attempts",
                        original_error=e,
                    ) from e

            except httpx.HTTPStatusError as e:
                # Retry on server errors (5xx) or rate limit (429)
                should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                if attempt < max_retries - 1 and should_retry:
                    delay = retry_delays[attempt]
                    logger.warning(
                        "TED API error, retrying",
                        extra={
                            "attempt": attempt + 1,
                            "status": e.response.status_code,
                        },
                    )
                    await asyncio.sleep(delay)
                else:
                    raise ExternalDataFetchError(
                        source="BaseGov_TED",
                        message=f"TED API HTTP {e.response.status_code}",
                        original_error=e,
                    ) from e

    raise ExternalDataFetchError(
        source="BaseGov_TED",
        message="Unexpected retry loop exit",
    )
