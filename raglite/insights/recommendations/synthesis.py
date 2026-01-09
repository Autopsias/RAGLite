"""LLM-powered recommendation synthesis.

Story 4.8 AC1/AC3: Strategic reasoning for recommendations.
"""

from raglite.shared.logging import get_logger
from raglite.shared.models import Insight, RecommendationCategory

logger = get_logger(__name__)


def _build_prompt(insight: Insight, category: RecommendationCategory) -> str:
    """Build LLM prompt for recommendation synthesis.

    Args:
        insight: Input insight to generate recommendation from
        category: Recommendation category

    Returns:
        Formatted prompt string
    """
    context = f"""Insight Summary: {insight.summary}
Category: {insight.category.value}
Priority: {insight.priority}/5
Supporting Data: {insight.supporting_data}
Rationale: {insight.rationale}
Recommended Action: {insight.recommended_action}"""

    return f"""Based on this financial insight, generate a strategic recommendation:

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


def _parse_llm_response(content: str) -> tuple[str, str, str, list[str]]:
    """Parse LLM response into structured components.

    Args:
        content: Raw LLM response text

    Returns:
        Tuple of (title, description, rationale, action_steps)
    """
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

    return title, description, rationale, actions


def _generate_fallback(
    insight: Insight,
    category: RecommendationCategory,
) -> tuple[str, str, str, list[str]]:
    """Generate fallback recommendation when LLM fails.

    Args:
        insight: Input insight
        category: Recommendation category

    Returns:
        Tuple of (title, description, rationale, action_steps)
    """
    title = f"{category.value.replace('_', ' ').title()} Recommendation"
    description = insight.summary
    rationale = insight.rationale or "Based on financial analysis."
    actions = [
        "Review the underlying data",
        "Assess impact on business objectives",
        "Develop action plan with stakeholders",
    ]
    return title, description, rationale, actions


def _apply_fallbacks(
    title: str,
    description: str,
    rationale: str,
    actions: list[str],
    insight: Insight,
    category: RecommendationCategory,
) -> tuple[str, str, str, list[str]]:
    """Apply fallback values for missing recommendation components.

    Args:
        title: Parsed title (may be empty)
        description: Parsed description (may be empty)
        rationale: Parsed rationale (may be empty)
        actions: Parsed action steps (may be empty)
        insight: Input insight
        category: Recommendation category

    Returns:
        Tuple with all missing components filled
    """
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
    return title, description, rationale, actions


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

    prompt = _build_prompt(insight, category)

    try:
        client = get_mistral_client()
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content if response.choices else ""

        title, description, rationale, actions = _parse_llm_response(content)
        title, description, rationale, actions = _apply_fallbacks(
            title, description, rationale, actions, insight, category
        )

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
        return _generate_fallback(insight, category)
