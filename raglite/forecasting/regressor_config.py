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
    # Cost-side regressors (energy, financing)
    "euribor_3m",  # ECB EURIBOR 3-month rate
    "ttf_gas",  # ICE TTF natural gas futures
    "api2_coal",  # ICE API2 coal futures
    "diesel",  # EU Oil Bulletin diesel prices
    "eurostat_electricity",  # Eurostat industrial electricity prices
    "ren_electricity",  # REN Data Hub Portuguese spot electricity (Story 7.0)
    # Economic indicators
    "gdp_growth",  # ECB GDP growth rate YoY (Story 6.17)
    "inflation",  # ECB HICP inflation index (Story 6.17)
    # Demand-side regressors (construction activity) - Story 7b-7
    "construction_output",  # Eurostat construction production index (Story 6.16)
    "industrial_production",  # Eurostat industrial production index (Story 6.16)
    "building_permits",  # INE building permits with Eurostat fallback (Story 6.18)
    "construction_confidence",  # EC Business Surveys via Eurostat (Story 6.19)
    "housing_transactions",  # Eurostat prc_hpi_inx quarterly->monthly (Story 7b-7)
    "dwelling_completions",  # Eurostat sts_cobp_m monthly (Story 7b-7)
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
    "ren_electricity": {
        "display_name": "Portuguese Electricity Spot Price",
        "source": "REN",
        "unit": "EUR/MWh",
    },
    # Story 7b-7: Demand-side regressors
    "housing_transactions": {
        "display_name": "Housing Transactions (Portugal)",
        "source": "Eurostat",
        "unit": "Count (quarterly, interpolated to monthly)",
    },
    "dwelling_completions": {
        "display_name": "Dwelling Completions (Portugal)",
        "source": "Eurostat",
        "unit": "Count (monthly)",
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
    # Story 7b-7: Added housing_transactions as demand-side regressor
    "revenue": [
        "construction_output",
        "building_permits",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "gdp_growth",
        "euribor_3m",  # Financial regressor for cost of capital
    ],
    "turnover": [
        "construction_output",
        "building_permits",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "gdp_growth",
    ],
    "turnover+vat": [
        "construction_output",
        "building_permits",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "gdp_growth",
    ],
    # EBITDA: Story 7b-7 fix - Added demand-side regressors for construction revenue
    # Portugal = 72% of Secil EBITDA, so construction demand is critical
    # EBITDA = Revenue - Costs: demand (revenue driver) and cost inputs
    # NOTE: euribor_3m removed per Story 7b-7 AC5 - less relevant to cement EBITDA
    # Epic 7 Enhancement: Added sales_volume and capacity_utilization per McKinsey research
    # EBITDA forecasting benefits from demand-linked regressors (inventory, utilization)
    "ebitda": [
        # Demand-side (construction activity -> revenue)
        "construction_output",
        "building_permits",
        "construction_confidence",
        "housing_transactions",  # Story 7b-7: Leading indicator (6-12 month lag)
        "sales_volume",  # Epic 7: Direct demand indicator for Portugal operations
        # Cost-side (energy costs -> margins)
        "ttf_gas",
        "diesel",
        "capacity_utilization",  # Epic 7: Efficiency factor affecting margins
    ],
    # Sales metrics benefit from economic indicators
    # Story 6.16: Added construction_output and industrial_production for sales metrics
    # Story 6.20: Cement industry - building permits for construction volume tracking
    "sales": ["construction_output", "building_permits", "euribor_3m"],
    # Forecasting Quality Enhancement: Added construction_confidence for market sentiment
    # Story 7b-7: Pure demand-side regressors for sales volume (removed euribor_3m)
    "sales_volume": [
        "construction_output",
        "building_permits",
        "construction_confidence",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "dwelling_completions",  # Story 7b-7: Lagging demand indicator
    ],
    "sales volumes": [
        "construction_output",
        "building_permits",
        "construction_confidence",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "dwelling_completions",  # Story 7b-7: Lagging demand indicator
    ],
    "sales volume": [
        "construction_output",
        "building_permits",
        "construction_confidence",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "dwelling_completions",  # Story 7b-7: Lagging demand indicator
    ],
    # Story 7.0: REN electricity replaces eurostat_electricity (9 points → 60+ monthly)
    # Story 6.25: RE-ENABLED energy cost regressors based on validation results
    # Story 6.20: Cement industry - electricity and production activity linked
    "electricity_cost": ["ren_electricity", "ttf_gas"],  # Story 7.0: REN spot prices with gas proxy
    "electrical energy": ["ren_electricity", "ttf_gas"],
    # Thermal cost continues with energy commodity regressors
    # Story 6.20: Cement industry - industrial production drives thermal energy demand
    "thermal_cost": ["api2_coal", "ttf_gas", "industrial_production"],
    "thermal energy": ["api2_coal", "ttf_gas", "industrial_production"],
    # Variable Cost: Story 6.20: Cement industry - energy and industrial activity
    # Story 6.25 fix - re-enabled energy regressors for 66% MAPE improvement
    # Epic 7 Enhancement: Multi-factor approach per manufacturing research
    # Variable costs depend on: raw materials, labor, energy, logistics
    "variable_cost": [
        "api2_coal",
        "ttf_gas",
        "industrial_production",
        "sales_volume",  # Epic 7: Volume affects unit cost (economies of scale)
        "diesel",  # Epic 7: Logistics/transport costs
        "capacity_utilization",  # Epic 7: Efficiency factor
    ],
    "variable cost": [
        "api2_coal",
        "ttf_gas",
        "industrial_production",
        "sales_volume",  # Epic 7: Volume affects unit cost (economies of scale)
        "diesel",  # Epic 7: Logistics/transport costs
        "capacity_utilization",  # Epic 7: Efficiency factor
    ],
    # Pricing metrics benefit from energy and economic indicators
    # Story 6.20: Cement industry - confidence and inflation drive pricing decisions
    # Story 7b-7: Added housing_transactions as demand-side regressor for pricing
    "avg_selling_price": [
        "construction_confidence",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "building_permits",
        "inflation",
    ],
    "sales price em - cement": [
        "construction_confidence",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "building_permits",
        "inflation",
    ],
    "sales price im": [
        "construction_confidence",
        "housing_transactions",  # Story 7b-7: Demand-side regressor
        "building_permits",
        "inflation",
    ],
    # Utilization metrics benefit from economic indicators
    # Story 6.16: Added industrial_production and construction_output for production metrics
    # Story 7b-7: Added demand-side regressors for capacity utilization
    "capacity_utilization": [
        "construction_output",
        "building_permits",
        "construction_confidence",
        "industrial_production",
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
        # Story 7b-7: Added housing_transactions as demand-side regressor
        "keywords": ["revenue", "turnover", "ebitda", "sales", "cost", "expense", "profit"],
        "regressors": [
            "construction_output",
            "building_permits",
            "housing_transactions",  # Story 7b-7
            "gdp_growth",
            "euribor_3m",  # Financial regressor for cost of capital
        ],
    },
    "energy": {
        # Electricity, thermal costs, fuel - energy prices + production
        # Story 7.0: Use ren_electricity (60+ points) instead of eurostat_electricity (9 points)
        "keywords": ["electricity", "thermal", "energy", "fuel", "power"],
        "regressors": ["ren_electricity", "ttf_gas", "api2_coal", "industrial_production"],
    },
    "production": {
        # Volume, utilization, capacity - construction indicators
        # Story 7b-7: Added housing_transactions as demand-side regressor
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
            "construction_confidence",
            "housing_transactions",  # Story 7b-7
            "industrial_production",
            "euribor_3m",  # Financial regressor for financing-driven demand
        ],
    },
    "pricing": {
        # Selling prices - confidence + inflation driven
        # Story 7b-7: Added housing_transactions as demand-side regressor
        "keywords": ["price", "selling", "asp", "unit price"],
        "regressors": [
            "construction_confidence",
            "housing_transactions",  # Story 7b-7
            "building_permits",
            "inflation",
        ],
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
    Story 7b-3: Fixed data leakage by excluding self-referencing regressors.

    Selection priority:
    1. Explicit mapping in METRIC_REGRESSORS (if non-empty)
    2. Category-based keyword matching
    3. Default economic indicators fallback

    CRITICAL: The returned list excludes the metric itself to prevent data leakage
    during cross-validation (using future values of the target to predict itself).

    Args:
        metric: Target metric name (e.g., "revenue", "ebitda", "electricity_cost")

    Returns:
        List of regressor names appropriate for the metric (excluding self)

    Example:
        >>> get_default_regressors("revenue")
        ['euribor_3m', 'diesel', 'ttf_gas']
        >>> get_default_regressors("electricity_cost")
        ['eurostat_electricity']
        >>> get_default_regressors("api2_coal")  # Self excluded
        ['ttf_gas', 'industrial_production']
    """
    metric_lower = metric.lower().strip()
    # Normalize metric name: replace underscores with spaces for consistency
    metric_normalized = metric_lower.replace("_", " ")

    regressors: list[str] = []

    # Priority 1: Check explicit mapping (only if non-empty)
    # Try both original and normalized forms
    if metric_lower in METRIC_REGRESSORS and METRIC_REGRESSORS[metric_lower]:
        regressors = METRIC_REGRESSORS[metric_lower].copy()
    elif metric_normalized in METRIC_REGRESSORS and METRIC_REGRESSORS[metric_normalized]:
        regressors = METRIC_REGRESSORS[metric_normalized].copy()
    else:
        # Priority 2: Check category keywords
        found_category = False
        for _category_name, config in METRIC_CATEGORIES.items():
            if any(kw in metric_normalized for kw in config["keywords"]):
                regressors = config["regressors"].copy()
                found_category = True
                break

        # Priority 3: Default fallback
        if not found_category:
            regressors = DEFAULT_REGRESSORS.copy()

    # Story 7b-3 FIX: Exclude self-referencing regressors to prevent data leakage
    # A variable cannot use itself as a regressor (would allow future values to predict itself)
    regressors = [r for r in regressors if r.lower() != metric_lower]

    return regressors


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
