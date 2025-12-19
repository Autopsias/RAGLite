"""MCP tools package for RAGLite.

Tools are registered via FastMCP decorators and exported for main.py.
"""

from raglite.mcp.tools.admin import manage_model_weights, retrain_forecasting_models
from raglite.mcp.tools.external_data import query_external_data, refresh_external_data
from raglite.mcp.tools.forecast import get_financial_forecast
from raglite.mcp.tools.health import check_database_health
from raglite.mcp.tools.ingestion import (
    get_ingestion_status,
    ingest_financial_document,
    ingest_financial_document_async,
)
from raglite.mcp.tools.insights import get_financial_insights
from raglite.mcp.tools.query import (
    analytical_query_financial_documents,
    query_financial_documents,
)
from raglite.mcp.tools.validation import (
    get_regressor_data,
    list_available_regressors,
    validate_forecasting_accuracy,
)

__all__ = [
    "ingest_financial_document",
    "ingest_financial_document_async",
    "get_ingestion_status",
    "query_financial_documents",
    "analytical_query_financial_documents",
    "get_financial_forecast",
    "get_financial_insights",
    "query_external_data",
    "refresh_external_data",
    "manage_model_weights",
    "retrain_forecasting_models",
    "validate_forecasting_accuracy",
    "list_available_regressors",
    "get_regressor_data",
    "check_database_health",
]
