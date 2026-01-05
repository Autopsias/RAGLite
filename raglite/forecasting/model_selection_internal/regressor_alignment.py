"""Regressor alignment utilities for model selection.

Private implementation details extracted to reduce main file size.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def _align_regressors(
    variable_name: str,
    historical_data: pd.Series,
    external_regressors: dict[str, pd.Series] | None,
) -> dict[str, pd.Series] | None:
    """Align external regressors to target index.

    Normalizes indices to month-start and reindexes to match target series.
    Drops regressors with insufficient overlap (<80% of target length).

    Args:
        variable_name: Name of the variable being forecasted
        historical_data: Target time series
        external_regressors: Dict of regressor name -> Series

    Returns:
        Aligned regressors dict, or None if no valid regressors
    """
    # Handle empty regressors dict as None
    if external_regressors is None or len(external_regressors) == 0:
        return None

    aligned_regressors: dict[str, pd.Series] = {}
    target_index = historical_data.index

    # BUG FIX: Normalize target index to month-start for consistent alignment
    normalized_target = target_index.to_period("M").to_timestamp()

    for reg_name, reg_series in external_regressors.items():
        # Normalize regressor index to month-start as well
        reg_normalized = reg_series.copy()
        reg_normalized.index = reg_series.index.to_period("M").to_timestamp()
        # Deduplicate if normalization created duplicates (take mean)
        reg_normalized = reg_normalized.groupby(reg_normalized.index).mean()

        # Reindex regressor to match normalized target dates, forward-fill gaps
        aligned = reg_normalized.reindex(normalized_target, method="ffill")

        # Map back to original target index for CV slicing
        aligned.index = target_index

        # Only keep if we have enough non-null values
        if aligned.notna().sum() >= len(target_index) * 0.8:
            aligned_regressors[reg_name] = aligned
        else:
            logger.warning(
                f"Regressor {reg_name} dropped: insufficient overlap with target index "
                f"({aligned.notna().sum()}/{len(target_index)} values)"
            )

    if not aligned_regressors:
        logger.warning("No regressors survived alignment - testing without regressors")
        return None

    logger.info(
        f"Aligned {len(aligned_regressors)} regressors to target index",
        extra={"regressors": list(aligned_regressors.keys())},
    )

    return aligned_regressors
