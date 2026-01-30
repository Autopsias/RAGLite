"""Admin MCP tools."""

import time
from datetime import UTC, date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from raglite.forecasting.backtest_job import trigger_backtest_now
from raglite.main import mcp
from raglite.mcp.models import ModelWeightAdminRequest, ModelWeightAdminResponse
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class WarmupResult(BaseModel):
    """Result from forecasting model warmup operation."""

    status: str = Field(description="Overall warmup status: 'success', 'partial', 'failed'")
    prophet_loaded: bool = Field(default=False, description="Whether Prophet model was loaded")
    prophet_load_time: float | None = Field(
        default=None, description="Prophet load time in seconds"
    )
    tft_loaded: bool = Field(default=False, description="Whether TFT model was loaded")
    tft_load_time: float | None = Field(default=None, description="TFT load time in seconds")
    chronos_loaded: bool = Field(default=False, description="Whether Chronos model was loaded")
    chronos_load_time: float | None = Field(
        default=None, description="Chronos load time in seconds"
    )
    database_connected: bool = Field(
        default=False, description="Whether database connection is active"
    )
    database_warmup_time: float | None = Field(
        default=None, description="DB warmup time in seconds"
    )
    total_warmup_time: float = Field(description="Total warmup time in seconds")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")
    message: str = Field(description="Human-readable summary")


@mcp.tool()
async def manage_model_weights(request: ModelWeightAdminRequest) -> str:
    """Manage adaptive model weights for ensemble forecasting.
    Story 6.12 AC5: Admin tool for viewing, triggering backtest, and resetting weights.
    Actions:
    - 'view': Display current weights from PostgreSQL (or static defaults if none stored)
    - 'run_backtest': Trigger immediate backtest job to recalculate weights
    - 'reset': Delete stored weights and revert to static configuration defaults
    Examples:
        manage_model_weights(action='view')
        -> Shows all model weights across all metrics
        manage_model_weights(action='view', metric='cement_demand')
        -> Shows weights only for cement_demand
        manage_model_weights(action='run_backtest')
        -> Triggers immediate backtest calculation
        manage_model_weights(action='reset', metric='cement_demand')
        -> Deletes cement_demand weights, reverts to config.py defaults
    Args:
        request: ModelWeightAdminRequest with action and optional metric filter
    Returns:
        JSON string with ModelWeightAdminResponse
    """
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.forecasting.adaptive_weights import _get_static_weights
    from raglite.shared.database import get_session

    logger.info(
        "Model weight admin action",
        extra={"action": request.action, "metric": request.metric},
    )
    try:
        session = get_session()
        storage = ExternalDataStorage(session)
        if request.action == "view":
            db_weights = storage.get_model_weights(request.metric)
            if db_weights:
                weights_data = [
                    {
                        "metric_name": w.metric_name,
                        "model_name": w.model_name,
                        "weight": float(w.weight),
                        "backtest_rmse": float(w.backtest_rmse) if w.backtest_rmse else None,
                        "backtest_mape": float(w.backtest_mape) if w.backtest_mape else None,
                        "calculated_at": w.calculated_at.isoformat() if w.calculated_at else None,
                    }
                    for w in db_weights
                ]
                message = f"Found {len(weights_data)} weight entries in database"
            else:
                static = _get_static_weights()
                weights_data = [
                    {
                        "metric_name": "default",
                        "model_name": k,
                        "weight": v,
                        "source": "static_config",
                    }
                    for k, v in static.items()
                ]
                message = "No adaptive weights stored - showing static defaults from config"
            session.close()
            return ModelWeightAdminResponse(
                action="view",
                success=True,
                message=message,
                weights=weights_data,
            ).model_dump_json(indent=2)
        elif request.action == "run_backtest":
            session.close()
            backtest_result = await trigger_backtest_now(
                metrics=[request.metric] if request.metric else None
            )
            return ModelWeightAdminResponse(
                action="run_backtest",
                success=True,
                message="Backtest job triggered",
                backtest_status=backtest_result,
            ).model_dump_json(indent=2)
        elif request.action == "reset":
            deleted_count = storage.delete_model_weights(request.metric)
            session.close()
            return ModelWeightAdminResponse(
                action="reset",
                success=True,
                message=f"Deleted {deleted_count} weight entries. Using static defaults.",
            ).model_dump_json(indent=2)
        else:
            session.close()
            return ModelWeightAdminResponse(
                action=request.action,
                success=False,
                message=f"Unknown action: {request.action}. Use 'view', 'run_backtest', or 'reset'.",
            ).model_dump_json(indent=2)
    except Exception as e:
        logger.error(f"Model weight admin failed: {e}", exc_info=True)
        return ModelWeightAdminResponse(
            action=request.action,
            success=False,
            message=f"Error: {e}",
        ).model_dump_json(indent=2)


