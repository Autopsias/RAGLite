"""Regressor configuration for multi-variate forecasting.

Story 6.11.1: MCP Multi-Variate Forecasting Interface
Story 6.11.2: Auto-Regressor Selection by Metric Type

This module provides configuration for external regressors used in multi-variate
forecasting, including:
- Per-metric regressor mappings
- Category-based auto-selection
- Default fallback configuration
- Model type selection logic

Regressors are external economic indicators fetched from APIs:
- euribor_3m: 3-month EURIBOR rate (ECB)
- ttf_gas: TTF natural gas price (ICE Futures)
- api2_coal: API2 coal price (ICE Futures)
- diesel: Diesel price (EU Oil Bulletin)
- eurostat_electricity: Industrial electricity price (Eurostat)
"""

from __future__ import annotations

from raglite.forecasting.regressor_config_data.metric_mappings import (
    DEFAULT_REGRESSORS,
    METRIC_CATEGORIES,
    METRIC_REGRESSORS,
)

# Import data-only modules (refactored for maintainability)
# These modules contain only data definitions, no imports from other forecasting modules
from raglite.forecasting.regressor_config_data.regressor_metadata import (
    AVAILABLE_REGRESSORS,
)

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
