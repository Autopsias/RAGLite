"""Analysis Agent module - financial calculations and reasoning."""

from raglite.agentic.agents.analysis.calculations import (
    _calculate_percentage,
    _calculate_trend,
    _calculate_variance,
    _calculate_yoy_growth,
)
from raglite.agentic.agents.analysis.reasoning import (
    _build_analysis_prompt,
    _get_claude_reasoning,
    _get_default_reasoning,
)
from raglite.agentic.agents.analysis.workflow import (
    _build_analysis_error,
    _build_analysis_result,
    _execute_analysis_calculation,
    _extract_analysis_type_and_data,
    _format_analysis_value,
    _perform_analysis_with_reasoning,
    _validate_analysis_inputs,
    analysis_agent,
)

# Import for test compatibility (tests patch this function)
from raglite.shared.clients import get_claude_client  # noqa: F401

__all__ = [
    "analysis_agent",
    "_calculate_yoy_growth",
    "_calculate_variance",
    "_calculate_trend",
    "_calculate_percentage",
    "_extract_analysis_type_and_data",
    "_execute_analysis_calculation",
    "_format_analysis_value",
    "_build_analysis_result",
    "_build_analysis_error",
    "_validate_analysis_inputs",
    "_perform_analysis_with_reasoning",
    "_get_claude_reasoning",
    "_build_analysis_prompt",
    "_get_default_reasoning",
    "get_claude_client",
]
