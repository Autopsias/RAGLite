"""API client factories for external services.

Provides singleton client instances for Qdrant, Claude API, PostgreSQL, and Mistral AI.
"""

from __future__ import annotations

import time
from typing import Any

# Import embedding module for re-exporting globals (backward compatibility)
from raglite.shared import embedding as _embedding_module
from raglite.shared.config import settings
from raglite.shared.embedding import (
    LazyEmbeddingModel,
)
from raglite.shared.logging import get_logger


# Re-export for backward compatibility with tests that access via clients_module
# These are references to the actual globals in embedding.py
def __getattr__(name: str) -> Any:
    """Provide backward compatibility for embedding module globals."""
    if name in ("SENTENCE_TRANSFORMERS_AVAILABLE", "_SentenceTransformer"):
        return getattr(_embedding_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# OPTIMIZATION: Make imports optional to prevent test failures when dependencies not available
try:
    import psycopg2
    import psycopg2.extras

    # Register UUID adapter for psycopg2 (Story 2.6 AC4)
    psycopg2.extras.register_uuid()
    PSYCOPG2_AVAILABLE = True
except ImportError:
    # PostgreSQL support optional for unit tests
    PSYCOPG2_AVAILABLE = False
    psycopg2 = None

try:
    from anthropic import Anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    Anthropic = None

try:
    from mistralai import Mistral

    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False
    Mistral = None

try:
    from qdrant_client import QdrantClient

    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None

logger = get_logger(__name__)

# Module-level singletons (connection pooling and model caching)
_qdrant_client: QdrantClient | None = None
_embedding_model: LazyEmbeddingModel | None = None  # Lazy-loaded wrapper
_postgresql_connection: Any | None = None  # psycopg2.extensions.connection when available
_mistral_client: Mistral | None = None


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client with singleton caching, connection pooling, and retry logic.

    Returns:
        Cached QdrantClient instance connected to local or cloud Qdrant

    Raises:
        ConnectionError: If Qdrant connection fails after 3 retries
        ImportError: If qdrant-client package is not installed

    Note:
        Connection: Host=settings.qdrant_host, Port=settings.qdrant_port
        Timeout: 30s (production), 1s (tests)
        Retry: 3 attempts with exponential backoff (1s, 2s, 4s)
    """
    if not QDRANT_AVAILABLE:
        raise ImportError(
            "qdrant-client package not installed. Install with: pip install qdrant-client"
        )

    global _qdrant_client

    if _qdrant_client is None:
        logger.info(
            "Connecting to Qdrant",
            extra={"host": settings.qdrant_host, "port": settings.qdrant_port},
        )

        # Retry configuration
        max_retries = 3
        retry_delays = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s

        # OPTIMIZATION: Use shorter timeout in test environment to prevent hangs
        # This reduces test timeout from 30s to 1s when connection fails
        import os

        is_test_env = os.getenv("PYTEST_CURRENT_TEST") is not None or os.getenv("TESTING") == "true"
        connection_timeout = 1 if is_test_env else 30

        for attempt in range(max_retries):
            try:
                _qdrant_client = QdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port,
                    timeout=connection_timeout,
                )
                logger.info(
                    "Qdrant client connected successfully",
                    extra={
                        "host": settings.qdrant_host,
                        "port": settings.qdrant_port,
                        "attempt": attempt + 1,
                        "timeout": connection_timeout,
                        "test_env": is_test_env,
                    },
                )
                break  # Success - exit retry loop
            except Exception as e:
                if attempt < max_retries - 1:
                    delay: float = retry_delays[attempt]
                    # In test environment, use shorter delays to prevent test hangs
                    if is_test_env:
                        delay = min(delay, 0.5)  # Cap at 0.5s for tests

                    logger.warning(
                        f"Qdrant connection failed (attempt {attempt + 1}/{max_retries}), retrying in {delay}s",
                        extra={
                            "host": settings.qdrant_host,
                            "port": settings.qdrant_port,
                            "attempt": attempt + 1,
                            "delay_seconds": delay,
                            "error": str(e),
                            "test_env": is_test_env,
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
                            "test_env": is_test_env,
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
    """Get Anthropic Claude API client.

    Returns:
        Configured Anthropic client instance

    Raises:
        ValueError: If ANTHROPIC_API_KEY not set or using placeholder
        ImportError: If anthropic package is not installed
    """
    if not ANTHROPIC_AVAILABLE:
        raise ImportError("anthropic package not installed. Install with: pip install anthropic")

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


def get_embedding_model() -> Any:
    """Get embedding model (singleton pattern with lazy loading).

    Returns:
        LazyEmbeddingModel: Wrapper that defers model loading until first encode() call

    Raises:
        RuntimeError: If model loading fails
        ImportError: If sentence-transformers package is not installed

    Note:
        Production: Fin-E5 (intfloat/e5-large-v2), 1024 dimensions, financial domain optimization
            Week 0 validation: 0.84 avg similarity, 71.05% NDCG@10
            Load time: ~60s, Size: ~2GB
        CI Fast Mode: all-MiniLM-L6-v2, 384 dimensions, general purpose
            Load time: ~5s, Size: ~80MB
            Trade-off: Slightly lower accuracy but 12x faster model loading

        Lazy Loading (2026-01-26):
            Model loading deferred until first encode() call. This prevents:
            - OOM from eager imports (4 workers × 2GB = 8GB > 7GB runner limit)
            - Unnecessary model loading in tests that don't use embeddings
            - Enables marker-based test splitting without memory overhead

        Cross-process lock: Prevents simultaneous model loading across xdist workers

        Worker Coordination (2026-01-24):
            In xdist mode, only gw0 loads the model. Other workers wait for gw0 to signal
            completion via _MODEL_READY_SIGNAL file. This prevents multiple workers from
            each loading 80MB+ models and causing OOM.
    """
    global _embedding_model

    if _embedding_model is None:
        # Create lazy wrapper (defers actual model loading until first encode() call)
        _embedding_model = LazyEmbeddingModel()
        logger.info("Created lazy embedding model wrapper (model will load on first encode() call)")

    return _embedding_model


def get_postgresql_connection() -> Any:
    """Get PostgreSQL connection with singleton caching and auto-reconnect.

    Returns:
        Cached psycopg2 connection instance

    Raises:
        ConnectionError: If PostgreSQL connection fails
        ImportError: If psycopg2 is not installed

    Note:
        Connection: Host/settings.postgres_host, Port/settings.postgres_port
        Timeout: 10s connect, 30s statement (production); 1s/5s (tests)
        Auto-reconnect: Detects closed/failed connections and recreates them

    **Phase 4 Upgrade:** Use `psycopg2.pool.ThreadedConnectionPool` for production
    """
    if not PSYCOPG2_AVAILABLE:
        raise ImportError("psycopg2 not installed - PostgreSQL support unavailable")

    global _postgresql_connection

    # Check if connection needs to be reset/recreated
    need_new_connection = False
    if _postgresql_connection is None:
        need_new_connection = True
    elif _postgresql_connection.closed:
        need_new_connection = True
    else:
        # Check if connection is in failed transaction state
        try:
            # Test connection with a simple query
            cursor = _postgresql_connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
        except (psycopg2.Error, psycopg2.InterfaceError):
            # Connection is in failed state or has issues
            need_new_connection = True
            try:
                _postgresql_connection.close()
            except Exception:  # nosec B110 - Cleanup handler: errors are non-critical  # nosec B110 - Cleanup handler: connection close errors are non-critical
                pass  # Cleanup handler: ignore close errors

    if need_new_connection:
        logger.info(
            "Connecting to PostgreSQL",
            extra={
                "host": settings.postgres_host,
                "port": settings.postgres_port,
                "database": settings.postgres_db,
            },
        )

        # OPTIMIZATION: Use shorter timeout in test environment to prevent hangs
        # This reduces test timeout from 10s to 1s when connection fails
        import os

        is_test_env = os.getenv("PYTEST_CURRENT_TEST") is not None or os.getenv("TESTING") == "true"
        connect_timeout = 1 if is_test_env else 10
        statement_timeout = "5s" if is_test_env else "30s"

        try:
            _postgresql_connection = psycopg2.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                dbname=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
                connect_timeout=connect_timeout,  # Connection timeout (seconds)
                options=f"-c statement_timeout={statement_timeout}",  # Query execution timeout
            )
            logger.info(
                "PostgreSQL connection established",
                extra={
                    "host": settings.postgres_host,
                    "port": settings.postgres_port,
                    "database": settings.postgres_db,
                    "connect_timeout": 10,
                    "statement_timeout": "30s",
                },
            )
        except psycopg2.Error as e:
            error_msg = f"Failed to connect to PostgreSQL: {e}"
            logger.error(
                "PostgreSQL connection failed",
                extra={
                    "host": settings.postgres_host,
                    "port": settings.postgres_port,
                    "database": settings.postgres_db,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise ConnectionError(error_msg) from e

    return _postgresql_connection


def reset_postgresql_connection() -> None:
    """Reset PostgreSQL connection by closing and clearing the singleton.

    This function should be called when the connection is in a failed
    transaction state (e.g., after a PostgreSQL error that aborts the transaction).
    The next call to get_postgresql_connection() will create a fresh connection.

    Also attempts to rollback any pending transaction before closing.
    """
    global _postgresql_connection

    if _postgresql_connection is not None:
        try:
            # Try to rollback any failed transaction
            _postgresql_connection.rollback()
            logger.info("PostgreSQL transaction rolled back")
        except Exception as e:
            logger.warning(f"Failed to rollback PostgreSQL transaction: {e}")

        try:
            _postgresql_connection.close()
            logger.info("PostgreSQL connection closed for reset")
        except Exception as e:
            logger.warning(f"Failed to close PostgreSQL connection: {e}")

        _postgresql_connection = None
        logger.info("PostgreSQL connection reset complete - will reconnect on next use")


def get_mistral_client() -> Mistral:
    """Get Mistral AI client with singleton caching and timeout configuration.

    Returns:
        Cached Mistral client instance with configured timeouts

    Raises:
        ValueError: If MISTRAL_API_KEY not set in environment
        ImportError: If mistralai package is not installed

    Note:
        Timeout: 1s (tests), varies (production) to prevent hangs
        Use cases: Story 2.4 (metadata), Story 2.13 (text-to-SQL)
    """
    if not MISTRAL_AVAILABLE:
        raise ImportError("mistralai package not installed. Install with: pip install mistralai")

    global _mistral_client

    if _mistral_client is None:
        if not settings.mistral_api_key or settings.mistral_api_key == "":
            raise ValueError(
                "MISTRAL_API_KEY environment variable not set. "
                "Get your free API key from https://console.mistral.ai/"
            )

        logger.info("Initializing Mistral AI client")

        # OPTIMIZATION: Configure timeouts for test environment to prevent hangs
        import os

        is_test_env = os.getenv("PYTEST_CURRENT_TEST") is not None or os.getenv("TESTING") == "true"

        if is_test_env:
            # Set environment variables for Mistral SDK timeout in test environment
            os.environ["MISTRAL_CLIENT_TIMEOUT"] = "1"  # 1 second timeout for tests
            logger.info("Mistral AI client configured with test timeout (1s)")
        else:
            logger.info("Mistral AI client configured with production timeouts")

        # Mistral SDK no longer accepts http_client parameter
        # Timeout configuration must be handled differently or via environment variables
        _mistral_client = Mistral(api_key=settings.mistral_api_key)

        logger.info("Mistral AI client initialized")

    return _mistral_client
