"""Exception classes for external data integration.

Story 6.1: Tier 1 External Data Source Integration
"""

from __future__ import annotations


class ExternalDataError(Exception):
    """Base exception for external data operations."""

    pass


class ExternalDataFetchError(ExternalDataError):
    """Raised when fetching data from external API fails after all retries.

    Attributes:
        source: Name of the data source (e.g., "INE", "OMIE")
        message: Error description
        original_error: The underlying exception that caused the failure
    """

    def __init__(
        self,
        source: str,
        message: str,
        original_error: Exception | None = None,
    ) -> None:
        self.source = source
        self.message = message
        self.original_error = original_error
        super().__init__(f"[{source}] {message}")


class ExternalDataValidationError(ExternalDataError):
    """Raised when external data fails validation.

    Attributes:
        source: Name of the data source
        message: Validation error description
    """

    def __init__(self, source: str, message: str) -> None:
        self.source = source
        self.message = message
        super().__init__(f"[{source}] Validation failed: {message}")


class ExternalDataStaleError(ExternalDataError):
    """Raised when cached data is too stale to use.

    Attributes:
        source: Name of the data source
        days_stale: Number of days since last update
        max_days: Maximum allowed staleness
    """

    def __init__(self, source: str, days_stale: int, max_days: int) -> None:
        self.source = source
        self.days_stale = days_stale
        self.max_days = max_days
        super().__init__(f"[{source}] Data is {days_stale} days old (max allowed: {max_days})")
