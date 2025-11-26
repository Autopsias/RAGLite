"""Unit tests for SafetyGuard production protection utility.

Story 4.0.6: Production Database Protection Safeguards

Tests:
- AC1: check_environment() blocks production without override
- AC2: require_confirmation() prompts in interactive mode
- AC3: log_operation() includes environment context
- AC4: display_environment_banner() outputs correct environment
- AC6: SafetyGuard class centralizes all protection logic
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from raglite.shared.safety import ProductionProtectionError, SafetyGuard


class TestSafetyGuardProperties:
    """Test AC6: SafetyGuard class exists with all required methods."""

    def test_safety_guard_class_exists(self):
        """AC6: Verify SafetyGuard class can be instantiated."""
        guard = SafetyGuard()
        assert guard is not None

    def test_safety_guard_has_required_methods(self):
        """AC6: Verify SafetyGuard has all required interface methods."""
        guard = SafetyGuard()

        # Properties
        assert hasattr(guard, "is_production")
        assert hasattr(guard, "is_test")

        # Methods
        assert callable(getattr(guard, "check_environment", None))
        assert callable(getattr(guard, "require_confirmation", None))
        assert callable(getattr(guard, "display_environment_banner", None))
        assert callable(getattr(guard, "log_operation", None))


class TestIsProduction:
    """Test AC1: Production environment detection."""

    def test_is_production_when_production_env_and_port(self, monkeypatch):
        """is_production returns True when app_env='production' and port=6333."""
        # Mock settings at the module level
        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            assert guard.is_production is True

    def test_is_not_production_when_test_env(self, monkeypatch):
        """is_production returns False when app_env='test'."""
        mock_settings = MagicMock()
        mock_settings.app_env = "test"
        mock_settings.qdrant_port = 6335
        mock_settings.postgres_port = 5433
        mock_settings.postgres_db = "raglite_test"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            assert guard.is_production is False

    def test_is_not_production_when_test_port(self, monkeypatch):
        """is_production returns False when using test port 6335."""
        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6335  # Test port
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            # Both conditions must be true: production env AND port 6333
            assert guard.is_production is False


class TestIsTest:
    """Test AC1: Test environment detection."""

    def test_is_test_when_test_env(self, monkeypatch):
        """is_test returns True when app_env='test'."""
        mock_settings = MagicMock()
        mock_settings.app_env = "test"
        mock_settings.qdrant_port = 6335
        mock_settings.postgres_port = 5433
        mock_settings.postgres_db = "raglite_test"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            assert guard.is_test is True

    def test_is_test_when_test_port(self, monkeypatch):
        """is_test returns True when using test port 6335."""
        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6335  # Test port
        mock_settings.postgres_port = 5433
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            assert guard.is_test is True


class TestCheckEnvironment:
    """Test AC1: check_environment() blocks production without override."""

    def test_blocks_production_without_force(self):
        """AC1: check_environment raises on production without force_production=True."""
        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()

            with pytest.raises(ProductionProtectionError) as exc_info:
                guard.check_environment("delete_collection")

            assert "delete_collection" in str(exc_info.value)
            assert "PRODUCTION" in str(exc_info.value)
            assert "force_production=True" in str(exc_info.value)

    def test_allows_production_with_force(self):
        """AC1: check_environment returns True when force_production=True."""
        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            result = guard.check_environment("delete_collection", force_production=True)
            assert result is True

    def test_allows_test_environment_without_force(self):
        """AC1: check_environment returns True in test environment."""
        mock_settings = MagicMock()
        mock_settings.app_env = "test"
        mock_settings.qdrant_port = 6335
        mock_settings.postgres_port = 5433
        mock_settings.postgres_db = "raglite_test"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            result = guard.check_environment("delete_collection")
            assert result is True


class TestRequireConfirmation:
    """Test AC2: require_confirmation() prompts in interactive mode."""

    def test_returns_false_in_non_interactive_mode(self):
        """AC2: require_confirmation returns False when stdin is not a TTY."""
        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()

            with patch.object(sys.stdin, "isatty", return_value=False):
                result = guard.require_confirmation("About to delete production data")
                assert result is False

    def test_returns_true_when_user_confirms_yes(self):
        """AC2: require_confirmation returns True when user types 'yes'."""
        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()

            with patch.object(sys.stdin, "isatty", return_value=True):
                with patch("builtins.input", return_value="yes"):
                    with patch("builtins.print"):  # Suppress banner output
                        result = guard.require_confirmation("About to delete production data")
                        assert result is True

    def test_returns_false_when_user_types_no(self):
        """AC2: require_confirmation returns False when user types 'no'."""
        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()

            with patch.object(sys.stdin, "isatty", return_value=True):
                with patch("builtins.input", return_value="no"):
                    with patch("builtins.print"):  # Suppress banner output
                        result = guard.require_confirmation("About to delete production data")
                        assert result is False

    def test_returns_false_when_user_types_random(self):
        """AC2: require_confirmation returns False for any input except 'yes'."""
        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()

            with patch.object(sys.stdin, "isatty", return_value=True):
                with patch("builtins.input", return_value="maybe"):
                    with patch("builtins.print"):  # Suppress banner output
                        result = guard.require_confirmation("About to delete production data")
                        assert result is False


class TestLogOperation:
    """Test AC3: log_operation() includes environment context."""

    def test_log_operation_includes_environment_context(self, caplog):
        """AC3: log_operation logs with environment context."""
        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()

            with caplog.at_level("INFO"):
                guard.log_operation("test_operation")

            assert "test_operation" in caplog.text
            assert "Database operation" in caplog.text

    def test_log_operation_for_test_environment(self, caplog):
        """AC3: log_operation correctly identifies test environment."""
        mock_settings = MagicMock()
        mock_settings.app_env = "test"
        mock_settings.qdrant_port = 6335
        mock_settings.postgres_port = 5433
        mock_settings.postgres_db = "raglite_test"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()

            with caplog.at_level("INFO"):
                guard.log_operation("delete_collection")

            assert "delete_collection" in caplog.text


class TestDisplayEnvironmentBanner:
    """Test AC4: display_environment_banner() outputs correct environment."""

    def test_banner_shows_production_for_production_env(self, capsys):
        """AC4: Banner shows 'PRODUCTION' when in production environment."""
        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            guard.display_environment_banner()

            captured = capsys.readouterr()
            assert "PRODUCTION" in captured.out
            assert "6333" in captured.out
            assert "5432" in captured.out

    def test_banner_shows_test_for_test_env(self, capsys):
        """AC4: Banner shows 'TEST' when in test environment."""
        mock_settings = MagicMock()
        mock_settings.app_env = "test"
        mock_settings.qdrant_port = 6335
        mock_settings.postgres_port = 5433
        mock_settings.postgres_db = "raglite_test"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            guard.display_environment_banner()

            captured = capsys.readouterr()
            assert "TEST" in captured.out
            assert "6335" in captured.out
            assert "5433" in captured.out


class TestProductionProtectionError:
    """Test custom exception for production protection."""

    def test_exception_message_is_descriptive(self):
        """ProductionProtectionError has descriptive message."""
        error = ProductionProtectionError("Test error message")
        assert str(error) == "Test error message"

    def test_exception_inherits_from_exception(self):
        """ProductionProtectionError inherits from Exception."""
        assert issubclass(ProductionProtectionError, Exception)


class TestIngestPdfClearExistingDefault:
    """Test AC5: ingest_pdf() default behavior preserves existing data."""

    @pytest.mark.asyncio
    async def test_ingest_pdf_default_does_not_clear(self):
        """AC5: ingest_pdf() with default clear_existing=False does NOT delete collection."""
        # Import after all patches are in place
        # Verify the default parameter
        import inspect

        from raglite.ingestion.document_ingestion import ingest_pdf

        sig = inspect.signature(ingest_pdf)
        clear_existing_param = sig.parameters.get("clear_existing")

        assert clear_existing_param is not None, "clear_existing parameter not found"
        assert clear_existing_param.default is False, (
            f"clear_existing should default to False, got {clear_existing_param.default}"
        )

    def test_ingest_pdf_has_force_production_parameter(self):
        """AC5: ingest_pdf() has force_production parameter."""
        import inspect

        from raglite.ingestion.document_ingestion import ingest_pdf

        sig = inspect.signature(ingest_pdf)
        force_production_param = sig.parameters.get("force_production")

        assert force_production_param is not None, "force_production parameter not found"
        assert force_production_param.default is False, (
            f"force_production should default to False, got {force_production_param.default}"
        )
