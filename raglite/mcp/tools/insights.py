"""Insights MCP tools."""

import time

from raglite.main import mcp
from raglite.mcp.tools.insights_helpers import (
    SUPPORTED_INSIGHT_CATEGORIES,
    TIME_PERIOD_MAPPINGS,
    format_insights_for_display,
    parse_insights_query,
)
from raglite.retrieval.search import QueryError
from raglite.shared.logging import get_logger
from raglite.shared.models import (
    InsightCategory,
    InsightsQueryRequest,
    InsightsQueryResponse,
    Recommendation,
)

logger = get_logger(__name__)


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
        from raglite.forecasting.timeseries import extract_timeseries
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