def _parse_model_list(models: str) -> list[str]:
    """Parse and validate model list from comma-separated string.

    Args:
        models: Comma-separated model names or 'all'

    Returns:
        List of validated model names

    Raises:
        ValueError: If invalid model names provided
    """
    if models == "all":
        model_list = ["tft"]
    else:
        model_list = [m.strip() for m in models.split(",")]

    valid_models = {"tft"}
    invalid = [m for m in model_list if m not in valid_models]
    if invalid:
        raise ValueError(f"Invalid model names: {invalid}. Valid options: {valid_models}")

    return model_list


def _check_checkpoint_freshness(
    storage: Any, model_list: list[str], force: bool, start_time: float
) -> str | None:
    """Check if checkpoint is recent enough to skip training.

    Args:
        storage: ExternalDataStorage instance
        model_list: List of models to train
        force: If True, skip freshness check
        start_time: Training start time for duration calculation

    Returns:
        JSON response string if training should be skipped, None otherwise
    """
    import time

    from raglite.external_data.models import RetrainResult

    if force or "tft" not in model_list:
        return None

    active_checkpoint = storage.get_active_model("tft")
    if not active_checkpoint:
        return None

    # Ensure both datetimes are timezone-aware for comparison
    # Database returns naive datetime, so we make it timezone-aware
    trained_at = active_checkpoint.trained_at
    if trained_at.tzinfo is None:
        trained_at = trained_at.replace(tzinfo=UTC)
    age = datetime.now(UTC) - trained_at
    if age >= timedelta(days=settings.tft_checkpoint_freshness_days):
        return None

    logger.info(
        "TFT checkpoint is recent - skipping training",
        extra={
            "checkpoint_age_days": age.days,
            "freshness_threshold": settings.tft_checkpoint_freshness_days,
        },
    )
    return RetrainResult(
        status="skipped",
        models_trained=[],
        checkpoint_path=active_checkpoint.checkpoint_path,
        metrics={"checkpoint_age_days": age.days},
        duration_seconds=time.time() - start_time,
        errors=[f"TFT checkpoint is recent ({age.days} days old), use force=True to retrain"],
    ).model_dump_json(indent=2)


