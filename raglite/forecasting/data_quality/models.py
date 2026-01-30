"""Data models for variable quality configuration.

Story: Data Quality Testing Framework
Defines enums and dataclasses for quality requirements.
"""

from dataclasses import dataclass, field
from enum import Enum


class EntityMatchMode(Enum):
    """How to match entity names in SQL queries."""

    EXACT = "exact"  # entity = 'GROUP'
    ILIKE = "ilike"  # entity ILIKE '%portugal%'
    ANY = "any"  # No entity filter


class ExpectedSign(Enum):
    """Expected sign/direction of values."""

    POSITIVE = "positive"  # > 0
    NEGATIVE = "negative"  # < 0
    ANY = "any"  # No sign constraint


class Frequency(Enum):
    """Expected time series frequency."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    DAILY = "daily"


@dataclass
class ValueRangeConfig:
    """Value range constraints for a variable.

    Attributes:
        min_value: Minimum expected value (None = no lower bound)
        max_value: Maximum expected value (None = no upper bound)
        expected_sign: Expected sign constraint
        unit: Expected unit for display
        detect_scale_mismatch: Check for 1000x scale issues
        scale_reference_median: Expected median for scale check
        outlier_mad_threshold: MAD threshold for outlier detection (default 3.5)
    """

    min_value: float | None = None
    max_value: float | None = None
    expected_sign: ExpectedSign = ExpectedSign.ANY
    unit: str = ""
    detect_scale_mismatch: bool = False
    scale_reference_median: float | None = None  # Expected median for scale check
    outlier_mad_threshold: float = 3.5  # MAD threshold for outlier detection


@dataclass
class EntityConfig:
    """Entity filtering configuration.

    Attributes:
        required_entity: Entity name to filter by (e.g., 'GROUP', 'portugal')
        match_mode: How to match (exact, ilike, any)
        contamination_check: Enable entity contamination check (fuzzy vs exact)
    """

    required_entity: str | None = None
    match_mode: EntityMatchMode = EntityMatchMode.ANY
    contamination_check: bool = False


@dataclass
class FrequencyConfig:
    """Time series frequency constraints.

    Attributes:
        expected: Expected frequency (monthly, quarterly, etc.)
        allow_year_end_only: Allow year-end only data (Dec-only patterns)
        max_gap_months: Maximum allowed gap between data points
    """

    expected: Frequency = Frequency.MONTHLY
    allow_year_end_only: bool = False
    max_gap_months: int = 3


@dataclass
class VariableQualityConfig:
    """Complete quality configuration for a forecast variable.

    Attributes:
        name: Variable identifier (e.g., 'ebitda', 'revenue')
        display_name: Human-readable name
        value_range: Value constraints and unit
        entity: Entity filtering configuration
        frequency: Time series frequency constraints
        min_data_points: Minimum required data points
        max_missing_rate: Maximum allowed missing data rate (0.0-1.0)
        db_metric_aliases: SQL metric names to search for
        is_external_only: True if data comes from external APIs only
        checks_to_skip: List of check names to skip for this variable
    """

    name: str
    display_name: str
    value_range: ValueRangeConfig = field(default_factory=ValueRangeConfig)
    entity: EntityConfig = field(default_factory=EntityConfig)
    frequency: FrequencyConfig = field(default_factory=FrequencyConfig)
    min_data_points: int = 6
    max_missing_rate: float = 0.2
    db_metric_aliases: list[str] = field(default_factory=list)
    is_external_only: bool = False
    checks_to_skip: list[str] = field(default_factory=list)
