"""Unit tests for raglite.shared.config module.

ENVIRONMENT ISOLATION (2025-12-19):
These tests validate the Settings class behavior across different environments
(production, test, CI). To ensure reliable results regardless of the host
environment (local dev, CI pipeline, VS Code), we use:

1. `patch.dict(os.environ, {...}, clear=True)` - Clears ALL env vars
2. `Settings(_env_file=None)` - Prevents loading from .env/.env.test files

This complete isolation ensures tests pass consistently everywhere.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from raglite.shared.config import Settings

# =============================================================================
# Basic Settings Tests (use default test environment from conftest.py)
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_settings_load_from_env(monkeypatch: MonkeyPatch) -> None:
    """Test Settings loads from environment variables."""
    monkeypatch.setenv("QDRANT_HOST", "testhost")
    monkeypatch.setenv("QDRANT_PORT", "9999")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-abc123")

    settings = Settings()
    assert settings.qdrant_host == "testhost"
    assert settings.qdrant_port == 9999
    assert settings.anthropic_api_key == "test-key-abc123"


@pytest.mark.priority("P1")
@pytest.mark.unit
def test_settings_default_values(monkeypatch: MonkeyPatch) -> None:
    """Test Settings uses default values when env vars not set.

    Story 4.0.5: Note that tests run in test environment (APP_ENV=test) by default,
    so test ports are expected instead of production ports.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "required-key")

    settings = Settings()
    assert settings.qdrant_host == "localhost"
    # In test environment (APP_ENV=test set by conftest.py), expect test port
    assert settings.qdrant_port == 6335, "Test environment should use port 6335"
    assert settings.embedding_model == "intfloat/e5-large-v2"
    assert settings.embedding_dimension == 1024


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_settings_missing_api_key_optional(monkeypatch: MonkeyPatch) -> None:
    """Test Settings allows missing ANTHROPIC_API_KEY (optional until Story 1.11)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    settings = Settings()
    assert settings.anthropic_api_key is None  # Optional field, defaults to None


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_settings_type_validation(monkeypatch: MonkeyPatch) -> None:
    """Test Settings validates port as integer."""
    monkeypatch.setenv("QDRANT_PORT", "invalid_port")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    with pytest.raises(ValidationError):
        Settings()


# =============================================================================
# Environment-Based Database Separation Tests (Story 4.0.5)
# These tests require COMPLETE environment isolation to work in CI
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_adjust_for_environment_production_default() -> None:
    """Test adjust_for_environment() uses production settings by default.

    Story 4.0.5 AC1: Production environment should use default ports and collections.

    CRITICAL: Uses clear=True and _env_file=None for complete isolation from
    CI environment (where CI=true, GITHUB_ACTIONS=true are set) and .env.test file.
    """
    with patch.dict(os.environ, {}, clear=True):
        # Create Settings without loading any .env file
        settings = Settings(_env_file=None)

        # Verify production settings (all defaults from class definition)
        assert settings.app_env == "production"
        assert settings.qdrant_port == 6333
        assert settings.qdrant_collection_name == "financial_docs"
        assert settings.postgres_port == 5432
        assert settings.postgres_db == "raglite"
        assert settings.postgres_user == "raglite"
        assert settings.postgres_password == "raglite"


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_adjust_for_environment_test_mode() -> None:
    """Test adjust_for_environment() switches to test databases when APP_ENV=test.

    Story 4.0.5 AC1: Test environment should use separate ports and collections.

    PostgreSQL settings come from explicit env vars (not auto-adjusted).
    Qdrant settings auto-adjust (port 6335, collection _test suffix).
    """
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "test",
            # No CI variables = non-CI test environment
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "raglite_test",
            "POSTGRES_USER": "raglite_test",
            "POSTGRES_PASSWORD": "raglite_test",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        # Verify test settings
        assert settings.app_env == "test"
        # Qdrant auto-adjusts for test environment
        assert settings.qdrant_port == 6335
        assert settings.qdrant_collection_name == "financial_docs_test"
        # PostgreSQL uses explicit env vars
        assert settings.postgres_port == 5433
        assert settings.postgres_db == "raglite_test"
        assert settings.postgres_user == "raglite_test"
        assert settings.postgres_password == "raglite_test"


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_adjust_for_environment_ci_github_actions() -> None:
    """Test adjust_for_environment() detects GitHub Actions CI environment.

    Story 4.0.5 AC4: CI environment should use _ci collection suffix.

    Tests that GITHUB_ACTIONS=true triggers CI detection even when
    CI and CONTINUOUS_INTEGRATION are not set.
    """
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "test",
            "GITHUB_ACTIONS": "true",  # Only GITHUB_ACTIONS set
            "POSTGRES_DB": "raglite_ci",
            "POSTGRES_USER": "raglite_ci",
            "POSTGRES_PASSWORD": "raglite_ci",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        # Verify CI-specific collection name
        assert settings.app_env == "test"
        assert settings.qdrant_collection_name == "financial_docs_ci"
        assert settings.postgres_db == "raglite_ci"
        assert settings.postgres_user == "raglite_ci"
        assert settings.postgres_password == "raglite_ci"


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_adjust_for_environment_ci_generic() -> None:
    """Test adjust_for_environment() detects generic CI environment variable.

    Story 4.0.5 AC4: Should detect CI=true as CI environment.

    Tests that CI=true triggers CI detection even when
    GITHUB_ACTIONS and CONTINUOUS_INTEGRATION are not set.
    """
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "test",
            "CI": "true",  # Only CI set
            "POSTGRES_DB": "raglite_ci",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        # Verify CI-specific collection name
        assert settings.qdrant_collection_name == "financial_docs_ci"
        assert settings.postgres_db == "raglite_ci"


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_adjust_for_environment_ci_continuous_integration() -> None:
    """Test adjust_for_environment() detects CONTINUOUS_INTEGRATION variable.

    Story 4.0.5 AC4: Should detect CONTINUOUS_INTEGRATION=true as CI environment.

    Tests that CONTINUOUS_INTEGRATION=true triggers CI detection even when
    CI and GITHUB_ACTIONS are not set.
    """
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "test",
            "CONTINUOUS_INTEGRATION": "true",  # Only CONTINUOUS_INTEGRATION set
            "POSTGRES_DB": "raglite_ci",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        # Verify CI-specific collection name
        assert settings.qdrant_collection_name == "financial_docs_ci"
        assert settings.postgres_db == "raglite_ci"


@pytest.mark.priority("P1")
@pytest.mark.unit
def test_adjust_for_environment_respects_explicit_overrides() -> None:
    """Test adjust_for_environment() respects explicit environment variable overrides.

    Story 4.0.5: Explicit env vars should NOT be auto-adjusted by the validator.
    """
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "test",
            "QDRANT_PORT": "7777",  # Explicit override
            "QDRANT_COLLECTION_NAME": "custom_collection",  # Explicit override
            "POSTGRES_PORT": "9999",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        # Explicit overrides should be respected (not changed to test values)
        assert settings.qdrant_port == 7777  # NOT 6335
        assert settings.qdrant_collection_name == "custom_collection"  # NOT financial_docs_test
        assert settings.postgres_port == 9999


@pytest.mark.priority("P1")
@pytest.mark.unit
def test_adjust_for_environment_all_branches() -> None:
    """Test adjust_for_environment() covers all conditional branches.

    Story 4.0.5: Comprehensive test of all validator logic branches.
    Each scenario uses complete environment isolation.
    """
    # Test 1: Production environment (no adjustment)
    with patch.dict(os.environ, {}, clear=True):
        settings_prod = Settings(_env_file=None)
        assert settings_prod.app_env == "production"
        assert settings_prod.qdrant_port == 6333
        assert settings_prod.qdrant_collection_name == "financial_docs"

    # Test 2: Test environment without CI (adjusts to _test suffix)
    with patch.dict(os.environ, {"APP_ENV": "test"}, clear=True):
        settings_test = Settings(_env_file=None)
        assert settings_test.app_env == "test"
        assert settings_test.qdrant_port == 6335
        assert settings_test.qdrant_collection_name == "financial_docs_test"

    # Test 3: Test environment WITH CI (adjusts to _ci suffix)
    with patch.dict(os.environ, {"APP_ENV": "test", "GITHUB_ACTIONS": "true"}, clear=True):
        settings_ci = Settings(_env_file=None)
        assert settings_ci.qdrant_collection_name == "financial_docs_ci"

    # Test 4: Development environment (treated as production - no adjustment)
    with patch.dict(os.environ, {"APP_ENV": "development"}, clear=True):
        settings_dev = Settings(_env_file=None)
        assert settings_dev.qdrant_port == 6333  # No adjustment for development
        assert settings_dev.qdrant_collection_name == "financial_docs"
