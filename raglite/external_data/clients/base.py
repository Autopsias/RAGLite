"""Base class for external data API clients.

Provides common functionality:
- Retry logic with exponential backoff
- HTTP error handling
- Structured logging
- Response caching infrastructure

Story 8.2 Task 2: Extract shared patterns from BaseGov, ECB, Eurostat clients.
"""

from __future__ import annotations

import asyncio

# Removed ABC - not needed without abstract methods
from typing import Any

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

# NFR1: Exponential backoff retry delays (seconds)
RETRY_DELAYS = [2, 4, 8]


class BaseExternalClient:
    """Abstract base class for external data API clients.

    Provides shared functionality for all external data API clients:
    - Retry logic with exponential backoff (NFR1)
    - HTTP error handling
    - Structured logging
    - Timeout configuration

    Subclasses should:
    - Call super().__init__() in their __init__
    - Use _fetch_with_retry() for all HTTP requests
    - Override _init_cache() if custom caching is needed

    Example:
        >>> class MyClient(BaseExternalClient):
        ...     def __init__(self):
        ...         super().__init__()
        ...
        ...     async def fetch_data(self, url: str) -> dict:
        ...         response = await self._fetch_with_retry(url)
        ...         return response.json()
    """

    def __init__(self, timeout: float | None = None) -> None:
        """Initialize base client.

        Args:
            timeout: Request timeout in seconds (default: from settings)
        """
        self.timeout = timeout if timeout is not None else float(settings.external_data_timeout)
        self.logger = get_logger(self.__class__.__name__)
        self._init_cache()

    def _init_cache(self) -> None:
        """Initialize caching infrastructure.

        Override in subclass if custom caching is needed.
        Default implementation does nothing (stateless client).
        """
        pass

    async def _fetch_with_retry(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Fetch with exponential backoff retry logic.

        Implements NFR1: Retry logic for external API calls with exponential backoff.

        Retry conditions:
        - Timeout errors (all attempts)
        - HTTP 5xx errors (server errors)
        - HTTP 429 (rate limiting)

        Non-retry conditions:
        - HTTP 4xx errors (except 429) - client errors are not retryable

        Args:
            url: Request URL
            params: Query parameters for GET requests
            method: HTTP method ("GET" or "POST")
            json_body: JSON body for POST requests
            headers: Request headers

        Returns:
            httpx.Response object

        Raises:
            ExternalDataFetchError: If all retries fail
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = RETRY_DELAYS

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    if method == "GET":
                        response = await client.get(url, params=params, headers=headers)
                    elif method == "POST":
                        response = await client.post(url, json=json_body, headers=headers)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")

                    response.raise_for_status()
                    return response

                except httpx.TimeoutException as e:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        self.logger.warning(
                            "API timeout, retrying",
                            extra={
                                "attempt": attempt + 1,
                                "delay": delay,
                                "url": url,
                                "method": method,
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source=self.__class__.__name__,
                            message=f"Timeout after {max_retries} attempts for {url}",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    # Retry on server errors (5xx) or rate limiting (429)
                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        self.logger.warning(
                            "API error, retrying",
                            extra={
                                "attempt": attempt + 1,
                                "delay": delay,
                                "status_code": e.response.status_code,
                                "url": url,
                                "method": method,
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source=self.__class__.__name__,
                            message=f"HTTP {e.response.status_code} for {url}",
                            original_error=e,
                        ) from e

                except httpx.RequestError as e:
                    # Network errors, connection errors, etc.
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        self.logger.warning(
                            "Request error, retrying",
                            extra={
                                "attempt": attempt + 1,
                                "delay": delay,
                                "error": str(e),
                                "url": url,
                                "method": method,
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source=self.__class__.__name__,
                            message=f"Request failed after {max_retries} attempts: {e}",
                            original_error=e,
                        ) from e

        # Should never reach here
        raise ExternalDataFetchError(
            source=self.__class__.__name__,
            message="Unexpected retry loop exit",
        )
