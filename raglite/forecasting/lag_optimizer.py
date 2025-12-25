"""Cross-correlation based lag optimization for external regressors.

Epic 7 Enhancement: Implements optimal lag selection based on research showing
that different regressors have different lead times:
- Energy prices (gas, coal): 1-5 period lags (fast reaction)
- Macro indicators (GDP, inflation): 3-6 month lags
- Housing/construction indicators: 6-12 month lags

Uses cross-correlation analysis and mutual information to find optimal lags.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class LagOptimizationResult:
    """Result of lag optimization for a single regressor."""

    regressor_name: str
    optimal_lag: int
    correlation_at_optimal: float
    all_correlations: dict[int, float] = field(default_factory=dict)


def optimize_regressor_lag(
    target: pd.Series,
    regressor: pd.Series,
    max_lag: int = 12,
    min_overlap: int = 10,
) -> LagOptimizationResult:
    """Find optimal lag for a regressor using cross-correlation.

    Computes Pearson correlation between target and lagged regressor for
    lags 1 to max_lag, selecting the lag with maximum absolute correlation.

    Args:
        target: Target time series to predict
        regressor: External regressor time series
        max_lag: Maximum lag to test (default: 12 periods)
        min_overlap: Minimum overlapping observations required (default: 10)

    Returns:
        LagOptimizationResult with optimal lag and correlation values

    Example:
        >>> result = optimize_regressor_lag(revenue_series, gdp_growth_series)
        >>> print(f"Optimal lag: {result.optimal_lag}, correlation: {result.correlation_at_optimal:.2f}")
    """
    correlations: dict[int, float] = {}

    # Normalize indices to month-start for alignment
    target_normalized = target.copy()
    target_normalized.index = target.index.to_period("M").to_timestamp()

    regressor_normalized = regressor.copy()
    regressor_normalized.index = regressor.index.to_period("M").to_timestamp()

    for lag in range(1, max_lag + 1):
        # Shift regressor by lag periods (lag=1 means use last month's value)
        lagged_reg = regressor_normalized.shift(lag)

        # Align with target
        aligned = pd.concat([target_normalized, lagged_reg], axis=1).dropna()

        if len(aligned) >= min_overlap:
            corr = aligned.corr().iloc[0, 1]
            if not np.isnan(corr):
                correlations[lag] = corr

    if correlations:
        # Select lag with maximum absolute correlation
        optimal_lag = max(correlations.keys(), key=lambda k: abs(correlations[k]))
        correlation_at_optimal = correlations[optimal_lag]
    else:
        # Default to lag 1 if no valid correlations found
        optimal_lag = 1
        correlation_at_optimal = 0.0
        logger.warning(
            f"No valid correlations found for regressor, defaulting to lag {optimal_lag}",
            extra={"max_lag": max_lag, "min_overlap": min_overlap},
        )

    return LagOptimizationResult(
        regressor_name=regressor.name if hasattr(regressor, "name") else "unknown",
        optimal_lag=optimal_lag,
        correlation_at_optimal=correlation_at_optimal,
        all_correlations=correlations,
    )


def optimize_all_regressors(
    target: pd.Series,
    regressors: dict[str, pd.Series],
    max_lag: int = 12,
    min_overlap: int = 10,
) -> dict[str, LagOptimizationResult]:
    """Optimize lags for all regressors in a dictionary.

    Args:
        target: Target time series to predict
        regressors: Dictionary mapping regressor names to time series
        max_lag: Maximum lag to test
        min_overlap: Minimum overlapping observations required

    Returns:
        Dictionary mapping regressor names to optimization results
    """
    results = {}

    for name, regressor in regressors.items():
        # Set name attribute for result tracking
        regressor_with_name = regressor.copy()
        regressor_with_name.name = name

        result = optimize_regressor_lag(
            target=target,
            regressor=regressor_with_name,
            max_lag=max_lag,
            min_overlap=min_overlap,
        )
        results[name] = result

        logger.info(
            f"Optimized lag for {name}: lag={result.optimal_lag}, corr={result.correlation_at_optimal:.3f}",
            extra={
                "regressor": name,
                "optimal_lag": result.optimal_lag,
                "correlation": result.correlation_at_optimal,
            },
        )

    return results


def apply_optimized_lags(
    regressors: dict[str, pd.Series],
    lag_results: dict[str, LagOptimizationResult],
) -> dict[str, pd.Series]:
    """Apply optimized lags to regressor series.

    Args:
        regressors: Original regressor series
        lag_results: Optimization results with optimal lags

    Returns:
        Dictionary of lagged regressor series
    """
    lagged_regressors = {}

    for name, series in regressors.items():
        if name in lag_results:
            optimal_lag = lag_results[name].optimal_lag
            lagged_regressors[name] = series.shift(optimal_lag)
        else:
            # Default to lag 1 if not optimized
            lagged_regressors[name] = series.shift(1)

    return lagged_regressors


# Default lag hints based on domain knowledge (fallback if optimization fails)
DEFAULT_LAG_HINTS: dict[str, int] = {
    # Energy prices: Fast reaction (1-3 periods)
    "ttf_gas": 1,
    "api2_coal": 1,
    "ren_electricity": 1,
    "diesel": 2,
    # Macro indicators: Medium lag (3-6 periods)
    "gdp_growth": 3,
    "inflation": 3,
    "euribor_3m": 2,
    # Construction/demand indicators: Long lag (6-12 periods)
    "construction_output": 3,
    "building_permits": 6,
    "construction_confidence": 3,
    "housing_transactions": 6,  # Leading indicator (6-12 month lag per Story 7b-7)
    "dwelling_completions": 3,
    "industrial_production": 2,
}


def get_default_lag(regressor_name: str) -> int:
    """Get default lag hint for a regressor based on domain knowledge.

    Args:
        regressor_name: Name of the regressor

    Returns:
        Default lag in periods (months for monthly data)
    """
    return DEFAULT_LAG_HINTS.get(regressor_name.lower(), 1)
