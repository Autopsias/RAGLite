"""IMPIC XLSX client module for BaseGov.

Story 8.2 Task 4: Extract IMPIC XLSX logic from basegov.py
Handles fetching and caching of IMPIC yearly contract files from dados.gov.pt.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

from raglite.external_data.clients.base import RETRY_DELAYS
from raglite.external_data.clients.basegov.config import (
    CACHE_DIR,
    CACHE_TTL_HOURS,
    DADOS_GOV_API_BASE,
    IMPIC_CONTRACTS_DATASET,
)
from raglite.external_data.clients.basegov.parsers import parse_impic_xlsx
from raglite.external_data.models import BaseGovContract
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def get_impic_resource_urls(timeout: float = 30.0) -> dict[int, str]:
    """Get URLs for IMPIC yearly XLSX files.

    Story 6.9.5: Primary data source - dados.gov.pt IMPIC dataset

    Args:
        timeout: Request timeout in seconds

    Returns:
        Dict mapping year to XLSX URL, e.g. {2024: "https://...contratos2024.xlsx"}
    """
    url = f"{DADOS_GOV_API_BASE}/datasets/{IMPIC_CONTRACTS_DATASET}/"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            year_urls: dict[int, str] = {}
            for resource in data.get("resources", []):
                resource_url = resource.get("url", "")
                title = resource.get("title", "")

                # Extract year from filename like "contratos2024.xlsx"
                if title.startswith("contratos") and title.endswith(".xlsx"):
                    try:
                        year = int(title.replace("contratos", "").replace(".xlsx", ""))
                        year_urls[year] = resource_url
                    except ValueError:
                        continue

            logger.info(
                "Found IMPIC XLSX resources",
                extra={"years": sorted(year_urls.keys()), "count": len(year_urls)},
            )
            return year_urls

    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning(
            "Failed to get IMPIC resource URLs",
            extra={"error": str(e)},
        )
        return {}


def get_cached_impic_xlsx(year: int, cache_dir: Path = CACHE_DIR) -> bytes | None:
    """Get cached IMPIC XLSX file if valid.

    Args:
        year: Contract year
        cache_dir: Cache directory path

    Returns:
        XLSX bytes if cached and valid, None otherwise
    """
    cache_file = cache_dir / f"impic_contratos{year}.xlsx"

    if not cache_file.exists():
        return None

    # Check cache age
    age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
    if age > timedelta(hours=CACHE_TTL_HOURS):
        logger.debug(f"IMPIC cache expired for year {year}")
        return None

    return cache_file.read_bytes()


def save_impic_xlsx_cache(year: int, content: bytes, cache_dir: Path = CACHE_DIR) -> None:
    """Save IMPIC XLSX to cache.

    Args:
        year: Contract year
        content: XLSX bytes
        cache_dir: Cache directory path
    """
    try:
        cache_file = cache_dir / f"impic_contratos{year}.xlsx"
        cache_file.write_bytes(content)
        logger.debug(f"Cached IMPIC XLSX for year {year}")
    except OSError as e:
        logger.warning(f"Failed to cache IMPIC XLSX: {e}")


async def fetch_impic_xlsx(year: int, url: str, cache_dir: Path = CACHE_DIR) -> bytes | None:
    """Download IMPIC XLSX file for a specific year.

    Story 6.9.5: Fetches yearly contract data from dados.gov.pt

    Args:
        year: Contract year
        url: URL to XLSX file
        cache_dir: Cache directory path

    Returns:
        XLSX bytes or None if fetch failed
    """
    # Check cache first
    cached = get_cached_impic_xlsx(year, cache_dir)
    if cached:
        logger.info(f"Using cached IMPIC XLSX for {year}")
        return cached

    max_retries = settings.external_data_retry_attempts

    async with httpx.AsyncClient(timeout=60.0) as client:  # Larger timeout for XLSX
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Downloading IMPIC XLSX for {year}",
                    extra={"url": url[:80], "attempt": attempt + 1},
                )

                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                content = response.content
                save_impic_xlsx_cache(year, content, cache_dir)
                return content

            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                else:
                    logger.warning(f"IMPIC XLSX download timeout for {year}")
                    return None

            except httpx.HTTPStatusError as e:
                if attempt < max_retries - 1 and e.response.status_code >= 500:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                else:
                    logger.warning(
                        f"IMPIC XLSX download failed for {year}: HTTP {e.response.status_code}"
                    )
                    return None

    return None


async def fetch_impic_contracts(
    start_date: date,
    end_date: date,
    cpv_code: str | None = None,
    timeout: float = 30.0,
    cache_dir: Path = CACHE_DIR,
) -> list[BaseGovContract]:
    """Fetch contracts from dados.gov.pt IMPIC XLSX dataset.

    Story 6.9.5: Primary data source for Portuguese public contracts

    Args:
        start_date: Start of date range
        end_date: End of date range
        cpv_code: CPV code filter
        timeout: Request timeout for metadata fetch
        cache_dir: Cache directory path

    Returns:
        List of contracts from IMPIC dataset
    """
    # Get available yearly files
    year_urls = await get_impic_resource_urls(timeout)

    if not year_urls:
        logger.warning("IMPIC dataset not available")
        return []

    # Determine which years to fetch
    years_needed = set(range(start_date.year, end_date.year + 1))
    years_available = set(year_urls.keys())
    years_to_fetch = years_needed & years_available

    if not years_to_fetch:
        logger.warning(
            "No IMPIC data for requested period",
            extra={
                "years_needed": list(years_needed),
                "years_available": list(years_available),
            },
        )
        return []

    results: list[BaseGovContract] = []

    for year in sorted(years_to_fetch):
        url = year_urls[year]
        content = await fetch_impic_xlsx(year, url, cache_dir)

        if content:
            parsed = parse_impic_xlsx(content, start_date, end_date, cpv_code)
            results.extend(parsed)
            logger.info(f"Parsed {len(parsed)} contracts from IMPIC {year}")

    return results
