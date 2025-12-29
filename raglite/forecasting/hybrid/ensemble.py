"""Hybrid forecasting - Ensemble forecast generation and explanation.

Part of Story 8.1 refactoring to split hybrid.py.

Provides:
- generate_forecast: Main hybrid forecasting entry point combining Prophet + LLM reasoning
- explain_forecast: LLM-powered confidence reasoning
- calculate_accuracy: Cross-validation metrics calculation
"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from prophet import Prophet

from raglite.forecasting.hybrid.lazy_imports import _get_prophet_class
from raglite.forecasting.hybrid.model_generators import _route_to_model
from raglite.forecasting.hybrid.preprocessing import (
    _generate_future_regressors,
    ensure_historical_data,
    prepare_regressors,
    select_regressors,
    validate_timeseries_for_forecast,
)
from raglite.forecasting.models.base import MIN_DATA_POINTS
from raglite.forecasting.models.chronos_model import (
    generate_chronos_cold_start_forecast,
)
from raglite.shared.clients import get_mistral_client
from raglite.shared.logging import get_logger
from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesData

# Module-level constants
logger = get_logger(__name__)
MIN_CV_DATA_POINTS = 12  # Minimum points for cross-validation
POSITIVE_ONLY_METRICS = {"ebitda", "revenue", "capacity_utilization", "sales_volume"}

# Story 7b-6: Model selection cache integration
try:
    from raglite.external_data.storage import get_cached_model_selection
except ImportError:
    # Storage module may not be available in some test scenarios
    get_cached_model_selection = None  # type: ignore


async def generate_forecast(
    metric: str,
    historical_data: TimeSeriesData | None = None,
    periods_ahead: int = 4,
    external_regressors: dict[str, pd.Series] | None = None,
    frequency: str = "M",
    future_regressor_strategy: str = "constant",
    use_model_selection: bool = True,
) -> ForecastResult:
    """Generate forecast for financial metric using Prophet + LLM.

    Story 4.2 AC1-AC4: Hybrid forecasting with Prophet statistical model
    and Mistral Large for confidence reasoning.

    Story 6.3: Extended with multi-variate forecasting support.
    Story 7b-6: Integrated with model selection cache for automatic optimal model routing.

    Args:
        metric: Metric name (e.g., "revenue", "cash_flow", "expenses")
        historical_data: Time-series data from Story 4.1 extraction.
            DEPRECATED in Story 6.3 - use fetch_historical_metric() instead.
        periods_ahead: Number of periods to forecast (default 4 quarters)
        external_regressors: Optional dict of external regressor series for
            multi-variate forecasting (Story 6.3)
        frequency: Data frequency - 'M' (monthly), 'Q' (quarterly), 'D' (daily)
        future_regressor_strategy: Strategy for future regressor values:
            - 'constant': Use last known value (default)
            - 'extrapolate': Linear extrapolation from last 3 values
            - 'provided': Use values already in external_regressors
        use_model_selection: If True, use cached model selection (default: True).
            When enabled, checks model_selection cache and routes to optimal model.
            When disabled, uses default Prophet model.

    Returns:
        ForecastResult with predictions, confidence intervals, and reasoning.
        When external_regressors provided, includes:
        - model_type: 'prophet_multivariate'
        - accuracy_metrics: {'rmse': X, 'mae': Y, 'mape': Z}
        - regressors_used: list of regressor names
        - improvement_vs_baseline: percentage improvement vs Epic 4 baseline
        When use_model_selection=True, includes:
        - model_source: 'cached' (from cache), 'default' (no cache), 'fallback' (error)
        - model_selection_reason: Human-readable explanation of model choice

    Raises:
        InsufficientDataError: If <6 data points available
    """
    # Story 6.3 AC8: Deprecation warning for historical_data
    if historical_data is not None:
        warnings.warn(
            "historical_data parameter is deprecated, will be removed in Epic 7. "
            "Use metric parameter to fetch from PostgreSQL.",
            DeprecationWarning,
            stacklevel=2,
        )

    # Story 7b-6 AC-7b.6.1: Check model selection cache first
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

    # Determine if multi-variate mode
    is_multivariate = external_regressors is not None and len(external_regressors) > 0

    logger.info(
        "Generating forecast",
        extra={
            "metric": metric,
            "data_points": len(historical_data.points) if historical_data else 0,
            "periods": periods_ahead,
            "multivariate": is_multivariate,
            "regressors": list(external_regressors.keys()) if external_regressors else [],
            "use_model_selection": use_model_selection,
            "selected_model": selected_model,
        },
    )

    # Validate minimum data requirement (AC4: 6+ data points for reliability)
    # Story 8.5: Auto-fetch historical data when not provided
    historical_data = await ensure_historical_data(metric, historical_data, logger)

    # Story 6.13 AC2: Cold-start path for insufficient data
    # Route to Chronos-2 zero-shot when < MIN_DATA_POINTS
    if len(historical_data.points) < MIN_DATA_POINTS:
        logger.info(
            "Cold-start detected: routing to Chronos-2 zero-shot",
            extra={"metric": metric, "data_points": len(historical_data.points)},
        )
        return await generate_chronos_cold_start_forecast(
            metric=metric,
            historical_data=historical_data,
            periods_ahead=periods_ahead,
        )

    # Story 7b-6 AC-7b.6.3: Filter external_regressors based on cached selection
    # This applies to ALL models when cache hit
    filtered_regressors_for_routing = external_regressors
    if selected_model is not None:
        if selected_regressors is not None and external_regressors is not None:
            # Only pass regressors that are in the cached selection AND available
            filtered_regressors_for_routing = {
                name: series
                for name, series in external_regressors.items()
                if name in selected_regressors
            }
            if not filtered_regressors_for_routing:
                # If none of the selected regressors are available, pass None
                filtered_regressors_for_routing = None
        elif selected_regressors is None:
            # use_regressors=False in cache - don't pass any regressors
            filtered_regressors_for_routing = None

    # Story 7b-6 AC-7b.6.2: Route to selected model (including Prophet)
    if selected_model is not None:
        # Prophet is handled by the main Prophet path below - skip routing
        if selected_model == "prophet":
            logger.info(
                f"Prophet selected for {metric}, using main Prophet path",
                extra={"metric": metric, "model": "prophet"},
            )
            # Update external_regressors to filtered version for Prophet path
            external_regressors = filtered_regressors_for_routing
            # Fall through to main Prophet path below
        else:
            # AC-7b.6.4: Try to route to selected model with fallback
            try:
                result = await _route_to_model(
                    model_name=selected_model,
                    metric=metric,
                    historical_data=historical_data,
                    periods_ahead=periods_ahead,
                    external_regressors=filtered_regressors_for_routing,
                )
                # Add metadata from cache
                result.model_source = model_source  # type: ignore[assignment]
                if model_selection_reason:
                    result.model_selection_reason = model_selection_reason

                # Add LLM explanation
                context = f"Historical {metric} data with {len(historical_data.points)} points"
                explanation = await explain_forecast(forecast=result, context=context)
                result.confidence_reasoning = explanation

                return result
            except NotImplementedError:
                # Model not yet implemented - fall through to main Prophet path as fallback
                logger.debug(
                    f"Model {selected_model} not yet implemented, using main Prophet path for {metric}",
                    extra={"metric": metric, "requested_model": selected_model},
                )
                # Update external_regressors to filtered version for Prophet path
                external_regressors = filtered_regressors_for_routing
                # Update source to indicate fallback
                model_source = "fallback"
                model_selection_reason = (
                    f"{selected_model} model not yet implemented, using Prophet fallback"
                )
            except Exception as e:
                # Fallback to Prophet on model failure
                logger.warning(
                    f"Model {selected_model} failed for {metric}, falling back to Prophet",
                    extra={
                        "model": selected_model,
                        "error": str(e),
                        "metric": metric,
                    },
                )
                # Update source to indicate fallback
                model_source = "fallback"
                model_selection_reason = f"Fallback due to {selected_model} failure: {str(e)}"
                # Fall through to main Prophet path below

    # FIX (2025-12-16): Pre-flight data quality validation
    # Validates data before forecasting to catch issues like:
    # - Negative values for positive-only metrics (EBITDA, revenue)
    # - Extreme swings (>10x) indicating data contamination
    # - Scale mismatches (kEUR vs M€ that wasn't normalized)
    is_valid, validation_issues = validate_timeseries_for_forecast(
        metric=metric, points=historical_data.points
    )
    if not is_valid:
        # Log issues but don't block forecasting (data already filtered/normalized upstream)
        # The validation serves as a diagnostic tool to detect if upstream fixes are working
        logger.warning(
            f"Pre-forecast validation issues for {metric}: {validation_issues[:3]}",
            extra={
                "metric": metric,
                "issues": validation_issues,
                "data_points": len(historical_data.points),
            },
        )

    # Step 1: Prepare DataFrame for Prophet (requires 'ds' and 'y' columns)
    df = pd.DataFrame(
        {
            "ds": [p.date for p in historical_data.points],
            "y": [p.value for p in historical_data.points],
        }
    )

    # BUG FIX (P0): Handle duplicate dates before creating Prophet model
    # Duplicates cause "cannot reindex on an axis with duplicate labels" error
    if df.duplicated(subset=["ds"]).any():
        dup_count = df.duplicated(subset=["ds"]).sum()
        logger.warning(
            "Duplicate dates detected in historical data - aggregating by taking mean",
            extra={
                "metric": metric,
                "duplicates": dup_count,
                "total_points": len(df),
            },
        )
        # Group by date and take mean of values
        df = df.groupby("ds", as_index=False).agg({"y": "mean"})

    # Step 2: Configure Prophet based on data availability
    # CRITICAL: Only enable yearly seasonality if we have 12+ months of data.
    # With less data, Prophet hallucinates seasonal patterns causing negative forecasts.
    data_span_days = (df["ds"].max() - df["ds"].min()).days
    has_full_year_data = data_span_days >= 335  # ~11 months minimum for yearly seasonality

    # Story 6.23: Detect ALL metrics that need flat growth
    # Cement industry metrics have sparse/irregular patterns where trend extrapolation causes overfitting.
    # Flat growth Prophet achieves much better accuracy than linear trend or external regressors:
    # - Variable Cost: 8.04% MAPE (vs >100% with regressors)
    # - Capacity Utilization: 3.49% MAPE (vs >100% with regressors)
    # - Revenue (Turnover+VAT): 6.32% MAPE (was 787% with regressors)
    # - EBITDA: Testing (was 852% with regressors)
    # - Sales Volume: Testing (was 31% with regressors)
    metric_lower = metric.lower().strip()
    flat_growth_metrics = [
        # Story 6.25: REMOVED variable_cost - Dec 9 achieved 0.7% MAPE with regressors
        # Story 6.25: REMOVED electricity_cost - Dec 9 achieved 3.0% MAPE with regressors
        # Story 6.25: REMOVED avg_selling_price - Dec 9 achieved 1.6% MAPE with regressors
        # Commit 88785ba added these to flat growth causing 9-11x regressions
        # Story 6.24: REMOVED thermal energy - flat growth = 25.48% MAPE, test linear growth
        # Thermal Energy has 69 periods, 1398 rows (NOT sparse), should use Prophet linear growth
        # Utilization metrics (DB names + variable names)
        "capacity_utilization",
        "frequency ratio",
        "utilization",
        # Financial metrics - sparse data patterns (DB names + variable names)
        "revenue",
        "turnover",
        "turnover+vat",
        # Story 6.25: EBITDA REMOVED from flat growth - commit 88785ba regression!
        # Before 88785ba (Dec 9): linear growth + regressors = 0.2-2.5% MAPE
        # After 88785ba (Dec 13): flat growth added EBITDA here = 13.56% MAPE
        # Root cause: Flat growth disables trend component that regressors capture
        "profit",
        "net_income",
        # Story 6.25: REMOVED sales metrics - Dec 9 achieved 0.8% MAPE with regressors
        # Commit 88785ba added these to flat growth = 31.68% MAPE (39.6x regression)
        # Sales volume responds to macroeconomic trends (euribor, diesel, ttf_gas)
    ]
    use_flat_growth = any(metric_kw in metric_lower for metric_kw in flat_growth_metrics)

    # For short data spans, use simpler model (trend only)
    Prophet = _get_prophet_class()  # Lazy-load Prophet on first use

    # FIX (2025-12-14): Detect significant gaps in data that cause Prophet instability
    # EBITDA data often spans multiple years but has multi-month gaps (e.g., Mar 2023 → Jan 2024)
    # This causes changepoint_prior_scale=0.2 to produce negative forecast extrapolations
    # because Prophet treats gaps as potential changepoints, leading to erratic trend estimates
    has_data_gaps = False
    if len(df) >= 2:
        for i in range(len(df) - 1):
            gap_days = (df["ds"].iloc[i + 1] - df["ds"].iloc[i]).days
            if gap_days > 60:  # More than 2 months gap indicates sparse data
                has_data_gaps = True
                logger.info(
                    f"Data gap detected: {gap_days} days between {df['ds'].iloc[i]} and {df['ds'].iloc[i + 1]}",
                    extra={"metric": metric, "gap_days": gap_days},
                )
                break

    # Story 6.24: Special case for Thermal Energy - override gap detection
    # Thermal Energy has expected quarterly gaps from SECIL reports (every ~90 days)
    # These gaps are normal reporting cycles, NOT sparse data that needs conservative priors
    # Without this override, gap detection triggers and breaks fuel price correlation (2.6% → 23.76% MAPE regression)
    if metric.lower() in ("thermal_cost", "thermal energy", "thermal"):
        if has_data_gaps:
            logger.info(
                "Thermal Energy: Overriding gap detection (quarterly reporting pattern is expected)",
                extra={
                    "metric": metric,
                    "original_has_data_gaps": True,
                    "override": "quarterly_pattern",
                },
            )
        has_data_gaps = False  # Override - quarterly pattern is normal

    # Story 6.23: Very conservative changepoint_prior_scale for flat growth
    if use_flat_growth:
        changepoint_prior = 0.001  # Minimal flexibility for flat cost metrics
        logger.info(
            f"Using flat growth for {metric} (detected as sparse data pattern)",
            extra={"metric": metric, "growth": "flat", "changepoint_prior": changepoint_prior},
        )
    elif not has_full_year_data or has_data_gaps:
        changepoint_prior = 0.05  # Conservative for short data OR data with gaps
        if has_data_gaps:
            logger.info(
                f"Using conservative changepoint prior for {metric} due to data gaps",
                extra={
                    "metric": metric,
                    "changepoint_prior": changepoint_prior,
                    "has_data_gaps": True,
                },
            )
    else:
        changepoint_prior = 0.2  # Standard for full year data

    model = Prophet(
        growth="flat" if use_flat_growth else "linear",  # Story 6.23: flat for sparse cost metrics
        yearly_seasonality=has_full_year_data
        and not use_flat_growth,  # Disable seasonality for flat growth
        weekly_seasonality=False,  # Financial data is quarterly/monthly, not weekly
        daily_seasonality=False,
        changepoint_prior_scale=changepoint_prior,
        interval_width=0.95,
        uncertainty_samples=1000,
    )

    # Story 6.3: Add external regressors for multi-variate forecasting
    regressors_used: list[str] = []
    if is_multivariate and external_regressors:
        # Select regressors by correlation
        target_series = pd.Series(
            [p.value for p in historical_data.points],
            index=pd.to_datetime([p.date for p in historical_data.points]),
        )
        selected = select_regressors(target_series, external_regressors)

        if selected:
            # Prepare regressors (align, interpolate, auto-transform YoY%)
            target_index = pd.DatetimeIndex(df["ds"])
            prepared = prepare_regressors(
                {k: v for k, v in external_regressors.items() if k in selected},
                target_index,
                target_series=target_series,  # Story 6.7: Enable YoY% auto-detection
            )

            # Add each regressor to Prophet and DataFrame
            for name, series in prepared.items():
                model.add_regressor(name, mode="additive")
                df[name] = series.values
                regressors_used.append(name)

            logger.info(
                "Multi-variate regressors added",
                extra={"regressors": regressors_used},
            )

    logger.info(
        "Prophet configured",
        extra={
            "data_points": len(df),
            "data_span_days": data_span_days,
            "yearly_seasonality": has_full_year_data,
            "changepoint_prior_scale": 0.05 if not has_full_year_data else 0.2,
            "regressors": regressors_used,
        },
    )

    # Step 3: Fit model and generate forecast
    # CRITICAL FIX: Prophet must forecast at the same frequency as input data.
    # If input is monthly, forecast monthly then aggregate to quarterly.
    model.fit(df)

    # Determine input data frequency
    # FIX: Use median of RECENT date differences to handle sparse historical data
    # Story 6.23: Variable Cost data is sparse historically but monthly recently
    if len(df) >= 2:
        # Use last 5 date differences (or all if fewer than 5)
        num_recent = min(5, len(df) - 1)
        start_idx = len(df) - 1 - num_recent
        date_diffs = [
            (df["ds"].iloc[i + 1] - df["ds"].iloc[i]).days for i in range(start_idx, len(df) - 1)
        ]
        median_diff = sorted(date_diffs)[len(date_diffs) // 2]
        is_monthly_data = 25 <= median_diff <= 35
    else:
        is_monthly_data = False

    if is_monthly_data:
        # Story 6.7: Respect frequency parameter - return monthly if requested
        output_monthly = frequency.upper() in ("M", "ME", "MS")

        if output_monthly:
            # Monthly input, monthly output (Story 6.7)
            # FIX (2025-12-14): Use freq="MS" to match historical data format
            # Historical data uses month-start dates (e.g., 2025-10-01)
            # Using "ME" (month-end) caused severe forecast errors because Prophet
            # treated month-end as different time points, causing wild interpolation
            # (e.g., €102M forecast instead of €15K for EBITDA)
            future = model.make_future_dataframe(periods=periods_ahead, freq="MS")

            # Story 6.3: Add regressor values to future dataframe
            if regressors_used and external_regressors:
                future_dates = pd.DatetimeIndex(future["ds"].tail(periods_ahead))
                extended = _generate_future_regressors(
                    {k: v for k, v in external_regressors.items() if k in regressors_used},
                    future_dates,
                    strategy=future_regressor_strategy,
                )
                for name in regressors_used:
                    if name in extended:
                        # Story 6.11: Reindex and fill any NaN with forward-fill then backward-fill
                        reindexed = extended[name].reindex(future["ds"])
                        reindexed = reindexed.ffill().bfill()
                        future[name] = reindexed.values

            prophet_forecast = model.predict(future)

            # FIX (2025-12-14): With freq="MS", Prophet produces clean future dates
            # No need for complex filtering - just take the last periods_ahead rows
            forecast_months = prophet_forecast.tail(periods_ahead)

            # Return monthly forecasts directly (no aggregation)
            forecast_points = []
            for _, row in forecast_months.iterrows():
                month_name = row["ds"].strftime("%b %Y")
                forecast_points.append(
                    ForecastPoint(
                        date=row["ds"].to_pydatetime(),
                        value=row["yhat"],
                        lower=row["yhat_lower"],
                        upper=row["yhat_upper"],
                        label=month_name,
                    )
                )

            # FIX (2025-12-16): Clamp negative values for positive-only metrics
            # EBITDA, revenue, capacity_utilization should never be negative
            if metric.lower() in POSITIVE_ONLY_METRICS:
                clamped_count = 0
                for i, point in enumerate(forecast_points):
                    if point.value < 0:
                        clamped_count += 1
                        forecast_points[i] = ForecastPoint(
                            date=point.date,
                            value=0.0,  # Clamp to 0
                            lower=max(0.0, point.lower),
                            upper=point.upper,
                            label=point.label,
                        )
                if clamped_count > 0:
                    logger.warning(
                        f"Clamped {clamped_count} negative forecast values to 0 for positive-only metric {metric}",
                        extra={"metric": metric, "clamped_count": clamped_count},
                    )

            logger.debug(
                "Monthly forecast generated",
                extra={"periods": periods_ahead, "output_frequency": "monthly"},
            )
        else:
            # Monthly input, quarterly output (aggregate 3 months)
            monthly_periods = periods_ahead * 3  # 3 months per quarter
            # FIX (2025-12-14): Use freq="MS" to match historical data format
            future = model.make_future_dataframe(periods=monthly_periods, freq="MS")

            # Story 6.3: Add regressor values to future dataframe
            if regressors_used and external_regressors:
                future_dates = pd.DatetimeIndex(future["ds"].tail(monthly_periods))
                extended = _generate_future_regressors(
                    {k: v for k, v in external_regressors.items() if k in regressors_used},
                    future_dates,
                    strategy=future_regressor_strategy,
                )
                for name in regressors_used:
                    if name in extended:
                        # Story 6.11: Reindex and fill any NaN with forward-fill then backward-fill
                        reindexed = extended[name].reindex(future["ds"])
                        reindexed = reindexed.ffill().bfill()
                        future[name] = reindexed.values

            prophet_forecast = model.predict(future)

            # Get only the future monthly predictions (not historical)
            forecast_months = prophet_forecast.tail(monthly_periods)

            # Aggregate monthly forecasts into quarterly
            forecast_points = []
            for q_idx in range(periods_ahead):
                # Get 3 months for this quarter
                start_idx = q_idx * 3
                end_idx = start_idx + 3
                quarter_months = forecast_months.iloc[start_idx:end_idx]

                # Sum monthly values to get quarterly total
                quarterly_value = quarter_months["yhat"].sum()
                quarterly_lower = quarter_months["yhat_lower"].sum()
                quarterly_upper = quarter_months["yhat_upper"].sum()

                # Use the last month's date as the quarter-end date
                quarter_end_date = quarter_months.iloc[-1]["ds"]
                quarter = (quarter_end_date.month - 1) // 3 + 1
                label = f"Q{quarter} {quarter_end_date.year}"

                forecast_points.append(
                    ForecastPoint(
                        date=quarter_end_date.to_pydatetime(),
                        value=quarterly_value,
                        lower=quarterly_lower,
                        upper=quarterly_upper,
                        label=label,
                    )
                )

                logger.debug(
                    f"Quarterly aggregation: {label} = sum of 3 monthly forecasts",
                    extra={
                        "quarter": label,
                        "monthly_values": quarter_months["yhat"].tolist(),
                        "quarterly_total": quarterly_value,
                    },
                )
    else:
        # Non-monthly input: use original quarterly forecast
        future = model.make_future_dataframe(periods=periods_ahead, freq="QE")

        # Story 6.3: Add regressor values to future dataframe
        if regressors_used and external_regressors:
            future_dates = pd.DatetimeIndex(future["ds"].tail(periods_ahead))
            extended = _generate_future_regressors(
                {k: v for k, v in external_regressors.items() if k in regressors_used},
                future_dates,
                strategy=future_regressor_strategy,
            )
            for name in regressors_used:
                if name in extended:
                    # Story 6.11: Reindex and fill any NaN with forward-fill then backward-fill
                    # (matches monthly path at line 1461-1464)
                    reindexed = extended[name].reindex(future["ds"])
                    reindexed = reindexed.ffill().bfill()
                    future[name] = reindexed.values

        prophet_forecast = model.predict(future)

        # Step 4: Extract forecast points (only the predicted periods, not historical)
        forecast_points = []
        forecast_rows = prophet_forecast.tail(periods_ahead)

        for _, row in forecast_rows.iterrows():
            # Generate quarter label
            quarter = (row["ds"].month - 1) // 3 + 1
            label = f"Q{quarter} {row['ds'].year}"

            forecast_points.append(
                ForecastPoint(
                    date=row["ds"].to_pydatetime(),
                    value=row["yhat"],
                    lower=row["yhat_lower"],
                    upper=row["yhat_upper"],
                    label=label,
                )
            )

    # Step 5: Calculate accuracy metrics if multi-variate
    accuracy_metrics: dict[str, float] = {}
    improvement_vs_baseline: float | None = None

    if is_multivariate:
        # Calculate accuracy using cross-validation
        accuracy_metrics = calculate_accuracy(model, df)

        # Calculate improvement vs baseline
        baseline_rmse = get_baseline_rmse(metric)
        if baseline_rmse and accuracy_metrics.get("rmse", 0) > 0:
            improvement_vs_baseline = (
                (baseline_rmse - accuracy_metrics["rmse"]) / baseline_rmse
            ) * 100

            logger.info(
                "Accuracy improvement calculated",
                extra={
                    "baseline_rmse": baseline_rmse,
                    "new_rmse": accuracy_metrics["rmse"],
                    "improvement_pct": improvement_vs_baseline,
                },
            )

    # Step 6: Build ForecastResult with multi-variate fields
    model_type = "prophet_multivariate" if regressors_used else "prophet_univariate"
    basis_text = f"Prophet model trained on {len(historical_data.points)} data points"
    if regressors_used:
        basis_text += f" with {len(regressors_used)} external regressors"

    result = ForecastResult(
        metric_name=metric,
        historical_data=historical_data.points,
        forecast=forecast_points,
        basis=basis_text,
        accuracy_estimate="±15% (NFR10 target)",
        periods_ahead=periods_ahead,
        # Story 6.3: Multi-variate fields
        model_type=model_type,
        accuracy_metrics=accuracy_metrics,
        regressors_used=regressors_used,
        improvement_vs_baseline=improvement_vs_baseline,
        # Story 7b-6: Model selection metadata
        model_source=model_source,  # type: ignore[arg-type]
        model_selection_reason=model_selection_reason,
    )

    # Step 7: Generate LLM explanation for confidence reasoning
    context = f"Historical {metric} data from {len(historical_data.source_documents)} documents"
    if regressors_used:
        context += f". Multi-variate forecast using: {', '.join(regressors_used)}"
    explanation = await explain_forecast(result, context)
    result.confidence_reasoning = explanation

    logger.info(
        "Forecast generated",
        extra={
            "metric": metric,
            "forecast_points": len(forecast_points),
            "model_type": model_type,
            "regressors": regressors_used,
            "accuracy_metrics": accuracy_metrics,
        },
    )

    return result


async def explain_forecast(forecast: ForecastResult, context: str) -> str:
    """Use Mistral Large to explain forecast with context.

    Story 4.2 AC1: LLM reasoning layer for confidence rationale.

    Args:
        forecast: Prophet forecast result
        context: Retrieved document context (trends, events)

    Returns:
        Natural language explanation with confidence rationale
    """
    logger.info("Generating forecast explanation with Mistral Large")

    client = get_mistral_client()

    # Build forecast summary for prompt
    forecast_summary = {
        "metric": forecast.metric_name,
        "periods_ahead": forecast.periods_ahead,
        "historical_points": len(forecast.historical_data),
        "predictions": [
            {
                "period": p.label,
                "value": round(p.value, 2),
                "range": f"{round(p.lower, 2)} - {round(p.upper, 2)}",
            }
            for p in forecast.forecast
        ],
    }

    prompt = f"""You are a financial analyst explaining a forecast to stakeholders.

