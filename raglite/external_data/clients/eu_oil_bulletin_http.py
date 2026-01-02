"""EU Oil Bulletin HTTP client and caching utilities.

Story 6.9.4: XLSX download with caching for ~4MB historical file.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def fetch_xlsx_data(
    base_url: str,
    doc_id: str,
    filename: str,
    timeout: float,
) -> bytes:
    """Fetch historical oil bulletin XLSX file.

    Story 6.9.4 AC1/AC7: New XLSX download with retry logic

    Args:
        base_url: Base URL for EU Oil Bulletin
        doc_id: Document ID for XLSX file
        filename: Filename parameter for download
        timeout: HTTP timeout in seconds

    Returns:
        XLSX file content as bytes

    Raises:
        ExternalDataFetchError: If fetch fails
    """
    max_retries = settings.external_data_retry_attempts
    # Story 6.9.4 AC7: NFR1 exponential backoff at 2s/4s/8s intervals
    retry_delays = [2, 4, 8]

    # Story 6.9.4 AC1: New XLSX download URL
    url = f"{base_url}/document/download/{doc_id}"
    params = {"filename": filename}

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(max_retries):
            try:
                logger.info(
                    "Downloading EU Oil Bulletin XLSX",
                    extra={"url": url, "attempt": attempt + 1},
                )
                response = await client.get(url, params=params)
                response.raise_for_status()

                content = response.content
                # Verify it's actually an XLSX file (starts with PK - ZIP signature)
                if not content[:2] == b"PK":
                    raise ExternalDataFetchError(
                        source="EU_Oil_Bulletin",
                        message="Downloaded file is not a valid XLSX",
                    )

                logger.info(
                    "Downloaded EU Oil Bulletin XLSX",
                    extra={"size_bytes": len(content)},
                )
                return content

            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(
                        "EU Oil Bulletin timeout, retrying",
                        extra={"attempt": attempt + 1, "delay": delay},
                    )
                    await asyncio.sleep(delay)
                else:
                    raise ExternalDataFetchError(
                        source="EU_Oil_Bulletin",
                        message=f"Timeout after {max_retries} attempts",
                        original_error=e,
                    ) from e

            except httpx.HTTPStatusError as e:
                # Retry on server errors (5xx) or rate limit (429)
                should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                if attempt < max_retries - 1 and should_retry:
                    delay = retry_delays[attempt]
                    logger.warning(
                        "EU Oil Bulletin HTTP error, retrying",
                        extra={"attempt": attempt + 1, "status": e.response.status_code},
                    )
                    await asyncio.sleep(delay)
                else:
                    raise ExternalDataFetchError(
                        source="EU_Oil_Bulletin",
                        message=f"HTTP {e.response.status_code}",
                        original_error=e,
                    ) from e

    raise ExternalDataFetchError(
        source="EU_Oil_Bulletin",
        message="Unexpected retry loop exit",
    )


def get_cached_xlsx(cache_dir: Path, cache_ttl_hours: int) -> bytes | None:
    """Get cached XLSX file if valid.

    Story 6.9.4 AC5: Caching for large historical file

    Args:
        cache_dir: Cache directory path
        cache_ttl_hours: Cache TTL in hours

    Returns:
        Cached XLSX bytes or None if cache invalid/expired
    """
    cache_file = cache_dir / "eu_oil_bulletin_history.xlsx"

    if not cache_file.exists():
        return None

    # Check cache age
    mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
    age = datetime.now() - mtime

    if age > timedelta(hours=cache_ttl_hours):
        logger.info(
            "EU Oil Bulletin cache expired",
            extra={"age_hours": age.total_seconds() / 3600},
        )
        return None

    logger.info(
        "Using cached EU Oil Bulletin XLSX",
        extra={"cache_age_hours": age.total_seconds() / 3600},
    )
    return cache_file.read_bytes()


def save_to_cache(cache_dir: Path, content: bytes) -> None:
    """Save XLSX content to cache.

    Story 6.9.4 AC5: Caching for large historical file

    Args:
        cache_dir: Cache directory path
        content: XLSX file bytes
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "eu_oil_bulletin_history.xlsx"
    cache_file.write_bytes(content)
    logger.info("Saved EU Oil Bulletin XLSX to cache")
