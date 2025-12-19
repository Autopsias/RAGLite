"""RAGLite MCP Server - Model Context Protocol entry point.

This module implements the FastMCP server that exposes RAGLite capabilities
to MCP clients. Tools have been refactored to raglite.mcp.tools (Story 7.4).

For new code, import tools from raglite.mcp.tools.* instead of raglite.main.
"""
from fastmcp import FastMCP

from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Initialize FastMCP server - must be in main for decorator access
mcp = FastMCP("RAGLite")

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
    ingestion,
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
from raglite.mcp.tools.forecast import (  # noqa: E402, F401
    get_financial_forecast,
)
from raglite.mcp.tools.health import check_database_health  # noqa: E402, F401

# Re-export DocumentProcessingError for backward compatibility (AC4)
# Re-export all tools for backward compatibility (AC4)
from raglite.mcp.tools.ingestion import (  # noqa: E402, F401
    DocumentProcessingError,  # noqa: E402, F401
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
    "manage_model_weights",
    "retrain_forecasting_models",
    "validate_forecasting_accuracy",
    "list_available_regressors",
    "get_regressor_data",
    "check_database_health",
    "ExternalDataQueryRequest",
    "ExternalDataPoint",
    "ExternalDataQueryResponse",
]

def __getattr__(name):
    """Lazy import for admin tools to avoid circular import during module load."""
    if name == "manage_model_weights":
        from raglite.mcp.tools import admin
        return admin.manage_model_weights
    elif name == "retrain_forecasting_models":
        from raglite.mcp.tools import admin
        return admin.retrain_forecasting_models
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


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
            "Failed to start scheduler - continuing without scheduled refreshes", extra={"error": str(e)}
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
        },
    )

    _start_scheduler_sync()
    atexit.register(_shutdown_scheduler_sync)
    mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
