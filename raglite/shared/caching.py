"""Local file caching for external data clients.

Story 6.10.3: Provides TTL-based file caching to improve external API reliability.
Only 3/11 external clients had caching. This module provides a reusable cache
that can be integrated into any client.
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class ExternalDataCache:
    """Simple file-based cache with TTL for external API responses.

    Usage:
        cache = ExternalDataCache(ttl_hours=24)

        # Try cache first
        cached = cache.get("ine_building_permits_2024")
        if cached:
            return cached

        # Fetch from API
        data = await fetch_from_api()
        cache.set("ine_building_permits_2024", data)
        return data
    """

    CACHE_DIR = Path(".cache/external_data")
    DEFAULT_TTL_HOURS = 24

    def __init__(self, ttl_hours: int = DEFAULT_TTL_HOURS):
        """Initialize cache with configurable TTL.

        Args:
            ttl_hours: Time-to-live in hours (default: 24)
        """
        self.ttl_hours = ttl_hours
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """Generate safe filename from cache key."""
        # Hash long keys to avoid filesystem issues (not used for security)
        safe_key = (
            hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()[:16]
            + "_"
            + key[:50].replace("/", "_")
        )
        return self.CACHE_DIR / f"{safe_key}.json"

    def get(self, key: str) -> Any | None:
        """Get cached data if valid (within TTL).

        Args:
            key: Cache key

        Returns:
            Cached payload or None if expired/missing
        """
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            data = json.loads(cache_path.read_text())
            cached_at = datetime.fromisoformat(data["cached_at"])

            if datetime.now() - cached_at > timedelta(hours=self.ttl_hours):
                logger.debug(f"Cache expired for key: {key}")
                return None

            logger.debug(f"Cache hit for key: {key}")
            return data["payload"]

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Invalid cache file for key {key}: {e}")
            return None

    def set(self, key: str, payload: Any) -> None:
        """Cache data with timestamp.

        Args:
            key: Cache key
            payload: Data to cache (must be JSON-serializable)
        """
        cache_path = self._get_cache_path(key)
        try:
            cache_path.write_text(
                json.dumps(
                    {"cached_at": datetime.now().isoformat(), "payload": payload}, default=str
                )
            )
            logger.debug(f"Cached data for key: {key}")
        except (TypeError, OSError) as e:
            logger.warning(f"Failed to cache data for key {key}: {e}")

    def clear(self, key: str | None = None) -> int:
        """Clear cache entries.

        Args:
            key: Specific key to clear, or None to clear all

        Returns:
            Number of entries cleared
        """
        if key:
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
                return 1
            return 0

        count = 0
        for cache_file in self.CACHE_DIR.glob("*.json"):
            cache_file.unlink()
            count += 1
        return count
