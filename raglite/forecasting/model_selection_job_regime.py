"""
Regime detection functions for energy crisis period.

This module provides functions to add regime indicator features and check
if variables are affected by energy crisis regime changes.
"""

import logging

import pandas as pd

from raglite.forecasting.model_selection_job_config import (
    ENERGY_AFFECTED_VARIABLES,
    ENERGY_CRISIS_END,
    ENERGY_CRISIS_PEAK,
    ENERGY_CRISIS_START,
)

logger = logging.getLogger(__name__)


def add_regime_features(data: pd.DataFrame | pd.Series) -> pd.DataFrame:
    """Add regime indicator features for energy crisis period.

    Epic 7 Enhancement: Structural break handling based on Exa deep research.
    Energy markets experienced distinct regimes:
    - Pre-crisis: Stable prices (before Feb 2022)
    - Crisis: High volatility, extreme prices (Feb 2022 - Aug 2022)
    - Post-crisis: New normal with elevated but stable prices (after Jun 2023)

    Args:
        data: DataFrame or Series with DatetimeIndex

    Returns:
        DataFrame with added regime indicator columns
    """
    if isinstance(data, pd.Series):
        df = data.to_frame()
    else:
        df = data.copy()

    # Ensure index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        logger.warning("Data index is not DatetimeIndex, skipping regime features")
        return df

    # Add regime indicator columns
    df["regime_pre_crisis"] = (df.index < ENERGY_CRISIS_START).astype(int)
    df["regime_crisis"] = (
        (df.index >= ENERGY_CRISIS_START) & (df.index <= ENERGY_CRISIS_PEAK)
    ).astype(int)
    df["regime_post_peak"] = (
        (df.index > ENERGY_CRISIS_PEAK) & (df.index <= ENERGY_CRISIS_END)
    ).astype(int)
    df["regime_new_normal"] = (df.index > ENERGY_CRISIS_END).astype(int)

    return df


def is_energy_affected_variable(var_name: str) -> bool:
    """Check if a variable is affected by energy crisis regime changes.

    Args:
        var_name: Variable name to check

    Returns:
        True if the variable is in the energy-affected list
    """
    return var_name.lower() in [v.lower() for v in ENERGY_AFFECTED_VARIABLES]