def _collect_training_data(storage: Any) -> list[dict] | None:
    """Collect historical data from all external data sources.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        List of data points for training, or None if no data available
    """
    from raglite.external_data.orm_models import ExternalDataSourceORM
    from raglite.shared.database import get_session

    MIN_DATA_POINTS = 24
    session = get_session()
    sources = (
        session.query(ExternalDataSourceORM)
        .filter(ExternalDataSourceORM.deleted_at.is_(None))
        .all()
    )

    if not sources:
        logger.warning("No external data sources found - skipping TFT training")
        return None

    all_data = []
    end_date = date.today()
    buffer_days = settings.regressor_buffer_years * 365
    start_date = end_date - timedelta(days=buffer_days)

    for source in sources:
        try:
            metric_names = storage.get_metrics_for_source(source.source_name)
            for metric in metric_names:
                data_points = storage.query_data_range(
                    source_name=source.source_name,
                    start_date=start_date,
                    end_date=end_date,
                    metric_name=metric,
                )
                if len(data_points) >= MIN_DATA_POINTS:
                    for idx, point in enumerate(data_points):
                        all_data.append(
                            {
                                "metric_name": f"{source.source_name}_{metric}",
                                "date": point.date,
                                "value": point.value,
                                "time_idx": idx,
                            }
                        )
                    logger.info(
                        f"Included metric: {source.source_name}_{metric} ({len(data_points)} points)"
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch data for source {source.source_name}: {e}")
            continue

    if not all_data:
        logger.warning("No metrics with sufficient historical data - skipping TFT training")
        return None

    return all_data


def _train_tft_model(
    training_data: list[dict],
) -> tuple[str | None, dict[str, float | str], list[str]]:
    """Train TFT model with provided data.

    Args:
        training_data: List of training data points

    Returns:
        Tuple of (checkpoint_path, metrics, errors)
    """
    import pandas as pd

    from raglite.forecasting.tft_training import (
        prepare_tft_dataset,
        save_tft_checkpoint,
        train_tft_model,
    )

    checkpoint_path: str | None = None
    metrics: dict[str, float | str] = {}
    errors: list[str] = []

    try:
        df = pd.DataFrame(training_data)
        logger.info(f"Preparing TFT datasets with {len(df)} total data points")
        training_dataset, validation_dataset = prepare_tft_dataset(
            df=df,
            target_column="value",
            group_column="metric_name",
            time_column="time_idx",
        )
        logger.info("Starting TFT model training")
        tft_model, train_metrics = train_tft_model(
            training_dataset=training_dataset,
            validation_dataset=validation_dataset,
        )
        checkpoint_path = save_tft_checkpoint(
            model=tft_model,
            metrics=train_metrics,
        )
        metrics.update(train_metrics)
        metrics["training_samples"] = len(training_dataset)
        metrics["validation_samples"] = len(validation_dataset)
        logger.info(
            "TFT training completed successfully",
            extra={
                "checkpoint_path": checkpoint_path,
                "metrics": train_metrics,
            },
        )
    except Exception as e:
        logger.error(f"TFT training failed: {e}", exc_info=True)
        errors.append(f"TFT training failed: {str(e)}")

    return checkpoint_path, metrics, errors


def _determine_training_status(models_trained: list[str], model_list: list[str]) -> str:
    """Determine overall training status based on results.

    Args:
        models_trained: List of successfully trained models
        model_list: List of models that were requested for training

    Returns:
        Status string: 'success', 'partial', or 'failed'
    """
    if len(models_trained) == len(model_list):
        return "success"
    elif len(models_trained) > 0:
        return "partial"
    else:
        return "failed"


@mcp.tool()
async def retrain_forecasting_models(
    models: str = "tft",
    force: bool = False,
) -> str:
    """Retrain forecasting models with latest external data.

    Args:
        models: Comma-separated model names or 'all' (default: 'tft')
        force: If True, bypass checkpoint freshness check (default: False)

    Returns:
        JSON string with RetrainResult containing status, metrics, and errors

    Examples:
        retrain_forecasting_models()
        -> Train TFT model if checkpoint is stale

        retrain_forecasting_models(force=True)
        -> Force retrain TFT model even if checkpoint is recent

        retrain_forecasting_models(models='all')
        -> Train all available models
    """
    import time

    from raglite.external_data.models import RetrainResult
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.shared.database import get_session

    logger.info(
        "Manual model retraining triggered",
        extra={"models": models, "force": force},
    )
    start_time = time.time()
    errors: list[str] = []
    models_trained: list[str] = []
    checkpoint_path: str | None = None
    metrics: dict[str, float | str] = {}

    try:
        model_list = _parse_model_list(models)

        session = get_session()
        storage = ExternalDataStorage(session)

        skip_response = _check_checkpoint_freshness(
            storage=storage,
            model_list=model_list,
            force=force,
            start_time=start_time,
        )
        if skip_response:
            return skip_response

        if "tft" in model_list:
            training_data = _collect_training_data(storage)
            if training_data is None:
                errors.append("No external data sources or insufficient historical data")
            else:
                checkpoint_path, train_metrics, train_errors = _train_tft_model(training_data)
                if checkpoint_path:
                    models_trained.append("tft")
                    metrics.update(train_metrics)
                errors.extend(train_errors)

        status = _determine_training_status(models_trained, model_list)
        duration = time.time() - start_time

        return RetrainResult(
            status=status,
            models_trained=models_trained,
            checkpoint_path=checkpoint_path,
            metrics=metrics,
            duration_seconds=duration,
            errors=errors,
        ).model_dump_json(indent=2)
    except Exception as e:
        logger.error(f"Model retraining failed: {e}")
        duration = time.time() - start_time
        return RetrainResult(
            status="failed",
            models_trained=[],
            checkpoint_path=None,
            metrics={},
            duration_seconds=duration,
            errors=[str(e)],
        ).model_dump_json(indent=2)


def _warmup_prophet() -> tuple[bool, float | None, str | None]:
    """Load Prophet model and return status.

    Returns:
        Tuple of (success, load_time_seconds, error_message)
    """
    try:
        start = time.time()
        from prophet import Prophet  # noqa: F401

        elapsed = time.time() - start
        return True, elapsed, None
    except ImportError:
        return False, None, "Prophet not installed"
    except Exception as e:
        return False, None, str(e)


def _warmup_tft() -> tuple[bool, float | None, str | None]:
    """Load TFT model checkpoint and return status.

    Returns:
        Tuple of (success, load_time_seconds, error_message)
    """
    try:
        import asyncio

        from raglite.forecasting.models.tft_model import _get_tft_model_with_timeout

        start = time.time()
        loop = asyncio.new_event_loop()
        try:
            model = loop.run_until_complete(
                _get_tft_model_with_timeout(timeout=settings.tft_preload_timeout)
            )
            elapsed = time.time() - start
            if model is not None:
                return True, elapsed, None
            else:
                return False, elapsed, "No TFT checkpoint available"
        finally:
            loop.close()
    except ImportError:
        return False, None, "pytorch-forecasting not installed"
    except Exception as e:
        return False, None, str(e)


def _warmup_chronos() -> tuple[bool, float | None, str | None]:
    """Load Chronos model and return status.

    Returns:
        Tuple of (success, load_time_seconds, error_message)
    """
    try:
        start = time.time()
        # Import the Chronos model to trigger download/caching
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        model_name = settings.chronos_model_name
        # This will download/cache the model if not already present
        AutoTokenizer.from_pretrained(model_name)
        AutoModelForSeq2SeqLM.from_pretrained(model_name)
        elapsed = time.time() - start
        return True, elapsed, None
    except ImportError:
        return False, None, "transformers not installed"
    except Exception as e:
        return False, None, str(e)


def _warmup_database() -> tuple[bool, float | None, str | None]:
    """Warm database connection pool and return status.

    Returns:
        Tuple of (success, warmup_time_seconds, error_message)
    """
    try:
        from sqlalchemy import text

        from raglite.shared.database import get_session

        start = time.time()
        session = get_session()
        session.execute(text("SELECT 1"))
        session.close()
        elapsed = time.time() - start
        return True, elapsed, None
    except Exception as e:
        return False, None, str(e)


@mcp.tool()
async def warmup_forecasting_models(
    include_chronos: bool = False,
) -> str:
    """Manually warm up forecasting models and database connections.

    Use this tool ONCE after server start (or after long idle periods) to ensure
    forecasting tools respond quickly. This preloads:
    - Prophet model (avoids 3-5s import delay)
    - TFT model checkpoint (avoids 5-25s loading delay)
    - Chronos model (optional, avoids 5-10s download delay)
    - Database connection pool (avoids 0.5-2s connection delay)

    **When to use:**
    - After server restart
    - Before critical forecast requests
    - If forecasts have been timing out

    **Note:** Prophet and TFT are automatically preloaded at server startup.
    Use this tool to verify warmup status or to manually trigger warmup
    if automatic preloading failed.

    Args:
        include_chronos: If True, also warm up Chronos model (adds 5-10s)

    Returns:
        JSON string with WarmupResult containing status of each component
    """
    logger.info(
        "Manual forecasting warmup triggered",
        extra={"include_chronos": include_chronos},
    )

    total_start = time.time()
    errors: list[str] = []

    # Warmup Prophet
    prophet_loaded, prophet_time, prophet_err = _warmup_prophet()
    if prophet_err:
        errors.append(f"Prophet: {prophet_err}")

    # Warmup TFT
    tft_loaded, tft_time, tft_err = _warmup_tft()
    if tft_err:
        errors.append(f"TFT: {tft_err}")

    # Warmup Chronos (optional)
    chronos_loaded, chronos_time, chronos_err = False, None, None
    if include_chronos:
        chronos_loaded, chronos_time, chronos_err = _warmup_chronos()
        if chronos_err:
            errors.append(f"Chronos: {chronos_err}")

    # Warmup database
    db_connected, db_time, db_err = _warmup_database()
    if db_err:
        errors.append(f"Database: {db_err}")

    total_time = time.time() - total_start

    # Determine overall status
    core_loaded = prophet_loaded and db_connected
    if core_loaded and tft_loaded:
        status = "success"
    elif core_loaded:
        status = "partial"
    else:
        status = "failed"

    # Build human-readable message
    loaded_models = []
    if prophet_loaded:
        loaded_models.append("Prophet")
    if tft_loaded:
        loaded_models.append("TFT")
    if chronos_loaded:
        loaded_models.append("Chronos")

    if status == "success":
        message = f"Forecasting models ready: {', '.join(loaded_models)}. DB connected."
    elif status == "partial":
        message = (
            f"Partial warmup: {', '.join(loaded_models) or 'none'} loaded. Some models unavailable."
        )
    else:
        message = "Warmup failed. Check errors for details."

    result = WarmupResult(
        status=status,
        prophet_loaded=prophet_loaded,
        prophet_load_time=round(prophet_time, 2) if prophet_time else None,
        tft_loaded=tft_loaded,
        tft_load_time=round(tft_time, 2) if tft_time else None,
        chronos_loaded=chronos_loaded,
        chronos_load_time=round(chronos_time, 2) if chronos_time else None,
        database_connected=db_connected,
        database_warmup_time=round(db_time, 2) if db_time else None,
        total_warmup_time=round(total_time, 2),
        errors=errors,
        message=message,
    )

    logger.info(
        "Forecasting warmup complete",
        extra={
            "status": status,
            "prophet_loaded": prophet_loaded,
            "tft_loaded": tft_loaded,
            "chronos_loaded": chronos_loaded,
            "db_connected": db_connected,
            "total_time": round(total_time, 2),
        },
    )

    return result.model_dump_json(indent=2)
