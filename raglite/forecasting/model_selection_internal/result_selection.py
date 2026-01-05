"""Result selection and CV orchestration for model selection.

Private implementation details extracted to reduce main file size.
"""

import logging

import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from raglite.forecasting.data_analyzer import DataCharacteristics

from . import cross_validation

logger = logging.getLogger(__name__)


async def _run_cv_comparison(
    variable_name: str,
    historical_data: pd.Series,
    models_to_test: list[str],
    aligned_regressors: dict[str, pd.Series] | None,
    tscv: TimeSeriesSplit,
    use_recency_weights: bool,
) -> dict:
    """Run cross-validation for all model configurations.

    Tests each model with and without regressors, collecting MAPE/MASE metrics.

    Args:
        variable_name: Name of the variable being forecasted
        historical_data: Target time series
        models_to_test: List of model names to test
        aligned_regressors: Aligned external regressors (or None)
        tscv: TimeSeriesSplit object
        use_recency_weights: Whether to weight recent folds higher

    Returns:
        Dict mapping config_key to metrics dict
    """
    results = {}

    if use_recency_weights:
        logger.info(
            f"Using recency-weighted CV for volatile variable {variable_name}",
            extra={"cv": "recency weights enabled"},
        )

    for model_name in models_to_test:
        # Test without regressors
        config_key_no_regs = f"{model_name}_False"
        try:
            cv_metrics = await cross_validation._cv_evaluate(
                model_name, historical_data, None, tscv, use_recency_weights
            )
            results[config_key_no_regs] = {
                **cv_metrics,
                "with_regressors": False,
                "regressor_set": [],
            }
            logger.info(
                f"Model {config_key_no_regs} CV complete",
                extra={
                    "variable": variable_name,
                    "mape": cv_metrics["mape"],
                    "mase": cv_metrics["mase"],
                },
            )
        except Exception as e:
            logger.warning(
                f"Model {model_name} (no regressors) failed for {variable_name}: {e}",
                extra={"model": model_name, "error": str(e)},
            )
            results[config_key_no_regs] = {
                "error": str(e),
                "mape": float("inf"),
                "mase": float("inf"),
            }

        # Test with regressors if provided (skip chronos, ets - they don't support regressors)
        if aligned_regressors and model_name not in ("chronos", "ets"):
            config_key_with_regs = f"{model_name}_True"
            try:
                cv_metrics = await cross_validation._cv_evaluate(
                    model_name, historical_data, aligned_regressors, tscv, use_recency_weights
                )
                results[config_key_with_regs] = {
                    **cv_metrics,
                    "with_regressors": True,
                    "regressor_set": list(aligned_regressors.keys()),
                }
                logger.info(
                    f"Model {config_key_with_regs} CV complete",
                    extra={
                        "variable": variable_name,
                        "mape": cv_metrics["mape"],
                        "mase": cv_metrics["mase"],
                    },
                )
            except Exception as e:
                logger.warning(
                    f"Model {model_name} (with regressors) failed for {variable_name}: {e}",
                    extra={"model": model_name, "error": str(e)},
                )
                results[config_key_with_regs] = {
                    "error": str(e),
                    "mape": float("inf"),
                    "mase": float("inf"),
                }

    return results


def _select_best_from_results(
    variable_name: str,
    results: dict,
    data_chars: DataCharacteristics,
) -> tuple:
    """Select best model from CV results.

    Args:
        variable_name: Name of the variable being forecasted
        results: Dict of config_key -> metrics
        data_chars: Analyzed data characteristics

    Returns:
        Tuple of (best_model_name, best_result_dict)

    Raises:
        ModelSelectionError: If all models failed
    """
    from raglite.forecasting.model_selection import ModelSelectionError

    # Ensure at least one model succeeded
    valid_results = {k: v for k, v in results.items() if "error" not in v}
    if not valid_results:
        raise ModelSelectionError(
            f"All models failed for variable {variable_name}. Errors: {results}"
        )

    # Select best by MASE (primary), then MAPE (secondary)
    best_key = min(
        valid_results.keys(), key=lambda k: (valid_results[k]["mase"], valid_results[k]["mape"])
    )
    best_result = valid_results[best_key]
    best_model_name = best_key.rsplit("_", 1)[0]

    # Epic 7 Enhancement: MASE >= 1.0 Fallback Rule (Hyndman 2006 best practice)
    if best_result["mase"] >= 1.0:
        logger.warning(
            f"Best model {best_model_name} has MASE >= 1.0 ({best_result['mase']:.2f}), "
            "attempting fallback to simpler models (Hyndman 2006 best practice)",
            extra={"variable": variable_name, "mase": best_result["mase"]},
        )

        # Try fallback models in order of typical stability
        fallback_models = ["ets", "arima", "linear", "prophet"]
        for fallback in fallback_models:
            fallback_key = f"{fallback}_False"
            if fallback_key in valid_results:
                fallback_result = valid_results[fallback_key]
                if fallback_result["mase"] < 1.0:
                    logger.info(
                        f"Fallback successful: {fallback} has MASE {fallback_result['mase']:.2f} < 1.0",
                        extra={
                            "variable": variable_name,
                            "original_model": best_model_name,
                            "fallback_model": fallback,
                        },
                    )
                    best_model_name = fallback
                    best_result = fallback_result
                    break

        # If still >= 1.0, log warning but keep the best available
        if best_result["mase"] >= 1.0:
            logger.warning(
                f"No fallback model achieved MASE < 1.0 for {variable_name}. "
                f"Keeping {best_model_name} with MASE {best_result['mase']:.2f}. "
                "Consider using naive forecast for this variable.",
                extra={"variable": variable_name, "mase": best_result["mase"]},
            )

    return best_model_name, best_result
