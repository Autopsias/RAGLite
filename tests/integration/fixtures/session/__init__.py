"""Session-scoped fixtures: database schema, embedding warmup, and PDF ingestion (Django/FastAPI pattern).

This facade re-exports all fixtures for backward compatibility.
"""

# Re-export test detection functions
# Re-export all fixtures from _legacy
from ._legacy import (
    ensure_test_database_schema,
    session_ingested_collection,
    warmup_embedding_model,
)
from .test_detection import _has_integration_tests, _is_postgresql_only_tests

__all__ = [
    "_has_integration_tests",
    "_is_postgresql_only_tests",
    "ensure_test_database_schema",
    "session_ingested_collection",
    "warmup_embedding_model",
]
