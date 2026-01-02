"""SQL extraction execution helpers.

Handles SQL query execution, entity filtering, and configuration logic.
Part of Story 8.1 refactoring to split sql_extraction.py.
"""

from raglite.forecasting.timeseries.sql_extraction_config import (
    determine_aggregation_function,
    get_entity_filters,
    get_metric_synonyms,
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
        canonical_entity = normalize_entity(entity)
        if canonical_entity:
            ENTITY_FILTERS[metric_search] = (canonical_entity, False)
            logger.info(
                "User-specified entity filter applied",
                extra={"metric": metric, "entity": entity, "canonical": canonical_entity},
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
                entity_filter = f"""AND (
                          UPPER(entity) = '{required_entity.upper()}'
                          OR entity = 'SECIL Group'
                      )
                      AND entity NOT LIKE '%%+%%'"""
                logger.info(
                    "Using GROUP priority-based entity selection (Story 6.28)",
                    extra={
                        "metric": metric_search,
                        "required_entity": required_entity,
                        "entity_priority": "GROUP > SECIL Group",
                        "prefer_ytd": prefer_ytd,
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
    return entity_filter, prefer_ytd


async def execute_sql_with_fallback(
    metric: str,
    metric_search: str,
    entity_filter: str,
    prefer_ytd: bool,
    aggregation: str,
) -> list[tuple]:
    """Execute SQL query with exact match first, wildcard fallback.

    Args:
        metric: Original metric name
        metric_search: Metric name after synonym resolution
        entity_filter: SQL entity filter clause
        prefer_ytd: Whether to prefer YTD periods
        aggregation: Aggregation function

    Returns:
        List of SQL result rows

    Raises:
        ExtractionError: If no data found after both attempts
    """
    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Try exact match first
    metric_condition = "metric = %s"
    metric_param = metric_search
    match_type = "exact"

    query = build_timeseries_query(metric_condition, entity_filter, prefer_ytd, aggregation)

    logger.debug(
        "Executing SQL query (exact match first)",
        extra={
            "metric_condition": metric_condition,
            "metric_param": metric_param,
            "match_type": match_type,
            "query_preview": query[:500],
        },
    )

    cursor.execute(query, (metric_param,))
    rows = cursor.fetchall()

    # If no results with exact match, try wildcard as fallback
    if not rows and match_type == "exact":
        logger.info(
            "No results with exact match, trying wildcard fallback",
            extra={"metric_search": metric_search},
        )

        # Switch to wildcard matching
        metric_condition = "LOWER(metric) LIKE %s"
        metric_param = f"%{metric_search.lower()}%"
        match_type = "wildcard"

        query = build_timeseries_query(metric_condition, entity_filter, prefer_ytd, aggregation)
        cursor.execute(query, (metric_param,))
        rows = cursor.fetchall()

        if rows:
            logger.info(
                "Wildcard fallback succeeded",
                extra={"rows_found": len(rows), "metric_param": metric_param},
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
