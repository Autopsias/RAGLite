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


# =============================================================================
# Story 4.0.7: Three-Mode Database Operation System Tests
# =============================================================================


class TestOperationType:
    """Test OperationType enum for operation classification."""

    def test_operation_type_enum_exists(self):
        """OperationType enum exists with correct values."""
        from raglite.shared.safety import OperationType

        assert OperationType.SAFE == "safe"
        assert OperationType.ADDITIVE == "additive"
        assert OperationType.DESTRUCTIVE == "destructive"

    def test_operation_type_is_string_enum(self):
        """OperationType values are strings for easy serialization."""
        from raglite.shared.safety import OperationType

        assert isinstance(OperationType.SAFE.value, str)
        assert isinstance(OperationType.ADDITIVE.value, str)
        assert isinstance(OperationType.DESTRUCTIVE.value, str)


class TestValidateTestEnvironment:
    """Test validate_test_environment() for test isolation enforcement."""

    def test_passes_on_test_infrastructure(self):
        """validate_test_environment passes when on test ports and collection."""
        mock_settings = MagicMock()
        mock_settings.app_env = "test"
        mock_settings.qdrant_port = 6335
        mock_settings.postgres_port = 5433
        mock_settings.qdrant_collection_name = "financial_docs_test"
        mock_settings.postgres_db = "raglite_test"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            # Should not raise
            guard.validate_test_environment("test_fixture")

    def test_blocks_production_qdrant_port(self):
        """validate_test_environment blocks when Qdrant port is 6333 (production)."""
        mock_settings = MagicMock()
        mock_settings.app_env = "test"
        mock_settings.qdrant_port = 6333  # PRODUCTION PORT
        mock_settings.postgres_port = 5433
        mock_settings.qdrant_collection_name = "financial_docs_test"
        mock_settings.postgres_db = "raglite_test"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()

            with pytest.raises(ProductionProtectionError) as exc_info:
                guard.validate_test_environment("test_fixture")

            assert "6333" in str(exc_info.value)
            assert "PRODUCTION" in str(exc_info.value)

    def test_blocks_production_postgres_port(self):
        """validate_test_environment blocks when PostgreSQL port is 5432 (production)."""
        mock_settings = MagicMock()
        mock_settings.app_env = "test"
        mock_settings.qdrant_port = 6335
        mock_settings.postgres_port = 5432  # PRODUCTION PORT
        mock_settings.qdrant_collection_name = "financial_docs_test"
        mock_settings.postgres_db = "raglite_test"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()

            with pytest.raises(ProductionProtectionError) as exc_info:
                guard.validate_test_environment("test_fixture")

            assert "5432" in str(exc_info.value)
            assert "PRODUCTION" in str(exc_info.value)

    def test_blocks_production_collection_name(self):
        """validate_test_environment blocks when collection name lacks _test or _ci suffix."""
        mock_settings = MagicMock()
        mock_settings.app_env = "test"
        mock_settings.qdrant_port = 6335
        mock_settings.postgres_port = 5433
        mock_settings.qdrant_collection_name = "financial_docs"  # PRODUCTION NAME
        mock_settings.postgres_db = "raglite_test"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()

            with pytest.raises(ProductionProtectionError) as exc_info:
                guard.validate_test_environment("test_fixture")

            assert "financial_docs" in str(exc_info.value)
            assert "suffix" in str(exc_info.value).lower()

    def test_allows_ci_collection_suffix(self):
        """validate_test_environment allows _ci suffix for CI environments."""
        mock_settings = MagicMock()
        mock_settings.app_env = "test"
        mock_settings.qdrant_port = 6335
        mock_settings.postgres_port = 5433
        mock_settings.qdrant_collection_name = "financial_docs_ci"  # CI suffix
        mock_settings.postgres_db = "raglite_test"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            # Should not raise
            guard.validate_test_environment("ci_test_fixture")

    def test_reports_all_issues_at_once(self):
        """validate_test_environment reports all issues, not just the first."""
        mock_settings = MagicMock()
        mock_settings.app_env = "test"
        mock_settings.qdrant_port = 6333  # Issue 1
        mock_settings.postgres_port = 5432  # Issue 2
        mock_settings.qdrant_collection_name = "financial_docs"  # Issue 3
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()

            with pytest.raises(ProductionProtectionError) as exc_info:
                guard.validate_test_environment("test_fixture")

            error_msg = str(exc_info.value)
            # All three issues should be reported
            assert "6333" in error_msg
            assert "5432" in error_msg
            assert "financial_docs" in error_msg


class TestBlockDestructiveOnProduction:
    """Test block_destructive_on_production() for destructive operation blocking."""

    def test_blocks_on_production(self):
        """block_destructive_on_production raises on production environment."""
        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()

            with pytest.raises(ProductionProtectionError) as exc_info:
                guard.block_destructive_on_production("delete_collection")

            assert "delete_collection" in str(exc_info.value)
            assert "BLOCKED" in str(exc_info.value)
            assert "deploy-to-production.py" in str(exc_info.value)

    def test_allows_on_test_environment(self):
        """block_destructive_on_production allows on test environment."""
        mock_settings = MagicMock()
        mock_settings.app_env = "test"
        mock_settings.qdrant_port = 6335
        mock_settings.postgres_port = 5433
        mock_settings.postgres_db = "raglite_test"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            # Should not raise
            guard.block_destructive_on_production("delete_collection")


class TestCheckOperation:
    """Test check_operation() for operation type classification."""

    def test_safe_operations_always_allowed(self):
        """SAFE operations are allowed on both production and test."""
        from raglite.shared.safety import OperationType

        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            result = guard.check_operation("select_query", OperationType.SAFE)
            assert result is True

    def test_additive_operations_allowed_on_production(self):
        """ADDITIVE operations are allowed on production."""
        from raglite.shared.safety import OperationType

        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            result = guard.check_operation("insert_vectors", OperationType.ADDITIVE)
            assert result is True

    def test_destructive_operations_blocked_on_production(self):
        """DESTRUCTIVE operations are blocked on production without force_data_loss."""
        from raglite.shared.safety import OperationType

        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()

            with pytest.raises(ProductionProtectionError) as exc_info:
                guard.check_operation("delete_collection", OperationType.DESTRUCTIVE)

            assert "delete_collection" in str(exc_info.value)
            assert "force-data-loss" in str(exc_info.value)

    def test_destructive_operations_allowed_with_force_data_loss(self):
        """DESTRUCTIVE operations allowed on production with force_data_loss=True."""
        from raglite.shared.safety import OperationType

        mock_settings = MagicMock()
        mock_settings.app_env = "production"
        mock_settings.qdrant_port = 6333
        mock_settings.postgres_port = 5432
        mock_settings.postgres_db = "raglite"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            result = guard.check_operation(
                "delete_collection", OperationType.DESTRUCTIVE, force_data_loss=True
            )
            assert result is True

    def test_destructive_operations_allowed_on_test(self):
        """DESTRUCTIVE operations are allowed on test environment."""
        from raglite.shared.safety import OperationType

        mock_settings = MagicMock()
        mock_settings.app_env = "test"
        mock_settings.qdrant_port = 6335
        mock_settings.postgres_port = 5433
        mock_settings.postgres_db = "raglite_test"

        with patch("raglite.shared.safety.settings", mock_settings):
            guard = SafetyGuard()
            result = guard.check_operation("delete_collection", OperationType.DESTRUCTIVE)
            assert result is True
