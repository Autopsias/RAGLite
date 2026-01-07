"""Claude reasoning integration for analysis agent.

This module handles all interactions with Claude Haiku for generating
business explanations of financial analysis results.
"""

from raglite.shared.clients import get_claude_client
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


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
