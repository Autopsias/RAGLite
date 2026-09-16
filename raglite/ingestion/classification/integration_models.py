"""Data models for classification integration module."""

from dataclasses import dataclass


@dataclass
class ClassificationSummary:
    """Summary of classification results for a document."""

    total_rows: int
    classification_duration_ms: int

    # Period type breakdown
    period_monthly_actual: int
    period_ytd_actual: int
    period_budget: int
    period_ytd_budget: int
    period_unknown: int

    # Value type breakdown
    value_actual: int
    value_budget: int
    value_forecast: int
    value_variance: int
    value_unknown: int

    # Entity level breakdown
    entity_consolidated: int
    entity_company_only: int
    entity_segment: int
    entity_geographic: int
    entity_unknown: int
