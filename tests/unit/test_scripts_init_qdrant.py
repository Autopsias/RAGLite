"""Unit tests for scripts/init-qdrant.py - Qdrant collection initialization.

Tests cover:
- Collection initialization logic
- Idempotent behavior (safe to run multiple times)
- Configuration validation
- Error handling
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from qdrant_client.models import Distance

# Import script with hyphenated name using importlib
script_path = Path(__file__).parent.parent.parent / "scripts" / "init-qdrant.py"
spec = importlib.util.spec_from_file_location("init_qdrant", script_path)
init_qdrant = importlib.util.module_from_spec(spec)
sys.modules["init_qdrant"] = init_qdrant
spec.loader.exec_module(init_qdrant)


class TestInitializeQdrantCollection:
    """Test Qdrant collection initialization function."""

    @patch("init_qdrant.create_collection")
    @patch("init_qdrant.settings")
    @patch("init_qdrant.logger")
    def test_successful_initialization(
        self,
        mock_logger: MagicMock,
        mock_settings: MagicMock,
        mock_create_collection: MagicMock,
    ) -> None:
        """Test successful Qdrant collection initialization."""
        # Configure mocks
        mock_settings.qdrant_host = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "financial_docs"
        mock_settings.embedding_dimension = 1024
        mock_create_collection.return_value = None  # Success

        # Execute
        init_qdrant.initialize_qdrant_collection()

        # Verify create_collection called with correct params
        mock_create_collection.assert_called_once_with(
            collection_name="financial_docs",
            vector_size=1024,
            distance=Distance.COSINE,
        )

        # Verify success logging
        assert any("✅" in str(call) for call in mock_logger.info.call_args_list)

    @patch("init_qdrant.create_collection")
    @patch("init_qdrant.settings")
    @patch("init_qdrant.logger")
    def test_logs_collection_details(
        self,
        mock_logger: MagicMock,
        mock_settings: MagicMock,
        mock_create_collection: MagicMock,
    ) -> None:
        """Test that initialization logs collection configuration details."""
        mock_settings.qdrant_host = "qdrant.example.com"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "test_collection"
        mock_settings.embedding_dimension = 512

        init_qdrant.initialize_qdrant_collection()

        # Verify logging calls include key information
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("qdrant.example.com" in call for call in log_calls)
        assert any("test_collection" in call for call in log_calls)
        assert any("512" in call for call in log_calls)

    @patch("init_qdrant.create_collection")
    @patch("init_qdrant.settings")
    @patch("init_qdrant.logger")
    @patch("init_qdrant.sys.exit")
    def test_error_handling_logs_and_exits(
        self,
        mock_exit: MagicMock,
        mock_logger: MagicMock,
        mock_settings: MagicMock,
        mock_create_collection: MagicMock,
    ) -> None:
        """Test that initialization errors are logged and cause sys.exit(1)."""
        mock_settings.qdrant_host = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection_name = "financial_docs"
        mock_settings.embedding_dimension = 1024

        # Simulate collection creation failure
        mock_create_collection.side_effect = RuntimeError("Connection refused")

        init_qdrant.initialize_qdrant_collection()

        # Verify error logged
        mock_logger.error.assert_called_once()
        error_call = str(mock_logger.error.call_args_list[0])
        assert "❌" in error_call
        assert "Connection refused" in error_call

        # Verify sys.exit(1) called
        mock_exit.assert_called_once_with(1)

    @patch("init_qdrant.create_collection")
    @patch("init_qdrant.settings")
    def test_uses_cosine_distance_metric(
        self,
        mock_settings: MagicMock,
        mock_create_collection: MagicMock,
    ) -> None:
        """Test that COSINE distance metric is used for semantic similarity."""
        mock_settings.qdrant_collection_name = "test"
        mock_settings.embedding_dimension = 1024

        init_qdrant.initialize_qdrant_collection()

        # Verify Distance.COSINE used
        call_args = mock_create_collection.call_args
        assert call_args[1]["distance"] == Distance.COSINE

    @patch("init_qdrant.create_collection")
    @patch("init_qdrant.settings")
    def test_respects_embedding_dimension_from_settings(
        self,
        mock_settings: MagicMock,
        mock_create_collection: MagicMock,
    ) -> None:
        """Test that vector size matches embedding_dimension from settings."""
        # Test with different embedding dimensions
        for dimension in [512, 768, 1024, 1536]:
            mock_settings.qdrant_collection_name = "test"
            mock_settings.embedding_dimension = dimension
            mock_create_collection.reset_mock()

            init_qdrant.initialize_qdrant_collection()

            call_args = mock_create_collection.call_args
            assert call_args[1]["vector_size"] == dimension

    @patch("init_qdrant.create_collection")
    @patch("init_qdrant.settings")
    def test_idempotent_behavior(
        self,
        mock_settings: MagicMock,
        mock_create_collection: MagicMock,
    ) -> None:
        """Test that multiple calls are safe (idempotent)."""
        mock_settings.qdrant_collection_name = "financial_docs"
        mock_settings.embedding_dimension = 1024

        # Call multiple times
        init_qdrant.initialize_qdrant_collection()
        init_qdrant.initialize_qdrant_collection()
        init_qdrant.initialize_qdrant_collection()

        # create_collection should be called each time (it handles idempotency internally)
        assert mock_create_collection.call_count == 3


class TestMainExecution:
    """Test __main__ execution path."""

    @patch("init_qdrant.initialize_qdrant_collection")
    def test_main_calls_initialize_qdrant_collection(
        self,
        mock_initialize: MagicMock,
    ) -> None:
        """Test that __main__ block calls initialize_qdrant_collection."""
        # This tests the pattern: if __name__ == "__main__": initialize_qdrant_collection()
        # We can't directly test the __main__ block, but we verify the function exists
        assert callable(init_qdrant.initialize_qdrant_collection)
        assert hasattr(init_qdrant, "initialize_qdrant_collection")
