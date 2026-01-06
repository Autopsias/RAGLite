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


async def _parse_query_filters(
    request: InsightsQueryRequest,
) -> tuple[str | None, str | None]:
    """Parse query to extract category and time period filters.

    Args:
        request: Insights query request

    Returns:
        Tuple of (category_filter, time_period)
    """
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
    return category_filter, time_period


async def _collect_anomalies_and_trends() -> tuple[list, list, list[str]]:
    """Collect anomalies and trends from available time-series metrics.

    Returns:
        Tuple of (all_anomalies, all_trends, source_documents)
    """
    from raglite.forecasting.timeseries import extract_timeseries
    from raglite.insights.anomalies import detect_anomalies
    from raglite.insights.trends import analyze_trends

    source_documents: list[str] = []
    all_anomalies = []
    all_trends = []

    # Collect anomalies
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

    # Collect trends
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
    return all_anomalies, all_trends, source_documents


def _create_empty_response(
    source_documents: list[str],
    time_period: str | None,
    generation_time_ms: float,
) -> InsightsQueryResponse:
    """Create response when no insights could be generated.

    Args:
        source_documents: List of source documents analyzed
        time_period: Time period filter
        generation_time_ms: Time taken to generate response

    Returns:
        InsightsQueryResponse with empty insights
    """
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


async def _generate_and_filter_insights(
    all_anomalies: list,
    all_trends: list,
    category_filter: str | None,
    limit: int,
) -> tuple:
    """Generate insights from anomalies/trends and apply filters.

    Args:
        all_anomalies: Detected anomalies
        all_trends: Detected trends
        category_filter: Optional category filter
        limit: Max insights to return

    Returns:
        Tuple of (filtered_insights, insight_result)
    """
    from raglite.insights.proactive import filter_insights, generate_insights

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

    filtered_insights = filtered_insights[:limit]
    return filtered_insights, insight_result


async def _generate_recommendations_if_requested(
    insights: list,
    include_recommendations: bool,
) -> tuple[list[Recommendation], int]:
    """Generate recommendations for insights if requested.

    Args:
        insights: Filtered insights
        include_recommendations: Whether to generate recommendations

    Returns:
        Tuple of (recommendations, total_recommendations)
    """
    from raglite.insights.recommendations import generate_recommendations

    recommendations: list[Recommendation] = []
    total_recommendations = 0

    if include_recommendations and insights:
        try:
            rec_result = await generate_recommendations(
                insights=insights,
                auto_synthesize=True,
            )
            recommendations = rec_result.recommendations[:5]
            total_recommendations = rec_result.total_generated
        except Exception as e:
            logger.warning(
                "Recommendation generation failed",
                extra={"error": str(e)},
            )

    return recommendations, total_recommendations


@mcp.tool()
async def get_financial_insights(
    request: InsightsQueryRequest,
) -> InsightsQueryResponse:
    """Request proactive financial insights via MCP (Story 4.9).

    Combines anomaly detection, trend analysis, and strategic recommendations.
    Supports both structured queries (category/time_period filters) and
    natural language queries.

    Args:
        request: Query parameters (category, time_period, limit, recommendations)

    Returns:
        InsightsQueryResponse with ranked insights, recommendations, and summary

    Raises:
        QueryError: If insight generation fails

    Examples:
        >>> await get_financial_insights(InsightsQueryRequest(category="RISK"))
        >>> await get_financial_insights(InsightsQueryRequest(query="What risks?"))
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

    try:
        # Parse query filters
        category_filter, time_period = await _parse_query_filters(request)

        # Collect anomalies and trends
        all_anomalies, all_trends, source_documents = await _collect_anomalies_and_trends()

        # Check if we have any data
        if not all_anomalies and not all_trends:
            logger.info(
                "No insights generated - insufficient data",
                extra={"anomalies_count": 0, "trends_count": 0},
            )
            generation_time_ms = (time.perf_counter() - start_time) * 1000
            return _create_empty_response(source_documents, time_period, generation_time_ms)

        # Generate and filter insights
        filtered_insights, insight_result = await _generate_and_filter_insights(
            all_anomalies=all_anomalies,
            all_trends=all_trends,
            category_filter=category_filter,
            limit=request.limit,
        )

        # Generate recommendations if requested
        recommendations, total_recommendations = await _generate_recommendations_if_requested(
            insights=filtered_insights,
            include_recommendations=request.include_recommendations,
        )

        # Format and return response
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
                "category_filter": request.category,
                "time_period": request.time_period,
                "error": str(e),
                "error_type": type(e).__name__,
                "generation_time_ms": f"{generation_time_ms:.2f}",
            },
            exc_info=True,
        )
        raise QueryError(f"Insight generation failed: {e}") from e
