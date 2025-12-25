"""Test fixtures package for RAGLite.

This package provides organized test fixtures loaded via pytest_plugins in conftest.py.

Fixture Modules:
    database_fixtures: Session-scoped Qdrant and PostgreSQL database fixtures
    mock_clients: Mock fixtures for Qdrant, Claude, and Mistral API clients
    mistral_mock_helpers: Helper functions for generating mock Mistral API responses
    sample_data: Sample document metadata and chunk fixtures for testing
    pytest_hooks: Custom pytest hooks for test collection and execution
    performance_monitoring: Session timing and performance budget validation

All fixtures are automatically loaded by pytest via the pytest_plugins list in
tests/conftest.py. Individual tests do not need to import from this package.
"""
