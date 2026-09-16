"""Classification integration module for table extraction pipeline.

Coordinates period_type, value_type, and entity_level classifiers to enrich
table rows with classification fields during extraction.

Functions:
- classify_row: Enrich a single row with classification fields
- classify_rows_batch: Batch-process multiple rows for efficiency
- generate_classification_summary: Create classification summary report

Usage:
    from raglite.ingestion.classification.integration import classify_rows_batch

    rows = extract_table_data(...)  # Raw extraction
    rows = classify_rows_batch(rows)  # Add classification fields

Row Schema Extension:
    Input:  {entity, metric, period, ...}
    Output: {entity, metric, period, ..., period_type, value_type, entity_level}

Performance:
- ~10ms per 100 rows (regex + lookups)
- <20% overhead vs extraction-only baseline (per Epic 9 AC4)
"""

import logging
import time
from typing import Any, cast

from raglite.ingestion.classification.entity_level_classifier import (
    classify_entity_level,
    classify_entity_levels_batch,
)
from raglite.ingestion.classification.integration_models import ClassificationSummary
from raglite.ingestion.classification.models import (
    ClassifiedEntityLevel,
    ClassifiedPeriod,
    ClassifiedValueType,
    EntityLevel,
    PeriodType,
    ValueType,
)
from raglite.ingestion.classification.period_classifier import classify_period
from raglite.ingestion.classification.value_type_classifier import (
    classify_value_type,
    classify_value_types_batch,
)

logger = logging.getLogger(__name__)


def classify_row(row: dict[str, Any]) -> dict[str, Any]:
    """Enrich a table row with classification fields.

    Args:
        row: Table row dict with entity, metric, period, unit fields

    Returns:
        Row dict with added period_type, value_type, entity_level fields (string values).
        If currency detection corrects the entity (e.g., BRL currency -> Brazil),
        the entity field is updated to the corrected value.

    Example:
        >>> row = {"entity": "Portugal Cement", "period": "Dec-24", "metric": "Revenue"}
        >>> enriched = classify_row(row)
        >>> enriched["period_type"]
        'monthly_actual'
        >>> enriched["value_type"]
        'actual'
        >>> enriched["entity_level"]
        'company_only'
        >>> # Currency detection example
        >>> row = {"entity": "SECIL Group", "period": "Dec-24", "unit": "1000 BRL"}
        >>> enriched = classify_row(row)
        >>> enriched["entity_level"]
        'geographic'
        >>> enriched["entity"]
        'Brazil'
    """
    # Get input values (handle None gracefully)
    period = row.get("period", "") or ""
    entity = row.get("entity", "") or ""
    unit = row.get("unit", "") or ""

    # Classify period type
    period_result: ClassifiedPeriod = classify_period(period)
    period_type = period_result.period_type

    # Classify value type (uses period_type for coordination)
    value_result: ClassifiedValueType = classify_value_type(period=period, period_type=period_type)

    # Classify entity level (with currency detection and metric context)
    metric = row.get("metric", "") or ""
    entity_result: ClassifiedEntityLevel = classify_entity_level(entity, unit=unit, metric=metric)

    # Build enriched row (use enum .value for JSON serialization)
    enriched_row = {
        **row,
        "period_type": period_type.value,
        "value_type": value_result.value_type.value,
        "entity_level": entity_result.entity_level.value,
    }

    # If currency detection corrected the entity, update entity field
    if entity_result.corrected_entity:
        enriched_row["entity"] = entity_result.corrected_entity

    return enriched_row


