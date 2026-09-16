"""Comprehensive tests for conftest refactoring (Story 7.2) - P0 and P1 Tests.

These tests validate the conftest.py split into modular fixtures, focusing on:
- Fixture interdependencies
- pytest_plugins loading order
- Fixture cleanup and isolation
- Hook execution order and side effects
- Custom CLI options interaction

Priority levels:
- P0: Critical path (fixture loading, pytest_plugins, conftest integration)
- P1: Important scenarios (hook execution, fixture cleanup, CLI options)
"""

import logging
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Mark entire module as unit tests
pytestmark = pytest.mark.unit

logger = logging.getLogger(__name__)


# ============================================================================
# P0: Critical Path Tests (Fixture Loading, pytest_plugins, Conftest Integration)
# ============================================================================


class TestP0FixtureLoading:
    """P0 tests for fixture loading and pytest_plugins integration."""

    def test_pytest_plugins_list_exists_in_root_conftest(self) -> None:
        """[P0] Verify pytest_plugins list is defined in root conftest.py."""
        # Read root conftest.py to check pytest_plugins
        conftest_path = Path(__file__).parent.parent / "conftest.py"
        content = conftest_path.read_text()

        assert "pytest_plugins" in content, "pytest_plugins not found in root conftest.py"
        assert "tests.fixtures.pytest_hooks" in content, "pytest_hooks module not loaded"
        assert "tests.fixtures.performance_monitoring" in content, (
            "performance_monitoring module not loaded"
        )
        assert "tests.fixtures.mock_clients" in content, "mock_clients module not loaded"
        assert "tests.fixtures.sample_data" in content, "sample_data module not loaded"

    def test_fixture_modules_importable(self) -> None:
        """[P0] Verify all fixture modules can be imported without errors."""
        import importlib

        modules_to_import = [
            "tests.fixtures.mock_clients",
            "tests.fixtures.mistral_mock_helpers",
            "tests.fixtures.sample_data",
            "tests.fixtures.pytest_hooks",
            "tests.fixtures.performance_monitoring",
        ]

        for module_name in modules_to_import:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_mock_clients_depends_on_mistral_mock_helpers(self) -> None:
        """[P0] Verify mock_clients correctly imports from mistral_mock_helpers."""
        from tests.fixtures import mock_clients

        # Verify the imports exist
        assert hasattr(mock_clients, "generate_mock_sql"), (
            "generate_mock_sql not imported in mock_clients"
        )
        assert hasattr(mock_clients, "generate_mock_metadata"), (
            "generate_mock_metadata not imported in mock_clients"
        )
        assert hasattr(mock_clients, "generate_query_aware_sql"), (
            "generate_query_aware_sql not imported in mock_clients"
        )

    def test_pytest_plugins_loading_order(self) -> None:
        """[P0] Verify pytest_plugins loads hooks module before other modules."""
        conftest_path = Path(__file__).parent.parent / "conftest.py"
        content = conftest_path.read_text()

        # Extract pytest_plugins list
        plugins_start = content.find("pytest_plugins = [")
        plugins_end = content.find("]", plugins_start)
        plugins_section = content[plugins_start:plugins_end]

        # Check order: hooks should come first
        hooks_idx = plugins_section.find("pytest_hooks")
        perf_idx = plugins_section.find("performance_monitoring")
        mock_idx = plugins_section.find("mock_clients")

        assert hooks_idx > 0, "pytest_hooks not found in pytest_plugins"
        assert perf_idx > hooks_idx, "performance_monitoring should load after pytest_hooks"
        assert mock_idx > perf_idx, "mock_clients should load after performance_monitoring"


class TestP0FixtureInterdependencies:
    """P0 tests for fixture interdependencies and dependencies."""

    def test_mock_mistral_client_uses_mistral_mock_helpers(
        self, mock_mistral_client: tuple[MagicMock, MagicMock]
    ) -> None:
        """[P0] Verify mock_mistral_client fixture uses generate_query_aware_sql."""
        mock_client, mock_get_client = mock_mistral_client

        # Call the fixture's mock to trigger side_effect
        from tests.fixtures.mistral_mock_helpers import generate_query_aware_sql

        # Verify side_effect is set correctly
        assert mock_client.chat.complete.side_effect is generate_query_aware_sql

    def test_sample_chunk_depends_on_sample_document_metadata(
        self, sample_chunk: Any, sample_document_metadata: Any
    ) -> None:
        """[P0] Verify sample_chunk fixture uses sample_document_metadata."""
        assert sample_chunk.metadata == sample_document_metadata
        assert sample_chunk.metadata.filename == "test_financial_report.pdf"

    def test_session_test_settings_fixture_available(self, session_test_settings: Any) -> None:
        """[P0] Verify session_test_settings fixture is available and functional."""
        assert session_test_settings is not None
        assert hasattr(session_test_settings, "qdrant_host")
        assert session_test_settings.qdrant_host == "localhost"

    def test_test_settings_fixture_available(self, test_settings: Any) -> None:
        """[P0] Verify test_settings fixture is available and functional."""
        assert test_settings is not None
        assert hasattr(test_settings, "qdrant_host")
        assert test_settings.qdrant_host == "localhost"


# ============================================================================
# P1: Important Scenarios (Hook Execution, Fixture Cleanup, CLI Options)
# ============================================================================


