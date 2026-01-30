"""SQL extraction execution helpers.

Handles SQL query execution, entity filtering, and configuration logic.
Part of Story 8.1 refactoring to split sql_extraction.py.
"""

from typing import Any

from raglite.forecasting.timeseries.sql_extraction_config import (
    determine_aggregation_function,
    get_contaminated_entities,
    get_entity_filters,
    get_metric_synonyms,
    get_segment_entities_for_group_exclusion,
)
from raglite.forecasting.timeseries.sql_extraction_query import build_timeseries_query
from raglite.ingestion.entity_normalizer import (
    get_entity_exact_match_clause,
    normalize_entity,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def configure_entity_filter(
    metric: str,
    metric_search: str,
    entity: str | None,
) -> tuple[dict[str, tuple[str | None, bool]], str]:
    """Configure entity filter for SQL query.

    Args:
        metric: Original metric name
        metric_search: Metric name after synonym resolution
        entity: Optional user-specified entity

    Returns:
        Tuple of (ENTITY_FILTERS dict, canonical_entity or empty string)
    """
    from raglite.forecasting.timeseries.sql_extraction_config import prefer_group_level

    ENTITY_FILTERS = get_entity_filters().copy()

    if entity is not None:
        # User-specified entity filter takes precedence
        # Fix 2026-01-30: Preserve prefer_ytd from original config when overriding entity
        canonical_entity = normalize_entity(entity)
        if canonical_entity:
            # Get original prefer_ytd from config (if exists), otherwise False
            existing_config = ENTITY_FILTERS.get(metric_search)
            original_prefer_ytd = existing_config[1] if existing_config else False
            ENTITY_FILTERS[metric_search] = (canonical_entity, original_prefer_ytd)
            logger.info(
                "User-specified entity filter applied",
                extra={
                    "metric": metric,
                    "entity": entity,
                    "canonical": canonical_entity,
                    "prefer_ytd": original_prefer_ytd,
                },
            )
        return ENTITY_FILTERS, canonical_entity or entity
    else:
        # Dynamically add GROUP filter for aggregate metrics
        preferred_entity = prefer_group_level(None, metric)
        if preferred_entity == "Group" and metric_search not in ENTITY_FILTERS:
            ENTITY_FILTERS[metric_search] = ("GROUP", False)
            logger.debug(
                "Dynamic GROUP filter applied via prefer_group_level",
                extra={"metric": metric, "metric_search": metric_search},
            )
        return ENTITY_FILTERS, ""


def build_entity_filter_clause(
    metric_search: str,
    ENTITY_FILTERS: dict[str, tuple[str | None, bool]],
) -> tuple[str, bool]:
    """Build entity filter SQL clause.

    Args:
        metric_search: Metric name after synonym resolution
        ENTITY_FILTERS: Entity filter configuration dict

    Returns:
        Tuple of (entity_filter SQL clause, prefer_ytd flag)
    """
    entity_filter = ""
    prefer_ytd = False
    filter_config = ENTITY_FILTERS.get(metric_search)
    if filter_config:
        required_entity, prefer_ytd = filter_config
        if required_entity is not None:
            canonical_entity = normalize_entity(required_entity)
            canonical = canonical_entity or required_entity

            if canonical.upper() == "GROUP":
                # Include all GROUP variations from entity_normalizer.py
                # Story 6.28: Expanded filter for complete GROUP entity matching
                group_variations = [
                    "GROUP",
                    "Group",
                    "SECIL Group",
                    "Secil Group",
                    "SECIL GROUP",
                    "Total",
                    "TOTAL",
                    "Consolidado",
                    "Consolidated",
                    "Group Total",
                    "Total Group",
                    "Conso",
                    "CONSO",
                    "Groupe",
                ]
                variations_sql = ", ".join(f"'{v}'" for v in group_variations)

                # Forecast debug fix (2026-01-28): Exclude segment entities
                # to prevent mixing GROUP-level with regional segment data
                segment_entities = get_segment_entities_for_group_exclusion()
                segment_exclusion_sql = ", ".join(f"'{e}'" for e in segment_entities)

                entity_filter = f"""AND (
                          entity IN ({variations_sql})
                          OR UPPER(entity) = 'GROUP'
                      )
                      AND entity NOT LIKE '%%+%%'
                      AND entity NOT IN ({segment_exclusion_sql})"""
                logger.info(
                    "Using GROUP priority-based entity selection (Story 6.28)",
                    extra={
                        "metric": metric_search,
                        "required_entity": required_entity,
                        "entity_priority": "GROUP > SECIL Group",
                        "prefer_ytd": prefer_ytd,
                        "segment_exclusion": len(segment_entities),
                    },
                )
            else:
                exact_clause = get_entity_exact_match_clause(canonical)
                entity_filter = f"""AND {exact_clause}
                      AND entity NOT LIKE '%%+%%'"""
                logger.info(
                    "Using exact entity match clause (Story 6.29 entity contamination fix)",
                    extra={
                        "metric": metric_search,
                        "required_entity": required_entity,
                        "canonical": canonical,
                        "exact_clause": exact_clause,
                        "prefer_ytd": prefer_ytd,
                    },
                )
        else:
            logger.info(
                "Using YTD period mode without entity filter",
                extra={"metric": metric_search, "prefer_ytd": prefer_ytd},
            )

    # Data quality fix: Always exclude contaminated entities (metrics stored as entities)
    contaminated = get_contaminated_entities()
    if contaminated:
        contaminated_sql = ", ".join(f"'{e}'" for e in contaminated)
        exclusion_clause = f"AND (entity IS NULL OR entity NOT IN ({contaminated_sql}))"
        if entity_filter:
            entity_filter = f"{entity_filter}\n                      {exclusion_clause}"
        else:
            entity_filter = exclusion_clause

    return entity_filter, prefer_ytd


async def execute_sql_with_fallback(
    metric: str,
    metric_search: str,
    entity_filter: str,
    prefer_ytd: bool,
    aggregation: str,
) -> list[tuple[Any, ...]]:
    """Execute SQL query with exact match first, wildcard fallback, entity column fallback.

    Args:
        metric: Original metric name
        metric_search: Metric name after synonym resolution
        entity_filter: SQL entity filter clause
        prefer_ytd: Whether to prefer YTD periods
        aggregation: Aggregation function

    Returns:
        List of SQL result rows

    Raises:
        ExtractionError: If no data found after all attempts

    Note:
        Phase 3 (entity column fallback) handles inverted data where the metric name
        is stored in the entity column instead of the metric column (e.g., when
        entity="EBITDA IFRS" and metric=NULL).
    """
    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Phase 5 Data Quality Fix (2026-01-29): REMOVED pre-aggregation filter for EBITDA
    # Root cause analysis: 338 EBITDA rows exist in database, but cascading filters
    # (SQL value filter + YTD preference + outlier bounds) reduced to only 6-8 rows
    # causing MASE > 1.0 (worse than naive baseline).
    #
    # Solution: Remove pre-aggregation SQL filter - post-aggregation MAD-based
    # outlier detection in _normalization.py is more statistically sound and
    # handles extreme values appropriately after aggregation.
    #
    # Historical note: Previous filters were:
    # - ABS(value) < 50 (too aggressive, 2026-01-28)
    # - ABS(value) < 200 (still too aggressive, 2026-01-29)
    # Both created artificial data sparsity.
    value_filter = ""
    # EBITDA no longer needs pre-aggregation filtering - let normalization handle outliers

    # Phase 1: Try exact match first
    metric_condition = "metric = %s"
    metric_param = metric_search
    match_type = "exact"

    query = build_timeseries_query(
        metric_condition, entity_filter, prefer_ytd, aggregation, value_filter
    )

    logger.debug(
        "Phase 1: Executing SQL query (exact match)",
        extra={
            "metric_condition": metric_condition,
            "metric_param": metric_param,
            "match_type": match_type,
            "query_preview": query[:500],
        },
    )

    cursor.execute(query, (metric_param,))
    rows: list[tuple[Any, ...]] = cursor.fetchall()

    # Phase 2: If no results with exact match, try wildcard fallback
    if not rows:
        logger.info(
            "Phase 1 failed, trying Phase 2: wildcard fallback",
            extra={"metric_search": metric_search},
        )

        metric_condition = "LOWER(metric) LIKE %s"
        metric_param = f"%{metric_search.lower()}%"
        match_type = "wildcard"

        query = build_timeseries_query(
            metric_condition, entity_filter, prefer_ytd, aggregation, value_filter
        )
        cursor.execute(query, (metric_param,))
        rows = cursor.fetchall()

        if rows:
            logger.info(
                "Phase 2 wildcard fallback succeeded",
                extra={"rows_found": len(rows), "metric_param": metric_param},
            )

    # Phase 3: If still no results, try entity column fallback (for inverted data)
    # This handles cases where metric name is in entity column and metric column is NULL
    if not rows:
        logger.info(
            "Phase 2 failed, trying Phase 3: entity column fallback for inverted data",
            extra={"metric_search": metric_search},
        )

        # Search entity column when metric is NULL or 'None' (inverted data pattern)
        # Disable entity filter since entity column contains the metric name
        metric_condition = """(
            LOWER(entity) LIKE %s
            AND (metric IS NULL OR metric = 'None' OR TRIM(metric) = '')
        )"""
        metric_param = f"%{metric_search.lower()}%"
        match_type = "entity_fallback"

        # Build query WITHOUT entity filter (empty string) since entity has metric data
        query = build_timeseries_query(metric_condition, "", prefer_ytd, aggregation, value_filter)
        cursor.execute(query, (metric_param,))
        rows = cursor.fetchall()

        if rows:
            logger.info(
                "Phase 3 entity column fallback succeeded (inverted data detected)",
                extra={
                    "rows_found": len(rows),
                    "metric_param": metric_param,
                    "match_type": match_type,
                },
            )

    cursor.close()
    return rows


def configure_extraction(
    metric: str,
    aggregation: str,
    entity: str | None,
) -> tuple[str, str, dict[str, tuple[str | None, bool]]]:
    """Configure extraction parameters (synonyms, aggregation, entity filters).

    Args:
        metric: Original metric name
        aggregation: Aggregation method
        entity: Optional entity filter

    Returns:
        Tuple of (metric_search, final_aggregation, ENTITY_FILTERS)
    """
    # Apply metric synonyms (revenue → turnover, ebitda → EBITDA IFRS, etc.)
    metric_search = get_metric_synonyms().get(metric.lower(), metric)

    # Determine aggregation function based on metric type
    aggregation = determine_aggregation_function(metric_search, aggregation)
    if aggregation != "sum":
        logger.info(
            f"Using {aggregation.upper()} aggregation for {metric_search}",
            extra={"metric": metric_search, "aggregation": aggregation},
        )

    # Configure entity filters
    ENTITY_FILTERS, _ = configure_entity_filter(metric, metric_search, entity)

    return metric_search, aggregation, ENTITY_FILTERS
