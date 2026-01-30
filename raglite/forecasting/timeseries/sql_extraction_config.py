"""SQL extraction configuration and lookup functions.

Part of Story 8.1 refactoring to split sql_extraction.py.
"""

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


# Unit scaling factors to normalize to EUR millions (M EUR).
# Phase 2 data quality: Explicit unit-based normalization replaces value heuristics.
# Scale factor converts from source unit to M EUR.
UNIT_SCALING_FACTORS: dict[str | None, float] = {
    # EUR variants → normalize to EUR millions
    "EUR": 0.000001,  # 1 EUR = 0.000001 M EUR
    "K EUR": 0.001,  # 1 kEUR = 0.001 M EUR
    "kEUR": 0.001,
    "KEUR": 0.001,
    "1000 EUR": 0.001,
    "1.000 EUR": 0.001,  # European decimal separator
    "Thousands of EUR": 0.001,
    "M EUR": 1.0,  # Already in millions
    "MEUR": 1.0,
    "Meur": 1.0,
    "M€": 1.0,
    "EUR M": 1.0,
    "Million EUR": 1.0,
    "Millions EUR": 1.0,
    # Percentage (no scaling - different dimension)
    "%": 1.0,
    "Percent": 1.0,
    # Per-unit metrics (keep as-is - different dimension)
    "EUR/ton": 1.0,
    "Eur/ton": 1.0,
    "EUR/MWh": 1.0,
    "€/ton": 1.0,
    "€/MWh": 1.0,
    # Regional currencies in thousands → scale to M EUR (approximate)
    # Note: These need FX rates for accurate conversion, using 0.001 as proxy
    "1000 BRL": 0.001,  # ~0.0002 actual (BRL/EUR ~5.5)
    "1000 LBP": 0.001,  # Near zero (hyperinflation)
    "1000 AOA": 0.001,  # ~0.000012 actual
    # Unknown/missing → assume M EUR (current data scale)
    None: 1.0,
    "": 1.0,
}


def get_unit_scaling_factor(unit: str | None) -> float:
    """Get scaling factor to normalize unit to EUR millions.

    Args:
        unit: Unit string from database (may be None)

    Returns:
        Scaling factor (1.0 if unknown unit)

    Note:
        Unknown units log a warning and return 1.0 (no scaling).
        This preserves data while flagging potential issues.
    """
    if unit is None or unit == "":
        return 1.0

    cleaned_unit = unit.strip()
    factor = UNIT_SCALING_FACTORS.get(cleaned_unit)

    if factor is not None:
        return factor

    # Try case-insensitive lookup for common variants
    lower_unit = cleaned_unit.lower()
    for known_unit, known_factor in UNIT_SCALING_FACTORS.items():
        if known_unit and known_unit.lower() == lower_unit:
            return known_factor

    # Unknown unit - log warning and return 1.0
    logger.warning(
        "Unknown unit encountered, no scaling applied",
        extra={"unit": unit, "action": "no_scaling"},
    )
    return 1.0


# Data quality fix: Entities that are actually metrics (data contamination)
# These values were incorrectly stored in entity_normalized and should be excluded
# Note: EBITDA/EBITDA IFRS REMOVED (2026-01-29) - these are VALID entity values
# in the database representing metric groups, not contamination. Blocking them
# prevented Phase 3 fallback from extracting 338 rows of valid Portugal data.
CONTAMINATED_ENTITIES: set[str] = {
    # Cash flow metrics incorrectly stored as entities
    "CF from Operations",
    "Net interest expenses",
    "De(in)crease Trade Working Capital",
    "CF from Operating Activities",
    "Other Working Capital Variances",
    "Trade Working Capital",
    # Working capital and other financial metrics
    "Net Income",
    # EBITDA removed - valid entity value representing metric group
    # EBITDA IFRS removed - valid entity value representing metric group
    "Revenue",
    "Turnover",
}


# Entities to EXCLUDE for GROUP-level metrics (EBITDA, consolidated revenue)
# These are valid entities for regional metrics but should not be used for GROUP aggregation
# Forecast debug fix (2026-01-28): Prevents mixing GROUP-level with segment-level data
# Phase 3 Quality Fix (2026-01-29): Removed Portugal from exclusion list since we want
# to aggregate Portugal + Portugal sub-regions (Cape Verde, Madeira, etc.)
SEGMENT_ENTITIES_FOR_GROUP_EXCLUSION: set[str] = {
    # "Portugal" - REMOVED: We want to aggregate Portugal sub-regions
    "Portugal + Spain",
    "Spain",
    "Iberia",
    "Brazil",
    "Tunisia",
    "Lebanon",
    "Angola",
    "Cape Verde",
    "Cabo Verde",
}