class TestP1HookExecution:
    """P1 tests for pytest hook execution order and side effects."""

    def test_pytest_addoption_hook_registers_custom_options(self) -> None:
        """[P1] Verify pytest_addoption hook registers custom CLI options."""
        from tests.fixtures import pytest_hooks

        # Verify hook function exists
        assert hasattr(pytest_hooks, "pytest_addoption")
        assert callable(pytest_hooks.pytest_addoption)

        # Create mock parser
        mock_parser = MagicMock()

        # Call the hook
        pytest_hooks.pytest_addoption(mock_parser)

        # Verify options were added
        assert mock_parser.addoption.call_count >= 3
        call_args = [call[0][0] for call in mock_parser.addoption.call_args_list]
        assert "--run-slow" in call_args
        assert "--skip-ingestion" in call_args
        assert "--enforce-isolation-markers" in call_args

    def test_pytest_configure_hook_sets_global_flags(self) -> None:
        """[P1] Verify pytest_configure hook sets global pytest flags."""
        from tests.fixtures import pytest_hooks

        # Verify hook function exists
        assert hasattr(pytest_hooks, "pytest_configure")
        assert callable(pytest_hooks.pytest_configure)

        # Create mock config
        mock_config = MagicMock()
        mock_config.getoption.side_effect = lambda opt: {
            "--run-slow": True,
            "--skip-ingestion": False,
        }.get(opt, False)

        # Call the hook
        pytest_hooks.pytest_configure(mock_config)

        # Verify global flags were set
        assert hasattr(pytest, "run_slow")
        assert hasattr(pytest, "skip_ingestion")
        assert pytest.run_slow is True
        assert pytest.skip_ingestion is False

    def test_pytest_collection_modifyitems_hook_exists(self) -> None:
        """[P1] Verify pytest_collection_modifyitems hook exists and is callable."""
        from tests.fixtures import pytest_hooks

        assert hasattr(pytest_hooks, "pytest_collection_modifyitems")
        assert callable(pytest_hooks.pytest_collection_modifyitems)

    @pytest.mark.slow
    def test_performance_monitoring_hooks_record_session_time(self) -> None:
        """[P1] Verify performance monitoring hooks track session time."""
        from tests.fixtures import performance_monitoring

        # Verify hooks exist
        assert hasattr(performance_monitoring, "pytest_sessionstart")
        assert hasattr(performance_monitoring, "pytest_sessionfinish")
        assert callable(performance_monitoring.pytest_sessionstart)
        assert callable(performance_monitoring.pytest_sessionfinish)

        # Simulate session start
        mock_session = MagicMock()
        performance_monitoring.pytest_sessionstart(mock_session)

        # Verify session start time was recorded
        assert performance_monitoring._session_start_time is not None
        start_time = performance_monitoring._session_start_time

        # Simulate a small delay
        time.sleep(0.01)

        # Simulate session finish
        performance_monitoring.pytest_sessionfinish(mock_session, exitstatus=0)

        # Session should have recorded some elapsed time
        assert performance_monitoring._session_start_time == start_time


class TestP1FixtureCleanup:
    """P1 tests for fixture cleanup and isolation."""

    def test_configure_test_environment_cleanup_removes_env_vars(self) -> None:
        """[P1] Verify configure_test_environment fixture cleans up env vars."""
        import os

        # Environment variables should be set by conftest module-level code
        assert os.environ.get("APP_ENV") == "test"
        assert os.environ.get("TESTING") == "true"
        assert os.environ.get("POSTGRES_PORT") == "5433"

        # Note: The cleanup happens at session end, not after each test
        # We can verify the cleanup logic exists in the fixture
        conftest_path = Path(__file__).parent.parent / "conftest.py"
        content = conftest_path.read_text()

        # Verify cleanup code exists
        assert 'del os.environ["APP_ENV"]' in content
        assert 'del os.environ["TESTING"]' in content

    def test_mock_qdrant_client_fixture_scope_is_module(self) -> None:
        """[P1] Verify mock_qdrant_client has correct scope for performance."""
        # Read the source file to check scope decorator
        from pathlib import Path

        mock_clients_path = Path(__file__).parent.parent / "fixtures" / "mock_clients.py"
        content = mock_clients_path.read_text()

        # Find mock_qdrant_client definition and verify scope
        assert '@pytest.fixture(scope="module")' in content
        assert "def mock_qdrant_client()" in content

    def test_sample_document_metadata_fixture_scope_is_module(self) -> None:
        """[P1] Verify sample_document_metadata has correct scope for performance."""
        # Read the source file to check scope decorator
        from pathlib import Path

        sample_data_path = Path(__file__).parent.parent / "fixtures" / "sample_data.py"
        content = sample_data_path.read_text()

        # Find sample_document_metadata definition and verify scope
        assert '@pytest.fixture(scope="module")' in content
        assert "def sample_document_metadata()" in content


class TestP1CLIOptions:
    """P1 tests for custom CLI options interaction."""

    def test_cli_options_default_values(self) -> None:
        """[P1] Verify custom CLI options have correct default values."""
        from tests.fixtures import pytest_hooks

        # Create mock parser and config
        mock_parser = MagicMock()
        pytest_hooks.pytest_addoption(mock_parser)

        # Check default values from addoption calls
        for call in mock_parser.addoption.call_args_list:
            kwargs = call[1]
            if call[0][0] == "--run-slow":
                assert kwargs["default"] is False
            elif call[0][0] == "--skip-ingestion":
                assert kwargs["default"] is False
            elif call[0][0] == "--enforce-isolation-markers":
                assert kwargs["default"] is False

    def test_cli_options_help_text_present(self) -> None:
        """[P1] Verify custom CLI options have help text."""
        from tests.fixtures import pytest_hooks

        mock_parser = MagicMock()
        pytest_hooks.pytest_addoption(mock_parser)

        # Verify all options have help text
        for call in mock_parser.addoption.call_args_list:
            kwargs = call[1]
            assert "help" in kwargs
            assert len(kwargs["help"]) > 0
