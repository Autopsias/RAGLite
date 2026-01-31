"""RAGLite MCP Server - Model Context Protocol entry point.

This module implements the FastMCP server that exposes RAGLite capabilities
to MCP clients. Tools have been refactored to raglite.mcp.tools (Story 7.4).

For new code, import tools from raglite.mcp.tools.* instead of raglite.main.
"""

from typing import Any

from fastmcp import FastMCP

from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Initialize FastMCP server - must be in main for decorator access
mcp: FastMCP = FastMCP("RAGLite")

# Import all tool modules to register @mcp.tool() decorators
# noqa comments suppress import order warnings
# Re-export MCP models for backward compatibility (AC4)
from raglite.mcp.models import (  # noqa: E402, F401
    ExternalDataPoint,
    ExternalDataQueryRequest,
    ExternalDataQueryResponse,
)
from raglite.mcp.tools import (  # noqa: E402, F401
    admin,
    external_data,
    forecast,
    health,
    ingestion_tool,  # noqa: E402, F401
    insights,
    query,
    validation,
)

# Admin tools accessed via module namespace to avoid circular imports
# from raglite.mcp.tools.admin import manage_model_weights, retrain_forecasting_models
from raglite.mcp.tools.external_data import (  # noqa: E402, F401
    _format_response,
    _get_visualization_hint,
    _parse_date_range,
    _query_all_sources,
    _query_single_source,
    query_external_data,
    refresh_external_data,
)
from raglite.mcp.tools.forecast import get_financial_forecast  # noqa: E402, F401
from raglite.mcp.tools.health import check_database_health  # noqa: E402, F401

# Re-export DocumentProcessingError for backward compatibility (AC4)
# Re-export all tools for backward compatibility (AC4)
from raglite.mcp.tools.ingestion_tool import (  # noqa: E402, F401
    DocumentProcessingError,
    _perform_forecast_refresh,
    get_ingestion_status,
    ingest_financial_document,
    ingest_financial_document_async,
)
from raglite.mcp.tools.insights import (  # noqa: E402, F401
    SUPPORTED_INSIGHT_CATEGORIES,
    TIME_PERIOD_MAPPINGS,
    format_insights_for_display,
    get_financial_insights,
    parse_insights_query,
)
from raglite.mcp.tools.query import (  # noqa: E402, F401
    analytical_query_financial_documents,
    parse_forecast_query,
    query_financial_documents,
)
from raglite.mcp.tools.validation import (  # noqa: E402, F401
    get_regressor_data,
    list_available_regressors,
    validate_forecasting_accuracy,
)

__all__ = [
    "mcp",
    "DocumentProcessingError",
    "ingest_financial_document",
    "ingest_financial_document_async",
    "get_ingestion_status",
    "_perform_forecast_refresh",
    "query_financial_documents",
    "analytical_query_financial_documents",
    "parse_forecast_query",
    "get_financial_forecast",
    "SUPPORTED_INSIGHT_CATEGORIES",
    "TIME_PERIOD_MAPPINGS",
    "get_financial_insights",
    "parse_insights_query",
    "format_insights_for_display",
    "query_external_data",
    "refresh_external_data",
    "_parse_date_range",
    "_get_visualization_hint",
    "_query_single_source",
    "_query_all_sources",
    "_format_response",
    "validate_forecasting_accuracy",
    "list_available_regressors",
    "get_regressor_data",
    "check_database_health",
    # check_forecast_readiness and warmup_forecasting_models are lazy-loaded via __getattr__
    "ExternalDataQueryRequest",
    "ExternalDataPoint",
    "ExternalDataQueryResponse",
]


def __getattr__(name: str) -> Any:
    """Lazy import for admin/health tools to avoid circular import during module load."""
    if name == "manage_model_weights":
        from raglite.mcp.tools import admin

        return admin.manage_model_weights
    elif name == "retrain_forecasting_models":
        from raglite.mcp.tools import admin

        return admin.retrain_forecasting_models
    elif name == "warmup_forecasting_models":
        from raglite.mcp.tools import admin

        return admin.warmup_forecasting_models
    elif name == "check_forecast_readiness":
        from raglite.mcp.tools import health

        return health.check_forecast_readiness
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def _preload_prophet_model() -> None:
    """Preload Prophet at server startup to avoid 3-5s import penalty on first forecast.

    Prophet has heavy dependencies (cmdstanpy, numpy, pandas) that take 3-5 seconds
    to import on first use. By importing at startup, we avoid this latency during
    actual forecast requests.
    """
    try:
        import time

        start = time.time()
        from prophet import Prophet  # noqa: F401

        elapsed = time.time() - start
        logger.info(
            "Prophet preloaded successfully",
            extra={"import_time_seconds": round(elapsed, 2)},
        )
    except ImportError:
        logger.debug(
            "Prophet not installed - Prophet preloading skipped",
            extra={"reason": "ImportError"},
        )
    except Exception as e:
        logger.warning(
            "Prophet preload failed (will retry on first request)",
            extra={"error": str(e), "error_type": type(e).__name__},
        )


