"""Insights query parser and formatting helpers."""

import re

from raglite.shared.models import Insight, InsightCategory, Recommendation

# Constants for insight categories and time periods
SUPPORTED_INSIGHT_CATEGORIES = {
    "RISK",
    "OPPORTUNITY",
    "ANOMALY",
    "TREND",
    "STRATEGIC_PRIORITY",
}

TIME_PERIOD_MAPPINGS = {
    "last_quarter": "Previous Quarter",
    "current_quarter": "Current Quarter",
    "last_year": "Last 12 Months",
    "ytd": "Year-to-Date",
}


def parse_insights_query(query: str) -> tuple[InsightCategory | None, str | None]:
    """Parse natural language query to extract category and time period.

    Args:
        query: Natural language query string

    Returns:
        Tuple of (category, time_period) or (None, None) if not found
    """
    query_lower = query.lower()
    category = None
    if re.search(r"\b(?:risk|risks|dangers?|threats?|warnings?)\b", query_lower):
        category = InsightCategory.RISK
    elif re.search(r"\b(?:opportunit(?:y|ies)|growth|potential|upside)\b", query_lower):
        category = InsightCategory.OPPORTUNITY
    elif re.search(r"\b(?:anomal(?:y|ies)|outliers?|unusual|unexpected)\b", query_lower):
        category = InsightCategory.ANOMALY
    elif re.search(r"\b(?:trends?|trending|patterns?|direction)\b", query_lower):
        category = InsightCategory.TREND
    elif re.search(r"\b(?:strategic|priorit(?:y|ies|ize)|focus|important)\b", query_lower):
        category = InsightCategory.STRATEGIC_PRIORITY
    time_period = None
    if re.search(r"\b(?:last|previous)\s*quarter\b", query_lower):
        time_period = "last_quarter"
    elif re.search(r"\b(?:this|current)\s*quarter\b", query_lower):
        time_period = "current_quarter"
    elif re.search(r"\b(?:last|past)\s*(?:year|12\s*months)\b", query_lower):
        time_period = "last_year"
    elif re.search(r"\b(?:year\s*to\s*date|ytd)\b", query_lower):
        time_period = "ytd"
    return category, time_period


def format_insights_for_display(
    insights: list[Insight],
    recommendations: list[Recommendation],
) -> str:
    """Format insights and recommendations for conversational display.

    Args:
        insights: List of insight objects
        recommendations: List of recommendation objects

    Returns:
        Formatted markdown string with insights and recommendations
    """
    lines = []
    if insights:
        critical_count = sum(1 for i in insights if i.priority == 1)
        risk_count = sum(1 for i in insights if i.category == InsightCategory.RISK)
        opp_count = sum(1 for i in insights if i.category == InsightCategory.OPPORTUNITY)
        summary_parts = []
        if critical_count > 0:
            summary_parts.append(f"{critical_count} critical finding(s)")
        if risk_count > 0:
            summary_parts.append(f"{risk_count} risk(s)")
        if opp_count > 0:
            summary_parts.append(f"{opp_count} opportunity(ies)")
        if summary_parts:
            lines.append(f"**Executive Summary:** {', '.join(summary_parts)} identified.\n")
    else:
        lines.append("**Executive Summary:** No significant insights detected.\n")
    if insights:
        lines.append("**Key Insights:**\n")
        for i, insight in enumerate(insights[:5], 1):
            if insight.priority == 1:
                indicator = "🔴 Critical"
            elif insight.priority == 2:
                indicator = "🟠 High"
            elif insight.priority == 3:
                indicator = "🟡 Medium"
            else:
                indicator = "🟢 Low"
            lines.append(f"{i}. [{indicator}] {insight.summary}")
            if insight.rationale:
                lines.append(f"   Rationale: {insight.rationale[:150]}...")
            lines.append("")
    if recommendations:
        lines.append("**Recommended Actions:**\n")
        for i, rec in enumerate(recommendations[:3], 1):
            urgency_icon = "⚡" if rec.urgency == "high" else "📋"
            lines.append(f"{i}. {urgency_icon} {rec.title} (Impact: {rec.impact_score}/10)")
            if rec.action_steps:
                lines.append(f"   Next step: {rec.action_steps[0]}")
            lines.append("")
    return "\n".join(lines)
