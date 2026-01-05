"""Setup and initialization helpers for forecast generation.

Story 8: Refactoring helpers - setup, cache, and deprecation handling.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from logging import Logger

    from raglite.shared.models import TimeSeriesData


def handle_deprecation_warning(historical_data: TimeSeriesData | None) -> None:
    """Emit deprecation warning for historical_data parameter.

    Story 6.3 AC8: Parameter deprecated, will be removed in Epic 7.
    """
    if historical_data is not None:
        warnings.warn(
            "historical_data parameter is deprecated, will be removed in Epic 7. "
            "Use metric parameter to fetch from PostgreSQL.",
            DeprecationWarning,
            stacklevel=3,  # Caller is 2 levels up from here
        )


def check_model_selection_cache(
    metric: str,
    use_model_selection: bool,
    get_cached_model_selection: Any,
    logger: Logger,
) -> tuple[str, str | None, str | None, list[str] | None]:
    """Check model selection cache and return selection info.

    Story 7b-6 AC-7b.6.1: Check model selection cache first.

    Args:
        metric: Metric name
        use_model_selection: Whether to use model selection cache
        get_cached_model_selection: Cache lookup function (or None if unavailable)
        logger: Logger instance

    Returns:
        Tuple of (model_source, model_selection_reason, selected_model, selected_regressors)
    """
    model_source = "default"
    model_selection_reason = None
    selected_model = None
    selected_regressors = None

    if use_model_selection and get_cached_model_selection is not None:
        try:
            cached = get_cached_model_selection(metric)
            if cached and not cached.is_expired:
                selected_model = cached.best_model
                selected_regressors = cached.regressor_list if cached.use_regressors else None
                model_source = "cached"
                # Get model rationale from data_characteristics if available
                if cached.data_characteristics:
                    model_selection_reason = cached.data_characteristics.get("model_rationale")
                logger.info(
                    f"Using cached model selection for {metric}",
                    extra={
                        "model": selected_model,
                        "source": model_source,
                        "use_regressors": cached.use_regressors,
                        "regressor_count": len(selected_regressors) if selected_regressors else 0,
                    },
                )
            else:
                cache_status = "miss" if not cached else "expired"
                logger.info(
                    f"No valid cache for {metric}, using default Prophet",
                    extra={"cache_status": cache_status},
                )
        except Exception as e:
            # Any error in cache lookup shouldn't break forecasting
            logger.warning(
                f"Error checking model selection cache for {metric}: {e}",
                extra={"error": str(e)},
            )

    return model_source, model_selection_reason, selected_model, selected_regressors


async def handle_initial_setup(
    metric: str,
    historical_data: TimeSeriesData | None,
    periods_ahead: int,
    external_regressors: dict[str, Any] | None,
    use_model_selection: bool,
    get_cached_model_selection: Any,
    ensure_historical_data_func: Any,
    logger: Logger,
    min_data_points: int,
) -> tuple[
    str,
    str | None,
    str | None,
    list[str] | None,
    TimeSeriesData | None,
    dict[str, Any] | None,
    bool,
]:
    """Handle deprecation, cache check, data loading, and cold-start detection.

    Story 8.1: Extracted from generate_forecast (Steps 1-2).

    Args:
        metric: Metric name
        historical_data: Time-series data (may be None)
        periods_ahead: Number of periods to forecast
        external_regressors: External regressors dict
        use_model_selection: Whether to use model selection cache
        get_cached_model_selection: Cache lookup function
        ensure_historical_data_func: Function to ensure data is loaded
        logger: Logger instance
        min_data_points: Minimum points required (for cold-start check)

    Returns:
        Tuple of (model_source, model_selection_reason, selected_model, selected_regressors,
                  historical_data, external_regressors, is_multivariate)

    Raises:
        May raise from ensure_historical_data_func if data cannot be loaded
    """
    # Handle deprecation warning
    handle_deprecation_warning(historical_data)

    # Check model selection cache
    model_source, model_selection_reason, selected_model, selected_regressors = (
        check_model_selection_cache(metric, use_model_selection, get_cached_model_selection, logger)
    )

    # Determine if multivariate
    is_multivariate = external_regressors is not None and len(external_regressors) > 0

    # Log start
    logger.info(
        "Generating forecast",
        extra={
            "metric": metric,
            "data_points": len(historical_data.points) if historical_data else 0,
            "periods": periods_ahead,
            "multivariate": is_multivariate,
            "selected_model": selected_model,
        },
    )

    # Ensure historical data is loaded
    historical_data = await ensure_historical_data_func(metric, historical_data, logger)

    return (
        model_source,
        model_selection_reason,
        selected_model,
        selected_regressors,
        historical_data,
        external_regressors,
        is_multivariate,
    )