def _prewarm_database_connections() -> None:
    """Pre-warm database connection pool at server startup.

    Creating database connections on first request adds 0.5-2s latency.
    By establishing the connection pool at startup, we avoid this delay
    during actual forecast requests.
    """
    try:
        import time

        from sqlalchemy import text

        start = time.time()
        from raglite.shared.database import get_session

        # Create a session to establish connection pool
        session = get_session()
        # Execute a simple query to fully warm the connection
        session.execute(text("SELECT 1"))
        session.close()

        elapsed = time.time() - start
        logger.info(
            "Database connection pool pre-warmed successfully",
            extra={"warmup_time_seconds": round(elapsed, 2)},
        )
    except Exception as e:
        logger.warning(
            "Database connection pre-warming failed (will connect on first request)",
            extra={"error": str(e), "error_type": type(e).__name__},
        )


def _preload_tft_model() -> None:
    """Preload TFT model at server startup to avoid first-request latency.

    This moves the slow DB + model loading from request time to startup time,
    preventing timeouts on the first forecast request.
    """
    if not settings.preload_tft_model:
        return

    try:
        import asyncio

        from raglite.forecasting.models.tft_model import _get_tft_model_with_timeout

        logger.info(
            "Preloading TFT model...",
            extra={"timeout_seconds": settings.tft_preload_timeout},
        )

        # Run the async model loading in a new event loop (since main() hasn't started yet)
        loop = asyncio.new_event_loop()
        try:
            model = loop.run_until_complete(
                _get_tft_model_with_timeout(timeout=settings.tft_preload_timeout)
            )
            if model is not None:
                logger.info("TFT model preloaded successfully")
            else:
                logger.warning(
                    "TFT model preload returned None (no checkpoint or timeout) - "
                    "TFT forecasts may not be available"
                )
        finally:
            loop.close()

    except ImportError:
        logger.debug(
            "pytorch-forecasting not installed - TFT preloading skipped",
            extra={"reason": "ImportError"},
        )
    except Exception as e:
        logger.warning(
            "TFT model preload failed (forecasts will retry on first request)",
            extra={"error": str(e), "error_type": type(e).__name__},
        )


def _start_scheduler_sync() -> None:
    """Start the scheduler synchronously (before mcp.run() takes over event loop)."""
    from raglite.external_data.scheduler import _register_refresh_jobs, get_scheduler

    if not settings.scheduler_enabled:
        return

    try:
        scheduler = get_scheduler()
        if not scheduler.running:
            _register_refresh_jobs(scheduler)
            scheduler.start()
            logger.info(
                "External data scheduler started", extra={"timezone": settings.scheduler_timezone}
            )
    except Exception as e:
        logger.warning(
            "Failed to start scheduler - continuing without scheduled refreshes",
            extra={"error": str(e)},
        )


def _shutdown_scheduler_sync() -> None:
    """Shutdown the scheduler synchronously."""
    from raglite.external_data.scheduler import get_scheduler

    if not settings.scheduler_enabled:
        return

    try:
        scheduler = get_scheduler()
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("Scheduler shutdown complete")
    except Exception as e:
        logger.warning(f"Error during scheduler shutdown: {e}")


def main() -> None:
    """Main entry point for RAGLite MCP server."""
    import atexit

    logger.info(
        "Starting RAGLite MCP Server",
        extra={
            "qdrant_host": settings.qdrant_host,
            "qdrant_port": settings.qdrant_port,
            "collection": settings.qdrant_collection_name,
            "scheduler_enabled": settings.scheduler_enabled,
            "preload_tft_model": settings.preload_tft_model,
        },
    )

    # Preload forecasting models and warm database connections at startup
    # This avoids first-request latency that causes MCP timeouts
    logger.info("Starting model preloading and database warmup...")
    _preload_prophet_model()
    _prewarm_database_connections()
    _preload_tft_model()
    logger.info("Startup preloading complete")

    _start_scheduler_sync()
    atexit.register(_shutdown_scheduler_sync)
    mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
