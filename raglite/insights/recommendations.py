"""Strategic recommendation engine from financial insights.

Story 4.8: Generates actionable recommendations based on financial data analysis.
Target: ~80-120 lines per Tech Spec (comprehensive docstrings acceptable).
"""

import time
from datetime import UTC, datetime

from raglite.shared.logging import get_logger
from raglite.shared.models import (
    Insight,
    InsightCategory,
    Recommendation,
    RecommendationCategory,
    RecommendationResult,
)

logger = get_logger(__name__)


def calculate_impact_score(insight: Insight) -> int:
    """Calculate recommendation impact score (1-10) based on insight priority and category.

    Story 4.8 AC2: Impact scoring algorithm.

    Args:
        insight: Input insight to score

    Returns:
        Impact score from 1 (low) to 10 (high)

    Example:
        >>> calculate_impact_score(Insight(category=InsightCategory.RISK, priority=1, ...))
        10
        >>> calculate_impact_score(Insight(category=InsightCategory.TREND, priority=3, ...))
        5
    """
    # Base score from insight priority (inverted: priority 1 = high impact)
    # Priority 1 -> 9, Priority 2 -> 7, Priority 3 -> 5, Priority 4 -> 3, Priority 5 -> 1
    base_score = 11 - min(insight.priority * 2, 10)

    # Boost for critical categories
    if insight.category == InsightCategory.RISK:
        base_score = min(base_score + 2, 10)
    elif insight.category == InsightCategory.STRATEGIC_PRIORITY:
        base_score = min(base_score + 1, 10)
    elif insight.category == InsightCategory.OPPORTUNITY:
        base_score = min(base_score + 1, 10)

    return max(1, min(base_score, 10))


def categorize_recommendation(insight: Insight) -> RecommendationCategory:
    """Map insight category to recommendation category.

    Story 4.8 AC1: Category mapping logic.

    Args:
        insight: Input insight to categorize

    Returns:
        RecommendationCategory for the resulting recommendation

    Example:
        >>> categorize_recommendation(Insight(category=InsightCategory.RISK, ...))
        RecommendationCategory.RISK_MITIGATION
    """
    if insight.category == InsightCategory.RISK:
        return RecommendationCategory.RISK_MITIGATION
    elif insight.category == InsightCategory.OPPORTUNITY:
        # Determine if cost-related or revenue-related from supporting data
        supporting_str = str(insight.supporting_data).lower()
        if "cost" in supporting_str or "expense" in supporting_str:
            return RecommendationCategory.COST_REDUCTION
        return RecommendationCategory.REVENUE_GROWTH
    elif insight.category == InsightCategory.ANOMALY:
        return RecommendationCategory.OPERATIONAL_EFFICIENCY
    elif insight.category == InsightCategory.STRATEGIC_PRIORITY:
        return RecommendationCategory.STRATEGIC_INVESTMENT
    else:  # TREND
        return RecommendationCategory.OPERATIONAL_EFFICIENCY


def determine_urgency(insight: Insight, impact_score: int) -> str:
    """Determine urgency level based on insight priority and impact score.

    Story 4.8 Task 3.5: Urgency level determination.

    Args:
        insight: Input insight
        impact_score: Calculated impact score

    Returns:
        Urgency level: "high", "medium", or "low"
    """
    # High urgency: critical priority or high impact
    if insight.priority == 1 or impact_score >= 8:
        return "high"
    # Low urgency: low priority and low impact
    elif insight.priority >= 4 and impact_score <= 4:
        return "low"
    return "medium"


