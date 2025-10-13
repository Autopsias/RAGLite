"""API client factories for external services.

Provides singleton client instances for Qdrant and Claude API.
"""

import time

from anthropic import Anthropic
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


# Module-level singletons (connection pooling and model caching)
_qdrant_client: QdrantClient | None = None
_embedding_model: SentenceTransformer | None = None


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


def get_embedding_model() -> SentenceTransformer:
    """Lazy-load Fin-E5 embedding model (singleton pattern).

    Loads intfloat/e5-large-v2 model on first call and caches it for reuse.
    Model is downloaded once and cached locally by sentence-transformers.

    Returns:
        SentenceTransformer: Cached Fin-E5 model instance (1024 dimensions)

    Raises:
        RuntimeError: If model loading fails

    Note:
        Model specifications:
        - Name: intfloat/e5-large-v2 (marketed as "Fin-E5")
        - Dimensions: 1024
        - Domain: Financial text optimization
        - Week 0 validation: 0.84 avg similarity score, 71.05% NDCG@10

    Example:
        >>> model = get_embedding_model()
        >>> embedding = model.encode(["financial query text"])[0]
        >>> len(embedding)
        1024
    """
    global _embedding_model

    if _embedding_model is None:
        logger.info("Loading Fin-E5 embedding model", extra={"model": "intfloat/e5-large-v2"})

        try:
            _embedding_model = SentenceTransformer("intfloat/e5-large-v2")
            dimensions = _embedding_model.get_sentence_embedding_dimension()

            logger.info(
                "Fin-E5 model loaded successfully",
                extra={"model": "intfloat/e5-large-v2", "dimensions": dimensions},
            )
        except Exception as e:
            error_msg = f"Failed to load Fin-E5 model: {e}"
            logger.error(
                "Embedding model loading failed",
                extra={"model": "intfloat/e5-large-v2", "error": str(e)},
                exc_info=True,
            )
            raise RuntimeError(error_msg) from e

    return _embedding_model
