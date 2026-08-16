"""Ingestion fixtures package - facade for backward compatibility."""

# Re-export the main fixture from the original module
from .ingestion_fixtures import session_ingested_collection  # noqa: F401

__all__ = ["session_ingested_collection"]