async def synthesize_recommendation(
    insight: Insight,
    category: RecommendationCategory,
) -> tuple[str, str, str, list[str]]:
    """Generate LLM-powered recommendation synthesis.

    Story 4.8 AC1/AC3: Strategic reasoning for recommendations.

    Args:
        insight: Input insight to generate recommendation from
        category: Recommendation category

    Returns:
        Tuple of (title, description, rationale, action_steps)

    Example:
        >>> title, desc, rationale, actions = await synthesize_recommendation(insight, category)
    """
    from raglite.shared.clients import get_mistral_client

    # Build context for LLM
    context = f"""Insight Summary: {insight.summary}
Category: {insight.category.value}
Priority: {insight.priority}/5
Supporting Data: {insight.supporting_data}
Rationale: {insight.rationale}
Recommended Action: {insight.recommended_action}"""

    prompt = f"""Based on this financial insight, generate a strategic recommendation:

{context}

Recommendation Category: {category.value}

Provide:
1. TITLE: A concise recommendation title (max 50 chars)
2. DESCRIPTION: A detailed description (2-3 sentences)
3. RATIONALE: Why this recommendation matters strategically (2-3 sentences)
4. ACTIONS: 3-5 specific action steps (numbered)

Respond in this exact format:
TITLE: [your title]
DESCRIPTION: [your description]
RATIONALE: [your rationale]
ACTIONS:
1. [action 1]
2. [action 2]
3. [action 3]"""

    try:
        client = get_mistral_client()
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content if response.choices else ""

        # Parse response
        title = ""
        description = ""
        rationale = ""
        actions: list[str] = []
        in_actions = False

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("TITLE:"):
                title = line[6:].strip()
                in_actions = False
            elif line.startswith("DESCRIPTION:"):
                description = line[12:].strip()
                in_actions = False
            elif line.startswith("RATIONALE:"):
                rationale = line[10:].strip()
                in_actions = False
            elif line.startswith("ACTIONS:"):
                in_actions = True
            elif in_actions and line and line[0].isdigit():
                # Parse numbered action (e.g., "1. Action text")
                action_text = line.split(".", 1)[-1].strip() if "." in line else line
                if action_text:
                    actions.append(action_text)

        # Fallbacks
        if not title:
            title = f"{category.value.replace('_', ' ').title()} Recommendation"
        if not description:
            description = insight.summary
        if not rationale:
            rationale = insight.rationale or "Based on financial analysis."
        if not actions:
            actions = [
                "Review the underlying data",
                "Assess impact on business objectives",
                "Develop action plan with stakeholders",
            ]

        logger.info(
            "Recommendation synthesized",
            extra={
                "category": category.value,
                "title": title[:50],
                "action_count": len(actions),
            },
        )

        return title, description, rationale, actions

    except Exception as e:
        logger.warning(f"LLM synthesis failed: {e}", extra={"error": str(e)})
        # Fallback synthesis
        title = f"{category.value.replace('_', ' ').title()} Recommendation"
        description = insight.summary
        rationale = insight.rationale or "Based on financial analysis."
        actions = [
            "Review the underlying data",
            "Assess impact on business objectives",
            "Develop action plan with stakeholders",
        ]
        return title, description, rationale, actions


def _get_insight_key(insight: Insight) -> str:
    """Extract unique key for deduplication based on insight content."""
    return f"{insight.category.value}:{':'.join(sorted(insight.sources))}"


def filter_recommendations(
    recommendations: list[Recommendation],
    *,
    category: RecommendationCategory | None = None,
    min_impact: int | None = None,
    limit: int | None = None,
) -> list[Recommendation]:
    """Filter and limit recommendations by category, impact threshold, or count.

    Story 4.8 Task 4.3: Recommendation filtering.

    Args:
        recommendations: List of recommendations to filter
        category: Optional category filter
        min_impact: Optional minimum impact score (1-10, inclusive)
        limit: Optional max number of results

    Returns:
        Filtered list of recommendations

    Example:
        >>> filtered = filter_recommendations(recs, category=RecommendationCategory.RISK_MITIGATION, limit=5)
    """
    result = recommendations

    if category:
        result = [r for r in result if r.category == category]

    if min_impact:
        result = [r for r in result if r.impact_score >= min_impact]

    if limit:
        result = result[:limit]

    return result


async def _process_single_insight(
    insight: Insight,
    seen_keys: set[str],
    *,
    auto_synthesize: bool = True,
) -> Recommendation | None:
    """Process a single insight into a recommendation.

    Args:
        insight: Input insight to process
        seen_keys: Set of already-processed insight keys for deduplication
        auto_synthesize: Whether to use LLM synthesis

    Returns:
        Recommendation object or None if deduplicated

    Story 4.8: Extracted from generate_recommendations() for function size management.
    """
    # Deduplication
    insight_key = _get_insight_key(insight)
    if insight_key in seen_keys:
        return None
    seen_keys.add(insight_key)

    # Calculate scores and category
    category = categorize_recommendation(insight)
    impact_score = calculate_impact_score(insight)
    urgency = determine_urgency(insight, impact_score)

    if auto_synthesize:
        (
            title,
            description,
            rationale,
            action_steps,
        ) = await synthesize_recommendation(insight, category)
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
        recommendation = await _process_single_insight(
            insight, seen_keys, auto_synthesize=auto_synthesize
        )
        if recommendation:
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
