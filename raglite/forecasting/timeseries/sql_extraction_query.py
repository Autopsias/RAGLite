"""SQL query building for timeseries extraction.

Part of Story 8.1 refactoring to split sql_extraction.py.
Handles complex SQL query construction with entity filtering, YTD support, and deduplication.
"""


def _get_period_match_clause(prefer_ytd: bool) -> tuple[str, str, str]:
    """Get period matching clause based on YTD preference.

    Args:
        prefer_ytd: If True, extract YTD periods (with monthly fallback);
                    if False, extract monthly periods only

    Returns:
        Tuple of (period_match_sql, period_extract_sql, is_ytd_flag)

    Note:
        Story 9.8: Simplified to use pre-classified period_type and value_type columns
        instead of complex regex patterns.

        Classification is done at ingestion time (Stories 9.1-9.7), so queries can
        use simple equality checks on indexed columns instead of regex scans.
    """
    if prefer_ytd:
        # YTD-only mode: Extract ONLY ytd_actual periods (no monthly fallback)
        # FIX (2026-02-03): Mixing YTD and monthly in the same query caused negative
        # values — monthly value (18M) minus previous YTD (200M) = -182M after
        # finalize_timeseries() applied YTD→monthly conversion to ALL points.
        # YTD-only extraction is safe: EBITDA has 28+ distinct YTD periods.
        # If no YTD data exists, Phase 2/3 fallbacks in execute_sql_with_fallback() handle it.
        period_match = """
              AND period_type = 'ytd_actual'
              AND value_type = 'actual'"""
        period_extract = "(REGEXP_MATCH(period, '([A-Za-z]{3}-[0-9]{2,4})'))[1]"
        # Dynamic: TRUE if period_type is ytd_actual
        is_ytd_flag = "CASE WHEN period_type = 'ytd_actual' THEN TRUE ELSE FALSE END"
    else:
        # Standard mode: Extract monthly_actual periods only
        # Epic 9: All rows classified at ingestion - strict equality (no NULL fallback)
        period_match = """AND period_type = 'monthly_actual'
              AND value_type = 'actual'"""
        period_extract = "period"
        is_ytd_flag = "FALSE"
    return period_match, period_extract, is_ytd_flag


def _get_entity_priority_expr(entity_filter: str) -> str:
    """Get entity priority expression based on filter configuration.

    Args:
        entity_filter: SQL entity filter clause

    Returns:
        SQL expression for entity priority (1=highest, 3=lowest)
    """
    use_entity_priority = bool(entity_filter.strip())
    if use_entity_priority:
        return """CASE
                    WHEN UPPER(entity) = 'GROUP' THEN 1
                    WHEN entity = 'SECIL Group' THEN 2
                    ELSE 3
                END"""
    else:
        return "1"  # Constant when no filter


def _get_month_translation_case() -> str:
    """Get SQL CASE statement for Portuguese month abbreviations.

    Returns:
        SQL CASE statement that translates Portuguese months to English
    """
    return """CASE SUBSTRING(ft.clean_period FROM 1 FOR 3)
                WHEN 'Fev' THEN 'Feb' || SUBSTRING(ft.clean_period FROM 4)
                WHEN 'Abr' THEN 'Apr' || SUBSTRING(ft.clean_period FROM 4)
                WHEN 'Mai' THEN 'May' || SUBSTRING(ft.clean_period FROM 4)
                WHEN 'Ago' THEN 'Aug' || SUBSTRING(ft.clean_period FROM 4)
                WHEN 'Set' THEN 'Sep' || SUBSTRING(ft.clean_period FROM 4)
                WHEN 'Out' THEN 'Oct' || SUBSTRING(ft.clean_period FROM 4)
                WHEN 'Dez' THEN 'Dec' || SUBSTRING(ft.clean_period FROM 4)
                ELSE ft.clean_period
            END"""


