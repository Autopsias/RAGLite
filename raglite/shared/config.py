"""Application configuration using Pydantic Settings.

This module provides type-safe configuration management loaded from environment
variables via .env file.

Environment-based configuration:
- APP_ENV=production (default): Uses production databases (ports 6333, 5432)
- APP_ENV=test: Automatically uses test databases (ports 6335, 5433)
- APP_ENV=development: Uses development settings (same as production for now)

All settings can be overridden by environment variables.
"""

from __future__ import annotations

import logging
import os
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables or .env file.
    Required settings will raise validation errors if not provided.

    APP_ENV determines which database instances to use:
    - production: localhost:6333 (Qdrant), localhost:5432 (PostgreSQL)
    - test: localhost:6335 (Qdrant), localhost:5433 (PostgreSQL)
    """

    # Environment Configuration (NEW)
    app_env: str = "production"  # Options: production, test, development

    # Qdrant Vector Database
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "financial_docs"

    # PostgreSQL Database (Story 2.6: Structured metadata storage)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "raglite"
    postgres_user: str = "raglite"
    postgres_password: str = "raglite"

    # Anthropic Claude API (optional for Phase 1 setup, required for Story 1.11+)
    anthropic_api_key: str | None = None

    # Mistral API (Story 2.4: Mistral Small for metadata extraction)
    # Replaces OpenAI o1-mini which had 50% failure rate due to reasoning token overflow
    # Mistral Small: FREE, 91% accuracy, native JSON schema support
    mistral_api_key: str | None = None
    metadata_extraction_model: str = (
        "mistral-small-latest"  # Mistral model for chunk metadata extraction
    )

    # AWS Strands Agentic Framework (Story 3.1: Epic 3 orchestration)
    strands_orchestration_model: str = (
        "mistral-small-latest"  # Orchestration LLM (tunable to claude-3-5-sonnet-20241022)
    )
    strands_agent_timeout_seconds: int = 15  # Per NFR26: 15s max per agent
    strands_enable_opentelemetry: bool = False  # Optional: can defer detailed setup to Story 3.5

    # Embedding Model Configuration
    embedding_model: str = "intfloat/e5-large-v2"
    embedding_dimension: int = 1024

    # MCP Server Configuration
    mcp_server_port: int = 8000

    # PDF Processing Configuration (Story 2.2)
    pdf_processing_threads: int = 8  # Parallel page processing threads (default 8, range 1-16)

    # Forecasting Auto-Update Configuration (Story 4.3)
    enable_forecast_auto_update: bool = True  # Auto-refresh forecasts on document ingestion
    forecast_refresh_timeout: int = 300  # 5-minute timeout for forecast refresh (AC3)

    # Metrics Discovery Cache Configuration (Story 5.0.4 Advisory)
    metrics_cache_ttl_seconds: int = 300  # 5-minute TTL for development; tune for production

    # Parallel Ingestion Configuration (Story 5.0.6)
    ingestion_parallel_docs: int = 2  # Max concurrent documents (default: 2, range: 1-4)

    # Metadata Extraction Strategy (Story 5.0.6: Strategy C - Query-time enrichment)
    skip_ingestion_metadata: bool = (
        True  # Skip metadata extraction at ingestion (saves 400 API calls/doc)
    )
    query_time_metadata_enabled: bool = True  # Enable query-time metadata enrichment
    query_time_metadata_timeout: float = 2.5  # Query-time enrichment timeout (seconds)

    # Unit Inference Optimization (Story 5.0.6)
    unit_inference_llm_tables_only: bool = True  # Only use LLM for table chunks (user preference)

    # External Data API Keys (Story 6.1: Tier 1 sources)
    ine_api_key: str | None = None
    bpstat_api_key: str | None = None
    omie_api_key: str | None = None  # May not require key
    ipma_api_key: str | None = None  # Public API, no key needed

    # External Data Configuration (Story 6.1)
    external_data_stale_days: int = 30  # Max days before data considered stale
    external_data_retry_attempts: int = 3  # Retry attempts with exponential backoff
    external_data_timeout: int = 30  # HTTP timeout seconds

    # Story 6.4: Ensemble Forecasting Configuration
    # Story 6.8: Added LightGBM to ensemble (AC4)
    forecasting_models: str = "prophet,linear,xgboost,lightgbm"  # Comma-separated model list
    ensemble_weight_prophet: float = 0.35  # Prophet model weight (35%)
    ensemble_weight_linear: float = 0.20  # Linear Regression weight (20%)
    ensemble_weight_xgboost: float = 0.25  # XGBoost weight (25%)
    ensemble_weight_lightgbm: float = 0.20  # LightGBM weight (20%)
    ensemble_fast_mode: bool = False  # Use reduced hyperparameter grid for faster training

    # Story 6.5: Automated Data Refresh Scheduler Configuration
    scheduler_enabled: bool = True  # Enable/disable the scheduler
    scheduler_timezone: str = "UTC"  # Timezone for scheduled jobs (always UTC per AC2)
    scheduler_job_coalesce: bool = True  # Coalesce missed jobs after downtime (AC1)
    scheduler_misfire_grace_time: int = 3600  # 1 hour grace time for misfired jobs (AC1)

    # Cron schedules for external data refresh (AC2)
    # Format: minute hour day_of_month month day_of_week
    refresh_cron_daily: str = "0 6 * * *"  # Daily at 06:00 UTC
    refresh_cron_weekly: str = "0 6 * * 0"  # Sunday at 06:00 UTC
    refresh_cron_monthly: str = "0 6 1 * *"  # 1st of month at 06:00 UTC

    @model_validator(mode="after")
    def adjust_for_environment(self) -> Self:
        """Automatically adjust database settings based on APP_ENV.

        CRITICAL FIX (2025-11-23): Removed PostgreSQL auto-adjustment to eliminate
        configuration race condition in CI. PostgreSQL settings now come ONLY from
        explicit environment variables set by CI workflow.

        Root cause: The validator runs at Settings instantiation (module import time),
        which happens BEFORE GitHub Actions sets CI=true. This caused Settings to use
        "raglite_test" instead of "raglite_ci", creating a database mismatch where
        ingestion wrote to one database and tests read from another.

        Environment routing (Story 4.0.5):
        - Production (default): Qdrant:6333, collection: financial_docs
        - Test (APP_ENV=test): Qdrant:6335, collection: financial_docs_test
        - CI: Uses explicit env vars (POSTGRES_DB=raglite_ci, etc.)

        CI detection: Checks GITHUB_ACTIONS, CI, or CONTINUOUS_INTEGRATION environment variables
        """
        import os

        # Detect if running in CI environment
        is_ci = (
            os.getenv("GITHUB_ACTIONS") == "true"
            or os.getenv("CI") == "true"
            or os.getenv("CONTINUOUS_INTEGRATION") == "true"
        )

        if self.app_env == "test":
            # Qdrant adjustments (non-critical, useful for test isolation)
            if self.qdrant_port == 6333:
                self.qdrant_port = 6335
            if self.qdrant_collection_name == "financial_docs":
                # Story 4.0.5 AC4: Separate CI collection to avoid conflicts with local tests
                collection_suffix = "_ci" if is_ci else "_test"
                self.qdrant_collection_name = f"financial_docs{collection_suffix}"

            # REMOVED: PostgreSQL auto-adjustment (causes CI race condition)
            # PostgreSQL settings now come ONLY from explicit environment variables:
            #   - CI: POSTGRES_DB=raglite_ci (set by .github/workflows/ci.yml)
            #   - Local tests: POSTGRES_DB=raglite_test (set by local .env.test)
            # This ensures Settings use the correct database name regardless of
            # when CI=true environment variable is set.

        return self

    # Pydantic 2.x configuration using SettingsConfigDict
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from .env (e.g., TEST_PDF_PATH)
    )


# Singleton instance - import this in other modules
settings = Settings()

# Diagnostic logging for Settings initialization (helps debug CI configuration issues)
logger = logging.getLogger(__name__)
logger.info(
    "Settings initialized",
    extra={
        "postgres_db": settings.postgres_db,
        "postgres_port": settings.postgres_port,
        "postgres_user": settings.postgres_user,
        "qdrant_collection": settings.qdrant_collection_name,
        "qdrant_port": settings.qdrant_port,
        "app_env": settings.app_env,
        "ci_detected": os.getenv("CI") == "true",
        "github_actions": os.getenv("GITHUB_ACTIONS") == "true",
    },
)
