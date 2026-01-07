"""Analysis workflow orchestration and main agent.

This module contains the main analysis agent function and orchestration logic
that coordinates calculations, formatting, and reasoning.
"""

import json
import time

try:
    from strands import tool
except ImportError:
    # Strands not installed - deferred until Epic 3 (Story 3.1+)
    # For now, use a no-op decorator
    def tool(func):  # type: ignore
        """No-op tool decorator when strands is not available."""
        return func


from raglite.agentic.agents.analysis.calculations import (
    _calculate_percentage,
    _calculate_trend,
    _calculate_variance,
    _calculate_yoy_growth,
)
from raglite.agentic.agents.analysis.reasoning import (
    _get_claude_reasoning,
)
from raglite.agentic.state import AnalysisResult
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def _extract_analysis_type_and_data(
    instruction: str, context: dict | None
) -> tuple[str, dict[str, float]]:
    """Extract analysis type and data from instruction and context.

    Args:
        instruction: Task instruction containing analysis directive
        context: Context data from previous agents

    Returns:
        Tuple of (analysis_type, data_dict)
    """
    analysis_type = "yoy_growth"
    data: dict[str, float] = {}

    if context and isinstance(context, dict) and "data" in context:
        data = context["data"]

    instruction_lower = instruction.lower()
    if "growth" in instruction_lower or "yoy" in instruction_lower:
        analysis_type = "yoy_growth"
    elif "variance" in instruction_lower or "difference" in instruction_lower:
        analysis_type = "variance"
    elif "trend" in instruction_lower:
        analysis_type = "trend"
    elif "percentage" in instruction_lower or "percent" in instruction_lower:
        analysis_type = "percentage"

    return analysis_type, data


def _execute_analysis_calculation(
    analysis_type: str, data: dict[str, float]
) -> tuple[float | None, str | None, str]:
    """Execute the appropriate analysis calculation.

    Args:
        analysis_type: Type of analysis to perform
        data: Financial data points

    Returns:
        Tuple of (calculation_value, calculation_string, trend_direction)
    """
    calculation_value = None
    calculation_str = None

    if analysis_type == "yoy_growth":
        calculation_value, calculation_str = _calculate_yoy_growth(data)
    elif analysis_type == "variance":
        calculation_value, calculation_str = _calculate_variance(data)
    elif analysis_type == "trend":
        slope_value, trend_direction, calculation_str = _calculate_trend(data)
        calculation_value = slope_value
        return calculation_value, calculation_str, trend_direction
    elif analysis_type == "percentage":
        calculation_value, calculation_str = _calculate_percentage(data)

    return calculation_value, calculation_str, ""


def _format_analysis_value(
    calculation_value: float | None, analysis_type: str, trend_direction: str = ""
) -> str:
    """Format calculation value for display.

    Args:
        calculation_value: Numerical result
        analysis_type: Type of analysis performed
        trend_direction: Trend direction for trend analysis

    Returns:
        Formatted value string
    """
    if analysis_type in ["yoy_growth", "variance"]:
        percentage_change = (calculation_value or 0.0) * 100
        sign = "+" if percentage_change >= 0 else ""
        return f"{sign}{percentage_change:.1f}%"
    elif analysis_type == "percentage":
        return f"{calculation_value:.1f}%"
    elif analysis_type == "trend":
        return trend_direction
    else:
        return str(calculation_value or 0.0)


def _build_analysis_result(
    calculation_str: str,
    calculation_value: float | None,
    formatted_value: str,
    reasoning: str,
    data: dict[str, float],
) -> str:
    """Build AnalysisResult and return JSON string.

    Args:
        calculation_str: Calculation formula string
        calculation_value: Numerical result
        formatted_value: Human-readable format
        reasoning: LLM-generated explanation
        data: Original data dictionary

    Returns:
        JSON-serialized AnalysisResult
    """
    numeric_value = (
        calculation_value
        if isinstance(calculation_value, float)
        else float(calculation_value or 0.0)
    )

    result = AnalysisResult(
        calculation=calculation_str or "",
        value=numeric_value,
        formatted_value=str(formatted_value),
        reasoning=reasoning,
        data_points_used=data,
    )

    return result.model_dump_json()


