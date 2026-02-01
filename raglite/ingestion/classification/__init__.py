"""Period and value type classification modules for ingestion pipeline.

Provides classification of financial period strings into types:
- MONTHLY_ACTUAL: "Dec-21", "Jan-25"
- YTD_ACTUAL: "YTD Dec-21", "YTD Jun-24"
- BUDGET: "B Dec-21", "Dec-21 B"
- YTD_BUDGET: "YTD B Dec-21"
- UNKNOWN: Empty, N/A, malformed

And value types:
- ACTUAL: Realized/historical values
- BUDGET: Planned/budgeted values
- FORECAST: Predicted/projected values
- VARIANCE: Difference calculations
- UNKNOWN: Cannot determine type

And entity levels:
- CONSOLIDATED: Group-level aggregated data
- COMPANY_ONLY: Individual company data
- SEGMENT: Business segment data
- GEOGRAPHIC: Geographic region data
- UNKNOWN: Cannot determine level

Supports Portuguese month abbreviations and batch classification with caching.
"""

from raglite.ingestion.classification import value_type_classifier
from raglite.ingestion.classification.entity_level_classifier import (
    classify_entity_level,
    classify_entity_levels_batch,
)
from raglite.ingestion.classification.models import (
    ClassificationReport,
    ClassifiedEntityLevel,
    ClassifiedPeriod,
    ClassifiedValueType,
    EntityLevel,
    EntityLevelReport,
    PeriodType,
    ValueType,
    ValueTypeReport,
)
from raglite.ingestion.classification.period_classifier import (
    classify_period,
    classify_periods_batch,
)
from raglite.ingestion.classification.value_type_classifier import (
    classify_value_type,
    classify_value_types_batch,
)

__all__ = [
    # Period classification
    "PeriodType",
    "ClassifiedPeriod",
    "ClassificationReport",
    "classify_period",
    "classify_periods_batch",
    # Value type classification
    "ValueType",
    "ClassifiedValueType",
    "ValueTypeReport",
    "classify_value_type",
    "classify_value_types_batch",
    # Entity level classification
    "EntityLevel",
    "ClassifiedEntityLevel",
    "EntityLevelReport",
    "classify_entity_level",
    "classify_entity_levels_batch",
    # Modules (for test inspection)
    "value_type_classifier",
]
