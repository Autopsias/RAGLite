"""API client factories for external services.

Provides singleton client instances for Qdrant and Claude API.
"""

from anthropic import Anthropic
from qdrant_client import QdrantClient

from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def get_qdrant_client() -> QdrantClient:
    """Factory function for Qdrant vector database client.

    Returns:
        Configured QdrantClient instance connected to local or cloud Qdrant

    Raises:
        ConnectionError: If Qdrant connection fails

    Example:
        >>> client = get_qdrant_client()
        >>> client.get_collections()
    """
    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        logger.info(
            "Qdrant client initialized",
            extra={"host": settings.qdrant_host, "port": settings.qdrant_port},
        )
        return client
    except Exception as e:
        logger.error("Qdrant connection failed", extra={"error": str(e)}, exc_info=True)
        raise ConnectionError(f"Failed to connect to Qdrant: {e}") from e


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
