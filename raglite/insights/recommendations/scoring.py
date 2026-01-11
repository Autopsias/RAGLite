"""Scoring utilities for recommendations.

Story 4.8 AC2: Impact scoring algorithm and categorization.
"""

from raglite.shared.models import Insight, InsightCategory, RecommendationCategory


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
