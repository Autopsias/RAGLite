"""Regressor configuration for multi-variate forecasting.

Story 6.11.1: MCP Multi-Variate Forecasting Interface
Story 6.11.2: Auto-Regressor Selection by Metric Type

This module provides configuration for external regressors used in multi-variate
forecasting, including:
- Per-metric regressor mappings
- Category-based auto-selection
- Default fallback configuration

Regressors are external economic indicators fetched from APIs:
- euribor_3m: 3-month EURIBOR rate (ECB)
- ttf_gas: TTF natural gas price (ICE Futures)
- api2_coal: API2 coal price (ICE Futures)
- diesel: Diesel price (EU Oil Bulletin)
- eurostat_electricity: Industrial electricity price (Eurostat)
"""

from __future__ import annotations

# =============================================================================
# Available Regressors
# =============================================================================

AVAILABLE_REGRESSORS: list[str] = [
    "euribor_3m",  # ECB EURIBOR 3-month rate
    "ttf_gas",  # ICE TTF natural gas futures
    "api2_coal",  # ICE API2 coal futures
    "diesel",  # EU Oil Bulletin diesel prices
    "eurostat_electricity",  # Eurostat industrial electricity prices
    # NOTE: The following are currently disabled due to API issues (Story 6.10.5):
    # "building_permits",  # INE building permits (wrong indicator)
    # "hpi",  # INE house price index
    # "construction_confidence",  # INE construction confidence
    # "omie_spot",  # OMIE spot electricity (too slow - 1000+ HTTP requests)
]


# =============================================================================
# Per-Metric Regressor Mappings
# =============================================================================

# Story 6.10.5: Updated to use only working external data sources
# - Removed INE-dependent regressors (building_permits, hpi, construction_confidence)
# - Using euribor_3m, diesel, ttf_gas as primary macro indicators
METRIC_REGRESSORS: dict[str, list[str]] = {
    # Financial metrics
    "revenue": ["euribor_3m", "diesel", "ttf_gas"],
    "turnover": ["euribor_3m", "diesel", "ttf_gas"],
    "turnover+vat": ["euribor_3m", "diesel", "ttf_gas"],
    "ebitda": ["euribor_3m", "ttf_gas", "diesel", "api2_coal"],
    "sales": ["euribor_3m", "diesel", "ttf_gas"],
    "sales_volume": ["euribor_3m", "diesel", "ttf_gas"],
    "sales volumes": ["euribor_3m", "diesel", "ttf_gas"],
    # Energy costs
    "electricity_cost": ["eurostat_electricity"],
    "electrical energy": ["eurostat_electricity"],
    "thermal_cost": ["api2_coal", "ttf_gas"],
    "thermal energy": ["api2_coal", "ttf_gas"],
    "variable_cost": ["ttf_gas", "diesel"],
    "variable cost": ["ttf_gas", "diesel"],
    # Pricing metrics
    "avg_selling_price": ["diesel", "euribor_3m", "ttf_gas"],
    "sales price em - cement": ["diesel", "euribor_3m", "ttf_gas"],
    "sales price im": ["diesel", "euribor_3m", "ttf_gas"],
    # Utilization metrics
    "capacity_utilization": ["euribor_3m", "diesel", "ttf_gas"],
    "frequency ratio": ["euribor_3m", "diesel", "ttf_gas"],
}


# =============================================================================
# Category-Based Regressor Selection
# =============================================================================

# Story 6.11.2: Auto-select regressors based on metric category
METRIC_CATEGORIES: dict[str, dict[str, list[str]]] = {
    "financial": {
        # Revenue, EBITDA, sales, costs
        "keywords": ["revenue", "turnover", "ebitda", "sales", "cost", "expense", "profit"],
        "regressors": ["euribor_3m", "diesel", "ttf_gas"],
    },
    "energy": {
        # Electricity, thermal costs, fuel
        "keywords": ["electricity", "thermal", "energy", "fuel", "power"],
        "regressors": ["eurostat_electricity", "ttf_gas", "api2_coal"],
    },
    "production": {
        # Volume, utilization, capacity
        "keywords": ["volume", "capacity", "utilization", "production", "output"],
        "regressors": ["euribor_3m", "diesel", "ttf_gas"],
    },
    "pricing": {
        # Selling prices
        "keywords": ["price", "selling", "asp", "unit price"],
        "regressors": ["diesel", "euribor_3m", "ttf_gas"],
    },
    "commodity": {
        # Commodity prices
        "keywords": ["coal", "gas", "petcoke", "co2", "carbon"],
        "regressors": ["ttf_gas", "api2_coal"],
    },
}

# Default regressors when no match is found
DEFAULT_REGRESSORS: list[str] = ["euribor_3m", "diesel", "ttf_gas"]


# =============================================================================
# Model Type Selection (Story 6.11.6)
# =============================================================================

# High-value financial metrics where ensemble provides most benefit
# These metrics are core to financial planning and justify longer execution time
HIGH_VALUE_METRICS: list[str] = [
    "revenue",
    "turnover",
    "turnover+vat",
    "ebitda",
    "profit",
    "cash_flow",
    "net_income",
]

