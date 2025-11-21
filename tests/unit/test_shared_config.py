"""Unit tests for raglite.shared.config module."""

import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from raglite.shared.config import Settings


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


# Story 4.0.5: Environment-based database separation tests
@pytest.mark.priority("P0")
@pytest.mark.unit
def test_adjust_for_environment_production_default(monkeypatch: MonkeyPatch) -> None:
    """Test adjust_for_environment() uses production settings by default.

    Story 4.0.5 AC1: Production environment should use default ports and collections.
    """
    # Clean environment - no APP_ENV set
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("CONTINUOUS_INTEGRATION", raising=False)

    settings = Settings()

    # Verify production settings (defaults)
    assert settings.app_env == "production"
    assert settings.qdrant_port == 6333
    assert settings.qdrant_collection_name == "financial_docs"
    assert settings.postgres_port == 5432
    assert settings.postgres_db == "raglite"
    assert settings.postgres_user == "raglite"
    assert settings.postgres_password == "raglite"


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_adjust_for_environment_test_mode(monkeypatch: MonkeyPatch) -> None:
    """Test adjust_for_environment() switches to test databases when APP_ENV=test.

    Story 4.0.5 AC1: Test environment should use separate ports and collections.
    """
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("CONTINUOUS_INTEGRATION", raising=False)

    settings = Settings()

    # Verify test settings
    assert settings.app_env == "test"
    assert settings.qdrant_port == 6335
    assert settings.qdrant_collection_name == "financial_docs_test"
    assert settings.postgres_port == 5433
    assert settings.postgres_db == "raglite_test"
    assert settings.postgres_user == "raglite_test"
    assert settings.postgres_password == "raglite_test"


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_adjust_for_environment_ci_github_actions(monkeypatch: MonkeyPatch) -> None:
    """Test adjust_for_environment() detects GitHub Actions CI environment.

    Story 4.0.5 AC4: CI environment should use separate collection to avoid conflicts.
    """
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    settings = Settings()

    # Verify CI-specific collection name
    assert settings.app_env == "test"
    assert settings.qdrant_collection_name == "financial_docs_ci"
    assert settings.postgres_db == "raglite_ci"
    assert settings.postgres_user == "raglite_ci"
    assert settings.postgres_password == "raglite_ci"


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_adjust_for_environment_ci_generic(monkeypatch: MonkeyPatch) -> None:
    """Test adjust_for_environment() detects generic CI environment variable.

    Story 4.0.5 AC4: Should detect CI=true as CI environment.
    """
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("CI", "true")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    settings = Settings()

    # Verify CI-specific collection name
    assert settings.qdrant_collection_name == "financial_docs_ci"
    assert settings.postgres_db == "raglite_ci"


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_adjust_for_environment_ci_continuous_integration(monkeypatch: MonkeyPatch) -> None:
    """Test adjust_for_environment() detects CONTINUOUS_INTEGRATION variable.

    Story 4.0.5 AC4: Should detect CONTINUOUS_INTEGRATION=true as CI environment.
    """
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("CONTINUOUS_INTEGRATION", "true")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)

    settings = Settings()

    # Verify CI-specific collection name
    assert settings.qdrant_collection_name == "financial_docs_ci"
    assert settings.postgres_db == "raglite_ci"


@pytest.mark.priority("P1")
@pytest.mark.unit
def test_adjust_for_environment_respects_explicit_overrides(monkeypatch: MonkeyPatch) -> None:
    """Test adjust_for_environment() respects explicit environment variable overrides.

    Story 4.0.5: Environment-based adjustment should only apply to default values,
    allowing explicit overrides via environment variables.
    """
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("QDRANT_PORT", "7777")  # Explicit override
    monkeypatch.setenv("QDRANT_COLLECTION_NAME", "custom_collection")  # Explicit override

    settings = Settings()

    # Verify explicit overrides are respected
    assert settings.qdrant_port == 7777  # Should NOT be changed to 6335
    assert (
        settings.qdrant_collection_name == "custom_collection"
    )  # Should NOT be changed to financial_docs_test

    # But other defaults should still be adjusted for test environment
    assert settings.postgres_port == 5433  # This should still be adjusted


@pytest.mark.priority("P1")
@pytest.mark.unit
def test_adjust_for_environment_all_branches(monkeypatch: MonkeyPatch) -> None:
    """Test adjust_for_environment() covers all conditional branches.

    Story 4.0.5: Comprehensive test of all validator logic branches.
    """
    # Test 1: Production (no adjustment)
    monkeypatch.delenv("APP_ENV", raising=False)
    settings_prod = Settings()
    assert settings_prod.qdrant_port == 6333

    # Test 2: Test environment (adjustments)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("CONTINUOUS_INTEGRATION", raising=False)
    settings_test = Settings()
    assert settings_test.qdrant_port == 6335
    assert settings_test.qdrant_collection_name == "financial_docs_test"

    # Test 3: CI environment (CI-specific adjustments)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    settings_ci = Settings()
    assert settings_ci.qdrant_collection_name == "financial_docs_ci"

    # Test 4: Development environment (treated as production for now)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    settings_dev = Settings()
    assert settings_dev.qdrant_port == 6333  # No adjustment for development yet
