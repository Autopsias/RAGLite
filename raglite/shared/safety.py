"""Database operation safety controls for production protection.

This module provides centralized safeguards to prevent accidental modification
or deletion of production database data. Created after 2025-11-25 incident
where production databases were found empty.

Story 4.0.6: Production Database Protection Safeguards
"""

from __future__ import annotations

import logging
import sys

from raglite.shared.config import settings

logger = logging.getLogger(__name__)


class ProductionProtectionError(Exception):
    """Raised when a destructive operation is attempted on production without override."""

    pass


class SafetyGuard:
    """Centralized database operation safety controls.

    Prevents accidental modification of production databases by:
    1. Checking APP_ENV before destructive operations
    2. Requiring explicit confirmation for production changes
    3. Logging all operations with environment context

    Example:
        >>> guard = SafetyGuard()
        >>> guard.check_environment("delete_collection")  # Raises on production
        >>> guard.check_environment("delete_collection", force_production=True)  # OK
    """

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
