"""Helper functions for external data refresh operations.

Contains retry logic and staleness detection utilities used by refresh operations.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Retry configuration (AC3)
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s


async def retry_with_backoff(
    coro_func: Any,
    source_name: str,
    *args: Any,
    **kwargs: Any,
) -> tuple[bool, int, str | None, Any]:
    """Execute coroutine with exponential backoff retry.

    AC3: Retry failed jobs with 3 attempts and exponential backoff (1s, 2s, 4s).

    Args:
        coro_func: Async function to execute
        source_name: Source name for logging
        *args: Positional arguments for coro_func
        **kwargs: Keyword arguments for coro_func

    Returns:
        Tuple of (success, attempts, error_message, result)
        result is the return value from coro_func on success, None on failure
    """
    max_attempts = settings.external_data_retry_attempts
    last_error: str | None = None

    for attempt in range(max_attempts):
        try:
            result = await coro_func(*args, **kwargs)
            return True, attempt + 1, None, result

        except ExternalDataFetchError as e:
            last_error = str(e)
            if attempt < max_attempts - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(
                    "External data fetch failed, retrying",
                    extra={
                        "source": source_name,
                        "attempt": attempt + 1,
                        "max_attempts": max_attempts,
                        "delay_seconds": delay,
                        "error": last_error,
                    },
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "External data fetch failed after all retries",
                    extra={
                        "source": source_name,
                        "attempts": max_attempts,
                        "error": last_error,
                    },
                )

        except Exception as e:
            last_error = f"Unexpected error: {type(e).__name__}: {str(e)}"
            logger.error(
                "Unexpected error during external data refresh",
                extra={
                    "source": source_name,
                    "attempt": attempt + 1,
                    "error": last_error,
                },
            )
            if attempt < max_attempts - 1:
                delay = RETRY_DELAYS[attempt]
                await asyncio.sleep(delay)

    return False, max_attempts, last_error, None


def check_staleness(source_name: str, last_refresh_at: datetime | None) -> bool:
    """Check if external data source is stale and log warning if so.

    AC5: Alert if external data >30 days old (WARNING level log).

    Args:
        source_name: Name of the data source
        last_refresh_at: Last refresh timestamp (UTC)

    Returns:
        True if data is stale (>30 days old), False otherwise
    """
    if last_refresh_at is None:
        logger.warning(
            "External data source has never been refreshed",
            extra={"source": source_name, "staleness_days": "never"},
        )
        return True

    # Ensure timezone-aware comparison
    if last_refresh_at.tzinfo is None:
        last_refresh_at = last_refresh_at.replace(tzinfo=UTC)

    now = datetime.now(UTC)
    days_old = (now - last_refresh_at).days

    if days_old > settings.external_data_stale_days:
        logger.warning(
            "External data source is stale",
            extra={
                "source": source_name,
                "staleness_days": days_old,
                "threshold_days": settings.external_data_stale_days,
                "last_refresh": last_refresh_at.isoformat(),
            },
        )
        return True

    return False
