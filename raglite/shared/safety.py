"""Database operation safety controls for production protection.

This module provides centralized safeguards to prevent accidental modification
or deletion of production database data. Created after 2025-11-25 incident
where production databases were found empty.

Story 4.0.6: Production Database Protection Safeguards
Story 4.0.7: Three-Mode Database Operation System (2025-11-27)

The three modes are:
1. TEST - Full CRUD on test databases (ports 6335/5433), blocked from production
2. PRODUCTION READ/WRITE - Read/Insert/Update on production, blocked from deletion
3. PRODUCTION DEPLOY - Explicit schema updates with typed confirmation
"""

from __future__ import annotations

import logging
import os
import sys
from enum import StrEnum

from raglite.shared.config import settings

logger = logging.getLogger(__name__)


class OperationType(StrEnum):
    """Classify database operations by safety level.

    Used by SafetyGuard.check_operation() to determine if an operation
    is allowed based on the current environment.
    """

    # SAFE: Can run on production without confirmation
    # Examples: SELECT, COUNT, CREATE IF NOT EXISTS
    SAFE = "safe"

    # ADDITIVE: Adds to production, needs confirmation but no data loss
    # Examples: INSERT, CREATE INDEX, ADD COLUMN
    ADDITIVE = "additive"

    # DESTRUCTIVE: May cause data loss, needs --force-data-loss flag
    # Examples: DELETE, DROP, TRUNCATE, delete_collection()
    DESTRUCTIVE = "destructive"


class ProductionProtectionError(Exception):
    """Raised when a destructive operation is attempted on production without override."""

    pass


