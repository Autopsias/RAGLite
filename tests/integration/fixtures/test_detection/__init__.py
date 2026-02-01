"""Test detection helpers for conditional fixture loading.

This package provides utilities to detect if integration tests are being run,
allowing expensive fixtures (embedding model, PDF ingestion) to skip for unit-only runs.
"""

from ._legacy import has_integration_tests, is_postgresql_only_tests

__all__ = ["has_integration_tests", "is_postgresql_only_tests"]
