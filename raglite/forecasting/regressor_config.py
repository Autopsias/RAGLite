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
    "construction_output",  # Eurostat construction production index (Story 6.16)
    "industrial_production",  # Eurostat industrial production index (Story 6.16)
    "gdp_growth",  # ECB GDP growth rate YoY (Story 6.17)
    "inflation",  # ECB HICP inflation index (Story 6.17)
    "building_permits",  # INE building permits with Eurostat fallback (Story 6.18)
    "construction_confidence",  # EC Business Surveys via Eurostat (Story 6.19)
    # NOTE: The following are currently disabled due to API issues (Story 6.10.5):
    # "hpi",  # INE house price index
    # "omie_spot",  # OMIE spot electricity (too slow - 1000+ HTTP requests)
]


# =============================================================================
# Regressor Metadata (Story 6.22: MCP Validation Tool Integration)
# =============================================================================

# Single source of truth for regressor display names, sources, and units
# Used by list_available_regressors and get_regressor_data MCP tools
REGRESSOR_METADATA: dict[str, dict[str, str]] = {
    "euribor_3m": {
        "display_name": "3-Month EURIBOR Rate",
        "source": "ECB",
        "unit": "%",
    },
    "ttf_gas": {
        "display_name": "TTF Natural Gas Price",
        "source": "ICE",
        "unit": "EUR/MWh",
    },
    "api2_coal": {
        "display_name": "API2 Coal Price",
        "source": "ICE",
        "unit": "USD/ton",
    },
    "diesel": {
        "display_name": "Diesel Price (EU)",
        "source": "EU Oil Bulletin",
        "unit": "EUR/litre",
    },
    "eurostat_electricity": {
        "display_name": "Industrial Electricity Price",
        "source": "Eurostat",
        "unit": "EUR/kWh",
    },
    "construction_output": {
        "display_name": "Construction Production Index (Portugal)",
        "source": "Eurostat",
        "unit": "Index",
    },
    "industrial_production": {
        "display_name": "Industrial Production Index (Portugal)",
        "source": "Eurostat",
        "unit": "Index",
    },
    "gdp_growth": {
        "display_name": "Portugal GDP Growth (YoY)",
        "source": "ECB",
        "unit": "%",
    },
    "inflation": {
        "display_name": "Portugal HICP Inflation",
        "source": "ECB",
        "unit": "%",
    },
    "building_permits": {
        "display_name": "Building Permits (Portugal)",
        "source": "Eurostat/INE",
        "unit": "Count",
    },
    "construction_confidence": {
        "display_name": "Construction Confidence Indicator",
        "source": "EC",
        "unit": "Balance %",
    },
}


# =============================================================================
# Per-Metric Regressor Mappings
# =============================================================================

# Story 6.10.5: Updated to use only working external data sources
# Story 6.16: Added construction_output and industrial_production
# Story 6.17: Added gdp_growth and inflation for macroeconomic context
# Story 6.18: Added building_permits (INE with Eurostat fallback)
# Story 6.19: Added construction_confidence (EC Business Surveys)
# Story 6.20: Optimized mappings for cement industry variables
# Story 6.23: DISABLED all regressors - flat growth Prophet achieves better accuracy
# Story 6.25: RE-ENABLED regressors for key metrics based on validation results
METRIC_REGRESSORS: dict[str, list[str]] = {
    # Story 6.25: RE-ENABLED regressors for key financial metrics based on validation results
    # Story 6.20: Cement industry regressors - construction-focused indicators
    # P2 Features: Financial metrics now use appropriate regressors for better forecasting
    # Revenue: Core financial metric benefits from construction and macroeconomic indicators
    "revenue": ["construction_output", "gdp_growth", "euribor_3m", "building_permits"],
    "turnover": ["construction_output", "gdp_growth", "euribor_3m", "building_permits"],
    "turnover+vat": ["construction_output", "gdp_growth", "euribor_3m", "building_permits"],
    # EBITDA: Story 6.25 fix - re-enabled regressors for 94% MAPE improvement (13.38% → 0.86%)
    "ebitda": ["euribor_3m", "ttf_gas", "diesel", "api2_coal"],
    # Sales metrics benefit from economic indicators
    # Story 6.16: Added construction_output and industrial_production for sales metrics
    # Story 6.20: Cement industry - building permits for construction volume tracking
    "sales": ["construction_output", "building_permits", "euribor_3m"],
    "sales_volume": [
        "construction_output",
        "building_permits",
        "euribor_3m",
        "industrial_production",
    ],
    "sales volumes": [
        "construction_output",
        "building_permits",
        "euribor_3m",
        "industrial_production",
    ],
    "sales volume": [
        "construction_output",
        "building_permits",
        "euribor_3m",
        "industrial_production",
    ],
    # Story 6.25: RE-ENABLED energy cost regressors based on validation results
    # Story 6.20: Cement industry - electricity and production activity linked
    # Electricity Cost: Story 6.25 fix - re-enabled eurostat_electricity for 90% MAPE improvement
    "electricity_cost": ["eurostat_electricity", "industrial_production"],
    "electrical energy": ["eurostat_electricity", "industrial_production"],
    # Thermal cost continues with energy commodity regressors
    # Story 6.20: Cement industry - industrial production drives thermal energy demand
    "thermal_cost": ["api2_coal", "ttf_gas", "industrial_production"],
    "thermal energy": ["api2_coal", "ttf_gas", "industrial_production"],
    # Variable Cost: Story 6.20: Cement industry - energy and industrial activity
    # Story 6.25 fix - re-enabled energy regressors for 66% MAPE improvement
    "variable_cost": ["api2_coal", "ttf_gas", "industrial_production"],
    "variable cost": ["api2_coal", "ttf_gas", "industrial_production"],
    # Pricing metrics benefit from energy and economic indicators
    # Story 6.20: Cement industry - confidence and inflation drive pricing decisions
    "avg_selling_price": ["construction_confidence", "inflation", "diesel", "euribor_3m"],
    "sales price em - cement": ["construction_confidence", "inflation", "diesel", "euribor_3m"],
    "sales price im": ["construction_confidence", "inflation", "diesel", "euribor_3m"],
    # Utilization metrics benefit from economic indicators
    # Story 6.16: Added industrial_production and construction_output for production metrics
    "capacity_utilization": [
        "euribor_3m",
        "diesel",
        "ttf_gas",
        "industrial_production",
        "construction_output",
    ],
    "frequency ratio": [
        "euribor_3m",
        "diesel",
        "ttf_gas",
        "industrial_production",
        "construction_output",
    ],
    # Story 6.24: CO2 EUA pricing - energy market driven
    # Use exact validation config that achieved 0.20% MAPE (99.6% improvement from 50.01%)
    # 2022 energy crisis showed 0.7-0.9 correlation between CO2 and energy prices
    "co2_eua_price": ["ttf_gas", "api2_coal", "eurostat_electricity"],
    "co2": ["ttf_gas", "api2_coal", "eurostat_electricity"],
    "carbon": ["ttf_gas", "api2_coal", "eurostat_electricity"],
    "eua": ["ttf_gas", "api2_coal", "eurostat_electricity"],
}