# Metrics where Prophet performs well and ensemble adds minimal value
# Typically operational metrics with simpler patterns
PROPHET_PREFERRED_METRICS: list[str] = [
    "capacity_utilization",
    "frequency ratio",
    "volume",
    "production",
    "output",
]


def select_model_type(
    metric: str,
    prefer_accuracy: bool = False,
    num_regressors: int = 0,
    min_ensemble_regressors: int = 3,
) -> tuple[str, str]:
    """Intelligently select forecasting model based on context.

    Story 6.11.6: Intelligent model selection for MCP.

    Selection Logic:
    1. If prefer_accuracy=True AND sufficient regressors → ensemble
    2. If high-value financial metric AND prefer_accuracy=True → ensemble
    3. If insufficient regressors for ensemble → prophet
    4. Otherwise → prophet (faster, same accuracy for most metrics)

    The key insight from validation:
    - Prophet Multi-Variate: ~2.2% avg MAPE, ~21s per variable
    - Ensemble: ~78s per variable (3.7x slower), similar accuracy
    - Ensemble requires ≥3 regressors to run all 4 models (Prophet+Linear+XGBoost+LightGBM)

    Args:
        metric: Target metric name (e.g., "revenue", "ebitda")
        prefer_accuracy: User explicitly wants highest accuracy (accepts slower execution)
        num_regressors: Number of available external regressors
        min_ensemble_regressors: Minimum regressors needed for effective ensemble

    Returns:
        Tuple of (model_type, selection_reason)

    Example:
        >>> select_model_type("revenue", prefer_accuracy=True, num_regressors=4)
        ('ensemble', 'High-value financial metric with accuracy preference and 4 regressors available')
        >>> select_model_type("capacity_utilization", prefer_accuracy=False, num_regressors=3)
        ('prophet', 'Prophet preferred for operational metrics (faster with comparable accuracy)')
    """
    metric_lower = metric.lower().strip()

    # Check if metric is high-value financial metric
    is_high_value = any(hv in metric_lower for hv in HIGH_VALUE_METRICS)
    is_prophet_preferred = any(pp in metric_lower for pp in PROPHET_PREFERRED_METRICS)

    # Decision logic
    if prefer_accuracy and num_regressors >= min_ensemble_regressors:
        if is_high_value:
            return (
                "ensemble",
                f"High-value financial metric with accuracy preference and {num_regressors} regressors available",
            )
        else:
            return (
                "ensemble",
                f"Accuracy preference enabled with {num_regressors} regressors available",
            )

    if num_regressors < min_ensemble_regressors:
        return (
            "prophet",
            f"Insufficient regressors for ensemble ({num_regressors} < {min_ensemble_regressors} required)",
        )

    if is_prophet_preferred:
        return (
            "prophet",
            "Prophet preferred for operational metrics (faster with comparable accuracy)",
        )

    # Default: Prophet is faster with similar accuracy
    return ("prophet", "Prophet selected (faster execution ~21s vs ~78s with comparable accuracy)")


# =============================================================================
# Auto-Selection Functions
# =============================================================================


def get_default_regressors(metric: str) -> list[str]:
    """Auto-select regressors based on metric name.

    Story 6.11.2 AC1-AC4: Auto-selection with keyword matching and fallback.

    Selection priority:
    1. Explicit mapping in METRIC_REGRESSORS
    2. Category-based keyword matching
    3. Default economic indicators fallback

    Args:
        metric: Target metric name (e.g., "revenue", "ebitda", "electricity_cost")

    Returns:
        List of regressor names appropriate for the metric

    Example:
        >>> get_default_regressors("revenue")
        ['euribor_3m', 'diesel', 'ttf_gas']
        >>> get_default_regressors("electricity_cost")
        ['eurostat_electricity']
        >>> get_default_regressors("unknown_metric")
        ['euribor_3m', 'diesel', 'ttf_gas']
    """
    metric_lower = metric.lower().strip()

    # Priority 1: Check explicit mapping
    if metric_lower in METRIC_REGRESSORS:
        return METRIC_REGRESSORS[metric_lower]

    # Priority 2: Check category keywords
    for _category_name, config in METRIC_CATEGORIES.items():
        if any(kw in metric_lower for kw in config["keywords"]):
            return config["regressors"]

    # Priority 3: Default fallback
    return DEFAULT_REGRESSORS


def get_available_regressors() -> list[str]:
    """Return list of all available regressor names.

    Returns:
        List of regressor names that can be fetched from external APIs
    """
    return AVAILABLE_REGRESSORS.copy()


def validate_regressor_names(names: list[str]) -> tuple[list[str], list[str]]:
    """Validate regressor names against available regressors.

    Args:
        names: List of regressor names to validate

    Returns:
        Tuple of (valid_names, invalid_names)
    """
    valid = []
    invalid = []

    for name in names:
        if name.lower() in [r.lower() for r in AVAILABLE_REGRESSORS]:
            valid.append(name)
        else:
            invalid.append(name)

    return valid, invalid
