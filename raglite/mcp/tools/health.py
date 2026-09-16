"""Health MCP tools."""

import json
import sys

from pydantic import BaseModel, Field

from raglite.main import mcp
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class ForecastReadinessResult(BaseModel):
    """Result from forecast readiness check."""

    is_ready: bool = Field(description="Whether forecasting is ready for immediate use")
    prophet_ready: bool = Field(default=False, description="Prophet module is importable")
    tft_ready: bool = Field(default=False, description="TFT checkpoint is loaded in memory")
    tft_checkpoint_exists: bool = Field(default=False, description="TFT checkpoint file exists")
    chronos_ready: bool = Field(default=False, description="Chronos model is available")
    database_ready: bool = Field(default=False, description="Database connection is active")
    estimated_first_forecast_time: str = Field(
        description="Estimated time for first forecast (e.g., '<5s' or '30-50s')"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Actions to improve readiness"
    )
    details: dict = Field(default_factory=dict, description="Additional diagnostic details")


@mcp.tool()
async def check_database_health() -> str:
    """Check data synchronization between Qdrant and PostgreSQL.
    Validates that all documents ingested into Qdrant also have their table data
    stored in PostgreSQL. Detects data drift caused by:
    - Snapshot restorations without PostgreSQL sync
    - Table extraction failures during ingestion
    - Partial ingestion runs
    Returns a detailed integrity report with:
    - Document counts per database
    - List of any missing documents
    - Actionable recommendations to fix drift
    Example:
        check_database_health()
        -> {"is_synchronized": false, "missing_in_postgresql": ["2024-05 Report.pdf", ...]}
    Returns:
        JSON string with DataIntegrityResult containing sync status and recommendations
    """
    from raglite.shared.validation import check_data_integrity

    logger.info("Running database health check")
    try:
        result = await check_data_integrity()
        if result.is_synchronized:
            logger.info(
                "Database health check passed",
                extra={
                    "qdrant_docs": result.qdrant.documents,
                    "postgresql_docs": result.postgresql.documents,
                },
            )
        else:
            logger.warning(
                "Database health check found data drift",
                extra={
                    "qdrant_docs": result.qdrant.documents,
                    "postgresql_docs": result.postgresql.documents,
                    "missing_in_postgresql": len(result.missing_in_postgresql),
                    "missing_in_qdrant": len(result.missing_in_qdrant),
                },
            )
        return result.model_dump_json(indent=2)
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return json.dumps(
            {
                "error": f"Health check failed: {e}",
                "is_synchronized": False,
                "recommendations": ["Check database connectivity"],
            },
            indent=2,
        )


def _check_prophet_ready() -> bool:
    """Check if Prophet module is already imported (no import delay)."""
    return "prophet" in sys.modules


def _check_tft_ready() -> tuple[bool, bool]:
    """Check TFT model readiness.

    Returns:
        Tuple of (model_in_memory, checkpoint_exists)
    """
    import os

    # Check if checkpoint exists
    checkpoint_dir = settings.tft_checkpoint_dir
    checkpoint_exists = False
    try:
        if os.path.exists(checkpoint_dir):
            checkpoint_exists = any(
                f.endswith(".ckpt")
                for f in os.listdir(checkpoint_dir)
                if os.path.isfile(os.path.join(checkpoint_dir, f))
            )
    except OSError:
        pass

    # Check if model is loaded in memory (check the module-level cache in tft_model.py)
    model_in_memory = False
    try:
        from raglite.forecasting.models import tft_model

        model_in_memory = tft_model._tft_model is not None
    except (ImportError, AttributeError):
        pass

    return model_in_memory, checkpoint_exists


def _check_chronos_ready() -> bool:
    """Check if Chronos model is cached locally."""
    try:
        import os

        from transformers.utils import TRANSFORMERS_CACHE

        model_name = settings.chronos_model_name
        # Simple heuristic: check if the model folder exists in cache
        cache_path = os.path.join(TRANSFORMERS_CACHE, f"models--{model_name.replace('/', '--')}")
        return os.path.exists(cache_path)
    except Exception:
        return False


def _check_database_ready() -> bool:
    """Check if database connection pool is active."""
    try:
        from sqlalchemy import text

        from raglite.shared.database import get_session

        session = get_session()
        session.execute(text("SELECT 1"))
        session.close()
        return True
    except Exception:
        return False