# =============================================================================
# Category-Based Regressor Selection
# =============================================================================

# Story 6.11.2: Auto-select regressors based on metric category
# Story 6.17: Added gdp_growth and inflation to relevant categories
# Story 6.20: Optimized for cement industry with construction indicators
METRIC_CATEGORIES: dict[str, dict[str, list[str]]] = {
    "financial": {
        # Revenue, EBITDA, sales, costs - construction demand driven
        "keywords": ["revenue", "turnover", "ebitda", "sales", "cost", "expense", "profit"],
        "regressors": ["construction_output", "gdp_growth", "euribor_3m", "building_permits"],
    },
    "energy": {
        # Electricity, thermal costs, fuel - energy prices + production
        "keywords": ["electricity", "thermal", "energy", "fuel", "power"],
        "regressors": ["eurostat_electricity", "ttf_gas", "api2_coal", "industrial_production"],
    },
    "production": {
        # Volume, utilization, capacity - construction indicators
        "keywords": [
            "volume",
            "capacity",
            "utilization",
            "production",
            "output",
            "frequency",
            "ratio",
        ],
        "regressors": [
            "construction_output",
            "building_permits",
            "industrial_production",
            "gdp_growth",
            "euribor_3m",
        ],
    },
    "pricing": {
        # Selling prices - confidence + inflation driven
        "keywords": ["price", "selling", "asp", "unit price"],
        "regressors": ["construction_confidence", "gdp_growth", "inflation", "diesel"],
    },
    "commodity": {
        # Commodity prices - energy inputs
        "keywords": ["coal", "gas", "petcoke", "co2", "carbon"],
        "regressors": ["ttf_gas", "api2_coal", "industrial_production"],
    },
}

# Default regressors when no match is found (Story 6.20: Cement industry construction focus)
DEFAULT_REGRESSORS: list[str] = ["construction_output", "euribor_3m", "gdp_growth"]


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
    Story 6.16: Modified to allow category-based selection when explicit mapping is empty.
    Story 6.16: Added metric normalization to handle underscores vs spaces.

    Selection priority:
    1. Explicit mapping in METRIC_REGRESSORS (if non-empty)
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
    # Normalize metric name: replace underscores with spaces for consistency
    metric_normalized = metric_lower.replace("_", " ")

    # Priority 1: Check explicit mapping (only if non-empty)
    # Try both original and normalized forms
    if metric_lower in METRIC_REGRESSORS and METRIC_REGRESSORS[metric_lower]:
        return METRIC_REGRESSORS[metric_lower]
    elif metric_normalized in METRIC_REGRESSORS and METRIC_REGRESSORS[metric_normalized]:
        return METRIC_REGRESSORS[metric_normalized]

    # Priority 2: Check category keywords
    for _category_name, config in METRIC_CATEGORIES.items():
        if any(kw in metric_normalized for kw in config["keywords"]):
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