def classify_rows_batch(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Batch-process multiple rows with classification fields.

    Uses batch classification functions for efficiency. Recommended for >10 rows.
    Supports currency detection: non-EUR currencies (BRL, AOA, LBP, TND) will
    override entity classification to geographic and correct the entity name.

    Args:
        rows: List of table row dicts (with entity, period, unit fields)

    Returns:
        List of enriched row dicts with classification fields.
        Entity field may be corrected if currency detection applies.

    Performance:
        - ~10ms for 100 rows
        - ~100ms for 1000 rows (per Story 9.5 AC4 requirement)
    """
    if not rows:
        return []

    # Measure classification timing (M4)
    start_time = time.perf_counter()

    # Extract periods, entities, units, and metrics for classification
    periods = [row.get("period", "") or "" for row in rows]
    entities = [row.get("entity", "") or "" for row in rows]
    units = [row.get("unit", "") or "" for row in rows]
    metrics = [row.get("metric", "") or "" for row in rows]

    # Batch classify periods (M2: use batch function)
    # Note: classify_periods_batch returns only ClassificationReport, not individual results
    # So we still need individual calls to get period_type per row
    period_results_list = [classify_period(period) for period in periods]
    period_types = [result.period_type for result in period_results_list]

    # Batch classify value types (with period_type coordination)
    # Cast to list[PeriodType | None] for type compatibility (period_type is never None)
    value_results_list, _value_report = classify_value_types_batch(
        periods=periods, period_types=cast(list[PeriodType | None], period_types)
    )

    # Batch classify entity levels (with currency detection via units, metric context)
    entity_results_list, _entity_report = classify_entity_levels_batch(
        entities, units=units, metrics=metrics
    )

    # Enrich all rows
    enriched_rows = []
    for row, period_type, value_result, entity_result in zip(
        rows, period_types, value_results_list, entity_results_list, strict=True
    ):
        enriched_row = {
            **row,
            "period_type": period_type.value,
            "value_type": value_result.value_type.value,
            "entity_level": entity_result.entity_level.value,
        }
        # If currency detection corrected the entity, update entity field
        if entity_result.corrected_entity:
            enriched_row["entity"] = entity_result.corrected_entity
        enriched_rows.append(enriched_row)

    # Calculate timing
    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # Generate and log classification summary (M3: INFO-level logging)
    summary = generate_classification_summary(enriched_rows, duration_ms)
    logger.info(
        "Classification complete",
        extra={
            "total_rows": summary.total_rows,
            "duration_ms": summary.classification_duration_ms,
            "period_monthly_actual": summary.period_monthly_actual,
            "period_ytd_actual": summary.period_ytd_actual,
            "period_budget": summary.period_budget,
            "value_actual": summary.value_actual,
            "value_budget": summary.value_budget,
            "value_forecast": summary.value_forecast,
            "entity_consolidated": summary.entity_consolidated,
            "entity_company_only": summary.entity_company_only,
            "entity_segment": summary.entity_segment,
        },
    )

    return enriched_rows


def generate_classification_summary(
    rows: list[dict[str, Any]], duration_ms: int = 0
) -> ClassificationSummary:
    """Generate classification summary report from enriched rows.

    Args:
        rows: List of enriched rows with classification fields
        duration_ms: Classification duration in milliseconds (default: 0)

    Returns:
        ClassificationSummary with counts by type

    Example:
        >>> summary = generate_classification_summary(enriched_rows, duration_ms=15)
        >>> summary.total_rows
        100
        >>> summary.period_monthly_actual
        85
        >>> summary.value_actual
        90
    """
    if not rows:
        return ClassificationSummary(
            total_rows=0,
            classification_duration_ms=duration_ms,
            period_monthly_actual=0,
            period_ytd_actual=0,
            period_budget=0,
            period_ytd_budget=0,
            period_unknown=0,
            value_actual=0,
            value_budget=0,
            value_forecast=0,
            value_variance=0,
            value_unknown=0,
            entity_consolidated=0,
            entity_company_only=0,
            entity_segment=0,
            entity_geographic=0,
            entity_unknown=0,
        )

    # Count period types
    period_counts = {
        PeriodType.MONTHLY_ACTUAL.value: 0,
        PeriodType.YTD_ACTUAL.value: 0,
        PeriodType.BUDGET.value: 0,
        PeriodType.YTD_BUDGET.value: 0,
        PeriodType.UNKNOWN.value: 0,
    }

    # Count value types
    value_counts = {
        ValueType.ACTUAL.value: 0,
        ValueType.BUDGET.value: 0,
        ValueType.FORECAST.value: 0,
        ValueType.VARIANCE.value: 0,
        ValueType.UNKNOWN.value: 0,
    }

    # Count entity levels
    entity_counts = {
        EntityLevel.CONSOLIDATED.value: 0,
        EntityLevel.COMPANY_ONLY.value: 0,
        EntityLevel.SEGMENT.value: 0,
        EntityLevel.GEOGRAPHIC.value: 0,
        EntityLevel.UNKNOWN.value: 0,
    }

    # Count all classifications
    for row in rows:
        period_type = row.get("period_type", PeriodType.UNKNOWN.value)
        value_type = row.get("value_type", ValueType.UNKNOWN.value)
        entity_level = row.get("entity_level", EntityLevel.UNKNOWN.value)

        period_counts[period_type] = period_counts.get(period_type, 0) + 1
        value_counts[value_type] = value_counts.get(value_type, 0) + 1
        entity_counts[entity_level] = entity_counts.get(entity_level, 0) + 1

    return ClassificationSummary(
        total_rows=len(rows),
        classification_duration_ms=duration_ms,
        # Period types
        period_monthly_actual=period_counts.get(PeriodType.MONTHLY_ACTUAL.value, 0),
        period_ytd_actual=period_counts.get(PeriodType.YTD_ACTUAL.value, 0),
        period_budget=period_counts.get(PeriodType.BUDGET.value, 0),
        period_ytd_budget=period_counts.get(PeriodType.YTD_BUDGET.value, 0),
        period_unknown=period_counts.get(PeriodType.UNKNOWN.value, 0),
        # Value types
        value_actual=value_counts.get(ValueType.ACTUAL.value, 0),
        value_budget=value_counts.get(ValueType.BUDGET.value, 0),
        value_forecast=value_counts.get(ValueType.FORECAST.value, 0),
        value_variance=value_counts.get(ValueType.VARIANCE.value, 0),
        value_unknown=value_counts.get(ValueType.UNKNOWN.value, 0),
        # Entity levels
        entity_consolidated=entity_counts.get(EntityLevel.CONSOLIDATED.value, 0),
        entity_company_only=entity_counts.get(EntityLevel.COMPANY_ONLY.value, 0),
        entity_segment=entity_counts.get(EntityLevel.SEGMENT.value, 0),
        entity_geographic=entity_counts.get(EntityLevel.GEOGRAPHIC.value, 0),
        entity_unknown=entity_counts.get(EntityLevel.UNKNOWN.value, 0),
    )