@mcp.tool()
async def check_forecast_readiness() -> str:
    """Check if forecasting models are loaded and ready for immediate use.

    Use this tool to diagnose forecast timeout issues. It reports:
    - Which models are loaded in memory (Prophet, TFT, Chronos)
    - Database connection status
    - Estimated time for first forecast
    - Recommendations to improve readiness

    **Interpreting results:**
    - `is_ready=True`: Forecasts should complete in <30 seconds
    - `is_ready=False`: First forecast may timeout; call `warmup_forecasting_models()`

    **When to use:**
    - Before running forecasts if timeouts have occurred
    - After server restart to verify preloading completed
    - To diagnose why forecasts are slow

    Returns:
        JSON string with ForecastReadinessResult containing model status and recommendations
    """
    logger.info("Checking forecast readiness")

    recommendations: list[str] = []
    details: dict = {}

    # Check Prophet
    prophet_ready = _check_prophet_ready()
    if not prophet_ready:
        recommendations.append("Prophet not loaded. First forecast will take 3-5s longer.")
        details["prophet_note"] = "Will import on first forecast request"

    # Check TFT
    tft_in_memory, tft_checkpoint_exists = _check_tft_ready()
    if not tft_in_memory and tft_checkpoint_exists:
        recommendations.append(
            "TFT checkpoint exists but not loaded. Call warmup_forecasting_models()."
        )
    elif not tft_checkpoint_exists:
        recommendations.append("No TFT checkpoint. Run retrain_forecasting_models() to create one.")
        details["tft_note"] = "TFT model not available - ensemble will use other models"

    # Check Chronos
    chronos_ready = _check_chronos_ready()
    if not chronos_ready:
        details["chronos_note"] = "Chronos model not cached - will download on first use (5-10s)"

    # Check Database
    database_ready = _check_database_ready()
    if not database_ready:
        recommendations.append("Database connection failed. Check PostgreSQL container is running.")
        details["database_note"] = "Forecasts require database for historical data"

    # Calculate overall readiness
    # Prophet + DB are critical; TFT is nice-to-have
    is_ready = prophet_ready and database_ready

    # Estimate first forecast time
    delays = []
    if not prophet_ready:
        delays.append(("Prophet import", "3-5s"))
    if not tft_in_memory and tft_checkpoint_exists:
        delays.append(("TFT load", "5-15s"))
    if not database_ready:
        delays.append(("DB connect", "1-2s"))

    if is_ready:
        estimated_time = "<30s (Prophet-only) or 40-60s (Ensemble)"
    elif delays:
        delay_str = " + ".join([f"{d[0]}: {d[1]}" for d in delays])
        estimated_time = f"50-90s due to: {delay_str}"
    else:
        estimated_time = "Unknown - database not available"

    # Add async pattern recommendation if not ready
    if not is_ready:
        recommendations.append(
            "Consider using get_financial_forecast_async() + get_forecast_status() pattern to avoid timeouts."
        )

    result = ForecastReadinessResult(
        is_ready=is_ready,
        prophet_ready=prophet_ready,
        tft_ready=tft_in_memory,
        tft_checkpoint_exists=tft_checkpoint_exists,
        chronos_ready=chronos_ready,
        database_ready=database_ready,
        estimated_first_forecast_time=estimated_time,
        recommendations=recommendations,
        details=details,
    )

    logger.info(
        "Forecast readiness check complete",
        extra={
            "is_ready": is_ready,
            "prophet_ready": prophet_ready,
            "tft_ready": tft_in_memory,
            "database_ready": database_ready,
        },
    )

    return result.model_dump_json(indent=2)


class ForecastEnvironmentResult(BaseModel):
    """Result from forecast environment check."""

    is_production: bool = Field(description="Whether connected to production database")
    database: str = Field(description="Current database name")
    port: int = Field(description="Current database port")
    expected_database: str = Field(default="raglite", description="Expected production database")
    expected_port: int = Field(default=5432, description="Expected production port")
    has_data: bool = Field(default=False, description="Whether database has financial data")
    data_row_count: int = Field(default=0, description="Number of rows in financial_tables")
    env_overrides: list[str] = Field(
        default_factory=list, description="Environment variables overriding .env"
    )
    fix_command: str | None = Field(
        default=None, description="Command to fix environment if misconfigured"
    )
    recommendations: list[str] = Field(default_factory=list, description="Actions to fix issues")


def _get_database_row_count() -> int:
    """Get row count from financial_tables."""
    try:
        from sqlalchemy import text

        from raglite.shared.database import get_session

        session = get_session()
        result = session.execute(text("SELECT COUNT(*) FROM financial_tables"))
        count = result.scalar() or 0
        session.close()
        return count
    except Exception:
        return 0


@mcp.tool()
async def check_forecast_environment() -> str:
    """Check if forecast environment is correctly configured.

    Use this tool to diagnose "wrong database" issues where forecasts
    return no data due to shell environment variables overriding .env settings.

    **Common scenario:**
    After running tests, shell environment may have POSTGRES_DB=raglite_ci set.
    This causes forecasts to query the empty CI database instead of production.

    **What this tool checks:**
    - Current database name and port
    - Whether environment variables are overriding .env
    - Whether the database actually contains financial data
    - Provides fix command if misconfigured

    **When to use:**
    - Forecasts returning "insufficient data" errors unexpectedly
    - After running tests in the same terminal
    - Server startup shows non-production database warning

    Returns:
        JSON string with ForecastEnvironmentResult containing configuration status
    """
    from raglite.shared.config import (
        detect_env_overrides,
        get_settings,
        validate_forecast_environment,
    )

    logger.info("Checking forecast environment configuration")

    current_settings = get_settings()
    env_status = validate_forecast_environment()
    overrides = detect_env_overrides()
    row_count = _get_database_row_count()

    recommendations: list[str] = []

    # Check for non-production database
    if not env_status["is_production"]:
        recommendations.append(
            f"Connected to '{current_settings.postgres_db}' instead of 'raglite'. "
            "Forecasts will return no data."
        )
        if env_status["fix_command"]:
            recommendations.append(f"Fix: Run '{env_status['fix_command']}' and restart server.")

    # Check for empty database
    if row_count == 0:
        recommendations.append(
            f"Database '{current_settings.postgres_db}' has no financial data. "
            "Re-ingest documents or check database configuration."
        )

    # Check for environment overrides
    if overrides:
        recommendations.append(
            f"Shell environment variables are overriding .env: {list(overrides.keys())}. "
            "These persist from previous test runs."
        )

    result = ForecastEnvironmentResult(
        is_production=env_status["is_production"],
        database=current_settings.postgres_db,
        port=current_settings.postgres_port,
        expected_database="raglite",
        expected_port=5432,
        has_data=row_count > 0,
        data_row_count=row_count,
        env_overrides=list(overrides.keys()),
        fix_command=env_status.get("fix_command"),
        recommendations=recommendations,
    )

    logger.info(
        "Forecast environment check complete",
        extra={
            "is_production": result.is_production,
            "database": result.database,
            "has_data": result.has_data,
            "env_overrides": result.env_overrides,
        },
    )

    return result.model_dump_json(indent=2)
