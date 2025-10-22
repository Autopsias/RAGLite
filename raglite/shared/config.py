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

    # OpenAI API (Story 2.4: GPT-5 nano for metadata extraction)
    openai_api_key: str | None = None
    openai_metadata_model: str = "gpt-5-nano"  # AI7: Configurable model for metadata extraction

    # OpenAI Pricing (Story 2.4 AI4: Externalized for maintainability)
    # GPT-5 nano pricing as of 2025-10 (per million tokens)
    gpt5_nano_input_price_per_mtok: float = 0.10  # $0.10 per 1M input tokens
    gpt5_nano_output_price_per_mtok: float = 0.40  # $0.40 per 1M output tokens
    gpt5_nano_cached_input_price_per_mtok: float = 0.005  # $0.005 per 1M cached tokens

    # Embedding Model Configuration
    embedding_model: str = "intfloat/e5-large-v2"
    embedding_dimension: int = 1024

    # MCP Server Configuration
    mcp_server_port: int = 8000

    # PDF Processing Configuration (Story 2.2)
    pdf_processing_threads: int = 8  # Parallel page processing threads (default 8, range 1-16)

    # Pydantic 2.x configuration using SettingsConfigDict
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from .env (e.g., TEST_PDF_PATH)
    )


# Singleton instance - import this in other modules
settings = Settings()