def _build_periods_with_year_cte(
    period_extract: str,
    is_ytd_flag: str,
    entity_priority_expr: str,
    metric_condition: str,
    period_match: str,
    entity_filter: str,
    value_filter: str = "",
    entity_level_filter: str = "",
) -> str:
    """Build the periods_with_year CTE.

    Args:
        period_extract: SQL expression to extract period
        is_ytd_flag: TRUE or FALSE string
        entity_priority_expr: SQL expression for entity priority
        metric_condition: SQL WHERE clause for metric
        period_match: SQL WHERE clause for period matching
        entity_filter: SQL WHERE clause for entity filtering
        value_filter: Optional SQL WHERE clause for value filtering (e.g., "AND value < 50")
        entity_level_filter: Optional SQL WHERE clause for entity_level filtering
                            (e.g., "AND entity_level = 'geographic'"). Epic 9 multi-entity support.

    Returns:
        SQL CTE string
    """
    return f"""periods_with_year AS (
            -- Extract fiscal year from period when fiscal_year is NULL
            -- For YTD data: "YTD  Apr-25" → Apr-25 → 2025
            -- For standard: "Jan-25" → 2025
            SELECT
                -- Extract the Mon-YY portion (strip YTD prefix if present)
                {period_extract} as clean_period,
                -- Flag whether this is YTD data
                {is_ytd_flag} as is_ytd,
                -- Infer fiscal year from the Mon-YY suffix (e.g., "Jun-25" → 2025)
                2000 + CAST(SUBSTRING(period FROM '[0-9]{{2}}$') AS INTEGER) as inferred_fiscal_year,
                document_id,
                value,
                entity,
                entity_normalized,
                metric,
                -- Unit column for explicit unit-based normalization (Phase 2 data quality)
                unit,
                -- Entity priority for selection: prefer GROUP over SECIL Group
                -- FIX (2025-12-22): Only when entity_filter configured, else constant 1
                {entity_priority_expr} as entity_priority
            FROM financial_tables
            WHERE {metric_condition}
              AND period IS NOT NULL
              {period_match}
              AND value IS NOT NULL
              {entity_filter}
              {entity_level_filter}
              {value_filter}
        )"""


def _build_entity_deduplication_ctes() -> str:
    """Build CTEs for entity-based deduplication.

    Returns:
        SQL CTEs for best_entity_per_period and filtered_by_entity

    Note:
        filtered_by_entity preserves all columns from periods_with_year including unit.
    """
    return """best_entity_per_period AS (
            -- For each period, select the highest-priority entity (GROUP > SECIL Group)
            SELECT
                clean_period,
                inferred_fiscal_year,
                MIN(entity_priority) as best_priority
            FROM periods_with_year
            GROUP BY clean_period, inferred_fiscal_year
        ),
        filtered_by_entity AS (
            -- Keep only rows matching the best entity for each period
            -- Preserves all columns including unit for downstream normalization
            SELECT p.*
            FROM periods_with_year p
            INNER JOIN best_entity_per_period be
                ON p.clean_period = be.clean_period
                AND p.inferred_fiscal_year = be.inferred_fiscal_year
                AND p.entity_priority = be.best_priority
        )"""


def _build_latest_doc_cte() -> str:
    """Build CTE for document-based deduplication.

    Returns:
        SQL CTE for latest_doc_per_period
    """
    return """latest_doc_per_period AS (
            -- For each period (using clean period without YTD prefix), identify the most recent document
            SELECT
                clean_period,
                inferred_fiscal_year,
                MAX(document_id) as latest_doc
            FROM filtered_by_entity
            GROUP BY clean_period, inferred_fiscal_year
        )"""