def get_contaminated_entities() -> set[str]:
    """Get entities that are actually metrics (data contamination).

    These are metric names that were incorrectly stored in the entity column
    and should be excluded from entity filtering to prevent incorrect matches.

    Returns:
        Set of contaminated entity names to exclude
    """
    return CONTAMINATED_ENTITIES


def get_segment_entities_for_group_exclusion() -> set[str]:
    """Get segment entities to exclude when querying GROUP-level data.

    For metrics like EBITDA that should use consolidated GROUP data,
    these regional segment entities should be excluded to prevent
    mixing GROUP-level with segment-level data.

    Forecast debug fix (2026-01-28): Prevents incorrect EBITDA values
    from regional segments being used instead of consolidated GROUP.

    Returns:
        Set of segment entity names to exclude for GROUP metrics
    """
    return SEGMENT_ENTITIES_FOR_GROUP_EXCLUSION


def get_metric_synonyms() -> dict[str, str]:
    """Get metric name synonym mappings.

    Story 6.26: Routes metrics to their canonical database names.
    Phase 3 Fix (2026-01-29): DO NOT add exact DB metric names here!
    Synonyms are for user-friendly aliases (e.g., "revenue" → "turnover"),
    not for exact DB names like "Turnover+VAT" which should be passed through.
    """
    return {
        "revenue": "turnover",
        "revenues": "turnover",
        "sales": "turnover",
        # NOTE: Do NOT add turnover+vat here - it's an exact DB metric name!
        # EBITDA mapping
        "ebitda": "EBITDA IFRS",
        # Electricity cost synonyms
        "electricity_cost": "Electrical Energy",
        "electricity": "Electrical Energy",
        # Thermal cost synonyms
        "thermal_cost": "Thermal Energy",
        "fuel_cost": "Thermal Energy",
        # Variable cost synonym (case variants)
        "variable_cost": "Variable Cost",
    }


def get_entity_filters() -> dict[str, tuple[str | None, bool]]:
    """Get entity filter configuration for metrics.

    Format: metric -> (entity_filter, prefer_ytd)

    Story 6.28: GROUP filter for EBITDA IFRS - REMOVED (2026-01-29)
    Story 6.29: Portugal filter for regional metrics to prevent contamination.
    Phase 2 data quality: Added turnover/revenue with no entity filter.

    Note on EBITDA IFRS (2026-01-29): Changed from ("GROUP", True) to (None, True)
    because database has entity="Portugal" with 338 rows of valid EBITDA IFRS data,
    but NO entity="GROUP" data exists. The GROUP filter returned 0 rows, falling
    back to Phase 3 which was blocked by CONTAMINATED_ENTITIES.

    Note on turnover: Data analysis shows turnover has entity="Currency (1000 EUR)"
    not "GROUP", so entity filtering is disabled (None) to allow all entities.
    The unit normalization (Phase 2) handles the kEUR scaling instead.
    """
    return {
        # EBITDA IFRS: No entity filter - allow Portugal-level data (338 rows)
        # MAX aggregation handles duplicate prevention
        # Phase 5 Data Quality Fix (2026-01-29): Changed prefer_ytd from True to False
        # Root cause: YTD filtering was overly restrictive, reducing 338 rows to ~40
        # Most EBITDA data uses standard monthly period format, not YTD
        "EBITDA IFRS": (None, False),
        # Turnover/Revenue: No entity filter - uses unit-based normalization instead
        # Entity values are "Currency (1000 EUR)" not "GROUP"
        "turnover": (None, False),
        # Phase 3 Fix (2026-01-29): Explicit Turnover+VAT entries with correct entity
        # Database stores this with entity="Currency (1000 EUR)" - aligns with validation script
        "Turnover+VAT": ("Currency (1000 EUR)", False),
        "turnover+vat": ("Currency (1000 EUR)", False),
        "Sales Volumes": ("portugal", False),
        "sales volumes": ("portugal", False),
        "Volume IM - kton": ("portugal", False),
        "Sales Price EM - Cement": ("portugal", False),
        "Sales Price IM": ("portugal", False),
        "Sales Price-Transport Cost": ("portugal", False),
        "selling_price": ("portugal", False),
        "Variable Cost": ("portugal", False),
        "variable cost": ("portugal", False),
        "Other Variable Costs": ("portugal", False),
        "Electrical Energy": ("portugal", False),
        "electrical energy": ("portugal", False),
        "electricity": ("portugal", False),
        "Thermal Energy": ("portugal", False),
        "thermal energy": ("portugal", False),
        "fuel_cost": ("portugal", False),
    }


