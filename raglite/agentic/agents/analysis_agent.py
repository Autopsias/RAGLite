"""Analysis Agent for financial calculations and reasoning.

Story 3.3 AC1-AC3: Implements a @tool decorator-based analysis agent
that performs financial calculations (YoY growth, variance, trend, percentage)
and uses Claude Haiku for structured reasoning.

NOTE: Strands import is optional - agentic workflows deferred until Epic 3.
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


from raglite.agentic.state import AnalysisResult
from raglite.shared.clients import get_claude_client
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def _calculate_yoy_growth(data: dict[str, float]) -> tuple[float, str]:
    """Calculate year-over-year growth percentage.

    Expects dict with two values (previous and current).
    Formula: (current - previous) / previous
    """
    if len(data) < 2:
        raise ValueError("YoY growth requires at least 2 data points")

    values = sorted(data.values())
    previous, current = values[0], values[1]

    if previous == 0:
        raise ValueError("Previous value cannot be zero for YoY growth")

    growth = (current - previous) / previous
    calculation = f"({current} - {previous}) / {previous} = {growth:.2f}"

    return growth, calculation


def _calculate_variance(data: dict[str, float]) -> tuple[float, str]:
    """Calculate variance (difference between actual and budget).

    Expects dict with 'budget' and 'actual' keys.
    Formula: (actual - budget) / budget
    """
    if "budget" not in data or "actual" not in data:
        raise ValueError("Variance requires 'budget' and 'actual' keys")

    budget = data["budget"]
    actual = data["actual"]

    if budget == 0:
        raise ValueError("Budget cannot be zero for variance calculation")

    variance = (actual - budget) / budget
    calculation = f"({actual} - {budget}) / {budget} = {variance:.2f}"

    return variance, calculation


def _calculate_trend(data: dict[str, float]) -> tuple[float, str, str]:
    """Detect trend (increasing, decreasing, or stable).

    Calculates slope of data points.

    Returns:
        Tuple of (slope_value, trend_direction, calculation_str)
    """
    if len(data) < 2:
        raise ValueError("Trend detection requires at least 2 data points")

    values = list(data.values())
    n = len(values)

    # Simple linear regression slope
    x_mean = (n - 1) / 2.0  # Indices: 0, 1, 2, ... n-1
    y_mean = sum(values) / n

    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    slope = numerator / denominator if denominator != 0 else 0

    # Determine trend direction
    if slope > 0.1:
        trend = "increasing"
    elif slope < -0.1:
        trend = "decreasing"
    else:
        trend = "stable"

    calculation = f"slope={slope:.2f} per period"

    return slope, trend, calculation


def _calculate_percentage(data: dict[str, float]) -> tuple[float, str]:
    """Calculate percentage (part / whole * 100).

    Expects dict with 'part' and 'whole' keys.
    """
    if "part" not in data or "whole" not in data:
        raise ValueError("Percentage requires 'part' and 'whole' keys")

    part = data["part"]
    whole = data["whole"]

    if whole == 0:
        raise ValueError("Whole cannot be zero for percentage calculation")

    percentage = (part / whole) * 100
    calculation = f"({part} / {whole}) × 100 = {percentage:.2f}"

    return percentage, calculation


@tool
async def analysis_agent(
    data: dict[str, float],
    analysis_type: str,
    context: str | None = None,
) -> str:
    """Analysis Agent: Perform financial calculations and reasoning.

    Story 3.3 AC1-AC3: Implements financial analysis with Claude Haiku
    for structured reasoning over calculation results.

    Args:
        data: Financial data points (e.g., {"Q3_2023_revenue": 10.0, "Q3_2024_revenue": 12.0})
        analysis_type: Type of analysis ("yoy_growth", "variance", "trend", "percentage")
        context: Optional contextual information for LLM reasoning

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

    try:
        logger.info(
            "Analysis agent called",
            extra={
                "analysis_type": analysis_type,
                "data_keys": list(data.keys()),
                "has_context": context is not None,
            },
        )

        # Validate analysis type
        valid_types = {"yoy_growth", "variance", "trend", "percentage"}
        if analysis_type not in valid_types:
            raise ValueError(
                f"Invalid analysis_type: {analysis_type}. Must be one of {valid_types}"
            )

        # Execute appropriate analysis calculation
        calculation_value = None
        calculation_str = None

        if analysis_type == "yoy_growth":
            calculation_value, calculation_str = _calculate_yoy_growth(data)
        elif analysis_type == "variance":
            calculation_value, calculation_str = _calculate_variance(data)
        elif analysis_type == "trend":
            slope_value, trend_direction, calculation_str = _calculate_trend(data)
            calculation_value = slope_value
        elif analysis_type == "percentage":
            calculation_value, calculation_str = _calculate_percentage(data)

        # Format the value for display
        if analysis_type in ["yoy_growth", "variance"]:
            percentage_change = (calculation_value or 0.0) * 100
            sign = "+" if percentage_change >= 0 else ""
            formatted_value = f"{sign}{percentage_change:.1f}%"
        elif analysis_type == "percentage":
            formatted_value = f"{calculation_value:.1f}%"
        elif analysis_type == "trend":
            formatted_value = trend_direction
        else:
            formatted_value = str(calculation_value)

        # Get reasoning from Claude Haiku
        reasoning = await _get_claude_reasoning(
            data=data,
            analysis_type=analysis_type,
            calculation=calculation_str or "",
            value=calculation_value if calculation_value is not None else 0.0,
            formatted_value=formatted_value,
            context=context,
        )

        # Build AnalysisResult
        # All analysis types should have numeric value and formatted display string
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

        return result.model_dump_json()

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

        # Return error metadata as JSON
        error_result = {
            "error": error_msg,
            "analysis_type": analysis_type,
            "data_points_used": data,
            "success": False,
        }

        return json.dumps(error_result)


