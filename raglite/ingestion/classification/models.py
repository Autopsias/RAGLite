"""Data models for period and value type classification.

Adapted from raglite/forecasting/timeseries/period_classification.py
for use in ingestion pipeline.
"""

from dataclasses import dataclass
from enum import Enum


class PeriodType(Enum):
    """Classification of period formats in financial data.

    Used to filter and normalize periods before forecasting.
    Only MONTHLY_ACTUAL and YTD_ACTUAL are usable for forecasting.
    """

    MONTHLY_ACTUAL = "monthly_actual"  # "Dec-21", "Jan-25"
    YTD_ACTUAL = "ytd_actual"  # "YTD Dec-21", "YTD Jun-24"
    BUDGET = "budget"  # "B Dec-21", "Dec-21 B"
    YTD_BUDGET = "ytd_budget"  # "YTD B Dec-21"
    UNKNOWN = "unknown"  # Empty, N/A, malformed


class ValueType(Enum):
    """Classification of value types in financial data.

    Used to filter actual vs budget vs forecast data for analysis.
    """

    ACTUAL = "actual"  # Realized/historical values
    BUDGET = "budget"  # Planned/budgeted values
    FORECAST = "forecast"  # Predicted/projected values
    VARIANCE = "variance"  # Difference calculations
    UNKNOWN = "unknown"  # Cannot determine type


@dataclass
class ClassifiedPeriod:
    """Result of period classification with normalized form."""

    original: str
    period_type: PeriodType
    normalized: str | None  # None for excluded types (BUDGET, YTD_BUDGET, UNKNOWN)
    is_usable: bool  # True for MONTHLY_ACTUAL and YTD_ACTUAL


@dataclass
class ClassifiedValueType:
    """Result of value type classification with source attribution."""

    original: str  # Original period string
    value_type: ValueType  # Classification result
    source: (
        str  # Where classification came from: "period_type", "period_prefix", "header", "default"
    )


@dataclass
class ClassificationReport:
    """Summary of period classification results."""

    total_records: int
    usable_records: int
    monthly_actual_count: int
    ytd_actual_count: int
    budget_count: int
    ytd_budget_count: int
    unknown_count: int

    @property
    def usability_rate(self) -> float:
        """Percentage of records that are usable."""
        if self.total_records == 0:
            return 0.0
        return self.usable_records / self.total_records * 100

    @property
    def exclusion_breakdown(self) -> dict[str, int]:
        """Breakdown of excluded records by type."""
        return {
            "budget": self.budget_count,
            "ytd_budget": self.ytd_budget_count,
            "unknown": self.unknown_count,
        }


@dataclass
class ValueTypeReport:
    """Summary of value type classification results."""

    total_records: int
    actual_count: int
    budget_count: int
    forecast_count: int
    variance_count: int
    unknown_count: int

    @property
    def value_type_breakdown(self) -> dict[str, int]:
        """Breakdown of records by value type."""
        return {
            "actual": self.actual_count,
            "budget": self.budget_count,
            "forecast": self.forecast_count,
            "variance": self.variance_count,
            "unknown": self.unknown_count,
        }


class EntityLevel(Enum):
    """Classification of entity levels in financial data.

    Used to filter consolidated vs company vs segment data for analysis.
    """

    CONSOLIDATED = "consolidated"  # Group-level aggregated data
    COMPANY_ONLY = "company_only"  # Individual company data
    SEGMENT = "segment"  # Business segment data
    GEOGRAPHIC = "geographic"  # Geographic region data
    UNKNOWN = "unknown"  # Cannot determine level


@dataclass
class ClassifiedEntityLevel:
    """Result of entity level classification with source attribution."""

    original: str  # Original entity string
    entity_level: EntityLevel  # Classification result
    source: str  # Where classification came from: "table_title", "entity_pattern", "default", "empty", "unknown_marker", "ambiguous"


@dataclass
class EntityLevelReport:
    """Summary of entity level classification results."""

    total_records: int
    consolidated_count: int
    company_only_count: int
    segment_count: int
    geographic_count: int
    unknown_count: int

    @property
    def entity_level_breakdown(self) -> dict[str, int]:
        """Breakdown of records by entity level."""
        return {
            "consolidated": self.consolidated_count,
            "company_only": self.company_only_count,
            "segment": self.segment_count,
            "geographic": self.geographic_count,
            "unknown": self.unknown_count,
        }