class SafetyGuard:
    """Centralized database operation safety controls.

    Prevents accidental modification of production databases by:
    1. Checking APP_ENV before destructive operations
    2. Requiring explicit confirmation for production changes
    3. Logging all operations with environment context
    4. Validating test environment before any test fixture operations

    Example:
        >>> guard = SafetyGuard()
        >>> guard.check_environment("delete_collection")  # Raises on production
        >>> guard.check_environment("delete_collection", force_production=True)  # OK
        >>> guard.validate_test_environment("test_fixture")  # Raises if on production ports
    """

    # Port constants for environment validation
    PRODUCTION_QDRANT_PORT = 6333
    PRODUCTION_POSTGRES_PORT = 5432
    TEST_QDRANT_PORT = 6335
    TEST_POSTGRES_PORT = 5433

    # Emergency lockfile path (kill switch for all production operations)
    EMERGENCY_LOCKFILE = "/tmp/raglite_production_locked"  # nosec B108 - Platform-standard temp dir

    def __init__(self) -> None:
        """Initialize SafetyGuard with current environment settings."""
        self._app_env = settings.app_env
        self._qdrant_port = settings.qdrant_port
        self._postgres_port = settings.postgres_port

    @property
    def is_production(self) -> bool:
        """Check if current environment is production.

        Returns True if app_env is 'production' AND using production ports.
        """
        return self._app_env == "production" and self._qdrant_port == 6333

    @property
    def is_test(self) -> bool:
        """Check if current environment is test.

        Returns True if app_env is 'test' OR using test ports (6335/5433).
        """
        return self._app_env == "test" or self._qdrant_port == 6335

    def check_environment(
        self,
        operation: str,
        force_production: bool = False,
    ) -> bool:
        """Validate environment before destructive operation.

        Args:
            operation: Description of operation (e.g., "delete_collection")
            force_production: If True, allow operation on production

        Returns:
            True if operation should proceed

        Raises:
            ProductionProtectionError: If production operation without force flag
        """
        self.log_operation(operation)

        if self.is_production and not force_production:
            raise ProductionProtectionError(
                f"Operation '{operation}' blocked on PRODUCTION database. "
                f"Set force_production=True or APP_ENV=test to proceed."
            )
        return True

    def require_confirmation(self, message: str) -> bool:
        """Prompt for confirmation in interactive mode.

        Args:
            message: Warning message to display

        Returns:
            True if user confirms, False otherwise (or non-interactive)
        """
        is_interactive = sys.stdin.isatty()

        if not is_interactive:
            logger.warning(
                "Non-interactive mode - operation requires confirmation",
                extra={"warning_text": message, "environment": self._app_env},
            )
            return False

        self.display_environment_banner()
        print(f"\n{'!' * 60}")
        print(f"WARNING: {message}")
        print(f"{'!' * 60}")

        response = input("\nType 'yes' to confirm: ")
        confirmed = response.lower().strip() == "yes"

        logger.info(
            "User confirmation result",
            extra={"confirmed": confirmed, "operation": message},
        )

        return confirmed

    def require_typed_confirmation(self, operation: str, data_description: str) -> bool:
        """Require user to type EXACT confirmation phrase for destructive operations.

        This provides defense-in-depth by requiring conscious action rather than
        just a simple "yes" confirmation. Prevents accidental script execution
        with hardcoded force flags.

        Args:
            operation: Name of the operation (e.g., "cleanup_production")
            data_description: What will be deleted (e.g., "financial documents and tables")

        Returns:
            True if user typed exact confirmation phrase

        Raises:
            ProductionProtectionError: If not in interactive terminal or phrase doesn't match
        """
        if not sys.stdin.isatty():
            raise ProductionProtectionError(
                f"Cannot confirm '{operation}' - not in interactive terminal. "
                f"Destructive operations require manual confirmation."
            )

        confirmation_phrase = f"DELETE ALL {data_description.upper()} FROM PRODUCTION"

        print(f"\n{'!' * 80}")
        print(f"  ⚠️  DESTRUCTIVE OPERATION: {operation}")
        print(f"  📊 This will delete: {data_description}")
        print(f"  🗄️  Database: {settings.postgres_db}@localhost:{self._postgres_port}")
        print(f"  🔍 Qdrant: localhost:{self._qdrant_port}")
        print(f"{'!' * 80}")
        print(f"\nTo proceed, type EXACTLY: {confirmation_phrase}")

        user_input = input("\n> ").strip()

        if user_input != confirmation_phrase:
            raise ProductionProtectionError(
                f"Confirmation phrase did not match - operation '{operation}' aborted"
            )

        logger.warning(
            f"User confirmed destructive operation: {operation}",
            extra={
                "operation": operation,
                "data_description": data_description,
                "environment": "PRODUCTION",
            },
        )

        return True

    def check_emergency_lock(self) -> None:
        """Check for emergency lockfile and block all production operations if present.

        The lockfile serves as an emergency kill switch to prevent ANY operations
        on production databases. Useful during incidents or maintenance windows.

        Usage:
            To activate: touch /tmp/raglite_production_locked
            To deactivate: rm /tmp/raglite_production_locked

        Raises:
            ProductionProtectionError: If lockfile exists and environment is production
        """
        if os.path.exists(self.EMERGENCY_LOCKFILE):
            if self.is_production:
                raise ProductionProtectionError(
                    f"EMERGENCY LOCK ACTIVE\n"
                    f"Production operations blocked by lockfile: {self.EMERGENCY_LOCKFILE}\n"
                    f"Remove lockfile to proceed: rm {self.EMERGENCY_LOCKFILE}"
                )
            else:
                logger.warning(
                    "Emergency lockfile present but environment is test - proceeding",
                    extra={"lockfile": self.EMERGENCY_LOCKFILE, "env": self._app_env},
                )

    def log_operation(self, operation: str) -> None:
        """Log operation with environment context.

        Args:
            operation: Description of operation being performed
        """
        env_label = "PRODUCTION" if self.is_production else "TEST"

        logger.info(
            f"Database operation: {operation}",
            extra={
                "operation": operation,
                "environment": env_label,
                "app_env": self._app_env,
                "qdrant_port": self._qdrant_port,
                "postgres_port": self._postgres_port,
            },
        )

    def display_environment_banner(self) -> None:
        """Display prominent environment indicator."""
        env_label = "PRODUCTION" if self.is_production else "TEST"
        env_emoji = "\U0001f534" if self.is_production else "\U0001f7e2"  # Red/Green circle

        print(f"\n{'=' * 60}")
        print(f"  {env_emoji} Environment: {env_label}")
        print(f"  Qdrant: localhost:{self._qdrant_port}")
        print(f"  PostgreSQL: {settings.postgres_db}@localhost:{self._postgres_port}")
        print(f"{'=' * 60}\n")

    def validate_test_environment(self, operation: str = "test_operation") -> None:
        """Validate that current environment is safe for test operations.

        This is a HARD BLOCK - if any check fails, an exception is raised.
        Use this at the start of any test fixture that performs destructive operations.

        Checks:
        1. Qdrant port must be TEST_QDRANT_PORT (6335), not production (6333)
        2. PostgreSQL port must be TEST_POSTGRES_PORT (5433), not production (5432)
        3. Collection name must end with '_test' or '_ci'

        Args:
            operation: Name of the operation for error messages

        Raises:
            ProductionProtectionError: If any check fails (on production infrastructure)

        Example:
            >>> guard = SafetyGuard()
            >>> guard.validate_test_environment("session_fixture")  # Raises if on prod
        """
        issues = []

        # Check Qdrant port
        if self._qdrant_port == self.PRODUCTION_QDRANT_PORT:
            issues.append(
                f"Qdrant port {self._qdrant_port} is PRODUCTION (expected {self.TEST_QDRANT_PORT})"
            )

        # Check PostgreSQL port
        if self._postgres_port == self.PRODUCTION_POSTGRES_PORT:
            issues.append(
                f"PostgreSQL port {self._postgres_port} is PRODUCTION "
                f"(expected {self.TEST_POSTGRES_PORT})"
            )

        # Check collection name has test suffix
        collection_name = settings.qdrant_collection_name
        if not collection_name.endswith(("_test", "_ci")):
            issues.append(
                f"Collection '{collection_name}' missing test suffix (expected '_test' or '_ci')"
            )

        if issues:
            error_msg = (
                f"TEST ISOLATION VIOLATION for '{operation}':\n"
                + "\n".join(f"  - {issue}" for issue in issues)
                + "\n\nTests must run on test infrastructure. "
                "Set APP_ENV=test before running tests."
            )
            logger.error(
                "Test isolation violation detected",
                extra={
                    "operation": operation,
                    "issues": issues,
                    "qdrant_port": self._qdrant_port,
                    "postgres_port": self._postgres_port,
                    "collection": collection_name,
                },
            )
            raise ProductionProtectionError(error_msg)

        logger.info(
            f"Test environment validated for '{operation}'",
            extra={
                "operation": operation,
                "qdrant_port": self._qdrant_port,
                "postgres_port": self._postgres_port,
                "collection": collection_name,
            },
        )

    def block_destructive_on_production(self, operation: str) -> None:
        """Block destructive operations on production without explicit deploy mode.

        This is used for operations that should NEVER run on production
        except through the explicit deploy-to-production.py script.

        Args:
            operation: Name of the operation being blocked

        Raises:
            ProductionProtectionError: If on production environment
        """
        if self.is_production:
            raise ProductionProtectionError(
                f"BLOCKED: '{operation}' is destructive and cannot run on production.\n"
                f"Use scripts/deploy-to-production.py with explicit confirmation for "
                f"schema changes."
            )

    def check_operation(
        self,
        operation: str,
        op_type: OperationType,
        force_data_loss: bool = False,
    ) -> bool:
        """Check if operation is allowed based on environment and type.

        Args:
            operation: Description of the operation
            op_type: Classification of operation (SAFE, ADDITIVE, DESTRUCTIVE)
            force_data_loss: If True, allow destructive operations on production

        Returns:
            True if operation should proceed

        Raises:
            ProductionProtectionError: If destructive on production without force flag
                                      or if emergency lockfile is present
        """
        # Check emergency lockfile first (kill switch for all production operations)
        self.check_emergency_lock()

        self.log_operation(f"{operation} (type={op_type.value})")

        if op_type == OperationType.SAFE:
            return True  # Always allowed

        if op_type == OperationType.ADDITIVE:
            if self.is_production:
                logger.info(
                    f"Additive operation '{operation}' on production",
                    extra={"operation": operation, "type": op_type.value},
                )
            return True  # Allowed on both environments

        if op_type == OperationType.DESTRUCTIVE:
            if self.is_production and not force_data_loss:
                raise ProductionProtectionError(
                    f"BLOCKED: '{operation}' is destructive.\n"
                    f"Use --force-data-loss flag to proceed on production."
                )
            return True

        return False
