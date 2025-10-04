"""Application configuration using Pydantic Settings.

This module provides type-safe configuration management loaded from environment
variables via .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables or .env file.
    Required settings will raise validation errors if not provided.
    """

    # Qdrant Vector Database
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "financial_docs"

    # Anthropic Claude API (optional for Phase 1 setup, required for Story 1.11+)
    anthropic_api_key: str | None = None

    # Embedding Model Configuration
    embedding_model: str = "intfloat/e5-large-v2"
    embedding_dimension: int = 1024

    # MCP Server Configuration
    mcp_server_port: int = 8000

    # Pydantic 2.x configuration using SettingsConfigDict
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from .env (e.g., TEST_PDF_PATH)
    )


# Singleton instance - import this in other modules
settings = Settings()
