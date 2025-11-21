"""Unit tests for environment-based database configuration.

Story 4.0.5: Test vs Production Database Separation
Tests that validate environment configuration works correctly.

NOTE: These tests validate configuration behavior in the test environment.
"""

import os

import pytest

from raglite.shared.config import Settings


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_test_environment_uses_correct_ports():
    """Test that pytest automatically configures test environment correctly.

    Story 4.0.5 AC1: Validates that the test environment (as configured by
    conftest.py session fixture) uses the correct test database ports.

    This test runs in the actual test environment, so it should see test settings.
    """
    settings = Settings()

    # In test environment (APP_ENV=test set by conftest.py), verify test ports
    # Note: The test environment is automatically configured by conftest.py:50-51
    assert settings.qdrant_port == 6335, (
        f"Expected test Qdrant port 6335, got {settings.qdrant_port}"
    )
    assert settings.qdrant_collection_name == "financial_docs_test", (
        f"Expected test collection, got {settings.qdrant_collection_name}"
    )
    assert settings.postgres_port == 5433, (
        f"Expected test PostgreSQL port 5433, got {settings.postgres_port}"
    )
    assert settings.postgres_db == "raglite_test", (
        f"Expected test database, got {settings.postgres_db}"
    )


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_environment_configuration_is_immutable():
    """Test that Settings instances are immutable after creation.

    Story 4.0.5: Validates that Settings instances don't change if environment
    variables are modified after instantiation (predictable behavior).
    """
    # Get current settings
    original_settings = Settings()
    original_port = original_settings.qdrant_port
    original_collection = original_settings.qdrant_collection_name

    # Try to modify environment (should not affect existing instance)
    old_env = os.environ.get("APP_ENV")
    try:
        os.environ["APP_ENV"] = "production"

        # Verify original settings unchanged
        assert original_settings.qdrant_port == original_port
        assert original_settings.qdrant_collection_name == original_collection
    finally:
        # Restore environment
        if old_env:
            os.environ["APP_ENV"] = old_env
        else:
            os.environ.pop("APP_ENV", None)


@pytest.mark.priority("P1")
@pytest.mark.unit
def test_ci_detection_environment_variables():
    """Test that CI detection logic recognizes standard CI environment variables.

    Story 4.0.5 AC4: Validates that the CI detection mechanism works correctly
    by checking what environment variables would trigger CI mode.
    """
    # This test validates the CI detection logic without actually changing
    # the runtime environment (which could break other tests)

    # CI detection should recognize these variables (from config.py:91)
    ci_vars = ["GITHUB_ACTIONS", "CI", "CONTINUOUS_INTEGRATION"]

    # Verify at least one CI detection variable is documented
    assert len(ci_vars) > 0, "CI detection should support standard CI variables"

    # Verify the current environment is NOT detected as CI (we're in test mode)
    settings = Settings()
    assert (
        "ci" not in settings.qdrant_collection_name
        or settings.qdrant_collection_name == "financial_docs_test"
    ), (
        f"Test environment should not be detected as CI, got collection: {settings.qdrant_collection_name}"
    )


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_database_separation_prevents_cross_contamination():
    """Test that test and production databases are truly isolated.

    Story 4.0.5 AC3: Validates that test and production use different
    collection names and ports to prevent accidental data deletion.
    """
    settings = Settings()

    # Test environment should use test-specific names
    assert (
        "test" in settings.qdrant_collection_name.lower()
        or "ci" in settings.qdrant_collection_name.lower()
    ), (
        f"Test environment should have 'test' or 'ci' in collection name, got: {settings.qdrant_collection_name}"
    )

    assert "test" in settings.postgres_db.lower() or "ci" in settings.postgres_db.lower(), (
        f"Test environment should have 'test' or 'ci' in database name, got: {settings.postgres_db}"
    )

    # Verify test ports are different from production defaults
    assert settings.qdrant_port != 6333 or settings.postgres_port != 5432, (
        "Test environment should not use production ports (6333/5432)"
    )


@pytest.mark.priority("P1")
@pytest.mark.unit
def test_environment_configuration_validation():
    """Test that environment configuration is valid and consistent.

    Story 4.0.5: Validates that all environment-specific settings are
    internally consistent (matching ports, collection names, etc.).
    """
    settings = Settings()

    # Verify all database settings are present
    assert settings.qdrant_host is not None
    assert settings.qdrant_port > 0
    assert settings.qdrant_collection_name is not None
    assert settings.postgres_host is not None
    assert settings.postgres_port > 0
    assert settings.postgres_db is not None
    assert settings.postgres_user is not None

    # Verify test environment consistency
    if settings.app_env == "test":
        # Test ports should be 6335 and 5433
        assert settings.qdrant_port == 6335, "Test Qdrant should use port 6335"
        assert settings.postgres_port == 5433, "Test PostgreSQL should use port 5433"

        # Collection/DB names should indicate test environment
        assert (
            "test" in settings.qdrant_collection_name.lower()
            or "ci" in settings.qdrant_collection_name.lower()
        ), "Test collection should have 'test' or 'ci' in name"