Forecast Data:
{json.dumps(forecast_summary, indent=2)}

Context:
{context}

Please provide a clear, concise explanation that:
1. Summarizes the forecast values and confidence intervals
2. Explains why confidence intervals are what they are (data quality, trends)
3. Identifies 2-3 key risks
4. Identifies 1-2 opportunities

Format your response as JSON:
{{
    "summary": "2-3 sentence natural language explanation of the forecast",
    "confidence_rationale": "Why confidence intervals are narrow/wide",
    "risks": ["Risk 1", "Risk 2"],
    "opportunities": ["Opportunity 1"]
}}"""

    try:
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
        )
        llm_response = response.choices[0].message.content if response.choices else ""

        # Parse JSON response and format as explanation text
        if llm_response:
            # Try to parse as JSON, fall back to raw text
            try:
                parsed = json.loads(llm_response)
                explanation = parsed.get("summary", "")
                if parsed.get("confidence_rationale"):
                    explanation += f" {parsed['confidence_rationale']}"
                return str(explanation)
            except json.JSONDecodeError:
                return llm_response

    except Exception as e:
        logger.warning(f"LLM explanation failed, using fallback: {e}")

    # Fallback explanation if LLM fails
    return (
        f"Forecast based on {len(forecast.historical_data)} historical data points. "
        f"Confidence intervals reflect model uncertainty over {forecast.periods_ahead} periods."
    )


def calculate_accuracy(model: Prophet, df: pd.DataFrame) -> dict[str, float]:
    """Calculate RMSE, MAE, MAPE using Prophet cross-validation.

    Story 6.3 AC5: Accuracy metrics calculation.

    Args:
        model: Fitted Prophet model
        df: Training DataFrame with 'ds' and 'y' columns

    Returns:
        Dictionary with 'rmse', 'mae', 'mape' metrics
    """
    # Only run CV if sufficient data (12+ points)
    if len(df) < MIN_CV_DATA_POINTS:
        logger.warning(
            f"Insufficient data for CV ({len(df)} < {MIN_CV_DATA_POINTS}). Returning zero metrics."
        )
        return {"rmse": 0.0, "mae": 0.0, "mape": 0.0}

    try:
        from prophet.diagnostics import cross_validation, performance_metrics

        # Calculate appropriate CV parameters based on data length
        data_span_days = (df["ds"].max() - df["ds"].min()).days

        # Initial training period: ~60% of data
        initial_days = int(data_span_days * 0.6)
        initial = f"{initial_days} days"

        # Period between cutoffs: ~30 days
        period = "30 days"

        # Horizon: ~90 days (3 months)
        horizon = "90 days"

        cv = cross_validation(model, initial=initial, period=period, horizon=horizon)
        metrics = performance_metrics(cv)

        return {
            "rmse": float(metrics["rmse"].mean()),
            "mae": float(metrics["mae"].mean()),
            "mape": float(metrics["mape"].mean()),
        }

    except Exception as e:
        logger.warning(f"Cross-validation failed: {e}. Returning zero metrics.")
        return {"rmse": 0.0, "mae": 0.0, "mape": 0.0}


def get_baseline_rmse(metric: str) -> float | None:
    """Get Epic 4 baseline RMSE from stored results.

    Story 6.3 AC5: Baseline RMSE lookup for improvement calculation.

    Args:
        metric: Metric name to look up

    Returns:
        Baseline RMSE if available, None otherwise
    """
    # Check environment variable first
    env_key = f"BASELINE_RMSE_{metric.upper()}"
    env_value = os.getenv(env_key)
    if env_value:
        try:
            return float(env_value)
        except ValueError:
            pass

    # Check accuracy tracking log file
    log_path = Path("docs/accuracy-tracking-log.jsonl")
    if log_path.exists():
        try:
            with open(log_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if (
                        entry.get("metric") == metric
                        and entry.get("type") == "baseline"
                        and "rmse" in entry
                    ):
                        return float(entry["rmse"])
        except (json.JSONDecodeError, OSError):
            pass

    return None
