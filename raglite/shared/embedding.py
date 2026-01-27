"""Lazy-loading embedding model wrapper for efficient model management.

Provides LazyEmbeddingModel class for deferred SentenceTransformer loading.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any

import filelock

from raglite.shared.config import get_settings
from raglite.shared.logging import get_logger

# LAZY LOAD: sentence_transformers is heavy (imports PyTorch ~3-10s)
# Deferred until first use to speed up MCP server startup
SENTENCE_TRANSFORMERS_AVAILABLE: bool | None = None  # Will be set on first check
_SentenceTransformer: type | None = None


def _get_sentence_transformer_class() -> type | None:
    """Lazy-load SentenceTransformer class to avoid slow startup.

    sentence_transformers imports PyTorch which takes 3-10 seconds.
    By deferring this import, MCP server startup is much faster.
    """
    global SENTENCE_TRANSFORMERS_AVAILABLE, _SentenceTransformer
    if SENTENCE_TRANSFORMERS_AVAILABLE is None:
        try:
            from sentence_transformers import SentenceTransformer

            _SentenceTransformer = SentenceTransformer
            SENTENCE_TRANSFORMERS_AVAILABLE = True
        except ImportError:
            SENTENCE_TRANSFORMERS_AVAILABLE = False
            _SentenceTransformer = None
    return _SentenceTransformer


logger = get_logger(__name__)


class LazyEmbeddingModel:
    """Lazy-loading wrapper for SentenceTransformer embedding model.

    Defers actual model loading until first encode() call. This prevents:
    - OOM from eager imports in parallel test execution
    - Unnecessary model loading in tests that don't use embeddings
    - Enables marker-based test splitting without memory overhead
    """

    def __init__(self) -> None:
        """Initialize lazy wrapper without loading model."""
        self._model: Any | None = None
        self._model_name: str | None = None

    def _wait_for_gw0_model_ready(self, worker_id: str) -> None:
        """Wait for gw0 worker to load embedding model (xdist coordination).

        Args:
            worker_id: The current xdist worker ID

        Raises:
            RuntimeError: If timeout waiting for gw0 to signal model ready
        """
        logger.warning(
            f"Worker {worker_id} attempting to load embedding model. "
            "This may indicate missing xdist_group marker on embedding tests.",
            extra={"worker_id": worker_id, "xdist_mode": True},
        )
        # Wait for gw0 to signal model ready (with timeout)
        wait_start = time.time()
        max_wait = 180  # 3 minutes max wait
        while not _MODEL_READY_SIGNAL.exists():
            if time.time() - wait_start > max_wait:
                logger.error(
                    f"Worker {worker_id}: Timeout waiting for gw0 to load embedding model",
                    extra={"worker_id": worker_id, "waited_seconds": max_wait},
                )
                raise RuntimeError(
                    f"Worker {worker_id} timed out waiting for gw0 to load embedding model. "
                    "Ensure tests using embeddings have @pytest.mark.xdist_group(name='embedding_model')"
                )
            time.sleep(1)
        logger.info(
            f"Worker {worker_id}: gw0 has loaded embedding model, waiting for lock",
            extra={"worker_id": worker_id},
        )

    def _get_model_name_for_environment(self) -> tuple[str, bool]:
        """Determine which embedding model to use based on environment.

        Returns:
            tuple[str, bool]: (model_name, use_fast_model)
        """
        import os

        # CRITICAL FIX (2026-01-24): Check env var DIRECTLY as fallback
        current_settings = get_settings()

        # Direct env var check - most reliable in xdist workers
        ci_fast_env_raw = os.environ.get("CI_FAST_EMBEDDING", "")
        ci_env_raw = os.environ.get("CI", "")
        ci_fast_from_env = ci_fast_env_raw.lower() == "true"
        ci_from_env = ci_env_raw.lower() == "true"

        # Use fast model if EITHER settings OR direct env var indicates CI mode
        use_fast_model = (
            current_settings.ci_fast_embedding_enabled or ci_fast_from_env or ci_from_env
        )

        # Diagnostic logging for CI debugging
        logger.info(
            "Embedding model selection (lazy load)",
            extra={
                "CI_FAST_EMBEDDING_env": ci_fast_env_raw or "NOT SET",
                "CI_env": ci_env_raw or "NOT SET",
                "settings_ci_fast_enabled": current_settings.ci_fast_embedding_enabled,
                "use_fast_model": use_fast_model,
            },
        )

        # CI Optimization: Use smaller, faster model in CI
        if use_fast_model:
            model_name = current_settings.ci_fast_embedding_model
            logger.info(
                "Loading CI fast embedding model (with lock)",
                extra={
                    "model": model_name,
                    "ci_fast_mode": True,
                    "reason": "env_var" if (ci_fast_from_env or ci_from_env) else "settings",
                },
            )
        else:
            model_name = current_settings.embedding_model
            logger.info(
                "Loading Fin-E5 embedding model (with lock)",
                extra={"model": model_name, "ci_fast_mode": False},
            )

        return model_name, use_fast_model

    def _load_model(self) -> None:
        """Load the actual SentenceTransformer model (called on first encode)."""
        if self._model is not None:
            return  # Already loaded

        # Lazy-load the SentenceTransformer class
        SentenceTransformerClass = _get_sentence_transformer_class()
        if SentenceTransformerClass is None:
            raise ImportError(
                "sentence-transformers package not installed. Install with: pip install sentence-transformers"
            )

        import os

        # CRITICAL FIX (2026-01-24): Worker coordination to prevent OOM
        worker_id = os.environ.get("PYTEST_XDIST_WORKER", "")
        is_xdist = bool(worker_id)

        if is_xdist and worker_id not in ("", "gw0"):
            # Non-gw0 worker trying to load model - likely a misconfiguration
            self._wait_for_gw0_model_ready(worker_id)

        # Cross-process lock prevents simultaneous loading across xdist workers
        lock = filelock.FileLock(_EMBEDDING_LOCK_FILE, timeout=180)

        with lock:
            # Double-check after acquiring lock (another process may have loaded it)
            if self._model is not None:
                logger.info("Embedding model already loaded by another process")
                return

            # Determine which model to use based on environment
            self._model_name, use_fast_model = self._get_model_name_for_environment()

            try:
                self._model = SentenceTransformerClass(self._model_name)
                dimensions = self._model.get_sentence_embedding_dimension()

                logger.info(
                    "Embedding model loaded successfully (lazy)",
                    extra={
                        "model": self._model_name,
                        "dimensions": dimensions,
                        "ci_fast_mode": use_fast_model,
                    },
                )

                # CRITICAL FIX (2026-01-24): Signal to other workers that model is ready
                if is_xdist:
                    try:
                        _MODEL_READY_SIGNAL.touch()
                        logger.info(
                            f"Worker {worker_id or 'master'}: Created model ready signal",
                            extra={"signal_path": str(_MODEL_READY_SIGNAL)},
                        )
                    except OSError as signal_err:
                        logger.warning(
                            f"Failed to create model ready signal: {signal_err}",
                            extra={"error": str(signal_err)},
                        )
            except Exception as e:
                error_msg = f"Failed to load embedding model ({self._model_name}): {e}"
                logger.error(
                    "Embedding model loading failed",
                    extra={"model": self._model_name, "error": str(e)},
                    exc_info=True,
                )
                raise RuntimeError(error_msg) from e

    def encode(self, *args: Any, **kwargs: Any) -> Any:
        """Encode text to embeddings (loads model on first call)."""
        self._load_model()
        assert self._model is not None  # Guaranteed after _load_model()
        return self._model.encode(*args, **kwargs)

    def get_sentence_embedding_dimension(self) -> int:
        """Get embedding dimension (loads model if needed)."""
        self._load_model()
        assert self._model is not None  # Guaranteed after _load_model()
        result: int = self._model.get_sentence_embedding_dimension()
        return result

    def __getattr__(self, name: str) -> Any:
        """Proxy other attributes to underlying model (loads on access)."""
        self._load_model()
        return getattr(self._model, name)


# Cross-process lock file for embedding model loading (prevents race conditions in xdist)
# Use tempfile.gettempdir() for secure temporary directory selection
_EMBEDDING_LOCK_FILE = Path(tempfile.gettempdir()) / "raglite_embedding_model.lock"

# Signal file created by gw0 when model is loaded (other workers wait for this)
_MODEL_READY_SIGNAL = Path(tempfile.gettempdir()) / "raglite_embedding_ready.lock"
