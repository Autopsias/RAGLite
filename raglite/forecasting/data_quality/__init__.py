"""Data quality testing framework for RAGLite forecasting.

Provides reusable checks for detecting data quality issues across
forecast variables including entity contamination, value ranges,
time series integrity, and more.

Usage:
    from raglite.forecasting.data_quality import (
        DataQualityOrchestrator,
        VARIABLE_QUALITY_CONFIGS,
        CheckResult,
        CheckStatus,
    )

    orchestrator = DataQualityOrchestrator()
    audit = await orchestrator.run_audit()
    print(f"Pass rate: {audit.pass_rate:.1%}")
"""

from raglite.forecasting.data_quality.check_result import CheckResult, CheckStatus
from raglite.forecasting.data_quality.config import (
    VARIABLE_QUALITY_CONFIGS,
    EntityConfig,
    EntityMatchMode,
    ExpectedSign,
    Frequency,
    FrequencyConfig,
    ValueRangeConfig,
    VariableQualityConfig,
    get_external_variables,
    get_secil_variables,
    get_variable_config,
    list_configured_variables,
)
from raglite.forecasting.data_quality.orchestrator import (
    AuditResult,
    DataQualityOrchestrator,
    VariableAuditResult,
)
from raglite.forecasting.data_quality.report import (
    audit_to_dict,
    export_json,
    format_markdown,
    print_console_report,
)

__all__ = [
    # Core types
    "CheckResult",
    "CheckStatus",
    # Config types
    "VariableQualityConfig",
    "ValueRangeConfig",
    "EntityConfig",
    "FrequencyConfig",
    "EntityMatchMode",
    "ExpectedSign",
    "Frequency",
    # Configs
    "VARIABLE_QUALITY_CONFIGS",
    "get_variable_config",
    "list_configured_variables",
    "get_secil_variables",
    "get_external_variables",
    # Orchestrator
    "DataQualityOrchestrator",
    "AuditResult",
    "VariableAuditResult",
    # Report
    "audit_to_dict",
    "export_json",
    "format_markdown",
    "print_console_report",
]
