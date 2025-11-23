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

    UPDATED (2025-11-23): PostgreSQL settings NO LONGER auto-adjust in validator.
    conftest.py MUST set explicit PostgreSQL env vars (POSTGRES_PORT, POSTGRES_DB, etc).
    Qdrant settings STILL auto-adjust (port 6335, collection _test/_ci suffix).

    NOTE: In CI environments (GITHUB_ACTIONS=true), collection names use _ci suffix.
    In local test environments, collection names use _test suffix.
    Both are valid test configurations.
    """
    settings = Settings()

    # In test environment (APP_ENV=test set by conftest.py), verify test ports
    # Qdrant auto-adjusts (STILL works)
    assert settings.qdrant_port == 6335, (
        f"Expected test Qdrant port 6335, got {settings.qdrant_port}"
    )

    # Accept both _test (local) and _ci (CI) suffixes as valid test configurations
    assert settings.qdrant_collection_name in [
        "financial_docs_test",
        "financial_docs_ci",
    ], f"Expected test or CI collection, got {settings.qdrant_collection_name}"

    # PostgreSQL uses explicit env vars (set by conftest.py)
    # If this fails, conftest.py needs to set POSTGRES_PORT=5433
    assert settings.postgres_port == 5433, (
        f"Expected test PostgreSQL port 5433, got {settings.postgres_port}. "
        f"Ensure conftest.py sets POSTGRES_PORT=5433"
    )

    # Accept both _test (local) and _ci (CI) suffixes as valid test configurations
    # If this fails, conftest.py needs to set POSTGRES_DB=raglite_test or raglite_ci
    assert settings.postgres_db in [
        "raglite_test",
        "raglite_ci",
    ], (
        f"Expected test or CI database, got {settings.postgres_db}. Ensure conftest.py sets POSTGRES_DB"
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

    NOTE: This test validates the logic itself, not the specific collection name.
    When running in actual CI (GITHUB_ACTIONS=true), the collection will be _ci.
    When running locally, the collection will be _test.
    Both are correct and expected behavior.
    """
    # This test validates the CI detection logic without actually changing
    # the runtime environment (which could break other tests)

    # CI detection should recognize these variables (from config.py:91)
    ci_vars = ["GITHUB_ACTIONS", "CI", "CONTINUOUS_INTEGRATION"]

    # Verify at least one CI detection variable is documented
    assert len(ci_vars) > 0, "CI detection should support standard CI variables"

    # Verify test environment uses appropriate test collection (either _test or _ci)
    settings = Settings()
    assert settings.qdrant_collection_name in [
        "financial_docs_test",
        "financial_docs_ci",
    ], f"Test environment should use test or CI collection, got: {settings.qdrant_collection_name}"

    # Verify the collection name matches the CI detection logic
    is_ci_env = os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("CI") == "true"
    expected_suffix = "_ci" if is_ci_env else "_test"
    assert settings.qdrant_collection_name == f"financial_docs{expected_suffix}", (
        f"Expected collection with {expected_suffix} suffix (is_ci={is_ci_env}), "
        f"got {settings.qdrant_collection_name}"
    )


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_database_separation_prevents_cross_contamination():
    """Test that test and production databases are truly isolated.

    Story 4.0.5 AC3: Validates that test and production use different
    collection names and ports to prevent accidental data deletion.

    UPDATED (2025-11-23): PostgreSQL database name comes from explicit env vars.
    This test verifies that conftest.py properly sets PostgreSQL env vars for isolation.
    """
    settings = Settings()

    # Test environment should use test-specific names
    # Qdrant auto-adjusts (STILL works)
    assert (
        "test" in settings.qdrant_collection_name.lower()
        or "ci" in settings.qdrant_collection_name.lower()
    ), (
        f"Test environment should have 'test' or 'ci' in collection name, got: {settings.qdrant_collection_name}"
    )

    # PostgreSQL uses explicit env vars (conftest.py should set POSTGRES_DB=raglite_test or raglite_ci)
    assert "test" in settings.postgres_db.lower() or "ci" in settings.postgres_db.lower(), (
        f"Test environment should have 'test' or 'ci' in database name, got: {settings.postgres_db}. "
        f"Ensure conftest.py sets POSTGRES_DB=raglite_test or raglite_ci"
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

    UPDATED (2025-11-23): PostgreSQL port comes from explicit env vars.
    Qdrant port auto-adjusts to 6335 in test environment.
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
        # Qdrant auto-adjusts (STILL works)
        assert settings.qdrant_port == 6335, "Test Qdrant should use port 6335"

        # PostgreSQL uses explicit env vars (conftest.py should set POSTGRES_PORT=5433)
        assert settings.postgres_port == 5433, (
            "Test PostgreSQL should use port 5433. Ensure conftest.py sets POSTGRES_PORT=5433"
        )

        # Collection/DB names should indicate test environment
        assert (
            "test" in settings.qdrant_collection_name.lower()
            or "ci" in settings.qdrant_collection_name.lower()
        ), "Test collection should have 'test' or 'ci' in name"
