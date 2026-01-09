"""Main recommendation generation engine.

Story 4.8 AC1-AC5: Strategic recommendation engine with LLM synthesis.
"""

import time
from datetime import UTC, datetime

from raglite.shared.logging import get_logger
from raglite.shared.models import Insight, Recommendation, RecommendationResult

from .scoring import calculate_impact_score, categorize_recommendation, determine_urgency
from .synthesis import synthesize_recommendation

logger = get_logger(__name__)


def _get_insight_key(insight: Insight) -> str:
    """Extract unique key for deduplication based on insight content."""
    return f"{insight.category.value}:{':'.join(sorted(insight.sources))}"


async def _process_insight_to_recommendation(
    insight: Insight,
    auto_synthesize: bool,
) -> Recommendation:
    """Convert a single insight into a recommendation.

    Args:
        insight: Source insight to convert
        auto_synthesize: If True, generate LLM recommendations

    Returns:
        Recommendation object with calculated scores and content
    """
    category = categorize_recommendation(insight)
    impact_score = calculate_impact_score(insight)
    urgency = determine_urgency(insight, impact_score)

    if auto_synthesize:
        title, description, rationale, action_steps = await synthesize_recommendation(
            insight, category
        )
    else:
        title = f"{category.value.replace('_', ' ').title()} Recommendation"
        description = insight.summary
        rationale = ""
        action_steps = []

    recommendation = Recommendation(
        category=category,
        impact_score=impact_score,
        title=title,
        description=description,
        rationale=rationale,
        supporting_evidence=insight.supporting_data,
        action_steps=action_steps,
        urgency=urgency,
        sources=insight.sources,
        created_at=datetime.now(UTC),
    )

    logger.info(
        "Recommendation generated",
        extra={
            "category": category.value,
            "impact_score": impact_score,
            "urgency": urgency,
            "sources_count": len(insight.sources),
        },
    )

    return recommendation


async def generate_recommendations(
    insights: list[Insight],
    context: str | None = None,
    *,
    auto_synthesize: bool = True,
) -> RecommendationResult:
    """Generate strategic recommendations from analyzed insights.

    Story 4.8 AC1-AC5: Strategic recommendation engine with LLM synthesis.

    Args:
        insights: List of proactive insights from Story 4.7
        context: Optional additional context (company strategy, constraints)
        auto_synthesize: If True, generate LLM recommendations. Default True.

    Returns:
        RecommendationResult containing:
          - recommendations: List of Recommendation objects sorted by impact
          - total_generated: Count before filtering
          - generation_method: "LLM synthesis (Mistral Large)"
          - insights_analyzed: Number of insights processed

    Raises:
        ValueError: If insights list is empty

    Example:
        >>> from raglite.insights.proactive import Insight, InsightCategory
        >>> insights = [Insight(category=InsightCategory.RISK, priority=1, ...)]
        >>> result = await generate_recommendations(insights)
        >>> print(result.recommendations[0].category)
        RecommendationCategory.RISK_MITIGATION
    """
    start_time = time.time()

    if not insights:
        raise ValueError("No insights to generate recommendations from")

    logger.info(
        "Starting recommendation generation",
        extra={
            "insights_count": len(insights),
            "auto_synthesize": auto_synthesize,
            "has_context": context is not None,
        },
    )

    recommendations: list[Recommendation] = []
    seen_keys: set[str] = set()

    for insight in insights:
        # Deduplication
        insight_key = _get_insight_key(insight)
        if insight_key in seen_keys:
            continue
        seen_keys.add(insight_key)

        recommendation = await _process_insight_to_recommendation(insight, auto_synthesize)
        recommendations.append(recommendation)

    # Sort by impact score descending (10=highest first)
    recommendations.sort(key=lambda x: x.impact_score, reverse=True)

    total_generated = len(recommendations)
    generation_time_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "Recommendation generation complete",
        extra={
            "total_generated": total_generated,
            "insights_analyzed": len(insights),
            "generation_time_ms": generation_time_ms,
        },
    )

    return RecommendationResult(
        recommendations=recommendations,
        total_generated=total_generated,
        generation_method="LLM synthesis (Mistral Large)" if auto_synthesize else "Rule-based",
        insights_analyzed=len(insights),
    )