def _build_analysis_error(
    error_msg: str,
    analysis_type: str,
    context: dict | None,
) -> str:
    """Build error result for analysis agent.

    Args:
        error_msg: Error message
        analysis_type: Type of analysis that failed
        context: Original context data

    Returns:
        JSON-serialized error result
    """
    error_result = {
        "error": error_msg,
        "analysis_type": analysis_type,
        "data_points_used": context.get("data") if context else {},
        "success": False,
    }

    return json.dumps(error_result)


def _validate_analysis_inputs(
    analysis_type: str,
    data: dict[str, float],
) -> None:
    """Validate analysis inputs.

    Args:
        analysis_type: Type of analysis to perform
        data: Financial data points

    Raises:
        ValueError: If validation fails
    """
    valid_types = {"yoy_growth", "variance", "trend", "percentage"}
    if analysis_type not in valid_types:
        raise ValueError(f"Invalid analysis_type: {analysis_type}. Must be one of {valid_types}")

    if not data:
        raise ValueError("No financial data available for analysis")


async def _perform_analysis_with_reasoning(
    analysis_type: str,
    data: dict[str, float],
) -> tuple[float | None, str | None, str, str]:
    """Perform calculation and get Claude reasoning.

    Args:
        analysis_type: Type of analysis to perform
        data: Financial data points

    Returns:
        Tuple of (calculation_value, calculation_str, formatted_value, reasoning)
    """
    calculation_value, calculation_str, trend_direction = _execute_analysis_calculation(
        analysis_type, data
    )
    formatted_value = _format_analysis_value(calculation_value, analysis_type, trend_direction)

    reasoning = await _get_claude_reasoning(
        data=data,
        analysis_type=analysis_type,
        calculation=calculation_str or "",
        value=calculation_value if calculation_value is not None else 0.0,
        formatted_value=formatted_value,
        context=None,
    )

    return calculation_value, calculation_str, formatted_value, reasoning


@tool
async def analysis_agent(
    instruction: str,
    context: dict | None = None,
) -> str:
    """Analysis Agent: Perform financial calculations and reasoning.

    Story 3.3 AC1-AC3: Implements financial analysis with Claude Haiku
    for structured reasoning over calculation results.

    Args:
        instruction: Task instruction containing analysis directive and data
        context: Context data from previous agents containing financial data points

    Returns:
        JSON string containing:
        {
            "calculation": Formula string (e.g., "(12.0 - 10.0) / 10.0 = 0.20"),
            "value": Numerical result (e.g., 0.20),
            "formatted_value": Human-readable format (e.g., "+20%"),
            "reasoning": LLM-generated explanation,
            "data_points_used": Original data dictionary
        }

    Supported Analysis Types:
        - yoy_growth: Year-over-year growth percentage
        - variance: Difference between two values (budget vs actual)
        - trend: Detect increasing/decreasing/stable pattern
        - percentage: Calculate part/whole percentage

    Performance Constraints (NFR5):
        - Target execution time: <800ms p50, <1200ms p95
        - Log execution time via structured logging
    """
    start_time = time.time()
    success = False
    error_msg = None
    analysis_type = "yoy_growth"

    try:
        analysis_type, data = _extract_analysis_type_and_data(instruction, context)

        logger.info(
            "Analysis agent called",
            extra={
                "instruction": instruction[:100],
                "analysis_type": analysis_type,
                "data_keys": list(data.keys()) if data else [],
                "has_context": context is not None,
            },
        )

        _validate_analysis_inputs(analysis_type, data)

        (
            calculation_value,
            calculation_str,
            formatted_value,
            reasoning,
        ) = await _perform_analysis_with_reasoning(analysis_type, data)

        success = True
        execution_time = (time.time() - start_time) * 1000

        logger.info(
            "Analysis agent completed",
            extra={
                "analysis_type": analysis_type,
                "success": success,
                "execution_time_ms": execution_time,
            },
        )

        return _build_analysis_result(
            calculation_str or "",
            calculation_value,
            formatted_value,
            reasoning,
            data,
        )

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        error_msg = str(e)

        logger.error(
            "Analysis agent failed",
            extra={
                "analysis_type": analysis_type,
                "error": error_msg,
                "execution_time_ms": execution_time,
            },
            exc_info=True,
        )

        return _build_analysis_error(error_msg, analysis_type, context)
