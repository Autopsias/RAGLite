"""Insights MCP tools."""

import time

from raglite.main import mcp
from raglite.retrieval.search import QueryError
from raglite.shared.logging import get_logger
from raglite.shared.models import (
    Insight,
    InsightCategory,
    InsightsQueryRequest,
    InsightsQueryResponse,
    Recommendation,
)

logger = get_logger(__name__)

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


@mcp.tool()
async def get_financial_insights(
    request: InsightsQueryRequest,
) -> InsightsQueryResponse:
    """Request proactive financial insights via MCP.
    Story 4.9 AC1-AC5: MCP tool for conversational insight queries combining
    anomaly detection, trend analysis, and strategic recommendations.
    **Supported Categories:** RISK, OPPORTUNITY, ANOMALY, TREND, STRATEGIC_PRIORITY
    **Input Modes:**
    1. **Structured Query (Programmatic):**
       Provide explicit `category` and `time_period` parameters.
       Example:
           >>> request = InsightsQueryRequest(category="RISK", limit=3)
           >>> response = await get_financial_insights(request)
    2. **Natural Language Query (Conversational):**
       Provide a `query` parameter and let the system extract filters.
       Example:
           >>> request = InsightsQueryRequest(query="What risks should I know about?")
           >>> response = await get_financial_insights(request)
    **How It Works:**
    1. Parse query to extract category and time period (if using natural language)
    2. Retrieve anomaly detection results (Story 4.5)
    3. Retrieve trend analysis results (Story 4.6)
    4. Generate insights from anomalies and trends (Story 4.7)
    5. Generate strategic recommendations (Story 4.8)
    6. Filter and rank results by priority/impact
    7. Format for conversational display
    Args:
        request: Insights query parameters containing:
          - category: Optional filter by insight category
          - time_period: Optional time period filter (last_quarter, ytd, etc.)
          - limit: Max insights to return (default 5, max 20)
          - include_recommendations: Include strategic recommendations (default True)
          - query: Optional natural language query
    Returns:
        InsightsQueryResponse containing:
          - insights: Ranked list of Insight objects
          - recommendations: List of Recommendation objects (if requested)
          - formatted_summary: LLM-friendly summary text
          - source_documents: Documents analyzed
    Raises:
        QueryError: If no documents available or insight generation fails
    Example - Structured Query:
        >>> request = InsightsQueryRequest(category="RISK", limit=5)
        >>> response = await get_financial_insights(request)
        >>> print(f"Found {len(response.insights)} risk insights")
    Example - Natural Language Query:
        >>> request = InsightsQueryRequest(query="What should I focus on?")
        >>> response = await get_financial_insights(request)
        >>> print(response.formatted_summary)
        "🔴 Critical: Marketing spend increased 30% with no revenue increase..."
    """
    start_time = time.perf_counter()
    logger.info(
        "Insights query received",
        extra={
            "category_filter": request.category,
            "time_period": request.time_period,
            "limit": request.limit,
            "include_recommendations": request.include_recommendations,
            "query": request.query,
        },
    )
    category_filter = request.category
    time_period = request.time_period
    if request.query and not category_filter:
        parsed_category, parsed_period = parse_insights_query(request.query)
        if parsed_category:
            category_filter = parsed_category.value.upper()
        if parsed_period and not time_period:
            time_period = parsed_period
        logger.info(
            "Parsed natural language query",
            extra={
                "original_query": request.query,
                "parsed_category": category_filter,
                "parsed_period": time_period,
            },
        )
    try:
        from raglite.forecasting.timeseries_extract import extract_timeseries
        from raglite.insights.anomalies import detect_anomalies
        from raglite.insights.proactive import filter_insights, generate_insights
        from raglite.insights.recommendations import generate_recommendations
        from raglite.insights.trends import analyze_trends

        source_documents: list[str] = []
        all_anomalies = []
        all_trends = []
        for metric in ["revenue", "expenses", "cash_flow"]:
            try:
                ts_data = await extract_timeseries(docs=[], metric=metric)
                if ts_data.points:
                    source_documents.extend(ts_data.source_documents)
                    anomaly_result = await detect_anomalies(metric, ts_data)
                    all_anomalies.extend(anomaly_result.anomalies)
            except Exception as e:
                logger.debug(
                    f"Skipping metric {metric} for anomaly detection",
                    extra={"error": str(e)},
                )
        try:
            ts_list = []
            for metric in ["revenue", "expenses", "cash_flow"]:
                try:
                    ts_data = await extract_timeseries(docs=[], metric=metric)
                    if ts_data.points:
                        ts_list.append(ts_data)
                except Exception:
                    continue
            if ts_list:
                ts_dict = {ts.metric_name: ts for ts in ts_list}
                metrics_list = list(ts_dict.keys())
                trend_result = await analyze_trends(metrics_list, ts_dict)
                all_trends.extend(trend_result.trends)
        except Exception as e:
            logger.debug(
                "Trend analysis skipped",
                extra={"error": str(e)},
            )
        source_documents = list(set(source_documents))
        if not all_anomalies and not all_trends:
            logger.info(
                "No insights generated - insufficient data",
                extra={"anomalies_count": 0, "trends_count": 0},
            )
            generation_time_ms = (time.perf_counter() - start_time) * 1000
            return InsightsQueryResponse(
                insights=[],
                recommendations=[],
                total_insights=0,
                total_recommendations=0,
                formatted_summary=(
                    "**No insights available.** Please ingest financial documents "
                    "containing time-series data (revenue, expenses, cash flow) to "
                    "enable proactive insight generation."
                ),
                time_period_analyzed=TIME_PERIOD_MAPPINGS.get(
                    time_period or "all_time", "All available data"
                ),
                generation_time_ms=generation_time_ms,
                source_documents=source_documents,
            )
        insight_result = await generate_insights(
            anomalies=all_anomalies,
            trends=all_trends,
            forecasts=[],
            auto_synthesize=True,
        )
        filtered_insights = insight_result.insights
        if category_filter:
            try:
                category_enum = InsightCategory(category_filter.lower())
                filtered_insights = filter_insights(
                    filtered_insights,
                    category=category_enum,
                )
            except ValueError:
                logger.warning(
                    f"Invalid category filter: {category_filter}",
                    extra={"valid_categories": list(SUPPORTED_INSIGHT_CATEGORIES)},
                )
        filtered_insights = filtered_insights[: request.limit]
        recommendations: list[Recommendation] = []
        total_recommendations = 0
        if request.include_recommendations and filtered_insights:
            try:
                rec_result = await generate_recommendations(
                    insights=filtered_insights,
                    auto_synthesize=True,
                )
                recommendations = rec_result.recommendations[:5]
                total_recommendations = rec_result.total_generated
            except Exception as e:
                logger.warning(
                    "Recommendation generation failed",
                    extra={"error": str(e)},
                )
        formatted_summary = format_insights_for_display(filtered_insights, recommendations)
        generation_time_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Insights query complete",
            extra={
                "category_filter": category_filter,
                "time_period": time_period,
                "insights_count": len(filtered_insights),
                "recommendations_count": len(recommendations),
                "total_insights": insight_result.total_generated,
                "total_recommendations": total_recommendations,
                "generation_time_ms": f"{generation_time_ms:.2f}",
                "source_documents_count": len(source_documents),
            },
        )
        return InsightsQueryResponse(
            insights=filtered_insights,
            recommendations=recommendations,
            total_insights=insight_result.total_generated,
            total_recommendations=total_recommendations,
            formatted_summary=formatted_summary,
            time_period_analyzed=TIME_PERIOD_MAPPINGS.get(
                time_period or "all_time", "All available data"
            ),
            generation_time_ms=generation_time_ms,
            source_documents=source_documents,
        )
    except Exception as e:
        generation_time_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "Insights query failed",
            extra={
                "category_filter": category_filter,
                "time_period": time_period,
                "error": str(e),
                "error_type": type(e).__name__,
                "generation_time_ms": f"{generation_time_ms:.2f}",
            },
            exc_info=True,
        )
        raise QueryError(f"Insight generation failed: {e}") from e


def parse_insights_query(query: str) -> tuple[InsightCategory | None, str | None]:
    import re

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
