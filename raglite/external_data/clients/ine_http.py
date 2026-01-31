"""INE API HTTP retry logic.

Extracted from ine.py for better modularity (Story 8.3).
"""

from __future__ import annotations

import asyncio
from datetime import date

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# NFR1: exponential backoff at 2s/4s/8s intervals
RETRY_DELAYS = [2, 4, 8]


def _parse_response(json_data: list | dict) -> dict:
    """Parse INE API response and check for errors."""
    if isinstance(json_data, list) and len(json_data) > 0:
        result = json_data[0]
        if "Sucesso" in result:
            falso = result.get("Sucesso", {}).get("Falso", [])
            if falso:
                error_msg = falso[0].get("Msg", "Unknown API error")
                raise ExternalDataFetchError(source="INE", message=f"API error: {error_msg}")
        return dict(result)
    return dict(json_data) if isinstance(json_data, dict) else {}


async def _handle_timeout(
    attempt: int, max_retries: int, indicator: str, error: httpx.TimeoutException
) -> None:
    """Handle timeout with retry logic."""
    if attempt < max_retries - 1:
        delay = RETRY_DELAYS[attempt]
        logger.warning(
            "INE API timeout, retrying",
            extra={"attempt": attempt + 1, "delay": delay, "indicator": indicator},
        )
        await asyncio.sleep(delay)
    else:
        logger.error(
            "INE API timeout after retries", extra={"indicator": indicator, "error": str(error)}
        )
        raise ExternalDataFetchError(
            source="INE", message=f"Timeout after {max_retries} attempts", original_error=error
        ) from error


async def _handle_http_error(
    attempt: int, max_retries: int, indicator: str, error: httpx.HTTPStatusError
) -> bool:
    """Handle HTTP error with retry logic. Returns True if should continue loop."""
    should_retry = error.response.status_code >= 500 or error.response.status_code == 429
    if attempt < max_retries - 1 and should_retry:
        delay = RETRY_DELAYS[attempt]
        logger.warning(
            "INE API error, retrying",
            extra={"attempt": attempt + 1, "delay": delay, "status": error.response.status_code},
        )
        await asyncio.sleep(delay)
        return True

    logger.error(
        "INE API request failed",
        extra={"indicator": indicator, "status": error.response.status_code},
    )
    raise ExternalDataFetchError(
        source="INE", message=f"HTTP {error.response.status_code}", original_error=error
    ) from error


async def fetch_with_retry(
    base_url: str,
    indicator: str,
    start_date: date,
    end_date: date,
    timeout: float,
    api_key: str | None = None,
) -> dict:
    """Fetch data from INE API with retry logic.

    Args:
        base_url: INE API base URL
        indicator: INE indicator code (7 digits, e.g., '0008074')
        start_date: Start of date range
        end_date: End of date range
        timeout: HTTP timeout in seconds
        api_key: Optional API key for authentication

    Returns:
        JSON response from API

    Raises:
        ExternalDataFetchError: If all retries fail
    """
    max_retries = settings.external_data_retry_attempts

    params = {
        "op": "2",
        "varcd": indicator,
        "Dim1": "T",
        "lang": "PT",
    }
    # Add date range parameters if provided (INE API format)
    if start_date:
        params["datIni"] = start_date.strftime("%Y-%m-%d")
    if end_date:
        params["datFim"] = end_date.strftime("%Y-%m-%d")

    headers = {
        "Accept": "application/json",
        "User-Agent": "RAGLite/1.0 (https://github.com/raglite)",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(max_retries):
            try:
                response = await client.get(base_url, params=params, headers=headers)
                response.raise_for_status()
                return _parse_response(response.json())

            except httpx.TimeoutException as e:
                await _handle_timeout(attempt, max_retries, indicator, e)

            except httpx.HTTPStatusError as e:
                await _handle_http_error(attempt, max_retries, indicator, e)

    raise ExternalDataFetchError(source="INE", message="Unexpected retry loop exit")
