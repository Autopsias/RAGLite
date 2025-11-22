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

    @model_validator(mode="after")
    def adjust_for_environment(self) -> Self:
        """Automatically adjust database settings based on APP_ENV and CI detection.

        This ensures test environments use separate database instances without
        requiring explicit environment variable overrides for every setting.

        Environment routing (Story 4.0.5):
        - Production (default): Qdrant:6333, PostgreSQL:5432, collection: financial_docs
        - Test (APP_ENV=test): Qdrant:6335, PostgreSQL:5433, collection: financial_docs_test
        - CI (APP_ENV=test + CI=true): Same as test but collection: financial_docs_ci

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
            # Only override if using default values (allows env var overrides)
            if self.qdrant_port == 6333:
                self.qdrant_port = 6335
            if self.qdrant_collection_name == "financial_docs":
                # Story 4.0.5 AC4: Separate CI collection to avoid conflicts with local tests
                collection_suffix = "_ci" if is_ci else "_test"
                self.qdrant_collection_name = f"financial_docs{collection_suffix}"
            if self.postgres_port == 5432:
                self.postgres_port = 5433
            if self.postgres_db == "raglite":
                db_suffix = "_ci" if is_ci else "_test"
                self.postgres_db = f"raglite{db_suffix}"
            if self.postgres_user == "raglite":
                user_suffix = "_ci" if is_ci else "_test"
                self.postgres_user = f"raglite{user_suffix}"
            if self.postgres_password == "raglite":  # nosec B105
                pass_suffix = "_ci" if is_ci else "_test"
                self.postgres_password = f"raglite{pass_suffix}"
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
