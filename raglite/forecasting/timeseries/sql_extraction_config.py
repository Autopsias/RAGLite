"""SQL extraction configuration and lookup functions.

Part of Story 8.1 refactoring to split sql_extraction.py.
"""

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def get_metric_synonyms() -> dict[str, str]:
    """Get metric name synonym mappings.

    Story 6.26: Routes metrics to their canonical database names.
    """
    return {
        "revenue": "turnover",
        "revenues": "turnover",
        "sales": "turnover",
        "ebitda": "EBITDA IFRS",
        "electricity_cost": "Electrical Energy",
        "electricity": "Electrical Energy",
    }


def get_entity_filters() -> dict[str, tuple[str | None, bool]]:
    """Get entity filter configuration for metrics.

    Format: metric -> (entity_filter, prefer_ytd)

    Story 6.28: GROUP filter for EBITDA IFRS to prevent entity mixing.
    Story 6.29: Portugal filter for regional metrics to prevent contamination.
    """
    return {
        "EBITDA IFRS": ("GROUP", True),
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
    """
    return {
        "EBITDA IFRS",
        "ebitda ifrs",
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

    Args:
        entity: Requested entity (may be None)
        metric: Metric name being extracted

    Returns:
        'Group' for aggregate metrics when no specific entity requested,
        original entity if specified, or None to disable entity filter.
    """
    # Story 6.10.4: Only EBITDA has actual GROUP-level data in database
    GROUP_PREFERRED_METRICS: set[str] = {"ebitda"}

    metric_lower = metric.lower().strip()

    # If this is a GROUP-preferred metric and no specific entity requested
    if metric_lower in GROUP_PREFERRED_METRICS and entity is None:
        return "Group"

    # Return entity if specified, None otherwise
    return entity


def get_percentage_metrics() -> set[str]:
    """Get metrics that represent percentages (0-100 range).

    Story 6.24.1: Percentage metrics need bounds checking and year value filtering.
    """
    return {
        "frequency ratio",
        "capacity_utilization",
        "capacity utilization",
        "utilization",
    }


def get_cost_metrics() -> set[str]:
    """Get metrics that represent costs (need absolute value conversion).

    Story 6.23: Cost metrics are recorded as negative but need positive values for forecasting.
    """
    return {
        "electrical energy",
        "electricity",
        "electricity_cost",
        "thermal energy",
        "thermal",
        "thermal_cost",
        "fuel_cost",
        "variable cost",
        "variable_cost",
    }


def get_ebitda_metrics() -> set[str]:
    """Get EBITDA-related metrics.

    Story 6.25.1: EBITDA metrics need special YTD normalization handling.
    """
    return {"ebitda", "ebitda ifrs"}
