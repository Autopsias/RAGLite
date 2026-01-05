"""Filtering utilities for recommendations.

Story 4.8 Task 4.3: Recommendation filtering.
"""

from raglite.shared.models import Recommendation, RecommendationCategory


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
