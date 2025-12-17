"""Data quality check result structures.

Provides standardized result types for all data quality checks.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CheckStatus(Enum):
    """Status codes for data quality checks."""

    PASS = "PASS"  # nosec B105 - This is a status code, not a password
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class CheckResult:
    """Result of a single data quality check.

    Attributes:
        check_name: Identifier for the check (e.g., 'entity_contamination')
        status: Pass/Warn/Fail/Skip status
        message: Human-readable description of the result
        variable: Variable name this check applies to
        severity: 1-5 scale (5 = critical)
        actual_value: The observed value that was checked
        threshold: The threshold/limit that was compared against
        sample_rows: Example rows demonstrating the issue
    """

    check_name: str
    status: CheckStatus
    message: str
    variable: str
    severity: int = 1
    actual_value: Any = None
    threshold: float | None = None
    sample_rows: list[dict] = field(default_factory=list)

    def is_passing(self) -> bool:
        """Check if result is passing (PASS or SKIP)."""
        return self.status in (CheckStatus.PASS, CheckStatus.SKIP)

    def is_actionable(self) -> bool:
        """Check if result requires attention (WARN or FAIL)."""
        return self.status in (CheckStatus.WARN, CheckStatus.FAIL)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "check_name": self.check_name,
            "status": self.status.value,
            "message": self.message,
            "variable": self.variable,
            "severity": self.severity,
            "actual_value": self.actual_value,
            "threshold": self.threshold,
            "sample_rows": self.sample_rows,
        }
