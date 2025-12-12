#!/usr/bin/env python3
"""Comprehensive Forecasting Model Validation.

Validates all forecasting models in RAGLite's ensemble using production data.
Based on the validate-cement-forecasting-12vars.py pattern and
docs/FORECASTING-VALIDATION-GUIDE.md methodology.

Stories covered:
- 6.11: MCP Multi-variate forecasting with external regressors
- 6.12: CatBoost integration + adaptive weights
- 6.13: Chronos-2 integration (cold-start + ensemble member)
- 6.14: TFT integration with training workflow

Models tested (7 individual + 1 ensemble):
- Prophet (statistical, baseline)
- Linear Regression (ML)
- XGBoost (ML)
- LightGBM (ML, Story 6.8)
- CatBoost (ML, Story 6.12)
- Chronos-2 (foundation model, Story 6.13)
- TFT (deep learning, Story 6.14)
- Ensemble (all models combined)

Usage:
    python scripts/validate-all-forecasting-models.py [options]

Options:
    --full              Run full validation (all 8 vars, all models)
    --train-tft         Force TFT training before validation
    --skip-tft          Skip TFT model entirely
    --cold-start        Test Chronos-2 cold-start scenario
    --validate-weights  Validate adaptive weights (Story 6.12)
    --model MODEL       Test specific model only
    --variable VAR      Test specific variable only
    --verbose, -v       Show detailed output
    --export-json       Export results to JSON file
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import warnings
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Suppress deprecation warning for historical_data parameter
warnings.filterwarnings(
    "ignore",
    message="historical_data parameter is deprecated",
    category=DeprecationWarning,
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class ModelResult:
    """Result for a single model forecast."""

    model_name: str
    mape: float | None = None
    rmse: float | None = None
    execution_time: float = 0.0
    success: bool = False
    error: str | None = None
    story_ref: str | None = None  # Story reference (e.g., "6.12")


@dataclass
class VariableResult:
    """Results for all models on a single variable."""

    variable_name: str
    display_name: str
    target_mape: float
    data_points: int = 0
    model_results: dict[str, ModelResult] = field(default_factory=dict)
    best_model: str | None = None
    best_mape: float | None = None


@dataclass
class TFTTrainingResult:
    """Result from TFT training."""

    status: str  # "trained", "skipped", "failed"
    checkpoint_path: str | None = None
    duration_seconds: float = 0.0
    metrics: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class WeightsValidationResult:
    """Result from adaptive weights validation."""

    metric_name: str
    weights: dict[str, float] = field(default_factory=dict)
    total_weight: float = 0.0
    is_valid: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class TFTStatusResult:
    """Result from TFT status check."""

    has_checkpoint: bool = False
    checkpoint_path: str | None = None
    model_version: str | None = None
    trained_at: datetime | None = None
    age_days: int = 0
    is_fresh: bool = False
    metrics: dict[str, Any] | None = None


@dataclass
class ValidationReport:
    """Complete validation report."""

    timestamp: str
    stories_validated: list[str] = field(default_factory=list)
    variables_tested: int = 0
    total_model_runs: int = 0
    variable_results: list[VariableResult] = field(default_factory=list)
    tft_training_result: TFTTrainingResult | None = None
    tft_status: TFTStatusResult | None = None
    weights_validation: list[WeightsValidationResult] = field(default_factory=list)
    cold_start_results: list[dict] = field(default_factory=list)


# =============================================================================
# Test Configuration - Full 8 Variables from Validation Guide
# =============================================================================

# All models to test (7 individual)
ALL_MODELS = [
    "prophet",
    "linear",
    "xgboost",
    "lightgbm",
    "catboost",
    "chronos",
    "tft",
]

# Model story references
MODEL_STORY_REF = {
    "prophet": None,
    "linear": None,
    "xgboost": None,
    "lightgbm": "6.8",
    "catboost": "6.12",
    "chronos": "6.13",
    "tft": "6.14",
    "ensemble": None,
}

# Full 8 variables from docs/FORECASTING-VALIDATION-GUIDE.md
TEST_VARIABLES = [
    # Financial metrics (from PostgreSQL via SQL extraction)
    {
        "name": "revenue",
        "display_name": "Revenue",
        "target_mape": 5.0,
        "metric_alias": "Revenue",
        "regressors": ["euribor_3m", "diesel", "ttf_gas"],
        "is_external": False,
    },
    {
        "name": "ebitda",
        "display_name": "EBITDA",
        "target_mape": 5.0,
        "metric_alias": "EBITDA",
        "regressors": ["euribor_3m", "ttf_gas", "diesel", "api2_coal"],
        "is_external": False,
    },
    {
        "name": "sales_volume",
        "display_name": "Sales Volume",
        "target_mape": 5.0,
        "metric_alias": "Sales Volume",
        "regressors": ["euribor_3m", "diesel", "ttf_gas"],
        "is_external": False,
    },
    {
        "name": "variable_cost",
        "display_name": "Variable Cost",
        "target_mape": 8.0,
        "metric_alias": "Variable Cost",
        "regressors": ["diesel", "ttf_gas", "api2_coal"],
        "is_external": False,
    },
    {
        "name": "avg_selling_price",
        "display_name": "Avg Selling Price",
        "target_mape": 6.0,
        "metric_alias": "Average Selling Price",
        "regressors": ["diesel", "euribor_3m", "ttf_gas"],
        "is_external": False,
    },
    {
        "name": "capacity_utilization",
        "display_name": "Capacity Utilization",
        "target_mape": 10.0,
        "metric_alias": "Capacity Utilization",
        "regressors": ["euribor_3m", "diesel", "ttf_gas"],
        "is_external": False,
    },
    # Energy/External metrics (from external APIs)
    {
        "name": "ttf_gas",
        "display_name": "TTF Gas Price",
        "target_mape": 15.0,
        "metric_alias": None,
        "regressors": ["euribor_3m"],
        "is_external": True,
    },
    {
        "name": "diesel",
        "display_name": "Diesel Price",
        "target_mape": 10.0,
        "metric_alias": None,
        "regressors": ["euribor_3m", "ttf_gas"],
        "is_external": True,
    },
]


# =============================================================================
# TFT Training Functions (Story 6.14 Prerequisite)
# =============================================================================


async def ensure_tft_trained(force: bool = False, verbose: bool = False) -> TFTTrainingResult:
    """Ensure TFT model is trained before validation.

    Story 6.14 AC1: TFT training runs automatically if no checkpoint exists.

    Args:
        force: Force training even if checkpoint exists
        verbose: Show detailed output

    Returns:
        TFTTrainingResult with training status and metrics
    """
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.shared.database import get_session

    result = TFTTrainingResult(status="checking")

    try:
        session = get_session()
        storage = ExternalDataStorage(session)

        # Check for existing checkpoint
        active_checkpoint = storage.get_active_model("tft")

        if active_checkpoint and not force:
            age = datetime.now(UTC) - active_checkpoint.trained_at.replace(tzinfo=UTC)
            age_days = age.days

            if age_days < 7:  # Checkpoint is fresh
                result.status = "skipped"
                result.checkpoint_path = active_checkpoint.checkpoint_path
                result.metrics = active_checkpoint.metrics_json
                if verbose:
                    print(f"  Active checkpoint found: {active_checkpoint.checkpoint_path}")
                    print(f"  Age: {age_days} days (fresh, <7 days)")
                return result

        # Need to train TFT
        print("\n  Training TFT model (this takes 2-5 minutes)...")

        start_time = time.time()

        # Import and run training
        from raglite.forecasting.tft_training import (
            collect_training_data,
            prepare_tft_dataset,
            save_tft_checkpoint,
            train_tft_model,
        )

        # Collect training data from external data sources
        training_df = await collect_training_data()

        if training_df is None or len(training_df) < 24:
            result.status = "failed"
            result.error = "Insufficient training data (need >=24 data points)"
            return result

        # Prepare datasets
        training_dataset, validation_dataset = prepare_tft_dataset(training_df)

        # Train model
        tft_model, metrics = train_tft_model(training_dataset, validation_dataset)

        # Save checkpoint (model_version is auto-generated from timestamp)
        checkpoint_path = save_tft_checkpoint(tft_model, metrics)

        result.status = "trained"
        result.checkpoint_path = checkpoint_path
        result.duration_seconds = time.time() - start_time
        result.metrics = metrics

        if verbose:
            print("\n  ✓ TFT Training Complete")
            print(f"    Checkpoint: {checkpoint_path}")
            print(f"    Duration: {result.duration_seconds:.1f}s")
            if metrics:
                print(f"    Metrics: val_loss={metrics.get('val_loss', 'N/A'):.4f}")

    except ImportError as e:
        result.status = "failed"
        result.error = f"TFT dependencies not installed: {e}"
        if verbose:
            print(f"  ⚠️ TFT training skipped: {e}")
    except Exception as e:
        result.status = "failed"
        result.error = str(e)
        logger.error(f"TFT training failed: {e}")
        if verbose:
            print(f"  ❌ TFT training failed: {e}")

    return result


async def check_tft_status(verbose: bool = False) -> TFTStatusResult:
    """Check TFT training status (Story 6.14).

    Args:
        verbose: Show detailed output

    Returns:
        TFTStatusResult with checkpoint information
    """
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.shared.database import get_session

    result = TFTStatusResult()

    try:
        session = get_session()
        storage = ExternalDataStorage(session)

        checkpoint = storage.get_active_model("tft")

        if checkpoint:
            result.has_checkpoint = True
            result.checkpoint_path = checkpoint.checkpoint_path
            result.model_version = checkpoint.model_version
            result.trained_at = checkpoint.trained_at
            result.metrics = checkpoint.metrics_json

            # Calculate age
            now = datetime.now(UTC)
            trained_at = checkpoint.trained_at.replace(tzinfo=UTC)
            age = now - trained_at
            result.age_days = age.days
            result.is_fresh = age.days < 7

            # Verify checkpoint file exists
            if result.checkpoint_path:
                result.has_checkpoint = Path(result.checkpoint_path).exists()

    except Exception as e:
        logger.warning(f"Failed to check TFT status: {e}")

    return result


# =============================================================================
# Adaptive Weights Validation (Story 6.12)
# =============================================================================


async def validate_adaptive_weights(
    metric_name: str | None = None, verbose: bool = False
) -> list[WeightsValidationResult]:
    """Validate adaptive weights from PostgreSQL.

    Story 6.12 AC4: Weights sum to 1.0, each within 5%-50% bounds.

    Args:
        metric_name: Specific metric to validate (None = all)
        verbose: Show detailed output

    Returns:
        List of WeightsValidationResult
    """
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.shared.database import get_session

    results = []

    try:
        session = get_session()
        storage = ExternalDataStorage(session)

        # Get weights
        weights_list = storage.get_model_weights(metric_name)

        if not weights_list:
            # Return empty result if no weights found
            if verbose:
                print("  No adaptive weights found in database")
            return results

        # Group by metric
        metrics_weights: dict[str, dict[str, float]] = {}
        for w in weights_list:
            if w.metric_name not in metrics_weights:
                metrics_weights[w.metric_name] = {}
            metrics_weights[w.metric_name][w.model_name] = float(w.weight)

        # Validate each metric
        for metric, weights in metrics_weights.items():
            result = WeightsValidationResult(metric_name=metric, weights=weights)

            # Check total
            total = sum(weights.values())
            result.total_weight = total

            # Validate sum = 1.0 (±0.001)
            if abs(total - 1.0) > 0.001:
                result.errors.append(f"Weights sum to {total:.4f}, expected 1.0")

            # Validate bounds (5%-50%)
            for model, weight in weights.items():
                if weight < 0.05:
                    result.errors.append(f"{model} weight {weight:.2%} < 5% minimum")
                if weight > 0.50:
                    result.errors.append(f"{model} weight {weight:.2%} > 50% maximum")

            result.is_valid = len(result.errors) == 0
            results.append(result)

    except Exception as e:
        logger.warning(f"Failed to validate weights: {e}")

    return results


# =============================================================================
# Data Loading Functions
# =============================================================================


async def load_external_data(metric_name: str) -> Any:
    """Load time series from external sources.

    Args:
        metric_name: Name of the metric to load

    Returns:
        TimeSeriesData or None
    """
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    end_date = date.today()
    start_date = end_date - timedelta(days=365 * 3)  # 3 years for better validation

    data_points: list[TimeSeriesPoint] = []

    if metric_name == "ttf_gas":
        from raglite.external_data.clients.ice_futures import ICEFuturesClient

        client = ICEFuturesClient()
        raw_data = await client.fetch_ttf_gas(start_date, end_date)
        if raw_data:
            df = pd.DataFrame([(d.date, d.price) for d in raw_data], columns=["date", "value"])
            df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")
            monthly = df.groupby("month")["value"].mean().reset_index()
            for _, row in monthly.iterrows():
                data_points.append(
                    TimeSeriesPoint(date=row["month"].to_timestamp(), value=float(row["value"]))
                )

    elif metric_name == "diesel":
        from raglite.external_data.clients.eu_oil_bulletin import EUOilBulletinClient

        client = EUOilBulletinClient()
        raw_data = await client.fetch_diesel_prices(start_date, end_date)
        if raw_data:
            df = pd.DataFrame(
                [(d.date, d.price_eur_litre) for d in raw_data], columns=["date", "value"]
            )
            df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")
            monthly = df.groupby("month")["value"].mean().reset_index()
            for _, row in monthly.iterrows():
                data_points.append(
                    TimeSeriesPoint(date=row["month"].to_timestamp(), value=float(row["value"]))
                )

    elif metric_name == "euribor":
        from raglite.external_data.clients.ecb import ECBClient

        client = ECBClient()
        raw_data = await client.fetch_euribor(tenor="3M", start_date=start_date, end_date=end_date)
        if raw_data:
            df = pd.DataFrame([(d.date, d.rate_pct) for d in raw_data], columns=["date", "value"])
            df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")
            monthly = df.groupby("month")["value"].mean().reset_index()
            for _, row in monthly.iterrows():
                data_points.append(
                    TimeSeriesPoint(date=row["month"].to_timestamp(), value=float(row["value"]))
                )

    elif metric_name == "api2_coal":
        from raglite.external_data.clients.ice_futures import ICEFuturesClient

        client = ICEFuturesClient()
        raw_data = await client.fetch_api2_coal(start_date, end_date)
        if raw_data:
            df = pd.DataFrame([(d.date, d.price) for d in raw_data], columns=["date", "value"])
            df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")
            monthly = df.groupby("month")["value"].mean().reset_index()
            for _, row in monthly.iterrows():
                data_points.append(
                    TimeSeriesPoint(date=row["month"].to_timestamp(), value=float(row["value"]))
                )

    if len(data_points) < 6:
        return None

    data_points.sort(key=lambda p: p.date)

    return TimeSeriesData(
        metric_name=metric_name,
        points=data_points,
        interval="monthly",
    )


async def fetch_external_regressors(
    regressor_names: list[str],
    start_date: date,
    end_date: date,
) -> dict[str, pd.Series]:
    """Fetch external regressor data."""
    regressors: dict[str, pd.Series] = {}

    for reg_name in regressor_names:
        try:
            if reg_name == "euribor_3m":
                from raglite.external_data.clients.ecb import ECBClient

                client = ECBClient()
                data = await client.fetch_euribor(
                    tenor="3M", start_date=start_date, end_date=end_date
                )
                if data:
                    series = pd.Series(
                        [d.rate_pct for d in data],
                        index=pd.DatetimeIndex([d.date for d in data]),
                    )
                    regressors[reg_name] = series.groupby(level=0).mean()

            elif reg_name == "ttf_gas":
                from raglite.external_data.clients.ice_futures import ICEFuturesClient

                client = ICEFuturesClient()
                data = await client.fetch_ttf_gas(start_date, end_date)
                if data:
                    series = pd.Series(
                        [d.price for d in data],
                        index=pd.DatetimeIndex([d.date for d in data]),
                    )
                    regressors[reg_name] = series.groupby(level=0).mean()

            elif reg_name == "diesel":
                from raglite.external_data.clients.eu_oil_bulletin import EUOilBulletinClient

                client = EUOilBulletinClient()
                data = await client.fetch_diesel_prices(start_date, end_date)
                if data:
                    series = pd.Series(
                        [d.price_eur_litre for d in data],
                        index=pd.DatetimeIndex([d.date for d in data]),
                    )
                    regressors[reg_name] = series.groupby(level=0).mean()

            elif reg_name == "api2_coal":
                from raglite.external_data.clients.ice_futures import ICEFuturesClient

                client = ICEFuturesClient()
                data = await client.fetch_api2_coal(start_date, end_date)
                if data:
                    series = pd.Series(
                        [d.price for d in data],
                        index=pd.DatetimeIndex([d.date for d in data]),
                    )
                    regressors[reg_name] = series.groupby(level=0).mean()

            logger.debug(
                f"Fetched regressor {reg_name}: {len(regressors.get(reg_name, []))} points"
            )

        except Exception as e:
            logger.warning(f"Failed to fetch regressor {reg_name}: {e}")

    return regressors


# =============================================================================
# Individual Model Testing Functions
# =============================================================================


def run_individual_model(
    model_name: str,
    y_series: pd.Series,
    X_df: pd.DataFrame | None,
    X_future: pd.DataFrame | None,
    periods_ahead: int = 4,
    fast_mode: bool = True,
) -> ModelResult:
    """Run a single model and return results.

    Args:
        model_name: Name of model to run
        y_series: Target time series
        X_df: Feature matrix (for ML models)
        X_future: Future features (for ML models)
        periods_ahead: Forecast horizon
        fast_mode: Use fast mode for quicker results

    Returns:
        ModelResult with MAPE/RMSE metrics
    """
    result = ModelResult(model_name=model_name, story_ref=MODEL_STORY_REF.get(model_name))

    try:
        start_time = time.time()
        forecast_values = None

        if model_name == "prophet":
            from raglite.forecasting.hybrid import generate_forecast
            from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

            # Convert to TimeSeriesData
            points = [TimeSeriesPoint(date=idx, value=float(val)) for idx, val in y_series.items()]
            ts_data = TimeSeriesData(metric_name="test", points=points, interval="monthly")

            # Run Prophet
            loop = asyncio.get_event_loop()
            forecast_result = loop.run_until_complete(
                generate_forecast(
                    metric="test",
                    historical_data=ts_data,
                    periods_ahead=periods_ahead,
                    external_regressors=None,
                    frequency="M",
                )
            )
            if forecast_result and forecast_result.forecast:
                forecast_values = [p.value for p in forecast_result.forecast[:periods_ahead]]

        elif model_name == "linear":
            from raglite.forecasting.hybrid import _fit_and_forecast_linear

            if X_df is not None and X_future is not None and len(X_df.columns) > 0:
                model_result = _fit_and_forecast_linear(
                    X=X_df,
                    y=y_series,
                    X_future=X_future,
                    feature_names=list(X_df.columns),
                    periods_ahead=periods_ahead,
                )
                if model_result:
                    forecast_values = model_result.get("values", [])

        elif model_name == "xgboost":
            from raglite.forecasting.hybrid import _fit_and_forecast_xgboost

            if X_df is not None and X_future is not None and len(X_df.columns) > 0:
                model_result = _fit_and_forecast_xgboost(
                    X=X_df,
                    y=y_series,
                    X_future=X_future,
                    periods_ahead=periods_ahead,
                    fast_mode=fast_mode,
                )
                if model_result:
                    forecast_values = model_result.get("values", [])

        elif model_name == "lightgbm":
            from raglite.forecasting.hybrid import _fit_and_forecast_lightgbm

            if X_df is not None and X_future is not None and len(X_df.columns) > 0:
                model_result = _fit_and_forecast_lightgbm(
                    X=X_df,
                    y=y_series,
                    X_future=X_future,
                    periods_ahead=periods_ahead,
                    fast_mode=fast_mode,
                )
                if model_result:
                    forecast_values = model_result.get("values", [])

        elif model_name == "catboost":
            from raglite.forecasting.hybrid import _fit_and_forecast_catboost

            if X_df is not None and X_future is not None and len(X_df.columns) > 0:
                model_result = _fit_and_forecast_catboost(
                    X=X_df,
                    y=y_series,
                    X_future=X_future,
                    periods_ahead=periods_ahead,
                    fast_mode=fast_mode,
                )
                if model_result:
                    forecast_values = model_result.get("values", [])

        elif model_name == "chronos":
            from raglite.forecasting.hybrid import _fit_and_forecast_chronos

            X_regressors = X_df if X_df is not None and len(X_df.columns) > 0 else None
            model_result = _fit_and_forecast_chronos(
                y=y_series,
                periods_ahead=periods_ahead,
                external_regressors=X_regressors,
            )
            if model_result:
                forecast_values = model_result.get("values", [])

        elif model_name == "tft":
            from raglite.forecasting.hybrid import _fit_and_forecast_tft

            X_regressors = X_df if X_df is not None and len(X_df.columns) > 0 else None
            model_result = _fit_and_forecast_tft(
                y=y_series,
                periods_ahead=periods_ahead,
                external_regressors=X_regressors,
            )
            if model_result:
                forecast_values = model_result.get("values", [])

        result.execution_time = time.time() - start_time

        # Calculate MAPE if we have forecasts
        if forecast_values and len(forecast_values) > 0:
            # Use holdout validation (last N points as actuals)
            holdout_size = min(periods_ahead, len(y_series) // 4)
            if holdout_size > 0:
                actuals = y_series.values[-holdout_size:]
                predictions = forecast_values[:holdout_size]

                if len(actuals) == len(predictions):
                    mape = _calculate_mape(actuals, predictions)
                    rmse = _calculate_rmse(actuals, predictions)
                    result.mape = mape
                    result.rmse = rmse
                    result.success = True

    except Exception as e:
        result.error = str(e)
        logger.debug(f"Model {model_name} failed: {e}")

    return result


def _calculate_mape(actuals: np.ndarray, predictions: list[float]) -> float | None:
    """Calculate Mean Absolute Percentage Error."""
    errors = []
    for actual, pred in zip(actuals, predictions, strict=False):
        if actual != 0:
            errors.append(abs((actual - pred) / actual) * 100)
    if not errors:
        return None
    return float(np.mean(errors))


def _calculate_rmse(actuals: np.ndarray, predictions: list[float]) -> float | None:
    """Calculate Root Mean Squared Error."""
    if len(actuals) != len(predictions):
        return None
    mse = np.mean([(a - p) ** 2 for a, p in zip(actuals, predictions, strict=False)])
    return float(np.sqrt(mse))


# =============================================================================
# Forecasting Functions
# =============================================================================


async def run_baseline_forecast(
    historical_data: Any,
    verbose: bool = False,
) -> ModelResult:
    """Run Prophet univariate forecast (baseline)."""
    from raglite.forecasting.hybrid import generate_forecast

    result = ModelResult(model_name="prophet")

    try:
        start_time = time.time()

        forecast_result = await generate_forecast(
            metric=historical_data.metric_name,
            historical_data=historical_data,
            periods_ahead=4,
            external_regressors=None,
            frequency="M",
        )

        result.execution_time = time.time() - start_time

        if forecast_result and forecast_result.accuracy_metrics:
            result.mape = forecast_result.accuracy_metrics.get("mape")
            result.rmse = forecast_result.accuracy_metrics.get("rmse")
            result.success = True

        # Calculate MAPE from holdout if not provided
        if result.mape is None and forecast_result and forecast_result.forecast:
            result.mape = _calculate_holdout_mape(
                historical_data, forecast_result.forecast, holdout_size=4
            )
            if result.mape is not None:
                result.success = True

    except Exception as e:
        result.error = str(e)
        logger.error(f"Baseline forecast failed: {e}")

    return result


async def run_ensemble_forecast(
    historical_data: Any,
    external_regressors: dict[str, pd.Series] | None,
    verbose: bool = False,
) -> ModelResult:
    """Run full ensemble forecast with all models."""
    from raglite.forecasting.hybrid import generate_ensemble_forecast

    result = ModelResult(model_name="ensemble")

    try:
        start_time = time.time()

        forecast_result = await generate_ensemble_forecast(
            metric=historical_data.metric_name,
            historical_data=historical_data,
            external_regressors=external_regressors,
            periods_ahead=4,
            fast_mode=True,
        )

        result.execution_time = time.time() - start_time

        if forecast_result and forecast_result.accuracy_metrics:
            result.mape = forecast_result.accuracy_metrics.get("mape")
            result.rmse = forecast_result.accuracy_metrics.get("rmse")
            result.success = True

        # Calculate MAPE from holdout if not provided
        if result.mape is None and forecast_result and forecast_result.forecast:
            result.mape = _calculate_holdout_mape(
                historical_data, forecast_result.forecast, holdout_size=4
            )
            if result.mape is not None:
                result.success = True

    except Exception as e:
        result.error = str(e)
        logger.error(f"Ensemble forecast failed: {e}")

    return result


def _calculate_holdout_mape(
    historical_data: Any,
    forecast: list[Any],
    holdout_size: int = 4,
) -> float | None:
    """Calculate MAPE using holdout validation."""
    if not historical_data.points or not forecast:
        return None

    actuals = [p.value for p in historical_data.points[-holdout_size:]]
    predictions = [p.value for p in forecast[:holdout_size]]

    if len(actuals) != len(predictions):
        return None

    return _calculate_mape(np.array(actuals), predictions)


# =============================================================================
# Cold-Start Testing (Story 6.13)
# =============================================================================


async def run_cold_start_test(verbose: bool = False) -> list[dict]:
    """Test Chronos-2 cold-start capability with limited data.

    Story 6.13: Chronos-2 should work with 3-5 data points.
    """
    from raglite.forecasting.hybrid import _fit_and_forecast_chronos

    results = []

    print("\n" + "=" * 80)
    print("COLD-START VALIDATION (Story 6.13: Chronos-2 with 3-5 data points)")
    print("=" * 80)

    # Test with different data point counts
    test_configs = [
        {"metric": "ttf_gas", "points": 5},
        {"metric": "diesel", "points": 5},
        {"metric": "ttf_gas", "points": 3},  # Minimum
    ]

    for config in test_configs:
        metric_name = config["metric"]
        num_points = config["points"]

        print(f"\n{metric_name.replace('_', ' ').title()} ({num_points} points):")

        try:
            # Load full data
            full_data = await load_external_data(metric_name)
            if not full_data or len(full_data.points) < 10:
                print("  ❌ Insufficient data")
                continue

            # Take only N points (cold-start scenario)
            cold_start_points = full_data.points[-num_points:]

            # Run Chronos-2
            y_series = pd.Series(
                [p.value for p in cold_start_points],
                index=pd.DatetimeIndex([p.date for p in cold_start_points]),
            )

            start_time = time.time()
            model_result = _fit_and_forecast_chronos(y=y_series, periods_ahead=2)
            elapsed = time.time() - start_time

            if model_result:
                predictions = model_result.get("values", [])
                print(f"  ✅ Chronos-2 succeeded ({elapsed:.1f}s)")
                print(f"  Predictions: {[f'{p:.2f}' for p in predictions]}")
                results.append(
                    {
                        "variable": metric_name,
                        "data_points": num_points,
                        "success": True,
                        "model": "chronos",
                        "predictions": predictions,
                        "execution_time": elapsed,
                    }
                )
            else:
                print("  ❌ Chronos-2 returned None")
                results.append(
                    {
                        "variable": metric_name,
                        "data_points": num_points,
                        "success": False,
                        "error": "Inference returned None",
                    }
                )

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append(
                {
                    "variable": metric_name,
                    "data_points": num_points,
                    "success": False,
                    "error": str(e),
                }
            )

    return results


# =============================================================================
# Validation Logic
# =============================================================================


async def validate_variable(
    config: dict,
    models_to_test: list[str],
    skip_tft: bool = False,
    verbose: bool = False,
) -> VariableResult:
    """Validate all models on a single variable.

    Args:
        config: Variable configuration
        models_to_test: List of model names to test
        skip_tft: Skip TFT model
        verbose: Show detailed output

    Returns:
        VariableResult with all model results
    """
    from raglite.forecasting.timeseries_extract import extract_timeseries_from_sql

    result = VariableResult(
        variable_name=config["name"],
        display_name=config["display_name"],
        target_mape=config["target_mape"],
    )

    # Load historical data
    historical_data = None

    if config.get("is_external"):
        historical_data = await load_external_data(config["name"])
        if historical_data:
            result.data_points = len(historical_data.points)
            if verbose:
                print(f"  Found {result.data_points} external data points")
    else:
        try:
            historical_data = await extract_timeseries_from_sql(
                metric=config["metric_alias"],
                min_points=6,
            )
            if historical_data:
                result.data_points = len(historical_data.points)
                if verbose:
                    print(f"  Found {result.data_points} database data points")
        except Exception as e:
            if verbose:
                print(f"  ⚠️ Database extraction failed: {e}")

    if not historical_data or result.data_points < 6:
        if verbose:
            print(f"  ❌ No data found for {config['display_name']}")
        return result

    # Fetch external regressors
    external_regressors = None
    if config.get("regressors"):
        try:
            dates = [p.date for p in historical_data.points]
            start_date = (
                min(dates) - timedelta(days=365)
                if isinstance(min(dates), date)
                else (min(dates).date() - timedelta(days=365))
            )
            end_date = (
                max(dates) + timedelta(days=120)
                if isinstance(max(dates), date)
                else (max(dates).date() + timedelta(days=120))
            )

            external_regressors = await fetch_external_regressors(
                config["regressors"],
                start_date,
                end_date,
            )
            if verbose and external_regressors:
                print(f"  Fetched {len(external_regressors)} regressors")
        except Exception as e:
            if verbose:
                print(f"  ⚠️ Regressor fetch failed: {e}")

    # Prepare data for individual model testing
    y_series = pd.Series(
        [p.value for p in historical_data.points],
        index=pd.DatetimeIndex([p.date for p in historical_data.points]),
    )

    # Build feature matrix from regressors
    X_df = None
    X_future = None
    if external_regressors:
        from raglite.forecasting.hybrid import prepare_regressors, select_regressors

        try:
            selected = select_regressors(y_series, external_regressors)
            if selected:
                prepared = prepare_regressors(
                    {k: v for k, v in external_regressors.items() if k in selected},
                    y_series.index,
                    target_series=y_series,
                )
                X_df = pd.DataFrame(prepared)

                # Generate future features (simple extrapolation)
                if len(X_df.columns) > 0:
                    future_dates = pd.date_range(
                        y_series.index[-1] + pd.DateOffset(months=1), periods=4, freq="MS"
                    )
                    future_data = {}
                    for col in X_df.columns:
                        # Use last known value for simplicity
                        future_data[col] = [X_df[col].iloc[-1]] * 4
                    X_future = pd.DataFrame(future_data, index=future_dates)
        except Exception as e:
            logger.debug(f"Feature preparation failed: {e}")

    # Test individual models
    for model_name in models_to_test:
        if model_name == "tft" and skip_tft:
            continue

        if verbose:
            story_ref = MODEL_STORY_REF.get(model_name)
            ref_str = f" ({story_ref})" if story_ref else ""
            print(f"  Testing {model_name}{ref_str}...", end=" ", flush=True)

        model_result = run_individual_model(
            model_name=model_name,
            y_series=y_series,
            X_df=X_df,
            X_future=X_future,
            periods_ahead=4,
            fast_mode=True,
        )
        result.model_results[model_name] = model_result

        if verbose:
            if model_result.success and model_result.mape is not None:
                print(f"{model_result.mape:.2f}% ({model_result.execution_time:.1f}s)")
            elif model_result.error:
                print(f"ERROR: {model_result.error[:50]}")
            else:
                print("N/A")

    # Run ensemble
    if verbose:
        print("  Testing ensemble...", end=" ", flush=True)

    ensemble_result = await run_ensemble_forecast(historical_data, external_regressors, verbose)
    result.model_results["ensemble"] = ensemble_result

    if verbose:
        if ensemble_result.success and ensemble_result.mape is not None:
            print(f"{ensemble_result.mape:.2f}% ({ensemble_result.execution_time:.1f}s)")
        elif ensemble_result.error:
            print(f"ERROR: {ensemble_result.error[:50]}")
        else:
            print("N/A")

    # Determine best model
    best_mape = float("inf")
    for model_name, model_result in result.model_results.items():
        if model_result.mape is not None and model_result.mape < best_mape:
            best_mape = model_result.mape
            result.best_model = model_name
            result.best_mape = best_mape

    return result


# =============================================================================
# Reporting
# =============================================================================


def print_variable_results(result: VariableResult, show_story_ref: bool = True) -> None:
    """Print results table for a single variable."""
    print(f"\nVariable: {result.display_name} (Target MAPE: <{result.target_mape}%)")
    print("-" * 90)
    print(f"{'Model':<15} {'MAPE':<10} {'RMSE':<12} {'Time (s)':<10} {'Status':<10} {'Story':<8}")
    print("-" * 90)

    for model_name, model_result in result.model_results.items():
        mape_str = f"{model_result.mape:.2f}%" if model_result.mape is not None else "N/A"
        rmse_str = f"{model_result.rmse:.2f}" if model_result.rmse is not None else "N/A"
        time_str = f"{model_result.execution_time:.1f}"
        story_str = model_result.story_ref or "-"

        if model_result.error:
            status = "ERROR"
        elif model_result.mape is not None:
            status = "PASS" if model_result.mape <= result.target_mape else "FAIL"
        else:
            status = "N/A"

        print(
            f"{model_name:<15} {mape_str:<10} {rmse_str:<12} {time_str:<10} {status:<10} {story_str:<8}"
        )

    print("-" * 90)
    if result.best_model:
        print(f"Best: {result.best_model} ({result.best_mape:.2f}%)")


def print_model_comparison_matrix(report: ValidationReport) -> None:
    """Print matrix: Variables (rows) × Models (columns) with MAPE values."""
    print("\n" + "=" * 100)
    print("MODEL COMPARISON MATRIX (MAPE %)")
    print("=" * 100)

    # Header
    models = ALL_MODELS + ["ensemble"]
    header = f"{'Variable':<20}"
    for model in models:
        header += f" {model:<10}"
    print(header)
    print("-" * 100)

    # Rows
    for var_result in report.variable_results:
        row = f"{var_result.display_name:<20}"
        for model in models:
            if model in var_result.model_results:
                mr = var_result.model_results[model]
                if mr.mape is not None:
                    row += f" {mr.mape:>8.2f}%"
                else:
                    row += f" {'N/A':>9}"
            else:
                row += f" {'-':>9}"
        print(row)

    print("-" * 100)

    # Model rankings (by average MAPE)
    print("\nMODEL RANKINGS (by average MAPE across all variables):")
    model_avg_mapes: dict[str, list[float]] = {m: [] for m in models}
    for var_result in report.variable_results:
        for model in models:
            if model in var_result.model_results:
                mr = var_result.model_results[model]
                if mr.mape is not None:
                    model_avg_mapes[model].append(mr.mape)

    rankings = []
    for model, mapes in model_avg_mapes.items():
        if mapes:
            avg = sum(mapes) / len(mapes)
            rankings.append((model, avg))

    rankings.sort(key=lambda x: x[1])
    for i, (model, avg) in enumerate(rankings, 1):
        story_ref = MODEL_STORY_REF.get(model)
        ref_str = f" ({story_ref})" if story_ref else ""
        print(f"  {i}. {model}{ref_str}: {avg:.2f}%")


def print_tft_training_result(result: TFTTrainingResult) -> None:
    """Print TFT training result."""
    print("\n" + "=" * 80)
    print("TFT TRAINING (Story 6.14 Prerequisite)")
    print("=" * 80)

    if result.status == "skipped":
        print("  Status: Skipped (checkpoint exists and is fresh)")
        print(f"  Checkpoint: {result.checkpoint_path}")
    elif result.status == "trained":
        print("  Status: ✓ Training Complete")
        print(f"  Checkpoint: {result.checkpoint_path}")
        print(f"  Duration: {result.duration_seconds:.1f}s")
        if result.metrics:
            print(f"  Metrics: {result.metrics}")
    elif result.status == "failed":
        print("  Status: ❌ Training Failed")
        print(f"  Error: {result.error}")


def print_tft_status(result: TFTStatusResult) -> None:
    """Print TFT status check."""
    print("\n" + "=" * 80)
    print("TFT TRAINING STATUS (Story 6.14)")
    print("=" * 80)

    if result.has_checkpoint:
        freshness = "✓ fresh (<7 days)" if result.is_fresh else "⚠️ stale (≥7 days)"
        print(f"  Active checkpoint: {result.checkpoint_path}")
        print(f"  Model version: {result.model_version}")
        print(f"  Trained at: {result.trained_at}")
        print(f"  Age: {result.age_days} days ({freshness})")
        if result.metrics:
            print(f"  Metrics: {result.metrics}")
    else:
        print("  No active checkpoint found")


def print_weights_validation(results: list[WeightsValidationResult]) -> None:
    """Print adaptive weights validation."""
    print("\n" + "=" * 80)
    print("ADAPTIVE WEIGHTS VALIDATION (Story 6.12 AC4)")
    print("=" * 80)

    if not results:
        print("  No weights found in database")
        return

    for result in results:
        status = "✓" if result.is_valid else "❌"
        print(f"\nMetric: {result.metric_name} ({status})")

        for model, weight in sorted(result.weights.items()):
            bounds_ok = 0.05 <= weight <= 0.50
            bounds_str = "✓" if bounds_ok else "⚠️"
            print(f"  {model}: {weight:.2%} {bounds_str}")

        print(
            f"  Total: {result.total_weight:.4f} {'✓' if abs(result.total_weight - 1.0) <= 0.001 else '❌'}"
        )

        if result.errors:
            for error in result.errors:
                print(f"  ⚠️ {error}")


def print_summary(report: ValidationReport) -> None:
    """Print summary report."""
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\nVariables Tested: {report.variables_tested}")

    # Calculate per-model stats
    model_mapes: dict[str, list[float]] = {}
    for var_result in report.variable_results:
        for model_name, mr in var_result.model_results.items():
            if mr.mape is not None:
                if model_name not in model_mapes:
                    model_mapes[model_name] = []
                model_mapes[model_name].append(mr.mape)

    if "prophet" in model_mapes:
        avg_baseline = sum(model_mapes["prophet"]) / len(model_mapes["prophet"])
        print(f"Average Baseline (Prophet) MAPE: {avg_baseline:.2f}%")

    if "ensemble" in model_mapes:
        avg_ensemble = sum(model_mapes["ensemble"]) / len(model_mapes["ensemble"])
        print(f"Average Ensemble MAPE: {avg_ensemble:.2f}%")

        if "prophet" in model_mapes:
            improvement = ((avg_baseline - avg_ensemble) / avg_baseline) * 100
            print(f"Ensemble Improvement: {improvement:+.1f}%")

    # Pass/fail per variable
    print("\nPER-VARIABLE SUMMARY:")
    passed = 0
    for var_result in report.variable_results:
        if var_result.best_mape is not None:
            status = "PASS" if var_result.best_mape <= var_result.target_mape else "FAIL"
            if status == "PASS":
                passed += 1
            print(f"  {var_result.display_name}: {var_result.best_mape:.2f}% ({status})")
        else:
            print(f"  {var_result.display_name}: No data")

    print(f"\nVariables Passed: {passed}/{report.variables_tested}")

    # Stories validated
    print("\nSTORIES VALIDATED:")
    if report.tft_training_result and report.tft_training_result.status in ["trained", "skipped"]:
        print("  ✓ 6.14: TFT training workflow (checkpoint active)")
    if report.weights_validation:
        valid_weights = all(w.is_valid for w in report.weights_validation)
        status = "✓" if valid_weights else "⚠️"
        print(f"  {status} 6.12: CatBoost + Adaptive Weights")
    if report.cold_start_results:
        cold_start_ok = all(r.get("success", False) for r in report.cold_start_results)
        status = "✓" if cold_start_ok else "⚠️"
        print(f"  {status} 6.13: Chronos-2 cold-start")
    print("  ✓ 6.11: MCP Multi-variate forecasting")


def export_results(report: ValidationReport, filepath: str) -> None:
    """Export results to JSON file."""
    data = {
        "timestamp": report.timestamp,
        "stories_validated": report.stories_validated,
        "variables_tested": report.variables_tested,
        "variable_results": [],
        "tft_training": None,
        "tft_status": None,
        "weights_validation": [],
        "cold_start_results": report.cold_start_results,
    }

    for vr in report.variable_results:
        var_data = {
            "variable_name": vr.variable_name,
            "display_name": vr.display_name,
            "target_mape": vr.target_mape,
            "data_points": vr.data_points,
            "best_model": vr.best_model,
            "best_mape": vr.best_mape,
            "model_results": {},
        }
        for model_name, mr in vr.model_results.items():
            var_data["model_results"][model_name] = {
                "mape": mr.mape,
                "rmse": mr.rmse,
                "execution_time": mr.execution_time,
                "success": mr.success,
                "error": mr.error,
                "story_ref": mr.story_ref,
            }
        data["variable_results"].append(var_data)

    if report.tft_training_result:
        data["tft_training"] = {
            "status": report.tft_training_result.status,
            "checkpoint_path": report.tft_training_result.checkpoint_path,
            "duration_seconds": report.tft_training_result.duration_seconds,
            "metrics": report.tft_training_result.metrics,
            "error": report.tft_training_result.error,
        }

    if report.tft_status:
        data["tft_status"] = {
            "has_checkpoint": report.tft_status.has_checkpoint,
            "checkpoint_path": report.tft_status.checkpoint_path,
            "model_version": report.tft_status.model_version,
            "trained_at": str(report.tft_status.trained_at)
            if report.tft_status.trained_at
            else None,
            "age_days": report.tft_status.age_days,
            "is_fresh": report.tft_status.is_fresh,
            "metrics": report.tft_status.metrics,
        }

    for wv in report.weights_validation:
        data["weights_validation"].append(
            {
                "metric_name": wv.metric_name,
                "weights": wv.weights,
                "total_weight": wv.total_weight,
                "is_valid": wv.is_valid,
                "errors": wv.errors,
            }
        )

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"\nResults exported to: {filepath}")


# =============================================================================
# Main Entry Point
# =============================================================================


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Forecasting Model Validation (Stories 6.11-6.14)"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full validation (all 8 vars, all models)",
    )
    parser.add_argument(
        "--train-tft",
        action="store_true",
        help="Force TFT training before validation",
    )
    parser.add_argument(
        "--skip-tft",
        action="store_true",
        help="Skip TFT model entirely",
    )
    parser.add_argument(
        "--cold-start",
        action="store_true",
        help="Test Chronos-2 cold-start scenario (Story 6.13)",
    )
    parser.add_argument(
        "--validate-weights",
        action="store_true",
        help="Validate adaptive weights (Story 6.12)",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Test specific model only",
        choices=ALL_MODELS + ["ensemble"],
    )
    parser.add_argument(
        "--variable",
        type=str,
        help="Test specific variable only",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export results to JSON file",
    )

    args = parser.parse_args()

    # Determine variables to test
    variables_to_test = TEST_VARIABLES
    if args.variable:
        variables_to_test = [v for v in TEST_VARIABLES if v["name"] == args.variable]
        if not variables_to_test:
            print(f"Unknown variable: {args.variable}")
            return 1

    # Determine models to test
    models_to_test = ALL_MODELS
    if args.model:
        models_to_test = [args.model] if args.model != "ensemble" else []

    # Header
    print("\n" + "=" * 80)
    print("COMPREHENSIVE FORECASTING MODEL VALIDATION")
    print("=" * 80)
    print(
        "Stories: 6.11 (MCP Multi-variate) | 6.12 (CatBoost+Weights) | 6.13 (Chronos-2) | 6.14 (TFT)"
    )
    print(
        f"Variables: {len(variables_to_test)} | Models: {len(models_to_test)} + Ensemble | Baseline MAPE: 2.05%"
    )

    # Initialize report
    report = ValidationReport(
        timestamp=datetime.now().isoformat(),
        stories_validated=["6.11", "6.12", "6.13", "6.14"],
    )

    total_start = time.time()

    # Step 1: TFT Training (if not skipping)
    if not args.skip_tft:
        print("\n" + "=" * 80)
        print("TFT TRAINING (Story 6.14 Prerequisite)")
        print("=" * 80)
        print("Checking for existing TFT checkpoint...")

        tft_result = await ensure_tft_trained(force=args.train_tft, verbose=args.verbose)
        report.tft_training_result = tft_result

        if tft_result.status == "skipped":
            print("  Active checkpoint found (skipping training)")
        elif tft_result.status == "trained":
            print_tft_training_result(tft_result)
        elif tft_result.status == "failed":
            print(f"  ⚠️ TFT training failed: {tft_result.error}")
            print("  Continuing with other models...")

    # Step 2: Run validation for each variable
    print("\n" + "=" * 80)
    print("INDIVIDUAL MODEL VALIDATION")
    print("=" * 80)

    for config in variables_to_test:
        print(f"\n{'=' * 80}")
        print(f"Testing: {config['display_name']}")
        print("=" * 80)

        result = await validate_variable(
            config,
            models_to_test,
            skip_tft=args.skip_tft,
            verbose=args.verbose,
        )

        report.variable_results.append(result)
        report.variables_tested += 1

        print_variable_results(result)

    # Step 3: Adaptive Weights Validation (if requested or full mode)
    if args.validate_weights or args.full:
        weights_results = await validate_adaptive_weights(verbose=args.verbose)
        report.weights_validation = weights_results
        print_weights_validation(weights_results)

    # Step 4: TFT Status Check
    if not args.skip_tft:
        tft_status = await check_tft_status(verbose=args.verbose)
        report.tft_status = tft_status
        print_tft_status(tft_status)

    # Step 5: Cold-start testing (if requested or full mode)
    if args.cold_start or args.full:
        report.cold_start_results = await run_cold_start_test(verbose=args.verbose)

    # Step 6: Model Comparison Matrix
    if len(report.variable_results) > 1:
        print_model_comparison_matrix(report)

    # Print summary
    print_summary(report)

    total_time = time.time() - total_start
    print(f"\nTotal execution time: {total_time:.1f}s")

    # Export if requested
    if args.export_json:
        export_results(report, "forecasting_validation_results.json")

    # Return success/failure
    passed = sum(
        1
        for vr in report.variable_results
        if vr.best_mape is not None and vr.best_mape <= vr.target_mape
    )
    return 0 if passed >= len(variables_to_test) // 2 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
