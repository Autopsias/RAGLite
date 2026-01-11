"""Composite Variable Forecasting via Decomposition.

Epic 7 Enhancement: Implements decomposition-based forecasting for composite metrics.

Research shows that composite metrics like EBITDA are better forecasted by
decomposing into components, forecasting each separately, and aggregating:
- EBITDA = Revenue - Costs (separates demand-side from cost-side volatility)
- Variable Cost = Energy + Materials + Logistics
- Thermal Energy = Gas + Coal + Electricity costs

This approach:
1. Isolates independent volatility sources
2. Allows component-specific regressors
3. Reduces forecast error through component specialization
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CompositeDefinition:
    """Definition of a composite variable and its components."""

    name: str
    components: list[str]
    aggregation: str  # "sum", "difference", "weighted_sum"
    weights: list[float] = field(default_factory=list)
    description: str = ""


# Epic 7: Composite variable definitions
# These define how composite metrics can be decomposed for better forecasting
COMPOSITE_DEFINITIONS: dict[str, CompositeDefinition] = {
    "ebitda": CompositeDefinition(
        name="ebitda",
        components=["revenue", "operating_costs"],
        aggregation="difference",
        description="EBITDA = Revenue - Operating Costs",
    ),
    "variable_cost": CompositeDefinition(
        name="variable_cost",
        components=["energy_cost", "materials_cost"],
        aggregation="sum",
        description="Variable Cost = Energy + Materials",
    ),
    "thermal_cost": CompositeDefinition(
        name="thermal_cost",
        components=["gas_cost", "coal_cost", "electricity_cost"],
        aggregation="sum",
        description="Thermal Energy = Gas + Coal + Electricity",
    ),
}


@dataclass
class CompositeResult:
    """Result of composite forecast."""

    variable_name: str
    composite_forecast: pd.Series
    component_forecasts: dict[str, pd.Series]
    aggregation_method: str
    components_used: list[str]
    fallback_used: bool = False
    fallback_reason: str = ""


def is_composite_variable(variable_name: str) -> bool:
    """Check if a variable is defined as a composite.

    Args:
        variable_name: Name of the variable to check

    Returns:
        True if the variable has a composite definition
    """
    return variable_name.lower() in COMPOSITE_DEFINITIONS


def get_composite_definition(variable_name: str) -> CompositeDefinition | None:
    """Get composite definition for a variable.

    Args:
        variable_name: Name of the variable

    Returns:
        CompositeDefinition if variable is composite, None otherwise
    """
    return COMPOSITE_DEFINITIONS.get(variable_name.lower())


async def forecast_composite(
    variable_name: str,
    component_data: dict[str, pd.Series],
    forecast_horizon: int,
    forecast_function: Any,
    **forecast_kwargs: Any,
) -> CompositeResult:
    """Forecast a composite variable by forecasting its components.

    This function:
    1. Looks up the composite definition
    2. Forecasts each component independently
    3. Aggregates component forecasts using the defined aggregation method

    Args:
        variable_name: Name of the composite variable (e.g., "ebitda")
        component_data: Dictionary mapping component names to historical data
        forecast_horizon: Number of periods to forecast
        forecast_function: Async function to use for forecasting each component
            Should have signature: async def(variable_name, data, horizon, **kwargs)
        **forecast_kwargs: Additional kwargs passed to forecast_function

    Returns:
        CompositeResult with aggregated and component forecasts

    Example:
        >>> result = await forecast_composite(
        ...     "ebitda",
        ...     {"revenue": revenue_series, "operating_costs": cost_series},
        ...     forecast_horizon=12,
        ...     forecast_function=my_forecast_func,
        ... )
        >>> print(result.composite_forecast)
    """
    definition = get_composite_definition(variable_name)

    if definition is None:
        raise ValueError(f"No composite definition found for {variable_name}")

    # Validate component data and check for missing components
    missing = _validate_component_data(definition, component_data, variable_name)
    if missing:
        return _create_missing_components_fallback(variable_name, definition, missing)

    # Forecast each component
    component_forecasts, failed_component = await _forecast_components(
        definition,
        component_data,
        variable_name,
        forecast_horizon,
        forecast_function,
        **forecast_kwargs,
    )

    if failed_component:
        return _create_component_failed_fallback(
            variable_name, definition, component_forecasts, failed_component
        )

    # Aggregate component forecasts
    composite_forecast = _aggregate_forecasts(
        component_forecasts,
        definition.aggregation,
        definition.weights,
    )

    logger.info(
        f"Composite forecast complete for {variable_name}",
        extra={
            "variable": variable_name,
            "components": list(component_forecasts.keys()),
            "aggregation": definition.aggregation,
        },
    )

    return CompositeResult(
        variable_name=variable_name,
        composite_forecast=composite_forecast,
        component_forecasts=component_forecasts,
        aggregation_method=definition.aggregation,
        components_used=list(component_forecasts.keys()),
        fallback_used=False,
    )


def _validate_component_data(
    definition: CompositeDefinition,
    component_data: dict[str, pd.Series],
    variable_name: str,
) -> set[str] | None:
    """Validate that all required components are present.

    Args:
        definition: Composite definition with required components
        component_data: Available component data
        variable_name: Name of composite variable (for logging)

    Returns:
        Set of missing component names, or None if all present
    """
    available_components = set(component_data.keys())
    required_components = set(definition.components)
    missing = required_components - available_components

    if missing:
        logger.warning(
            f"Missing components for {variable_name}: {missing}. Falling back to direct forecast.",
            extra={"variable": variable_name, "missing": list(missing)},
        )
        return missing

    return None


def _create_missing_components_fallback(
    variable_name: str,
    definition: CompositeDefinition,
    missing: set[str],
) -> CompositeResult:
    """Create a fallback result when components are missing.

    Args:
        variable_name: Name of composite variable
        definition: Composite definition
        missing: Set of missing component names

    Returns:
        CompositeResult with fallback flag set
    """
    return CompositeResult(
        variable_name=variable_name,
        composite_forecast=pd.Series(dtype=float),
        component_forecasts={},
        aggregation_method=definition.aggregation,
        components_used=[],
        fallback_used=True,
        fallback_reason=f"Missing components: {missing}",
    )


async def _forecast_components(
    definition: CompositeDefinition,
    component_data: dict[str, pd.Series],
    variable_name: str,
    forecast_horizon: int,
    forecast_function: Any,
    **forecast_kwargs: Any,
) -> tuple[dict[str, pd.Series], str | None]:
    """Forecast each component independently.

    Args:
        definition: Composite definition with component list
        component_data: Available component data
        variable_name: Name of composite variable (for logging)
        forecast_horizon: Number of periods to forecast
        forecast_function: Async forecast function to use
        **forecast_kwargs: Additional kwargs for forecast function

    Returns:
        Tuple of (component_forecasts dict, failed_component_name or None)
    """
    component_forecasts: dict[str, pd.Series] = {}

    for component_name in definition.components:
        if component_name in component_data:
            try:
                logger.info(
                    f"Forecasting component {component_name} for composite {variable_name}",
                    extra={"component": component_name, "horizon": forecast_horizon},
                )
                forecast = await forecast_function(
                    component_name,
                    component_data[component_name],
                    forecast_horizon,
                    **forecast_kwargs,
                )
                component_forecasts[component_name] = forecast
            except Exception as e:
                logger.error(
                    f"Failed to forecast component {component_name}: {e}",
                    extra={"component": component_name, "error": str(e)},
                )
                # Return partial results and the failed component name
                return component_forecasts, component_name

    return component_forecasts, None


def _create_component_failed_fallback(
    variable_name: str,
    definition: CompositeDefinition,
    component_forecasts: dict[str, pd.Series],
    failed_component: str,
) -> CompositeResult:
    """Create a fallback result when component forecasting fails.

    Args:
        variable_name: Name of composite variable
        definition: Composite definition
        component_forecasts: Partial component forecasts before failure
        failed_component: Name of component that failed

    Returns:
        CompositeResult with fallback flag set
    """
    return CompositeResult(
        variable_name=variable_name,
        composite_forecast=pd.Series(dtype=float),
        component_forecasts=component_forecasts,
        aggregation_method=definition.aggregation,
        components_used=list(component_forecasts.keys()),
        fallback_used=True,
        fallback_reason=f"Component forecast failed: {failed_component}",
    )


def _aggregate_forecasts(
    component_forecasts: dict[str, pd.Series],
    aggregation: str,
    weights: list[float],
) -> pd.Series:
    """Aggregate component forecasts using the specified method.

    Args:
        component_forecasts: Dictionary of component name -> forecast series
        aggregation: Aggregation method ("sum", "difference", "weighted_sum")
        weights: Weights for weighted_sum aggregation

    Returns:
        Aggregated forecast series
    """
    if not component_forecasts:
        return pd.Series(dtype=float)

    # Get forecast arrays aligned by index
    components = list(component_forecasts.values())

    # Ensure all have same index
    first_index = components[0].index
    aligned_components = [c.reindex(first_index) for c in components]

    if aggregation == "sum":
        # Simple sum of all components
        result = sum(aligned_components)
        return result

    elif aggregation == "difference":
        # First component minus all others
        # For EBITDA: revenue - costs
        if len(aligned_components) < 2:
            return aligned_components[0]
        result = aligned_components[0] - sum(aligned_components[1:])
        return result

    elif aggregation == "weighted_sum":
        # Weighted sum using provided weights
        if not weights or len(weights) != len(aligned_components):
            logger.warning("Invalid weights for weighted_sum, using equal weights")
            weights = [1.0 / len(aligned_components)] * len(aligned_components)
        result = sum(w * c for w, c in zip(weights, aligned_components, strict=False))
        return result

    else:
        raise ValueError(f"Unknown aggregation method: {aggregation}")


def derive_ebitda_from_components(
    revenue_forecast: pd.Series,
    cost_forecast: pd.Series,
) -> pd.Series:
    """Simple EBITDA derivation from Revenue and Costs.

    Epic 7: Direct utility function for EBITDA decomposition.

    Args:
        revenue_forecast: Forecasted revenue series
        cost_forecast: Forecasted operating costs series

    Returns:
        Derived EBITDA forecast (Revenue - Costs)
    """
    # Align indices
    common_index = revenue_forecast.index.intersection(cost_forecast.index)

    if len(common_index) == 0:
        logger.warning("No overlapping dates for EBITDA derivation")
        return pd.Series(dtype=float)

    revenue_aligned = revenue_forecast.reindex(common_index)
    cost_aligned = cost_forecast.reindex(common_index)

    ebitda = revenue_aligned - cost_aligned

    logger.info(
        "Derived EBITDA from components",
        extra={
            "periods": len(ebitda),
            "avg_revenue": revenue_aligned.mean(),
            "avg_cost": cost_aligned.mean(),
            "avg_ebitda": ebitda.mean(),
        },
    )

    return ebitda


def validate_composite_forecast(
    composite_result: CompositeResult,
    historical_composite: pd.Series | None = None,
) -> dict[str, Any]:
    """Validate composite forecast results.

    Args:
        composite_result: Result from forecast_composite
        historical_composite: Optional historical data for validation

    Returns:
        Dictionary with validation metrics
    """
    validation = {
        "variable": composite_result.variable_name,
        "fallback_used": composite_result.fallback_used,
        "components_count": len(composite_result.components_used),
        "aggregation": composite_result.aggregation_method,
    }

    if composite_result.fallback_used:
        validation["fallback_reason"] = composite_result.fallback_reason
        validation["valid"] = False
        return validation

    # Check for reasonable forecast values
    forecast = composite_result.composite_forecast

    if len(forecast) == 0:
        validation["valid"] = False
        validation["error"] = "Empty forecast"
        return validation

    # Check for NaN values
    nan_count = forecast.isna().sum()
    if nan_count > 0:
        validation["nan_count"] = int(nan_count)
        validation["nan_ratio"] = float(nan_count / len(forecast))

    # Check for reasonable range if historical data provided
    if historical_composite is not None and len(historical_composite) > 0:
        hist_mean = historical_composite.mean()
        hist_std = historical_composite.std()
        forecast_mean = forecast.mean()

        # Check if forecast mean is within 3 std of historical mean
        if abs(forecast_mean - hist_mean) > 3 * hist_std:
            validation["warning"] = "Forecast mean significantly different from historical"
            validation["forecast_mean"] = float(forecast_mean)
            validation["historical_mean"] = float(hist_mean)

    validation["valid"] = True
    return validation
