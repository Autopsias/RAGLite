"""Centralized validation module for adaptive table extraction.

This module provides centralized validation and safe accessor functions to prevent
validation bypasses during entity and metric inference.

Phase 2 Architecture:
- All validation logic centralized in one place
- Safe wrapper functions that ALWAYS validate before returning values
- Type-safe interfaces that make bypasses impossible
- Comprehensive logging of all validation decisions

Created: 2025-12-02 (Phase 2 of validation bypass fixes)
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

# Phase 2.2: Import entity normalization for canonical mappings
from raglite.ingestion.entity_normalizer import normalize_entity

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ============================================================================
# CORE VALIDATION FUNCTIONS
# ============================================================================


def validate_entity(entity: str | None) -> bool:
    """Validate entity name against known invalid patterns.

    Args:
        entity: Entity name to validate

    Returns:
        True if entity is valid, False if invalid

    Invalid patterns (rejected):
    - Temporal descriptors: YTD, MTD, QTD, YoY, MoM, etc.
    - Variance descriptors: Var., %, Δ, etc.
    - Currency codes: EUR, USD, BRL, AOA, TND, etc.
    - Unit descriptors: 1000 EUR, Million, K, etc.
    - Placeholders: N/A, null, none, unknown, TBD, etc.
    - Single characters or numbers
    - Empty/whitespace-only strings
    """
    if not entity or not entity.strip():
        return False

    entity_clean = entity.strip()

    # Reject single characters or pure numbers
    if len(entity_clean) == 1 or entity_clean.isdigit():
        return False

    # Invalid patterns (case-insensitive)
    invalid_patterns = [
        # Temporal descriptors
        r"^(ytd|mtd|qtd|yoy|mom|qoq|ly|py|cy)$",
        r"\b(year.to.date|month.to.date|quarter.to.date)\b",
        # Variance indicators
        r"^(var\.?|variance|delta|change|diff)$",
        r"^%\s*(ly|py|b|budget|forecast)$",
        r"^\d+%$",  # Pure percentage like "100%"
        # Currency codes (ISO 4217)
        r"^(eur|usd|gbp|jpy|cny|brl|aoa|tnd|mzn|cve)$",
        r"\b(meur|musd|keur|kusd|€|\$|£|¥)\b",
        # Unit descriptors
        r"\b(thousand|million|billion|k|m|b)\s*(eur|usd|gbp)?\b",
        r"^\d+\s*(eur|usd|gbp|k|m)$",  # "1000 EUR", "100K", etc.
        r"^currency\b",  # "Currency (1000 EUR)"
        # Placeholders and generic terms
        r"^(n/?a|null|none|unknown|tbd|pending|blank)$",
        r"^(total|sum|average|avg|mean|median)$",
        # Special characters only
        r"^[^a-z0-9]+$",
    ]

    for pattern in invalid_patterns:
        if re.search(pattern, entity_clean, re.IGNORECASE):
            return False

    return True


def validate_metric(metric: str | None) -> bool:
    """Validate metric name against known invalid patterns.

    Args:
        metric: Metric name to validate

    Returns:
        True if metric is valid, False if invalid

    Invalid patterns (rejected):
    - Temporal descriptors: YTD, MTD, QTD, YoY, MoM, etc.
    - Variance descriptors: Var., %, Δ, etc.
    - Currency codes: EUR, USD, BRL, AOA, TND, etc.
    - Unit descriptors: 1000 EUR, Million, K, etc.
    - Placeholders: N/A, null, none, unknown, TBD, etc.
    - Single characters or numbers
    - Empty/whitespace-only strings
    - Strings ending with temporal or unit patterns
    """
    if not metric or not metric.strip():
        return False

    metric_clean = metric.strip()

    # Reject single characters or pure numbers
    if len(metric_clean) == 1 or metric_clean.isdigit():
        return False

    # Invalid patterns (case-insensitive)
    invalid_patterns = [
        # Temporal descriptors
        r"^(ytd|mtd|qtd|yoy|mom|qoq|ly|py|cy)$",
        r"^(ytd|mtd|qtd|yoy|mom|qoq|ly|py|cy)\s+",  # Metrics starting with temporal
        r"\b(year.to.date|month.to.date|quarter.to.date)\b",
        r"\(ytd\)$",  # Metrics ending with "(YTD)"
        # Variance indicators
        r"^(var\.?|variance|delta|change|diff)$",
        r"^%\s*(ly|py|b|budget|forecast)$",
        r"^\d+%$",  # Pure percentage like "100%"
        # Currency codes (ISO 4217)
        r"^(eur|usd|gbp|jpy|cny|brl|aoa|tnd|mzn|cve)$",
        r"^(eur|usd|gbp|jpy|cny|brl|aoa|tnd|mzn|cve)\s+",  # Metrics starting with currency
        r"\s+(eur|usd|gbp|jpy|cny|brl|aoa|tnd|mzn|cve)$",  # Metrics ending with currency
        r"\b(meur|musd|keur|kusd|€|\$|£|¥)\b",
        # Unit descriptors
        r"\b(thousand|million|billion|k|m|b)\s*(eur|usd|gbp)?\b",
        r"^\d+\s*(eur|usd|gbp|k|m)$",  # "1000 EUR", "100K", etc.
        r"^currency\b",  # "Currency (1000 EUR)"
        # Placeholders and generic terms
        r"^(n/?a|null|none|unknown|tbd|pending|blank)$",
        r"^(total|sum|average|avg|mean|median)$",
        # Special characters only
        r"^[^a-z0-9]+$",
        # Suspicious endings (likely incomplete extractions)
        r"\s+(ytd|mtd|qtd|ly|py|cy|var|%)$",
    ]

    for pattern in invalid_patterns:
        if re.search(pattern, metric_clean, re.IGNORECASE):
            return False

    return True


# ============================================================================
# SAFE WRAPPER FUNCTIONS (Prevent Validation Bypasses)
# ============================================================================


def safe_assign_entity(
    entity: str | None,
    *,
    source: str = "unknown",
    page_number: int | None = None,
    table_index: int | None = None,
    row_idx: int | None = None,
    col_idx: int | None = None,
) -> str | None:
    """Safely assign entity with MANDATORY normalization and validation.

    Phase 2.2 Update: Now normalizes entity to canonical form BEFORE validation.
    This improves entity coverage from 22-88% to expected 70-95%.

    This wrapper function ALWAYS:
    1. Normalizes the entity to canonical form (e.g., "PT" → "Portugal")
    2. Validates the normalized entity
    It is IMPOSSIBLE to bypass validation when using this function.

    Args:
        entity: Entity value to normalize, validate and assign
        source: Source of the entity (e.g., "header", "context_inference", "cell")
        page_number: Page number for logging (optional)
        table_index: Table index for logging (optional)
        row_idx: Row index for logging (optional)
        col_idx: Column index for logging (optional)

    Returns:
        Normalized and validated entity if valid, None if invalid

    Logging:
        - Logs warning if entity is invalid with full context
        - Logs debug if entity is valid (for audit trail)
        - Logs info when normalization changes the entity name
    """
    if not entity:
        return None

    entity_clean = entity.strip()

    # Phase 2.2: Normalize entity to canonical form BEFORE validation
    entity_normalized = normalize_entity(entity_clean)

    # Log normalization if entity was changed
    if entity_normalized and entity_normalized != entity_clean:
        logger.info(
            f"Entity normalized: '{entity_clean}' → '{entity_normalized}'",
            extra={
                "source": source,
                "raw_entity": entity_clean,
                "canonical_entity": entity_normalized,
                "page_number": page_number,
                "table_index": table_index,
            },
        )

    # Use normalized entity for validation
    entity_to_validate = entity_normalized if entity_normalized else entity_clean

    if validate_entity(entity_to_validate):
        logger.debug(
            f"Valid entity assigned from {source}: '{entity_to_validate}'",
            extra={
                "source": source,
                "entity": entity_to_validate,
                "raw_entity": entity_clean if entity_normalized != entity_clean else None,
                "page_number": page_number,
                "table_index": table_index,
                "row_idx": row_idx,
                "col_idx": col_idx,
            },
        )
        return entity_to_validate

    # Invalid entity - log warning and return None
    logger.warning(
        f"Invalid entity from {source} - rejected: '{entity_clean}'",
        extra={
            "source": source,
            "invalid_entity": entity_clean,
            "normalized_form": entity_normalized,
            "page_number": page_number,
            "table_index": table_index,
            "row_idx": row_idx,
            "col_idx": col_idx,
        },
    )
    return None


def safe_assign_metric(
    metric: str | None,
    *,
    source: str = "unknown",
    page_number: int | None = None,
    table_index: int | None = None,
    row_idx: int | None = None,
    col_idx: int | None = None,
) -> str | None:
    """Safely assign metric with MANDATORY validation.

    This wrapper function ALWAYS validates the metric before returning it.
    It is IMPOSSIBLE to bypass validation when using this function.

    Args:
        metric: Metric value to validate and assign
        source: Source of the metric (e.g., "header", "context_inference", "cell")
        page_number: Page number for logging (optional)
        table_index: Table index for logging (optional)
        row_idx: Row index for logging (optional)
        col_idx: Column index for logging (optional)

    Returns:
        Validated metric if valid, None if invalid

    Logging:
        - Logs warning if metric is invalid with full context
        - Logs debug if metric is valid (for audit trail)
    """
    if not metric:
        return None

    metric_clean = metric.strip()

    if validate_metric(metric_clean):
        logger.debug(
            f"Valid metric assigned from {source}: '{metric_clean}'",
            extra={
                "source": source,
                "metric": metric_clean,
                "page_number": page_number,
                "table_index": table_index,
                "row_idx": row_idx,
                "col_idx": col_idx,
            },
        )
        return metric_clean

    # Invalid metric - log warning and return None
    logger.warning(
        f"Invalid metric from {source} - rejected: '{metric_clean}'",
        extra={
            "source": source,
            "invalid_metric": metric_clean,
            "page_number": page_number,
            "table_index": table_index,
            "row_idx": row_idx,
            "col_idx": col_idx,
        },
    )
    return None


def safe_infer_entity_from_context(
    page_context: dict[str, Any],
    *,
    page_number: int | None = None,
    table_index: int | None = None,
    row_idx: int | None = None,
    col_idx: int | None = None,
) -> str | None:
    """Safely infer entity from page context with MANDATORY validation.

    This wrapper function ALWAYS validates the inferred entity before returning it.
    It is IMPOSSIBLE to bypass validation when using this function.

    Args:
        page_context: Page context dictionary with entity information
        page_number: Page number for logging (optional)
        table_index: Table index for logging (optional)
        row_idx: Row index for logging (optional)
        col_idx: Column index for logging (optional)

    Returns:
        Validated entity if valid, None if invalid or not found

    Context extraction:
        - Tries page_context.get("entity")
        - Tries page_context.get("heading")
        - Returns None if no context found
    """
    # Try to extract entity from context
    inferred_entity = page_context.get("entity") or page_context.get("heading")

    if not inferred_entity:
        return None

    # MANDATORY validation via safe_assign_entity
    return safe_assign_entity(
        inferred_entity,
        source="context_inference",
        page_number=page_number,
        table_index=table_index,
        row_idx=row_idx,
        col_idx=col_idx,
    )


def safe_infer_metric_from_context(
    page_context: dict[str, Any],
    *,
    page_number: int | None = None,
    table_index: int | None = None,
    row_idx: int | None = None,
    col_idx: int | None = None,
) -> str | None:
    """Safely infer metric from page context with MANDATORY validation.

    This wrapper function ALWAYS validates the inferred metric before returning it.
    It is IMPOSSIBLE to bypass validation when using this function.

    Args:
        page_context: Page context dictionary with metric information
        page_number: Page number for logging (optional)
        table_index: Table index for logging (optional)
        row_idx: Row index for logging (optional)
        col_idx: Column index for logging (optional)

    Returns:
        Validated metric if valid, None if invalid or not found

    Context extraction:
        - Tries page_context.get("metric")
        - Tries page_context.get("heading")
        - Returns None if no context found
    """
    # Try to extract metric from context
    inferred_metric = page_context.get("metric") or page_context.get("heading")

    if not inferred_metric:
        return None

    # MANDATORY validation via safe_assign_metric
    return safe_assign_metric(
        inferred_metric,
        source="context_inference",
        page_number=page_number,
        table_index=table_index,
        row_idx=row_idx,
        col_idx=col_idx,
    )
