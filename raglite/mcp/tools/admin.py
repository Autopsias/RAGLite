"""Admin MCP tools."""

from datetime import UTC, date, datetime, timedelta

from raglite.forecasting.backtest_job import trigger_backtest_now
from raglite.main import mcp
from raglite.mcp.models import ModelWeightAdminRequest, ModelWeightAdminResponse
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


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


@mcp.tool()
async def retrain_forecasting_models(
    models: str = "tft",
    force: bool = False,
) -> str:
    import time

    from raglite.external_data.models import RetrainResult
    from raglite.external_data.storage import ExternalDataStorage

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
        if models == "all":
            model_list = ["tft"]
        else:
            model_list = [m.strip() for m in models.split(",")]
        valid_models = {"tft"}
        invalid = [m for m in model_list if m not in valid_models]
        if invalid:
            raise ValueError(f"Invalid model names: {invalid}. Valid options: {valid_models}")
        from raglite.shared.database import get_session

        session = get_session()
        storage = ExternalDataStorage(session)
        if not force and "tft" in model_list:
            active_checkpoint = storage.get_active_model("tft")
            if active_checkpoint:
                age = datetime.now(UTC) - active_checkpoint.trained_at
                if age < timedelta(days=settings.tft_checkpoint_freshness_days):
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
                        errors=[
                            f"TFT checkpoint is recent ({age.days} days old), use force=True to retrain"
                        ],
                    ).model_dump_json(indent=2)
        if "tft" in model_list:
            try:
                import pandas as pd

                from raglite.external_data.orm_models import ExternalDataSourceORM
                from raglite.forecasting.tft_training import (
                    prepare_tft_dataset,
                    save_tft_checkpoint,
                    train_tft_model,
                )
                from raglite.shared.database import get_session

                MIN_DATA_POINTS = 24
                session = get_session()
                storage_instance = ExternalDataStorage(session)
                sources = (
                    session.query(ExternalDataSourceORM)
                    .filter(ExternalDataSourceORM.deleted_at.is_(None))
                    .all()
                )
                if not sources:
                    logger.warning("No external data sources found - skipping TFT training")
                    errors.append("No external data sources available")
                else:
                    all_data = []
                    end_date = date.today()
                    buffer_days = settings.regressor_buffer_years * 365
                    start_date = end_date - timedelta(days=buffer_days)
                    for source in sources:
                        try:
                            metric_names = storage_instance.get_metrics_for_source(
                                source.source_name
                            )
                            for metric in metric_names:
                                data_points = storage_instance.query_data_range(
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
                            logger.warning(
                                f"Failed to fetch data for source {source.source_name}: {e}"
                            )
                            continue
                    if not all_data:
                        logger.warning(
                            "No metrics with sufficient historical data - skipping TFT training"
                        )
                        errors.append("No metrics with sufficient historical data (>=24 months)")
                    else:
                        df = pd.DataFrame(all_data)
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
                        models_trained.append("tft")
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
        if len(models_trained) == len(model_list):
            status = "success"
        elif len(models_trained) > 0:
            status = "partial"
        else:
            status = "failed"
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
