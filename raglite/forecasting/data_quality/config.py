"""Variable quality configuration for data quality checks.

Story: Data Quality Testing Framework
Provides per-variable quality requirements and thresholds.

This module serves as a facade, re-exporting models and configurations
from separate modules for better maintainability.
"""

# Re-export all models
from raglite.forecasting.data_quality.models import (
    EntityConfig,
    EntityMatchMode,
    ExpectedSign,
    Frequency,
    FrequencyConfig,
    ValueRangeConfig,
    VariableQualityConfig,
)

# Re-export variable configurations
from raglite.forecasting.data_quality.variable_configs import (
    VARIABLE_QUALITY_CONFIGS,
)

__all__ = [
    # Models
    "EntityMatchMode",
    "ExpectedSign",
    "Frequency",
    "ValueRangeConfig",
    "EntityConfig",
    "FrequencyConfig",
    "VariableQualityConfig",
    # Configurations
    "VARIABLE_QUALITY_CONFIGS",
    # Utility functions
    "get_variable_config",
    "list_configured_variables",
    "get_secil_variables",
    "get_external_variables",
]


# =============================================================================
# Utility Functions
# =============================================================================


def get_variable_config(name: str) -> VariableQualityConfig | None:
    """Get quality config for a variable by name.

    Args:
        name: Variable name (case-insensitive)

    Returns:
        VariableQualityConfig or None if not found
    """
    return VARIABLE_QUALITY_CONFIGS.get(name.lower())


def list_configured_variables() -> list[str]:
    """List all configured variable names.

    Returns:
        Sorted list of variable names
    """
    return sorted(VARIABLE_QUALITY_CONFIGS.keys())


def get_secil_variables() -> list[str]:
    """Get list of SECIL internal variables (non-external).

    Returns:
        List of variable names from PostgreSQL financial_tables
    """
    return [
        name for name, config in VARIABLE_QUALITY_CONFIGS.items() if not config.is_external_only
    ]


def get_external_variables() -> list[str]:
    """Get list of external API variables.

    Returns:
        List of variable names from external APIs/data sources
    """
    return [name for name, config in VARIABLE_QUALITY_CONFIGS.items() if config.is_external_only]
