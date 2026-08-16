"""Database Edge Cases for Story 9.7 - Connection, Authentication, and Error Handling.

This file tests database-specific edge cases:
- Connection failures and timeouts
- Authentication failures
- Database state errors
- Backup verification logic
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import psycopg2
import pytest

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.story_9_7,
]


class TestPrepareReingestionDatabaseEdgeCases:
    """Database error paths for prepare-reingestion.py script."""

    def test_backup_verification_missing_directory(self) -> None:
        """[P1] Backup verification fails when backups directory missing.

        EDGE CASE: backups/ directory does not exist
        EXPECTED: Script fails with clear error message
        """
        # Arrange: Import backup verification
        sys.path.insert(0, str(Path("scripts")))
        try:
            # Import dynamically to avoid test discovery issues
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "prepare_reingestion", "scripts/prepare-reingestion.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Mock backups directory to not exist
            with patch("pathlib.Path.exists", return_value=False):
                # Act: Verify backup
                backup_ok, message = module.verify_backup_exists()

                # Assert: Should fail with directory error
                assert not backup_ok
                assert "Backup directory not found" in message
        finally:
            sys.path.pop(0)

    def test_backup_verification_no_postgresql_backups(self) -> None:
        """[P1] Backup verification fails when PostgreSQL backups missing.

        EDGE CASE: backups/ exists but no PostgreSQL backup files
        EXPECTED: Script fails with "No PostgreSQL backups found"
        """
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "prepare_reingestion", "scripts/prepare-reingestion.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Mock: directory exists but no backup files
            with (
                patch("pathlib.Path.exists", return_value=True),
                patch("pathlib.Path.glob", return_value=[]),
            ):
                backup_ok, message = module.verify_backup_exists()

                assert not backup_ok
                assert "No PostgreSQL backups found" in message
        finally:
            sys.path.pop(0)

    @pytest.mark.slow
    def test_backup_verification_stale_backups(self) -> None:
        """[P1] Backup verification fails when backups too old.

        EDGE CASE: Backups exist but are >24 hours old
        EXPECTED: Script fails with age warning
        """
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "prepare_reingestion", "scripts/prepare-reingestion.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Mock: old backup files (25 hours ago)
            mock_path = MagicMock()
            old_mtime = (datetime.now() - timedelta(hours=25)).timestamp()
            mock_path.stat.return_value.st_mtime = old_mtime

            with (
                patch("pathlib.Path.exists", return_value=True),
                patch("pathlib.Path.glob", return_value=[mock_path]),
            ):
                backup_ok, message = module.verify_backup_exists()

                assert not backup_ok
                assert "hours old" in message.lower()
        finally:
            sys.path.pop(0)

    @pytest.mark.slow
    def test_cleanup_qdrant_connection_refused(self) -> None:
        """[P0] Cleanup handles Qdrant connection errors gracefully.

        ERROR PATH: Qdrant is offline/unreachable
        EXPECTED: Exception is caught and logged, not propagated
        """
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            from qdrant_client.http.exceptions import ResponseHandlingException

            spec = importlib.util.spec_from_file_location(
                "prepare_reingestion", "scripts/prepare-reingestion.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Mock Qdrant client that raises connection error on delete
            mock_client = MagicMock()
            mock_client.delete_collection.side_effect = ResponseHandlingException(
                "Connection refused"
            )

            # Act: Should NOT raise (error is caught)
            # create_collection will also be called, so mock it
            module.cleanup_qdrant(mock_client, dry_run=False)

            # Assert: delete_collection was called despite error
            assert mock_client.delete_collection.called
            # create_collection should be called after delete attempt
            assert mock_client.create_collection.called
        finally:
            sys.path.pop(0)

    @pytest.mark.slow
    def test_cleanup_postgresql_invalid_credentials(self) -> None:
        """[P0] Cleanup handles PostgreSQL authentication failures.

        ERROR PATH: Invalid database credentials
        EXPECTED: Script fails with authentication error
        """
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "prepare_reingestion", "scripts/prepare-reingestion.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Mock SafetyGuard to avoid checking in tests
            with (
                patch.object(module.SafetyGuard, "check_operation", return_value=True),
                patch(
                    "psycopg2.connect",
                    side_effect=psycopg2.OperationalError("authentication failed"),
                ),
            ):
                # Act & Assert
                with pytest.raises(psycopg2.OperationalError, match="authentication failed"):
                    module.cleanup_postgresql(
                        "postgresql://invalid:creds@localhost/db", dry_run=False
                    )
        finally:
            sys.path.pop(0)

    @pytest.mark.slow
    def test_cleanup_postgresql_timeout(self) -> None:
        """[P1] Cleanup handles PostgreSQL connection timeout.

        ERROR PATH: Database connection timeout
        EXPECTED: Script fails with timeout error
        """
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "prepare_reingestion", "scripts/prepare-reingestion.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Mock SafetyGuard to avoid checking in tests
            with (
                patch.object(module.SafetyGuard, "check_operation", return_value=True),
                patch("psycopg2.connect", side_effect=psycopg2.OperationalError("timeout")),
            ):
                with pytest.raises(psycopg2.OperationalError, match="timeout"):
                    module.cleanup_postgresql("postgresql://user:pass@localhost/db", dry_run=False)
        finally:
            sys.path.pop(0)

    @pytest.mark.slow
    def test_dry_run_no_database_access(self) -> None:
        """[P0] Dry-run mode does not access databases.

        CRITICAL: Dry-run must NOT make any database calls
        EXPECTED: No Qdrant/PostgreSQL operations are executed
        """
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "prepare_reingestion", "scripts/prepare-reingestion.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Mock clients
            mock_qdrant = MagicMock()
            mock_pg_connect = MagicMock()

            with patch("psycopg2.connect", mock_pg_connect):
                # Act: Run cleanup in dry-run mode
                module.cleanup_qdrant(mock_qdrant, dry_run=True)
                module.cleanup_postgresql("conn_str", dry_run=True)

                # Assert: No database operations called
                mock_qdrant.delete_collection.assert_not_called()
                mock_qdrant.create_collection.assert_not_called()
                mock_pg_connect.assert_not_called()
        finally:
            sys.path.pop(0)
