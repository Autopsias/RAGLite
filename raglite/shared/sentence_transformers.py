"""Lazy-loading wrapper for sentence_transformers.

sentence_transformers imports PyTorch which takes 3-10 seconds.
This module provides lazy-loading to defer that import until first use.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "SENTENCE_TRANSFORMERS_AVAILABLE",
    "_SentenceTransformer",
    "get_sentence_transformer_class",
]

# LAZY LOAD: sentence_transformers is heavy (imports PyTorch ~3-10s)
# Deferred until first use to speed up MCP server startup
SENTENCE_TRANSFORMERS_AVAILABLE: bool | None = None  # Will be set on first check
_SentenceTransformer: type | None = None


def get_sentence_transformer_class() -> type[Any] | None:
    """Lazy-load SentenceTransformer class to avoid slow startup.

    sentence_transformers imports PyTorch which takes 3-10 seconds.
    By deferring this import, MCP server startup is much faster.

    Returns:
        SentenceTransformer class if available, None otherwise
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
