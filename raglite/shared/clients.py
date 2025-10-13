"""API client factories for external services.

Provides singleton client instances for Qdrant and Claude API.
"""

import time

from anthropic import Anthropic
from qdrant_client import QdrantClient

from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


# Module-level Qdrant client (singleton pattern with connection pooling)
_qdrant_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """Lazy-load Qdrant client (singleton pattern with connection pooling and retry logic).

    Creates client on first call and caches it for reuse. Provides connection
    pooling for efficient resource management across multiple storage operations.
    Implements exponential backoff retry logic for transient connection failures.

    Returns:
        Cached QdrantClient instance connected to local or cloud Qdrant

    Raises:
        ConnectionError: If Qdrant connection fails after all retries

    Note:
        Connection parameters:
        - Host: settings.qdrant_host (default: localhost)
        - Port: settings.qdrant_port (default: 6333)
        - Timeout: 30 seconds for operation completion
        - Retry policy: 3 attempts with exponential backoff (1s, 2s, 4s)

    Example:
        >>> client = get_qdrant_client()
        >>> client.get_collections()
        >>> # Subsequent calls return same cached instance
        >>> same_client = get_qdrant_client()
        >>> assert client is same_client
    """
    global _qdrant_client

    if _qdrant_client is None:
        logger.info(
            "Connecting to Qdrant",
            extra={"host": settings.qdrant_host, "port": settings.qdrant_port},
        )

        # Retry configuration
        max_retries = 3
        retry_delays = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s

        for attempt in range(max_retries):
            try:
                _qdrant_client = QdrantClient(
                    host=settings.qdrant_host, port=settings.qdrant_port, timeout=30
                )
                logger.info(
                    "Qdrant client connected successfully",
                    extra={
                        "host": settings.qdrant_host,
                        "port": settings.qdrant_port,
                        "attempt": attempt + 1,
                    },
                )
                break  # Success - exit retry loop
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(
                        f"Qdrant connection failed (attempt {attempt + 1}/{max_retries}), retrying in {delay}s",
                        extra={
                            "host": settings.qdrant_host,
                            "port": settings.qdrant_port,
                            "attempt": attempt + 1,
                            "delay_seconds": delay,
                            "error": str(e),
                        },
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Qdrant connection failed after {max_retries} attempts",
                        extra={
                            "host": settings.qdrant_host,
                            "port": settings.qdrant_port,
                            "error": str(e),
                        },
                        exc_info=True,
                    )
                    raise ConnectionError(
                        f"Failed to connect to Qdrant after {max_retries} attempts: {e}"
                    ) from e

    # Type safety: _qdrant_client is guaranteed to be initialized after the retry loop
    if _qdrant_client is None:
        raise ConnectionError("Qdrant client failed to initialize after successful retry loop")
    return _qdrant_client


def get_claude_client() -> Anthropic:
    """Factory function for Anthropic Claude API client.

    Returns:
        Configured Anthropic client instance

    Raises:
        ValueError: If ANTHROPIC_API_KEY not set in environment

    Example:
        >>> client = get_claude_client()
        >>> response = client.messages.create(...)
    """
    if (
        not settings.anthropic_api_key
        or settings.anthropic_api_key == "your_anthropic_api_key_here"
        or settings.anthropic_api_key == ""
    ):
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable not set or using placeholder value. "
            "Get your API key from https://console.anthropic.com/"
        )

    client = Anthropic(api_key=settings.anthropic_api_key)
    logger.info("Claude API client initialized")
    return client
