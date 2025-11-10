"""Unit tests for raglite.shared.clients module."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from pytest import MonkeyPatch

# Mock dependencies to prevent import errors during unit testing
# IMPORTANT: Mock only for unit test scope to avoid affecting integration tests
# We will use scoped patches instead of global sys.modules mocking
sys.modules["anthropic"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["qdrant_client"] = MagicMock()

# NOTE: We do NOT mock mistralai here because integration tests need the real module
# Instead, we mock it specifically in the unit tests that need it

from raglite.shared.clients import get_claude_client, get_qdrant_client
from raglite.shared.config import Settings


@pytest.mark.priority("P0")
@pytest.mark.unit
@patch("raglite.shared.clients.QdrantClient")
def test_get_qdrant_client_success(mock_qdrant_class: MagicMock, test_settings: Settings) -> None:
    """Test get_qdrant_client returns configured client."""
    # Reset global singleton before test
    import raglite.shared.clients as clients_module

    clients_module._qdrant_client = None

    mock_client = MagicMock()
    mock_qdrant_class.return_value = mock_client

    client = get_qdrant_client()

    assert client == mock_client
    # In test environment, timeout is reduced to 1s to prevent test hangs
    mock_qdrant_class.assert_called_once_with(
        host=test_settings.qdrant_host, port=test_settings.qdrant_port, timeout=1
    )


@pytest.mark.priority("P1")
@pytest.mark.unit
@patch("raglite.shared.clients.QdrantClient")
@patch("raglite.shared.clients.time.sleep")  # Mock time.sleep to prevent real delays
def test_get_qdrant_client_connection_error(
    mock_sleep: MagicMock, mock_qdrant_class: MagicMock
) -> None:
    """Test get_qdrant_client raises ConnectionError if Qdrant unavailable."""
    # Reset global singleton before test
    import raglite.shared.clients as clients_module

    clients_module._qdrant_client = None

    mock_qdrant_class.side_effect = Exception("Connection refused")
    mock_sleep.return_value = None  # Mock sleep to return immediately

    with pytest.raises(ConnectionError, match="Failed to connect to Qdrant"):
        get_qdrant_client()

    # Verify that sleep was called for retry attempts
    # Should be called twice (for first two failed attempts) before final failure
    assert mock_sleep.call_count == 2

    # Verify the retry delays were called correctly
    # In test environment, delays are capped at 0.5s to prevent test hangs
    expected_calls = [0.5, 0.5]  # Both retries capped at 0.5s in test environment
    actual_calls = [call.args[0] for call in mock_sleep.call_args_list]
    assert actual_calls == expected_calls


@pytest.mark.priority("P0")
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


@pytest.mark.priority("P0")
@pytest.mark.unit
def test_get_claude_client_missing_api_key(monkeypatch: MonkeyPatch) -> None:
    """Test get_claude_client raises ValueError if API key not set."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "your_anthropic_api_key_here")

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY environment variable"):
        get_claude_client()


@pytest.mark.priority("P0")
@pytest.mark.unit
@patch("raglite.shared.clients.settings")
def test_get_claude_client_empty_api_key(mock_settings: MagicMock) -> None:
    """Test get_claude_client raises ValueError if API key is empty."""
    mock_settings.anthropic_api_key = ""

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        get_claude_client()
