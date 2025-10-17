"""Unit tests for raglite.shared.config module."""

import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from raglite.shared.config import Settings


@pytest.mark.p0
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


@pytest.mark.p1
@pytest.mark.unit
def test_settings_default_values(monkeypatch: MonkeyPatch) -> None:
    """Test Settings uses default values when env vars not set."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "required-key")

    settings = Settings()
    assert settings.qdrant_host == "localhost"
    assert settings.qdrant_port == 6333
    assert settings.embedding_model == "intfloat/e5-large-v2"
    assert settings.embedding_dimension == 1024


@pytest.mark.p0
@pytest.mark.unit
def test_settings_missing_api_key_optional(monkeypatch: MonkeyPatch) -> None:
    """Test Settings allows missing ANTHROPIC_API_KEY (optional until Story 1.11)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    settings = Settings()
    assert settings.anthropic_api_key is None  # Optional field, defaults to None


@pytest.mark.p0
@pytest.mark.unit
def test_settings_type_validation(monkeypatch: MonkeyPatch) -> None:
    """Test Settings validates port as integer."""
    monkeypatch.setenv("QDRANT_PORT", "invalid_port")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    with pytest.raises(ValidationError):
        Settings()
