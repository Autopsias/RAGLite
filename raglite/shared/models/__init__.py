"""Pydantic data models for RAGLite.

This module maintains backward compatibility by re-exporting all models
from domain-specific submodules. Import from here as usual:

    from raglite.shared.models import DocumentMetadata, QueryResult

Internal architecture: Models are organized by domain in submodules
(document.py, query_schemas.py, timeseries_models.py, etc.) but all are available
via this __init__.py for compatibility.
"""

# Type aliases
from raglite.shared.models.base import JobID

# Chunking & Search
from raglite.shared.models.chunk import Chunk, SearchResult, WorkflowMetrics

# Document & Ingestion
from raglite.shared.models.document import (
    BatchIngestionResult,
    DocumentMetadata,
    ExtractedMetadata,
    IngestionJobStatus,
    IngestionResult,
)

# External Data & Regressors
from raglite.shared.models.external_data import (
    AsyncIngestionRequest,
    AsyncIngestionResponse,
    RegressorDataPoint,
    RegressorDataResponse,
    RegressorInfo,
    RegressorListResponse,
)

# Time Series & Forecasting
from raglite.shared.models.forecast_jobs import (
    AsyncForecastResponse,
    ForecastJobStatus,
)

# Insights, Anomalies, Trends, Recommendations
from raglite.shared.models.insights import (
    Anomaly,
    AnomalyDetectionResult,
    AnomalySeverity,
    CorrelationResult,
    Insight,
    InsightCategory,
    InsightGenerationResult,
    InsightsQueryRequest,
    InsightsQueryResponse,
    Recommendation,
    RecommendationCategory,
    RecommendationResult,
    Trend,
    TrendAnalysisResult,
    TrendDirection,
)

# Query Models
from raglite.shared.models.query_schemas import (
    AnalyticalQueryRequest,
    AnalyticalQueryResponse,
    QueryRequest,
    QueryResponse,
    QueryResult,
)
from raglite.shared.models.timeseries_models import (
    ForecastPoint,
    ForecastQueryRequest,
    ForecastQueryResponse,
    ForecastRefreshResult,
    ForecastResult,
    TimeSeriesData,
    TimeSeriesPoint,
)

# Validation
from raglite.shared.models.validation import (
    ModelPerformanceDetail,
    ValidationResponse,
    VariableValidationDetail,
)

# Re-export all for backward compatibility
__all__ = [
    # Type aliases
    "JobID",
    # Document & Ingestion
    "DocumentMetadata",
    "ExtractedMetadata",
    "BatchIngestionResult",
    "IngestionResult",
    "IngestionJobStatus",
    # Chunking & Search
    "Chunk",
    "SearchResult",
    "WorkflowMetrics",
    # Query Models
    "QueryRequest",
    "QueryResponse",
    "QueryResult",
    "AnalyticalQueryRequest",
    "AnalyticalQueryResponse",
    # Time Series & Forecasting
    "TimeSeriesPoint",
    "TimeSeriesData",
    "ForecastPoint",
    "ForecastResult",
    "ForecastRefreshResult",
    "ForecastQueryRequest",
    "ForecastQueryResponse",
    "AsyncForecastResponse",
    "ForecastJobStatus",
    # Insights
    "AnomalySeverity",
    "Anomaly",
    "AnomalyDetectionResult",
    "TrendDirection",
    "Trend",
    "TrendAnalysisResult",
    "CorrelationResult",
    "InsightCategory",
    "Insight",
    "InsightGenerationResult",
    "RecommendationCategory",
    "Recommendation",
    "RecommendationResult",
    "InsightsQueryRequest",
    "InsightsQueryResponse",
    # External Data
    "RegressorInfo",
    "RegressorListResponse",
    "RegressorDataResponse",
    "RegressorDataPoint",
    "AsyncIngestionRequest",
    "AsyncIngestionResponse",
    # Validation
    "ModelPerformanceDetail",
    "VariableValidationDetail",
    "ValidationResponse",
]
