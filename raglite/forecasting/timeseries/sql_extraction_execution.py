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


def build_entity_level_filter_clause(entity_level: str | None) -> str:
    """Build entity_level filter SQL clause for Epic 9 multi-entity support.

    Uses the entity_level column populated by Epic 9 classification pipeline
    to filter by semantic entity classification rather than entity name matching.

    Args:
        entity_level: Entity level to filter by: 'consolidated', 'geographic',
                     'segment', 'company_only', or None (no filter)

    Returns:
        SQL WHERE clause fragment (e.g., "AND entity_level = 'geographic'")
        or empty string if entity_level is None
    """
    if entity_level is None:
        return ""

    # Validate entity_level value to prevent SQL injection
    valid_levels = {"consolidated", "geographic", "segment", "company_only"}
    entity_level_lower = entity_level.lower().strip()

    if entity_level_lower not in valid_levels:
        logger.warning(
            "Invalid entity_level provided, ignoring filter",
            extra={"entity_level": entity_level, "valid_levels": list(valid_levels)},
        )
        return ""

    logger.info(
        "Building entity_level filter (Epic 9 multi-entity support)",
        extra={"entity_level": entity_level_lower},
    )
    return f"AND entity_level = '{entity_level_lower}'"


def build_entity_filter_clause(
    metric_search: str,
    ENTITY_FILTERS: dict[str, tuple[str | None, bool]],
    entity_level: str | None = None,
) -> tuple[str, str, bool]:
    """Build entity filter SQL clause.

    Args:
        metric_search: Metric name after synonym resolution
        ENTITY_FILTERS: Entity filter configuration dict
        entity_level: Optional entity level for Epic 9 filtering.
                     When specified, entity_level takes precedence over entity name filtering.
                     This enables multi-entity queries like "all geographic entities" instead
                     of hardcoded single-entity filtering.

    Returns:
        Tuple of (entity_filter SQL clause, entity_level_filter SQL clause, prefer_ytd flag)

    Note:
        Epic 9 multi-entity support: When entity_level is specified, we skip the entity name
        filter and rely purely on entity_level classification. This allows queries like
        entity_level='geographic' to return ALL geographic entities (Portugal, Angola, Brazil,
        Tunisia, Lebanon) instead of just one hardcoded entity.
    """
    entity_filter = ""
    prefer_ytd = False
    filter_config = ENTITY_FILTERS.get(metric_search)

    # Epic 9 multi-entity support: When entity_level is specified, skip entity name filtering
    # and rely on semantic entity_level classification instead.
    if entity_level is not None:
        # Get prefer_ytd from config if available, but skip entity name filter
        if filter_config:
            _, prefer_ytd = filter_config
        logger.info(
            "Using entity_level filter instead of entity name filter (Epic 9 multi-entity)",
            extra={
                "metric": metric_search,
                "entity_level": entity_level,
                "prefer_ytd": prefer_ytd,
                "skipped_entity_filter": True,
            },
        )
        # Skip to entity_level filter building
        entity_level_filter = build_entity_level_filter_clause(entity_level)
        return entity_filter, entity_level_filter, prefer_ytd

    if filter_config:
        required_entity, prefer_ytd = filter_config
        if required_entity is not None:
            canonical_entity = normalize_entity(required_entity)
            canonical = canonical_entity or required_entity

            if canonical.upper() == "GROUP":
                # Epic 9: Use entity_normalized column instead of hardcoded variations
                # entity_normalized='Group' covers GROUP, SECIL Group, Total, Consolidated, etc.
                segment_entities = get_segment_entities_for_group_exclusion()
                segment_exclusion_sql = ", ".join(f"'{e}'" for e in segment_entities)

                # Non-EUR currencies and incompatible unit types for GROUP-level queries.
                # BRL/AOA/TND/LBP rows mixed with EUR cause "unit mixing too severe".
                # FIX (2026-02-03): Also exclude '%' (EBITDA margin, not monetary) and
                # 'EUR/ton' (per-unit pricing, not totals). These are different metrics
                # that should never aggregate with M EUR monetary totals.
                non_eur_and_incompatible_units = (
                    "'1000 BRL','BRL','BRL/ton','BRL/m3',"
                    "'AOA','1000 AOA','AOA/ton',"
                    "'LBP','1000 LBP','LBP/ton',"
                    "'TND','1000 TND','TND/ton',"
                    "'%%','EUR/ton'"
                )

                entity_filter = f"""AND entity_normalized = 'Group'
                      AND entity_level NOT IN ('geographic', 'segment')
                      AND (unit IS NULL OR unit NOT IN ({non_eur_and_incompatible_units}))
                      AND entity NOT LIKE '%%+%%'
                      AND entity NOT IN ({segment_exclusion_sql})"""
                logger.info(
                    "Using entity_normalized GROUP filter (Epic 9)",
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

    # Epic 9 multi-entity support: Build entity_level filter
    entity_level_filter = build_entity_level_filter_clause(entity_level)

    return entity_filter, entity_level_filter, prefer_ytd


async def execute_sql_with_fallback(
    metric: str,
    metric_search: str,
    entity_filter: str,
    entity_level_filter: str,
    prefer_ytd: bool,
    aggregation: str,
) -> list[tuple[Any, ...]]:
    """Execute SQL query with exact match first, wildcard fallback, entity column fallback.

    Args:
        metric: Original metric name
        metric_search: Metric name after synonym resolution
        entity_filter: SQL entity filter clause
        entity_level_filter: SQL entity_level filter clause (Epic 9 multi-entity support)
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
        metric_condition, entity_filter, prefer_ytd, aggregation, value_filter, entity_level_filter
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
            metric_condition,
            entity_filter,
            prefer_ytd,
            aggregation,
            value_filter,
            entity_level_filter,
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
        # Also skip entity_level_filter for inverted data pattern
        query = build_timeseries_query(
            metric_condition, "", prefer_ytd, aggregation, value_filter, ""
        )
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
    entity_level: str | None = None,
) -> tuple[str, str, dict[str, tuple[str | None, bool]], str | None]:
    """Configure extraction parameters (synonyms, aggregation, entity filters).

    Args:
        metric: Original metric name
        aggregation: Aggregation method
        entity: Optional entity filter
        entity_level: Optional entity_level filter (Epic 9 multi-entity support)

    Returns:
        Tuple of (metric_search, final_aggregation, ENTITY_FILTERS, entity_level)
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

    # Log entity_level if specified
    if entity_level:
        logger.info(
            "Entity level filter specified (Epic 9 multi-entity support)",
            extra={"metric": metric, "entity_level": entity_level},
        )

    return metric_search, aggregation, ENTITY_FILTERS, entity_level
