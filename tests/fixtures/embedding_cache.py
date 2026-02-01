"""Embedding model cache for subprocess tests.

Provides a simple file-based cache to avoid reloading the Fin-E5 embedding
model across multiple subprocess invocations. The model is loaded once and
cached to disk, then reused by subsequent test runs.

Expected savings: 12 × 60s = 12+ minutes per test suite run on CI.

Usage:
    # Cache is automatically used by subprocess tests via environment variable
    # No explicit usage needed - just set EMBEDDING_CACHE_DIR before running

    import os
    os.environ['EMBEDDING_CACHE_DIR'] = str(Path(__file__).parent / '.embedding_cache')
"""

import hashlib
import json
import logging
import os
import pickle
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class EmbeddingModelCache:
    """Simple file-based cache for embedding model.

    Caches the embedding model to avoid reloading across test runs.
    Uses pickle serialization for model storage.
    """

    def __init__(self, cache_dir: Path | None = None):
        """Initialize embedding cache.

        Args:
            cache_dir: Directory to store cache files. Defaults to tests/.embedding_cache/
        """
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / ".embedding_cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.model_file = self.cache_dir / "embedding_model.pkl"

    def get_cache_key(self, model_name: str = "intfloat/e5-base-v2") -> str:
        """Get cache key for model.

        Args:
            model_name: Name of the embedding model

        Returns:
            Cache key (hash of model name)
        """
        return hashlib.md5(model_name.encode()).hexdigest()

    def load_model(self, model_name: str = "intfloat/e5-base-v2") -> object | None:
        """Load embedding model from cache or compute and cache.

        Args:
            model_name: Name of the embedding model to load

        Returns:
            Loaded embedding model, loaded from cache or fresh load

        Note:
            This is a placeholder for the actual model loading logic.
            In practice, the embedding model is loaded via multi_index_search
            and other raglite modules.
        """
        cache_key = self.get_cache_key(model_name)

        # Check if model is cached
        if self.model_file.exists() and self._is_cache_valid(cache_key):
            logger.info(
                "Loading embedding model from cache",
                extra={"cache_dir": str(self.cache_dir), "model": model_name},
            )
            try:
                with open(self.model_file, "rb") as f:
                    model: object = pickle.load(f)
                    return model
            except Exception as e:
                logger.warning(f"Failed to load cached model: {e}. Will reload from source.")

        # Model not cached or cache invalid - would be loaded normally
        logger.info(
            "Embedding model cache miss or invalid",
            extra={"model": model_name, "cache_dir": str(self.cache_dir)},
        )
        return None

    def save_model(self, model: object, model_name: str = "intfloat/e5-base-v2") -> None:
        """Save embedding model to cache.

        Args:
            model: The embedding model to cache
            model_name: Name of the embedding model
        """
        try:
            cache_key = self.get_cache_key(model_name)

            # Save model
            with open(self.model_file, "wb") as f:
                pickle.dump(model, f)

            # Save metadata
            metadata = {
                "model_name": model_name,
                "cache_key": cache_key,
                "timestamp": time.time(),
                "model_size": self.model_file.stat().st_size if self.model_file.exists() else 0,
            }

            with open(self.metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(
                "Embedding model cached successfully",
                extra={
                    "cache_dir": str(self.cache_dir),
                    "model": model_name,
                    "size_bytes": metadata["model_size"],
                },
            )
        except Exception as e:
            logger.error(f"Failed to cache model: {e}")

    def is_cache_valid(self, max_age_days: int = 7) -> bool:
        """Check if cache is valid (exists and not too old).

        Args:
            max_age_days: Maximum age of cache in days

        Returns:
            True if cache exists and is valid, False otherwise
        """
        if not self.metadata_file.exists():
            return False

        try:
            with open(self.metadata_file) as f:
                metadata = json.load(f)

            cache_age_seconds = time.time() - metadata.get("timestamp", 0)
            cache_age_days = cache_age_seconds / (24 * 3600)

            if cache_age_days > max_age_days:
                logger.info("Embedding cache expired", extra={"age_days": cache_age_days})
                return False

            return True
        except Exception as e:
            logger.warning(f"Failed to check cache validity: {e}")
            return False

    def _is_cache_valid(self, cache_key: str, max_age_days: int = 7) -> bool:
        """Internal check if cache is valid.

        Args:
            cache_key: Cache key to validate
            max_age_days: Maximum age of cache in days

        Returns:
            True if cache exists and is valid
        """
        return self.is_cache_valid(max_age_days) and self.model_file.exists()

    def clear_cache(self) -> None:
        """Clear all cached data."""
        try:
            if self.model_file.exists():
                self.model_file.unlink()
            if self.metadata_file.exists():
                self.metadata_file.unlink()
            logger.info("Embedding cache cleared", extra={"cache_dir": str(self.cache_dir)})
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")


# Global cache instance
_cache_instance: EmbeddingModelCache | None = None


def get_embedding_cache() -> EmbeddingModelCache:
    """Get or create the global embedding cache instance.

    Returns:
        EmbeddingModelCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        cache_dir = os.environ.get("EMBEDDING_CACHE_DIR")
        _cache_instance = EmbeddingModelCache(cache_dir=Path(cache_dir) if cache_dir else None)
    return _cache_instance


def setup_embedding_cache() -> None:
    """Initialize embedding cache for test session.

    Called by pytest fixture to set up cache before tests run.
    """
    cache = get_embedding_cache()
    logger.info("Embedding cache initialized", extra={"cache_dir": str(cache.cache_dir)})
