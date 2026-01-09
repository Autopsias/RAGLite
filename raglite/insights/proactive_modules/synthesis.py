"""LLM-powered insight synthesis module.

Story 4.7 AC1/AC5: Contextual reasoning combining anomalies, trends, and forecasts.
"""

from raglite.shared.logging import get_logger
from raglite.shared.models import Anomaly, ForecastResult, Trend

logger = get_logger(__name__)


def _build_context(
    anomaly: Anomaly | None,
    trend: Trend | None,
    forecast: ForecastResult | None,
) -> str:
    """Build context string from anomaly, trend, and forecast data.

    Args:
        anomaly: Optional anomaly data
        trend: Optional trend data
        forecast: Optional forecast data

    Returns:
        Context string for LLM prompt
    """
    context_parts = []
    if anomaly:
        context_parts.append(
            f"Anomaly: {anomaly.metric} shows {anomaly.magnitude_pct:.1f}% deviation "
            f"(z-score: {anomaly.z_score}, severity: {anomaly.severity.value}) on {anomaly.date}"
        )
    if trend:
        context_parts.append(
            f"Trend: {trend.metric} is {trend.direction.value} by {trend.magnitude:.1f}% "
            f"(CAGR: {trend.cagr:.1%}) from {trend.start_date} to {trend.end_date}"
        )
    if forecast:
        context_parts.append(
            f"Forecast: {forecast.metric_name} predicted for next {forecast.periods_ahead} periods"
        )

    return "\n".join(context_parts)


def _parse_llm_response(content: str) -> tuple[str, str, str]:
    """Parse LLM response into summary, rationale, and action.

    Args:
        content: Raw LLM response content

    Returns:
        Tuple of (summary, rationale, action)
    """
    summary = ""
    rationale = ""
    action = ""

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("SUMMARY:"):
            summary = line[8:].strip()
        elif line.startswith("RATIONALE:"):
            rationale = line[10:].strip()
        elif line.startswith("ACTION:"):
            action = line[7:].strip()

    return summary, rationale, action


def _generate_fallback_summary(
    anomaly: Anomaly | None,
    trend: Trend | None,
) -> str:
    """Generate fallback summary when LLM parsing fails.

    Args:
        anomaly: Optional anomaly data
        trend: Optional trend data

    Returns:
        Fallback summary string
    """
    if anomaly:
        return f"{anomaly.metric} shows {anomaly.severity.value} deviation of {anomaly.magnitude_pct:.1f}%"
    elif trend:
        return f"{trend.metric} {trend.direction.value} trend of {trend.magnitude:.1f}%"
    else:
        return "Financial metric requires attention"


def _get_error_fallback(
    anomaly: Anomaly | None,
    trend: Trend | None,
) -> tuple[str, str, str]:
    """Get structured fallback response when LLM call fails.

    Args:
        anomaly: Optional anomaly data
        trend: Optional trend data

    Returns:
        Tuple of (summary, rationale, action)
    """
    if anomaly:
        return (
            f"{anomaly.metric} shows {anomaly.severity.value} deviation of {anomaly.magnitude_pct:.1f}%",
            f"Value of {anomaly.value} deviates significantly from expected {anomaly.expected_value}.",
            "Investigate the cause of this deviation.",
        )
    elif trend:
        return (
            f"{trend.metric} {trend.direction.value} trend of {trend.magnitude:.1f}%",
            f"Trend from {trend.start_date} to {trend.end_date} shows {trend.cagr:.1%} CAGR.",
            "Monitor this trend and plan accordingly.",
        )
    else:
        return (
            "Financial metric requires attention",
            "Forecast data indicates uncertainty.",
            "Review forecast assumptions and data quality.",
        )


async def synthesize_insight(
    anomaly: Anomaly | None = None,
    trend: Trend | None = None,
    forecast: ForecastResult | None = None,
) -> tuple[str, str, str]:
    """Generate LLM-powered insight synthesis with rationale and recommendation.

    Story 4.7 AC1/AC5: Contextual reasoning combining anomalies, trends, and forecasts.

    Args:
        anomaly: Optional anomaly data
        trend: Optional trend data
        forecast: Optional forecast data

    Returns:
        Tuple of (summary, rationale, recommended_action)

    Example:
        >>> summary, rationale, action = await synthesize_insight(anomaly=anomaly)
        >>> print(summary)
        "Marketing spend increased 30% with no revenue increase - potential inefficiency"
    """
    from raglite.shared.clients import get_mistral_client

    context = _build_context(anomaly, trend, forecast)

    prompt = f"""Analyze this financial data and provide:
1. A one-sentence summary (max 100 chars)
2. A brief rationale (2-3 sentences explaining the significance)
3. A recommended action (1 sentence)

Financial Data:
{context}

Respond in this exact format:
SUMMARY: [your summary]
RATIONALE: [your rationale]
ACTION: [your recommended action]"""

    try:
        client = get_mistral_client()
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content if response.choices else ""

        summary, rationale, action = _parse_llm_response(content)

        # Fallback if parsing fails
        if not summary:
            summary = _generate_fallback_summary(anomaly, trend)

        logger.info(
            "Insight synthesized",
            extra={
                "has_anomaly": anomaly is not None,
                "has_trend": trend is not None,
                "has_forecast": forecast is not None,
            },
        )

        return summary, rationale, action

    except Exception as e:
        logger.warning(f"LLM synthesis failed: {e}", extra={"error": str(e)})
        return _get_error_fallback(anomaly, trend)