def _build_final_select(agg_func: str, month_translation: str) -> str:
    """Build the final SELECT statement.

    Args:
        agg_func: Aggregation function name (MAX, MIN, AVG, SUM, COUNT)
        month_translation: SQL CASE statement for month translation

    Returns:
        SQL SELECT statement

    Note:
        Phase 2 data quality: Includes unit column for explicit unit-based normalization.
        MODE() returns most common unit when multiple rows are aggregated.
    """
    return f"""SELECT
            ft.clean_period as period,
            ft.inferred_fiscal_year as fiscal_year,
            {agg_func}(ft.value) as total_value,
            COUNT(*) as row_count,
            MAX(ft.document_id) as source_doc,
            BOOL_OR(ft.is_ytd) as is_ytd_data,
            MODE() WITHIN GROUP (ORDER BY ft.unit) as unit
        FROM filtered_by_entity ft
        INNER JOIN latest_doc_per_period ld
            ON ft.clean_period = ld.clean_period
            AND ft.inferred_fiscal_year = ld.inferred_fiscal_year
            AND ft.document_id = ld.latest_doc
        GROUP BY ft.clean_period, ft.inferred_fiscal_year
        HAVING {agg_func}(ft.value) <> 0
        -- FIX (2025-12-09): Changed from > 0 to <> 0 to support cost metrics (negative values)
        -- FIX (2025-12-01): Sort chronologically, not alphabetically
        -- FIX (2025-12-22): Handle Portuguese month abbreviations (Fev, Abr, etc.) before TO_DATE
        ORDER BY ft.inferred_fiscal_year, TO_DATE({month_translation}, 'Mon-YY')"""


def build_timeseries_query(
    metric_condition: str,
    entity_filter: str,
    prefer_ytd: bool,
    aggregation: str,
    value_filter: str = "",
    entity_level_filter: str = "",
) -> str:
    """Build SQL query for timeseries extraction.

    Args:
        metric_condition: SQL WHERE clause for metric matching (e.g., "metric = %s")
        entity_filter: SQL WHERE clause for entity filtering (e.g., "AND entity = 'GROUP'")
        prefer_ytd: If True, extract YTD periods; if False, extract monthly periods
        aggregation: Aggregation function ("sum", "max", "avg", "min", "count")
        value_filter: Optional SQL WHERE clause for pre-aggregation value filtering
                     (e.g., "AND value < 50" for EBITDA to exclude mislabeled annual data)
        entity_level_filter: Optional SQL WHERE clause for entity_level filtering
                            (e.g., "AND entity_level = 'geographic'"). Epic 9 multi-entity support.

    Returns:
        SQL query string with placeholders for metric parameter

    Raises:
        ValueError: If invalid aggregation or SQL injection detected
    """
    # Security: Validate aggregation parameter to prevent SQL injection
    if aggregation.lower() not in ["sum", "max", "avg", "min", "count"]:
        raise ValueError(f"Invalid aggregation function: {aggregation}")

    agg_func_map = {
        "max": "MAX",
        "min": "MIN",
        "avg": "AVG",
        "sum": "SUM",
        "count": "COUNT",
    }
    agg_func = agg_func_map.get(aggregation.lower(), "SUM")

    # Security: Validate all SQL fragments before interpolation
    if not isinstance(metric_condition, str) or ";" in metric_condition:
        raise ValueError("Invalid metric condition")
    if not isinstance(entity_filter, str) or ";" in entity_filter:
        raise ValueError("Invalid entity filter")
    if not isinstance(value_filter, str) or ";" in value_filter:
        raise ValueError("Invalid value filter")
    if not isinstance(entity_level_filter, str) or ";" in entity_level_filter:
        raise ValueError("Invalid entity level filter")

    # Get configuration for query components
    period_match, period_extract, is_ytd_flag = _get_period_match_clause(prefer_ytd)
    entity_priority_expr = _get_entity_priority_expr(entity_filter)
    month_translation = _get_month_translation_case()

    # Build query CTEs
    periods_cte = _build_periods_with_year_cte(
        period_extract,
        is_ytd_flag,
        entity_priority_expr,
        metric_condition,
        period_match,
        entity_filter,
        value_filter,
        entity_level_filter,
    )
    entity_ctes = _build_entity_deduplication_ctes()
    latest_doc_cte = _build_latest_doc_cte()
    final_select = _build_final_select(agg_func, month_translation)

    # nosec B608 - SQL query uses validated internal variables only, not user input
    return f"""
        WITH {periods_cte},
        {entity_ctes},
        {latest_doc_cte}
        {final_select}
    """