def get_max_aggregation_metrics() -> set[str]:
    """Get metrics that use MAX aggregation instead of SUM.

    Story 6.26: MAX prevents duplicate document summing for consolidated metrics.
    Phase 2 data quality: Added turnover to prevent duplicate summing.
    """
    return {
        "EBITDA IFRS",
        "ebitda ifrs",
        "turnover",
        "Turnover",
        "Sales Price EM - Cement",
        "Sales Price IM",
        "Sales Price-Transport Cost",
        "selling_price",
        "Sales Volumes",
        "sales volumes",
        "Volume IM - kton",
    }


def get_avg_aggregation_metrics() -> set[str]:
    """Get metrics that use AVG aggregation.

    Story 7.0: AVG normalizes row count variance for electrical energy.
    """
    return {
        "Electrical Energy",
        "electrical energy",
    }


def get_min_aggregation_metrics() -> set[str]:
    """Get metrics that use MIN aggregation.

    Story 6.29 P1: Currently empty after testing showed SUM works better for costs.
    """
    return set()


def determine_aggregation_function(metric_search: str, default_aggregation: str) -> str:
    """Determine the aggregation function to use for a metric.

    Args:
        metric_search: The metric name after synonym mapping
        default_aggregation: Default aggregation method from parameter

    Returns:
        Aggregation function: "sum", "max", "avg", or "min"
    """
    if metric_search in get_avg_aggregation_metrics():
        return "avg"
    elif metric_search in get_max_aggregation_metrics():
        return "max"
    elif metric_search in get_min_aggregation_metrics():
        return "min"
    else:
        return default_aggregation


def prefer_group_level(entity: str | None, metric: str) -> str | None:
    """For metrics that aggregate regionally, prefer GROUP-level data.

    Story 6.10.1 AC5: For aggregate metrics like EBITDA,
    prefer GROUP-level consolidated data to avoid mixing regional data
    which causes high MAPE from aggregating incompatible data sources.

    Story 6.10.4 Fix: Return None for non-aggregate metrics to disable
    entity filtering (allow all entities). Previously returned "Group"
    by default which caused 10/12 SKIPs due to missing GROUP-level data.

    Story 6.10.4 Revenue Fix: Removed "revenue" and "turnover" from GROUP
    metrics because turnover data in database has entity="Currency (1000 EUR)",
    not "GROUP". Filtering by GROUP returns 0 rows causing 101,488% MAPE.

    Fix 2026-01-29: REMOVED EBITDA from GROUP_PREFERRED_METRICS because
    database has NO entity="GROUP" data for EBITDA - only entity="Portugal"
    with 338 valid rows. Forcing GROUP returned 0 rows causing extraction failure.

    Args:
        entity: Requested entity (may be None)
        metric: Metric name being extracted

    Returns:
        'Group' for aggregate metrics when no specific entity requested,
        original entity if specified, or None to disable entity filter.
    """
    # Fix 2026-01-29: EBITDA removed - no GROUP data exists in database
    # Database has entity="Portugal" (338 rows) and entity="EBITDA IFRS" (valid)
    GROUP_PREFERRED_METRICS: set[str] = set()  # Empty - no metrics need GROUP filter

    metric_lower = metric.lower().strip()

    # If this is a GROUP-preferred metric and no specific entity requested
    if metric_lower in GROUP_PREFERRED_METRICS and entity is None:
        return "Group"

    # Return entity if specified, None otherwise
    return entity


def get_percentage_metrics() -> set[str]:
    """Get metrics that represent percentages (0-100 range).

    Story 6.24.1: Percentage metrics need bounds checking and year value filtering.
    Phase 3 Quality Fix (2026-01-29): The code uses metric.lower() before checking,
    so all entries MUST be lowercase. Added "frequency ratio  (1)" with double spaces
    to match the exact DB metric name after lowercasing.
    """
    return {
        # Lowercase entries (code calls metric.lower() before checking)
        "frequency ratio",
        "frequency ratio  (1)",  # Exact DB name lowercased - NOTE: double spaces!
        "capacity_utilization",
        "capacity utilization",
        "utilization",
    }


def get_cost_metrics() -> set[str]:
    """Get metrics that represent costs (need absolute value conversion).

    Story 6.23: Cost metrics are recorded as negative but need positive values for forecasting.
    Phase 3 Quality Fix (2026-01-29): The code uses metric.lower() before checking,
    so all entries MUST be lowercase. No capitalized variations needed.
    """
    return {
        # Lowercase entries (code calls metric.lower() before checking)
        "electrical energy",
        "electricity",
        "electricity_cost",
        "thermal energy",
        "thermal",
        "thermal_cost",
        "fuel_cost",
        "variable cost",
        "variable_cost",
        "other variable costs",
    }


def get_ebitda_metrics() -> set[str]:
    """Get EBITDA-related metrics.

    Story 6.25.1: EBITDA metrics need special YTD normalization handling.
    """
    return {"ebitda", "ebitda ifrs"}
