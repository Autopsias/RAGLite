"""Unit tests for raglite.shared.clients module."""

from unittest.mock import MagicMock, patch

import pytest
from pytest import MonkeyPatch

from raglite.shared.clients import get_claude_client, get_qdrant_client
from raglite.shared.config import Settings


@pytest.mark.p0
@pytest.mark.unit
@patch("raglite.shared.clients.QdrantClient")
def test_get_qdrant_client_success(mock_qdrant_class: MagicMock, test_settings: Settings) -> None:
    """Test get_qdrant_client returns configured client."""
    mock_client = MagicMock()
    mock_qdrant_class.return_value = mock_client

    client = get_qdrant_client()

    assert client == mock_client
    mock_qdrant_class.assert_called_once_with(
        host=test_settings.qdrant_host, port=test_settings.qdrant_port
    )


@pytest.mark.p1
@pytest.mark.unit
@patch("raglite.shared.clients.QdrantClient")
def test_get_qdrant_client_connection_error(mock_qdrant_class: MagicMock) -> None:
    """Test get_qdrant_client raises ConnectionError if Qdrant unavailable."""
    mock_qdrant_class.side_effect = Exception("Connection refused")

    with pytest.raises(ConnectionError, match="Failed to connect to Qdrant"):
        get_qdrant_client()


@pytest.mark.p0
@pytest.mark.unit
@patch("raglite.shared.clients.Anthropic")
@patch("raglite.shared.clients.settings")
def test_get_claude_client_success(
    mock_settings: MagicMock, mock_anthropic_class: MagicMock
) -> None:
    """Test get_claude_client returns configured client."""
    # Mock settings with valid API key
    mock_settings.anthropic_api_key = "valid-api-key-abc123"

    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    client = get_claude_client()

    assert client == mock_client
    mock_anthropic_class.assert_called_once_with(api_key="valid-api-key-abc123")


@pytest.mark.p0
@pytest.mark.unit
def test_get_claude_client_missing_api_key(monkeypatch: MonkeyPatch) -> None:
    """Test get_claude_client raises ValueError if API key not set."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "your_anthropic_api_key_here")

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY environment variable"):
        get_claude_client()


@pytest.mark.p0
@pytest.mark.unit
@patch("raglite.shared.clients.settings")
def test_get_claude_client_empty_api_key(mock_settings: MagicMock) -> None:
    """Test get_claude_client raises ValueError if API key is empty."""
    mock_settings.anthropic_api_key = ""

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        get_claude_client()