async def _get_claude_reasoning(
    data: dict[str, float],
    analysis_type: str,
    calculation: str,
    value: float | str,
    formatted_value: str,
    context: str | None = None,
) -> str:
    """Get Claude Haiku reasoning for financial analysis result (AC3).

    Args:
        data: Original financial data
        analysis_type: Type of analysis performed
        calculation: Calculation formula string
        value: Numerical result
        formatted_value: Formatted display value
        context: Optional business context

    Returns:
        LLM-generated reasoning explanation

    Error Handling:
        If Claude API fails, returns default reasoning based on calculation type
    """
    try:
        client = get_claude_client()

        # Build structured prompt for numerical accuracy
        prompt = _build_analysis_prompt(
            data=data,
            analysis_type=analysis_type,
            calculation=calculation,
            value=value,
            formatted_value=formatted_value,
            context=context,
        )

        # Call Claude Haiku (5x faster than Sonnet, 10x cheaper)
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        from anthropic.types import TextBlock

        reasoning = (
            message.content[0].text
            if message.content and isinstance(message.content[0], TextBlock)
            else ""
        )

        logger.info(
            "Claude reasoning obtained",
            extra={
                "analysis_type": analysis_type,
                "reasoning_length": len(reasoning),
            },
        )

        return reasoning

    except Exception as e:
        logger.warning(
            "Claude reasoning failed, returning default explanation",
            extra={"analysis_type": analysis_type, "error": str(e)},
        )

        # Return sensible default reasoning if Claude fails
        return _get_default_reasoning(analysis_type, formatted_value)


def _build_analysis_prompt(
    data: dict[str, float],
    analysis_type: str,
    calculation: str,
    value: float | str,
    formatted_value: str,
    context: str | None = None,
) -> str:
    """Build structured prompt for Claude to ensure numerical accuracy (AC3)."""
    data_str = ", ".join(f"{k}=${v:,.0f}" for k, v in data.items())

    prompt = f"""Provide a concise business explanation for this financial analysis result.

**Analysis Type:** {analysis_type}
**Data:** {data_str}
**Calculation:** {calculation}
**Result:** {formatted_value}"""

    if context:
        prompt += f"\n**Context:** {context}"

    prompt += """\n\nExplain what this result means in business terms (1-2 sentences). Be specific about the numbers and their implications."""

    return prompt


def _get_default_reasoning(analysis_type: str, formatted_value: str) -> str:
    """Return sensible default reasoning if Claude API is unavailable."""
    if analysis_type == "yoy_growth":
        return f"Year-over-year growth shows {formatted_value} change in the metric."
    elif analysis_type == "variance":
        return f"Budget variance is {formatted_value} compared to planned amounts."
    elif analysis_type == "trend":
        return f"The data trend is {formatted_value}."
    else:  # percentage
        return f"The metric represents {formatted_value} of the total."
